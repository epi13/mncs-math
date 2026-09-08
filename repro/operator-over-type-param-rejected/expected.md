# Expected record: operators over type parameters rejected

## `source-study case.mncs`

- Exit nonzero. Diagnostic (verbatim code): `MNE120` (arithmetic
  operands must have an integer type).
- No backend reached. The container/projection use of `T` is *not*
  the blocker; operator application is.
