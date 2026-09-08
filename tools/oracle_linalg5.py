#!/usr/bin/env python3
"""Dev-time oracle for 5x5/6x6 fixtures (independent Python mirrors).

Emits tests/tables/linalg5.json. Determinants come from an exact
fraction-free Bareiss mirror; every determinant is cross-checked
against an independent Leibniz permutation sum before freezing
(feasible at 5!/6! terms). Rank cases are built with known rank by
construction and verified by Fraction elimination. Solve cases use a
known integer solution; the residual identity A*n == det*b is
asserted in-oracle, so the corpus residual case re-verifies it
in-MNCS.
"""
import json
from fractions import Fraction
from itertools import permutations
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOME = "mncs.math.linalg5.v1"
RAT = "mncs.math.rational.v1"
ERR = "mncs.math.error.v1"

CASES = []


def I(v):
    return {"i64": v}


def B(v):
    return {"bool": v}


def MAT_OK(v):
    return {"finite": {"enum": "MathResult", "variant": "Ok",
                       "discriminant": 0, "home": ERR,
                       "payload": {"value": {"i64": v}}}}


def SOLVE_OK(xs):
    pay = {}
    for i, (n, d) in enumerate(xs):
        pay["x%dn" % i] = {"i64": n}
        pay["x%dd" % i] = {"i64": d}
    return {"finite": {"enum": "SolveOut5", "variant": "Ok",
                       "discriminant": 0, "home": HOME, "payload": pay}}


def case(cid, fn, args, expected, budget=8000000):
    CASES.append({"id": cid, "fn": fn, "args": args,
                  "expect": expected, "budget": budget})


def bareiss(M):
    n = len(M)
    A = [row[:] for row in M]
    prev, sign = 1, 1
    for k in range(n - 1):
        if A[k][k] == 0:
            piv = next((r for r in range(k + 1, n) if A[r][k] != 0),
                       None)
            if piv is None:
                return 0
            A[k], A[piv] = A[piv], A[k]
            sign = -sign
        for i in range(k + 1, n):
            for j in range(k + 1, n):
                A[i][j] = (A[i][j] * A[k][k] - A[i][k] * A[k][j]) // prev
            A[i][k] = 0
        prev = A[k][k]
    return sign * A[n - 1][n - 1]


def leibniz(M):
    n = len(M)
    tot = 0
    for p in permutations(range(n)):
        inv = sum(1 for i in range(n) for j in range(i + 1, n)
                  if p[i] > p[j])
        t = 1
        for i in range(n):
            t *= M[i][p[i]]
        tot += -t if inv % 2 else t
    return tot


def rank_of(M):
    n = len(M)
    A = [[Fraction(v) for v in row] for row in M]
    r = 0
    for c in range(n):
        piv = next((i for i in range(r, n) if A[i][c] != 0), None)
        if piv is None:
            continue
        A[r], A[piv] = A[piv], A[r]
        for i in range(r + 1, n):
            f = A[i][c] / A[r][c]
            for j in range(c, n):
                A[i][j] -= f * A[r][j]
        r += 1
    return r


def flat(M):
    return [v for row in M for v in row]


def det_case(cid, fn, M, budget):
    d1, d2 = bareiss(M), leibniz(M)
    assert d1 == d2, (cid, d1, d2)
    case(cid, fn, [I(v) for v in flat(M)], [MAT_OK(d1)], budget)


I5 = [[1 if i == j else 0 for j in range(5)] for i in range(5)]
D5 = [[i + 1 if i == j else 0 for j in range(5)] for i in range(5)]
SING5 = [[1, 2, 3, 4, 5], [1, 2, 3, 4, 5], [0, 1, 0, 0, 0],
         [0, 0, 1, 0, 0], [0, 0, 0, 1, 0]]
PIV5 = [[0, 2, 1, 3, 1], [1, 0, 2, 1, 4], [2, 1, 0, 5, 2],
        [1, 3, 2, 0, 1], [4, 1, 3, 2, 0]]
GEN5 = [[2, 1, 3, 0, 1], [1, 0, 2, 1, 4], [3, 2, 0, 5, 2],
        [0, 1, 4, 2, 1], [1, 3, 1, 0, 2]]

det_case("det5-ident", "entry_det5", I5, 4000000)
det_case("det5-diag", "entry_det5", D5, 4000000)
det_case("det5-singular", "entry_det5", SING5, 4000000)
det_case("det5-pivot", "entry_det5", PIV5, 8000000)
det_case("det5-generic", "entry_det5", GEN5, 8000000)

Z5 = [[0] * 5 for _ in range(5)]
R3 = [[1, 0, 2, 0, 1], [0, 1, 1, 0, 0], [2, 1, 5, 0, 2],
      [0, 0, 0, 1, 0], [0, 0, 0, 0, 0]]
for cid, M, want in [("rank5-full", GEN5, 5), ("rank5-zero", Z5, 0),
                     ("rank5-three", R3, 3)]:
    assert rank_of(M) == want, cid
    case(cid, "entry_rank5", [I(v) for v in flat(M)],
         [MAT_OK(want)], 8000000)

# solve: known integer solution, Cramer numerators shared with resid
A = [[2, 1, 0, 1, 3], [1, 3, 1, 0, 1], [0, 1, 2, 1, 0],
     [1, 0, 1, 3, 2], [3, 1, 0, 2, 4]]
XT = [1, 2, -1, 3, 1]
RHS = [sum(A[i][j] * XT[j] for j in range(5)) for i in range(5)]
DET = bareiss(A)
assert DET == leibniz(A) and DET != 0
NS = []
for j in range(5):
    Mj = [row[:] for row in A]
    for i in range(5):
        Mj[i][j] = RHS[i]
    nj = bareiss(Mj)
    assert nj == leibniz(Mj)
    NS.append(nj)
XS = [(Fraction(n, DET).numerator, Fraction(n, DET).denominator)
      for n in NS]
case("solve5", "entry_solve5",
     [I(v) for v in flat(A) + RHS], [SOLVE_OK(XS)], 8000000)
# residual identity with raw (unreduced) numerators det*x
NN = [DET * x for x in XT]
for i in range(5):
    assert sum(A[i][j] * NN[j] for j in range(5)) == DET * RHS[i]
case("resid5", "entry_resid5",
     [I(v) for v in flat(A) + NN + [DET] + RHS], [B(True)], 4000000)

I6 = [[1 if i == j else 0 for j in range(6)] for i in range(6)]
D6 = [[i + 1 if i == j else 0 for j in range(6)] for i in range(6)]
SING6 = [row[:] + [0] for row in SING5[:4]] + [[0] * 6] + \
    [[0, 0, 0, 0, 0, 1]]
SING6 = [[1, 2, 3, 4, 5, 6], [1, 2, 3, 4, 5, 6],
         [0, 1, 0, 0, 0, 0], [0, 0, 1, 0, 0, 0],
         [0, 0, 0, 1, 0, 0], [0, 0, 0, 0, 1, 0]]
GEN6 = [[2, 1, 0, 3, 1, 2], [1, 4, 1, 0, 2, 1], [0, 1, 3, 1, 0, 4],
        [3, 0, 1, 2, 4, 0], [1, 2, 0, 4, 1, 3], [2, 1, 4, 0, 3, 1]]
det_case("det6-ident", "entry_det6", I6, 8000000)
det_case("det6-diag", "entry_det6", D6, 8000000)
det_case("det6-singular", "entry_det6", SING6, 8000000)
det_case("det6-generic", "entry_det6", GEN6, 8000000)

Z6 = [[0] * 6 for _ in range(6)]
# Zero diagonal forces row+column swaps at every step (det = -1).
P6 = [[0, 1, 0, 0, 0, 0], [0, 0, 1, 0, 0, 0], [0, 0, 0, 1, 0, 0],
      [0, 0, 0, 0, 1, 0], [0, 0, 0, 0, 0, 1], [1, 0, 0, 0, 0, 0]]
# Last two rows are combinations of the first four (rank 4).
R4 = [row[:] for row in GEN6[:4]]
R4 += [[R4[0][j] + R4[1][j] for j in range(6)],
       [R4[2][j] - R4[3][j] for j in range(6)]]
assert bareiss(P6) == leibniz(P6) == -1
for cid, M, want in [("rank6-full", GEN6, 6), ("rank6-zero", Z6, 0),
                     ("rank6-swap", P6, 6), ("rank6-four", R4, 4)]:
    assert rank_of(M) == want, cid
    assert (bareiss(M) != 0) == (want == 6), cid
    case(cid, "entry_rank6", [I(v) for v in flat(M)],
         [MAT_OK(want)], 8000000)

(ROOT / "tests" / "tables" / "linalg5.json").write_text(
    json.dumps({"module": HOME, "name": "linalg-5x5-6x6",
                "cases": CASES}, indent=1) + "\n")
print("linalg5: %d value cases" % len(CASES))
