# RFC 0006 — interval arithmetic semantics

Status: accepted (2026-09-07).

## Decision

Intervals are **closed, validated, and honestly ordered**:

- `Interval { lo: i64, hi: i64 }` (integer tranche; rational tranche mirrors
  it) with constructor validation `lo <= hi`. The empty interval is not a
  value — it is a `MathError::invalid_interval` reason at construction, and
  non-overlapping intersection likewise returns the reason instead of an
  empty inhabitant. (Rationale: an empty-interval value poisons every
  downstream operation silently; a reason forces handling.)
- **Width / midpoint**: `width = hi -| lo` (saturating, documented);
  `midpoint = lo +% (width / 2)` — rounded toward `lo`, documented, never
  overflowing.
- **Arithmetic**: `add/sub` exact; `mul` = min/max of the four products
  with wrapping products… no — checked products: any product overflow
  yields `overflow` reason rather than a wrapped interval (wrapping would
  silently invert containment — the one place this library refuses the
  wrapping default, justified in `docs/interval.md`).
- **Ordering is not scalar ordering**: there is no `<` on intervals.
  Predicates are `certainly_lt` (a.hi < b.lo), `possibly_lt`
  (a.lo < b.hi), `contains_point`, `contains_interval`, `overlaps`.
  Any generic algorithm instantiated over intervals must use these;
  silently deriving `Ord` is listed as a misuse in the docs.
- **Division**: partial — divisor intervals containing zero return
  `div_by_zero`; otherwise min/max of endpoint quotients with i64 division
  truncation documented as inward (honest: containment is then approximate
  and the function name says `div_trunc`, not `div`).
- **Outward rounding**: exact for integer arithmetic by construction;
  rational/fixed tranches document their rounding direction per operation
  (outward where containment is claimed). No containment claim is made that
  the rounding does not support.

## Pressure role

Intervals exercise aggregate validation, NaN-free edge semantics today,
and — once floats exist — outward-rounding control and infinity handling
(→ P001/P007). The API is already shaped for that: rounding-direction
arguments exist in the rational tranche ahead of the hardware that needs
them.
