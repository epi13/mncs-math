# Expected record: nested calls elaborate cleanly

## `source-study case.mncs`

- Exit 0. Zero errors (only standard CMP301 obligations): nested
  calls in `select` arms, record fields, and array literals all
  elaborate.
- This is a *negative* reproducer: it pins composition behavior that
  must keep working, and retracts the first-campaign MNE133/135
  nesting-ban claim.
