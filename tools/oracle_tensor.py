#!/usr/bin/env python3
"""Dev-time oracle for tensor fixtures (Python exact arithmetic).

Emits tests/tables/tensor.json and tests/tables/tensor-traps.json.
Strides/ravel/unravel expectations are computed by direct simulation;
the corpus pins the exact residue conventions (zero lanes, -1 broadcast
lanes, input-echo permutation residues).
"""
import json
from pathlib import Path

M63 = 2**63 - 1
MIN64 = -2**63

HOME = "mncs.math.tensor.v1"
EHOME = "mncs.math.error.v1"

CASES = []
TRAPS = []


def I(v):
    return {"i64": v}


def U(v):
    return {"u64": v}


def B(v):
    return {"bool": v}


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


def case(cid, fn, args, expected, budget=4096):
    CASES.append({"id": cid, "fn": fn, "args": args,
                  "expect": expected, "budget": budget})


def AI(*vs):
    return [I(v) for v in vs]


def main():
    global CASES, TRAPS

    # shape_ok
    case("shape-ok-4", "entry_shape_ok",
         AI(2, 3, 4, 5) + [U(4)], [B(True)])
    case("shape-ok-prefix", "entry_shape_ok",
         AI(2, 3, 0, 0) + [U(2)], [B(True)])
    case("shape-zero-dim", "entry_shape_ok",
         AI(2, 0, 4, 5) + [U(4)], [B(False)])
    case("shape-neg-dim", "entry_shape_ok",
         AI(2, -3, 4, 5) + [U(2)], [B(False)])
    case("shape-rank0", "entry_shape_ok",
         AI(0, 0, 0, 0) + [U(0)], [B(True)])
    case("shape-rank-too-big", "entry_shape_ok",
         AI(2, 3, 4, 5) + [U(5)], [B(False)])

    # strides4
    case("strides-4", "entry_strides4", AI(2, 3, 4, 5) + [U(4)],
         [SEQ([60, 20, 5, 1])])
    case("strides-2", "entry_strides4", AI(2, 3, 0, 0) + [U(2)],
         [SEQ([3, 1, 0, 0])])
    case("strides-1", "entry_strides4", AI(7, 0, 0, 0) + [U(1)],
         [SEQ([1, 0, 0, 0])])
    case("strides-0", "entry_strides4", AI(0, 0, 0, 0) + [U(0)],
         [SEQ([0, 0, 0, 0])])

    # numel4
    case("numel-4", "entry_numel4", AI(2, 3, 4, 5) + [U(4)], [ok(120)])
    case("numel-0", "entry_numel4", AI(0, 0, 0, 0) + [U(0)], [ok(1)])
    case("numel-1", "entry_numel4", AI(7, 0, 0, 0) + [U(1)], [ok(7)])
    case("numel-zero-dim", "entry_numel4", AI(2, 0, 4, 5) + [U(4)],
         [err(12)])
    case("numel-neg-dim", "entry_numel4", AI(2, -3, 0, 0) + [U(2)],
         [err(12)])
    case("numel-overflow", "entry_numel4",
         AI(M63, 2, 0, 0) + [U(2)], [err(2)])

    # ravel4
    case("ravel-basic", "entry_ravel4",
         AI(1, 2, 3, 4, 60, 20, 5, 1) + [U(4)], [ok(119)])
    case("ravel-rank0", "entry_ravel4",
         AI(9, 9, 9, 9, 0, 0, 0, 0) + [U(0)], [ok(0)])
    case("ravel-rank2", "entry_ravel4",
         AI(1, 2, 9, 9, 3, 1, 0, 0) + [U(2)], [ok(5)])
    case("ravel-overflow", "entry_ravel4",
         AI(M63, 0, 0, 0, 2, 0, 0, 0) + [U(1)], [err(2)])

    # unravel4
    case("unravel-4", "entry_unravel4", AI(119, 2, 3, 4, 5) + [U(4)],
         [SEQ([1, 2, 3, 4])])
    case("unravel-2", "entry_unravel4", AI(5, 2, 3, 0, 0) + [U(2)],
         [SEQ([1, 2, 0, 0])])
    case("unravel-1", "entry_unravel4", AI(7, 9, 0, 0, 0) + [U(1)],
         [SEQ([7, 0, 0, 0])])
    case("unravel-0", "entry_unravel4", AI(99, 0, 0, 0, 0) + [U(0)],
         [SEQ([0, 0, 0, 0])])
    case("unravel-3", "entry_unravel4", AI(23, 2, 3, 4, 0) + [U(3)],
         [SEQ([1, 2, 3, 0])])

    # perm_valid
    case("perm-ok", "entry_perm_valid", AI(2, 0, 1, 0) + [U(3)],
         [B(True)])
    case("perm-dup", "entry_perm_valid", AI(1, 1, 0, 0) + [U(3)],
         [B(False)])
    case("perm-range", "entry_perm_valid", AI(3, 0, 0, 0) + [U(3)],
         [B(False)])
    case("perm-rank0", "entry_perm_valid", AI(9, 9, 9, 9) + [U(0)],
         [B(True)])
    case("perm-rank-too-big", "entry_perm_valid", AI(0, 1, 2, 3) + [U(5)],
         [B(False)])
    case("perm-neg", "entry_perm_valid", AI(-1, 0, 1, 0) + [U(3)],
         [B(False)])

    # permute_shape
    case("permute-basic", "entry_permute_shape",
         AI(2, 3, 4, 5, 2, 0, 1, 0) + [U(3)], [SEQ([4, 2, 3, 0])])
    case("permute-rev", "entry_permute_shape",
         AI(2, 3, 4, 5, 3, 2, 1, 0) + [U(4)], [SEQ([5, 4, 3, 2])])
    case("permute-invalid-echo", "entry_permute_shape",
         AI(2, 3, 4, 5, 1, 1, 0, 0) + [U(3)], [SEQ([2, 3, 4, 0])])
    case("permute-neg-total", "entry_permute_shape",
         AI(2, 3, 4, 5, -1, 0, 1, 0) + [U(3)], [SEQ([2, 3, 4, 0])])

    # bcast_axis / bcast_ok4 / broadcast4
    case("axis-equal", "entry_bcast_axis", AI(3, 3), [I(3)])
    case("axis-stretch-left", "entry_bcast_axis", AI(1, 5), [I(5)])
    case("axis-stretch-right", "entry_bcast_axis", AI(5, 1), [I(5)])
    case("axis-clash", "entry_bcast_axis", AI(3, 4), [I(-1)])
    case("ok-true", "entry_bcast_ok4", AI(2, 3, 4, 1, 2, 1, 4, 7),
         [B(True)])
    case("ok-false", "entry_bcast_ok4", AI(2, 3, 4, 1, 2, 5, 4, 1),
         [B(False)])
    case("bcast-stretch", "entry_broadcast4",
         AI(2, 3, 0, 0) + [U(2)] + AI(3, 0, 0, 0) + [U(1)],
         [SEQ([1, 1, 2, 3])])
    case("bcast-scalar", "entry_broadcast4",
         AI(2, 3, 0, 0) + [U(2)] + AI(0, 0, 0, 0) + [U(0)],
         [SEQ([1, 1, 2, 3])])
    case("bcast-clash-lane", "entry_broadcast4",
         AI(2, 3, 0, 0) + [U(2)] + AI(5, 0, 0, 0) + [U(1)],
         [SEQ([1, 1, 2, -1])])
    case("bcast-4d", "entry_broadcast4",
         AI(2, 1, 4, 1) + [U(4)] + AI(2, 3, 1, 1) + [U(4)],
         [SEQ([2, 3, 4, 1])])

    table = {"module": HOME, "name": "tensor-index-maps",
             "cases": CASES}
    root = Path(__file__).resolve().parent.parent
    (root / "tests" / "tables" / "tensor.json").write_text(
        json.dumps(table, indent=1) + "\n")
    print("wrote tensor.json (%d cases)" % len(CASES))

    TRAPS = [
        {"id": "unravel-zero-dim",
         "fn": "entry_unravel4",
         "args": AI(5, 2, 3, 0, 4) + [U(4)]},
        {"id": "unravel-zero-dim-rank2",
         "fn": "entry_unravel4",
         "args": AI(5, 2, 0, 0, 0) + [U(2)]},
    ]
    traptable = {"module": HOME, "name": "tensor-traps",
                 "cases": TRAPS}
    (root / "tests" / "tables" / "tensor-traps.json").write_text(
        json.dumps(traptable, indent=1) + "\n")
    print("wrote tensor-traps.json (%d cases)" % len(TRAPS))


if __name__ == "__main__":
    main()
