#!/usr/bin/env bash
# Step-count benchmarks: per-case interpreter steps for every module
# corpus on both backends. Steps are a cost model, not wall time; they
# are deterministic for a fixed backend + corpus and expose algorithmic
# scaling (Bareiss vs Sarrus, Newton chains, sorting networks).
# Usage: scripts/bench.sh [module...]   (default: all modules)
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MNCS_LANG="${MNCS_LANG:-/home/epi13/Documents/Projects/mncs-math/../mncs-language}"
MNCS_BIN="${MNCS_BIN:-$MNCS_LANG/target/debug/mncs}"
export MNCS_LIBRARY_PATH="$ROOT/src:$MNCS_LANG/library"

MODS=("$@")
if [ "${#MODS[@]}" -eq 0 ]; then
  MODS=(error scalar rational internal bigint fixed complex vector matrix
        linalg tensor interval autodiff deterministic statistics numerical
        optimize float poly modular ntt sparse linalg5 tdata bigintx ode)
fi
BACKENDS=(mncs-research-bytecode mncs-portable-wasm-mvp)

printf 'module\tbackend\tcases\tsteps_total\tsteps_max\tsteps_max_case\n'
for mod in "${MODS[@]}"; do
  corpus="$ROOT/tests/corpora/$mod-corpus.json"
  [ -f "$corpus" ] || { echo "SKIP $mod (no corpus)" >&2; continue; }
  for b in "${BACKENDS[@]}"; do
    tmp="$(mktemp)"
    "$MNCS_BIN" experiment run "$ROOT/src/math/$mod.mncs" \
      --backend "$b" --corpus "$corpus" >"$tmp" 2>/dev/null \
      || { echo "FAIL $mod @ $b" >&2; rm -f "$tmp"; continue; }
    python3 - "$tmp" "$mod" "$b" <<'EOF'
import json, sys
d = json.load(open(sys.argv[1]))
mod, b = sys.argv[2], sys.argv[3]
tot, mx, mxid, n = 0, 0, "", 0
for c in d.get("cases", []):
    if c.get("status") == "returned":
        s = c.get("steps", 0) or 0
        tot += s
        n += 1
        if s > mx:
            mx, mxid = s, c.get("case_id", "")
print("%s\t%s\t%d\t%d\t%d\t%s" % (mod, b, n, tot, mx, mxid))
EOF
    rm -f "$tmp"
  done
done
