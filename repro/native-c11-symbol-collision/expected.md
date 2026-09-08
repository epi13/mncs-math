# Expected record: C11 symbol collision on `trunc`

## `t`: `trunc(5)`

- `mncs-research-bytecode`: overall `PASS`, `returned [i64 5]`.
- `mncs-llvm-ir`: `returned [i64 5]`, expectation met.
- `mncs-c11`: overall `FAIL`, case `unsupported`, clang
  `conflicting types for 'trunc'`. **Bug.**
- `mncs-portable-wasm-mvp`, `mncs-cranelift`: untested for this case
  at the time of writing; fill in with the backend matrix.
