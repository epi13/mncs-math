# Negative result: nested records DO work (corrects P005)

- Toolchain: mncs-language @ `26778de`. Profile 0.10.

## Exact command

```bash
$MNCS_BIN source-study case.mncs --node-id probe   # exit 0, no diagnostics
```

## What was claimed before

The first-campaign catalog said "Records cannot nest, so `DualQ` is a
flat four-lane record and dual-of-dual is inexpressible."

## What the probe shows

`case.mncs` declares `record Outer { inner: Inner, y: i64 }`,
constructs it nested (`Outer { inner: Inner { x: a }, y: b }`), and
projects through two levels inside a wrapping operator
(`o.inner.x +% o.y`). `source-study` exits 0 with zero diagnostics.
First-level projection (`o.y`) and deep projection (`o.inner.x`)
behave identically. (An early probe failure on this shape was a shell
`printf` eating the `%` in `+%`, not a language error.)

## What remains blocked (separately)

- *Generic* records (`record Wrap<T>`): still MNP123
  (`../generic-record-rejected`). Dual-of-dual needs a *type
  parameter*, not mere nesting — a concrete `Dual<Dual<Q>>` by nesting
  may now be expressible and is wave-2 work.
- Nested records *across* generic boundaries and in enum payloads are
  untested here.

## Lesson for the catalog

P005 must be decomposed: concrete nesting works; generic nominals do
not. Keep this negative result so the next campaign does not
re-litigate it.
