# Determinism: what is pinned and why it matters

`src/math/deterministic.mncs` makes determinism a tested property:
splitmix64 matches the published reference vector (`e220a8397b1dcdaf`
for seed 0), the Lemire high-word map is proved against bignum
arithmetic on carry-bit paths (including `(2^64-1)^2`), shuffles pin
exact permutations, and FNV-1a pins hashes — identically on every
backend. Any backend divergence in these values is a backend
soundness bug, and this module is the tripwire.

## Notes

- `lemire_high` carries a bound proof in comments: 16-bit limbs keep
  every partial product below 2^32, and the carry's rounding bit is
  computed by comparison, never by forming the overflowing sum.
- Bounded draws have Lemire's residual bias (documented, not hidden);
  unbiased rejection sampling needs data-dependent looping (**P007**).
- Power-of-two draws take the high bits; seed threading is explicit
  (`Rng` records), so streams are reproducible by construction.
