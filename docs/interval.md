# Interval arithmetic: capabilities and boundary

`src/math/interval.mncs` implements exact intervals over `i64`
endpoints: add/sub/mul/div, negation, width, containment,
intersection (+disjointness observer), and hull.

## Why integers are enough here

Every endpoint operation is exact, so outward rounding is automatic
and containment is a theorem. The division guard (zero-containment
test through total sign tests before any quotient evaluates) is the
whole soundness story, and the corpus pins it including the
`MIN / -1` quotient guard.

## Blocked on language changes

- Float intervals with directed rounding need a float type with
  rounding-mode control (**P001**).
- Decorations (validity flags per interval, e.g. IEEE 1788) would fit
  today's records; omitted as scope, not blocked.
- Empty intervals are a caller contract (`iv_ok`); a first-class empty
  value would need either sum-type payloads in records or wider enums
  — expressible today, deferred for API stability.
