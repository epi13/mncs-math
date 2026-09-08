# Runnable examples

`examples/` contains end-to-end programs that compose modules in ways
the per-module corpora do not. Each has a frozen corpus under
`examples/corpora/` and runs via `scripts/examples.sh` on both
backends. Regenerate corpora with `python3 tools/gen_examples.py`
(values are cross-checked at generation; see the script).

## ex_solve — solve with a machine-checked residual

`entry_ex_solve3` solves a 3x3 system by Cramer (`linalg`) and then
proves the answer: for unimodular `A` (det ±1) the coordinates are
integers, and the residual `r = A·x − b` is recomputed with checked
ops. The pinned case solves

```
A = [[1,2,3],[0,1,4],[5,6,0]], b = (1,2,3)
```

to `x = (27,-22,6)` with residual `(0,0,0)`. Non-unit denominators
fail with `domain` instead of truncating; singular systems propagate
the solver's `singular`.

## ex_sample — reproducible sampling into exact statistics

`entry_ex_median` / `entry_ex_mean_var` / `entry_ex_argmin` shuffle
`[1..8]` with splitmix64 (`deterministic`) and feed the deck straight
into the exact moments (`statistics`, `optimize`). Pinned at seed
2026: median `9/2` and moments `(9/2, 21/4)` are shuffle-invariant
for a full deck, while the argmin index (`2`) pins the stream itself.
Identical values on both backends are the cross-backend determinism
receipt.
