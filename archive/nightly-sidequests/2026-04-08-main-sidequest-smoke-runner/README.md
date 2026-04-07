# sidequest-smoke-runner

Zero-dependency Python 3 CLI for validating `nightly-lab` sidequest reports and optionally running their declared smoke tests.

## What it does
- Reads `nightly-lab/current-run.json` by default
- Discovers report files from `sidequest_reports.*`
- Parses the standard sidequest markdown fields (`Folder`, `Files`, `Test command`, `Status`, etc.)
- Validates that report files, declared folders, and listed files actually exist
- Optionally executes each report's `Test command` with a timeout and records pass/fail output
- Supports human-readable output or `--json`

## Why this is useful
The nightly flow now has multiple agents dropping tiny tools and markdown reports all over the workspace. By morning, the annoying part is not *finding* them — it's checking whether the report is complete and whether the claimed test command still works. This tool turns that into one command instead of manual eyeballing.

## Usage
List discovered sidequest reports:

```bash
python3 sidequest_smoke_runner.py --list
```

Validate every report from the active run:

```bash
python3 sidequest_smoke_runner.py
```

Validate a single agent report:

```bash
python3 sidequest_smoke_runner.py --agent maker
```

Run smoke tests for a single agent:

```bash
python3 sidequest_smoke_runner.py --agent maker --run-tests --timeout 90
```

Run against an explicit report path:

```bash
python3 sidequest_smoke_runner.py --report /root/.openclaw/workspace/nightly-lab/sidequests/2026-04-08/maker.md --run-tests
```

Emit JSON:

```bash
python3 sidequest_smoke_runner.py --agent maker --run-tests --json
```

## Exit codes
- `0`: clean validation / all tests passed
- `1`: warnings, missing fields/files, or failed smoke tests
- `2`: hard input errors (bad/missing current-run file, unreadable or unparsable inputs)

## Files
- `sidequest_smoke_runner.py` — main CLI
- `README.md` — this doc

## Test command
```bash
python3 /root/.openclaw/workspace/nightly-sidequests/2026-04-08-main-sidequest-smoke-runner/sidequest_smoke_runner.py --agent maker --run-tests
```
