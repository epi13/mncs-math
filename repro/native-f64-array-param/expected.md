# Expected record: f64 array value parameters on native backends

## `i8`: `entry_i8(10, 20, 30, 40, 50, 60, 70, 80)`, expected `360`

- `mncs-research-bytecode`: `returned [360]`, expectation met.
- `mncs-portable-wasm-mvp`: `returned [360]`, expectation met.
- `mncs-c11`: `returned [360]`, expectation met.
- `mncs-cranelift`: `returned [360]`, expectation met.
- `mncs-llvm-ir`: `unsupported` (module-wide clang failure below
  poisons this healthy entry too).

## `f4`: `entry_f4(1.0, 2.0, 3.0, 4.0)`, expected `10.0`

- `mncs-research-bytecode`: `returned [10.0]`, expectation met.
- `mncs-portable-wasm-mvp`: `returned [10.0]`, expectation met.
- `mncs-c11`: `returned [4.621819117588972e+18]`, expectation missed.
  **Bug.**
- `mncs-cranelift`: `returned [0.0]`, expectation missed. **Bug.**
- `mncs-llvm-ir`: `unsupported`, `compiler failure: clang failed:
  module.ll:87:20: error: invalid cast opcode for cast from 'i64' to
  'double'`. **Bug.**

## `f2`: `entry_f2(1.0, 2.0)`, expected `3.0`

- `mncs-research-bytecode`: `returned [3.0]`, expectation met.
- `mncs-portable-wasm-mvp`: `returned [3.0]`, expectation met.
- `mncs-c11`: `returned [4.613937818241073e+18]`, expectation missed.
  **Bug.**
- `mncs-cranelift`: `returned [0.0]`, expectation missed. **Bug.**
- `mncs-llvm-ir`: `unsupported` (same module-wide clang failure).
  **Bug.**

## `loop6`: `entry_loop(1e16, 1e16, -1e16, 2.0, -1e16, 1.0)`, expected `3.0`

- `mncs-research-bytecode`: `returned [3.0]`, expectation met.
- `mncs-portable-wasm-mvp`: `returned [3.0]`, expectation met.
- `mncs-c11`: `returned [8589934595.0]`, expectation missed.
  **Bug** (no call boundary involved).
- `mncs-cranelift`: `returned [1.852666552e-314]`, expectation
  missed. **Bug.**
- `mncs-llvm-ir`: `unsupported` (same module-wide clang failure).
  **Bug.**

## `loop6ctl`: `entry_loop(1.0, ..., 6.0)`, expected `21.0`

- `mncs-research-bytecode`: `returned [21.0]`, expectation met.
- `mncs-portable-wasm-mvp`: `returned [21.0]`, expectation met.
- `mncs-c11`: `returned [21.0]`, expectation met (small integers
  survive the same fault that corrupts `loop6`).
- `mncs-cranelift`: `returned [0.0]`, expectation missed. **Bug.**
- `mncs-llvm-ir`: `unsupported` (same module-wide clang failure).
  **Bug.**
