#!/usr/bin/env python3
"""Dev-time generator for bigintx unrolled schoolbook rows.

Emits the mul_full16 (16 rows) and mul_full32 (32 rows) bodies, which
are then pasted into src/math/bigintx.mncs. The rows are intentionally
unrolled rather than looped: one counted outer loop over rows would
need the row index as a u64 carry plus per-row carry flushes, and the
unrolled row count is itself the compiler-scaling datum (8 -> 16 ->
32 rows). Regenerate with: python3 tools/gen_bigintx.py
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def mul_full(n):
    L = []
    L.append("fn mul_full%d(a: [i64; %d], b: [i64; %d]) -> (result: MulFull%d) {"
             % (n, n, n, n))
    L.append("    let s0: RowState%d = RowState%d { lo: zeros%d(), hi: zeros%d(), carry: 0 };"
             % (n, n, n, n))
    for i in range(n):
        if i == 0:
            L.append("    let r0: RowState%d = mul_row%d(s0, a[0] as u64, 0, b);"
                     % (n, n))
        else:
            L.append("    let r%d: RowState%d = mul_row%d(RowState%d { lo: r%d.lo, hi: h%d, carry: 0 }, a[%d] as u64, %d, b);"
                     % (i, n, n, n, i - 1, i - 1, i, i))
        L.append("    let h%d: [i64; %d] = replace(r%d.hi, %d, (r%d.hi[%d] as u64 +%% r%d.carry) as i64);"
                 % (i, n, i, i, i, i, i))
    L.append("    return MulFull%d { lo: r%d.lo, hi: h%d };" % (n, n - 1, n - 1))
    L.append("}")
    return "\n".join(L)


def shl(n):
    return """fn shl1_%d(a: [i64; %d], carry_in: u64) -> (result: [i64; %d]) {
    iterate i over a carrying st: ShState%d = ShState%d { out: zeros%d(), cy: carry_in } {
        let w: u64 = (a[i] as u64) *%% 2 +%% st.cy;
        next st = ShState%d { out: replace(st.out, i, w as i64), cy: topbit_i64(a[i]) };
    }
    return st.out;
}""" % (n, n, n, n, n, n, n)


def shr(n):
    return """fn shr1_%d(a: [i64; %d], carry_in: u64) -> (result: [i64; %d]) {
    iterate i over a carrying st: ShrState%d = ShrState%d { out: zeros%d(), k: %d, cy: carry_in } {
        let limb: u64 = a[st.k] as u64;
        let w: u64 = limb / 2 +%% st.cy *%% 9223372036854775808;
        let next_k: u64 = st.k -%% 1;
        next st = ShrState%d { out: replace(st.out, st.k, w as i64), k: next_k, cy: limb %% 2 };
    }
    return st.out;
}""" % (n, n, n, n, n, n, n - 1, n)


def add(n):
    return """fn add%drec(a: [i64; %d], b: [i64; %d]) -> (result: AddOut%d) {
    iterate i over a carrying st: AddOut%d = AddOut%d { r: zeros%d(), cy: 0 } {
        let s: CyOut = adc(a[i] as u64, b[i] as u64, st.cy);
        next st = AddOut%d { r: replace(st.r, i, s.w as i64), cy: s.cy };
    }
    return st;
}""" % (n, n, n, n, n, n, n, n)


def sub(n):
    return """fn sub%drec(a: [i64; %d], b: [i64; %d]) -> (result: SubOut%d) {
    iterate i over a carrying st: SubOut%d = SubOut%d { d: zeros%d(), bw: 0 } {
        let m1: u64 = (a[i] as u64) -%% (b[i] as u64);
        let w1: u64 = select(m1 > (a[i] as u64), 1, 0);
        let m2: u64 = m1 -%% st.bw;
        let w2: u64 = select(m2 > m1, 1, 0);
        let bw: u64 = select(w1 == 1 || w2 == 1, 1, 0);
        next st = SubOut%d { d: replace(st.d, i, m2 as i64), bw: bw };
    }
    return st;
}""" % (n, n, n, n, n, n, n, n)


def col(n):
    return """fn col_get%d(lo: [i64; %d], hi: [i64; %d], k: u64) -> (result: u64) {
    if k < %d {
        return lo[k] as u64;
    }
    return hi[k - %d] as u64;
}

fn col_set%d(lo: [i64; %d], hi: [i64; %d], k: u64, v: u64) -> (result: ColPair%d) {
    if k < %d {
        return ColPair%d { lo: replace(lo, k, v as i64), hi: hi };
    }
    return ColPair%d { lo: lo, hi: replace(hi, k - %d, v as i64) };
}""" % (n, n, n, n, n, n, n, n, n, n, n, n, n)


def mul_row(n):
    return """fn mul_row%d(st: RowState%d, ai: u64, ictr: u64, b: [i64; %d]) -> (result: RowState%d) {
    iterate j over b carrying rs: RowState%d = st {
        let k: u64 = ictr + j;
        let w: Wide = mul_wide(ai, b[j] as u64);
        let col: u64 = col_get%d(rs.lo, rs.hi, k);
        let m1: u64 = col +%% rs.carry;
        let c1: u64 = select(m1 < col, 1, 0);
        let m2: u64 = m1 +%% w.lo;
        let c2: u64 = select(m2 < m1, 1, 0);
        let cp: ColPair%d = col_set%d(rs.lo, rs.hi, k, m2);
        next rs = RowState%d { lo: cp.lo, hi: cp.hi, carry: w.hi +%% c1 +%% c2 };
    }
    return rs;
}""" % (n, n, n, n, n, n, n, n, n)


if __name__ == "__main__":
    print(mul_full(16))
    print()
    print(mul_full(32))
