#!/usr/bin/env python3
"""Regenerate frozen execution corpora from authored oracle tables.

Usage: python3 tools/mkcorpus.py [module ...]
  Reads  tests/tables/<module>.json, writes tests/corpora/<module>-corpus.json.

Tables are the independent oracle: every expected value is authored by hand
(or cross-checked with exact Python arithmetic) and frozen here. This script
only encodes values into corpus JSON (notably finite payload identities);
it never invents expectations. Committed corpora are self-contained: no
Python runs at test time.

Value specs:
  {"i64": v} {"u64": v} {"i32": v} {"u32": v} {"bool": v} {"byte": v}
  {"seq": {"of": <scalar spec kind>, "values": [...]}}  (exact sequences)
  {"finite": {"enum": E, "variant": V, "discriminant": n,
              "payload": {"field": <spec>, ...}}}
  Trap cases: {"trap": true} instead of "expect" (asserts runtime_failure).

Corpus budgets default to 4096; override per case with "budget".
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TABLES = ROOT / "tests" / "tables"
CORPORA = ROOT / "tests" / "corpora"
IDENT = "mncs:0.2:finite-type:{module}::{enum}"
VIDENT = "mncs:0.2:finite-variant:{module}::{enum}::{variant}"
INT_KINDS = {"i64": (64, True), "u64": (64, False), "i32": (32, True),
             "u32": (32, False)}


def encode(spec, module):
    if not isinstance(spec, dict) or len(spec) != 1:
        raise ValueError("bad value spec: %r" % (spec,))
    (kind, val), = spec.items()
    if kind in INT_KINDS:
        bits, signed = INT_KINDS[kind]
        return {"integer": {"value": val, "type": {"bits": bits, "signed": signed}}}
    if kind == "bool":
        return {"boolean": {"value": bool(val)}}
    if kind == "byte":
        return {"byte": {"value": val}}
    if kind == "seq":
        of = val["of"]
        if of not in INT_KINDS:
            raise ValueError("sequence element kind unsupported: %r" % of)
        return {"sequence": {"values": [encode({of: v}, module) for v in val["values"]]}}
    if kind == "finite":
        # Expectations must name the DECLARING module's nominal identity,
        # which may differ from the corpus target module when the enum is
        # imported (e.g. MathResult lives in mncs.math.error.v1). Tables
        # pin it with an optional "home"; it defaults to the corpus module.
        home = val.get("home", module)
        payload = [[name, encode(vspec, module)]
                   for name, vspec in sorted(val.get("payload", {}).items())]
        body = {"type_identity": IDENT.format(module=home, enum=val["enum"]),
                "variant_identity": VIDENT.format(module=home, enum=val["enum"],
                                                 variant=val["variant"]),
                "discriminant": val["discriminant"]}
        if payload:
            body["payload"] = payload
        return {"finite": body}
    raise ValueError("unknown value kind: %r" % kind)


def request_of(modname, c):
    return {"schema_version": "0.1",
            "target": {"module": modname, "function": c["fn"]},
            "arguments": [encode(a, modname) for a in c.get("args", [])],
            "step_budget": c.get("budget", 4096)}


def build(module):
    # Value corpus: every case returns and meets its expectation.
    table = json.loads((TABLES / ("%s.json" % module)).read_text())
    modname = table["module"]
    cases = []
    for c in table["cases"]:
        if c.get("trap"):
            raise ValueError("trap case in value table (move to %s-traps.json): %r"
                             % (module, c["id"]))
        case = {"id": c["id"], "request": request_of(modname, c)}
        case["expected"] = [encode(e, modname) for e in c["expect"]]
        cases.append(case)
    corpus = {"schema_version": "0.1", "name": table["name"], "cases": cases}
    out = CORPORA / ("%s-corpus.json" % module)
    out.write_text(json.dumps(corpus, indent=1) + "\n")
    print("wrote %s (%d cases)" % (out.name, len(cases)))
    # Trap corpus (optional): every case must end in runtime_failure.
    # Kept separate because any runtime_failure drives the experiment's
    # overall status to FAIL even when every expectation is met.
    trappath = TABLES / ("%s-traps.json" % module)
    if trappath.exists():
        traptable = json.loads(trappath.read_text())
        tmodname = traptable["module"]
        tcases = [{"id": c["id"], "request": request_of(tmodname, c)}
                  for c in traptable["cases"]]
        for c in traptable["cases"]:
            if "expect" in c:
                raise ValueError("trap case must not carry expect: %r" % c["id"])
        tcorpus = {"schema_version": "0.1", "name": traptable["name"], "cases": tcases}
        tout = CORPORA / ("%s-traps-corpus.json" % module)
        tout.write_text(json.dumps(tcorpus, indent=1) + "\n")
        print("wrote %s (%d cases)" % (tout.name, len(tcases)))


def main(argv):
    mods = argv[1:] or sorted(p.stem for p in TABLES.glob("*.json")
                              if not p.stem.endswith("-traps"))
    for m in mods:
        build(m)


if __name__ == "__main__":
    main(sys.argv)
