# Automatic differentiation: capabilities and boundary

`src/math/autodiff.mncs` implements exact forward-mode AD in two
tiers: `DualZ` over checked `i64` (polynomial derivatives, no
division — integer division is not closed) and `DualQ` over
numerator/denominator pairs with the reducing rational ops (full
quotient rule, canonical by construction). Cubic Horner evaluation
ships on both tiers; `DualQ` observers exist so Newton-style loops
(`numerical.mncs`) can carry dual states.

Second-order information ships without nested duals: one exact
Halley step for the fixed cubic `c(x) = x^3 - 2x - 5` at a rational
start (`entry_halley`), where `f`/`f'` come from `dualq_poly3` over
`c` and `f''` is the tangent of `dualq_poly3` over
`c' = 3x^2 - 2` at the same dual point. The two `f'` lanes
(c-eval tangent, c'-eval value) are cross-checked for equality
inside the step — any divergence between the evaluations changes
the observation. The residual `f(x1)` rides along, so each corpus
case checks the step and the cubic contraction together
(`|f(x1)| < |f(t)|^2` is asserted by the oracle). A zero Halley
denominator surfaces as a div-by-zero `Err`, never a trap; the
corpus pins `Err` paths for zero-denominator starts and overflowing
starts alongside exact `111/53`, `1043/481`, `-15/11` steps.
`entry_d2cubic` spot-checks the `f'' = 6x` lane the step consumes.

## Blocked on language changes

- Reverse mode and tapes need heap-allocated dynamic structures and
  closures (**P005**, **P006**).
- Transcendental dual rules for exp/log need a float
  exp/log/sqrt tier (**P001**, remaining after Stage C1/C2); sin/cos
  dual rules are straight-line code of the same shape as
  `dualq_div` now that `float.mncs` ships host-libm sin/cos.
- Higher-order derivatives by dual-of-dual composition need nested
  records or record generics; the Halley step shows the current
  ceiling is "one second derivative per extra full evaluation",
  with the cross-check ladder as the price (**P005**).
- Differentiating through control flow (branches, loops) needs
  first-class functions to abstract over (**P006**).
