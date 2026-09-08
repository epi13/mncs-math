# repro: record carry over a `[u64; _]` traversal domain is rejected (MNB101)

- Toolchain: mncs-language @ `26778de`. Profile 0.10.
- Backend: none (fails elaboration in `source-study`).

## Exact command

```bash
$MNCS_BIN source-study case.mncs --node-id probe
```

## Actual behavior

`case.mncs` holds two functions. `rec_u64_over_i64` (record carry
over `[i64; N]`) elaborates; `rec_i64_over_u64` (record carry over
`[u64; N]`) fails with:

```
MNB101 error: functions[0].body.bounded_iterations[0].domain:
  sequence traversal domain must name a resolvable element type
```

The empirically complete rule from the probe matrix (each cell an
independent `source-study`):

| domain \ carry | i64 scalar | u64 scalar | record |
|---|---|---|---|
| `[i64; N]` param | ok | MNB101 | ok |
| `[i64; k]` let-bound | ok | MNB101 | ok |
| `[u64; N]` param | MNB101 | ok | MNB101 |
| `[u64; k]` let-bound | (untested) | ok | (untested, presumed MNB101) |

i.e. a scalar carry must match the domain element type exactly, and a
record carry additionally requires an i64 domain. The u64 side was
probed with all-u64 records too (`MEvSt { acc: u64, pw: u64 }` over
`[u64; N]` fails), so it is not a field-type mismatch: composite
state over u64 lanes is simply unresolvable.

## Desired semantics

Traversal domains and carry types should compose orthogonally: any
carry over any element type, with the index remaining abstract.

## Affected math workloads

`modular.mncs` `mpoly_eval`: the natural signature
`(c: [u64; N], x, m)` is inexpressible, so the function takes a
phantom `[i64; N]` index ladder purely to give the traversal an i64
domain. Every u64-lane stateful kernel pays one dummy parameter plus
a literal ladder at each call site. u64 bigint limbs, hashes, and
modular accumulators are all affected.

## Workaround in use

Phantom index-domain parameters (`mpoly_eval<N>(c, idx, x, m)`),
or i64-domain traversals with u64 lane projection. Cost: one extra
parameter per stateful u64 kernel and literal ladders per call site.
