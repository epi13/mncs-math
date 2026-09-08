# Numerical algorithms: capabilities and boundary

`src/math/numerical.mncs` implements bisection (8 fixed halvings over
a validated bracket), 3 unrolled Newton steps on the dual pair,
bit-exact Simpson quadrature for cubics, and an exact Euler step for
linear ODEs — all over canonical rationals, all failures as enums.

## Exactness notes

- Simpson with 2 subintervals integrates cubics exactly, so the
  corpus pins reduced fractions (30, 1/3, 0), not tolerances.
- Bisection validates the bracket first (endpoint roots collapse,
  same-sign starts fail with `domain`); midpoint code folds through
  observers so loops never match.
- Newton threads the iterate separately from the dual pair after a
  real bug was caught in review: the update subtracts from `x`, not
  from `f(x)` (see the module history; the oracle's independent
  577/408 chain pins it).

## Blocked on language changes

- Adaptive quadrature and tolerance-driven Newton need
  data-dependent loop exit plus floats (**P001**, **P007**).
- Nonlinear (non-polynomial) targets need callable values (**P006**);
  RK4 and higher Euler variants are straight-line extensions once
  those exist.
- Stiff solvers and implicit steps need the float linear algebra of
  `linear-algebra.md`.
