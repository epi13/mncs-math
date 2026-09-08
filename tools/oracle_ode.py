#!/usr/bin/env python3
"""Dev-time oracle for ODE/stencil fixtures (mirrored integer program).

Emits tests/tables/ode.json. The oracle is the identical milli
fixed-point program in Python: wrapping `+%`/`*%` via mod 2^64 into
signed range, and C-style truncating division via Fraction -> int.
Any divergence is a bug in one of the two mirrors.
"""
import json
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOME = "mncs.math.ode.v1"
M64 = 2**64

CASES = []


def W(v):
    v %= M64
    return v - M64 if v >= 2**63 else v


def T(a, b):
    return int(Fraction(a, b))


def I(v):
    return {"i64": v}


def SEQ(vs):
    return {"seq": {"of": "i64", "values": vs}}


def case(cid, fn, args, expected, budget=32768):
    CASES.append({"id": cid, "fn": fn, "args": args,
                  "expect": expected, "budget": budget})


def euler(x, v):
    return W(x + T(W(v * 100), 1000)), W(v + T(W(W(-x) * 100), 1000))


def rk4(x, v):
    k1x, k1v = v, W(-x)
    k2x = W(v + T(W(k1v * 60), 1000))
    k2v = W(-(W(x + T(W(k1x * 60), 1000))))
    k3x = W(v + T(W(k2v * 60), 1000))
    k3v = W(-(W(x + T(W(k2x * 60), 1000))))
    k4x = W(v + T(W(k3v * 120), 1000))
    k4v = W(-(W(x + T(W(k3x * 120), 1000))))
    dx = W(k1x + W(2 * k2x) + W(2 * k3x) + k4x)
    dv = W(k1v + W(2 * k2v) + W(2 * k3v) + k4v)
    return W(x + T(W(dx * 20), 1000)), W(v + T(W(dv * 20), 1000))


for x, v in [(1000, 0), (0, 1000), (707, 707), (-500, 2000)]:
    nx, nv = euler(x, v)
    case("euler-%d-%d" % (x, v), "entry_euler_sho",
         [I(x), I(v)], [SEQ([nx, nv])])
    rx, rv = rk4(x, v)
    case("rk4-%d-%d" % (x, v), "entry_rk4_sho",
         [I(x), I(v)], [SEQ([rx, rv])])

sx, sv = rk4(1000, 0)
tx, tv = rk4(sx, sv)
case("rk4-2steps", "entry_rk4_sho2", [I(1000), I(0)], [SEQ([tx, tv])])


def decay(x):
    return W(x + T(W(T(W(-x), 10) * 100), 1000))


d3 = decay(decay(decay(100000)))
case("decay-3steps", "entry_decay3", [I(100000)], [I(d3)])

# stencils of exact fixtures: f = x^2 at x = 4,6,8 (h = 2) -> f' = 12
case("d1", "entry_d1", [I(16), I(64), I(2)], [I((64 - 16) // 4)])
# f'' = 2 everywhere for x^2
case("d2", "entry_d2", [I(16), I(36), I(64), I(2)], [I(2)])
# Laplacian of f(x,y) = x^2 + y^2 at (3,5): 2 + 2 = 4, h = 1.
# Neighbors: n = f(3,4) = 25, s = f(3,6) = 45, w = f(2,5) = 29,
# e = f(4,5) = 41; (25 + 45 + 29 + 41 - 4*34)/1 = 4.
case("lap", "entry_lap",
     [I(34), I(25), I(45), I(29), I(41), I(1)], [I(4)])

(ROOT / "tests" / "tables" / "ode.json").write_text(
    json.dumps({"module": HOME, "name": "ode-fixed-step",
                "cases": CASES}, indent=1) + "\n")
print("ode: %d value cases" % len(CASES))
