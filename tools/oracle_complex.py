#!/usr/bin/env python3
"""Dev-time oracle for complex fixtures (exact integer arithmetic).

Simulates src/math/complex.mncs: Gaussian operations with checked i64
semantics and u128 intermediates, fixed-point complex through the milli
kernels of oracle_fixed. Gaussian gcd simulates the implementation's
round-half-away Euclid step-for-step, so associates match exactly.
"""
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import oracle_fixed as F

M64 = 2**63 - 1
MIN64 = -2**63
HOME = "mncs.math.complex.v1"
EHOME = "mncs.math.error.v1"


def gauss(payload=None, reason=None):
    if reason is None:
        re, im = payload
        return {"finite": {"enum": "GaussOutcome", "variant": "Ok", "discriminant": 0,
                           "home": HOME, "payload": {"re": {"i64": re}, "im": {"i64": im}}}}
    return {"finite": {"enum": "GaussOutcome", "variant": "Err", "discriminant": 1,
                       "home": HOME, "payload": {"reason": {"i64": reason}}}}


def cx(payload=None, reason=None):
    if reason is None:
        re, im = payload
        return {"finite": {"enum": "CxOutcome", "variant": "Ok", "discriminant": 0,
                           "home": HOME, "payload": {"re": {"i64": re}, "im": {"i64": im}}}}
    return {"finite": {"enum": "CxOutcome", "variant": "Err", "discriminant": 1,
                       "home": HOME, "payload": {"reason": {"i64": reason}}}}


def ck(v):
    return ("err", 2) if v > M64 or v < MIN64 else ("ok", v)


def g_add(a, b):
    r1, r2 = ck(a[0] + b[0]), ck(a[1] + b[1])
    if r1[0] == "err" or r2[0] == "err":
        return gauss(reason=2)
    return gauss((r1[1], r2[1]))


def g_sub(a, b):
    r1, r2 = ck(a[0] - b[0]), ck(a[1] - b[1])
    if r1[0] == "err" or r2[0] == "err":
        return gauss(reason=2)
    return gauss((r1[1], r2[1]))


def g_mul(a, b):
    ts = [a[0]*b[0], a[1]*b[1], a[0]*b[1], a[1]*b[0]]
    if any(t > M64 or t < MIN64 for t in ts):
        return gauss(reason=2)
    ac, bd, ad, bc = ts
    r1, r2 = ck(ac - bd), ck(ad + bc)
    if r1[0] == "err" or r2[0] == "err":
        return gauss(reason=2)
    return gauss((r1[1], r2[1]))


def g_conj(a):
    if a[1] == MIN64:
        return gauss(reason=2)
    return gauss((a[0], -a[1]))


def norm2(a):
    return a[0]*a[0] + a[1]*a[1]


def limbs128(v):
    v = v % 2**128
    return [w if w <= M64 else w - 2**64 for w in (v % 2**64, v // 2**64)]


def g_abs(a):
    n = norm2(a)
    if n >= 2**64:
        return F.err(11)
    return F.ok(math.isqrt(n))


def trunc_qr(n, d):
    q = abs(n) // abs(d)
    q = q if (n >= 0) == (d >= 0) else -q
    return q, n - q * d


def div_comp(n, d, rnd):
    q, r = trunc_qr(n, d)
    if rnd and 2 * abs(r) >= abs(d):
        q += 1 if n >= 0 else -1
    c = ck(q)
    return ("err", 2) if c[0] == "err" else ("ok", c[1])


def g_div(a, b, rnd):
    den = norm2(b)
    if den == 0:
        return gauss(reason=1)
    nre = a[0]*b[0] + a[1]*b[1]
    nim = a[1]*b[0] - a[0]*b[1]
    qr = div_comp(nre, den, rnd)
    qi = div_comp(nim, den, rnd)
    if qr[0] == "err" or qi[0] == "err":
        return gauss(reason=2)
    return gauss((qr[1], qi[1]))


def g_exact(a, b):
    den = norm2(b)
    if den == 0:
        return gauss(reason=1)
    nre = a[0]*b[0] + a[1]*b[1]
    nim = a[1]*b[0] - a[0]*b[1]
    qr, rr = trunc_qr(nre, den)
    qi, ri = trunc_qr(nim, den)
    if rr != 0 or ri != 0:
        return gauss(reason=13)
    if qr > M64 or qr < MIN64 or qi > M64 or qi < MIN64:
        return gauss(reason=2)
    return gauss((qr, qi))


def c_round_half_away(n, d):
    # complex division rounding identical to the implementation
    q, r = trunc_qr(n, d)
    if 2 * abs(r) >= abs(d):
        q += 1 if n >= 0 else -1
    return (q, r)


def g_gcd(a, b):
    x, y = tuple(a), tuple(b)
    for _ in range(200):
        if y == (0, 0):
            return gauss((x[0], x[1]))
        den = norm2(y)
        nre = x[0]*y[0] + x[1]*y[1]
        nim = x[1]*y[0] - x[0]*y[1]
        qr, _ = c_round_half_away(nre, den)
        qi, _ = c_round_half_away(nim, den)
        # checked multiply/subtract for the remainder
        ts = [y[0]*qr, y[1]*qi, y[1]*qr, y[0]*qi]
        if any(t > M64 or t < MIN64 for t in ts):
            return gauss(reason=2)
        pr = ts[0] - ts[1]
        pi = ts[2] + ts[3]
        rr, ri = ck(x[0] - pr), ck(x[1] - pi)
        if rr[0] == "err" or ri[0] == "err":
            return gauss(reason=2)
        if pr > M64 or pr < MIN64 or pi > M64 or pi < MIN64:
            return gauss(reason=2)
        x, y = y, (rr[1], ri[1])
    return gauss(reason=6)


cases = []


def case(cid, fn, args, expect):
    cases.append({"id": cid, "fn": fn, "args": args, "expect": expect})


def G(a, b):
    args = [{"i64": a[0]}, {"i64": a[1]}, {"i64": b[0]}, {"i64": b[1]}]
    return args


case("g-add", "entry_g_add", G((1, 2), (3, 4)), [g_add((1, 2), (3, 4))])
case("g-add-overflow", "entry_g_add", G((M64, 0), (1, 0)), [g_add((M64, 0), (1, 0))])
case("g-sub", "entry_g_sub", G((5, 7), (2, 10)), [g_sub((5, 7), (2, 10))])
case("g-mul", "entry_g_mul", G((1, 2), (3, 4)), [g_mul((1, 2), (3, 4))])
case("g-mul-i", "entry_g_mul", G((0, 1), (0, 1)), [g_mul((0, 1), (0, 1))])
case("g-mul-overflow", "entry_g_mul", G((M64, 0), (2, 0)),
     [g_mul((M64, 0), (2, 0))])
case("g-conj", "entry_g_conj", [{"i64": 3}, {"i64": -4}], [g_conj((3, -4))])
case("g-conj-min", "entry_g_conj", [{"i64": 0}, {"i64": MIN64}],
     [g_conj((0, MIN64))])
case("g-norm2-basic", "entry_g_norm2", [{"i64": 3}, {"i64": 4}],
     [{"seq": {"of": "i64", "values": limbs128(25)}}])
case("g-norm2-big", "entry_g_norm2", [{"i64": M64}, {"i64": M64}],
     [{"seq": {"of": "i64", "values": limbs128(2 * M64 * M64)}}])
case("g-abs-basic", "entry_g_abs", [{"i64": 3}, {"i64": 4}], [g_abs((3, 4))])
case("g-abs-floor", "entry_g_abs", [{"i64": 2}, {"i64": 2}], [g_abs((2, 2))])
case("g-abs-huge", "entry_g_abs", [{"i64": M64}, {"i64": 0}], [g_abs((M64, 0))])
case("g-div-round", "entry_g_div_round", G((1, 2), (3, 4)),
     [g_div((1, 2), (3, 4), True)])
case("g-div-round-half", "entry_g_div_round", G((1, 1), (2, 0)),
     [g_div((1, 1), (2, 0), True)])
case("g-div-trunc-half", "entry_g_div_trunc", G((1, 1), (2, 0)),
     [g_div((1, 1), (2, 0), False)])
case("g-div-zero", "entry_g_div_round", G((1, 2), (0, 0)),
     [g_div((1, 2), (0, 0), True)])
case("g-div-big-quotient", "entry_g_div_round", G((M64, M64), (1, 0)),
     [g_div((M64, M64), (1, 0), True)])
case("g-exact-yes", "entry_g_exact_div", G((2, 4), (1, 1)),
     [g_exact((2, 4), (1, 1))])
case("g-exact-no", "entry_g_exact_div", G((1, 2), (3, 4)),
     [g_exact((1, 2), (3, 4))])
case("g-exact-zero-div", "entry_g_exact_div", G((1, 2), (0, 0)),
     [g_exact((1, 2), (0, 0))])
case("g-divides-yes", "entry_g_divides", G((2, 4), (1, 1)),
     [{"bool": True}])
case("g-divides-no", "entry_g_divides", G((1, 2), (3, 4)),
     [{"bool": False}])
case("g-gcd-basic", "entry_g_gcd", G((8, 6), (4, 2)), [g_gcd((8, 6), (4, 2))])
case("g-gcd-zero", "entry_g_gcd", G((3, 4), (0, 0)), [g_gcd((3, 4), (0, 0))])
case("g-gcd-coprime", "entry_g_gcd", G((3, 0), (0, 2)), [g_gcd((3, 0), (0, 2))])
case("g-gcd-same", "entry_g_gcd", G((5, 5), (5, 5)), [g_gcd((5, 5), (5, 5))])


def CX(cid, fn, a, b):
    args = [{"i64": a[0]}, {"i64": a[1]}, {"i64": b[0]}, {"i64": b[1]}]
    cases.append({"id": cid, "fn": fn, "args": args, "expect": [None]})
    return len(cases) - 1


def milli_mul(a, b):
    return F.mul_trunc(a, b)


def cx_add(a, b):
    r1, r2 = F.ck_add(a[0], b[0]), F.ck_add(a[1], b[1])
    if r1[0] == "err" or r2[0] == "err":
        return cx(reason=2)
    return cx((r1[1], r2[1]))


def cx_mul(a, b):
    ts = [milli_mul(a[0], b[0]), milli_mul(a[1], b[1]),
          milli_mul(a[0], b[1]), milli_mul(a[1], b[0])]
    if any(t[0] == "err" for t in ts):
        return cx(reason=2)
    ac, bd, ad, bc = [t[1] for t in ts]
    r1, r2 = F.ck_add(ad, bc), F.ck_add(ac, -bd)
    if r1[0] == "err" or r2[0] == "err":
        return cx(reason=2)
    return cx((r2[1], r1[1]))


def cx_div(a, b):
    if b == (0, 0):
        return cx(reason=1)
    cr = milli_mul(b[0], b[0])
    ci = milli_mul(b[1], b[1])
    if cr[0] == "err" or ci[0] == "err":
        return cx(reason=2)
    den = F.ck_add(cr[1], ci[1])
    if den[0] == "err":
        return cx(reason=2)
    if den[1] == 0:
        return cx(reason=2)
    nrs = [milli_mul(a[0], b[0]), milli_mul(a[1], b[1]),
           milli_mul(a[1], b[0]), milli_mul(a[0], b[1])]
    if any(t[0] == "err" for t in nrs):
        return cx(reason=2)
    ac, bd, bc, ad = [t[1] for t in nrs]
    nr = F.ck_add(ac, bd)
    ni = F.ck_add(bc, -ad)
    if nr[0] == "err" or ni[0] == "err":
        return cx(reason=2)
    qr = F.div_trunc(nr[1], den[1])
    qi = F.div_trunc(ni[1], den[1])
    if qr[0] == "err" or qi[0] == "err":
        return cx(reason=2)
    return cx((qr[1], qi[1]))


idx = CX("c-add", "entry_c_add", (1000, 2000), (3000, 4000))
cases[idx]["expect"] = [cx_add((1000, 2000), (3000, 4000))]
idx = CX("c-add-overflow", "entry_c_add", (M64, 0), (1, 0))
cases[idx]["expect"] = [cx_add((M64, 0), (1, 0))]
idx = CX("c-mul-i", "entry_c_mul", (0, 1000), (0, 1000))
cases[idx]["expect"] = [cx_mul((0, 1000), (0, 1000))]
idx = CX("c-mul-basic", "entry_c_mul", (1500, 2000), (3000, -1000))
cases[idx]["expect"] = [cx_mul((1500, 2000), (3000, -1000))]
idx = CX("c-div-basic", "entry_c_div", (1000, 2000), (3000, 4000))
cases[idx]["expect"] = [cx_div((1000, 2000), (3000, 4000))]
idx = CX("c-div-zero", "entry_c_div", (1000, 2000), (0, 0))
cases[idx]["expect"] = [cx_div((1000, 2000), (0, 0))]
case("c-conj", "entry_c_conj", [{"i64": 1500}, {"i64": -2500}],
     [cx((1500, 2500))])
case("c-abs-345", "entry_c_abs", [{"i64": 3000}, {"i64": 4000}],
     [F.res(F.sqrt_impl(F.mul_trunc(3000, 3000)[1] + F.mul_trunc(4000, 4000)[1]))])

table = {"module": "mncs.math.complex.v1", "name": "complex-tiers",
         "cases": cases}
out = Path(__file__).resolve().parent.parent / "tests" / "tables" / "complex.json"
out.write_text(json.dumps(table, indent=1) + "\n")
print("wrote %s (%d cases)" % (out.name, len(cases)))
