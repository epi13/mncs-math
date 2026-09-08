# repro: f64 array handling miscompiles on every native backend

- Toolchain: mncs-language @ `6a29332` (binary sha256
  `aaf20d37...`, profile 0.12).
- Scope: `mncs-c11`, `mncs-cranelift`, and `mncs-llvm-ir` all wrong;
  `mncs-research-bytecode` and `mncs-portable-wasm-mvp` return the
  correct values.

## Exact command

```bash
export MNCS_LIBRARY_PATH="$PWD/src:<mncs-language>/library"
mncs experiment run repro/native-f64-array-param/case.mncs \
  --backend <backend> --corpus repro/native-f64-array-param/corpus.json
```

## Actual behavior

Cases `f2` (`entry_f2(1.0, 2.0)`, expected `3.0`) and `f4`
(`entry_f4(1.0, 2.0, 3.0, 4.0)`, expected `10.0`) pass a freshly built
`[f64; N]` array literal to a callee that reduces it with `iterate`.
Control case `i8` (same shape over `[i64; 8]`, expected `360`) passes
everywhere.

- `mncs-c11`: `returned` garbage — `f2` yields `4.613937818241073e+18`,
  `f4` yields `4.621819117588972e+18`. Overall `FAIL`.
- `mncs-cranelift`: `returned` `0.0` (bits `0`) for both `f2` and `f4`.
  Overall `FAIL`.
- `entry_loop` (same-file control: a *local* `[f64; 6]` reduced by
  `iterate`, no call boundary): the discriminating vector
  (`loop6`, expected `3.0`) returns `8589934595.0` (= 2^33 + 3) on
  C11 and a denormal `1.852666552e-314` on Cranelift, while the
  `[1..6]` control (`loop6ctl`, expected `21.0`) passes on C11 and
  returns `0.0` on Cranelift. So the lowering fault is not confined
  to call boundaries: C11 miscompiles value-dependently (small
  integers survive, large magnitudes do not), Cranelift drops the
  accumulation entirely.
- `mncs-llvm-ir`: the whole module is rejected by clang, so even the
  healthy `i8` control reports `unsupported`:
  `module.ll:87:20: error: invalid cast opcode for cast from 'i64' to
  'double'` (`%call5_v = trunc i64 %call5_raw to double`). One bad
  f64-lowering poisons every entry in the module, including
  pure-integer ones. Overall `FAIL`.
- `mncs-research-bytecode`, `mncs-portable-wasm-mvp`: all five cases
  `returned` with expectations met. Overall `UNKNOWN` (standing
  compile obligation with conservative fallback).

## Desired semantics

Passing an `[f64; N]` array by value must deliver its elements to the
callee on every backend, as it already does for `[i64; N]` — and
reducing a local `[f64; N]` with `iterate` must accumulate exactly,
as it does on bytecode/wasm.

## Discrimination performed (not part of the repro files)

- 2/4/6/8 scalar `f64` parameters sum correctly on C11: not a
  calling-convention arity limit.
- A callee-free local `[f64; 8]` of small integers reduced in the
  entry works on C11, but the same shape over large magnitudes
  (`loop6`) does not: not array construction as such — the fault
  is value-dependent on C11 and total on Cranelift.
- Monomorphic two-`[f64; 8]`-parameter dot and generic single-array
  sum both fail: not generics, not parameter count.
- `[i64; 8]` by value works on C11 and Cranelift: the trigger is the
  `f64` element type of a by-value array parameter, at every tested
  length (2, 4, 8).

## Affected math workloads

`float.mncs` `entry_fdot4` (`dot4-generic`: expected `12.25`, C11
returns `4.755801206509535e+18`) routes through the generic
`fdot_arr<4>([f64; 4], [f64; 4])`, and `candidate_fsum_loop`
(`sum6-loop`: expected `3.0`) reduces a local array with `iterate`.
Any past or future kernel that moves float arrays — across a call
boundary or inside a loop — is silently wrong on natives,
including 50/50 `float` corpus cases on `mncs-llvm-ir`.
