# Tensor index maps: capabilities and boundary

`src/math/tensor.mncs` implements the integer half of tensor work
completely: positivity-checked shapes, row-major strides, checked
element counts, checked ravel, rank-dispatched unravel, permutation
validation/application, and right-aligned broadcasting with
compatibility observers.

## Deliberate boundary

Rank-generic data kernels (contraction, tensordot over
dynamically-shaped operands) are not implemented: with loop bounds
fixed by concrete shapes and no closures/generics, each (rank,
dtype) kernel would be a bespoke unrolled copy. The module documents
exactly where that wall is instead of shipping one unrolled rank and
calling it a tensor library. The fixed-rank transpose-copy originally
planned was cut for the same reason: without a contraction to feed,
it proves nothing the index maps do not already pin.

## Blocked on language changes

- Rank-generic kernels need const-generic shapes or closures over
  axes (**P005**, **P006**).
- Broadcasting data (not just shapes) needs the same plus strided
  views; the `-1` residue-lane convention in `broadcast4` is designed
  to become the validity mask for that future kernel.
- Negative-lane permutations are total (clamped) with input-echo
  residue; a checked index type would turn the contract into a type
  (**P009**, aspirational).
