#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TOOL="$ROOT/jsonl-guard"

python3 "$TOOL" --help >/dev/null

out_valid="$(mktemp)"
out_invalid="$(mktemp)"
trap 'rm -f "$out_valid" "$out_invalid"' EXIT

python3 "$TOOL" "$ROOT/samples/valid.jsonl" >"$out_valid"
grep -q -- "What happened: ✓ JSONL validation passed." "$out_valid"
grep -q -- "- ✓ Invalid lines: 0" "$out_valid"

set +e
python3 "$TOOL" "$ROOT/samples/invalid.jsonl" >"$out_invalid" 2>&1
rc=$?
set -e
if [[ "$rc" -eq 0 ]]; then
  echo "expected non-zero exit for invalid JSONL" >&2
  exit 1
fi

grep -q -- "What happened: x JSONL validation failed." "$out_invalid"
grep -q -- "line 2:" "$out_invalid"

echo "tests passed"
