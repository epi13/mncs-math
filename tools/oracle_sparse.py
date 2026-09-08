#!/usr/bin/env python3
"""Dev-time oracle for sparse fixtures (independent Python mirror).

Emits tests/tables/sparse.json. The mirror implements the same
fixed-capacity masked semantics (inactive lanes ignored, duplicate
coordinates summed). The coo/csr SpMV pair shares expectations for
the same logical matrix (cross-implementation), as does a dense
matvec computed by a plain double loop.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOME = "mncs.math.sparse.v1"

CASES = []


def I(v):
    return {"i64": v}


def SEQ(vs):
    return {"seq": {"of": "i64", "values": vs}}


def B(v):
    return {"bool": v}


def case(cid, fn, args, expected, budget=32768):
    CASES.append({"id": cid, "fn": fn, "args": args,
                  "expect": expected, "budget": budget})


def spmv_coo(rows, cols, vals, length, x):
    y = [0, 0, 0, 0]
    for k in range(len(rows)):
        if k < length:
            y[rows[k]] += vals[k] * x[cols[k]]
    return y


def spmv_csr(vals, cols, ptr, x):
    y = []
    for r in range(4):
        acc = 0
        for k in range(len(vals)):
            if ptr[r] <= k < ptr[r + 1]:
                acc += vals[k] * x[cols[k]]
        y.append(acc)
    return y


def dense_matvec(M, x):
    return [sum(row[j] * x[j] for j in range(4)) for row in M]


# Logical 4x4: row0: (0,2) (2,1); row1: (1,3); row2: (0,4) (3,5);
# row3: empty. Plus a duplicate (0,7) to pin summing.
ROWS = [0, 0, 1, 2, 2, 0]
COLS = [0, 2, 1, 0, 3, 0]
VALS = [2, 1, 3, 4, 5, 7]
LN = 6
X = [1, 2, 3, 4]
PAD8 = [0] * (8 - LN)
Y = spmv_coo(ROWS, COLS, VALS, LN, X)

case("spmv-coo", "entry_spmv_coo",
     [I(v) for v in ROWS + PAD8 + COLS + PAD8 + VALS + PAD8 + [LN] + X],
     [SEQ(Y)])

# dense cross-check of the same logical matrix (duplicate summed: 2+7)
M = [[2 + 7, 0, 1, 0], [0, 3, 0, 0], [4, 0, 0, 5], [0, 0, 0, 0]]
assert dense_matvec(M, X) == Y

# CSR form of the same matrix (row-major runs)
CVALS = [2, 7, 1, 3, 4, 5]
CCOLS = [0, 0, 2, 1, 0, 3]
CPTR = [0, 3, 4, 6, 6]
Y2 = spmv_csr(CVALS + [0, 0], CCOLS + [0, 0], CPTR, X)
assert Y2 == Y, (Y2, Y)
case("spmv-csr", "entry_spmv_csr",
     [I(v) for v in CVALS + [0, 0] + CCOLS + [0, 0] + CPTR + X],
     [SEQ(Y2)])

# validation sides
case("coo-valid", "entry_coo_validate",
     [I(0), I(3), I(0), I(3), I(2)], [B(True)])
case("coo-bad-row", "entry_coo_validate",
     [I(0), I(4), I(0), I(0), I(2)], [B(False)])
case("coo-inactive-ignored", "entry_coo_validate",
     [I(0), I(9), I(0), I(9), I(1)], [B(True)])
case("rowptr-ok", "entry_rowptr_ok",
     [I(v) for v in CPTR] + [I(6)], [B(True)])
case("rowptr-nonmono", "entry_rowptr_ok",
     [I(0), I(3), I(2), I(6), I(6), I(6)], [B(False)])
case("rowptr-over-len", "entry_rowptr_ok",
     [I(v) for v in CPTR] + [I(5)], [B(False)])

# transpose: rows<->cols lanes
case("coo-transpose", "entry_coo_transpose",
     [I(0), I(1), I(2), I(3), I(0), I(2)], [SEQ([3, 0, 2, 0, 1, 2])])

# sparse dot: a = {1:10, 4:20}, b = {1:3, 2:5, 4:7} -> 10*3+20*7
case("sdot", "entry_sdot",
     [I(1), I(4), I(0), I(10), I(20), I(0), I(2),
      I(1), I(2), I(4), I(3), I(5), I(7), I(3)],
     [I(10 * 3 + 20 * 7)])

(ROOT / "tests" / "tables" / "sparse.json").write_text(
    json.dumps({"module": HOME, "name": "sparse-fixed-cap",
                "cases": CASES}, indent=1) + "\n")
print("sparse: %d value cases" % len(CASES))
