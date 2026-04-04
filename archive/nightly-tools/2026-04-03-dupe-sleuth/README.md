# DupeSleuth

A safe, zero-dependency Python 3 CLI to find **exact duplicate files** by SHA256 content hash.

## Safety first
- ✅ Identifies duplicates only
- ✅ Never deletes files
- ✅ Local directory scan only

## Files
- `dupe_sleuth.py` — main scanner
- `create_sample_input.py` — optional helper to generate a demo dataset

## Usage
```bash
python3 dupe_sleuth.py /path/to/scan
```

Verbose mode:
```bash
python3 dupe_sleuth.py /path/to/scan --verbose
```

## Output behavior
- Groups exact duplicates by hash
- Marks one path as `[KEEP]` (suggested keep)
- Marks other identical copies as `[DEL]` (manual cleanup candidates)
- Prints estimated reclaimable disk space
- Always prints warning that no deletion is performed

## Smoke test (quick)
```bash
python3 create_sample_input.py /tmp/dupe-sleuth-sample
python3 dupe_sleuth.py /tmp/dupe-sleuth-sample
```

Expected: at least one duplicate group is reported.

## Notes
- Exact-content matching only (no fuzzy/near-duplicate logic)
- Unreadable files are skipped and counted
- Symlinks are skipped to avoid cycles/double counting
