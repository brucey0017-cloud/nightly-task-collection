# json-delta

Semantic JSON diff CLI for quick before/after checks.

## What it does

`json-delta` compares two JSON documents and reports:
- **Changed** values
- **Added** keys/items
- **Removed** keys/items

It is order-stable for object keys and compares arrays **by index**.

> Limitation: arrays are compared by index; element reorders are reported as changes.

## Usage

```bash
./json-delta <file_a> <file_b> [--mode detail|summary] [--exit-code]
```

- `file_a`: baseline file (must be a normal file path)
- `file_b`: target file path, or `-` to read from stdin
- `--mode detail` (default): verdict + per-path diff lines
- `--mode summary`: verdict + counts only
- `--exit-code`: returns `1` when differences exist, `0` when identical

Exit codes:
- `0` = identical, or differences found without `--exit-code`
- `1` = differences found (only when `--exit-code` is set)
- `2` = error (bad JSON, missing file, invalid usage, I/O issue)

## 60-second smoke test

```bash
cd /tmp && mkdir -p jd-test && cd jd-test

# Test files
cat > a.json <<'JSON'
{"a":1,"b":"hello","c":[1,2,3]}
JSON

cat > b.json <<'JSON'
{"a":2,"b":"hello","d":true,"c":[1,2,4]}
JSON

# 1) Detail mode (default)
python3 /root/.openclaw/workspace/nightly-tools/2026-04-12-json-delta/json-delta a.json b.json
# Expected: Different verdict + changed a, changed c[2], added d

# 2) Summary mode
python3 /root/.openclaw/workspace/nightly-tools/2026-04-12-json-delta/json-delta a.json b.json --mode summary
# Expected: Different verdict + counts only (no per-key lines)

# 3) Exit code for differences
python3 /root/.openclaw/workspace/nightly-tools/2026-04-12-json-delta/json-delta a.json b.json --exit-code; echo "exit: $?"
# Expected: exit: 1

# 4) Identical files
python3 /root/.openclaw/workspace/nightly-tools/2026-04-12-json-delta/json-delta a.json a.json --exit-code; echo "exit: $?"
# Expected: "No JSON differences found." and exit: 0

# 5) Bad JSON -> error exit code
printf 'not-json\n' > bad.json
python3 /root/.openclaw/workspace/nightly-tools/2026-04-12-json-delta/json-delta a.json bad.json --exit-code; echo "exit: $?"
# Expected: error to stderr, exit: 2

# 6) stdin support (file_b only)
cat b.json | python3 /root/.openclaw/workspace/nightly-tools/2026-04-12-json-delta/json-delta a.json -
# Expected: same diff shape as test 1
```

## Example output (detail)

```text
Different: 3 changes
Changed (2):
- a: 1 -> 2
- c[2]: 3 -> 4
Added (1):
- d: true
Removed (0):
  (none)
```

## Example output (summary)

```text
Different: 3 changes
Changed: 2
Added: 1
Removed: 0
```
