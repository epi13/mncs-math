# Expected record: `next`-state calls rejected at parse

## `source-study case.mncs`

- Exit nonzero. First diagnostic (verbatim code): `MNP064` (expected
  expression) at the `bump(st, c[i])` call in `next` position,
  followed by MNP100/MNP061/MNP101-104 cascade.
- No backend reached.
