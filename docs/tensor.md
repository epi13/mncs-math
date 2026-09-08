# Tensor index maps and data kernels: capabilities and boundary

`src/math/tensor.mncs` implements the integer half of tensor work
completely: positivity-checked shapes, row-major strides, checked
element counts, checked ravel, rank-dispatched unravel, permutation
validation/application, and right-aligned broadcasting with
compatibility observers.

`src/math/tdata.mncs` crosses into movement with fixed-rank
kernels: 4x4 transpose-copy (with transpose-involution as a
metamorphic corpus property), 2x3*3x2 contraction, batched 2x2
matmul, axis-0 reduction, broadcast scalar-plus-vector, valid 1-D
convolution (signal-8 x kernel-3), and strided gather
(`out[j] = s[start + j*stride]`, covering window copies and
even/odd decimation). Shapes are explicit u64 lanes; rank is fixed
per kernel because rank-generic arrays do not exist (P005). The
representation is honest flattened row-major plus lane arithmetic,
and every kernel documents the rank it serves.

## Deliberate boundary

Rank-generic data kernels (contraction, tensordot over
dynamically-shaped operands) are not implemented: with loop bounds
fixed by concrete shapes and no closures/generics, each (rank,
dtype) kernel would be a bespoke unrolled copy. The module documents
exactly where that wall is instead of shipping one unrolled rank and
calling it a tensor library. The per-size copy cost is measured in
`docs/generics.md`.

## Blocked on language changes

- Rank-generic kernels need const-generic shapes or closures over
  axes (**P005**, **P006**).
- Broadcasting data (not just shapes) needs the same plus strided
  views; the `-1` residue-lane convention in `broadcast4` is designed
  to become the validity mask for that future kernel.
- Negative-lane permutations are total (clamped) with input-echo
  residue; a checked index type would turn the contract into a type
  (**P009**, aspirational).
- Strided/ragged gathers with data-dependent bounds need
  data-dependent loop exit for the bound search (**P007**); the
  shipped gather carries a valid-domain precondition instead.
