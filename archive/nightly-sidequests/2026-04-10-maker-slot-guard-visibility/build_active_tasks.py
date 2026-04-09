#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

STATUS = Path('/root/.openclaw/workspace/nightly-lab/runs/2026-04-10/status.jsonl')
OUT = Path('/root/.openclaw/workspace/nightly-sidequests/2026-04-10-maker-slot-guard-visibility/active-tasks.md')

rows = []
for line in STATUS.read_text(encoding='utf-8', errors='replace').splitlines():
    line = line.strip()
    if not line:
        continue
    try:
        rows.append(json.loads(line))
    except json.JSONDecodeError:
        continue

latest: dict[tuple[str, str], dict] = {}
for row in rows:
    key = (row.get('agent', ''), row.get('task', ''))
    latest[key] = row

active = [
    r for r in latest.values()
    if r.get('stage') not in {'done', 'error'}
]
active.sort(key=lambda r: (r.get('agent', ''), r.get('task', '')))

lines = [
    '# Active Tasks Snapshot',
    '',
    f'- Source: {STATUS}',
    '',
    '| agent | task | stage | ts | note |',
    '|---|---|---|---|---|',
]

for r in active:
    note = (r.get('note') or '').replace('|', '\\|')
    lines.append(
        f"| {r.get('agent', '')} | {r.get('task', '')} | {r.get('stage', '')} | {r.get('ts', '')} | {note} |"
    )

OUT.write_text('\n'.join(lines) + '\n', encoding='utf-8')
print(OUT)
