# env-doctor

A zero-dependency Python 3 checker for `.env` health.

## 30-second self-test

```bash
cd /tmp
rm -rf env-doctor-demo
mkdir -p env-doctor-demo
cat > env-doctor-demo/.env << 'EOF'
DATABASE_URL=
API_KEY=changeme
TOKEN=unquoted value with spaces
SECRET=-----BEGIN RSA PRIVATE KEY-----
DUPLICATE_KEY=first
EOF

cat > env-doctor-demo/.env.production << 'EOF'
DUPLICATE_KEY=second
EMPTY_VAR=
EOF

python3 /root/.openclaw/workspace/nightly-tools/2026-04-08-env-doctor/env_doctor.py env-doctor-demo
echo "EXIT: $?"
```

Expected:
- Output contains `[CRIT]` entries (empty values + private key pattern)
- Duplicate key is reported as `[WARN]`
- Exit code is `1`

## Usage

```bash
python3 env_doctor.py [path] [--no-color]
```

Examples:

```bash
# Scan current directory
python3 env_doctor.py .

# Scan with plain text output (CI/log friendly)
python3 env_doctor.py . --no-color

# Real-tree scan
python3 env_doctor.py /root/.openclaw/workspace/nightly-lab --no-color
```

## What it checks

- Empty values (`KEY=`) → `[CRIT]`
- Stale placeholders (`changeme`, `xxx`, `your-api-key-here`, `todo`) → `[WARN]`
- Syntax issues
  - missing `=`
  - unquoted values containing spaces
- Secret-leak candidates → `[CRIT]`
  - `-----BEGIN ... PRIVATE KEY-----`
  - base64-like values longer than 200 chars
- Duplicate keys across files → `[WARN]`

## Exit code quick reference

- `0`: no critical issues
- `1`: at least one critical issue found

## Notes

- No network calls.
- No auto-fix/write mode in v1.
- Stdlib only.
