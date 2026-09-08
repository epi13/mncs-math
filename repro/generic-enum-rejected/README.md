# repro: generic enums are rejected at parse (`enum Maybe<T>`)

- Toolchain: mncs-language @ `26778de`. Profile 0.10.
- Backend: none (fails `source-study`).

## Exact command

```bash
$MNCS_BIN source-study case.mncs --node-id probe
```

## Actual behavior

```
MNP072 error: expected '{' after finite type name
MNP074 error: expected '}' after finite variants
MNP075 error: finite type requires at least one variant
```

Same class as `../generic-record-rejected`: nominal generic aggregates
are not grammatical. In addition, even *concrete* array payloads are
refused at elaboration (`../array-enum-payload-rejected`, MNE171), so
enums today carry scalar/record payloads only.

## Desired semantics

`enum Maybe<T> { Nothing, Just { v: T } }` and concrete
array-payload variants, enabling fallible array kernels to return
structured errors instead of bool side-channels.

## Affected math workloads

`vector.mncs` validate-then-compute bool folds (`dot_overflows`,
`add_overflows` document that "there are no array-valued error enums
because enum payloads are scalar"); every array kernel that must
signal *why* it refused.

## Workaround in use

Bool pre-check + wrapping twin (`dot_overflows` then `dot_wrap`).
Cost: two traversals per checked kernel and no reason code on the
array path.
