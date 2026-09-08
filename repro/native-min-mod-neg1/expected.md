# Expected record: native backends crash on `i64::MIN % -1`

## `min-mod-neg1`: `min_mod_neg1(-9223372036854775808, -1)`

- `mncs-research-bytecode`: `returned [i64 0]`, expectation met,
  overall `UNKNOWN` (standing `body:integer-overflow` obligation;
  see README).
- `mncs-portable-wasm-mvp`: `returned [i64 0]`, expectation met
  (full-corpus baseline behavior; rerun here if challenging).
- `mncs-c11`: `invalid_request`, no observation. **Bug.**
- `mncs-llvm-ir`: `invalid_request`, no observation. **Bug.**
- `mncs-cranelift`: untested for this case at the time of writing;
  fill in when the backend matrix is run.
