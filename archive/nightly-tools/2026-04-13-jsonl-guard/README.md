# jsonl-guard

Fast JSONL validator for line-level correctness checks.

## 90-second Morning smoke test

```bash
cd /root/.openclaw/workspace/nightly-tools/2026-04-13-jsonl-guard

# 1) help should exit 0
python3 ./jsonl-guard --help

# 2) valid file should pass (exit 0)
python3 ./jsonl-guard ./samples/valid.jsonl

# 3) invalid file should fail (exit non-zero)
python3 ./jsonl-guard ./samples/invalid.jsonl; echo "exit: $?"
# expected: exit is non-zero and output includes invalid line diagnostics

# 4) automated tests
./tests/test_jsonl_guard.sh
```

## What it does

`jsonl-guard` checks a `.jsonl` file line by line and reports:
- total lines
- valid lines
- invalid lines
- invalid line numbers + parse messages (capped by `--max-errors`)

Exit codes:
- `0` = all lines valid
- `1` = one or more invalid lines
- `2` = usage/file/I/O error

## Usage

```bash
python3 ./jsonl-guard <path-to-jsonl> [--max-errors N]
```

Examples:

```bash
python3 ./jsonl-guard ./samples/valid.jsonl
python3 ./jsonl-guard ./samples/invalid.jsonl --max-errors 50
```

## Output format

Each run uses a 3-block layout:
1. **What happened** (single line)
2. **Key facts** (compact bullet points)
3. **Next command** (single copy-paste command)

Symbols used:
- `✓` done
- `!` attention
- `x` failed

On successful interactive runs (TTY stdout), it also prints:

`Done. You can trust this run.`
