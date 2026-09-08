# Error model

Every fallible operation in `mncs-math` reports through a payload enum
carrying a numeric **reason code** (`src/math/error.mncs`). Codes are
stable across modules: each module declares its own result enum shaped
for its payload, but the reason numbers never change meaning.

## Codes

| Code | Name | Meaning |
| ---- | ---- | ------- |
| 0 | ok | No error (the `Ok` arm of observers) |
| 1 | div_by_zero | Zero divisor, zero pivot reciprocal, or interval divisor containing zero |
| 2 | overflow | A checked integer op exceeded `i64` (or `u64` where noted) |
| 3 | invalid_interval | Reserved for empty-interval inputs (currently a caller contract; see below) |
| 4 | singular | Zero determinant / zero pivot / zero final LU pivot |
| 5 | shape_mismatch | Caller permutation or shape outside its domain |
| 6 | no_convergence | Reserved for iterative solvers that exhaust fixed steps without meeting tolerance |
| 7 | invalid_tolerance | Reserved for tolerance-driven drivers |
| 8 | index_out_of_bounds | Reserved: computed projections trap instead (see below) |
| 9 | broadcast_incompatible | Reserved: broadcast reports residue lanes instead (see below) |
| 10 | unsupported | Deliberately unimplemented operation reached |
| 11 | precision_exhausted | Reserved for fixed-precision exhaustion |
| 12 | invalid_dimensions | Non-positive extents (shapes, element counts) |
| 13 | domain | Mathematically undefined input (unbracketed start, zero derivative, non-unit solution denominators) |
| 14 | empty | Reserved for empty-collection inputs |

Reserved codes exist so future modules do not renumber history.

## Four failure classes

1. **Enum errors** (the common case): overflow, singularity, domain
   violations, and bad dimensions return as data inside the module's
   outcome enum. Callers match; loops fold sticky codes.
2. **Traps** (`runtime_failure`): integer `/`/`%` by zero, `MIN / -1`,
   checked-op overflow, and out-of-bounds computed projections. Code is
   structured so traps are unreachable on contracted inputs; the
   `*-traps` corpora pin the trap behavior itself (division by zero,
   zero-dim unravel, OOB projection).
3. **Residues**: where an enum cannot fit (array-returning entries),
   invalid outputs are documented residue (zero lanes, `-1` broadcast
   lanes, input-echo shapes) guarded by a companion validity entry
   (`perm_valid`, `bcast_ok4`, `lu_status3`). Residues are never
   presented as results.
4. **Contracts**: positivity of denominators and interval/shape
   validity are caller contracts, documented per function and pinned
   by observer entries (`shape_ok`, `iv_ok`, `lu_perm_ok`).

## Conventions

- Overflow is always reported, never wrapped, on value paths. Wrapping
  operators (`+%`, `-%`, `*%`) appear only with a proof comment that no
  wrap can occur (Lemire limbs, Bareiss trial values) or where function
  is total-by-construction (strides under the numel-Ok contract).
- First failure wins: combined codes keep the earliest error in
  evaluation order (`lu_combine`, `bisect_combine`, `ternary_combine`).
- Observers (`frac_code`, `dualq_code`, `reason_of`) map outcomes to
  `i64` so loops can carry errors as data; residues are trap-free by
  construction (denominator residue is `1`, never `0`).
