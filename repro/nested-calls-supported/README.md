# Negative result: nested calls DO elaborate (retracts MNE133/135 claim)

- Toolchain: mncs-language @ `26778de`. Profile 0.10.

## Exact command

```bash
$MNCS_BIN source-study case.mncs --node-id probe   # exit 0, no errors
```

## What was claimed before

The first-campaign catalog said "`sub(x, mul(a, b))` is rejected;
every composition must be flattened through `let` + match-split
helpers. Rational-heavy code pays a ~3-4x helper multiplier for this
alone", citing MNE133/MNE135.

## What the probe shows

`case.mncs` nests `sub2(x, mul2(a, b))` in four positions — `select`
arm, record field, array literal, and (in the companion probe
`p36_nestedcall`) direct call argument and return — and elaborates
with zero errors. MNE133 in the current toolchain means "call
argument *type* does not match the callee parameter" (observed when
passing an `up_to` index where `i64` was declared); it is a type
error, not a nesting ban. The `replace(replace(...))` nesting in
`matrix.mncs` `swap_rows4` is further in-repo proof.

## What remains restricted (separately)

The `next`-state argument grammar only (`../next-state-call-rejected`,
MNP064): no subscripts or nested calls inside `next` arguments.

## Lesson for the catalog

The "~3-4x helper multiplier" cost attributed to MNE133/135 does not
reproduce. Match-split helpers are still load-bearing for *enums*
(scrutinee discipline), but plain call composition is free. Keep this
negative result so the cost claim is not reintroduced.
