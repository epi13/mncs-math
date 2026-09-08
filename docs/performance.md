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
| autodiff | 29 | 250,928 | halley-5/2 (50,416) |
| deterministic | 21 | 4,028 | shuffle-basic (1,117) |
| statistics | 22 | 13,170 | cov-self (1,470) |
| numerical | 13 | 739,859 | bisect-cubic (238,135) |
| optimize | 7 | 509,753 | ternary-quadratic (261,047) |
| float | 50 | 359 | sum6-ctl-loop (62) |
| poly | 15 | 3,483 | qeval2 (2,652) |
| modular | 21 | 437,459 | inv-max-mod (347,555) |
| ntt | 6 | 1,066,824 | conv8-ntt (400,383) |
| sparse | 10 | 1,748 | spmv-csr (618) |
| linalg5 | 18 | 355,414 | solve5 (86,019) |
| tdata | 12 | 1,798 | bmm2 (322) |
| bigintx | 12 | 862,409 | powmod16 (704,589) |
| ode | 13 | 692 | rk4-2steps (191) |

## Generic-dimension step ladder (research bytecode steps)

Same-algorithm, per-size cost for the Bareiss/rank ports — the
step-count analogue of the source-copy table in `docs/generics.md`:

| Case | Steps |
| ---- | ----- |
| det4-tridiag | 5,979 |
| det5-generic | 13,638 |
| det6-generic | 24,279 |
| rank4-identity | 7,939 |
| rank5-full | 18,579 |
| rank6-full | 32,771 |
| rank6-swap (zero diagonal, swaps every step) | 28,059 |
| solve4-cramer | 32,494 |
| solve5 (six 5x5 dets + residual) | 86,019 |

Determinants roughly double per size step (2.3x from 4→5, 1.8x
from 5→6), rank likewise (2.3x, 1.8x), Cramer ~2.6x (6 dets vs 4
plus wider lanes). A Cramer-6x6 would project to ~7 × 24k +
residual ≈ 180k steps — well under the 8M ceiling, so the ceiling
binds source size (a seventh copy), not steps.

## Frontend study-time scaling (wall time, `source-study`)

Study time is not a function of source size. Same-size modules
differ by 12x; zero-import modules study in under 3s regardless of
content; controlled micro-probes rule out array lanes (8→36),
element width (i64→u64), and kernel count (1→6) as drivers — all
sub-second. Cost concentrates in specific modules and their import
closures (`tensor.v1`: 419 lines / ~15s, inherited by `tdata`).

| Module | Lines | Study | Imports |
| ------ | ----- | ----- | ------- |
| error | 134 | 0.4s | — |
| ode | 113 | 1.6s | — |
| float | 179 | 1.8s | — |
| sparse | 164 | 3.0s | — |
| scalar | 541 | 6.1s | error, internal, ordering |
| modular | 167 | 9.0s | scalar |
| ntt | 198 | 9.8s | scalar |
| rational | 447 | 10.4s | error, internal, scalar, logic |
| bigint | 738 | 12.4s | error, internal |
| poly | 216 | 14.9s | rational |
| statistics | 288 | 15.6s | error, scalar, rational |
| tdata | 153 | 15.8s | tensor |
| autodiff | 643 | 26.5s | error, scalar, rational |
| complex | 628 | 28.7s | error, scalar, bigint, fixed |
| numerical | 343 | 32.9s | error, scalar, rational, autodiff, internal |
| bigintx | 444 | 35.1s | error, scalar, bigint |
| optimize | 152 | 36.2s | error, scalar, rational, numerical, internal |
| linalg | 1261 | 57.1s | error, scalar, rational, matrix |
| linalg5 | 572 | 73.6s | error, scalar, rational, linalg |

The per-line extremes (`optimize`: 152 lines / 36s; `linalg5`:
643 lines / 74s vs `scalar`: 541 lines / 6s) show the driver is
construct-level, not size-level — unidentified from outside the
compiler, which is itself the finding (see `docs/language-pressure.md`).

## Findings

- **Division-heavy rational chains dominate.** Bisection (16 dual
  evaluations of 15-op chains per halving) and ternary narrowing are
  the most expensive per case; Cramer 4x4 solves cost ~32k steps
  against multi-million step budgets — budgets are generous, not
  tight, and could be halved without risk.
- **Bigint division and complex gcd are the arithmetic hot spots**
  (400k and 129k max cases); both are algorithmically necessary work
  (long division, Stein chains), not dispatch overhead. Wave-2 adds
  two of the same class: 16-bit `powmod` square-and-multiply chains
  (704,589 steps, the heaviest bytecode case in the tree) and NTT
  twiddle ladders (`conv8-ntt`, 400,383).
- **Portable WASM runs 7-15x the steps of research bytecode** on
  identical corpora with identical results (wave-2 range: ode 7.3x
  … float 15.4x) — a backend cost-model difference, explicitly not
  a semantic one. The identical frozen expectations on both backends
  are the determinism receipt.
- **Determinism is pinned, not asserted**: splitmix64 matches the
  published reference vector, shuffles pin exact permutations, and
  the sample example pins seed-dependent indices — any backend
  divergence fails the corpus. Float adds bit-frozen IEEE semantics:
  four reduction orders over identical inputs pin four distinct
  bit-patterns, so a reassociating backend fails loudly.
- Budgets are headroom, not limits: the heaviest bytecode case
  (`powmod16`, 704k steps) uses under a tenth of its 8M budget; the
  Halley steps (~50k) use a twentieth of their 1M budgets; most
  cases use under a tenth. The 8M runner ceiling is the first
  budget that bites — it already rules out a Cramer-6x6 copy
  (seven 6x6 determinants), which is itself a useful pressure
  signal (step budgets scale with algorithm choice, visibly).
