# status-reference-audit

A zero-dependency Python 3 CLI tool to audit nightly-lab status files for workflow visibility and reference integrity.

## Purpose

This tool checks `status.jsonl` and `current-run.json` for common inconsistencies that can occur during workflow execution, such as unresolved placeholder references, missing files, and stage ordering anomalies.

## Usage

```bash
python3 audit_status.py <status.jsonl> <current-run.json> [options]
```

### Options

- `-o, --output FILE` - Write JSON output to file
- `-q, --quiet` - Quiet mode (only show errors)
- `-s, --summary-only` - Only show summary, not individual issues

### Example

```bash
python3 audit_status.py \
  /root/.openclaw/workspace/nightly-lab/runs/2026-04-06/status.jsonl \
  /root/.openclaw/workspace/nightly-lab/current-run.json
```

## Checks Performed

### 1. Unresolved Placeholder References
**What it finds:** Report or artifact values that look like placeholder references (e.g., `team_reports.killjoy`, `sidequest_reports.maker`) instead of resolved absolute paths.

**Why it matters:** These indicate the reference resolution logic failed or hasn't run yet. The actual report paths should be resolved from `current-run.json` mappings.

---

### 2. Missing or Empty Report Paths
**What it finds:** Empty `report` fields at `artifact` or `done` stages where a report path is expected.

**Why it matters:** Missing reports mean workflow visibility is broken - there's no record of what happened for that agent/task.

---

### 3. Missing Artifacts
**What it finds:** Artifact paths that don't exist on disk.

**Why it matters:** Indicates the artifact wasn't created, was moved, or the path is incorrect. Note: This is a point-in-time check - artifacts may be created after the status entry is written.

---

### 4. Non-Absolute Paths
**What it finds:** Relative paths (not starting with `/`) where absolute paths are expected.

**Why it matters:** Relative paths can break when consumed by different processes or when the working directory changes.

---

### 5. Stage Ordering Anomalies
**What it finds:** Out-of-order stage progressions per agent/task, such as:
- `artifact` before `start`
- `done` before `artifact`
- Duplicate stages for the same agent/task

**Why it matters:** Indicates logging errors, duplicate events, or workflow logic problems.

---

### 6. JSON Parse Errors
**What it finds:** Lines in `status.jsonl` that cannot be parsed as valid JSON.

**Why it matters:** Corrupted status data means lost workflow history.

---

### 7. Missing Stages
**What it finds:** Incomplete stage sequences (e.g., has `start` and `done` but missing `artifact`).

**Why it matters:** Indicates incomplete workflow execution or missing log entries.

## Exit Codes

- `0` - No issues found
- `1` - Issues found
- `2` - File/path error (input files not found, parse error, etc.)

## JSON Output Format

When using `-o/--output`, the tool writes a JSON file with this structure:

```json
{
  "audited_at": "2026-04-06T12:00:00",
  "status_file": "/path/to/status.jsonl",
  "current_run_file": "/path/to/current-run.json",
  "total_issues": 5,
  "issues": [
    {
      "type": "unresolved_placeholder",
      "line": 4,
      "agent": "killjoy",
      "task": "team",
      "stage": "start",
      "field": "report",
      "value": "team_reports.killjoy",
      "message": "Unresolved placeholder in report: 'team_reports.killjoy'"
    }
  ]
}
```

## Requirements

- Python 3.6+
- No external dependencies (uses only stdlib)
