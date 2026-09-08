#!/usr/bin/env python3
"""Dev-time oracle for tensor data-kernel fixtures (plain Python).

Emits tests/tables/tdata.json. Transpose involution is metamorphic
(transpose twice shares one expectation); contraction/bmm/reduction
use direct index mirrors.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOME = "mncs.math.tdata.v1"

CASES = []


def I(v):
    return {"i64": v}


def U(v):
    return {"u64": v}


def SEQ(vs):
    return {"seq": {"of": "i64", "values": vs}}


def case(cid, fn, args, expected, budget=32768):
    CASES.append({"id": cid, "fn": fn, "args": args,
                  "expect": expected, "budget": budget})


A16 = [3, 1, 4, 1, 5, 9, 2, 6, 5, 3, 5, 8, 9, 7, 9, 3]
T16 = [A16[r * 4 + c] for c in range(4) for r in range(4)]
case("transpose4", "entry_transpose4", [I(v) for v in A16], [SEQ(T16)])
# involution: transpose of the transpose is the input
TT = [T16[r * 4 + c] for c in range(4) for r in range(4)]
assert TT == A16
case("transpose4-involution", "entry_transpose4",
     [I(v) for v in T16], [SEQ(A16)])

A6 = [1, 2, 3, 4, 5, 6]
B6 = [7, 8, 9, 10, 11, 12]
C4 = [sum(A6[r * 3 + k] * B6[k * 2 + c] for k in range(3))
      for r in range(2) for c in range(2)]
case("contract232", "entry_contract232",
     [I(v) for v in A6 + B6], [SEQ(C4)])

A8 = [1, 2, 3, 4, 5, 6, 7, 8]
B8 = [8, 7, 6, 5, 4, 3, 2, 1]
C8 = []
for bb in range(2):
    A = A8[bb * 4:bb * 4 + 4]
    B = B8[bb * 4:bb * 4 + 4]
    C8 += [A[0] * B[0] + A[1] * B[2], A[0] * B[1] + A[1] * B[3],
           A[2] * B[0] + A[3] * B[2], A[2] * B[1] + A[3] * B[3]]
case("bmm2", "entry_bmm2", [I(v) for v in A8 + B8], [SEQ(C8)])

R6 = [1, 2, 3, 4, 5, 6]
case("reduce0-2x3", "entry_reduce0_2x3", [I(v) for v in R6],
     [SEQ([R6[c] + R6[3 + c] for c in range(3)])])

case("bcast-add4", "entry_bcast_add4",
     [I(10), I(20), I(30), I(40), I(5)],
     [SEQ([15, 25, 35, 45])])

# valid convolution: signal 8 x kernel 3 -> 6 lanes
S8 = [1, 2, 3, 4, 5, 6, 7, 8]
K3 = [1, 0, -1]
C6 = [S8[j] * K3[0] + S8[j + 1] * K3[1] + S8[j + 2] * K3[2]
      for j in range(6)]
assert C6 == [-2, -2, -2, -2, -2, -2], C6
case("conv-valid83-edge", "entry_conv_valid83",
     [I(v) for v in S8 + K3], [SEQ(C6)])
K3B = [1, 2, 1]
C6B = [S8[j] * K3B[0] + S8[j + 1] * K3B[1] + S8[j + 2] * K3B[2]
       for j in range(6)]
assert C6B == [8, 12, 16, 20, 24, 28], C6B
case("conv-valid83-smooth", "entry_conv_valid83",
     [I(v) for v in S8 + K3B], [SEQ(C6B)])

# strided gather from an 8-lane signal
G8 = [10, 20, 30, 40, 50, 60, 70, 80]
for cid, start, stride in (("gather-window", 2, 1),
                           ("gather-tail", 4, 1),
                           ("gather-even", 0, 2),
                           ("gather-odd", 1, 2)):
    assert start + 3 * stride < 8
    want = [G8[start + j * stride] for j in range(4)]
    case(cid, "entry_gather_stride4",
         [I(v) for v in G8] + [U(start), U(stride)], [SEQ(want)])

(ROOT / "tests" / "tables" / "tdata.json").write_text(
    json.dumps({"module": HOME, "name": "tdata-kernels",
                "cases": CASES}, indent=1) + "\n")
print("tdata: %d value cases" % len(CASES))
