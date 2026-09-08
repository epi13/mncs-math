#!/usr/bin/env python3
"""Dev-time oracle for modular fixtures (Python integers + math.gcd).

Emits tests/tables/modular.json. pow()/mul() with three arguments are
the independent implementation; bgcd cases mirror the MNCS round
function exactly and are emitted only when the mirror converges
within the 64 counted rounds, with math.gcd as the cross-check.
"""
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOME = "mncs.math.modular.v1"

CASES = []


def U(v):
    return {"u64": v}


def USEQ(vs):
    return {"seq": {"of": "u64", "values": vs}}


def case(cid, fn, args, expected, budget=131072):
    CASES.append({"id": cid, "fn": fn, "args": args,
                  "expect": expected, "budget": budget})


# ---- inverses (Fermat) ----
case("inv-3-mod-7", "candidate_minv", [U(3), U(7)], [U(pow(3, 5, 7))])
case("inv-37-mod-101", "candidate_minv", [U(37), U(101)],
     [U(pow(37, 99, 101))])
case("inv-1-mod-13", "candidate_minv", [U(1), U(13)], [U(1)])
case("inv-max-mod", "candidate_minv", [U(2**64 - 2), U(2**64 - 59)],
     [U(pow(2**64 - 2, 2**64 - 61, 2**64 - 59))], budget=2000000)
case("div-6-by-3-mod-7", "candidate_mdiv", [U(6), U(3), U(7)],
     [U(6 * pow(3, 5, 7) % 7)])

# ---- 2x2 modular matrices ----
A = (2, 5, 7, 11)
B = (13, 17, 19, 23)
M = 101


def matmul(A, B, m):
    return (A[0] * B[0] + A[1] * B[2]) % m, \
           (A[0] * B[1] + A[1] * B[3]) % m, \
           (A[2] * B[0] + A[3] * B[2]) % m, \
           (A[2] * B[1] + A[3] * B[3]) % m


C = matmul(A, B, M)
case("mmat2mul", "candidate_mmat2mul",
     [U(v) for v in A + B] + [U(M)], [USEQ(list(C))])
# metamorphic: A * I == A
I2 = (1, 0, 0, 1)
case("mmat2mul-ident", "candidate_mmat2mul",
     [U(v) for v in A + I2] + [U(M)], [USEQ([a % M for a in A])])

a, b, c, d, m = 14, 9, 6, 21, 101
case("mdet2", "candidate_mdet2",
     [U(a), U(b), U(c), U(d), U(m)],
     [U((a * d - b * c) % m)])

# ---- modular Horner ----
coef, x, m = (5, 1, 2, 3), 7, 101
acc = 0
for lane in coef:
    acc = (acc + lane * 1) if False else acc
acc, pw = 0, 1
for lane in coef:
    acc = (acc + lane * pw) % m
    pw = pw * x % m
case("mpoly-eval3", "entry_mpoly_eval3",
     [U(v) for v in coef] + [U(x), U(m)], [U(acc)])


# ---- Stein gcd (mirror + round budget + math.gcd cross-check) ----
def ctz(x):
    n = 0
    while n < 64 and x % 2 == 0:
        x //= 2
        n += 1
    return n


def bgcd(a, b):
    if a == 0:
        return b, 0
    if b == 0:
        return a, 0
    shift = min(ctz(a), ctz(b))
    u, v = a >> ctz(a), b >> ctz(b)
    rounds = 0
    while v != 0 and rounds < 64:
        if u > v:
            u, v = v, (u - v) >> ctz(u - v)
        else:
            u, v = u, (v - u) >> ctz(v - u)
        rounds += 1
    return (u << shift) % 2**64, rounds


for a, b in [(0, 0), (0, 9), (12, 0), (12, 18), (100, 75),
              (1024, 768), (2**40, 2**32 + 8), (999983, 999979),
              (2**32 - 1, 2**32 - 5), (2**63, 2**63),
              (2**64 - 1, 2**64 - 2), (123456789, 987654321)]:
    got, rounds = bgcd(a, b)
    assert got == math.gcd(a, b), (a, b, got)
    assert rounds <= 64, (a, b, rounds)
    case("bgcd-%d-%d" % (a, b), "candidate_bgcd",
         [U(a), U(b)], [U(got)])

(ROOT / "tests" / "tables" / "modular.json").write_text(
    json.dumps({"module": HOME, "name": "modular-prime-field",
                "cases": CASES}, indent=1) + "\n")
print("modular: %d value cases" % len(CASES))
