# repro: concrete array payloads in enum variants are rejected (MNE171)

- Toolchain: mncs-language @ `26778de`. Profile 0.10.
- Backend: none (fails elaboration in `source-study`).

## Exact command

```bash
$MNCS_BIN source-study case.mncs --node-id probe
```

## Actual behavior

```
MNE171 error: variant payload field type does not name a supported
  scalar, finite, or declared record type
MNE172 error: finite constructor names a payload field the variant
  does not declare   (cascade)
```

`enum ArrOut { Ok { v: [i64; 2] }, ... }` is refused even though the
array type is concrete and fixed-size. Scalar and (flat) record
payloads elaborate fine.

## Desired semantics

Fixed-size array payloads in variants, so fallible array kernels can
return values or reasons through one type.

## Affected math workloads

Same as `../generic-enum-rejected`: checked array kernels across
`vector`/`matrix`/`linalg`/`tensor`.

## Workaround in use

Bool pre-check + wrapping twin. See `../generic-enum-rejected`.
