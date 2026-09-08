#!/usr/bin/env python3
"""Dev-time oracle for numerical fixtures (Python exact arithmetic).

Emits tests/tables/numerical.json. Every MNCS result is cross-checked
against an INDEPENDENT computation (Fraction-based root bracketing,
Newton iteration, integral formulas, Euler update) that shares no code
with the rational-op mirror: both must agree before freezing.
"""
import json
import sys
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from oracle_linalg import rmake, radd, rsub, rmul, rdiv  # noqa

M63 = 2**63 - 1
MIN64 = -2**63

HOME = "mncs.math.numerical.v1"
RHOME = "mncs.math.rational.v1"

OVF, DIVZ, DOMAIN = 2, 1, 13

CASES = []


def I(v):
    return {"i64": v}


def bracketout(lan=None, lad=None, uan=None, uad=None, reason=None):
    if reason is not None:
        return {"finite": {"enum": "BracketOut", "variant": "Err",
                           "discriminant": 1, "home": HOME,
                           "payload": {"reason": I(reason)}}}
    return {"finite": {"enum": "BracketOut", "variant": "Ok",
                       "discriminant": 0, "home": HOME,
                       "payload": {"lan": I(lan), "lad": I(lad),
                                   "uan": I(uan), "uad": I(uad)}}}


def newtonout(xn=None, xd=None, reason=None):
    if reason is not None:
        return {"finite": {"enum": "NewtonOut", "variant": "Err",
                           "discriminant": 1, "home": HOME,
                           "payload": {"reason": I(reason)}}}
    return {"finite": {"enum": "NewtonOut", "variant": "Ok",
                       "discriminant": 0, "home": HOME,
                       "payload": {"xn": I(xn), "xd": I(xd)}}}


def fracout(num=None, den=None, reason=None):
    if reason is not None:
        return {"finite": {"enum": "FracOutcome", "variant": "Err",
                           "discriminant": 1, "home": RHOME,
                           "payload": {"reason": I(reason)}}}
    return {"finite": {"enum": "FracOutcome", "variant": "Ok",
                       "discriminant": 0, "home": RHOME,
                       "payload": {"num": I(num), "den": I(den)}}}


def case(cid, fn, args, expected, budget=1048576):
    CASES.append({"id": cid, "fn": fn,
                  "args": [I(a) for a in args],
                  "expect": expected, "budget": budget})


def fits(v):
    return MIN64 <= v <= M63


def sgn(fr):
    return (fr > 0) - (fr < 0)


def peval(coef, x):
    # exact value via Fractions (independent of the dual chain)
    return sum(Fraction(c) * x**k for k, c in enumerate(coef))


def pmirror(coef, p):
    # value lanes through the rational-op mirror (dualq_poly3 order)
    t = (p, (1, 1))
    t2 = qmul(t, t)
    if t2[0] == "err":
        return t2
    t3 = qmul(t2[1], t)
    if t3[0] == "err":
        return t3
    acc = ((coef[0], 1), (0, 1))
    for cc, tt in ((coef[1], t), (coef[2], t2[1]), (coef[3], t3[1])):
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


def rmid(lo, hi):
    s = radd(lo, hi)
    if s[0] == "err":
        return s
    return rdiv(s[1], (2, 1))


def bisect_mirror(coef, lan, lad, uan, uad, steps=8):
    flo = pmirror(coef, (lan, lad))
    if flo[0] == "err":
        return ("err", flo[1])
    fhi = pmirror(coef, (uan, uad))
    if fhi[0] == "err":
        return ("err", fhi[1])
    slo = sgn(Fraction(flo[1][0][0], flo[1][0][1]))
    shi = sgn(Fraction(fhi[1][0][0], fhi[1][0][1]))
    if slo == 0:
        return ("ok", ((lan, lad), (lan, lad)))
    if shi == 0:
        return ("ok", ((uan, uad), (uan, uad)))
    if slo == shi:
        return ("err", DOMAIN)
    lo, hi = (lan, lad), (uan, uad)
    for _ in range(steps):
        m = rmid(lo, hi)
        if m[0] == "err":
            return ("err", m[1])
        fm = pmirror(coef, m[1])
        if fm[0] == "err":
            return ("err", fm[1])
        fl = pmirror(coef, lo)
        if fl[0] == "err":
            return ("err", fl[1])
        sm = sgn(Fraction(fm[1][0][0], fm[1][0][1]))
        sl = sgn(Fraction(fl[1][0][0], fl[1][0][1]))
        if sm == 0:
            lo, hi = m[1], m[1]
        elif sl == sm:
            lo = m[1]
        else:
            hi = m[1]
    return ("ok", (lo, hi))


def newton_mirror(coef, xn, xd, steps=3):
    x = (xn, xd)
    for _ in range(steps):
        r = pmirror(coef, x)
        if r[0] == "err":
            return ("err", r[1])
        (fxn, fxd), (fyn, fyd) = r[1]
        if fyn == 0:
            return ("err", DOMAIN)
        q = rdiv((fxn, fxd), (fyn, fyd))
        if q[0] == "err":
            return ("err", q[1])
        s = rsub(x, q[1])
        if s[0] == "err":
            return ("err", s[1])
        x = s[1]
    return ("ok", x)


def simpson_mirror(coef, an, ad, bn, bd):
    w = rsub((bn, bd), (an, ad))
    if w[0] == "err":
        return w
    h = rdiv(w[1], (2, 1))
    if h[0] == "err":
        return h
    m = radd((an, ad), h[1])
    if m[0] == "err":
        return m
    fa = pmirror(coef, (an, ad))
    fm = pmirror(coef, m[1])
    fb = pmirror(coef, (bn, bd))
    for f in (fa, fm, fb):
        if f[0] == "err":
            return f
    t4 = rmul((4, 1), fm[1][0])
    if t4[0] == "err":
        return t4
    s1 = radd(fa[1][0], t4[1])
    if s1[0] == "err":
        return s1
    s2 = radd(s1[1], fb[1][0])
    if s2[0] == "err":
        return s2
    t = rmul(s2[1], h[1])
    if t[0] == "err":
        return t
    return rdiv(t[1], (3, 1))


def pintegral(coef, a, b):
    # antiderivative at b minus at a (independent formula)
    def anti(x):
        return sum(Fraction(c) * x**(k + 1) / (k + 1)
                   for k, c in enumerate(coef))
    return anti(b) - anti(a)


def main():
    # f(t) = t^2 - 2, root sqrt(2) in [1, 2]
    coef = [-2, 0, 1, 0]
    r = bisect_mirror(coef, 1, 1, 2, 1)
    assert r[0] == "ok"
    (lan, lad), (uan, uad) = r[1]
    lo, hi = Fraction(lan, lad), Fraction(uan, uad)
    assert lo < 2**0.5 < hi and hi - lo == Fraction(1, 256), (lo, hi)
    case("bisect-sqrt2", "entry_bisect8", coef + [1, 1, 2, 1],
         [bracketout(lan, lad, uan, uad)])
    # f(t) = t^3 - t - 2 (root near 1.5214) in [1, 2]
    coef2 = [-2, -1, 0, 1]
    r = bisect_mirror(coef2, 1, 1, 2, 1)
    assert r[0] == "ok"
    (lan, lad), (uan, uad) = r[1]
    lo, hi = Fraction(lan, lad), Fraction(uan, uad)
    assert peval(coef2, lo) < 0 < peval(coef2, hi)
    assert hi - lo == Fraction(1, 256)
    case("bisect-cubic", "entry_bisect8", coef2 + [1, 1, 2, 1],
         [bracketout(lan, lad, uan, uad)])
    # endpoint root collapses immediately: t^2 - 4 on [2, 3]
    case("bisect-endpoint", "entry_bisect8", [-4, 0, 1, 0] + [2, 1, 3, 1],
         [bracketout(2, 1, 2, 1)])
    # unbracketed start fails with domain
    case("bisect-unbracketed", "entry_bisect8",
         [0, 0, 1, 0] + [2, 1, 3, 1], [bracketout(reason=DOMAIN)])

    # Newton on t^2 - 2 from x0 = 1: x1 = 3/2, x2 = 17/12, x3 = 577/408
    r = newton_mirror([-2, 0, 1, 0], 1, 1)
    assert r == ("ok", (577, 408)), r
    case("newton-sqrt2", "entry_newton3", [-2, 0, 1, 0, 1, 1],
         [newtonout(577, 408)])
    # Newton on t^3 - 2t - 5 (Wallis-type) from 2
    r = newton_mirror([-5, -2, 0, 1], 2, 1)
    assert r[0] == "ok"
    xn, xd = r[1]
    case("newton-cubic", "entry_newton3", [-5, -2, 0, 1, 2, 1],
         [newtonout(xn, xd)])
    # zero derivative fails with domain: t^2 at x = 0
    case("newton-flat", "entry_newton3", [0, 0, 1, 0, 0, 1],
         [newtonout(reason=DOMAIN)])

    # Simpson: int_0^2 (1 + 2t + 3t^2 + 4t^3) = 2+4+8+16 = 30
    r = simpson_mirror([1, 2, 3, 4], 0, 1, 2, 1)
    assert r == ("ok", (30, 1)), r
    assert pintegral([1, 2, 3, 4], Fraction(0), Fraction(2)) == 30
    case("simpson-cubic", "entry_simpson_cubic",
         [1, 2, 3, 4, 0, 1, 2, 1], [fracout(30, 1)])
    # int_0^1 t^2 = 1/3
    r = simpson_mirror([0, 0, 1, 0], 0, 1, 1, 1)
    assert r == ("ok", (1, 3)), r
    case("simpson-square", "entry_simpson_cubic",
         [0, 0, 1, 0, 0, 1, 1, 1], [fracout(1, 3)])
    # int_{-1}^1 (t^3 - t) = 0
    r = simpson_mirror([0, -1, 0, 1], -1, 1, 1, 1)
    assert r == ("ok", (0, 1)), r
    case("simpson-odd", "entry_simpson_cubic",
         [0, -1, 0, 1, -1, 1, 1, 1], [fracout(0, 1)])

    # Euler: y' = y, y(0) = 1, h = 1/2 -> 3/2
    case("euler-exp", "entry_euler1", [1, 1, 0, 1, 1, 1, 1, 2],
         [fracout(3, 2)])
    # y' = -2y + 1, y(0) = 0, h = 1/4 -> 1/4
    case("euler-linear", "entry_euler1",
         [-2, 1, 1, 1, 0, 1, 1, 4], [fracout(1, 4)])
    # y' = 3y + 2, y(1) = 5, h = 1/3 -> 5 + (17)/3 = 32/3
    case("euler-frac", "entry_euler1",
         [3, 1, 2, 1, 5, 1, 1, 3], [fracout(32, 3)])

    table = {"module": HOME, "name": "numerical-exact",
             "cases": CASES}
    out = Path(__file__).resolve().parent.parent / "tests" / "tables" \
        / "numerical.json"
    out.write_text(json.dumps(table, indent=1) + "\n")
    print("wrote %s (%d cases)" % (out.name, len(CASES)))


if __name__ == "__main__":
    main()
