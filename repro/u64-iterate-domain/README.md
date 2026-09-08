# repro: `iterate ... over` rejects a `[u64; N]` parameter domain (MNB101)

- Toolchain: mncs-language @ `6a29332` (binary sha256
  `aaf20d37...`, profile 0.12).
- Scope: front-end semantic check, so every backend is affected; the
  program never reaches codegen.

## Exact command

```bash
export MNCS_LIBRARY_PATH="$PWD/src:<mncs-language>/library"
mncs experiment run repro/u64-iterate-domain/case.mncs \
  --backend mncs-research-bytecode --corpus repro/u64-iterate-domain/corpus.json
```

## Actual behavior

`usum(a: [u64; 4])` with `iterate i over a carrying s: u64 = 0` is
rejected at parse/semantic checking:

- `MNB101 | functions[0].body.bounded_iterations[0].domain: sequence
  traversal domain must name a resolvable element type`

The identical shape over `[i64; 8]` (`sparse.mncs` `spmv_coo`,
green on all backends) and over `[f64; N]` (`float.mncs` `fdot_arr`,
green on bytecode/wasm) is accepted. Only the `u64` element type
fails domain resolution.

## Desired semantics

`iterate i over a` should accept a `[u64; N]` value parameter exactly
as it accepts `[i64; N]` and `[f64; N]`, yielding `u64` indices.

## Workaround cost

u64 kernels that need bounded traversal must either take `[i64; N]`
and cast elementwise, or restructure around `iterate x up_to k` with
manually threaded buffers — both add per-element casts or force a
signed domain onto unsigned data. `modular.mncs` and `bigintx.mncs`
were written to dodge this (index ladders over `up_to`, no
`iterate over` a u64 array).

## Affected math workloads

Any future kernel holding u64 blocks (modular towers, bigint limbs,
NTT buffers) that wants idiomatic `iterate i over buf` reduction.
