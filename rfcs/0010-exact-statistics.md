# RFC 0010 — exact descriptive statistics model

Status: accepted (2026-09-08).

## Decision

Moments are exact: count/sum/min/max/sort over `i64`, mean/variance/
median as reduced fractions through `rational.make`. The variance is
the population form `(8*S2 − S1^2)/64`, nonnegative by construction;
a negative numerator would signal an implementation bug. Overflow
anywhere in the accumulation chain is an honest `Err`, never a
wrapped accumulator.

- `sum8`/`sumsq8` checked folds; `min8`/`max8` total selections;
  `range8` checked difference.
- `mean_var8` chains five match-splits from sums to reduced pairs.
- `median8` is the exact mean of the two middle order statistics of
  `sort8`, itself a 19-comparator Bose-Nelson network proved by brute
  force over all 40320 permutations at fixture-generation time.
- Sample variance (Bessel) and higher moments are one more rational
  op each; omitted as scope, unblocked.

## Composition

`examples/ex_sample` feeds shuffled decks straight into
`median8`/`mean_var8`, pinning shuffle-invariance of the moments and
seed-dependence of `argmin8` on both backends. Future streaming
moments (Welford) need the same observer discipline as `bisect8`;
nothing in this design blocks them.
