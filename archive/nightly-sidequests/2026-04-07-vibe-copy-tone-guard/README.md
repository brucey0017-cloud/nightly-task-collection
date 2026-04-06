# Copy Tone Guard (VIBE sidequest)

A tiny Python 3 helper to catch cliché Chinese marketing phrases and overlong lines.

## Why
When copy drifts into corporate-speak, trust drops fast. This script gives a quick red-flag pass before posting content.

## Run
```bash
python3 copy_tone_guard.py sample_copy.txt
```

## JSON output
```bash
python3 copy_tone_guard.py sample_copy.txt --json
```

## Stdin mode
```bash
echo "我们做了一站式平台" | python3 copy_tone_guard.py --stdin
```

## Exit code
- `0`: no issues
- `1`: cliché phrase hit or long-line warning exists
- `2`: input error
