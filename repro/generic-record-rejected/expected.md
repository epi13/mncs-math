# Expected record: generic records rejected at parse

## `source-study case.mncs`

- Exit nonzero. Diagnostics (verbatim codes):
  `MNP123` (expected '{' after record name), `MNP127`, `MNP128`.
- No backend reached. Any profile `>= 0.6` behaves the same; the
  parameter list is not grammatical on records or on finite (enum)
  types (see `../generic-enum-rejected`).
