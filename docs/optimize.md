# Optimization: capabilities and boundary

`src/math/optimize.mncs` implements 8 fixed ternary narrowings for
convex cubics (exact `cmp` on thirds; the kept third provably contains
the minimizer of a convex target) and exact lattice extrema
(`argmin8`/`argmax8`, first index wins ties).

## Blocked on language changes

- Golden-section and gradient/coordinate descent with tolerances need
  floats and data-dependent convergence loops (**P001**, **P007**).
- Objective functions as values (closures) would generalize
  `ternary8` beyond cubic coefficients (**P006**).
- Constrained and combinatorial optimization (simplex, branch and
  bound) needs the float stack plus heap structures (**P001**,
  **P005**).
