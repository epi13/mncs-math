#!/usr/bin/env python3
"""Dev-time oracle for fixed-point fixtures.

Simulates src/math/fixed.mncs step-for-step (trunc-toward-zero division,
checked overflow, round-half-away adjustments) and freezes the outputs as
tests/tables/fixed.json. Additionally asserts mathematical ACCURACY of the
transcendentals against real exp/sin/log; violation fails loudly here, so
committed corpora pin both exact outputs and proven error bounds.
"""
import json
import math
from pathlib import Path

M64 = 2**63 - 1
MIN64 = -2**63
EHOME = "mncs.math.error.v1"


def ok(v):
    return {"finite": {"enum": "MathResult", "variant": "Ok", "discriminant": 0,
                       "home": EHOME, "payload": {"value": {"i64": v}}}}


def err(reason):
    return {"finite": {"enum": "MathResult", "variant": "Err", "discriminant": 1,
                       "home": EHOME, "payload": {"reason": {"i64": reason}}}}


def trunc_div(a, b):
    q = abs(a) // abs(b)
    return q if (a >= 0) == (b >= 0) else -q


def trunc_mod(a, b):
    return a - trunc_div(a, b) * b


def ck_add(a, b):
    s = a + b
    return ("err", 2) if s > M64 or s < MIN64 else ("ok", s)


def ck_mul(a, b):
    p = a * b
    return ("err", 2) if p > M64 or p < MIN64 else ("ok", p)


def ck_div(a, b):
    if b == 0:
        return ("err", 1)
    if a == MIN64 and b == -1:
        return ("err", 2)
    return ("ok", trunc_div(a, b))


def res(t):
    return ok(t[1]) if t[0] == "ok" else err(t[1])


# ---- milli ----
def mul_trunc(a, b):
    t = ck_mul(a, b)
    if t[0] == "err":
        return t
    return ("ok", trunc_div(t[1], 1000))


def mul_nearest(a, b):
    t = ck_mul(a, b)
    if t[0] == "err":
        return t
    p = t[1]
    q, r = trunc_div(p, 1000), trunc_mod(p, 1000)
    if p >= 0:
        return ("ok", q + 1 if r >= 500 else q)
    return ("ok", q - 1 if r <= -500 else q)


def div_trunc(a, b):
    if b == 0:
        return ("err", 1)
    t = ck_mul(a, 1000)
    if t[0] == "err":
        return t
    return ck_div(t[1], b)


def div_nearest(a, b):
    if b == 0:
        return ("err", 1)
    t = ck_mul(a, 1000)
    if t[0] == "err":
        return t
    s = t[1]
    neg = (s < 0) ^ (b < 0)
    man, mad = abs(s), abs(b)
    q, r = man // mad, man % mad
    rnd = q + (1 if r * 2 >= mad else 0)
    if neg:
        return ("err", 2) if rnd > 2**63 else ("ok", MIN64 if rnd == 2**63 else -rnd)
    return ("err", 2) if rnd > M64 else ("ok", rnd)


def mul_trunc_micro(a, b):
    t = ck_mul(a, b)
    if t[0] == "err":
        return t
    return ("ok", trunc_div(t[1], 1000000))


def add_micro(a, b):
    return ck_add(a, b)


def div_trunc_micro(a, b):
    if b == 0:
        return ("err", 1)
    t = ck_mul(a, 1000000)
    if t[0] == "err":
        return t
    return ck_div(t[1], b)


def micro_to_milli(x):
    q, r = trunc_div(x, 1000), trunc_mod(x, 1000)
    if r >= 500:
        return q + 1
    if r <= -500:
        return q - 1
    return q


def div_round_int(a, b):
    q, r = trunc_div(a, b), trunc_mod(a, b)
    mr, mb = abs(r), b
    if mr >= mb - mr:
        return q + 1 if a >= 0 else q - 1
    return q


def horner(coeffs, x, mul):
    acc = ("ok", coeffs[0])
    for c in coeffs[1:]:
        if acc[0] == "err":
            return acc
        acc = mul(acc[1], x)
        if acc[0] == "err":
            return acc
        acc = ck_add(acc[1], c)
    return acc


def milli_mul(a, b):
    return mul_trunc(a, b)


EXP_COEFFS = [198, 1389, 8333, 41667, 166667, 500000, 1000000, 1000000]


def taylor_micro(hmilli):
    t = ck_mul(hmilli, 1000)
    if t[0] == "err":
        return t
    return horner(EXP_COEFFS, t[1], mul_trunc_micro)


def exp_impl(x):
    if abs(x) > 9000:
        return ("err", 13)
    h = div_round_int(x, 128)
    r = x - h * 128
    t = taylor_micro(h)
    if t[0] == "err":
        return t
    v = t[1]
    for _ in range(7):
        s = mul_trunc_micro(v, v)
        if s[0] == "err":
            return s
        v = s[1]
    e = taylor_micro(r)
    if e[0] == "err":
        return e
    c = mul_trunc_micro(v, e[1])
    if c[0] == "err":
        return c
    return ("ok", micro_to_milli(c[1]))


def sin_small_impl(r):
    u = mul_trunc(r, r)
    if u[0] == "err":
        return u
    s = ck_mul(u[1], 1000)
    if s[0] == "err":
        return s
    p = horner([3, -198, 8333, -166667, 1000000], s[1], mul_trunc_micro)
    if p[0] == "err":
        return p
    return mul_trunc(r, micro_to_milli(p[1]))


def sin_neg(t):
    s = sin_small_impl(t)
    if s[0] == "err":
        return s
    return ("ok", -s[1])


def sin_impl(x):
    M = 2**64
    k = div_round_int(x, 6283)
    r = ((x * 1000 - k * 6283185) % M + M) % M
    r = r if r < 2**63 else r - M
    r = micro_to_milli(r)
    if r > 1600:
        return sin_small_impl(3142 - r)
    if r < -1600:
        return sin_neg(r + 3142)
    return sin_small_impl(r)


def ln1p_impl(x):
    if abs(x) > 500:
        return ("err", 13)
    # No constant term: ln(1+x) = x * Q(x); the Horner chain builds Q.
    q = horner([-125, 143, -167, 200, -250, 333, -500, 1000], x, milli_mul)
    if q[0] == "err":
        return q
    return milli_mul(q[1], x)


def isqrt_u64(n):
    return math.isqrt(n)


def sqrt_impl(x):
    if x < 0:
        return ("err", 13)
    t = ck_mul(x, 1000)
    if t[0] == "err":
        return t
    return ("ok", isqrt_u64(t[1]))


cases = []


def case(cid, fn, args, expect):
    cases.append({"id": cid, "fn": fn, "args": args, "expect": expect})


def C(cid, fn, args, tup):
    case(cid, fn, args, [res(tup)])


def I(cid, fn, args, v):
    case(cid, fn, args, [{"i64": v}])


# conversions
C("from-int", "entry_from_int_milli", [{"i64": 3}], ck_mul(3, 1000))
C("from-int-max-ok", "entry_from_int_milli", [{"i64": 9223372036854774}],
  ck_mul(9223372036854774, 1000))
C("from-int-overflow", "entry_from_int_milli", [{"i64": 9223372036854775}],
  ck_mul(9223372036854775, 1000))
I("to-int-trunc-pos", "entry_to_int_trunc_milli", [{"i64": 3500}], 3)
I("to-int-trunc-neg", "entry_to_int_trunc_milli", [{"i64": -3500}], -3)
I("to-int-floor-neg", "entry_to_int_floor_milli", [{"i64": -3500}], -4)
I("to-int-floor-pos", "entry_to_int_floor_milli", [{"i64": 3500}], 3)
# add/sat
C("add-basic", "entry_add_milli", [{"i64": 1500}, {"i64": 2300}], ck_add(1500, 2300))
C("add-overflow", "entry_add_milli", [{"i64": M64}, {"i64": 1}], ck_add(M64, 1))
I("add-sat-clamps", "entry_add_sat_milli", [{"i64": M64}, {"i64": 1}], M64)
# mul
C("mul-trunc-basic", "entry_mul_trunc_milli", [{"i64": 1500}, {"i64": 2000}],
  mul_trunc(1500, 2000))
C("mul-trunc-neg", "entry_mul_trunc_milli", [{"i64": -1500}, {"i64": 2000}],
  mul_trunc(-1500, 2000))
C("mul-trunc-frac", "entry_mul_trunc_milli", [{"i64": 1501}, {"i64": 1001}],
  mul_trunc(1501, 1001))
C("mul-nearest-frac", "entry_mul_nearest_milli", [{"i64": 1501}, {"i64": 1001}],
  mul_nearest(1501, 1001))
C("mul-nearest-half", "entry_mul_nearest_milli", [{"i64": 1500}, {"i64": 1001}],
  mul_nearest(1500, 1001))
C("mul-nearest-neg-half", "entry_mul_nearest_milli",
  [{"i64": -1500}, {"i64": 1001}], mul_nearest(-1500, 1001))
C("mul-overflow", "entry_mul_trunc_milli", [{"i64": 10**12}, {"i64": 10**12}],
  mul_trunc(10**12, 10**12))
# div
C("div-trunc-basic", "entry_div_trunc_milli", [{"i64": 3000}, {"i64": 2000}],
  div_trunc(3000, 2000))
C("div-trunc-frac", "entry_div_trunc_milli", [{"i64": 1000}, {"i64": 3000}],
  div_trunc(1000, 3000))
C("div-nearest-frac", "entry_div_nearest_milli", [{"i64": 1000}, {"i64": 3000}],
  div_nearest(1000, 3000))
C("div-nearest-half", "entry_div_nearest_milli", [{"i64": 1000}, {"i64": 2000}],
  div_nearest(1000, 2000))
C("div-nearest-neg", "entry_div_nearest_milli", [{"i64": -1000}, {"i64": 3000}],
  div_nearest(-1000, 3000))
C("div-by-zero", "entry_div_trunc_milli", [{"i64": 1000}, {"i64": 0}],
  ("err", 1))
C("div-overflow", "entry_div_trunc_milli", [{"i64": M64}, {"i64": 1}],
  div_trunc(M64, 1))
# micro
C("micro-mul", "entry_mul_trunc_micro",
  [{"i64": 2000000}, {"i64": 3000000}], mul_trunc_micro(2000000, 3000000))
C("micro-div", "entry_div_trunc_micro",
  [{"i64": 1000000}, {"i64": 2000000}], div_trunc_micro(1000000, 2000000))
I("micro-to-milli-half", "entry_micro_to_milli", [{"i64": 1500}], 2)
I("micro-to-milli-neg-half", "entry_micro_to_milli", [{"i64": -1500}], -2)
I("micro-to-milli-down", "entry_micro_to_milli", [{"i64": 1499}], 1)
C("milli-to-micro", "entry_milli_to_micro", [{"i64": 1500}], ck_mul(1500, 1000))
C("milli-to-micro-overflow", "entry_milli_to_micro", [{"i64": M64}],
  ck_mul(M64, 1000))
# sqrt
C("sqrt-exact", "entry_sqrt_milli", [{"i64": 4000}], sqrt_impl(4000))
C("sqrt-floor", "entry_sqrt_milli", [{"i64": 2000}], sqrt_impl(2000))
C("sqrt-neg", "entry_sqrt_milli", [{"i64": -1}], ("err", 13))
C("sqrt-zero", "entry_sqrt_milli", [{"i64": 0}], ("ok", 0))

# transcendentals with accuracy gates
acc = []


def T(cid, fn, xmilli, tup, trueval, bound):
    got = tup[1] if tup[0] == "ok" else None
    if got is not None:
        gap = abs(got - trueval)
        acc.append((cid, gap, bound))
        assert gap <= bound, "accuracy breach %s: got %d true %d gap %d > %d" % (
            cid, got, trueval, gap, bound)
    case(cid, fn, [{"i64": xmilli}], [res(tup)])


def TE(cid, fn, xmilli, tup):
    # exp accuracy is a MIXED bound: absolute near zero (result rounds to
    # 0 milli there), relative elsewhere. Absolute milli bounds do not
    # scale for exp: repeated squaring amplifies the Taylor value's
    # relative quantization ~2^squarings x, so the honest contract is
    # relative (0.05%) with a 2-milli floor. See docs/fixed-point.md.
    trueval = round(math.exp(xmilli / 1000.0) * 1000)
    bound = max(2, trueval // 2048 + 1)
    T(cid, fn, xmilli, tup, trueval, bound)


TE("exp-zero", "entry_exp_milli", 0, exp_impl(0))
TE("exp-one", "entry_exp_milli", 1000, exp_impl(1000))
TE("exp-neg-one", "entry_exp_milli", -1000, exp_impl(-1000))
TE("exp-nine", "entry_exp_milli", 9000, exp_impl(9000))
TE("exp-neg-nine", "entry_exp_milli", -9000, exp_impl(-9000))
TE("exp-two", "entry_exp_milli", 2000, exp_impl(2000))
case("exp-domain-hi", "entry_exp_milli", [{"i64": 9001}], [err(13)])
case("exp-domain-lo", "entry_exp_milli", [{"i64": -9001}], [err(13)])
T("sin-zero", "entry_sin_milli", 0, sin_impl(0), round(math.sin(0) * 1000), 2)
T("sin-half-pi", "entry_sin_milli", 1571, sin_impl(1571),
  round(math.sin(1.571) * 1000), 2)
T("sin-pi", "entry_sin_milli", 3142, sin_impl(3142),
  round(math.sin(3.142) * 1000), 2)
T("sin-neg-half-pi", "entry_sin_milli", -1571, sin_impl(-1571),
  round(math.sin(-1.571) * 1000), 2)
T("sin-two-pi", "entry_sin_milli", 6283, sin_impl(6283),
  round(math.sin(6.283) * 1000), 2)
T("sin-large", "entry_sin_milli", 100000, sin_impl(100000),
  round(math.sin(100.0) * 1000), 2)
T("ln1p-zero", "entry_ln1p_milli", 0, ln1p_impl(0), round(math.log1p(0) * 1000), 1)
T("ln1p-half", "entry_ln1p_milli", 500, ln1p_impl(500),
  round(math.log1p(0.5) * 1000), 1)
T("ln1p-neg-half", "entry_ln1p_milli", -500, ln1p_impl(-500),
  round(math.log1p(-0.5) * 1000), 1)
T("ln1p-small", "entry_ln1p_milli", 100, ln1p_impl(100),
  round(math.log1p(0.1) * 1000), 1)
case("ln1p-domain", "entry_ln1p_milli", [{"i64": 501}], [err(13)])

print("accuracy gates (milli):")
for cid, gap, bound in acc:
    print("  %s gap=%d bound=%d" % (cid, gap, bound))



def main():
    table = {"module": "mncs.math.fixed.v1", "name": "fixed-point-scales",
             "cases": cases}
    out = Path(__file__).resolve().parent.parent / "tests" / "tables" / "fixed.json"
    out.write_text(json.dumps(table, indent=1) + "\n")
    print("wrote %s (%d cases)" % (out.name, len(cases)))



if __name__ == "__main__":
    main()
