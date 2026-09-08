#!/usr/bin/env python3
"""Dev-time oracle for wide-limb fixtures (Python exact integers).

Emits tests/tables/bigintx.json. Values are arbitrary-precision
Python ints split into signed 64-bit little-endian limbs; the MNCS
carry chains must reproduce the same limbs bit-for-bit.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOME = "mncs.math.bigintx.v1"
M64 = 2**64

CASES = []


def S(w):
    w %= M64
    return w - M64 if w >= 2**63 else w


def I(v):
    return {"i64": v}


def U(v):
    return {"u64": v}


def LIMBS(v, n):
    return [I(S((v >> (64 * i)) & (M64 - 1))) for i in range(n)]


def case(cid, fn, args, expected, budget=8000000):
    CASES.append({"id": cid, "fn": fn, "args": args,
                  "expect": expected, "budget": budget})


A = 2**1023 + 123456789
B = 2**1000 + 987654321
S16 = (A + B) % 2**1024
case("add16", "entry_add16", LIMBS(A, 16) + LIMBS(B, 16),
     [{"seq": {"of": "i64", "values": [c["i64"] for c in LIMBS(S16, 16)]}}])
case("add16-cy", "entry_add16_cy",
     LIMBS(2**1024 - 1, 16) + LIMBS(1, 16), [U(1)])

P = (2**512 + 12345) * (2**256 + 999)
case("mul-lo16", "entry_mul_lo16",
     LIMBS(2**512 + 12345, 16) + LIMBS(2**256 + 999, 16),
     [{"seq": {"of": "i64",
               "values": [c["i64"] for c in LIMBS(P % 2**1024, 16)]}}])

case("shl1-16", "entry_shl1_16", LIMBS(2**1023, 16),
     [{"seq": {"of": "i64",
               "values": [c["i64"] for c in LIMBS(0, 16)]}}])
case("shl1-16-low", "entry_shl1_16", LIMBS(7, 16),
     [{"seq": {"of": "i64",
               "values": [c["i64"] for c in LIMBS(14, 16)]}}])

D = 1000000007
V = 2**1000 + 12345678901234567890
case("rem16", "entry_rem16", LIMBS(V, 16) + [U(D)], [U(V % D)])

R = pow(3, 1000, 101)
case("powmod16", "entry_powmod16", LIMBS(3, 16) + [U(1000), U(101)],
     [{"seq": {"of": "i64",
               "values": [c["i64"] for c in LIMBS(R, 16)]}}])

W = sum(i * 2**(64 * i) for i in range(16))
case("split16-lo", "entry_split16_lo", LIMBS(W, 16),
     [{"seq": {"of": "i64",
               "values": [c["i64"] for c in LIMBS(W % 2**512, 8)]}}])
case("split16-hi", "entry_split16_hi", LIMBS(W, 16),
     [{"seq": {"of": "i64",
               "values": [c["i64"] for c in LIMBS(W >> 512, 8)]}}])

C = 2**2000 + 5
E = 2**1999 + 7
case("add32", "entry_add32", LIMBS(C, 32) + LIMBS(E, 32),
     [{"seq": {"of": "i64",
               "values": [c["i64"] for c in LIMBS((C + E) % 2**2048, 32)]}}])

Q = (2**1000 + 1) ** 2 % 2**2048
case("mul-lo32", "entry_mul_lo32",
     LIMBS(2**1000 + 1, 32) + LIMBS(2**1000 + 1, 32),
     [{"seq": {"of": "i64",
               "values": [c["i64"] for c in LIMBS(Q, 32)]}}])

case("shl1-32", "entry_shl1_32", LIMBS(2**2047, 32),
     [{"seq": {"of": "i64",
               "values": [c["i64"] for c in LIMBS(0, 32)]}}])

(ROOT / "tests" / "tables" / "bigintx.json").write_text(
    json.dumps({"module": HOME, "name": "bigint-wide",
                "cases": CASES}, indent=1) + "\n")
print("bigintx: %d value cases" % len(CASES))
