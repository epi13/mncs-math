# MNCS Language pressure catalog (mncs-math runs)

Evidence-backed list of exactly where serious scientific computing
pressures MNCS Language today. Every item has a reproducer, an error
code where applicable, the workaround used, and the functionality it
unlocks. Nothing here was fixed in the language across either run
(hard boundary); everything was isolated and documented with
reproducers. Wave-2 additions are marked **[W2]**.

Conventions: `P0xx` = language capability gaps; `MNB/MNE/MNP` codes
are compiler diagnostics observed verbatim. `repro/` holds minimal
reproducers, each with `case.mncs`, `corpus.json`, `README.md`, and
`expected.md` (per-backend observed behavior).

## Capability gaps (need language work)

### P001 — Float tier partial (was: no float type) **[W2]**

Stage C1/C2 binary64 shipped since the first run: total finite-value
arithmetic with the trap rule, comparisons, int<->float `as`, and
host-libm sin/cos on all five backends (`float.mncs`, 50 value cases
+ 3 trap cases, all green on research-bytecode/wasm). Absent:
exp/log/sqrt/pow, rounding-mode control, float LU/QR/Cholesky/eigen
and condition estimation (`docs/linear-algebra.md`), exp/log dual
rules (`docs/autodiff.md` — sin/cos dual rules are expressible now),
golden-section and gradient descent (`docs/optimize.md`), adaptive
quadrature and tolerance-driven Newton (`docs/numerical.md`), float
intervals with directed rounding (`docs/interval.md`),
stiff/implicit ODE steps. The library proves everything it can
exactly; the rest is specified per-module, not faked. Still the
largest remaining expressiveness unlock.

### P002 — `select` evaluates both arms (strict)

Probed: `select(false, 1 / 0, 0)` fails with `runtime_failure`
(`integer div overflow or did not produce a value`) — the untaken arm
still traps. The same holds for `&&`/`||` operands. Discipline used
throughout: `select` arms carry total operations only; conditionally
safe arithmetic goes through `if`/`return` helpers (which are lazy),
e.g. `bareiss_quot`, `norm_abs_pos`, `lu_perm_ok` gating. Cost: every
conditional exact division needs a named helper (~4 lines each).

### P005 — No const-generics, nested records, or traits (partially decomposed) **[W2]**

Concrete nesting now works and is load-bearing: `repro/nested-calls-supported`
(call results bound with `let` and passed on) and
`repro/nested-record-supported` (records built from other records'
fields) both pass, and wave-2 leans on them (`Frac`/`DualQ` record
values as parameters, `halley_*` chains). What remains blocked:

- generic nominals and dimension arithmetic: each matrix size is a
  hand-written kernel (`det2` closed form, `det3` Sarrus, `det4`
  Bareiss, `det5`/`det6` Bareiss ports, `rank5`/`rank6` ports);
  const-expression bounds (`[i64; N - 1]`, MNP149) do not exist.
  Measured per-size cost in `docs/generics.md`.
- nested records: `DualQ` stays a flat four-lane record; dual-of-dual
  is inexpressible, so the Halley second derivative costs a second
  full evaluation plus a cross-check ladder instead of composition.
- traits: numeric kernels cannot abstract over Z/Q/fixed; tensor
  contraction over dynamic shapes is out.

### P006 — No callable values / closures

Function targets are fixed cubic coefficients (`bisect8`,
`newton3`, `ternary8`, `simpson_cubic` share the dual evaluator;
`entry_halley`/`entry_d2cubic` fix `x^3 - 2x - 5`). Nonlinear
targets, reverse-mode tapes, RK4 on nonlinear ODEs, and general
objectives all need values that can be called. This is the
second-biggest expressiveness unlock after floats.

### P007 — No data-dependent loop exit

All iteration is counted (`steps8`, traversals) or unrolled. Adaptive
quadrature, convergence loops, and unbiased rejection sampling are
inexpressible; fixed-step drivers with documented contracts are used
instead. (Early `return` inside a loop body is allowed — the
`complex.gcd` precedent — so sticky-error short-circuit works; only
the exit condition cannot depend on data.)

### P009 — No checked index type (aspirational)

`docs/tensor.md`: negative-lane permutations are total (clamped)
with input-echo residue; strided gathers carry valid-domain
preconditions. A checked index type would turn these contracts into
types. Library-level index discipline (residue lanes, `-1`
validity-mask convention in `broadcast4`) is the holding pattern.

## Native backend divergences (soundness, with reproducers) **[W2]**

All items below are green on `mncs-research-bytecode` and
`mncs-portable-wasm-mvp` and wrong on at least one native backend.
Each has a `repro/` directory with frozen per-backend expectations.

- **f64 array value parameters miscompile on all three natives**
  (`repro/native-f64-array-param`). Passing `[f64; N]` by value to a
  callee: C11 returns garbage (`4.613937818241073e+18` for a `3.0`
  sum), Cranelift returns `0.0`, LLVM emits `trunc i64 %x to double`
  and clang rejects the *whole module* — so one float-array kernel
  poisons even healthy integer entries sharing the module
  (`float.mncs`: 40/40 `unsupported` on LLVM; 39/40 on C11/Cranelift
  with only `dot4-generic` wrong). Scalars, local arrays, and `[i64;
  N]` parameters are all fine: the trigger is exactly the `f64`
  element type of a by-value array parameter (lengths 2, 4, 8
  probed). The fault is not confined to call boundaries: reducing
  a *local* `[f64; 6]` with `iterate` returns 2^33+3 on C11
  (value-dependent — small integers survive) and drops the
  accumulation on Cranelift (`loop6`/`loop6ctl` in the same
  repro). Consequences for science code: any kernel moving float
  buffers — across calls or inside loops — is silently wrong on
  natives.
- **Checked u64 `+`/`-` mistrap on high-bit operands (C11,
  Cranelift)** (`repro/native-c11-u64-widening`). Values ride in
  `int64_t` cells; the widening check reinterprets the signed cell
  instead of zero-extending (`(unsigned __int128)v` with
  `v = (int64_t)u64::MAX`). Any u64 operand `>= 2^63` poisons every
  checked plain op. LLVM is correct here. Wave-2 evidence:
  `modular.mncs` high-bit `bgcd`/`inv` cases fail identically on C11
  and Cranelift (18/21 each) while LLVM passes 21/21, and
  `deterministic.mncs` fails exactly the 9 u64-RNG cases
  (bounded draws, Lemire maps, shuffles — 12/21 pass) on both
  backends with the same signature. Failure sets differ by backend
  elsewhere in the family: `scalar.mncs` fails `min-mod-neg1` (no
  observation) plus `mul-mod-degenerate` on C11/LLVM but
  `gcd-min-magnitude` (i64::MIN magnitude) plus
  `mul-mod-degenerate` on Cranelift — same signed-cell root cause,
  three different faces. `rational.mncs` on Cranelift mistraps
  exactly the 5 `i64::MIN`-magnitude cases (50/55 pass) while LLVM
  passes 55/55.
- **C11 emits stdlib-colliding helper names**
  (`repro/native-c11-symbol-collision`, plus wave-2 instances).
  Helper names `min` and now `trunc` collide with libc declarations
  and clang rejects the module. Blast radius is not corner-only:
  `rational.mncs` — the foundation of every exact tier — fails
  55/55 on C11 for `trunc`, as do `linalg` (94/94), `autodiff`
  (29/29), `statistics` (22/22), `linalg5` (18/18), `poly`
  (15/15), `numerical` (13/13), and `optimize` (7/7); all pass on
  bytecode, wasm, and LLVM. Both end-to-end examples (`ex_sample`
  3/3, `ex_solve` 1/1) are likewise unbuildable on C11 for `trunc`:
  one identifier disables 257 corpus cases plus the integration
  story. Any module whose lowering needs one of these names is
  unbuildable on C11; the set grows with the workload.
- **`iterate ... over` rejects `[u64; N]` domains (MNB101,
  front-end)** (`repro/u64-iterate-domain`). Identical iteration
  over `[i64; N]` (`sparse.mncs`, green) and `[f64; N]`
  (`float.mncs`, green) is accepted; only the `u64` element type
  fails domain resolution, on every backend (fails before codegen).
  u64 kernels (modular towers, bigint limbs, NTT buffers) must take
  `[i64; N]` plus casts or restructure around `up_to` ladders.
- **Cranelift is an order of magnitude slower on heavy modules.**
  `linalg5` (18 cases) needs 14m21s wall time on Cranelift;
  `linalg` and `bigint` value corpora exceed a 590s per-cell guard
  on Cranelift while passing on every other backend. Slow, not
  stuck: the long rerun returns 18/18 green. Any CI-style gate
  over natives needs backend-aware timeouts, or Cranelift cells
  fail closed on time alone.
- **Harness exit code conflates divergence with runner failure.**
  Natives exit 1 for isolated divergences while still emitting full
  parseable case detail (`scalar.mncs` on C11: 61/63 meet
  expectations plus the two repro-isolated `min-mod-neg1` /
  `mul-mod-degenerate` failures). A triage that keys on the exit
  code reports RUNNER_ERROR and hides the 61 green cases;
  `scripts/conformance.sh` now triages whenever stdout parses and
  reserves RUNNER_ERROR for unparsable output. The exit-code
  contract itself belongs to the harness run, not this repo.

## Compiler diagnostics hit (with reproducers)

### MNB011 — Body-value identity collision on short names (compiler bug)

A record literal (or `==` inside an `||`-chain) makes elaboration
derive a temp identity from a parameter name and then report it as a
duplicate. Minimal reproducers (all verified with `source-study`):

```mncs
record DualZ { x: i64, dx: i64 }
fn no_literal(c0: i64, c1: i64, t: DualZ) -> (result: DualZ) {
    return DualZ { x: c1, dx: 0 };   // MNB011: duplicate "c0"
}
```

```mncs
fn bcast_ok4(a0: i64, ..., b3: i64) -> (result: bool) {
    ...
    let c3: bool = a3 == b3 || a3 == 1 || b3 == 1;  // MNB011: duplicate "b3"
    ...
}
```

Empirical rule: single-letter+digit identifiers (`c0`, `b3`) collide;
multi-character names (`coef0`, `a2n`, `t0`, `xn`) do not. Workaround:
rename (`tensor.mncs` `bcast_ok4` uses `xN`/`yN`; `autodiff.mncs`
polynomials use `coefN`). Recommended fix: hygienic temp identities
in the elaborator.

### MNB101 — u64 iterate domain unresolvable (front-end gap) **[W2]**

See backend section above (`repro/u64-iterate-domain`). The
sequence-traversal domain check resolves `i64`/`f64` element types
but not `u64`. Recommended fix: extend domain element-type
resolution to all integer widths (or document the restriction with
the cast workaround).

### MNE133/MNE135 — Call results cannot be call arguments

`sub(x, mul(a, b))` is rejected; every composition must be flattened
through `let` + match-split helpers. Rational-heavy code (substitution
chains, Simpson, Newton, and now the 11-rung Halley ladder) pays a
~3-4x helper multiplier for this alone. `let`-bound call results
passed as arguments are fine, as are calls in tail position.
Recommended: allow nested calls or document the restriction with
this cost estimate.

### MNE117/MNE119 — Mixed int/float operators rejected **[W2]**

Mixed `i64`/`f64` arithmetic has no overloads; crossings go through
explicit `as` conversions (`float.mncs` header documents the rule).
Precise and liveable; listing it so the float-tier contract is
complete.

### MNE156/MNE160 — Record literal field checks

Precise and helpful as diagnostics (they caught a real `byd:`/`yd:`
copy-paste typo in `autodiff.mncs` entries). No complaint.

### MNE192 — Constant out-of-range projection is a compile error

`a[9]` on `[i64; 4]` fails elaboration; computed indices elaborate as
runtime-checked and trap with `sequence index out of bounds` (probed
for both large and wrapped-negative indices). The split is sound and
useful: fixed bugs at compile time, contract checking at runtime.

### MNP051/MNP052 — `let` requires a type annotation

Unannotated `let s = ...` is a parse error. Verbose but consistent;
every binding in `mncs-math` is annotated.

### MNP064 — Negative literals are not call arguments **[W2]**

Hit while writing the Halley cubic coefficients:
`dualq_poly3_q(-5, -2, 0, 1, ...)` parses as MNP064 `expected
expression`; the workaround is `(0 - 5)` argument forms (4
call sites in `autodiff.mncs`). Cheap to fix in the grammar; until
then every negative constant argument pays the wrapping idiom.

## Small inconsistencies (cheap to fix)

- **No `!` operator.** Negation idiom is `select(c, false, true)`
  (`vector.mncs:115` precedent). Trivial sugar.
- **No u64 `-%`.** `+%` and `*%` accept u64 operands (probed), but
  `-%` resolves i64-only (MNE117/MNE119); plain `-` works and is exact
  where no underflow is possible (`deterministic.mncs` Lemire carry).
  Parity fix.
- **`as` casts and wide literals work contextually**: `x as u64`,
  `v as i64`, `u64` literals above `i64::MAX` (splitmix constants,
  FNV basis), computed shift amounts (`a >> k`), `&`/`^`/`<<` all
  probed good.
- **Step budgets cap at 8,000,000** (runner rejects above). Every
  wave-2 kernel fits (heaviest measured: `det6-generic` ~24k steps;
  budgets are ceilings, typically 100-300x headroom), but a future
  Cramer-6x6 (seven 6x6 determinants) would have to budget against
  this ceiling — part of why 6x6 ships without a solver.

## Proven patterns (load-bearing, verified by corpora)

- Concrete shapes + records; cross-module `use` of fns, record
  construction, enum match, and field projection (`ex_sample.mncs`
  projects `Shuf8.arr` across modules).
- Error-as-data via total observers (`frac_num/den/code`,
  `dualq_*`, `reason_of`); residues trap-free by construction.
- Match-split helper chains instead of match-in-loop; sticky codes
  with first-failure-wins combine functions.
- Counted loops carrying records; 2-level nesting via helpers called
  from loop bodies (`matmul9`/`row_dot9` precedent); early `return`
  in loop bodies.
- Multi-field enum construction/destructuring; `..` wildcard arms.
- Strict-`select` discipline and `if`-dispatch for rank/shape
  variation (`unravel4`, `strides4`, `numel4`).
- Oracle-generated frozen corpora: every expectation derived by an
  independent implementation (Python exact arithmetic, Fractions,
  bignum cross-checks, brute-forced sorting-network proof, published
  splitmix64 vector, host-libm frozen float bits), committed and
  self-contained.
- Reduction-order pinning: float addition is never reassociated by
  any backend — six-lane orders pin four distinct bit-patterns over
  identical inputs (`float.mncs` `candidate_fsum_*`). The `iterate`
  loop agrees with the left fold bit-for-bit on bytecode/wasm only;
  on natives it diverges (C11 value-dependent garbage, Cranelift
  dropped accumulation — `repro/native-f64-array-param` `loop6`). **[W2]**
- Dual-evaluation cross-checks: the Halley step's two `f'` lanes
  (c-eval tangent vs c'-eval value) are asserted equal inside the
  computation, and `cov(x,x) == var(x)` is pinned on both entries
  (`statistics.mncs`). **[W2]**

## Step-budget scaling (measured)

Division-heavy kernels dominate step usage: 4x4 Cramer solves peak
at ~32k steps per case (against ~2M budgets), bisection/ternary
heavier per case (up to ~260k), Bareiss determinants far below.
`scripts/bench.sh` collects per-case steps on both backends;
`docs/performance.md` tabulates them. Portable WASM runs roughly
10x the steps of research bytecode on identical corpora (different
cost model, same results).

Wave-2 additions: exact Halley steps peak at ~50k steps per case
(three dual-poly evaluations plus the step ladder) against 1M
budgets; rank-6 elimination peaks at 32,771 steps against 8M;
NTT and modular-exponentiation maxima reflect algorithmically
necessary work (twiddle chains, square-and-multiply), not dispatch
overhead. See `docs/performance.md` for the 4x4/5x5/6x6 ladder
(determinants and rank roughly double per size step).

## Frontend scaling hazard (measured) **[W2]**

`source-study` wall time is not a function of source size.
Same-size modules differ by 12x (`linalg5`: 572 lines / ~74s vs
`scalar`: 541 lines / ~6s); zero-import modules study in under 3s
regardless of content (`error`, `float`, `sparse`); controlled
micro-probes rule out array lanes (8→36), element width (i64→u64),
and kernel count (1→6) as drivers — all sub-second. Cost
concentrates in specific modules and their import closures
(`tensor.v1`: 419 lines / ~15s, inherited by `tdata`). Full table in
`docs/performance.md`. For a campaign pushing 10x-larger science
workloads, frontend scaling needs profiling in the language run;
from outside, the cost driver is unidentified by construction.

## Blocked / deferred work

See per-module docs: float stack (**P001**), rank-generic kernels
(**P005**), callable targets and reverse mode (**P006**), adaptive
loops (**P007**), nested records, traits, checked index types. The
fixed-rank transpose-copy was cut (proves nothing beyond the index
maps without a contraction to feed). Mode finding, quartiles, and
decorated intervals were deferred as scope, not blocked.

Wave-2 scope notes: 6x6 ships determinants and rank but no Cramer
solve (seven 6x6 determinants vs the 8M budget ceiling — a copy not
worth writing); no stride-3 gather quad fits 8 lanes (documented in
`tdata.mncs`); the Halley singular equation `2f'^2 - f*f'' = 0`
reduces to `6x^4 - 6x^2 + 15x + 4 = 0`, which has no rational root
at all (all 16 rational-root-theorem candidates tested empty), so
the Halley `Err` paths are pinned via zero-denominator and
overflow starts instead.

## Recommended next language campaign (prioritized)

1. **Native backend soundness**: f64 array parameters on all three
   natives, u64 widening on C11/Cranelift, C11 stdlib symbol
   collisions, LLVM `trunc`-to-double cast + module-wide poisoning.
   Silent wrong values beat missing features for harm.
2. **Float type completion** (exp/log/sqrt/pow + rounding-mode
   hooks): unlocks float linalg, transcendentals, float intervals,
   tolerance optimizers, adaptive quadrature, Krylov methods.
3. **Callable values/closures**: unlocks general Newton/bisection/
   ternary targets, nonlinear ODE steps, reverse-mode scaffolding.
4. **Const-generics / rank-generic arrays**: unlocks NxN kernels,
   tensor contraction, generic sorting/selection (measured copy
   costs in `docs/generics.md`).
5. **Frontend scaling**: profile `source-study` cost drivers; the
   campaign's modules show 12x same-size spreads.
6. **Data-dependent loop exit**: unlocks adaptive methods,
   rejection sampling, convergence loops.
7. **Nested records / record generics**: unlocks dual-of-dual,
   decorated intervals, composite states without lane plumbing.
8. **Compiler fixes**: hygienic temp identities (MNB011), u64
   iterate domains (MNB101), negative literal arguments (MNP064),
   nested call arguments (MNE133/135) or a documented cost model,
   u64 `-%` parity, `!` sugar.
9. **Traits**: generic numeric kernels over Z/Q/fixed without
   copy-paste tiers.

## 2026-09-26 native-testing campaign note

This catalog was not rewritten, but three items changed state during the
native-testing campaign (evidence in `tests/native/`, `src/math/approx.mncs`,
`docs/native-testing.md`):

- P001 (float tier partial): the transcendental remainder (exp/log/sqrt/pow,
  rounding control, float linalg) is now canonical
  `MNCS-LANG-35EF41F1B6E5` with a math observation. The 50+3 float corpora
  stand; `approx` tolerance policy is new math-owned coverage.
- New test-system pressure: native tests cannot assert expected traps, so
  all trapping behavior stays in `*-traps` corpora. Canonical
  `MNCS-TOOLING-06EB8DF14CC3` (non-blocking).
- `select` strictness (P002) is intended language semantics (pinned in the
  Source Profile 0.8 documentation); the lazy conditional expression now
  exists as uniform lazy `match` at profile 0.13.

Staleness warning: item 8's compiler list (u64 iterate domains MNB101,
negative literal arguments MNP064, nested call arguments MNE133/135, i64
`>>`) predates Source Profiles 0.12–0.13, which admit u64 domains, repeat
literals, shadowing, generic inference, and cross-module nested sequences
(sibling-engine re-verification 2026-09-26 confirms several no longer
reproduce). The catalog needs its own re-verification pass before the next
language run treats item 8 as current; until then, prefer the profile docs
plus fresh reproducers over these entries.
