# Expected record: `iterate over [u64; N]` domain (MNB101)

## `usum`: `entry_usum(5, 15, 25, 35)`, expected `80`

- `mncs-research-bytecode`: compile rejected before execution —
  `MNB101 ... sequence traversal domain must name a resolvable
  element type`. No cases run.
- `mncs-portable-wasm-mvp`, `mncs-c11`, `mncs-llvm-ir`,
  `mncs-cranelift`: same front-end rejection (verified
  `mncs-research-bytecode`; the diagnostic fires before any
  backend lowering, so backend choice cannot change the outcome).

## Controls (same shape, different element type — accepted)

- `[i64; 8]` parameter with `iterate i over a`: accepted; `sparse`
  corpus green on all backends that compile it (`sparse` C11:
  `UNKNOWN`, all expectations met).
- `[f64; N]` parameter with `iterate i over a`: accepted; `float`
  corpus green on `mncs-research-bytecode` and
  `mncs-portable-wasm-mvp`.
