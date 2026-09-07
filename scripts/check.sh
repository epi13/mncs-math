#!/usr/bin/env bash
# Fast per-module check: source-study + research bytecode + portable WASM.
# Usage: scripts/check.sh <module>   (e.g. scripts/check.sh scalar)
set -uo pipefail
MOD="${1:?usage: check.sh <module>}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MNCS_LANG="${MNCS_LANG:-/home/epi13/Documents/Projects/mncs-math/../mncs-language}"
MNCS_BIN="${MNCS_BIN:-$MNCS_LANG/target/debug/mncs}"
SRC="$ROOT/src/math/$MOD.mncs"
CORPUS="$ROOT/tests/corpora/$MOD-corpus.json"
export MNCS_LIBRARY_PATH="$ROOT/src:$MNCS_LANG/library"

fail=0
echo "== source-study $MOD =="
"$MNCS_BIN" source-study "$SRC" --node-id "local-$MOD" > /dev/null \
  || { echo "FAIL source-study $MOD"; fail=1; }
check_value_corpus() {
  # $1 = backend, $2 = corpus path: every case must return and meet expectation.
  "$MNCS_BIN" experiment run "$SRC" --backend "$1" --corpus "$2" >/tmp/mncs-check-out.json 2>/tmp/mncs-check-err.txt \
    || { echo "FAIL experiment $MOD @ $1 (exit $?)"; tail -n 20 /tmp/mncs-check-err.txt; return 1; }
  python3 - /tmp/mncs-check-out.json <<'EOF'
import json, sys
d = json.load(open(sys.argv[1]))
bad = []
for c in d.get("cases", []):
    if c.get("status") != "returned":
        bad.append((c["case_id"], "status=%s" % c.get("status")))
    elif c.get("expectation_met") is not True:
        bad.append((c["case_id"], "expectation missed"))
if d.get("status") not in ("PASS", "UNKNOWN"):
    bad.append(("<overall>", "status=%s" % d.get("status")))
if bad:
    print("FAIL", bad); sys.exit(1)
print("ok: %d cases, overall %s" % (len(d.get("cases", [])), d.get("status")))
EOF
}
check_trap_corpus() {
  # $1 = backend, $2 = corpus path: every case must end in runtime_failure.
  "$MNCS_BIN" experiment run "$SRC" --backend "$1" --corpus "$2" >/tmp/mncs-check-out.json 2>/tmp/mncs-check-err.txt \
    || { echo "FAIL trap experiment $MOD @ $1 (exit $?)"; tail -n 20 /tmp/mncs-check-err.txt; return 1; }
  python3 - /tmp/mncs-check-out.json <<'EOF'
import json, sys
d = json.load(open(sys.argv[1]))
bad = [(c["case_id"], "status=%s" % c.get("status"))
       for c in d.get("cases", []) if c.get("status") != "runtime_failure"]
if bad:
    print("FAIL", bad); sys.exit(1)
print("ok: %d trap cases fail deterministically" % len(d.get("cases", [])))
EOF
}
if [ -f "$CORPUS" ]; then
  for b in mncs-research-bytecode mncs-portable-wasm-mvp; do
    echo "== experiment $MOD @ $b =="
    check_value_corpus "$b" "$CORPUS" || { echo "FAIL experiment $MOD @ $b"; fail=1; }
  done
else
  echo "(no corpus yet for $MOD)"
fi
TRAPS="$ROOT/tests/corpora/$MOD-traps-corpus.json"
if [ -f "$TRAPS" ]; then
  for b in mncs-research-bytecode mncs-portable-wasm-mvp; do
    echo "== traps $MOD @ $b =="
    check_trap_corpus "$b" "$TRAPS" || { echo "FAIL traps $MOD @ $b"; fail=1; }
  done
fi
exit $fail
