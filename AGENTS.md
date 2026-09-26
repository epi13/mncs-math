# mncs-math — agent working agreement

Machine-native scientific mathematics for the MNCS ecosystem, written in
MNCS Language itself.

## Hard boundary

All committed changes in this repository must live under this repo root.
Never modify `mncs-language`, `mncs-commons`, `mncs-fabric`,
`mncs-harness`, or any other checkout. Those trees are read-only
references (toolchain, conventions, standard library). If the language is
missing something this library needs, record it in
`docs/language-pressure.md` with a reproducer under `repro/` — do not
work around it silently and do not patch the toolchain.

## Layout

```text
src/math/        MNCS sources, one module per file: mncs.math.<name>.v1
tests/corpora/   frozen execution corpora (*.json, schema 0.1)
tests/tables/    oracle tables consumed by tools/mkcorpus.py (dev-time only)
examples/        runnable MNCS programs + their corpora
benchmarks/      representative kernels + corpora + BENCHMARKS.md baselines
docs/            architecture, semantics, determinism, pressure, roadmap
rfcs/            long-term architectural decisions (0001-0007)
repro/           minimal language-pressure reproducers, one dir per P-ID
scripts/         conformance.sh, check.sh, freeze.sh (bash + mncs-cli only)
tools/           fixture generators (Python stdlib only, never numpy)
```

## Toolchain

The MNCS toolchain lives outside this repo. Point at it explicitly:

```bash
export MNCS_LANG=/home/epi13/Documents/Projects/mncs-language
export MNCS_BIN=$MNCS_LANG/target/debug/mncs   # cargo build -p mncs-cli
export MNCS_LIBRARY_PATH="$PWD/src:$MNCS_LANG/library"
```

Build once with `cargo build -p mncs-cli` inside `mncs-language`
(read-only use; never commit there). If `mncs` is already on PATH, prefer
that binary and record its version in any evidence you keep.

## Module conventions (`src/math/*.mncs`)

- Lowest `mncs 0.x;` profile header that parses (0.6 record/enum baseline,
  0.7 sequences/views, 0.8 vectors/masks, 0.10 generics, 0.11 nesting).
- One module per file: `module mncs.math.<name>.v1;` in
  `src/math/<name>.mncs` (mirrors the language library layout so
  `MNCS_LIBRARY_PATH=src` resolution works).
- Every operation total: checked traps only where the error model names
  them; otherwise wrapping (`+%`/`-%`/`*%`), saturating (`+|`/`-|`/`*|`),
  or enum-returned reasons. Never invent a silent wrap.
- Records and payload enums may cross function boundaries (verified on all
  five executable backends); keep corpus entry points scalar-, sequence-,
  or enum-shaped so corpora stay simple.
- Import with `use mncs.math.<other>.v1;` — never copy a helper.
- Comments state the mathematical contract, the overflow/edge behavior,
  and the profile features used. No TODO skeletons, no hard-coded returns.

## Tests

- Committed tests are frozen JSON corpora under `tests/corpora/` plus the
  `src/math/*.mncs` files they target. They must be self-contained: no
  Python/numpy at test time.
- `tools/mkcorpus.py` regenerates corpora from `tests/tables/`; expected
  values must be independently computed (hand-derived or Python-oracle
  cross-checked), never copied from tool output without verification.
- Fast check: `scripts/check.sh <module>` (study + bytecode + wasm).
- Full gate: `scripts/conformance.sh` (all modules x five backends,
  examples, benchmark smoke). Green means every case `returned` with
  `expectation_met == true`, every trap case `runtime_failure`, overall
  `PASS` or `UNKNOWN` (UNKNOWN = unresolved obligations, normal).
- Corpus case budgets: `step_budget >= 4096` for loop kernels.
- Native property suites live in `tests/native/` (profile 0.18 `test`
  declarations; 0.6–0.12 library imports are normal). They pin laws and
  properties (identities, commutativity, inverses, boundary reasons,
  float discipline, determinism, fixed-seed generative sweeps via
  `mncs.test.generative.replay`); expected traps stay in
  `*-traps-corpus.json` because native tests cannot assert traps.
  Run: `mncs test tests/native/<suite>.mncs` with `MNCS_LIBRARY_PATH`
  covering `<mncs-test>/native`, `src`, and the language library.
- Approximate equality is math-owned (`mncs.math.approx.v1`); generic
  assertions stay in `mncs-test`. See `docs/native-testing.md`.

## What "done" means for a module

Implemented in `.mncs`, corpus frozen with exact/edge/property cases,
`conformance.sh` green on all five backends (or a pressure entry explains
the gap with a reproducer), documented in `docs/` + status table in
`README.md`, RFC coverage where architectural.

## Commit discipline

Logical increments, one subsystem per commit where practical. Never commit
generated evidence blobs (`target/`, `.forge-evidence/` scratch) — the
`.gitignore` enforces this. Feature work happens on short branches merged
to `main`.
