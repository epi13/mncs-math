# repro: call expressions are ungrammatical as a `next` state (MNP064)

- Toolchain: mncs-language @ `26778de`. Profile 0.10.
- Backend: none (fails `source-study`).

## Exact command

```bash
$MNCS_BIN source-study case.mncs --node-id probe
```

## Actual behavior

`next st = bump(st, c[i]);` fails with `MNP064: expected expression`
at the call, cascading into MNP100/MNP061/MNP101-104 recovery noise.
The same holds for a `select(...)` call nested as a record field
inside `next` (`next st = DegSt { best: select(...), ... }`, also
MNP064).

Refinement from the probe matrix (`p34`/`p35`/`p36_selectnext`):
calls in `next` position elaborate with variable, projection, and
`select` arguments (`next st = idf(st)`, `next st = mk(st.a, st.b)`,
`next cur = div_micro2(cur, div)`, and record literals containing
`select(...)` all pass). What MNP064 rejects, precisely, is an
*over-domain loop index* inside a call argument
(`next st = bump(st, c[i])` fails; the `up_to` index in
`next s = shuffle_step(s, k)` and carry projections in
`next pp = rank_pivot_next(m[pp.q], ...)` pass). So one narrow
anti-case survives: over-index capture inside `next`-position calls.

(Cautionary note: an early version of this file also blamed
`select(...)` in `next` and unary `-1` initializers were a separate
real gap. Re-probing showed the `select` failure was cascade noise
from the `-1` initializer further up — error recovery misattributes
spans. Always re-probe each blamed construct in isolation.)

## Desired semantics

Either admit over-indices in `next`-position call arguments, or
document the single anti-case with its cost: pre-bind indexed values
with `let` before the call (see `poly.mncs` `pdegree`).

## Affected math workloads

`poly.mncs` `pdegree` (rewritten with let-bound `select`), any future
stateful traversal with a non-trivial step function (Newton
carries, elimination pivots, NTT butterflies that need a helper).

## Workaround in use

Let-bind call results above `next` and construct the carried record
literally (`bigint.mncs` `mul_row2` precedent). Cost: ~2 extra lines
per call in the step, and steps cannot be named helpers.

## Companion quirk (same file family)

Unary minus is ungrammatical in a carry *initializer*
(`DegSt { best: -1, ... }`, MNP064); the `-1` sentinel must be spelled
`0 - 1`. Plain `-` in function bodies is fine.
