# Performance and determinism findings

Step counts are collected by `scripts/bench.sh` (per-case interpreter
steps on both backends; steps are a deterministic cost model, not wall
time). Totals below are whole-corpus sums on research bytecode;
per-case maxima name the heaviest case.

## Whole-corpus cost (research bytecode steps)

| Module | Cases | Total | Max case (steps) |
| ------ | ----- | ----- | ---------------- |
| error | 8 | 54 | is-ok-false (9) |
| scalar | 63 | 51,823 | binom-past-i64 (8,814) |
| rational | 55 | 12,452 | div-improper (799) |
| internal | 3 | 152 | steps64-last (70) |
| bigint | 63 | 1,682,316 | div8-decimal (400,282) |
| fixed | 57 | 18,094 | exp-neg-nine (1,523) |
| complex | 35 | 974,197 | g-gcd-coprime (128,771) |
| vector | 25 | 3,596 | norm-milli-345 (1,244) |
| matrix | 15 | 4,092 | matmul-4x4-identity (1,568) |
| linalg | 94 | 574,658 | solve4-cramer (32,494) |
| tensor | 45 | 3,938 | bcast-4d (290) |
| interval | 35 | 2,467 | mul-cross (233) |
| autodiff | 19 | 28,698 | q-poly3 (12,439) |
| deterministic | 21 | 4,028 | shuffle-basic (1,117) |
| statistics | 17 | 6,877 | mean-var-basic (1,256) |
| numerical | 13 | 739,859 | bisect-cubic (238,135) |
| optimize | 7 | 509,753 | ternary-quadratic (261,047) |

## Findings

- **Division-heavy rational chains dominate.** Bisection (16 dual
  evaluations of 15-op chains per halving) and ternary narrowing are
  the most expensive per case; Cramer 4x4 solves cost ~32k steps
  against multi-million step budgets — budgets are generous, not
  tight, and could be halved without risk.
- **Bigint division and complex gcd are the arithmetic hot spots**
  (400k and 129k max cases); both are algorithmically necessary work
  (long division, Stein chains), not dispatch overhead.
- **Portable WASM runs 6-13x the steps of research bytecode** on
  identical corpora with identical results — a backend cost-model
  difference, explicitly not a semantic one. The identical frozen
  expectations on both backends are the determinism receipt.
- **Determinism is pinned, not asserted**: splitmix64 matches the
  published reference vector, shuffles pin exact permutations, and
  the sample example pins seed-dependent indices — any backend
  divergence fails the corpus.
- Budgets are headroom, not limits: the heaviest bytecode case
  (`bisect-cubic`, 238k steps) uses about a quarter of its 1M budget;
  most cases use under a tenth. Division-heavy kernels are where a
  future 5x5 elimination or deeper Newton chain would first feel the
  budget, which is itself a useful pressure signal (step budgets
  scale with algorithm choice, visibly).
