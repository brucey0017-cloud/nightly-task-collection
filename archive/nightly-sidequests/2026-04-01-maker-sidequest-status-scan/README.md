# Sidequest Status Scan

Small zero-dependency Python tool for **workflow visibility** of nightly sidequest reports.

It scans:

- `/root/.openclaw/workspace/nightly-lab/sidequests/<DATE>/<AGENT>.md`

and summarizes status + built item for each report.

## Usage

```bash
python3 sidequest_status.py --date 2026-04-01 --format text
```

```bash
python3 sidequest_status.py --date 2026-04-01 --format json
```

```bash
python3 sidequest_status.py --root /custom/sidequests --format text
```

## Output

- `text`: quick human-readable summary (totals, status counts, per-agent lines)
- `json`: machine-readable payload for automation

## Notes

- Uses only Python 3 standard library.
- Handles missing root/date gracefully.
- Flags files that do not contain `# Sidequest Report` template marker.
