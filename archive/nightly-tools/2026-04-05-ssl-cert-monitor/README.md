# SSL Cert Monitor

Quick Python 3 (stdlib-only) CLI to check certificate expiration for:
- HTTPS endpoints (`https://...`)
- Local certificate files (`.pem`, `.crt`, `.cer`)

No third-party dependencies.

## Files
- `ssl_cert_monitor.py` — runnable script
- `sample_targets.txt` — sample input list

## Usage

### 1) Check inline targets
```bash
python3 ssl_cert_monitor.py https://sha256.badssl.com https://expired.badssl.com
```

### 2) Check from input file
```bash
python3 ssl_cert_monitor.py --input-file sample_targets.txt
```

### 3) Tune warning and timeout
```bash
python3 ssl_cert_monitor.py --warn-days 14 --timeout 8 https://sha256.badssl.com
```

## Output format
Each result is one parseable text line (no ANSI colors):

`STATUS<TAB>TARGET<TAB>expires_at=<iso|-><TAB>days_left=<int|-><TAB>note=<text>`

Status values:
- `VALID`: certificate not near expiry
- `EXPIRING`: certificate expires within `--warn-days`
- `EXPIRED`: certificate already expired
- `UNKNOWN`: verification failed (for example self-signed/hostname mismatch), expiration may still be shown
- `ERROR`: bad input, timeout, connection failure, or decode error

## Exit codes
- `0`: no ERROR and no EXPIRED
- `1`: at least one EXPIRED
- `2`: at least one ERROR

## Smoke test
```bash
python3 ssl_cert_monitor.py --input-file sample_targets.txt --warn-days 30 --timeout 5
```

Expected behavior for sample list:
- `sha256.badssl.com` => usually `VALID` or `EXPIRING`
- `expired.badssl.com` => `EXPIRED`
- `self-signed.badssl.com` => `UNKNOWN`
- `example.invalid` => `ERROR`
