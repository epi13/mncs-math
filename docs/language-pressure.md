# MNCS Language pressure catalog (mncs-math run)

Evidence-backed list of exactly where serious scientific computing
pressures MNCS Language today. Every item has a reproducer, an error
code where applicable, the workaround used, and the functionality it
unlocks. Nothing here was fixed in the language this run (hard
boundary); everything was isolated and documented with reproducers.

Conventions: `P0xx` = language capability gaps; `MNB/MNE/MNP` codes
are compiler diagnostics observed verbatim.

## Capability gaps (need language work)

### P001 — No float type

The single largest blocker. Absent: float LU/QR/Cholesky/eigen and
condition estimation (`docs/linear-algebra.md`), transcendental dual
rules (`docs/autodiff.md`), golden-section and gradient descent
(`docs/optimize.md`), adaptive quadrature and tolerance-driven Newton
(`docs/numerical.md`), float intervals with directed rounding
(`docs/interval.md`), stiff/implicit ODE steps. The library proves
everything it can exactly; the rest is specified per-module, not
faked. Unlocks the most functionality of any single change.

### P002 — `select` evaluates both arms (strict)

Probed: `select(false, 1 / 0, 0)` fails with `runtime_failure`
(`integer div overflow or did not produce a value`) — the untaken arm
still traps. The same holds for `&&`/`||` operands. Discipline used
throughout: `select` arms carry total operations only; conditionally
safe arithmetic goes through `if`/`return` helpers (which are lazy),
e.g. `bareiss_quot`, `norm_abs_pos`, `lu_perm_ok` gating. Cost: every
conditional exact division needs a named helper (~4 lines each).

### P005 — No const-generics, nested records, or traits

Each matrix size is a hand-written kernel (`det2` closed form,
`det3` Sarrus, `det4` Bareiss; `rank3` by minors, `rank4` by
elimination). 5x5+ is feasible but quadratic in code size. Records
cannot nest, so `DualQ` is a flat four-lane record and dual-of-dual
is inexpressible. No traits means numeric kernels cannot abstract
over Z/Q/fixed. Tensor contraction over dynamic shapes is out.

### P006 — No callable values / closures

Function targets are fixed cubic coefficients (`bisect8`,
`newton3`, `ternary8`, `simpson_cubic` share the dual evaluator).
Nonlinear targets, reverse-mode tapes, RK4 on nonlinear ODEs, and
general objectives all need values that can be called. This is the
second-biggest expressiveness unlock after floats.

### P007 — No data-dependent loop exit

All iteration is counted (`steps8`, traversals) or unrolled. Adaptive
quadrature, convergence loops, and unbiased rejection sampling are
inexpressible; fixed-step drivers with documented contracts are used
instead. (Early `return` inside a loop body is allowed — the
`complex.gcd` precedent — so sticky-error short-circuit works; only
the exit condition cannot depend on data.)

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

### MNE133/MNE135 — Call results cannot be call arguments

`sub(x, mul(a, b))` is rejected; every composition must be flattened
through `let` + match-split helpers. Rational-heavy code (substitution
chains, Simpson, Newton) pays a ~3-4x helper multiplier for this
alone. `let`-bound call results passed as arguments are fine, as are
calls in tail position. Recommended: allow nested calls or document
the restriction with this cost estimate.

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
  splitmix64 vector), committed and self-contained.

## Step-budget scaling (measured)

Division-heavy kernels dominate budgets: 4x4 Cramer solves run at
~2M steps, LU/Newton/bisection/ternary at ~1M, Bareiss determinants
far below. `scripts/bench.sh` collects per-case steps on both
backends; `docs/performance.md` tabulates them. Portable WASM runs
roughly 10x the steps of research bytecode on identical corpora
(different cost model, same results).

## Blocked / deferred work

See per-module docs: float stack (**P001**), rank-generic kernels
(**P005**), callable targets and reverse mode (**P006**), adaptive
loops (**P007**), nested records, traits, checked index types. The
fixed-rank transpose-copy was cut (proves nothing beyond the index
maps without a contraction to feed). Mode finding, quartiles, and
decorated intervals were deferred as scope, not blocked.

## Recommended next language campaign (prioritized)

1. **Float type** with IEEE semantics (+ rounding-mode hooks):
   unlocks float linalg, transcendentals, float intervals,
   tolerance optimizers, adaptive quadrature, Krylov methods.
2. **Callable values/closures**: unlocks general Newton/bisection/
   ternary targets, nonlinear ODE steps, reverse-mode scaffolding.
3. **Const-generics / rank-generic arrays**: unlocks NxN kernels,
   tensor contraction, generic sorting/selection.
4. **Data-dependent loop exit**: unlocks adaptive methods,
   rejection sampling, convergence loops.
5. **Nested records / record generics**: unlocks dual-of-dual,
   decorated intervals, composite states without lane plumbing.
6. **Compiler fixes**: hygienic temp identities (MNB011), nested
   call arguments (MNE133/135) or a documented cost model, u64 `-%`
   parity, `!` sugar.
7. **Traits**: generic numeric kernels over Z/Q/fixed without
   copy-paste tiers.
