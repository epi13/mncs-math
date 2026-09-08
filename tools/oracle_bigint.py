#!/usr/bin/env python3
"""Dev-time oracle for bigint fixtures (Python exact arithmetic).

Emits tests/tables/bigint.json. Committed corpora remain self-contained;
this script documents how every expected limb pattern was derived.
Limbs print as SIGNED i64 bit patterns matching the [i64; N] storage.
"""
import json
from pathlib import Path

M64 = 2**64 - 1
M63 = 2**63 - 1
MIN64 = -2**63


def limbs(v, n):
    v = v % 2**(64 * n)
    out = []
    for _ in range(n):
        w = v % 2**64
        out.append(w if w <= M63 else w - 2**64)
        v //= 2**64
    return out


def I(v):
    return {"i64": v}


def U(v):
    return {"u64": v}


def SEQ(vs):
    return {"seq": {"of": "i64", "values": vs}}


HOME = "mncs.math.bigint.v1"
EHOME = "mncs.math.error.v1"


def divout(q, r, n):
    ql, rl = limbs(q, n), limbs(r, n)
    payload = {}
    for i, w in enumerate(ql):
        payload["q%d" % i] = I(w)
    for i, w in enumerate(rl):
        payload["r%d" % i] = I(w)
    return {"finite": {"enum": "DivOut%d" % n, "variant": "Ok",
                       "discriminant": 0, "home": HOME, "payload": payload}}


def err(reason, enum, home):
    disc = 1
    return {"finite": {"enum": enum, "variant": "Err", "discriminant": disc,
                       "home": home, "payload": {"reason": I(reason)}}}


def ok(v):
    return {"finite": {"enum": "MathResult", "variant": "Ok", "discriminant": 0,
                       "home": EHOME, "payload": {"value": I(v)}}}


def A2(*vs):
    assert len(vs) == 2
    return [{"i64": v} for v in vs]


def A8(*vs):
    assert len(vs) == 8
    return [{"i64": v} for v in vs]


cases = []


DIVBUDGET = 1048576


def case(cid, fn, args, expect, budget=65536):
    cases.append({"id": cid, "fn": fn, "args": args, "expect": expect,
                  "budget": budget})


# u64 x u64 -> 128
case("wide-lo-max", "entry_mul_wide", [U(M64), U(M64), U(0)], [U(1)])
case("wide-hi-max", "entry_mul_wide", [U(M64), U(M64), U(1)], [U(M64 - 1)])
case("wide-small", "entry_mul_wide", [U(123456789), U(987654321), U(0)],
     [U(123456789 * 987654321 % 2**64)])

# u128 add/sub
case("add2-small", "entry_add2", A2(1, 0) + A2(2, 0), [SEQ([3, 0])])
case("add2-carry", "entry_add2", A2(-1, 0) + A2(1, 0), [SEQ([0, 1])])
case("add2-cy-out", "entry_add2_cy", A2(-1, -1) + A2(1, 0), [U(1)])
case("add2-cy-zero", "entry_add2_cy", A2(1, 0) + A2(2, 0), [U(0)])
case("sub2-basic", "entry_sub2", A2(5, 0) + A2(3, 0), [SEQ([2, 0])])
case("sub2-borrow", "entry_sub2", A2(0, 0) + A2(1, 0),
     [SEQ([-1, -1])])
case("sub2-bw", "entry_sub2_bw", A2(0, 0) + A2(1, 0), [U(1)])

# u128 mul
p = (2**128 - 1) ** 2
case("mul2-max-lo", "entry_mul_lo2", A2(-1, -1) + A2(-1, -1),
     [SEQ(limbs(p % 2**128, 2))])
case("mul2-max-hi", "entry_mul_hi2", A2(-1, -1) + A2(-1, -1),
     [SEQ(limbs(p // 2**128, 2))])
case("mul2-small-lo", "entry_mul_lo2", A2(3, 0) + A2(7, 0), [SEQ([21, 0])])
case("mul2-hi-basic", "entry_mul_hi2", A2(0, 1) + A2(0, 1), [SEQ([1, 0])])
case("mul2-hi-carry", "entry_mul_hi2", A2(-1, 0) + A2(-1, 0),
     [SEQ(limbs(((2**64 - 1) ** 2) // 2**128, 2))])
case("mul2-small-hi", "entry_mul_hi2", A2(3, 0) + A2(7, 0), [SEQ([0, 0])])

# u128 div
q, r = divmod(100, 7)
case("div2-small", "entry_divmod2", A2(100, 0) + A2(7, 0),
     [divout(q, r, 2)])
q, r = divmod(2**100, 3)
case("div2-big", "entry_divmod2", A2(*limbs(2**100, 2)) + A2(3, 0),
     [divout(q, r, 2)])
case("div2-exact", "entry_divmod2", A2(*limbs(2**64 - 1, 2)) + A2(1, 0),
     [divout(2**64 - 1, 0, 2)])
case("div2-zero", "entry_divmod2", A2(100, 0) + A2(0, 0),
     [err(1, "DivOut2", HOME)])

# u128 shifts / cmp / conv
case("shl2-basic", "entry_shl1_2", A2(1, 0), [SEQ([2, 0])])
case("shl2-carry", "entry_shl1_2", A2(MIN64, 0), [SEQ([0, 1])])
case("shr2-basic", "entry_shr1_2", A2(4, 0), [SEQ([2, 0])])
case("shr2-top", "entry_shr1_2", A2(0, 1), [SEQ([MIN64, 0])])
case("cmp2-less", "entry_cmp2", A2(3, 0) + A2(5, 0), [I(-1)])
case("cmp2-equal", "entry_cmp2", A2(5, 7) + A2(5, 7), [I(0)])
case("cmp2-high-wins", "entry_cmp2", A2(0, 1) + A2(-1, 0), [I(1)])
case("scmp2-neg-pos", "entry_scmp2", A2(-1, -1) + A2(1, 0), [I(-1)])
case("scmp2-neg-neg", "entry_scmp2", A2(-5, -1) + A2(-3, -1), [I(-1)])
case("from-i64-neg", "entry_from_i64_2", [I(-5)], [SEQ([-5, -1])])
case("to-i64-ok", "entry_to_i64_2", A2(-5, -1), [ok(-5)])
case("to-i64-pos", "entry_to_i64_2", A2(5, 0), [ok(5)])
case("to-i64-wide", "entry_to_i64_2", A2(5, 1), [err(2, "MathResult", EHOME)])
case("neg2-basic", "entry_neg2", A2(5, 0), [SEQ(limbs(-5 % 2**128, 2))])

# u512 add/sub
case("add8-small", "entry_add8",
     A8(1, 0, 0, 0, 0, 0, 0, 0) + A8(2, 0, 0, 0, 0, 0, 0, 0),
     [SEQ([3, 0, 0, 0, 0, 0, 0, 0])])
a = [0, 0, 0, 0, 1, 0, 0, 0]  # 2^256
b = [-1, -1, -1, -1, 0, 0, 0, 0]  # 2^256 - 1
case("sub8-borrow-chain", "entry_sub8",
     [{"i64": v} for v in a] + [{"i64": v} for v in b],
     [SEQ(limbs(1, 8))])
case("add8-cy", "entry_add8_cy",
     [{"i64": v} for v in [-1]*8] + A8(1, 0, 0, 0, 0, 0, 0, 0), [U(1)])

# u512 mul
case("mul8-small-lo", "entry_mul_lo8",
     A8(3, 0, 0, 0, 0, 0, 0, 0) + A8(7, 0, 0, 0, 0, 0, 0, 0),
     [SEQ([21, 0, 0, 0, 0, 0, 0, 0])])
case("mul8-small-hi", "entry_mul_hi8",
     A8(3, 0, 0, 0, 0, 0, 0, 0) + A8(7, 0, 0, 0, 0, 0, 0, 0),
     [SEQ([0]*8)])
p = (2**256 - 1) ** 2
case("mul8-maxsq-lo", "entry_mul_lo8",
     [{"i64": v} for v in limbs(2**256 - 1, 8)] * 2,
     [SEQ(limbs(p % 2**512, 8))])
case("mul8-maxsq-hi", "entry_mul_hi8",
     [{"i64": v} for v in limbs(2**256 - 1, 8)] * 2,
     [SEQ(limbs(p // 2**512, 8))])

# u512 div
q, r = divmod(2**256 - 1, 2**128 - 1)
case("div8-exact", "entry_divmod8",
     [{"i64": v} for v in limbs(2**256 - 1, 8)] +
     [{"i64": v} for v in limbs(2**128 - 1, 8)],
     [divout(q, r, 8)], DIVBUDGET)
q, r = divmod(10**40, 7)
case("div8-decimal", "entry_divmod8",
     [{"i64": v} for v in limbs(10**40, 8)] + A8(7, 0, 0, 0, 0, 0, 0, 0),
     [divout(q, r, 8)], DIVBUDGET)
case("div8-zero", "entry_divmod8",
     A8(100, 0, 0, 0, 0, 0, 0, 0) + A8(0, 0, 0, 0, 0, 0, 0, 0),
     [err(1, "DivOut8", HOME)])

# u512 signed div (truncation toward zero: -100/7 -> q=-14, r=-2)
case("sdiv8-neg-pos", "entry_sdivmod8",
     [{"i64": v} for v in limbs((-100) % 2**512, 8)] +
     A8(7, 0, 0, 0, 0, 0, 0, 0),
     [divout(2**512 - 14, 2**512 - 2, 8)], DIVBUDGET)
case("sdiv8-pos-neg", "entry_sdivmod8",
     A8(100, 0, 0, 0, 0, 0, 0, 0) +
     [{"i64": v} for v in limbs((-7) % 2**512, 8)],
     [divout(2**512 - 14, 2, 8)], DIVBUDGET)
case("sdiv8-min", "entry_sdivmod8",
     A8(0, 0, 0, 0, 0, 0, 0, MIN64) + A8(1, 0, 0, 0, 0, 0, 0, 0),
     [err(2, "DivOut8", HOME)])

# u512 shifts / cmp / conv / bits
case("shl8-basic", "entry_shl1_8", A8(1, 0, 0, 0, 0, 0, 0, 0),
     [SEQ([2, 0, 0, 0, 0, 0, 0, 0])])
case("shr8-top", "entry_shr1_8", A8(0, 1, 0, 0, 0, 0, 0, 0),
     [SEQ([MIN64, 0, 0, 0, 0, 0, 0, 0])])
case("cmp8-less", "entry_cmp8",
     A8(3, 0, 0, 0, 0, 0, 0, 0) + A8(5, 0, 0, 0, 0, 0, 0, 0), [I(-1)])
case("scmp8-neg-pos", "entry_scmp8",
     A8(-1, -1, -1, -1, -1, -1, -1, -1) + A8(1, 0, 0, 0, 0, 0, 0, 0),
     [I(-1)])
case("from-i64-neg8", "entry_from_i64_8", [I(-5)],
     [SEQ([-5] + [-1]*7)])
case("to-i64-ok8", "entry_to_i64_8", [{"i64": v} for v in [-5] + [-1]*7],
     [ok(-5)])
case("to-i64-wide8", "entry_to_i64_8", A8(0, 1, 0, 0, 0, 0, 0, 0),
     [err(2, "MathResult", EHOME)])
case("neg8-basic", "entry_neg8", A8(5, 0, 0, 0, 0, 0, 0, 0),
     [SEQ(limbs((-5) % 2**512, 8))])
case("bitlen8-zero", "entry_bitlen8", A8(0, 0, 0, 0, 0, 0, 0, 0), [U(0)])
case("bitlen8-one", "entry_bitlen8", A8(1, 0, 0, 0, 0, 0, 0, 0), [U(1)])
case("bitlen8-65", "entry_bitlen8", A8(0, 1, 0, 0, 0, 0, 0, 0), [U(65)])
case("bitlen8-max", "entry_bitlen8", [{"i64": -1}]*8, [U(512)])
case("clz64-zero", "entry_clz64", [U(0)], [U(64)])
case("clz64-one", "entry_clz64", [U(1)], [U(63)])
case("clz64-top", "entry_clz64", [U(2**63)], [U(0)])
case("clz64-max", "entry_clz64", [U(M64)], [U(0)])



def main():
    table = {"module": "mncs.math.bigint.v1", "name": "bigint-limb-kernels",
             "cases": cases}
    out = Path(__file__).resolve().parent.parent / "tests" / "tables" / "bigint.json"
    out.write_text(json.dumps(table, indent=1) + "\n")
    print("wrote %s (%d cases)" % (out.name, len(cases)))



if __name__ == "__main__":
    main()
