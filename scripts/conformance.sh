#!/usr/bin/env bash
# Full five-backend conformance gate for mncs-math.
# Usage: scripts/conformance.sh [--modules "a b..."] [--backends "a b..."]
#        [--out DIR]   (default subset: all modules, all backends)
#
# For every (module x backend): source-study, value corpus, trap corpus
# (where present). For every (example x backend): example corpus.
# Collects compiler_study.unresolved_obligations into obligations.tsv
# (the UNKNOWN inventory) and prints a verdict matrix.
#
# Verdict classes per cell:
#   OK                  all cases returned + expectations met
#   VALUE_DIVERGENCE    run ok, some expectation missed
#   RUNTIME_FAIL        value-corpus case ended runtime_failure
#   NATIVE_NO_OBS       backend produced no observation (native crash)
#   TRAP_OK             trap corpus fails deterministically (expected)
#   RUNNER_ERROR        unparsable output (reserved: a nonzero CLI exit
#                       with parseable cases still triages normally,
#                       since natives exit 1 for isolated divergences
#                       while emitting full case detail)
# Backend inability is reported, never hidden: a backend that cannot
# execute an artifact class shows NATIVE_NO_OBS/RUNNER_ERROR, not OK.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MNCS_LANG="${MNCS_LANG:-/home/epi13/Documents/Projects/mncs-math/../mncs-language}"
MNCS_BIN="${MNCS_BIN:-$MNCS_LANG/target/debug/mncs}"
export MNCS_LIBRARY_PATH="$ROOT/src:$MNCS_LANG/library"
MODULES_STR=""
BACKENDS_STR=""
OUT=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --modules) MODULES_STR="$2"; shift 2;;
    --backends) BACKENDS_STR="$2"; shift 2;;
    --out) OUT="$2"; shift 2;;
    *) echo "unknown flag $1" >&2; exit 2;;
  esac
done
MODULES_STR="${MODULES_STR:-error scalar rational internal bigint fixed complex vector matrix linalg tensor interval autodiff deterministic statistics numerical optimize float poly modular ntt sparse linalg5 tdata bigintx ode}"
BACKENDS_STR="${BACKENDS_STR:-mncs-research-bytecode mncs-portable-wasm-mvp mncs-c11 mncs-llvm-ir mncs-cranelift}"
OUT="${OUT:-$ROOT/target/conformance}"
# shellcheck disable=SC2206
MODS=($MODULES_STR)
# shellcheck disable=SC2206
BACKENDS=($BACKENDS_STR)
mkdir -p "$OUT"
TMP="$(mktemp -d "${TMPDIR:-/tmp}/mncs-conform.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

MATRIX="$OUT/matrix.tsv"
OBLIG="$OUT/obligations.tsv"
echo -e "module\tbackend\tclass\tcases\toverall" > "$MATRIX"
echo -e "backend\tmodule\tcase\toverall\tobligation" > "$OBLIG"

triage_value() {
  # $1 = result json: prints "CLASS ncases overall".
  python3 - "$1" <<'EOF'
import json, sys
d = json.load(open(sys.argv[1]))
cs = d.get("cases", [])
nocrash = sum(1 for c in cs if c.get("status") == "invalid_request")
nrtf = sum(1 for c in cs if c.get("status") == "runtime_failure")
nmiss = sum(1 for c in cs if c.get("status") == "returned" and c.get("expectation_met") is not True)
nother = sum(1 for c in cs if c.get("status") not in ("returned", "invalid_request", "runtime_failure"))
if nocrash: cls = "NATIVE_NO_OBS"
elif nrtf: cls = "RUNTIME_FAIL"
elif nmiss or nother: cls = "VALUE_DIVERGENCE"
else: cls = "OK"
print("%s %d %s" % (cls, len(cs), d.get("status")))
EOF
}

triage_traps() {
  # $1 = result json: every case must be runtime_failure.
  python3 - "$1" <<'EOF'
import json, sys
d = json.load(open(sys.argv[1]))
cs = d.get("cases", [])
bad = sum(1 for c in cs if c.get("status") != "runtime_failure")
print(("TRAP_OK" if not bad else "VALUE_DIVERGENCE") + " %d %s" % (len(cs), d.get("status")))
EOF
}

harvest_obligations() {
  # $1 = result json, $2 = backend, $3 = module: append obligation rows.
  python3 - "$1" "$2" "$3" <<'EOF' >> "$OBLIG"
import json, sys
d = json.load(open(sys.argv[1]))
b, m = sys.argv[2], sys.argv[3]
cs = d.get("compiler_study") or {}
for o in cs.get("unresolved_obligations", []):
    print("%s\t%s\t<compile>\t%s\t%s" % (b, m, d.get("status"), o))
EOF
}

fail=0
for m in "${MODS[@]}"; do
  SRC="$ROOT/src/math/$m.mncs"
  echo "== source-study $m =="
  if ! "$MNCS_BIN" source-study "$SRC" --node-id "conform-$m" > "$TMP/study-$m.json" 2>"$TMP/study-$m.err"; then
    echo "RUNNER_ERROR source-study $m"; fail=1
  fi
  for b in "${BACKENDS[@]}"; do
    for class in value traps; do
      if [[ "$class" == value ]]; then CORPUS="$ROOT/tests/corpora/$m-corpus.json"; else CORPUS="$ROOT/tests/corpora/$m-traps-corpus.json"; fi
      [[ -f "$CORPUS" ]] || continue
      OUT1="$TMP/$m-$b-$class.json"
      # A nonzero CLI exit must not mask triageable evidence: scalar on
      # natives exits 1 for two isolated divergences while still
      # emitting 63 parseable cases. Triage whenever stdout parses;
      # RUNNER_ERROR is reserved for unparsable output.
      # 590s per-cell guard: natives compile + interpret, and a hung
      # backend must fail its cell, not the whole matrix.
      timeout 590 "$MNCS_BIN" experiment run "$SRC" --backend "$b" --corpus "$CORPUS" > "$OUT1" 2>"$TMP/$m-$b-$class.err"
      cli_exit=$?
      if ! python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); assert isinstance(d.get("cases", None), list)' "$OUT1" 2>/dev/null; then
        echo -e "$m\t$b\tRUNNER_ERROR\t0\t-" >> "$MATRIX"
        echo "RUNNER_ERROR $m @ $b ($class) exit $cli_exit (unparsable)"; fail=1; continue
      fi
      if [[ "$class" == value ]]; then read -r cls n ov < <(triage_value "$OUT1"); else read -r cls n ov < <(triage_traps "$OUT1"); fi
      echo -e "$m\t$b\t$cls\t$n\t$ov" >> "$MATRIX"
      harvest_obligations "$OUT1" "$b" "$m"
      [[ "$cls" == OK || "$cls" == TRAP_OK ]] || fail=1
    done
  done
done
for ex in ex_solve ex_sample; do
  corpus_name="${ex//_/-}-corpus.json"
  for b in "${BACKENDS[@]}"; do
    OUT1="$TMP/ex-$ex-$b.json"
    timeout 590 "$MNCS_BIN" experiment run "$ROOT/examples/$ex.mncs" --backend "$b" --corpus "$ROOT/examples/corpora/$corpus_name" > "$OUT1" 2>"$TMP/ex-$ex-$b.err"
    cli_exit=$?
    if ! python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); assert isinstance(d.get("cases", None), list)' "$OUT1" 2>/dev/null; then
      echo -e "$ex\t$b\tRUNNER_ERROR\t0\t-" >> "$MATRIX"
      echo "RUNNER_ERROR example $ex @ $b exit $cli_exit (unparsable)"; fail=1; continue
    fi
    read -r cls n ov < <(triage_value "$OUT1")
    echo -e "$ex\t$b\t$cls\t$n\t$ov" >> "$MATRIX"
    harvest_obligations "$OUT1" "$b" "$ex"
    [[ "$cls" == OK ]] || fail=1
  done
done
echo "---- matrix ($MATRIX) ----"
column -t -s $'\t' "$MATRIX"
echo "---- obligations ($OBLIG, $(($(wc -l < "$OBLIG") - 1)) rows) ----"
exit $fail
