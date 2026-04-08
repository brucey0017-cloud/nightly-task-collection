# status-stage-lens

Tiny Python 3 CLI that summarizes nightly-lab `status.jsonl` by stage, agent, and `(agent, task)` workflow timeline.

## Examples

```bash
python3 stage_lens.py
python3 stage_lens.py --task sidequest --agent maker
python3 stage_lens.py --stage start --stage done --json
```

## Output fields

- `status_file`: source jsonl path
- `filters`: applied `agent` / `task` / `stages`
- `total_events`: included event count after filters
- `invalid_lines`: malformed/non-object json lines skipped
- `counts_by_stage`: counts grouped by `stage`
- `counts_by_agent`: counts grouped by `agent`
- `workflows`: per `(agent, task)` summary with:
  - `first_ts`
  - `last_ts`
  - `stages_seen` (ordered unique)
