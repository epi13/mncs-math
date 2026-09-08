# Expected record: record carry over u64 domain rejected

## `source-study case.mncs`

- Exit nonzero. `rec_i64_over_u64` fails with `MNB101` on its
  traversal domain; `rec_u64_over_i64` in the same file elaborates
  (only the standard CMP301 obligations).
- No backend reached. The asymmetry is the finding: identical shapes,
  only the domain element type differs.
