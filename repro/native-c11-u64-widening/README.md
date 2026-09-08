# repro: C11 backend mistraps plain u64 `+`/`-` when an operand has the high bit set

- Toolchain: mncs-language @ `26778de` (binary sha256
  `aaf20d37...27892a71e8273f`, snapshot 2026-09-07; tree dirty, see
  baseline record). Profile 0.10.
- Backend: `mncs-c11` only. `mncs-research-bytecode` and `mncs-llvm-ir`
  return the correct value.

## Exact command

```bash
export MNCS_BIN=<mncs-cli>
$MNCS_BIN experiment run case.mncs --backend mncs-c11 --corpus corpus.json
```

## Actual behavior

Case `add-0-0-max` (`addm(0, 0, u64::MAX)`, expected `0`):

- `mncs-c11`: `runtime_failure`, no value.
- `mncs-research-bytecode`, `mncs-llvm-ir`: `returned`, `0`, expectation met.

## Desired semantics

`addm` is overflow-free by construction (`room = m - y`, compare, then
one subtraction or addition, all values `< 2^64`). `addm(0, 0, MAX)`
must return `0` on every backend.

## Root cause (read from the emitted C, `--output-dir` artifact)

u64 values ride in `int64_t` cells. Plain `-` lowers to a
`unsigned __int128` wide check that reinterprets the *signed* cell
instead of zero-extending it:

```c
{ unsigned __int128 mncs_wide = (unsigned __int128)v2 - (unsigned __int128)v1;
  ...
```

With `v2 = (int64_t)u64::MAX` (`-1`), `(unsigned __int128)v2` wraps to
2^128-1, the `> UINT64_MAX` guard fires, and the backend reports a
trap. Any u64 operand `>= 2^63` poisons every checked plain `+`/`-`.
Comparisons in the same file correctly cast through `(uint64_t)`; the
wide arithmetic does not. The companion `mncs_wide < 0ULL` test is dead
code (unsigned). Suggested direction: widen through `(uint64_t)` cells.

## Affected math workloads

`scalar.mncs` `mul_mod`/`add_mod`/`dbl_mod` (corpus case
`mul-mod-degenerate`), and every current or future u64 kernel that uses
plain `+`/`-` on values `>= 2^63`, including modular arithmetic,
bigint limbs, and hashing.

## Workaround in use

None inside `mncs-math`: the corpus expectation stays `0` and the C11
divergence is recorded as backend pressure. Rewriting kernels with
wrapping operators would hide the bug and change checked semantics.
