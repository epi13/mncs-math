# Expected record: C11 backend mistraps plain u64 arithmetic on high-bit operands

## `add-0-0-max`: `direct_add(0, 0, 18446744073709551615)`

- `mncs-research-bytecode`: `returned [u64 0]`, expectation met,
  overall `UNKNOWN` (standing compile obligation with conservative
  fallback; all expectations still met).
- `mncs-llvm-ir`: `returned [u64 0]`, expectation met.
- `mncs-c11`: `runtime_failure`, expectation missed. **This is the bug.**

## `mkrec-max`: `mk_rec(18446744073709551615, 1)`

- All three backends: `returned [u64 0]`, expectation met.
- Control case: u64 record construction, field projection, and wrapping
  `+%` on `u64::MAX` are all fine on C11. Only the checked plain-op
  widening path mistraps.
