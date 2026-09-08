# RFC 0008 — exact linear algebra model

Status: accepted (2026-09-08).

## Decision

Linear solving is **exact or it is an error**: determinants, Cramer
coordinates, ranks, substitution results, and LU factors are integers
or canonical rationals, never approximations.

- `det2` closed form, `det3` checked Sarrus, `det4` Bareiss
  fraction-free elimination with first-nonzero-row pivoting, sign
  tracking, and a singularity flag. Bareiss intermediates are exact
  subdeterminants, so every division is exact by construction; the
  implementation still proves exactness (`num % prev == 0`) before
  dividing.
- `solve2/3/4` by Cramer over exact determinants with coordinates
  canonicalized through `rational.make`. The inverse is never the
  solver; `inv2` (adjugate) is supplementary and documented as such.
- `rank3` by 2x2 minors; `rank4` by Bareiss elimination with full
  row+column pivoting (required: rank-2 4x4 matrices exist whose only
  nonzero 2x2 minor is non-contiguous).
- `lu3` with first-nonzero-row pivoting, explicit permutation vector,
  and a final-pivot singularity check; `lu_solve3` composes
  permute/forward/backward and is cross-checked against Cramer on the
  same inputs.
- Norms are the true induced 1/infinity norms (max column/row sums),
  the entrywise max norm, and squared Frobenius — all checked. An
  earlier draft summed all entries for `norm1`; it was corrected
  before freezing because a mislabeled norm is a correctness lie.

## Composition

Solvers feed `examples/ex_solve` (residual-checked unimodular solve).
Substitution factors feed `lu_solve3`. Norms will feed convergence
tests once iterative methods exist (→ P001, P007).

## Scaling rule

One hand-written kernel per size (no const-generics, → P005). 5x5+
follows the `det4`/`rank4` pattern. Float LU/QR/Cholesky/eigen need a
float type (→ P001), not a redesign: pivoting, factor tracking, and
the status/validity split transfer unchanged.
