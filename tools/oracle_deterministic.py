#!/usr/bin/env python3
"""Dev-time oracle for deterministic fixtures (Python exact arithmetic).

Emits tests/tables/deterministic.json. splitmix64, Lemire-high,
Fisher-Yates, and FNV-1a are mirrored bit-for-bit in Python integers
masked to 64 bits; any mismatch with the MNCS implementation is a bug
in one of the two, investigated before freezing.
"""
import json
from pathlib import Path

M64 = 2**64 - 1

HOME = "mncs.math.deterministic.v1"

CASES = []


def U(v):
    return {"u64": v}


def I(v):
    return {"i64": v}


def USEQ(vs):
    return {"seq": {"of": "u64", "values": vs}}


def SEQ(vs):
    return {"seq": {"of": "i64", "values": vs}}


def case(cid, fn, args, expected, budget=32768):
    CASES.append({"id": cid, "fn": fn, "args": args,
                  "expect": expected, "budget": budget})


def splitmix(st):
    z = (st + 0x9E3779B97F4A7C15) & M64
    a = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & M64
    b = ((a ^ (a >> 27)) * 0x94D049BB133111EB) & M64
    return z, b ^ (b >> 31)


def lemire_high(x, bound):
    return ((x * bound) >> 64) & M64


def shuffle8(x, seed):
    a = list(x)
    st = seed
    for k in range(7):
        st, r = splitmix(st)
        j = k + lemire_high(r, 8 - k)
        a[k], a[j] = a[j], a[k]
    return a, st


def fnv1a_8(x):
    h = 14695981039346656037
    for v in x:
        h = ((h ^ (v & M64)) * 1099511628211) & M64
    return h


def main():
    # splitmix64 stream from seed 0 (reference vectors)
    st, o = splitmix(0)
    assert (st, o) == (0x9E3779B97F4A7C15, 0xE220A8397B1DCDAF), (hex(st), hex(o))
    case("splitmix-seed0", "entry_splitmix", [U(0)], [USEQ([st, o])])
    st2, o2 = splitmix(st)
    case("splitmix-step2", "entry_splitmix", [U(st)], [USEQ([st2, o2])])
    st3, o3 = splitmix(123456789)
    case("splitmix-seedN", "entry_splitmix", [U(123456789)],
         [USEQ([st3, o3])])

    # lemire_high unit checks (hand-verifiable halves)
    assert lemire_high(2**64 - 1, 2**64 - 1) == 2**64 - 2
    case("lemire-max", "entry_lemire_high",
         [U(2**64 - 1), U(2**64 - 1)], [U(2**64 - 2)])
    assert lemire_high(2**64 - 1, 7) == 6
    case("lemire-bound7", "entry_lemire_high", [U(2**64 - 1), U(7)],
         [U(6)])
    assert lemire_high(0, 100) == 0
    case("lemire-zero", "entry_lemire_high", [U(0), U(100)], [U(0)])
    assert lemire_high(2**63, 2) == 1
    case("lemire-half", "entry_lemire_high", [U(2**63), U(2)],
         [U(1)])
    _, r0 = splitmix(42)
    assert lemire_high(r0, 10) == ((r0 * 10) >> 64)
    case("lemire-stream", "entry_lemire_high", [U(r0), U(10)],
         [U((r0 * 10) >> 64)])
    # cross-checks against exact bignum arithmetic (carry-bit paths)
    for i, (xx, bb) in enumerate([(2**64 - 1, 2**64 - 2),
                                  (2**63 + 12345, 2**63 + 6789),
                                  (0xFFFFFFFFFFFFFFFF, 0x100000001),
                                  (0x123456789ABCDEF0, 0xFEDCBA987654321)]):
        assert lemire_high(xx, bb) == ((xx * bb) >> 64)
        case("lemire-x%d" % i, "entry_lemire_high", [U(xx), U(bb)],
             [U((xx * bb) >> 64)])

    # bounded + pow2 draws (state threading asserted)
    st, r = splitmix(7)
    assert lemire_high(r, 6) == ((r * 6) >> 64)
    case("bounded-basic", "entry_uniform_bounded", [U(7), U(6)],
         [USEQ([st, (r * 6) >> 64])])
    case("bounded-one", "entry_uniform_bounded", [U(7), U(1)],
         [USEQ([st, 0])])
    st, r = splitmix(99)
    case("pow2-8", "entry_uniform_pow2", [U(99), U(8)],
         [USEQ([st, r >> 56])])
    case("pow2-1", "entry_uniform_pow2", [U(99), U(1)],
         [USEQ([st, r >> 63])])

    # shuffle: permutation property + exact order
    xs = [10, 20, 30, 40, 50, 60, 70, 80]
    perm, _ = shuffle8(xs, 2026)
    assert sorted(perm) == sorted(xs)
    case("shuffle-basic", "entry_shuffle8",
         [I(v) for v in xs] + [U(2026)], [SEQ(perm)])
    perm0, _ = shuffle8(xs, 0)
    assert sorted(perm0) == sorted(xs)
    case("shuffle-seed0", "entry_shuffle8",
         [I(v) for v in xs] + [U(0)], [SEQ(perm0)])

    # fnv1a over limbs
    h = fnv1a_8(xs)
    case("fnv-basic", "entry_fnv1a_8", [I(v) for v in xs], [U(h)])
    h0 = fnv1a_8([0] * 8)
    case("fnv-zeros", "entry_fnv1a_8", [I(0)] * 8, [U(h0)])
    hn = fnv1a_8([-1, -2, 3, -4, 5, -6, 7, -8])
    case("fnv-neg", "entry_fnv1a_8",
         [I(v) for v in [-1, -2, 3, -4, 5, -6, 7, -8]], [U(hn)])

    table = {"module": HOME, "name": "deterministic-streams",
             "cases": CASES}
    out = Path(__file__).resolve().parent.parent / "tests" / "tables" \
        / "deterministic.json"
    out.write_text(json.dumps(table, indent=1) + "\n")
    print("wrote %s (%d cases)" % (out.name, len(CASES)))


if __name__ == "__main__":
    main()
