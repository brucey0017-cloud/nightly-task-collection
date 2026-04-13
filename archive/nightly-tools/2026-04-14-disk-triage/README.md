# disk-triage

Find what is eating disk in 5 seconds.

`disk-triage` is a tiny read-only Python script to surface the biggest disk hotspots quickly.
It uses only Python stdlib and does not delete anything.

## Usage

```bash
python3 disk_triage.py [path] [--top N] [--depth N] [--warn-mb N] [--json] [--no-color]
```

Examples:

```bash
python3 disk_triage.py /tmp --top 10 --depth 2
python3 disk_triage.py / --warn-mb 500
python3 disk_triage.py /var --json | python3 -m json.tool | head -40
```

## Flags

- `path` (positional): target directory, default `/`
- `--top`: number of entries to show, default `15`
- `--depth`: scan depth for subdirectories, default `1`, max `3`
- `--warn-mb`: warning threshold (MB), default `100`
- `--json`: print machine-readable JSON output
- `--no-color`: force disable ANSI colors

## 30-second smoke test

```bash
mkdir -p /tmp/triage-demo/a /tmp/triage-demo/b /tmp/triage-demo/c
dd if=/dev/zero of=/tmp/triage-demo/a/big.bin bs=1M count=120 >/dev/null 2>&1
dd if=/dev/zero of=/tmp/triage-demo/b/med.bin bs=1M count=40  >/dev/null 2>&1
ln -s /tmp/triage-demo /tmp/triage-demo/c/loop

python3 disk_triage.py /tmp/triage-demo --top 5 --depth 2 --warn-mb 50
python3 disk_triage.py /tmp/triage-demo --json | python3 -c "import sys,json; d=json.load(sys.stdin); assert len(d)>0"

mkdir -p /tmp/triage-demo/d && chmod 000 /tmp/triage-demo/d
python3 disk_triage.py /tmp/triage-demo --depth 2 --top 5
chmod 755 /tmp/triage-demo/d

rm -rf /tmp/triage-demo
```
