# Automatic differentiation: capabilities and boundary

`src/math/autodiff.mncs` implements exact forward-mode AD in two
tiers: `DualZ` over checked `i64` (polynomial derivatives, no
division — integer division is not closed) and `DualQ` over
numerator/denominator pairs with the reducing rational ops (full
quotient rule, canonical by construction). Cubic Horner evaluation
ships on both tiers; `DualQ` observers exist so Newton-style loops
(`numerical.mncs`) can carry dual states.

## Blocked on language changes

- Reverse mode and tapes need heap-allocated dynamic structures and
  closures (**P005**, **P006**).
- Transcendentals (exp/log/sin) need a float type (**P001**); their
  dual rules are otherwise straight-line code of the same shape as
  `dualq_div`.
- Higher-order derivatives (dual-of-dual) need nested records or
  record generics; flat four-lane records were chosen instead.
- Differentiating through control flow (branches, loops) needs
  first-class functions to abstract over (**P006**).
