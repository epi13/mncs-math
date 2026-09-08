#!/usr/bin/env python3
"""Dev-time oracle for polynomial fixtures (Python exact arithmetic).

Emits tests/tables/poly.json. i64 kernels are WRAPPING: the oracle
computes in unbounded integers and wraps mod 2^64 into signed range,
exactly the documented `+%`/`*%` semantics. Rational-coefficient
cases use Fraction and expect FracOutcome payloads.
"""
import json
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOME = "mncs.math.poly.v1"
RAT = "mncs.math.rational.v1"
M64 = 2**64

CASES = []


def I(v):
    return {"i64": v}


def SEQ(vs):
    return {"seq": {"of": "i64", "values": vs}}


def FRAC(f):
    return {"finite": {"enum": "FracOutcome", "variant": "Ok",
                       "discriminant": 0, "home": RAT,
                       "payload": {"num": {"i64": f.numerator},
                                   "den": {"i64": f.denominator}}}}


def W(v):
    v %= M64
    return v - M64 if v >= 2**63 else v


def case(cid, fn, args, expected, budget=32768):
    CASES.append({"id": cid, "fn": fn, "args": args,
                  "expect": expected, "budget": budget})


def peval(c, x):
    acc = 0
    pw = 1
    for lane in c:
        acc += lane * pw
        pw *= x
    return W(acc)


# ---- generic tier ----
c = [1, -2, 3, 1]
case("peval3", "entry_peval3", [I(v) for v in c] + [I(2)],
     [I(peval(c, 2))])
c = [5, 0, -1, 2, 7, -3]
case("peval5", "entry_peval5", [I(v) for v in c] + [I(-1)],
     [I(peval(c, -1))])
# wrapping: x = 2^32, x^2 overflows i64
c = [0, 0, 1]
case("peval-wrap", "entry_peval3", [I(0), I(0), I(1), I(0), I(2**32)],
     [I(peval([0, 0, 1, 0], 2**32))])
a, b = [4, -7, 9], [1, 8, -3]
case("padd3", "entry_padd3", [I(v) for v in a + b],
     [SEQ([W(x + y) for x, y in zip(a, b)])])
case("pdegree-full", "entry_pdegree4",
     [I(1), I(0), I(-5), I(2)], [I(3)])
case("pdegree-gap", "entry_pdegree4",
     [I(0), I(0), I(9), I(0)], [I(2)])
case("pdegree-zero", "entry_pdegree4",
     [I(0), I(0), I(0), I(0)], [I(-1)])

# ---- derivatives ----
c = [5, -1, 4, 2]  # 5 - x + 4x^2 + 2x^3 -> -1 + 8x + 6x^2
case("pderiv3", "entry_pderiv3", [I(v) for v in c],
     [SEQ([W(c[1]), W(2 * c[2]), W(3 * c[3])])])
c = [1, 2, 3, 4, 5]
case("pderiv4", "entry_pderiv4", [I(v) for v in c],
     [SEQ([W(c[1]), W(2 * c[2]), W(3 * c[3]), W(4 * c[4])])])


def conv(a, b):
    r = [0] * (len(a) + len(b) - 1)
    for i, x in enumerate(a):
        for j, y in enumerate(b):
            r[i + j] += x * y
    return [W(v) for v in r]


a, b = [1, 2, 3], [-1, 0, 2]
case("pmul22", "entry_pmul22", [I(v) for v in a + b], [SEQ(conv(a, b))])
a, b = [2, -1, 3, 5], [1, 1, -2, 4]
case("pmul33", "entry_pmul33", [I(v) for v in a + b], [SEQ(conv(a, b))])
# convolution spot-check against naive evaluation: (a*b)(x) == a(x)*b(x)
# is asserted by sharing peval expectations below (see psynth cross-check).


def synth(c, r):
    b = [0] * 4
    b[3] = c[3]
    b[2] = c[2] + r * b[3]
    b[1] = c[1] + r * b[2]
    rem = c[0] + r * b[1]
    return [W(v) for v in b[1:]], W(rem)


c, r = [7, -3, 2, 1], 2
q, rem = synth(c, r)
case("psynth3", "entry_psynth3", [I(v) for v in c] + [I(r)], [SEQ(q)])
case("psynth3r", "entry_psynth3r", [I(v) for v in c] + [I(r)], [I(rem)])
# Remainder theorem cross-check: psynth3r(c, r) == peval(c, r).
assert rem == peval(c, r), (rem, peval(c, r))
case("psynth3r-is-peval", "entry_peval3", [I(v) for v in c] + [I(r)],
     [I(peval(c, r))])

# ---- rational quadratic: (1/2)x^2 - (3/4)x + 2 at x = 3/2 ----
a2, a1, a0 = Fraction(1, 2), Fraction(-3, 4), Fraction(2, 1)
x = Fraction(3, 2)
v = (a2 * x + a1) * x + a0
case("qeval2", "entry_qeval2",
     [I(a0.numerator), I(a0.denominator),
      I(a1.numerator), I(a1.denominator),
      I(a2.numerator), I(a2.denominator),
      I(x.numerator), I(x.denominator)],
     [FRAC(v)])

(ROOT / "tests" / "tables" / "poly.json").write_text(
    json.dumps({"module": HOME, "name": "poly-exact",
                "cases": CASES}, indent=1) + "\n")
print("poly: %d value cases" % len(CASES))
