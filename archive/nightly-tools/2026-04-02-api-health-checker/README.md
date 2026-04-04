# API Pulse Checker (MVB)

Minimal API health checker for on-call moments.

Checks each endpoint for:
- HTTP status = `200`
- JSON body is parseable
- response time, grouped as `FAILURES / SLOW / HEALTHY`

## Requirements
- Python 3 (standard library only)

## Usage

### 1) Check URLs directly
```bash
python3 api_pulse.py https://api.example.com/health https://api.example.com/status
```

### 2) Check URLs from a file
Create `urls.txt`:
```txt
# one URL per line
https://api.example.com/health
https://api.example.com/status
```

Run:
```bash
python3 api_pulse.py --file urls.txt
```

### Useful flags
- `--timeout 5` per-request timeout in seconds (default `5.0`)
- `--slow-ms 800` mark healthy endpoints slower than this threshold as SLOW (default `800`)
- `--no-color` disable ANSI colors

Example:
```bash
python3 api_pulse.py --file urls.txt --timeout 3 --slow-ms 500
```

## Exit codes
- `0`: all healthy
- `1`: no failures, but at least one slow endpoint
- `2`: at least one failed endpoint (or input error)

## Why this version
This is intentionally a minimal runnable baseline: single file, zero dependencies, quick to run in the morning.
