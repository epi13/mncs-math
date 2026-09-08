#!/usr/bin/env python3
"""Dev-time oracle for interval fixtures (Python exact arithmetic).

Emits tests/tables/interval.json. All expectations are small-integer
exact computations; overflow expectations use saturating inputs where
every evaluation order must fail.
"""
import json
from pathlib import Path

M63 = 2**63 - 1
MIN64 = -2**63

HOME = "mncs.math.interval.v1"
EHOME = "mncs.math.error.v1"

OVF, DIVZ = 2, 1

CASES = []


def I(v):
    return {"i64": v}


def B(v):
    return {"bool": v}


def SEQ(vs):
    return {"seq": {"of": "i64", "values": vs}}


def ivout(lo=None, hi=None, reason=None):
    if reason is not None:
        return {"finite": {"enum": "IvOut", "variant": "Err",
                           "discriminant": 1, "home": HOME,
                           "payload": {"reason": I(reason)}}}
    return {"finite": {"enum": "IvOut", "variant": "Ok",
                       "discriminant": 0, "home": HOME,
                       "payload": {"lo": I(lo), "hi": I(hi)}}}


def ok(v):
    return {"finite": {"enum": "MathResult", "variant": "Ok",
                       "discriminant": 0, "home": EHOME,
                       "payload": {"value": I(v)}}}


def err(code):
    return {"finite": {"enum": "MathResult", "variant": "Err",
                       "discriminant": 1, "home": EHOME,
                       "payload": {"reason": I(code)}}}


def case(cid, fn, args, expected, budget=4096):
    CASES.append({"id": cid, "fn": fn,
                  "args": [I(a) for a in args],
                  "expect": expected, "budget": budget})


def fits(v):
    return MIN64 <= v <= M63


def main():
    # validity / observers
    case("ok-true", "entry_iv_ok", [1, 5], [B(True)])
    case("ok-point", "entry_iv_ok", [3, 3], [B(True)])
    case("ok-empty", "entry_iv_ok", [5, 1], [B(False)])
    case("width-basic", "entry_iv_width", [1, 5], [ok(4)])
    case("width-overflow", "entry_iv_width", [1, M63], [ok(M63 - 1)])
    case("width-min", "entry_iv_width", [MIN64, M63], [err(OVF)])
    case("contains-in", "entry_iv_contains", [1, 5, 3], [B(True)])
    case("contains-edge", "entry_iv_contains", [1, 5, 5], [B(True)])
    case("contains-out", "entry_iv_contains", [1, 5, 6], [B(False)])

    # neg
    case("neg-basic", "entry_iv_neg", [1, 5], [ivout(-5, -1)])
    case("neg-cross", "entry_iv_neg", [-2, 7], [ivout(-7, 2)])
    case("neg-min-lo", "entry_iv_neg", [MIN64, 5], [ivout(reason=OVF)])
    case("neg-min-hi", "entry_iv_neg", [1, MIN64],
         [ivout(reason=OVF)])

    # add / sub
    case("add-basic", "entry_iv_add", [1, 2, 10, 20],
         [ivout(11, 22)])
    case("add-neg", "entry_iv_add", [-5, -1, -3, 4],
         [ivout(-8, 3)])
    case("add-overflow", "entry_iv_add", [M63, M63, 1, 1],
         [ivout(reason=OVF)])
    case("sub-basic", "entry_iv_sub", [1, 2, 10, 20],
         [ivout(-19, -8)])
    case("sub-overflow", "entry_iv_sub", [M63, M63, -1, -1],
         [ivout(reason=OVF)])

    # mul: min/max over the four products
    case("mul-pos", "entry_iv_mul", [1, 2, 10, 20],
         [ivout(10, 40)])
    case("mul-cross", "entry_iv_mul", [-2, 3, -4, 5],
         [ivout(-12, 15)])
    case("mul-neg-neg", "entry_iv_mul", [-5, -2, -7, -3],
         [ivout(6, 35)])
    case("mul-zero", "entry_iv_mul", [0, 0, -7, 9],
         [ivout(0, 0)])
    case("mul-overflow", "entry_iv_mul", [M63, M63, 2, 2],
         [ivout(reason=OVF)])
    case("mul-min-times-neg1", "entry_iv_mul", [MIN64, MIN64, -1, -1],
         [ivout(reason=OVF)])

    # div
    case("div-pos", "entry_iv_div", [1, 2, 10, 20],
         [ivout(0, 0)])  # 1/20..2/10 truncates to 0
    case("div-exact", "entry_iv_div", [10, 20, 2, 2],
         [ivout(5, 10)])
    case("div-neg-divisor", "entry_iv_div", [1, 4, -2, -1],
         [ivout(-4, 0)])  # 1/-1..4/-2 = -4..-1? see note
    case("div-zero-point", "entry_iv_div", [1, 2, 0, 0],
         [ivout(reason=DIVZ)])
    case("div-zero-straddle", "entry_iv_div", [1, 2, -1, 1],
         [ivout(reason=DIVZ)])
    case("div-min-by-neg1", "entry_iv_div", [MIN64, MIN64, -1, -1],
         [ivout(reason=OVF)])

    # lattice ops
    case("intersect-overlap", "entry_iv_intersect", [1, 5, 3, 7],
         [SEQ([3, 5])])
    case("disjoint-false", "entry_iv_disjoint", [1, 5, 3, 7],
         [B(False)])
    case("disjoint-true", "entry_iv_disjoint", [1, 5, 6, 7],
         [B(True)])
    case("hull-basic", "entry_iv_hull", [1, 5, 3, 7],
         [SEQ([1, 7])])
    case("hull-disjoint", "entry_iv_hull", [1, 2, 5, 6],
         [SEQ([1, 6])])

    table = {"module": HOME, "name": "interval-exact",
             "cases": CASES}
    out = Path(__file__).resolve().parent.parent / "tests" / "tables" \
        / "interval.json"
    out.write_text(json.dumps(table, indent=1) + "\n")
    print("wrote %s (%d cases)" % (out.name, len(CASES)))


if __name__ == "__main__":
    main()
