#!/usr/bin/env python3
"""Generate a compact markdown dashboard from nightly-lab status.jsonl."""

import json
from pathlib import Path

RUN_FILE = Path("/root/.openclaw/workspace/nightly-lab/current-run.json")
OUT_FILE = Path("/root/.openclaw/workspace/nightly-sidequests/2026-04-03-maker-status-glance/status-glance.md")


def load_run() -> dict:
    return json.loads(RUN_FILE.read_text())


def load_status_entries(status_file: Path) -> list[dict]:
    items: list[dict] = []
    for line in status_file.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            items.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return items


def latest_by_agent_task(entries: list[dict]) -> dict[tuple[str, str], dict]:
    latest: dict[tuple[str, str], dict] = {}
    for entry in entries:
        key = (entry.get("agent", ""), entry.get("task", ""))
        latest[key] = entry
    return latest


def render_table_rows(agents: list[str], task: str, latest: dict[tuple[str, str], dict]) -> list[str]:
    rows: list[str] = []
    for agent in agents:
        item = latest.get((agent, task))
        if not item:
            rows.append(f"| {agent} | {task} | (none) | - | - |")
            continue
        stage = item.get("stage", "")
        ts = item.get("ts", "")
        artifact = item.get("artifact", "") or "-"
        rows.append(f"| {agent} | {task} | {stage} | {ts} | {artifact} |")
    return rows


def build_markdown(run: dict, entries: list[dict]) -> str:
    latest = latest_by_agent_task(entries)
    team_agents = run.get("agents", {}).get("team", [])
    side_agents = run.get("agents", {}).get("sidequest", [])

    out: list[str] = []
    out.append("# Nightly Run Status Glance")
    out.append("")
    out.append(f"- Run ID: `{run.get('run_id')}`")
    out.append(f"- Logical date: `{run.get('logical_date')}`")
    out.append(f"- Status file: `{run.get('status_file')}`")
    out.append("")

    out.append("## Team task latest stage")
    out.append("")
    out.append("| Agent | Task | Stage | Timestamp (UTC) | Artifact |")
    out.append("|---|---|---|---|---|")
    out.extend(render_table_rows(team_agents, "team", latest))
    out.append("")

    out.append("## Sidequest latest stage")
    out.append("")
    out.append("| Agent | Task | Stage | Timestamp (UTC) | Artifact |")
    out.append("|---|---|---|---|---|")
    out.extend(render_table_rows(side_agents, "sidequest", latest))
    out.append("")

    out.append("## Last 8 status events")
    out.append("")
    for item in entries[-8:]:
        out.append(
            f"- `{item.get('ts', '')}` | `{item.get('agent', '')}` `{item.get('task', '')}` `{item.get('stage', '')}` | artifact: `{item.get('artifact', '') or '-'}`"
        )

    out.append("")
    out.append("## Refresh")
    out.append("")
    out.append("```bash")
    out.append("python3 /root/.openclaw/workspace/nightly-sidequests/2026-04-03-maker-status-glance/refresh_status_glance.py")
    out.append("```")
    out.append("")

    return "\n".join(out)


def main() -> None:
    run = load_run()
    status_file = Path(run["status_file"])
    entries = load_status_entries(status_file)
    OUT_FILE.write_text(build_markdown(run, entries))
    print(str(OUT_FILE))


if __name__ == "__main__":
    main()
