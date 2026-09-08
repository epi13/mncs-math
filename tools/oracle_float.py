#!/usr/bin/env python3
"""Dev-time oracle for float fixtures (host IEEE-754 + host libm).

Emits tests/tables/float.json and tests/tables/float-traps.json.
Basic-op expectations use Python floats, which are IEEE-754 binary64
with correctly-rounded +,-,*,/ and conversions -- exactly the MNCS
contract, so bits must agree. sin/cos expectations use the host libm
via math.sin/math.cos, the same host libm every MNCS backend calls;
bits are frozen at generation time and the corpus stays
self-contained afterwards.
"""
import json
import math
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOME = "mncs.math.float.v1"

CASES = []
TRAPS = []


def F(v):
    return {"f64": v}


def B(v):
    return {"bool": v}


def I(v):
    return {"i64": v}


def case(cid, fn, args, expected, budget=4096):
    CASES.append({"id": cid, "fn": fn, "args": args,
                  "expect": expected, "budget": budget})


def trap(cid, fn, args, budget=4096):
    TRAPS.append({"id": cid, "fn": fn, "args": args, "budget": budget})


# ---- basic arithmetic (exact IEEE prediction) ----
case("add", "candidate_fadd", [F(1.5), F(2.25)], [F(1.5 + 2.25)])
case("add-cancel", "candidate_fadd", [F(1e16), F(1.0)], [F(1e16 + 1.0)])
case("sub", "candidate_fsub", [F(5.5), F(8.0)], [F(5.5 - 8.0)])
case("mul", "candidate_fmul", [F(0.1), F(3.0)], [F(0.1 * 3.0)])
case("div", "candidate_fdiv", [F(7.0), F(2.0)], [F(7.0 / 2.0)])
case("div-recur", "candidate_fdiv", [F(1.0), F(3.0)], [F(1.0 / 3.0)])
case("neg", "candidate_fneg", [F(2.5)], [F(0.0 - 2.5)])
case("neg-zero", "candidate_fneg", [F(0.0)], [F(0.0 - 0.0)])
case("neg-negzero", "candidate_fneg", [F(-0.0)], [F(0.0 - -0.0)])

# ---- comparisons ----
case("lt-true", "candidate_flt", [F(1.0), F(2.0)], [B(True)])
case("lt-false", "candidate_flt", [F(2.0), F(2.0)], [B(False)])
case("ge-true", "candidate_fge", [F(2.0), F(2.0)], [B(True)])
case("ge-false", "candidate_fge", [F(1.5), F(2.5)], [B(False)])
case("eq-negzero", "candidate_feq", [F(0.0), F(-0.0)], [B(True)])

# ---- crossings ----
case("i2f-exact", "candidate_i2f", [I(42)], [F(42.0)])
case("i2f-neg", "candidate_i2f", [I(-7)], [F(-7.0)])
case("i2f-round", "candidate_i2f", [I(2**53 + 1)], [F(float(2**53 + 1))])
case("f2i-trunc", "candidate_f2i", [F(7.9)], [I(7)])
case("f2i-neg-trunc", "candidate_f2i", [F(-7.9)], [I(-7)])

# ---- dots ----
case("dot2", "candidate_fdot2",
     [F(2.5), F(-1.5), F(4.0), F(2.0)],
     [F(2.5 * 4.0 + -1.5 * 2.0)])
case("dot3", "candidate_fdot3",
     [F(1.0), F(2.0), F(3.0), F(4.0), F(-5.0), F(6.0)],
     [F(1.0 * 4.0 + 2.0 * -5.0 + 3.0 * 6.0)])
case("dot4-generic", "entry_fdot4",
     [F(1.5), F(2.5), F(-3.5), F(4.5),
      F(2.0), F(-1.0), F(0.5), F(3.0)],
     [F(1.5 * 2.0 + 2.5 * -1.0 + -3.5 * 0.5 + 4.5 * 3.0)])

# ---- Horner cubic: ((3x - 2)x + 1)x + 5 at x = 2 ----
x, c = 2.0, (5.0, 1.0, -2.0, 3.0)
case("horner", "candidate_fhorn3", [F(x)] + [F(v) for v in c],
     [F(((c[3] * x + c[2]) * x + c[1]) * x + c[0])])

# ---- one Newton step on x^3 - 2x - 5 from x0 = 2 ----
x0 = 2.0
cc = x0**3 - 2.0 * x0 - 5.0
dd = 3.0 * x0**2 - 2.0
case("newton-step", "candidate_fnewton_step", [F(x0)],
     [F(x0 - cc / dd)])

# ---- trig (host libm, frozen bits) ----
for xv in (0.0, 0.5, 1.0, -1.0, 3.0):
    case("sin-%s" % xv, "candidate_fsin", [F(xv)], [F(math.sin(xv))])
    case("cos-%s" % xv, "candidate_fcos", [F(xv)], [F(math.cos(xv))])
    s, c_ = math.sin(xv), math.cos(xv)
    case("pythag-%s" % xv, "candidate_fpythag", [F(xv)],
         [F(s * s + c_ * c_)])

# ---- reduction-order witness: (1e16+1)-1e16 vs (1e16-1e16)+1 ----
a = 10000000000000000.0
case("sum-gap", "candidate_fsum_gap", [],
     [F((a + 1.0 - a) - (a - a + 1.0))])

# ---- six-lane reduction orders over identical inputs ----
# Discriminating vector: every order gives a different finite result.
V6 = [1e16, 1e16, -1e16, 2.0, -1e16, 1.0]
A = [F(v) for v in V6]
o_left = ((((V6[0] + V6[1]) + V6[2]) + V6[3]) + V6[4]) + V6[5]
o_right = V6[0] + (V6[1] + (V6[2] + (V6[3] + (V6[4] + V6[5]))))
o_pair = ((V6[0] + V6[1]) + (V6[2] + V6[3])) + (V6[4] + V6[5])
o_eo = ((V6[0] + V6[2]) + V6[4]) + ((V6[1] + V6[3]) + V6[5])
assert len({o_left, o_right, o_pair, o_eo}) == 4, \
    (o_left, o_right, o_pair, o_eo)
assert (o_left, o_right, o_pair, o_eo) == (3.0, 0.0, 2.0, 4.0), \
    (o_left, o_right, o_pair, o_eo)
case("sum6-left", "candidate_fsum_left", A, [F(o_left)])
case("sum6-right", "candidate_fsum_right", A, [F(o_right)])
case("sum6-pair", "candidate_fsum_pair", A, [F(o_pair)])
case("sum6-evenodd", "candidate_fsum_evenodd", A, [F(o_eo)])
case("sum6-loop", "candidate_fsum_loop", A, [F(o_left)])
# Benign control: small integers sum identically in every order.
C6 = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
AC = [F(v) for v in C6]
for cid, fn in (("ctl-left", "candidate_fsum_left"),
                ("ctl-right", "candidate_fsum_right"),
                ("ctl-pair", "candidate_fsum_pair"),
                ("ctl-evenodd", "candidate_fsum_evenodd"),
                ("ctl-loop", "candidate_fsum_loop")):
    case("sum6-%s" % cid, fn, AC, [F(21.0)])

# ---- traps (assert runtime_failure) ----
trap("trap-div-zero", "candidate_fdiv_zero", [F(1.0)])
trap("trap-overflow", "candidate_foverflow", [])
trap("trap-f2i-huge", "candidate_f2i_huge", [])

(ROOT / "tests" / "tables" / "float.json").write_text(
    json.dumps({"module": HOME, "name": "float-binary64",
                "cases": CASES}, indent=1) + "\n")
(ROOT / "tests" / "tables" / "float-traps.json").write_text(
    json.dumps({"module": HOME, "name": "float-traps",
                "cases": TRAPS}, indent=1) + "\n")
print("float: %d value cases, %d trap cases"
      % (len(CASES), len(TRAPS)))
