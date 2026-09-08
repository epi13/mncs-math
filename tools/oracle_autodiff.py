#!/usr/bin/env python3
"""Dev-time oracle for autodiff fixtures (Python exact arithmetic).

Emits tests/tables/autodiff.json. DualZ expectations are checked-i64
computations; DualQ expectations reuse the rational mirrors from
oracle_linalg (imported, not duplicated).
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from oracle_linalg import rmake, radd, rsub, rmul, rdiv, rmake as _rm  # noqa

M63 = 2**63 - 1
MIN64 = -2**63

HOME = "mncs.math.autodiff.v1"

OVF = 2

CASES = []


def I(v):
    return {"i64": v}


def zout(x=None, dx=None, reason=None):
    if reason is not None:
        return {"finite": {"enum": "DualZOut", "variant": "Err",
                           "discriminant": 1, "home": HOME,
                           "payload": {"reason": I(reason)}}}
    return {"finite": {"enum": "DualZOut", "variant": "Ok",
                       "discriminant": 0, "home": HOME,
                       "payload": {"x": I(x), "dx": I(dx)}}}


def qout(xn=None, xd=None, yn=None, yd=None, reason=None):
    if reason is not None:
        return {"finite": {"enum": "DualQOut", "variant": "Err",
                           "discriminant": 1, "home": HOME,
                           "payload": {"reason": I(reason)}}}
    return {"finite": {"enum": "DualQOut", "variant": "Ok",
                       "discriminant": 0, "home": HOME,
                       "payload": {"xn": I(xn), "xd": I(xd),
                                   "yn": I(yn), "yd": I(yd)}}}


RAT = "mncs.math.rational.v1"
DIVZ = 1

C_CUBIC = [-5, -2, 0, 1]   # c(x) = x^3 - 2x - 5
C_DERIV = [-2, 0, 3, 0]    # c'(x) = 3x^2 - 2


def hout(xn=None, xd=None, fvn=None, fvd=None, reason=None):
    if reason is not None:
        return {"finite": {"enum": "HalleyOut", "variant": "Err",
                           "discriminant": 1, "home": HOME,
                           "payload": {"reason": I(reason)}}}
    return {"finite": {"enum": "HalleyOut", "variant": "Ok",
                       "discriminant": 0, "home": HOME,
                       "payload": {"xn": I(xn), "xd": I(xd),
                                   "fvn": I(fvn), "fvd": I(fvd)}}}


def fout(num=None, den=None, reason=None):
    if reason is not None:
        return {"finite": {"enum": "FracOutcome", "variant": "Err",
                           "discriminant": 1, "home": RAT,
                           "payload": {"reason": I(reason)}}}
    return {"finite": {"enum": "FracOutcome", "variant": "Ok",
                       "discriminant": 0, "home": RAT,
                       "payload": {"num": I(num), "den": I(den)}}}


def halley_step(t):
    """Mirror entry_halley op-for-op: (status, (x1n, x1d, fvn, fvd))."""
    from oracle_linalg import radd, rsub, rmul, rdiv
    f = qpoly3(C_CUBIC, (t, (1, 1)))
    if f[0] == "err":
        return f
    (fx, fy) = f[1]
    d = qpoly3(C_DERIV, (t, (1, 1)))
    if d[0] == "err":
        return d
    (fpx, fpp) = d[1]
    assert fpx == fy, (fpx, fy)  # c-eval tangent == c'-eval value
    n1 = rmul(fx, fpx)
    if n1[0] == "err":
        return n1
    num = radd(n1[1], n1[1])
    if num[0] == "err":
        return num
    p2 = rmul(fpx, fpx)
    if p2[0] == "err":
        return p2
    d1 = radd(p2[1], p2[1])
    if d1[0] == "err":
        return d1
    q1 = rmul(fx, fpp)
    if q1[0] == "err":
        return q1
    den = rsub(d1[1], q1[1])
    if den[0] == "err":
        return den
    step = rdiv(num[1], den[1])
    if step[0] == "err":
        return step
    x1 = rsub(t, step[1])
    if x1[0] == "err":
        return x1
    r = qpoly3(C_CUBIC, (x1[1], (1, 1)))
    if r[0] == "err":
        return r
    return ("ok", (x1[1][0], x1[1][1], r[1][0][0], r[1][0][1]))


def d2cubic(t):
    """Mirror entry_d2cubic: (status, (fppn, fppd))."""
    d = qpoly3(C_DERIV, (t, (1, 1)))
    if d[0] == "err":
        return d
    return ("ok", d[1][1])


def case(cid, fn, args, expected, budget=32768):
    CASES.append({"id": cid, "fn": fn,
                  "args": [I(a) for a in args],
                  "expect": expected, "budget": budget})


def fits(v):
    return MIN64 <= v <= M63


def zmul(a, b):
    ax, ad = a
    bx, bd = b
    x = ax * bx
    p1 = ax * bd
    p2 = ad * bx
    if not (fits(x) and fits(p1) and fits(p2)):
        return ("err", OVF)
    dx = p1 + p2
    if not fits(dx):
        return ("err", OVF)
    return ("ok", (x, dx))


def zpoly3(c, t):
    t2 = zmul(t, t)
    if t2[0] == "err":
        return t2
    t3 = zmul(t2[1], t)
    if t3[0] == "err":
        return t3
    acc = (c[0], 0)
    for cc, tt in ((c[1], t), (c[2], t2[1]), (c[3], t3[1])):
        m = zmul((cc, 0), tt)
        if m[0] == "err":
            return m
        s = (acc[0] + m[1][0], acc[1] + m[1][1])
        if not (fits(s[0]) and fits(s[1])):
            return ("err", OVF)
        acc = s
    return ("ok", acc)


def qmul(a, b):
    (axn, axd), (ayn, ayd) = a
    (bxn, bxd), (byn, byd) = b
    x = rmul((axn, axd), (bxn, bxd))
    if x[0] == "err":
        return x
    p1 = rmul((axn, axd), (byn, byd))
    if p1[0] == "err":
        return p1
    p2 = rmul((ayn, ayd), (bxn, bxd))
    if p2[0] == "err":
        return p2
    y = radd(p1[1], p2[1])
    if y[0] == "err":
        return y
    return ("ok", (x[1], y[1]))


def qdiv(a, b):
    (axn, axd), (ayn, ayd) = a
    (bxn, bxd), (byn, byd) = b
    x = rdiv((axn, axd), (bxn, bxd))
    if x[0] == "err":
        return x
    n1 = rmul((ayn, ayd), (bxn, bxd))
    if n1[0] == "err":
        return n1
    n2 = rmul((axn, axd), (byn, byd))
    if n2[0] == "err":
        return n2
    n = rsub(n1[1], n2[1])
    if n[0] == "err":
        return n
    d = rmul((bxn, bxd), (bxn, bxd))
    if d[0] == "err":
        return d
    y = rdiv(n[1], d[1])
    if y[0] == "err":
        return y
    return ("ok", (x[1], y[1]))


def qpoly3(c, t):
    t2 = qmul(t, t)
    if t2[0] == "err":
        return t2
    t3 = qmul(t2[1], t)
    if t3[0] == "err":
        return t3
    acc = ((c[0], 1), (0, 1))
    for cc, tt in ((c[1], t), (c[2], t2[1]), (c[3], t3[1])):
        m = qmul(((cc, 1), (0, 1)), tt)
        if m[0] == "err":
            return m
        x = radd(acc[0], m[1][0])
        if x[0] == "err":
            return x
        y = radd(acc[1], m[1][1])
        if y[0] == "err":
            return y
        acc = (x[1], y[1])
    return ("ok", acc)


def main():
    # DualZ basics
    case("z-add", "entry_dualz_add", [1, 2, 3, 4], [zout(4, 6)])
    case("z-sub", "entry_dualz_sub", [1, 2, 3, 4], [zout(-2, -2)])
    case("z-mul", "entry_dualz_mul", [2, 1, 3, 4], [zout(6, 11)])
    case("z-neg", "entry_dualz_neg", [5, -3], [zout(-5, 3)])
    case("z-mul-overflow", "entry_dualz_mul", [M63, 1, 2, 0],
         [zout(reason=OVF)])
    case("z-neg-min", "entry_dualz_neg", [MIN64, 0],
         [zout(reason=OVF)])
    # p(t) = 1 + 2t + 3t^2 + 4t^3 at t = 2: (49, 62)
    r = zpoly3([1, 2, 3, 4], (2, 1))
    assert r == ("ok", (49, 62)), r
    case("z-poly3", "entry_dualz_poly3", [1, 2, 3, 4, 2],
         [zout(49, 62)])
    r = zpoly3([0, 1, 0, 0], (7, 1))
    assert r == ("ok", (7, 1)), r
    case("z-poly3-ident", "entry_dualz_poly3", [0, 1, 0, 0, 7],
         [zout(7, 1)])

    # DualQ basics: a = (1/2, 1/3), b = (2, 3/4)
    a = ((1, 2), (1, 3))
    b = ((2, 1), (3, 4))
    r = qmul(a, b)
    assert r == ("ok", ((1, 1), (25, 24))), r
    flat = [r[1][0][0], r[1][0][1], r[1][1][0], r[1][1][1]]
    case("q-mul", "entry_dualq_mul", [1, 2, 1, 3, 2, 1, 3, 4],
         [qout(*flat)])
    r = qdiv(((3, 1), (1, 1)), ((2, 1), (1, 1)))
    assert r == ("ok", ((3, 2), (-1, 4))), r
    case("q-div", "entry_dualq_div", [3, 1, 1, 1, 2, 1, 1, 1],
         [qout(3, 2, -1, 4)])
    case("q-div-zero", "entry_dualq_div", [3, 1, 1, 1, 0, 1, 1, 1],
         [qout(reason=1)])
    r = qdiv(((1, 1), (0, 1)), ((2, 1), (0, 1)))
    assert r == ("ok", ((1, 2), (0, 1))), r
    case("q-div-const", "entry_dualq_div", [1, 1, 0, 1, 2, 1, 0, 1],
         [qout(1, 2, 0, 1)])
    # p(t) = 1 + 2t + t^2 at t = 1/2: (9/4, 3)
    r = qpoly3([1, 2, 1, 0], ((1, 2), (1, 1)))
    assert r == ("ok", ((9, 4), (3, 1))), r
    case("q-poly3", "entry_dualq_poly3", [1, 2, 1, 0, 1, 2],
         [qout(9, 4, 3, 1)])
    # observers over (1/2 + 1/3, 1/4 + 1/5): x = 5/6, y = 9/20
    oargs = [1, 2, 1, 4, 1, 3, 1, 5]
    case("q-obs-xn", "entry_dualq_xn", oargs, [I(5)])
    case("q-obs-xd", "entry_dualq_xd", oargs, [I(6)])
    case("q-obs-yn", "entry_dualq_yn", oargs, [I(9)])
    case("q-obs-yd", "entry_dualq_yd", oargs, [I(20)])
    case("q-obs-code", "entry_dualq_code", oargs, [I(0)])
    oargs2 = [M63, 1, 0, 1, M63, 1, 0, 1]
    case("q-obs-code-ovf", "entry_dualq_code", oargs2, [I(2)])

    # Halley steps for c(x) = x^3 - 2x - 5 (exact rationals).
    # t = 2: f = -1, f' = 10, f'' = 12 -> x1 = 111/53
    r = halley_step((2, 1))
    assert r[0] == "ok", r
    assert (r[1][0], r[1][1]) == (111, 53), r
    case("halley-2", "entry_halley", [2, 1], [hout(*r[1])],
         budget=1048576)
    # t = 3: f = 16, f' = 25, f'' = 18 -> x1 = 1043/481
    r = halley_step((3, 1))
    assert (r[1][0], r[1][1]) == (1043, 481), r
    case("halley-3", "entry_halley", [3, 1], [hout(*r[1])],
         budget=1048576)
    # t = -1: f = -4, f' = 1, f'' = -6 -> x1 = -15/11
    r = halley_step((-1, 1))
    assert (r[1][0], r[1][1]) == (-15, 11), r
    case("halley-neg1", "entry_halley", [-1, 1], [hout(*r[1])],
         budget=1048576)
    # t = 5/2 (non-integer start exercises reduction in every lane)
    r = halley_step((5, 2))
    assert r[0] == "ok", r
    case("halley-5/2", "entry_halley", [5, 2], [hout(*r[1])],
         budget=1048576)
    # Residuals must contract cubically: |f(x1)| < |f(t)|^2 spot check.
    from fractions import Fraction as Fr
    for tt in ((2, 1), (3, 1), (-1, 1), (5, 2)):
        rr = halley_step(tt)
        assert rr[0] == "ok", rr
        before = abs(Fr(tt[0], tt[1])**3 - 2 * Fr(tt[0], tt[1]) - 5)
        after = abs(Fr(rr[1][2], rr[1][3]))
        assert after < before * before, (tt, before, after)
    # Zero denominator start: dualq_var rejects it (div-by-zero reason).
    case("halley-zero-den", "entry_halley", [1, 0], [hout(reason=DIVZ)])
    # Overflow start: t^3 leaves i64 inside the cubic evaluation.
    r = halley_step((2**31, 1))
    assert r == ("err", OVF), r
    case("halley-overflow", "entry_halley", [2**31, 1],
         [hout(reason=OVF)])
    # Second-derivative spots: f''(x) = 6x.
    for cid, t, want in (("d2-2", (2, 1), (12, 1)),
                         ("d2-half", (1, 2), (3, 1)),
                         ("d2-neg3/2", (-3, 2), (-9, 1))):
        r = d2cubic(t)
        assert r == ("ok", want), (cid, r)
        case(cid, "entry_d2cubic", [t[0], t[1]], [fout(*r[1])])
    case("d2-zero-den", "entry_d2cubic", [1, 0], [fout(reason=DIVZ)])

    table = {"module": HOME, "name": "autodiff-dual",
             "cases": CASES}
    out = Path(__file__).resolve().parent.parent / "tests" / "tables" \
        / "autodiff.json"
    out.write_text(json.dumps(table, indent=1) + "\n")
    print("wrote %s (%d cases)" % (out.name, len(CASES)))


if __name__ == "__main__":
    main()
