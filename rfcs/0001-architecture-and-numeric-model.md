# RFC 0001 — mncs-math architecture and numeric model

Status: accepted (2026-09-07). Implements the module layout built in this run.

## Decision

`mncs-math` is a family of small MNCS Language modules under one naming
root, not a monolith:

```text
src/math/
  error.mncs        MathError taxonomy + fallible-result helpers
  scalar.mncs       checked/saturating/wrapping int ops, gcd/lcm/pow/isqrt,
                    modular arithmetic, combinatorics
  rational.mncs     normalized (num, den) rationals over i64
  bigint.mncs       arbitrary-precision u64-limb integers (signed + unsigned)
  fixed.mncs        deterministic fixed-point (Q-scale family over i64)
  complex.mncs      Gaussian integers + fixed-point complex
  interval.mncs     closed integer/rational intervals
  vector.mncs       fixed-size integer vectors over [i64; N]
  matrix.mncs       row-major integer matrices, Bareiss exact kernels
  linalg.mncs       exact solvers (Bareiss), substitution over rationals,
                    norms, conditioning groundwork
  tensor.mncs       rank/shape/stride storage model + elementwise/reduction/
                    contraction groundwork
  autodiff.mncs     forward-mode dual numbers over exact + fixed scalars
  optimize.mncs     bisection/Newton/secant/golden/descent with explicit
                    termination records
  numerical.mncs    finite differences, trapezoidal/Simpson integration,
                    interpolation, compensated summation
  statistics.mncs   Welford variance, covariance/correlation, quantiles
  deterministic.mncs canonical reductions, fingerprints, agreement policy
  internal.mncs     shared bounded-loop utilities (index tables, folds)
```

Each file declares `module mncs.math.<name>.v1;` and resolves through
`MNCS_LIBRARY_PATH=src` (same convention as the language library).

## Numeric model

Three exact tiers are first-class in MNCS source today:

1. **Machine integers** (`i32/i64/u64`, …): checked by default, explicit
   wrapping/saturating intents. The only arithmetic with backend-identical
   total semantics right now.
2. **Rationals** (normalized `num/den` pairs): exact, overflow-managed by
   reduce-before-multiply and the bounded `mul_div` quotient/remainder fold
   (partition-style, no `a*b` materialization).
3. **Fixed-point** (scaled i64, explicit rounding): the deterministic
   substitute for float workloads until the language gains a float type
   (see P001). Scale lives in the value/record type, never in a parameter.

A fourth tier, **limb bigint** (`[i64; N]` storage with u64 value
semantics, concrete N = 2/8 → 128/512 bits, two's complement signed),
covers magnitudes beyond i64 with schoolbook mul and restoring division
built from bounded traversals, concrete records, and unrolled block
chains (see RFC 0005).

Floats (`f32/f64`), and everything needing them, are **specified but
blocked**: documented in `docs/float-roadmap.md` with frozen oracle
fixtures, not implemented. No float emulation via hidden host calls.

## Boundaries

- Corpus entry points are scalar/sequence/enum shaped; records cross
  functions freely inside the library (verified on all five backends).
- Fallible math returns payload enums (`MathResult`-shaped), never magic
  numbers; trap-intent ops (`/`, `%`, `+`) are reserved for documented
  precondition-checked paths plus `trap-*` corpus cases.
- Dimensions that are static use exact sequences `[T; N]` (mismatch is an
  elaboration error); runtime lengths use bounded views with explicit
  length arguments.

## Non-goals

Float libm, probability distributions, sparse formats, GPU kernels — all
deferred to `docs/roadmap.md` withunlock conditions.
