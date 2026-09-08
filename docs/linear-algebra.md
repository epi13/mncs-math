# Linear algebra: capabilities and boundary

`src/math/linalg.mncs` implements exact linear algebra over integers
(determinants, ranks, norms) and rationals (solvers, substitution, LU).
`src/math/linalg5.mncs` extends the same Bareiss architecture to 5x5
(determinants, full-pivot rank, Cramer solve with integer-residual
check) and 6x6 (determinants, full-pivot rank); per-size copy costs
are measured in `docs/generics.md`.

## Provided

- `det2` (closed form), `det3` (Sarrus, checked), `det4` (Bareiss with
  first-nonzero-row pivoting, sign tracking, singularity flag).
- `solve2/3/4` by Cramer over exact determinants, coordinates
  canonicalized through `rational.make`. The inverse is never the
  solver; `inv2` (adjugate) exists as a supplementary entry only.
- `rank3` by 2x2 minors; `rank4` by Bareiss elimination with full
  (row+column) pivoting — required because rank-2 4x4 matrices exist
  whose nonzero 2x2 minor is non-contiguous.
- `sub_fwd3`/`sub_bwd3` over paired numerator/denominator arrays with
  fractional right-hand sides.
- `lu3` with first-nonzero-row pivoting, permutation tracking, and a
  final-pivot singularity check; `lu_solve3` composes
  permute-forward-backward and is cross-checked against Cramer.
- Induced 1/infinity norms (true max column/row sums, not entrywise
  sums), entrywise max norm, and squared Frobenius norm — all checked.

## Blocked on language changes

- Float LU/QR/Cholesky/eigen and condition estimation need a float
  type with division/sqrt semantics (**P001**).
- 5x5/6x6 elimination shipped as longer unrolled step chains,
  confirming the predicted quadratic copy cost (**P005**,
  `docs/generics.md`); 7x7+ and NxN need const-generic dimensions,
  and 6x6 ships no Cramer solve (seven 6x6 determinants against the
  8M step-budget ceiling).
- Iterative refinement and Krylov methods need tolerance-driven loops
  with data-dependent exit plus float arithmetic (**P001**, **P007**).
