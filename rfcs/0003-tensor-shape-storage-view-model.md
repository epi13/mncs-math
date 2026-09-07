# RFC 0003 — tensor shape / storage / view model

Status: accepted (2026-09-07).

## Decision

Tensors are explicit metadata plus contiguous storage — no hidden strides,
no views that alias mutably (the language has no mutable aliasing at all).

- **Storage**: one exact sequence `[i64; N]` (element type widens to
  fixed/rational payloads in later tranches; this run standardizes i64 and
  fixed-point element tensors), row-major (C-order), multiproduct index
  `flat = Σ index[k] * stride[k]`, `stride[k] = Π_{j>k} shape[j]`.
- **Shape**: exact sequence `[u64; R]` with rank `R ≤ 4` carried as a `Nat`
  generic; static mismatch is an elaboration error, dynamic mismatch is a
  `MathError` reason (`shape_mismatch`, `broadcast_incompatible`).
- **Views/slices**: bounded views `[T; up_to N]` with explicit
  `(offset, length)` — always a copy-free borrow of immutable cells with a
  runtime length; reshape is a metadata-only re-description requiring equal
  element count (`reshape` returns a fallible enum).
- **Broadcasting**: NumPy-style right-aligned rules, implemented as an
  explicit index-mapping function (no implicit expansion in storage);
  incompatible shapes fail with a reason, never silently.
- **Contraction groundwork**: `matmul` is the rank-2 contraction;
  general `contract(a, b, axes)` is specified for rank ≤ 3 with bounded
  helper-call loops (nesting budget: at most 2 levels per function, deeper
  nests become helper calls — Profile 0.11, see P004).

## Deliberate limits (this run)

- Element type i64 (+ fixed-point twins where cheap); no float tensors
  until P001 clears.
- Rank ≤ 4, total elements ≤ 64 per tensor (sequence ceiling → P003).
- No sparse, no lazy, no autograd tapes (forward duals only, RFC 0007).

## Future hooks (not implemented)

Strided (non-contiguous) descriptors, zero-copy transpose flags, backend
specialization markers (`contiguous`, `aligned(N)` intents) are reserved
names documented in `docs/tensor-model.md`; introducing them needs no
breaking change because reshape/transpose already return descriptors.
