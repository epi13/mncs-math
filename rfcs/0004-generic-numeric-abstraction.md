# RFC 0004 — generic numeric abstraction

Status: accepted (2026-09-07). Describes what is generic today and what is
structurally blocked (→ P005).

## Decision

Generics in `mncs-math` use exactly what Profile 0.10 provides: explicit
type parameters `<T>` and value parameters `<N: Nat>`, fully applied at
every call site, monomorphized deterministically.

What IS generic today:

- **Containers over element types**: `vec_sum<N>`, folds, sequence min/max,
  tensor index math — written once over `[T; N]` shapes where the element
  operations used are available for every intended `T`… in practice this
  means one copy per element type, because operator requirements cannot be
  named (see below).
- **Sizes over `N: Nat`**: dot products, norms, reductions, tensor
  flatten/reshape validate once for all `N ≤ 64`.
- **Scales over `S: Nat`**: fixed-point ops parameterize the scale as a
  value parameter so `Q8`/`Q16` share source (each instantiation is a
  separate verified function).

What is NOT generic (language pressure P005):

- There are no traits / interfaces / operator constraints, so one `dot`
  cannot span `i64`, rational, fixed, interval, and dual scalars. Each gets
  a same-shaped, separately tested function (`dot_i64`, `dot_fixed`, …).
  This is deliberate duplication with a removal condition, not abstraction
  failure: when the language gains constrained generics, these collapse
  behind one name and this RFC is revised.
- No higher-order functions: `map`/`zip`/`fold` over caller-supplied element
  functions do not exist. Reduction *patterns* are instead provided as
  copyable 6-line traversal templates documented in `docs/generics.md`,
  plus concrete instantiations for every scalar family.

## Rule

Never fake genericity with a comment. If two functions share a name stem
and contract but differ by scalar family, both exist, both are tested, and
both cite this RFC. When P005 clears, the collapse is mechanical and the
corpora stay valid unchanged (same entry names become specializations).
