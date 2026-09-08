#!/usr/bin/env python3
"""Freeze runnable example corpora (examples/corpora/*.json).

Tables are built in the same abstract spec as tests/tables/*.json and
encoded with tools.mkcorpus, so example corpora match module corpora
byte-for-byte in structure. Values are hand-verified in the module
comments and cross-checked here: the solve fixture recomputes Cramer
coordinates and the residual in Python integers; the sample fixtures
reuse oracle_deterministic.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from mkcorpus import encode  # noqa
from oracle_deterministic import shuffle8  # noqa

ROOT = HERE.parent


def I(v):
    return {"i64": v}


def U(v):
    return {"u64": v}


def corpus_of(modname, name, cases):
    out = []
    for cid, fn, args, expect, budget in cases:
        req = {"schema_version": "0.1",
               "target": {"module": modname, "function": fn},
               "arguments": [encode(a, modname) for a in args],
               "step_budget": budget}
        out.append({"id": cid, "request": req,
                    "expected": [encode(e, modname) for e in expect]})
    return {"schema_version": "0.1", "name": name, "cases": out}


def exout(x0, x1, x2, r0, r1, r2):
    return {"finite": {"enum": "ExOut", "variant": "Ok",
                       "discriminant": 0, "home": "ex.solve.v1",
                       "payload": {"x0": I(x0), "x1": I(x1),
                                   "x2": I(x2), "r0": I(r0),
                                   "r1": I(r1), "r2": I(r2)}}}


def fracout(num, den):
    return {"finite": {"enum": "FracOutcome", "variant": "Ok",
                       "discriminant": 0,
                       "home": "mncs.math.rational.v1",
                       "payload": {"num": I(num), "den": I(den)}}}


def statout(mn, md, vn, vd):
    return {"finite": {"enum": "StatOut", "variant": "Ok",
                       "discriminant": 0,
                       "home": "mncs.math.statistics.v1",
                       "payload": {"mean_n": I(mn), "mean_d": I(md),
                                   "var_n": I(vn), "var_d": I(vd)}}}


def det3(m):
    a, b, c, d, e, f, g, h, i = m
    return a*(e*i - f*h) - b*(d*i - f*g) + c*(d*h - e*g)


def main():
    A = [1, 2, 3, 0, 1, 4, 5, 6, 0]
    b = [1, 2, 3]
    assert det3(A) == 1
    xs = []
    for j in range(3):
        M = list(A)
        for r in range(3):
            M[r*3 + j] = b[r]
        xs.append(det3(M))
    assert xs == [27, -22, 6], xs
    res = [sum(A[r*3 + k] * xs[k] for k in range(3)) - b[r]
           for r in range(3)]
    assert res == [0, 0, 0], res
    solve = corpus_of("ex.solve.v1", "ex-solve", [
        ("unimodular-residual-zero", "entry_ex_solve3",
         [I(v) for v in A + b], [exout(27, -22, 6, 0, 0, 0)], 262144),
    ])
    (ROOT / "examples" / "corpora" / "ex-solve-corpus.json").write_text(
        json.dumps(solve, indent=1) + "\n")

    deck = [1, 2, 3, 4, 5, 6, 7, 8]
    perm, _ = shuffle8(deck, 2026)
    assert sorted(perm) == deck
    expect_min = perm.index(min(perm))
    sample = corpus_of("ex.sample.v1", "ex-sample", [
        ("median-invariant", "entry_ex_median", [U(2026)],
         [fracout(9, 2)], 131072),
        ("mean-var-invariant", "entry_ex_mean_var", [U(2026)],
         [statout(9, 2, 21, 4)], 131072),
        ("argmin-pins-stream", "entry_ex_argmin", [U(2026)],
         [U(expect_min)], 131072),
    ])
    (ROOT / "examples" / "corpora" / "ex-sample-corpus.json").write_text(
        json.dumps(sample, indent=1) + "\n")
    print("wrote example corpora (argmin index: %d)" % expect_min)


if __name__ == "__main__":
    main()
