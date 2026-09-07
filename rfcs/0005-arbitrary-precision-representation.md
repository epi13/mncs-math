# RFC 0005 — arbitrary precision representation

Status: accepted (2026-09-07).

## Decision

Big integers are **limb sequences**, little-endian, base 2⁶⁴:

- `UBig = [u64; N]`, `Big = { negative: bool, limbs: [u64; N] }`
  (sign-magnitude; zero is always non-negative — canonical).
- `N ≤ 8` (512 bits) this run: every kernel is verified at N = 2 and N = 8
  with traversal-only loops, so the bound is a ceiling, not a design limit.
- **Normalization**: no excess high zero limbs (`normalize` strips them;
  all constructors normalize; equality is limb-wise after normalization —
  no aliasing of values).
- **Carry discipline**: add/sub thread explicit carry/borrow words through
  helper calls (`adc_limb`, `sbb_limb`); no `u128` intermediate exists in
  the language, so double-word arithmetic is spelled as hi/lo comparisons
  (→ P006 documents the missing wide type, worked around exactly).
- **Multiplication**: schoolbook O(n²) via the partition-style
  quotient/remainder fold — the full `a*b` product is never materialized
  outside the accumulator limbs; each inner step is provably in-range.
- **Division**: restoring division, one bit per outer step, outer loop as a
  traversal over a 64-entry index table with limb helpers per step
  (shift/compare/subtract). Total: divisor zero returns `div_by_zero`.
- **Shifts**: limb + bit decomposition (`shl_bits`/`shr_bits`), counts
  modulo the width, logical for unsigned, arithmetic-helper for signed via
  sign-magnitude (no two's-complement smearing bugs possible by
  construction).
- **Conversion**: `from_i64`/`to_i64_checked` (range-checked, fallible
  enum), `to_u64_saturating`, decimal conversion deferred (needs host
  string emission which does not exist → roadmap, not pressure).

## Why sign-magnitude, not two's complement

Two's complement needs width-parameterized negation and sign extension;
sign-magnitude keeps every limb unsigned and total, matches the
`mul_div` fold idiom already proven in `mncs.core.partition.v1`, and makes
mixed-sign add/sub branchless-selectable. Cost: negation is trivial, but
comparisons need a sign check first — documented in `docs/bigint.md`.

## No external bignum

Wrapping a host big-integer facility would hide exactly the carry/borrow/
normalization behavior this substrate exists to pin down. Rejected.
