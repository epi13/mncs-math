# Generics gap: measured per-size copy costs (P005)

MNCS has no const-generics, no dimension arithmetic (`[i64; N - 1]`
is MNP149), and no traits. Every size is a hand-written kernel.
This note measures what that costs on the three size ladders in the
tree, so the later language run can price const-generics against
evidence instead of anecdotes.

## Linear algebra: 2x2 → 6x6

Entry arities grow exactly as `n^2` scalar parameters (no slice or
array-value affordance at the entry boundary): det4 takes 16,
det5 takes 25, det6 takes 36.

Source cost per kernel family (comment + blank lines included,
measured with `grep -n '^// ----'` section spans):

| Kernel | Section lines | Lanes |
| ------ | ------------- | ----- |
| det4 Bareiss (`linalg.mncs`) | ~143 | 16 |
| det5 Bareiss (`linalg5.mncs`) | ~119 | 25 |
| det6 Bareiss (`linalg5.mncs`) | ~130 | 36 |
| rank4 full-pivot (`linalg.mncs`) | ~69 | 16 |
| rank5 full-pivot (`linalg5.mncs`) | ~76 | 25 |
| rank6 full-pivot (`linalg5.mncs`) | ~81 | 36 |
| Cramer solve5 + resid (`linalg5.mncs`) | ~140 | 25 + 5 |
| Cramer solvers (`linalg.mncs`, 2/3/4x4) | ~203 | shared |

Read: each new size duplicates every kernel at ~120-140 lines for
determinants and ~70-80 for rank, plus its entry wrapper and corpus
cases — the 5x5 stack (det+rank+solve) is ~335 lines, the 6x6 stack
(det+rank, no solve) ~211. Step-count scaling for the same ladder
(det4-generic → det5-generic → det6-generic, solve4 → solve5) is
tabulated in `docs/performance.md`; budgets follow the same curve
(det cases at 4M, rank/solve at 8M, against the 8M runner ceiling
that already rules out a Cramer-6x6 copy).

What a const-generic dimension would collapse: the three Bareiss
ports differ only in lane count, literal bounds (`up_to 5` vs
`up_to 6`), and the `/5`/`%5` vs `/6`/`%6` index ladders; the three
rank ports differ only in the same three places plus the trailing
cell (`m[24]` vs `m[35]`). One `[i64; N*N]` Bareiss kernel deletes
~390 port lines (143 + 119 + 130) and one generic rank kernel
deletes ~230 more (69 + 76 + 81), plus three corpus-table stanzas.

## Sorting and tensor kernels

- The 8-sorter (`statistics.mncs`) is an explicit 19-comparator
  Bose–Nelson network: 19 `stage8` lines plus the oracle's
  generation-time proof over all 40320 permutations. A 16-sorter
  would be an ~80-comparator second copy; a generic network needs
  const-generic lengths or closures over comparators (P005/P006).
- `tdata.mncs` kernels (transpose4, contract232, bmm2, conv_valid83,
  gather_stride4) repeat one shape per (rank, dtype, window): each is
  15-40 lines of lane arithmetic plus entry plus oracle stanza.
  Rank-generic contraction or a strided-view type would collapse all
  five movement kernels into instances.

## Dual-number tiers

`DualZ`/`DualQ` are separate hand-written tiers over Z/Q (no traits
to abstract the ring), and the Halley second derivative is a second
full evaluation plus cross-check ladder because dual-of-dual needs
nested records. See `docs/autodiff.md`.

## Bottom line for the language run

The tree carries over six hundred counted lines of size copies
(~390 Bareiss + ~230 rank) plus the tier copies (`DualZ`/`DualQ`),
the 19-comparator sort network, and five single-shape data kernels.
Const-generic array dimensions subsume the largest share; traits
subsume the tier copies; nested records subsume the dual-of-dual
ladder. None is speculative: each maps to counted lines above.
