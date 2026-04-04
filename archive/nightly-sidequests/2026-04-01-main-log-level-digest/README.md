# log_level_digest.py

A tiny Python 3 zero-dependency utility that digests a log file by level.

## Usage

```bash
python3 log_level_digest.py sample.log
python3 log_level_digest.py sample.log -n 5
python3 log_level_digest.py sample.log --json
```

## Output

- total lines
- counts for TRACE / DEBUG / INFO / WARN / ERROR / FATAL / CRITICAL
- last N error-ish lines (ERROR / FATAL / CRITICAL)
