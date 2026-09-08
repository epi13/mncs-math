#!/usr/bin/env python3
"""Dev-time oracle for linalg fixtures (Python exact arithmetic).

Emits tests/tables/linalg.json. Committed corpora remain self-contained;
this script documents how every expected determinant, Cramer coordinate,
rank, substitution result, adjugate entry, and norm was derived.

Two independent paths cross-check every determinant value: a direct exact
computation (Sarrus / Fraction elimination) and a faithful simulation of
the implementation's algorithm (Bareiss with first-nonzero-row pivoting,
checked-op overflow order). Both must agree whenever no overflow occurs.
Overflow expectations are asserted only where every evaluation order must
fail (all-operand-saturating inputs), never on order-sensitive margins.
"""
import json
from fractions import Fraction
from pathlib import Path

M63 = 2**63 - 1
MIN64 = -2**63

HOME = "mncs.math.linalg.v1"
EHOME = "mncs.math.error.v1"

OVF = 2
SING = 4
DIVZ = 1


def I(v):
    return {"i64": v}


def ok(v):
    return {"finite": {"enum": "MathResult", "variant": "Ok",
                       "discriminant": 0, "home": EHOME,
                       "payload": {"value": I(v)}}}


def err(code):
    return {"finite": {"enum": "MathResult", "variant": "Err",
                       "discriminant": 1, "home": EHOME,
                       "payload": {"reason": I(code)}}}


def out2(okvals=None, reason=None):
    return outcome("SolveOut2", ["x0n", "x0d", "x1n", "x1d"], okvals, reason)


def out3(okvals=None, reason=None):
    return outcome("SolveOut3",
                   ["x0n", "x0d", "x1n", "x1d", "x2n", "x2d"],
                   okvals, reason)


def out4(okvals=None, reason=None):
    return outcome("SolveOut4",
                   ["x0n", "x0d", "x1n", "x1d", "x2n", "x2d",
                    "x3n", "x3d"],
                   okvals, reason)


def subout(okvals=None, reason=None):
    return outcome("SubOut3",
                   ["y0n", "y0d", "y1n", "y1d", "y2n", "y2d"],
                   okvals, reason)


def invout(okvals=None, reason=None):
    return outcome("InvOut2",
                   ["a00n", "a00d", "a01n", "a01d",
                    "a10n", "a10d", "a11n", "a11d"],
                   okvals, reason)


def outcome(enum, fields, okvals, reason):
    if reason is not None:
        return {"finite": {"enum": enum, "variant": "Err",
                           "discriminant": 1, "home": HOME,
                           "payload": {"reason": I(reason)}}}
    return {"finite": {"enum": enum, "variant": "Ok",
                       "discriminant": 0, "home": HOME,
                       "payload": {f: I(v)
                                   for f, v in zip(fields, okvals)}}}


# ---- checked i64 scaffolding (mirrors scalar checked-op order) ----

def c_add(a, b):
    v = a + b
    return (True, v) if MIN64 <= v <= M63 else (False, 0)


def c_sub(a, b):
    v = a - b
    return (True, v) if MIN64 <= v <= M63 else (False, 0)


def c_mul(a, b):
    v = a * b
    return (True, v) if MIN64 <= v <= M63 else (False, 0)


def add_ok(a, b):
    return MIN64 <= a + b <= M63


# ---- rational.make mirror (see rational.mncs make) ----

def rmake(num, den):
    if den == 0:
        return ("err", DIVZ)
    neg = (num < 0) != (den < 0)
    man, mad = abs(num), abs(den)
    import math
    g = math.gcd(man, mad)
    nn, dd = man // g, mad // g
    if dd > M63:
        return ("err", OVF)
    if neg:
        if nn > 2**63:
            return ("err", OVF)
        if nn == 2**63:
            return ("ok", (MIN64, dd))
        return ("ok", (-nn, dd))
    if nn > M63:
        return ("err", OVF)
    return ("ok", (nn, dd))


def radd(a, b):
    import math
    an, ad = a
    bn, bd = b
    g = math.gcd(ad, bd)
    d2r, d1r = bd // g, ad // g
    ok1, x = c_mul(an, d2r)
    if not ok1:
        return ("err", OVF)
    ok2, y = c_mul(bn, d1r)
    if not ok2:
        return ("err", OVF)
    ok3, num = c_add(x, y)
    if not ok3:
        return ("err", OVF)
    ok4, den = c_mul(bd, d1r)
    if not ok4:
        return ("err", OVF)
    return rmake(num, den)


def rsub(a, b):
    import math
    an, ad = a
    bn, bd = b
    g = math.gcd(ad, bd)
    d2r, d1r = bd // g, ad // g
    ok1, x = c_mul(an, d2r)
    if not ok1:
        return ("err", OVF)
    ok2, y = c_mul(bn, d1r)
    if not ok2:
        return ("err", OVF)
    ok3, num = c_sub(x, y)
    if not ok3:
        return ("err", OVF)
    ok4, den = c_mul(bd, d1r)
    if not ok4:
        return ("err", OVF)
    return rmake(num, den)


def rmul(a, b):
    import math
    an, ad = a
    bn, bd = b
    g1 = math.gcd(abs(an), abs(bd))
    g2 = math.gcd(abs(bn), abs(ad))
    a1, b2 = an // g1, bd // g1
    c1, d1 = bn // g2, ad // g2
    ok1, num = c_mul(a1, c1)
    if not ok1:
        return ("err", OVF)
    ok2, den = c_mul(d1, b2)
    if not ok2:
        return ("err", OVF)
    return rmake(num, den)


def rrecip(b):
    n, d = b
    if n == 0:
        return ("err", DIVZ)
    return rmake(d, n)


def rdiv(a, b):
    r = rrecip(b)
    if r[0] == "err":
        return r
    return rmul(a, r[1])


# ---- determinants ----

def det2_val(m):
    ok1, ad = c_mul(m[0], m[3])
    if not ok1:
        return ("err", OVF)
    ok2, bc = c_mul(m[1], m[2])
    if not ok2:
        return ("err", OVF)
    ok3, v = c_sub(ad, bc)
    if not ok3:
        return ("err", OVF)
    return ("ok", v)


def det3_val(m):
    terms = [(m[0], m[4], m[8]), (m[1], m[5], m[6]),
             (m[2], m[3], m[7]), (m[2], m[4], m[6]),
             (m[1], m[3], m[8]), (m[0], m[5], m[7])]
    prods = []
    for a, b, c in terms:
        ok1, p = c_mul(a, b)
        if not ok1:
            return ("err", OVF)
        ok2, p = c_mul(p, c)
        if not ok2:
            return ("err", OVF)
        prods.append(p)
    ok1, s = c_add(prods[0], prods[1])
    if not ok1:
        return ("err", OVF)
    ok2, s = c_add(s, prods[2])
    if not ok2:
        return ("err", OVF)
    for p in prods[3:]:
        ok3, s = c_sub(s, p)
        if not ok3:
            return ("err", OVF)
    return ("ok", s)


def det4_truth(m):
    # Independent exact determinant via Fraction elimination.
    n = 4
    a = [[Fraction(m[r * 4 + c]) for c in range(n)] for r in range(n)]
    det = Fraction(1)
    for k in range(n):
        piv = None
        for r in range(k, n):
            if a[r][k] != 0:
                piv = r
                break
        if piv is None:
            return 0
        if piv != k:
            a[k], a[piv] = a[piv], a[k]
            det = -det
        det *= a[k][k]
        for r in range(k + 1, n):
            f = a[r][k] / a[k][k]
            for c in range(k, n):
                a[r][c] -= f * a[k][c]
    assert det.denominator == 1
    return det.numerator


def bareiss4(m):
    # Faithful simulation of the implementation: first-nonzero-row pivot
    # per step, checked-op validity, exactness, sign tracking.
    a = list(m)
    prev = 1
    sign = 1
    for k in range(3):
        p = a[k * 4 + k]
        if p == 0:
            r = next((t for t in range(k, 4) if a[t * 4 + k] != 0), None)
            if r is None:
                return ("zero",)
            for c in range(4):
                a[k * 4 + c], a[r * 4 + c] = a[r * 4 + c], a[k * 4 + c]
            sign = -sign
            p = a[k * 4 + k]
        for i in range(k + 1, 4):
            for j in range(k + 1, 4):
                av, bv, cv = a[i * 4 + j], a[i * 4 + k], a[k * 4 + j]
                ok1, t1 = c_mul(av, p)
                ok2, t2 = c_mul(bv, cv)
                if not (ok1 and ok2):
                    return ("err", OVF)
                ok3, num = c_sub(t1, t2)
                if not ok3:
                    return ("err", OVF)
                if num % prev != 0:
                    raise AssertionError("Bareiss inexact at k=%d" % k)
                if num == MIN64 and prev == -1:
                    return ("err", OVF)
                a[i * 4 + j] = num // prev
        prev = p
    v = a[15] if sign == 1 else -a[15]
    if not MIN64 <= v <= M63:
        return ("err", OVF)
    return ("ok", v)


# ---- Cramer ----

def replace_col(m, b, n, j):
    out = list(m)
    for r in range(n):
        out[r * n + j] = b[r]
    return out


def cramer(m, b, n, detfn):
    d = detfn(m)
    if d[0] == "err":
        return ("err", d[1])
    det = d[1]
    if det == 0:
        return ("err", SING)
    coords = []
    for j in range(n):
        dj = detfn(replace_col(m, b, n, j))
        if dj[0] == "err":
            return ("err", dj[1])
        mk = rmake(dj[1], det)
        if mk[0] == "err":
            return ("err", mk[1])
        coords.append(mk[1])
    return ("ok", coords)


# ---- substitution (b as (num, den) pairs) ----

def sub_fwd(ln, ld, b):
    y0 = rdiv(b[0], (ln[0], ld[0]))
    if y0[0] == "err":
        return y0
    t1 = rsub(b[1], rmul_wrap((ln[3], ld[3]), y0[1]))
    if t1[0] == "err":
        return t1
    y1 = rdiv(t1[1], (ln[4], ld[4]))
    if y1[0] == "err":
        return y1
    t2 = rsub(rsub_wrap(b[2], rmul_wrap((ln[6], ld[6]), y0[1])),
              rmul_wrap((ln[7], ld[7]), y1[1]))
    if t2[0] == "err":
        return t2
    y2 = rdiv(t2[1], (ln[8], ld[8]))
    if y2[0] == "err":
        return y2
    return ("ok", [y0[1], y1[1], y2[1]])


def rmul_wrap(a, b):
    r = rmul(a, b)
    if r[0] == "err":
        raise AssertionError("unexpected rmul failure in oracle case")
    return r[1]


def rsub_wrap(a, b):
    r = rsub(a, b)
    if r[0] == "err":
        raise AssertionError("unexpected rsub failure in oracle case")
    return r[1]


def sub_bwd(un, ud, b):
    y2 = rdiv(b[2], (un[8], ud[8]))
    if y2[0] == "err":
        return y2
    t1 = rsub(b[1], rmul_wrap((un[5], ud[5]), y2[1]))
    if t1[0] == "err":
        return t1
    y1 = rdiv(t1[1], (un[4], ud[4]))
    if y1[0] == "err":
        return y1
    t0 = rsub(rsub_wrap(b[0], rmul_wrap((un[1], ud[1]), y1[1])),
              rmul_wrap((un[2], ud[2]), y2[1]))
    if t0[0] == "err":
        return t0
    y0 = rdiv(t0[1], (un[0], ud[0]))
    if y0[0] == "err":
        return y0
    return ("ok", [y0[1], y1[1], y2[1]])


def pairs(vs):
    return [(v, 1) for v in vs]


# ---- rank4 mirror (Bareiss + full pivoting, first-nonzero row-major) ----

def rank4_val(m):
    a = list(m)
    prev = 1
    piv = 0
    for k in range(3):
        found = None
        for r in range(k, 4):
            for c in range(k, 4):
                if a[r * 4 + c] != 0:
                    found = (r, c)
                    break
            if found:
                break
        if found is None:
            return ("ok", piv)
        r, c = found
        for cc in range(4):
            a[k * 4 + cc], a[r * 4 + cc] = a[r * 4 + cc], a[k * 4 + cc]
        for rr in range(4):
            a[rr * 4 + k], a[rr * 4 + c] = a[rr * 4 + c], a[rr * 4 + k]
        p = a[k * 4 + k]
        for i in range(k + 1, 4):
            for j in range(k + 1, 4):
                ok1, t1 = c_mul(a[i * 4 + j], p)
                ok2, t2 = c_mul(a[i * 4 + k], a[k * 4 + j])
                if not (ok1 and ok2):
                    return ("err", OVF)
                ok3, num = c_sub(t1, t2)
                if not ok3:
                    return ("err", OVF)
                if num % prev != 0:
                    raise AssertionError("rank4 Bareiss inexact")
                if num == MIN64 and prev == -1:
                    return ("err", OVF)
                a[i * 4 + j] = num // prev
        prev = p
        piv += 1
    return ("ok", piv + (1 if a[15] != 0 else 0))


# ---- LU mirror (canonical rational ops, first-nonzero-row pivoting) ----

def lu3_val(m):
    # U, L as (num, den) pair arrays; P as index list; err sticky code.
    # Mirrors lu_row exactly: multiplier residues are (0, 1) on failure
    # (frac_num/frac_den residues), j-loop keeps running, i-loop stops.
    U = [(v, 1) for v in m]
    L = [(1, 1) if i // 3 == i % 3 else (0, 1) for i in range(9)]
    p = [0, 1, 2]
    err = 0
    for k in range(2):
        if err:
            break
        r = next((t for t in range(k, 3) if U[t * 3 + k][0] != 0), None)
        if r is None:
            err = SING
            break
        for c in range(3):
            U[k * 3 + c], U[r * 3 + c] = U[r * 3 + c], U[k * 3 + c]
        for c in range(k):
            L[k * 3 + c], L[r * 3 + c] = L[r * 3 + c], L[k * 3 + c]
        p[k], p[r] = p[r], p[k]
        for i in range(k + 1, 3):
            if err:
                break
            mm = rdiv(U[i * 3 + k], U[k * 3 + k])
            mn, md = mm[1] if mm[0] == "ok" else (0, 1)
            if mm[0] == "err":
                err = mm[1]
            L[i * 3 + k] = (mn, md)
            for j in range(3):
                t = rmul((mn, md), U[k * 3 + j])
                tc = 0 if t[0] == "ok" else t[1]
                tpair = t[1] if t[0] == "ok" else (0, 1)
                n = rsub(U[i * 3 + j], tpair)
                nc = 0 if n[0] == "ok" else n[1]
                npair = n[1] if n[0] == "ok" else (0, 1)
                err = err or tc or nc
                if j >= k:
                    U[i * 3 + j] = npair
    if err == 0 and U[8][0] == 0:
        err = SING
    return {"ln": [v[0] for v in L], "ld": [v[1] for v in L],
            "un": [v[0] for v in U], "ud": [v[1] for v in U],
            "p": p, "err": err}


def SEQ(vs):
    return {"seq": {"of": "i64", "values": vs}}


def lu_case(cid, m, lu, budget):
    assert lu["err"] == 0
    case(cid + "-status", "entry_lu_status3", m, [ok(0)], budget)
    case(cid + "-ln", "entry_lu_Ln3", m, [SEQ(lu["ln"])], budget)
    case(cid + "-ld", "entry_lu_Ld3", m, [SEQ(lu["ld"])], budget)
    case(cid + "-un", "entry_lu_Un3", m, [SEQ(lu["un"])], budget)
    case(cid + "-ud", "entry_lu_Ud3", m, [SEQ(lu["ud"])], budget)
    case(cid + "-p", "entry_lu_P3", m, [SEQ(lu["p"])], budget)


def lu_solve_case(cid, lu, b, cref, budget):
    bp = [b[lu["p"][i]] for i in range(3)]
    y = sub_fwd(lu["ln"], lu["ld"], pairs(bp))
    assert y[0] == "ok", y
    x = sub_bwd(lu["un"], lu["ud"], y[1])
    assert x[0] == "ok", x
    assert cref[0] == "ok", cref
    assert [tuple(v) for v in x[1]] == [tuple(v) for v in cref[1]], (x, cref)
    ns = [v for pr in x[1] for v in pr]
    args = lu["ln"] + lu["ld"] + lu["un"] + lu["ud"] + lu["p"] + b + [1, 1, 1]
    case(cid, "entry_lu_solve3", args, [subout(ns)], budget)


# ---- rank3 ----

def rank3_val(m):
    d = det3_val(m)
    if d[0] == "err":
        return ("err", OVF)
    if d[1] != 0:
        return ("ok", 3)
    found = False
    for r in range(3):
        for c in range(3):
            r0, r1 = (r + 1) % 3, (r + 2) % 3
            c0, c1 = (c + 1) % 3, (c + 2) % 3
            dd = det2_val([m[r0 * 3 + c0], m[r0 * 3 + c1],
                           m[r1 * 3 + c0], m[r1 * 3 + c1]])
            if dd[0] == "err":
                return ("err", OVF)
            if dd[1] != 0:
                found = True
    if found:
        return ("ok", 2)
    if any(v != 0 for v in m):
        return ("ok", 1)
    return ("ok", 0)


# ---- norms ----

def norm1_val(m, n):
    sums = [0] * n
    for q, v in enumerate(m):
        if v == MIN64:
            return ("err", OVF)
        a = abs(v)
        c = q % n
        if not add_ok(sums[c], a):
            return ("err", OVF)
        sums[c] += a
    return ("ok", max(sums))


def norminf_val(m, n):
    sums = [0] * n
    for q, v in enumerate(m):
        if v == MIN64:
            return ("err", OVF)
        a = abs(v)
        r = q // n
        if not add_ok(sums[r], a):
            return ("err", OVF)
        sums[r] += a
    return ("ok", max(sums))


def normmax_val(m):
    if any(v == MIN64 for v in m):
        return ("err", OVF)
    return ("ok", max(abs(v) for v in m))


def frob2_val(m):
    s = 0
    for v in m:
        ok1, sq = c_mul(v, v)
        if not ok1:
            return ("err", OVF)
        ok2, s = c_add(s, sq)
        if not ok2:
            return ("err", OVF)
    return ("ok", s)


# ---- case emission ----

CASES = []


def case(cid, fn, args, expected, budget=4096):
    CASES.append({"id": cid, "fn": fn,
                  "args": [I(a) for a in args],
                  "expect": expected,
                  "budget": budget})


def mcase(cid, fn, args, res, budget=4096):
    if res[0] == "err":
        case(cid, fn, args, [err(res[1])], budget)
    else:
        case(cid, fn, args, [ok(res[1])], budget)


def main():
    global CASES
    B2, B3 = 2048, 16384
    B4, BS = 262144, 524288

    # det2
    mcase("det2-basic", "entry_det2", [1, 2, 3, 4], det2_val([1, 2, 3, 4]), B2)
    mcase("det2-neg", "entry_det2", [5, -2, 7, 3], det2_val([5, -2, 7, 3]), B2)
    mcase("det2-zero", "entry_det2", [2, 4, 1, 2], det2_val([2, 4, 1, 2]), B2)
    mcase("det2-min", "entry_det2", [MIN64, 0, 0, 1],
          det2_val([MIN64, 0, 0, 1]), B2)
    mcase("det2-overflow", "entry_det2", [M63, M63, 0, 1],
          det2_val([M63, M63, 0, 1]), B2)
    mcase("det2-sub-overflow", "entry_det2", [M63, MIN64, -1, 0],
          det2_val([M63, MIN64, -1, 0]), B2)

    # det3
    m3 = [1, 2, 3, 0, 1, 4, 5, 6, 0]
    assert det3_val(m3) == ("ok", 1)
    mcase("det3-basic", "entry_det3", m3, det3_val(m3), B3)
    mcase("det3-identity", "entry_det3", [1, 0, 0, 0, 1, 0, 0, 0, 1],
          ("ok", 1), B3)
    mcase("det3-neg", "entry_det3", [0, 1, 0, 1, 0, 0, 0, 0, 1],
          det3_val([0, 1, 0, 1, 0, 0, 0, 0, 1]), B3)
    mcase("det3-singular", "entry_det3", [1, 2, 3, 4, 5, 6, 7, 8, 9],
          det3_val([1, 2, 3, 4, 5, 6, 7, 8, 9]), B3)
    mall = [M63] * 9
    mcase("det3-overflow", "entry_det3", mall, det3_val(mall), B3)

    # det4 (Bareiss sim + independent truth cross-check)
    eye = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
    assert bareiss4(eye) == ("ok", 1) and det4_truth(eye) == 1
    mcase("det4-identity", "entry_det4", eye, bareiss4(eye), B4)
    dg = [2, 0, 0, 0, 0, 3, 0, 0, 0, 0, 4, 0, 0, 0, 0, 5]
    assert bareiss4(dg) == ("ok", 120) and det4_truth(dg) == 120
    mcase("det4-diag", "entry_det4", dg, bareiss4(dg), B4)
    sw = [0, 1, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
    assert bareiss4(sw) == ("ok", -1) and det4_truth(sw) == -1
    mcase("det4-row-swap", "entry_det4", sw, bareiss4(sw), B4)
    zc = [0, 1, 2, 3, 0, 4, 5, 6, 0, 7, 8, 9, 0, 1, 1, 1]
    assert bareiss4(zc) == ("zero",) and det4_truth(zc) == 0
    case("det4-zero-column", "entry_det4", zc, [ok(0)], B4)
    dep = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]
    assert det4_truth(dep) == 0
    bs = bareiss4(dep)
    assert bs == ("zero",) or (bs[0] == "ok" and bs[1] == 0)
    case("det4-dependent-rows", "entry_det4", dep, [ok(0)], B4)
    tri = [2, 1, 0, 0, 1, 2, 1, 0, 0, 1, 2, 1, 0, 0, 1, 2]
    assert bareiss4(tri) == ("ok", 5) and det4_truth(tri) == 5
    mcase("det4-tridiag", "entry_det4", tri, bareiss4(tri), B4)
    big = [M63] * 16
    assert bareiss4(big)[0] == "err"
    mcase("det4-overflow", "entry_det4", big, bareiss4(big), B4)

    # solve2
    r = cramer([2, 1, 1, 3], [5, 6], 2, det2_val)
    assert r == ("ok", [(9, 5), (7, 5)]), r
    case("solve2-fractions", "entry_solve2", [2, 1, 1, 3, 5, 6],
         [out2([9, 5, 7, 5])], BS)
    r = cramer([1, 2, 3, 4], [5, 6], 2, det2_val)
    assert r[0] == "ok"
    ns = [v for p in r[1] for v in p]
    case("solve2-identity-ish", "entry_solve2", [1, 2, 3, 4, 5, 6],
         [out2(ns)], BS)
    case("solve2-singular", "entry_solve2", [1, 2, 2, 4, 5, 6],
         [out2(reason=SING)], BS)

    # solve3
    r = cramer([1, 0, 0, 0, 1, 0, 0, 0, 1], [4, 5, 6], 3, det3_val)
    assert r == ("ok", [(4, 1), (5, 1), (6, 1)]), r
    case("solve3-identity", "entry_solve3",
         [1, 0, 0, 0, 1, 0, 0, 0, 1, 4, 5, 6], [out3([4, 1, 5, 1, 6, 1])], BS)
    m = [2, 1, 0, 1, 2, 1, 0, 1, 2]
    r = cramer(m, [1, 0, 0], 3, det3_val)
    assert r[0] == "ok"
    ns = [v for p in r[1] for v in p]
    case("solve3-cramer", "entry_solve3", m + [1, 0, 0], [out3(ns)], BS)
    case("solve3-singular", "entry_solve3",
         [1, 2, 3, 4, 5, 6, 7, 8, 9, 1, 0, 0], [out3(reason=SING)], BS)

    # solve4
    r = cramer(dg, [2, 3, 4, 5], 4, lambda m: bareiss_wrap(m))
    assert r == ("ok", [(1, 1), (1, 1), (1, 1), (1, 1)]), r
    case("solve4-diag", "entry_solve4", dg + [2, 3, 4, 5],
         [out4([1, 1, 1, 1, 1, 1, 1, 1])], 2097152)
    r = cramer(tri, [1, 0, 0, 0], 4, lambda m: bareiss_wrap(m))
    assert r[0] == "ok"
    ns = [v for p in r[1] for v in p]
    case("solve4-cramer", "entry_solve4", tri + [1, 0, 0, 0],
         [out4(ns)], 2097152)
    case("solve4-singular", "entry_solve4", dep + [1, 0, 0, 0],
         [out4(reason=SING)], 2097152)

    # rank3
    mcase("rank3-full", "entry_rank3",
          [1, 2, 3, 0, 1, 4, 5, 6, 0], rank3_val(m3), B3)
    mcase("rank3-two", "entry_rank3",
          [1, 2, 3, 4, 5, 6, 7, 8, 9], rank3_val([1, 2, 3, 4, 5, 6, 7, 8, 9]),
          65536)
    mcase("rank3-one", "entry_rank3",
          [0, 0, 0, 0, 5, 0, 0, 0, 0], rank3_val([0, 0, 0, 0, 5, 0, 0, 0, 0]),
          65536)
    mcase("rank3-zero", "entry_rank3", [0] * 9, ("ok", 0), 65536)
    mcase("rank3-overflow", "entry_rank3", mall, rank3_val(mall), 65536)

    # inv2
    r = cramer_inv([4, 7, 2, 6])
    case("inv2-basic", "entry_inv2", [4, 7, 2, 6], [r], BS)
    case("inv2-singular", "entry_inv2", [1, 2, 2, 4],
         [invout(reason=SING)], BS)
    case("inv2-neg-overflow", "entry_inv2", [1, MIN64, 0, 1],
         [invout(reason=OVF)], BS)

    # substitution (right-hand sides as (num, den) pairs; E = ones)
    L = [1, 0, 0, 2, 1, 0, 3, 4, 1]
    D = [1] * 9
    E = [1, 1, 1]
    r = sub_fwd(L, D, pairs([6, 7, 8]))
    assert r == ("ok", [(6, 1), (-5, 1), (10, 1)]), r
    ns = [v for p in r[1] for v in p]
    case("sub-fwd-unit", "entry_sub_fwd3", L + D + [6, 7, 8] + E,
         [subout(ns)], BS)
    Lh = [2, 0, 0, 0, 2, 0, 0, 0, 2]
    r = sub_fwd(Lh, D, pairs([4, 6, 8]))
    assert r == ("ok", [(2, 1), (3, 1), (4, 1)]), r
    ns = [v for p in r[1] for v in p]
    case("sub-fwd-scaled", "entry_sub_fwd3", Lh + D + [4, 6, 8] + E,
         [subout(ns)], BS)
    case("sub-fwd-zero-diag", "entry_sub_fwd3",
         [0, 0, 0, 2, 1, 0, 3, 4, 1] + D + [6, 7, 8] + E,
         [subout(reason=DIVZ)], BS)
    # fractional right-hand side exercises the bn/bd threading
    r = sub_fwd(Lh, D, [(1, 2), (3, 2), (5, 1)])
    assert r == ("ok", [(1, 4), (3, 4), (5, 2)]), r
    ns = [v for p in r[1] for v in p]
    case("sub-fwd-frac-rhs", "entry_sub_fwd3", Lh + D + [1, 3, 5] + [2, 2, 1],
         [subout(ns)], BS)
    U = [2, 1, 1, 0, 2, 1, 0, 0, 2]
    r = sub_bwd(U, D, pairs([8, 6, 4]))
    assert r == ("ok", [(2, 1), (2, 1), (2, 1)]), r
    ns = [v for p in r[1] for v in p]
    case("sub-bwd-basic", "entry_sub_bwd3", U + D + [8, 6, 4] + E,
         [subout(ns)], BS)
    case("sub-bwd-zero-diag", "entry_sub_bwd3",
         [2, 1, 1, 0, 2, 1, 0, 0, 0] + D + [9, 7, 4] + E,
         [subout(reason=DIVZ)], BS)

    # rank4
    mcase("rank4-identity", "entry_rank4", eye, rank4_val(eye), BS)
    mcase("rank4-diag3", "entry_rank4",
          [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0],
          rank4_val([1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0]), BS)
    mcase("rank4-two", "entry_rank4", dep, rank4_val(dep), BS)
    assert rank4_val(dep) == ("ok", 2)
    nc = [0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0]
    assert rank4_val(nc) == ("ok", 2)
    mcase("rank4-noncontig-two", "entry_rank4", nc, ("ok", 2), BS)
    mcase("rank4-one", "entry_rank4",
          [0] * 5 + [7] + [0] * 10, rank4_val([0] * 5 + [7] + [0] * 10), BS)
    mcase("rank4-zero", "entry_rank4", [0] * 16, ("ok", 0), BS)
    mcase("rank4-overflow", "entry_rank4", big, rank4_val(big), BS)
    assert rank4_val(big)[0] == "err"

    # LU at 3x3
    BLU = 1048576
    eye3 = [1, 0, 0, 0, 1, 0, 0, 0, 1]
    lu_eye = lu3_val(eye3)
    assert lu_eye["err"] == 0 and lu_eye["p"] == [0, 1, 2]
    lu_case("lu-identity", eye3, lu_eye, BLU)
    dg3 = [2, 0, 0, 0, 3, 0, 0, 0, 4]
    lu_dg = lu3_val(dg3)
    assert lu_dg["err"] == 0 and lu_dg["ln"] == eye3
    lu_case("lu-diag", dg3, lu_dg, BLU)
    sw3 = [0, 1, 0, 1, 0, 0, 0, 0, 1]
    lu_sw = lu3_val(sw3)
    assert lu_sw["err"] == 0 and lu_sw["p"] == [1, 0, 2], lu_sw
    assert lu_sw["ln"] == eye3 and lu_sw["un"] == eye3
    lu_case("lu-row-swap", sw3, lu_sw, BLU)
    mm = [2, 1, 0, 1, 2, 1, 0, 1, 2]
    lu_mm = lu3_val(mm)
    assert lu_mm["err"] == 0, lu_mm
    assert lu_mm["ln"] == [1, 0, 0, 1, 1, 0, 0, 2, 1], lu_mm["ln"]
    assert lu_mm["ld"] == [1, 1, 1, 2, 1, 1, 1, 3, 1], lu_mm["ld"]
    assert lu_mm["un"] == [2, 1, 0, 0, 3, 1, 0, 0, 4], lu_mm["un"]
    assert lu_mm["ud"] == [1, 1, 1, 1, 2, 1, 1, 1, 3], lu_mm["ud"]
    lu_case("lu-multipliers", mm, lu_mm, BLU)
    sing3 = [1, 2, 3, 4, 5, 6, 7, 8, 9]
    lu_sg = lu3_val(sing3)
    assert lu_sg["err"] == SING, lu_sg
    case("lu-status-singular", "entry_lu_status3", sing3, [err(SING)], BLU)
    ovf3 = [1, M63, 0, M63, 0, 0, 0, 0, 1]
    lu_ov = lu3_val(ovf3)
    assert lu_ov["err"] == OVF, lu_ov
    case("lu-status-overflow", "entry_lu_status3", ovf3, [err(OVF)], BLU)
    # solve-via-LU must agree with Cramer on both factor shapes
    lu_solve_case("lu-solve-multipliers", lu_mm, [3, 3, 3],
                  cramer(mm, [3, 3, 3], 3, det3_val), BLU)
    lu_solve_case("lu-solve-swapped", lu_sw, [5, 6, 7],
                  cramer(sw3, [5, 6, 7], 3, det3_val), BLU)
    # k=1 row swap with distinct L multipliers makes the L-swap observable
    ls = [2, 0, 0, 1, 0, 1, 3, 1, 0]
    lu_ls = lu3_val(ls)
    assert lu_ls["err"] == 0, lu_ls
    assert lu_ls["p"] == [0, 2, 1], lu_ls["p"]
    assert (lu_ls["ln"][3], lu_ls["ld"][3]) == (3, 2), lu_ls["ln"]
    assert (lu_ls["ln"][6], lu_ls["ld"][6]) == (1, 2), lu_ls["ln"]
    lu_case("lu-lswap", ls, lu_ls, BLU)
    lu_solve_case("lu-solve-lswap", lu_ls, [4, 5, 6],
                  cramer(ls, [4, 5, 6], 3, det3_val), BLU)
    # out-of-range caller permutation fails cleanly (shape_mismatch = 5)
    badp = lu_mm["ln"] + lu_mm["ld"] + lu_mm["un"] + lu_mm["ud"] \
        + [0, 1, 9] + [4, 5, 6] + [1, 1, 1]
    case("lu-solve-bad-perm", "entry_lu_solve3", badp,
         [subout(reason=5)], BLU)

    # norms (1/inf differ on purpose: col sums 12/15/18, row sums 6/15/24)
    nm = [1, -2, 3, -4, 5, -6, 7, -8, 9]
    mcase("norm1-basic", "entry_norm1_9", nm, norm1_val(nm, 3), B3)
    mcase("norm-inf-basic", "entry_norm_inf_9", nm, norminf_val(nm, 3), B3)
    mcase("norm-max-basic", "entry_norm_max_9", nm, normmax_val(nm), B3)
    mcase("frob2-basic", "entry_frob2_9", [1, 2, 3, 0, 0, 0, 0, 0, 0],
          frob2_val([1, 2, 3, 0, 0, 0, 0, 0, 0]), B3)
    mcase("norm1-overflow", "entry_norm1_9", mall, norm1_val(mall, 3), B3)
    mcase("norm-max-min", "entry_norm_max_9", [MIN64] + [0] * 8,
          ("err", OVF), B3)
    m16 = [1, -2, 3, -4, 5, -6, 7, -8, 9, 1, 1, 1, 1, 1, 1, 1]
    mcase("norm1-16", "entry_norm1_16", m16, norm1_val(m16, 4), B3)
    mcase("norm-inf-16", "entry_norm_inf_16", m16, norminf_val(m16, 4), B3)
    mcase("norm-max-16", "entry_norm_max_16", m16, normmax_val(m16), B3)
    mcase("frob2-16", "entry_frob2_16", m16, frob2_val(m16), B3)

    table = {"module": HOME, "name": "linalg-exact",
             "cases": CASES}
    out = Path(__file__).resolve().parent.parent / "tests" / "tables" \
        / "linalg.json"
    out.write_text(json.dumps(table, indent=1) + "\n")
    print("wrote %s (%d cases)" % (out.name, len(CASES)))


def bareiss_wrap(m):
    r = bareiss4(m)
    if r[0] == "zero":
        return ("ok", 0)
    return r


def cramer_inv(m):
    d = det2_val(m)
    if d[0] == "err":
        return invout(reason=d[1])
    det = d[1]
    if det == 0:
        return invout(reason=SING)
    coords = []
    for num in (m[3], -m[1] if m[1] != MIN64 else None,
                -m[2] if m[2] != MIN64 else None, m[0]):
        if num is None:
            return invout(reason=OVF)
        mk = rmake(num, det)
        if mk[0] == "err":
            return invout(reason=mk[1])
        coords.append(mk[1])
    flat = [v for p in coords for v in p]
    return invout(flat)


if __name__ == "__main__":
    main()
