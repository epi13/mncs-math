#!/usr/bin/env bash
# Run the runnable examples under examples/ on both backends.
# Usage: scripts/examples.sh [ex_solve|ex_sample]
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MNCS_LANG="${MNCS_LANG:-/home/epi13/Documents/Projects/mncs-math/../mncs-language}"
MNCS_BIN="${MNCS_BIN:-$MNCS_LANG/target/debug/mncs}"
export MNCS_LIBRARY_PATH="$ROOT/src:$MNCS_LANG/library"

EXS=("$@")
if [ "${#EXS[@]}" -eq 0 ]; then
  EXS=(ex_solve ex_sample)
fi
fail=0
for ex in "${EXS[@]}"; do
  corpus_name="${ex//_/-}-corpus.json"
  for b in mncs-research-bytecode mncs-portable-wasm-mvp; do
    echo "== example $ex @ $b =="
    "$MNCS_BIN" experiment run "$ROOT/examples/$ex.mncs" \
      --backend "$b" --corpus "$ROOT/examples/corpora/$corpus_name" \
      >/tmp/mncs-ex-out.json 2>/tmp/mncs-ex-err.txt \
      || { echo "FAIL example $ex @ $b (exit $?)"; fail=1; continue; }
    python3 - /tmp/mncs-ex-out.json <<'EOF'
import json, sys
d = json.load(open(sys.argv[1]))
bad = [(c["case_id"], c.get("status"))
       for c in d.get("cases", [])
       if c.get("status") != "returned"
       or c.get("expectation_met") is not True]
if d.get("status") not in ("PASS", "UNKNOWN") or bad:
    print("FAIL", d.get("status"), bad)
    sys.exit(1)
print("ok: %d cases, overall %s" % (len(d.get("cases", [])), d.get("status")))
EOF
    [ $? -ne 0 ] && fail=1
  done
done
exit "$fail"
