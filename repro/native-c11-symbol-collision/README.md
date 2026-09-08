# repro: C11 backend emits unprefixed C symbols that collide with libm

- Toolchain: mncs-language @ `26778de`. Profile 0.10.
- Backend: `mncs-c11` fails at C compile time;
  `mncs-research-bytecode` and `mncs-llvm-ir` pass.

## Exact command

```bash
$MNCS_BIN experiment run case.mncs --backend mncs-c11 --corpus corpus.json
```

## Actual behavior

Case `t` (`trunc(5)`, expected `5`):

- `mncs-c11`: overall `FAIL`, case `unsupported`,
  `failure_reason: "compiler failure: clang failed: module.c:7:6:
  error: conflicting types for 'trunc'"`. The emitter lowers the MNCS
  function to a global C `void trunc(...)`, colliding with libm
  `trunc()` from `<math.h>` (linked with `-lm` since Stage C1).
- `mncs-research-bytecode`: `PASS`, `returned`. `mncs-llvm-ir`:
  `returned`, expectation met.

## Desired semantics

Emitted C symbols must be namespaced (e.g. the `mncs_` prefix the
driver already uses for `mncs_main`), or collisions diagnosed at
elaboration with the offending name. Any MNCS function whose name
matches a libc/libm global (`trunc`, and by the same mechanism
plausibly `exp`, `log`, `round`, `index`, ...) silently bricks the
whole module on C11.

## Affected math workloads

`rational.mncs:328` defines `fn trunc(a: Frac) -> i64`. Everything
that transitively links rational — `linalg`, `numerical`,
`ex_solve`, most of the library — cannot execute on `mncs-c11` at
all. First observed as `RUNNER_ERROR example ex_solve @ mncs-c11`
in the conformance smoke run.

## Workaround in use

None: renaming our `trunc` would hide a backend soundness hole and
churn every call site and corpus entry. Recorded as backend
pressure; the language run should namespace emitted symbols.
