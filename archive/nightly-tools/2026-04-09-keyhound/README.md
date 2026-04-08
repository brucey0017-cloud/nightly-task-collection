# keyhound

## 30-second smoke test (copy/paste)

```bash
mkdir -p /tmp/kh-test && cd /tmp/kh-test
cat > bad.cfg <<'EOF'
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
EOF
cat > app.js <<'EOF'
const ghToken = "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnop1234";
EOF
cat > key.pem <<'EOF'
-----BEGIN RSA PRIVATE KEY-----
MIIE...
-----END RSA PRIVATE KEY-----
EOF
cat > clean.js <<'EOF'
const safe = "hello world";
EOF

python3 /root/.openclaw/workspace/nightly-tools/2026-04-09-keyhound/keyhound.py /tmp/kh-test
# expect: exit code 1, summary says 3 potential secrets found

python3 /root/.openclaw/workspace/nightly-tools/2026-04-09-keyhound/keyhound.py /tmp/kh-test --json
# expect: valid JSON array with 3 findings (file/line/type/preview)

python3 /root/.openclaw/workspace/nightly-tools/2026-04-09-keyhound/keyhound.py /tmp/kh-test --quiet
# expect: "3 potential secrets found", exit code 1

python3 /root/.openclaw/workspace/nightly-tools/2026-04-09-keyhound/keyhound.py /tmp/kh-test/clean.js
# expect: summary says 0 secrets found, exit code 0

rm -rf /tmp/kh-test
```

Smoke note: local validation run completed successfully during build (default / --json / --quiet / clean-file checks).

## Quick usage

```bash
python3 keyhound.py <path>
python3 keyhound.py <path> --json
python3 keyhound.py <path> --quiet
```

- `--json`: output findings as JSON array.
- `--quiet`: output only count line (`0 secrets found` or `N potential secrets found`).

## What it detects (v1)

Pattern-only detection (no entropy heuristics):

- AWS access key IDs (`AKIA...`)
- GitHub tokens (`ghp_`, `gho_`, `ghu_`, `ghs_`, `github_pat_...`)
- Private key begin lines (`-----BEGIN ... PRIVATE KEY-----`)
- Slack tokens (`xox[boapr]-...`)
- Google API keys (`AIza...`)

## Output + CI behavior

Default output is one finding per line:

```text
path:line  [type]  first8...last4
```

Then exactly two summary lines:

- `✅ 0 secrets found` + `exit=0 (clean)`
- `🚨 N potential secrets found` + `exit=1 (findings)`

Exit code is `0` when clean, `1` when findings exist.

## Scope and constraints

- Python 3 stdlib only (no third-party dependencies)
- Recursively scans directories or scans a single file
- Skips common noisy directories and lock/minified/template files
- Skips obvious binary files
