# RFC 0009 — exact numerical methods and optimization model

Status: accepted (2026-09-08).

## Decision

Keep the algorithms, drop the rounding: bisection, Newton, Simpson,
Euler, ternary narrowing, and lattice extrema run on canonical
rationals with fixed iteration counts, so results are exact
fractions, not tolerances.

- `bisect8`: bracket validated first (endpoint roots collapse,
  same-sign starts fail `domain`); 8 halvings; midpoint code folds
  through observers so loops never match.
- `newton3`: 3 unrolled steps on the dual pair from `autodiff`. The
  update subtracts from the **iterate**, not from `f(x)` — a real bug
  of exactly this shape was caught during this run and is pinned by
  the hand-verified 577/408 chain.
- `simpson_cubic`: 2 subintervals integrate cubics bit-exactly; the
  corpus pins reduced fractions (30, 1/3, 0).
- `euler1`: one exact linear step `y + h*(p*y + q)`; callers iterate.
- `ternary8`: 8 narrowings for convex targets (documented contract);
  final width is exactly `(2/3)^8` of the start, pinned.
- `argmin8`/`argmax8`: first extremal index wins (deterministic).

## Composition

Newton consumes `DualQ` observers; bisection/ternary/Simpson share
the dual-evaluator value lanes (`poly_value` seeds zero tangent).
`no_convergence` (reason 6) is reserved for the future adaptive
driver, which reports it instead of silently returning a stale
iterate.

## Blocked, not deferred

Adaptive quadrature, tolerance Newton, golden-section, and gradient
descent need floats plus data-dependent exit (→ P001, P007).
Nonlinear targets need callable values (→ P006). The fixed-count
drivers here become the inner steps of those drivers, not throwaway
prototypes.
