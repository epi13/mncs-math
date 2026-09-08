# repro: operators cannot be used over a type parameter (MNE120)

- Toolchain: mncs-language @ `26778de`. Profile 0.10.
- Backend: none (fails elaboration in `source-study`).

## Exact command

```bash
$MNCS_BIN source-study case.mncs --node-id probe
```

## Actual behavior

```
MNE120 error: arithmetic operands must have an integer type
```

for `fn gadd<T>(a: T, b: T) -> (result: T) { return a + b; }`.
The type parameter itself is fine — `fn first<T, N: Nat>(a: [T; N])
-> (result: T) { return a[0]; }` elaborates (retaining only the
standard compile obligations) — but no operator or trait bound can be
named, and there is no `trait`/`where`/`impl` surface in the language
(searched `spec/` at this toolchain commit: no hits). So a generic
container can be *moved* but never *computed on*.

## Desired semantics

Operator-constrained generics (or traits): one `dot`/`add`/`mul`
spanning `i64`, rational, fixed, interval, and dual scalars.

## Affected math workloads

Every scalar family tier: `dot_i64` vs `dot_fixed` vs rational folds
are same-shaped, separately tested duplicates (RFC 0004). The
duplication multiplier grows with each new scalar family.

## Workaround in use

One concrete instantiation per scalar family, per RFC 0004, with a
removal condition. Cost: N families x M kernels separately written,
tested, and budgeted functions.
