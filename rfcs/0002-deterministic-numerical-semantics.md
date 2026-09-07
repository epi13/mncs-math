# RFC 0002 — deterministic numerical semantics

Status: accepted (2026-09-07).

## Decision

Every `mncs-math` operation has a documented determinism contract:

- **Bitwise identical across the five executable backends** for all exact
  integer/rational/fixed/bigint kernels. Verified by running identical
  frozen corpora through `mncs-research-bytecode`, `mncs-portable-wasm-mvp`,
  `mncs-c11`, `mncs-llvm-ir`, `mncs-cranelift` in `scripts/conformance.sh`.
- **Reduction order is part of the contract**: left folds over index order
  (`iterate i over xs` from 0), pairwise where named `pairwise_*`, Kahan
  compensation where named `kahan_*`. A different order is a different
  function with a different name — never a backend choice.
- **No fused operations**: fixed-point `mul` exposes the rounding step
  explicitly; backends may not contract `mul+add` silently (nothing in the
  language permits it today; if a backend ever does, the agreement corpus
  fails closed and becomes a P0).
- **No NaN / infinities / signed zero** in the exact tiers by construction
  (integers have none). Float tiers inherit IEEE-754 binary64 semantics
  when the language gains floats; until then `docs/float-roadmap.md`
  freezes the intended rules (NaN propagates, `+0 == -0`, overflow of a
  checked op traps rather than producing infinity).

## Policy table

| Concern | Exact tiers (now) | Float tiers (blocked, specified) |
|---|---|---|
| operation order | index-order folds, frozen | index-order folds, frozen |
| reductions | named order per function | same |
| rounding | explicit (floor/nearest) args | round-to-nearest-even default, explicit elsewhere |
| overflow | checked trap / wrap / saturate intent | ±infinity per IEEE |
| div by zero | enum reason or documented trap | ±infinity / NaN per IEEE |
| cross-backend bits | identical (tested) | identical intended (untestable today → P001) |

## Conformance

`mncs.math.deterministic.v1` provides executable policy: canonical
`fold_sum` (index order), `fingerprint` (wrapping FNV-style fold over
sequences), `split_mix` for domain separation, and `checksum` helpers.
`tests/corpora/deterministic-corpus.json` pins their values; any backend
divergence is a release-blocking defect, not tolerance.
