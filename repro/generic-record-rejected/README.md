# repro: generic records are rejected at parse (`record Wrap<T>`)

- Toolchain: mncs-language @ `26778de`. Profile 0.10 (Nat generics).
- Backend: none (fails `source-study`, backend-independent).

## Exact command

```bash
$MNCS_BIN source-study case.mncs --node-id probe
```

## Actual behavior

```
MNP123 error: expected '{' after record name
MNP127 error: expected '}' after record fields
MNP128 error: record requires at least one field
```

The parameter list `<T>` after a record name is not in the grammar;
the same holds for value parameters (`record Buf<N: Nat>` — same
MNP123). Nat-generic *functions* over concrete array types
(`fn f<N: Nat>(a: [i64; N])`) elaborate fine, including multiple Nat
parameters (`<R: Nat, C: Nat>`) and type parameters over arrays
(`fn first<T, N: Nat>(a: [T; N])`), so the gap is specifically
*nominal generic aggregates*, not parameterization in general.

## Desired semantics

`record Wrap<T> { v: T }` usable with concrete instantiation
(`Wrap<i64>`), enabling dual-of-dual, decorated intervals, and
composite accumulator state without flat lane plumbing.

## Affected math workloads

`autodiff.mncs` (flat four-lane `DualQ` instead of `Dual<Dual<Q>>`),
interval decorations, mergeable statistics accumulators, sparse
row-pointer bundles keyed by element type.

## Workaround in use

One flat concrete record per scalar family (`DualQ` lanes `xn/xd/yn/yd`;
`DivOut2`/`DivOut8` per width). Cost: each new scalar family or width
repeats the record plus all helpers that construct it.
