# status-contract-check

Zero-dependency Python 3 CLI for auditing the `nightly-lab` sidequest lifecycle contract from `current-run.json` plus its `status.jsonl`.

## What it checks
- expected sidequest agents from `current-run.json`
- observed `start -> artifact -> done/error` stage flow per agent
- duplicate terminal stages (`done` + `error`, or multiple terminals)
- report path mismatches vs `sidequest_reports.*`
- missing report file after completion
- missing artifact path / missing artifact folder
- artifact path outside `roots.nightly_sidequests`

## Why this is useful
`status.jsonl` is the real execution ledger. When the nightly run gets weird, this CLI tells you whether an agent is merely in progress or has actually broken the contract.

## Usage
Audit the active run:

```bash
python3 status_contract_check.py
```

Audit one agent only:

```bash
python3 status_contract_check.py --agent main
```

Fail on in-progress agents too:

```bash
python3 status_contract_check.py --strict
```

Use a saved run file and emit JSON:

```bash
python3 status_contract_check.py --current-run /root/.openclaw/workspace/nightly-lab/runs/2026-04-09/run.json --json
```

## Exit codes
- `0`: clean, or only pending/in-progress agents
- `1`: contract warnings found (or pending agents when `--strict` is set)
- `2`: hard input error (missing/unreadable JSON inputs)

## Files
- `status_contract_check.py` — main CLI
- `README.md` — this doc

## Test command
```bash
python3 /root/.openclaw/workspace/nightly-sidequests/2026-04-09-main-status-contract-check/status_contract_check.py --current-run /root/.openclaw/workspace/nightly-lab/runs/2026-04-09/run.json --agent vibe
```
