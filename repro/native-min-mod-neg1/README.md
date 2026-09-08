# repro: native backends crash on `i64::MIN % -1` (interpreter returns 0)

- Toolchain: mncs-language @ `26778de` (binary sha256
  `aaf20d37...27892a71e8273f`, snapshot 2026-09-07). Profile 0.10.
- Backends: `mncs-c11` and `mncs-llvm-ir` fail;
  `mncs-research-bytecode` (and `mncs-portable-wasm-mvp`) return `0`.

## Exact command

```bash
export MNCS_BIN=<mncs-cli>
$MNCS_BIN experiment run case.mncs --backend mncs-c11 --corpus corpus.json
```

## Actual behavior

Case `min-mod-neg1` (`min_mod_neg1(i64::MIN, -1)`, expected `0`):

- `mncs-research-bytecode`: `returned [i64 0]`, expectation met,
  overall `UNKNOWN` (standing `body:integer-overflow` obligation: `%`
  retains its div-zero / MIN-divide trap obligation with a
  conservative fallback).
- `mncs-c11`, `mncs-llvm-ir`: `invalid_request`,
  `failure_reason: "invalid native observation: native program produced
  no JSON observation (stderr: )"`. The native program dies without
  writing an observation — consistent with the lowered C `%`
  trapping (SIGFPE on `INT64_MIN % -1`, C UB) and no guard in place.

## Desired semantics

MNCS pins `MIN % -1 == 0` without trapping (`scalar.mncs`
`checked_mod`, corpus case `mod-min-by-neg-one-is-zero`, only
`MIN / -1` traps). Native backends must implement the same edge:
either a pre-check or a non-trapping lowering. The interpreter
backends already do.

## Affected math workloads

`scalar.mncs` `checked_mod` and everything built on remainder edges
(rational normalization guards, modular kernels, bigint division
remainders). The in-repo comment claiming this edge is "verified
backend behavior" is currently true only for the interpreter backends;
it must be qualified until the native guard lands.

## Workaround in use

None: an MNCS-level `if b == -1` guard would change step counts and
hide a backend soundness hole. Recorded as backend pressure.
