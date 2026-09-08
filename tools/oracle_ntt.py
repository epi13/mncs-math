#!/usr/bin/env python3
"""Dev-time oracle for NTT fixtures (independent Python NTT mirror).

Emits tests/tables/ntt.json. The mirror implements DIT NTT directly
from the math (bit-reversal, butterfly stages, inverse with n^-1
scale) in Python integers mod p; agreement with MNCS validates both
the stage indexing and the twiddle computation. The intt(ntt(x)) == x
round-trips are metamorphic (identity expectations), and the
conv-ntt cross-check asserts NTT-convolution equals naive
convolution computed by an independent double loop.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOME = "mncs.math.ntt.v1"
P = 998244353
G = 3

CASES = []


def U(v):
    return {"u64": v}


def USEQ(vs):
    return {"seq": {"of": "u64", "values": vs}}


def case(cid, fn, args, expected, budget=1048576):
    CASES.append({"id": cid, "fn": fn, "args": args,
                  "expect": expected, "budget": budget})


def bitrev(a):
    n = len(a)
    bits = n.bit_length() - 1
    out = [0] * n
    for i, v in enumerate(a):
        r = int(bin(i)[2:].zfill(bits)[::-1], 2)
        out[r] = v
    return out


def ntt(a, root):
    n = len(a)
    a = bitrev(list(a))
    length = 1
    while length < n:
        wlen = pow(root, n // (2 * length), P)
        for i in range(0, n, 2 * length):
            w = 1
            for j in range(length):
                u = a[i + j]
                v = a[i + j + length] * w % P
                a[i + j] = (u + v) % P
                a[i + j + length] = (u - v) % P
                w = w * wlen % P
        length *= 2
    return a


def intt(a, root):
    n = len(a)
    winv = pow(root, P - 2, P)
    a = ntt(a, winv)
    ninv = pow(n, P - 2, P)
    return [v * ninv % P for v in a]


W8 = pow(G, (P - 1) // 8, P)
W16 = pow(G, (P - 1) // 16, P)

V8 = [1, 2, 3, 4, 5, 6, 7, 8]
N8 = ntt(V8, W8)
case("ntt8", "candidate_ntt8", [U(v) for v in V8], [USEQ(N8)])
case("intt8-back", "candidate_intt8", [U(v) for v in N8], [USEQ(V8)])
# metamorphic round-trip on a second vector (identity expectation)
V8B = [10, 0, 99, 1000, 5, 77, 100000, 42]
case("intt8-ntt8-id", "candidate_intt8",
     [U(v) for v in ntt(V8B, W8)], [USEQ(V8B)])

V16 = list(range(1, 17))
N16 = ntt(V16, W16)
case("ntt16", "candidate_ntt16", [U(v) for v in V16], [USEQ(N16)])


def naive_conv(a, b, n):
    r = [0] * n
    for i, x in enumerate(a):
        for j, y in enumerate(b):
            if i + j < n:
                r[i + j] = (r[i + j] + x * y) % P
    return r


A4 = [7, 0, 5, 11]
B4 = [3, 13, 0, 2]
C8 = naive_conv(A4, B4, 8)
case("conv4", "candidate_conv4",
     [U(v) for v in A4 + B4], [USEQ(C8)])
# Cross-implementation: the MNCS NTT convolution of the same inputs
# must equal the naive convolution (asserted in-corpus by sharing C8).
case("conv8-ntt", "candidate_conv8_ntt",
     [U(v) for v in A4 + B4], [USEQ(C8)])

(ROOT / "tests" / "tables" / "ntt.json").write_text(
    json.dumps({"module": HOME, "name": "ntt-shapes",
                "cases": CASES}, indent=1) + "\n")
print("ntt: %d value cases" % len(CASES))
