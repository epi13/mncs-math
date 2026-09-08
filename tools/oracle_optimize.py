#!/usr/bin/env python3
"""Dev-time oracle for optimize fixtures (Python exact arithmetic).

Emits tests/tables/optimize.json. Ternary narrowing is mirrored
through the rational ops and cross-checked independently: the true
minimizer must lie inside the final bracket and the width must shrink
by exactly (2/3)^8.
"""
import json
import sys
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from oracle_linalg import radd, rsub, rmul, rdiv  # noqa
from oracle_numerical import pmirror

HOME = "mncs.math.optimize.v1"
NHOME = "mncs.math.numerical.v1"

CASES = []


def I(v):
    return {"i64": v}


def U(v):
    return {"u64": v}


def bracketout(lan=None, lad=None, uan=None, uad=None, reason=None):
    if reason is not None:
        return {"finite": {"enum": "BracketOut", "variant": "Err",
                           "discriminant": 1, "home": NHOME,
                           "payload": {"reason": I(reason)}}}
    return {"finite": {"enum": "BracketOut", "variant": "Ok",
                       "discriminant": 0, "home": NHOME,
                       "payload": {"lan": I(lan), "lad": I(lad),
                                   "uan": I(uan), "uad": I(uad)}}}


def case(cid, fn, args, expected, budget=1048576):
    CASES.append({"id": cid, "fn": fn, "args": args,
                  "expect": expected, "budget": budget})


def IA(*vs):
    return [I(v) for v in vs]


def ternary_mirror(coef, lan, lad, uan, uad, steps=8):
    lo, hi = (lan, lad), (uan, uad)
    for _ in range(steps):
        w = rsub(hi, lo)
        if w[0] == "err":
            return ("err", w[1])
        t = rdiv(w[1], (3, 1))
        if t[0] == "err":
            return ("err", t[1])
        a = radd(lo, t[1])
        if a[0] == "err":
            return ("err", a[1])
        b = rsub(hi, t[1])
        if b[0] == "err":
            return ("err", b[1])
        f1 = pmirror(coef, a[1])
        f2 = pmirror(coef, b[1])
        if f1[0] == "err":
            return ("err", f1[1])
        if f2[0] == "err":
            return ("err", f2[1])
        v1 = Fraction(f1[1][0][0], f1[1][0][1])
        v2 = Fraction(f2[1][0][0], f2[1][0][1])
        if v1 > v2:
            lo = a[1]
        else:
            hi = b[1]
    return ("ok", (lo, hi))


def main():
    # f(t) = (t-3)^2 = t^2 - 6t + 9, minimizer 3, on [0, 8]
    coef = [9, -6, 1, 0]
    r = ternary_mirror(coef, 0, 1, 8, 1)
    assert r[0] == "ok"
    (lan, lad), (uan, uad) = r[1]
    lo, hi = Fraction(lan, lad), Fraction(uan, uad)
    assert lo <= 3 <= hi, (lo, hi)
    assert hi - lo == Fraction(8, 1) * Fraction(2, 3)**8, (hi - lo)
    case("ternary-quadratic", "entry_ternary8",
         IA(9, -6, 1, 0, 0, 1, 8, 1),
         [bracketout(lan, lad, uan, uad)])
    # f(t) = t^2 + 1 on [-2, 5], minimizer 0
    coef2 = [1, 0, 1, 0]
    r = ternary_mirror(coef2, -2, 1, 5, 1)
    assert r[0] == "ok"
    (lan, lad), (uan, uad) = r[1]
    lo, hi = Fraction(lan, lad), Fraction(uan, uad)
    assert lo <= 0 <= hi, (lo, hi)
    case("ternary-shifted", "entry_ternary8",
         IA(1, 0, 1, 0, -2, 1, 5, 1),
         [bracketout(lan, lad, uan, uad)])

    xs = [5, 3, 8, 1, 7, 2, 6, 4]
    case("argmin-basic", "entry_argmin8", IA(*xs), [U(3)])
    case("argmax-basic", "entry_argmax8", IA(*xs), [U(2)])
    case("argmin-tie-first", "entry_argmin8",
         IA(4, 1, 7, 1, 9, 2, 8, 3), [U(1)])
    case("argmax-tie-first", "entry_argmax8",
         IA(4, 9, 7, 9, 1, 2, 8, 3), [U(1)])
    case("argmin-neg", "entry_argmin8",
         IA(-5, 3, -8, 1, 0, -2, 6, 4), [U(2)])

    table = {"module": HOME, "name": "optimize-exact",
             "cases": CASES}
    out = Path(__file__).resolve().parent.parent / "tests" / "tables" \
        / "optimize.json"
    out.write_text(json.dumps(table, indent=1) + "\n")
    print("wrote %s (%d cases)" % (out.name, len(CASES)))


if __name__ == "__main__":
    main()
