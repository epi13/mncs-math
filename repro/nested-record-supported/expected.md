# Expected record: nested records elaborate cleanly

## `source-study case.mncs`

- Exit 0. Zero diagnostics. Nested declaration, nested construction,
  deep projection, and operators over deep projections all elaborate.
- This is a *negative* reproducer: it pins behavior that must keep
  working, and corrects the first-campaign "records cannot nest" claim.
