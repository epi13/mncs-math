#!/usr/bin/env python3
"""Dev-time oracle for statistics fixtures (Python exact arithmetic).

Emits tests/tables/statistics.json. The sorting network is verified by
brute force over all 40320 permutations of eight distinct inputs before
any fixture freezes: a wrong comparator list fails loudly here, never
silently in the corpus. Moments are exact integer/rational computations.
"""
import json
from fractions import Fraction
from itertools import permutations
from pathlib import Path

M63 = 2**63 - 1
MIN64 = -2**63

HOME = "mncs.math.statistics.v1"
EHOME = "mncs.math.error.v1"
RHOME = "mncs.math.rational.v1"

OVF = 2

CASES = []

# The exact comparator list mirrored from statistics.mncs sort8.
NETWORK = [(0, 1), (2, 3), (4, 5), (6, 7),
           (0, 2), (1, 3), (4, 6), (5, 7),
           (1, 2), (5, 6), (0, 4), (3, 7),
           (1, 5), (2, 6),
           (2, 4), (3, 5),
           (1, 2), (3, 4), (5, 6)]


def run_net(xs):
    a = list(xs)
    for i, j in NETWORK:
        if a[i] > a[j]:
            a[i], a[j] = a[j], a[i]
    return a


def I(v):
    return {"i64": v}


def SEQ(vs):
    return {"seq": {"of": "i64", "values": vs}}


def ok(v):
    return {"finite": {"enum": "MathResult", "variant": "Ok",
                       "discriminant": 0, "home": EHOME,
                       "payload": {"value": I(v)}}}


def err(code):
    return {"finite": {"enum": "MathResult", "variant": "Err",
                       "discriminant": 1, "home": EHOME,
                       "payload": {"reason": I(code)}}}


def statout(mean=None, var=None, reason=None):
    if reason is not None:
        return {"finite": {"enum": "StatOut", "variant": "Err",
                           "discriminant": 1, "home": HOME,
                           "payload": {"reason": I(reason)}}}
    (mn, md), (vn, vd) = mean, var
    return {"finite": {"enum": "StatOut", "variant": "Ok",
                       "discriminant": 0, "home": HOME,
                       "payload": {"mean_n": I(mn), "mean_d": I(md),
                                   "var_n": I(vn), "var_d": I(vd)}}}


def fracout(num=None, den=None, reason=None):
    if reason is not None:
        return {"finite": {"enum": "FracOutcome", "variant": "Err",
                           "discriminant": 1, "home": RHOME,
                           "payload": {"reason": I(reason)}}}
    return {"finite": {"enum": "FracOutcome", "variant": "Ok",
                       "discriminant": 0, "home": RHOME,
                       "payload": {"num": I(num), "den": I(den)}}}


def case(cid, fn, args, expected, budget=32768):
    CASES.append({"id": cid, "fn": fn,
                  "args": [I(a) for a in args],
                  "expect": expected, "budget": budget})


def fits(v):
    return MIN64 <= v <= M63


def mean_var(xs):
    s1 = sum(xs)
    if not fits(s1):
        return ("err", OVF)
    s2 = sum(v * v for v in xs)
    if not all(fits(v * v) for v in xs) or not fits(s2):
        return ("err", OVF)
    m = Fraction(s1, 8)
    t1 = 8 * s2
    t2 = s1 * s1
    if not (fits(t1) and fits(t2)):
        return ("err", OVF)
    num = t1 - t2
    if not fits(num):
        return ("err", OVF)
    v = Fraction(num, 64)
    assert v >= 0
    return ("ok", ((m.numerator, m.denominator),
                   (v.numerator, v.denominator)))


def main():
    # Prove the network sorts every permutation of 8 distinct inputs.
    base = list(range(8))
    bad = 0
    for p in permutations(base):
        if run_net(p) != base:
            bad += 1
    assert bad == 0, "network fails on %d permutations" % bad
    print("network verified over 40320 permutations")

    xs = [5, 3, 8, 1, 7, 2, 6, 4]
    case("sum-basic", "entry_sum8", xs, [ok(sum(xs))])
    case("sum-overflow", "entry_sum8", [M63] * 8, [err(OVF)])
    case("min-basic", "entry_min8", xs, [I(min(xs))])
    case("max-basic", "entry_max8", xs, [I(max(xs))])
    case("range-basic", "entry_range8", xs, [ok(max(xs) - min(xs))])
    case("range-overflow", "entry_range8",
         [MIN64, 0, 0, 0, 0, 0, 0, M63], [err(OVF)])

    # mean 36/8 = 9/2, var: S1=36, S2=204: (8*204-1296)/64 = 336/64 = 21/4
    r = mean_var(xs)
    assert r == ("ok", ((9, 2), (21, 4))), r
    case("mean-var-basic", "entry_mean_var8", xs,
         [statout((9, 2), (21, 4))])
    ys = [2, 2, 2, 2, 2, 2, 2, 2]
    r = mean_var(ys)
    assert r == ("ok", ((2, 1), (0, 1))), r
    case("mean-var-const", "entry_mean_var8", ys,
         [statout((2, 1), (0, 1))])
    case("mean-var-overflow", "entry_mean_var8", [M63] * 8,
         [statout(reason=OVF)])
    # median of sorted [1..8] = (4+5)/2 = 9/2
    case("median-basic", "entry_median8", xs, [fracout(9, 2)])
    case("median-even-pair", "entry_median8", ys, [fracout(2, 1)])
    case("median-overflow", "entry_median8", [M63] * 8,
         [fracout(reason=OVF)])

    case("sort-basic", "entry_sort8", xs, [SEQ(sorted(xs))])
    case("sort-sorted", "entry_sort8", sorted(xs), [SEQ(sorted(xs))])
    case("sort-reversed", "entry_sort8", sorted(xs, reverse=True),
         [SEQ(sorted(xs))])
    case("sort-dups", "entry_sort8", [3, 1, 3, 1, 3, 1, 3, 1],
         [SEQ([1, 1, 1, 1, 3, 3, 3, 3])])
    case("sort-neg", "entry_sort8", [-5, 3, -8, 1, 0, -2, 6, 4],
         [SEQ([-8, -5, -2, 0, 1, 3, 4, 6])])

    table = {"module": HOME, "name": "statistics-exact",
             "cases": CASES}
    out = Path(__file__).resolve().parent.parent / "tests" / "tables" \
        / "statistics.json"
    out.write_text(json.dumps(table, indent=1) + "\n")
    print("wrote %s (%d cases)" % (out.name, len(CASES)))


if __name__ == "__main__":
    main()
