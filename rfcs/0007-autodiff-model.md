# RFC 0007 — automatic differentiation model

Status: accepted (2026-09-07).

## Decision

Start with **forward-mode dual numbers**; architect so reverse mode can
land later without breaking the forward API.

- `Dual { x: i64, dx: i64 }` over exact scalars and `DualFx` over
  fixed-point: `d(a+b) = da+db`, `d(a*b) = a*db + b*da` (computed in the
  widened/managed discipline of the underlying tier — exact tier uses the
  `mul_div`-safe ordering, fixed tier rounds once, documented).
- Division: quotient rule with explicit zero-derivative-of-denominator
  handling; zero primal denominator → `div_by_zero` reason (not NaN —
  there is no NaN in these tiers).
- Elementary functions over fixed-point: Taylor/Horner polynomials with
  frozen term counts (`exp_taylor8`, `ln_pade` groundwork, `sin_taylor7`)
  — each is a pure bounded traversal, so derivative propagation through
  them is exact structural chain rule, tested against analytic derivatives
  at frozen points.
- `grad(f, x)` convention: seed `dx = ONE`, read `.dx` of the result.
  Multivariate gradients are `N` forward passes over basis seeds
  (documented O(N) cost, the honest forward-mode price).
- **Reverse-mode hook (not implemented)**: every forward primitive records
  its rule in `docs/autodiff.md` in pullback form
  (`pullback_mul(upstream, a, b) -> (up_a, up_b)`) as prose + fixed-point
  reference values, so the later tape/VJP tranche implements against
  frozen expectations. No tape type is declared until closures or
  growable buffers exist (→ P005/P008).

## Composition

Dual numbers compose with `optimize` (Newton uses analytic dual
derivatives, secant does not) and with `numerical` (finite differences
validate dual derivatives in corpora — two independent implementations of
the same derivative must agree within the frozen tolerance).

## Blocked by floats, not by design

Float duals are the same struct with float fields; every rule transfers
unchanged. The integer/fixed tranche proves the propagation machinery so
the float tranche is a widening, not a redesign.
