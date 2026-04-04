# Workflow Glance - Quick OpenClaw Status Tool

A simple, zero-dependency Python script for quickly checking OpenClaw workflow status and team coordination.

## Features

- ✅ Zero-dependencies (uses built-in Python modules)
- ✅ Self-contained workflow monitoring
- ✅ Quick team coordination aid
- ✅ No external API calls required
- ✅ Lightweight and fast execution

## Usage

```bash
python3 workflow_glance.py
```

## Output

The tool provides:
- Current timestamp
- Active OpenClaw processes
- Recent workspace activity (files modified in last hour)
- Status summary with validation checks
- Tool information and location

## Files

- `workflow_glance.py` - Main tool script
- `README.md` - This documentation
- `test_command.txt` - Testing instructions

## Test Command

```bash
cd /root/.openclaw/workspace/nightly-sidequests/2026-04-05-commander-workflow-glance/
python3 workflow_glance.py
```

## Integration

This tool can be easily integrated into:
- Daily team check-in routines
- Development workflow automation
- Status monitoring scripts
- Team coordination processes

## License

Open source - available for team use and extension.