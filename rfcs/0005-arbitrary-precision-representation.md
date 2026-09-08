# RFC 0005 — arbitrary precision representation

Status: accepted, revised 2026-09-07 (two's complement; see history note).

## Decision

Big integers are **limb sequences**, little-endian, base 2⁶⁴, stored as
`[i64; N]` (i64 by storage — body validation refuses traversal over u64
sequences, MNB101 — u64 by value via `as` reinterpretation at each
arithmetic site).

- Widths are **concrete**: N = 2 (u128) and N = 8 (u512). Multi-value loop
  state (result + carry, remainder + quotient) travels in records with
  concrete sequence fields; generic `[i64; N]` records do not exist in
  Profile 0.10 (→ P006). Generic-N coverage returns when the language
  gains generic records.
- **Signed integers are two's complement** over the same limbs, so every
  unsigned kernel (add/sub/mul/shift) is shared bit-exactly; signed twins
  are thin `neg`/`scmp`/`sdivmod` layers. Most-negative operands fail
  `sdivmod` with overflow (unrepresentable magnitudes).
- **Carry discipline**: add/sub thread explicit carry/borrow words in
  carried records; the 64x64→128 wide product is synthesized from four
  exact 32-bit partial products (no wider type exists — same workaround
  P006 anticipated, implemented exactly and tested).
- **Multiplication**: schoolbook O(n²) rows with unrolled block chaining;
  each row's final carry folds into its landing column with a wrapping add
  that is exact because true column values always fit u64.
- **Division**: restoring division, one 64-step block per limb position,
  blocks chained as sequential helper calls (8 for u512, 2 for u128).
  Total: divisor zero returns `div_by_zero`.
- **Shifts**: single-bit `shl1`/`shr1` across all limbs (shr threads an
  explicit down-counter since borrows flow against traversal order).
- **Conversion**: `from_i64` (sign extension), `to_i64_checked`
  (range-checked, fallible enum), `fits_u64`, `bitlen`/`clz64`; decimal
  conversion deferred (needs host string emission which does not exist →
  roadmap, not pressure).

## Revision history

The original version of this RFC specified sign-magnitude. Implementation
evidence reversed that call: sign-magnitude duplicates every kernel with
sign threading, while two's complement reuses the unsigned kernels
bit-exactly and needs only `neg`/`scmp`/sign-guarded division on top.
The `scmp` implementation itself caught a real sign bug during testing
(two's complement preserves order within each half, so the both-negative
branch compares directly rather than swapping arguments).

## No external bignum

Wrapping a host big-integer facility would hide exactly the carry/borrow/
normalization behavior this substrate exists to pin down. Rejected.
