#!/usr/bin/env python3
"""
nightly_digest.py — One-command summary of a nightly-lab run.

Usage:
    python3 nightly_digest.py [run_dir]

If run_dir is omitted, reads current-run.json to find the latest run.

Output: markdown digest to stdout covering:
  - Run metadata (date, status)
  - Per-agent task status + timestamps
  - Sidequest reports found
  - Overall completion %
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

NIGHTLY_LAB = Path("/root/.openclaw/workspace/nightly-lab")


def load_json(path: Path):
    if path.exists():
        return json.loads(path.read_text())
    return None


def parse_status_jsonl(path: Path):
    """Parse status.jsonl → list of dicts, newest last."""
    if not path.exists():
        return []
    entries = []
    for line in path.read_text().strip().splitlines():
        line = line.strip()
        if line:
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return entries


def fmt_ts(ts_str: str) -> str:
    """ISO timestamp → short readable form."""
    try:
        dt = datetime.fromisoformat(ts_str)
        return dt.strftime("%H:%M:%S")
    except Exception:
        return ts_str


def agent_stage_summary(entries: list, agent: str):
    """Return last stage + timestamp for an agent's team task."""
    relevant = [
        e for e in entries
        if e.get("agent") == agent and e.get("task") == "team"
    ]
    if not relevant:
        return None
    last = relevant[-1]
    return {
        "stage": last.get("stage", "?"),
        "ts": fmt_ts(last.get("timestamp", "")),
        "report": last.get("report", ""),
    }


def sidequest_summary(entries: list, agent: str):
    """Return last sidequest stage for an agent."""
    relevant = [
        e for e in entries
        if e.get("agent") == agent and e.get("task") == "sidequest"
    ]
    if not relevant:
        return None
    last = relevant[-1]
    return {
        "stage": last.get("stage", "?"),
        "ts": fmt_ts(last.get("timestamp", "")),
        "artifact": last.get("artifact", ""),
    }


def build_digest(run_dir: Path):
    run_json = load_json(run_dir / "run.json")
    if not run_json:
        return f"❌ No run.json found in {run_dir}"

    status_entries = parse_status_jsonl(run_dir / "status.jsonl")
    done = load_json(run_dir / "done.json")

    logical_date = run_json.get("logical_date", "?")
    created = run_json.get("created_at", "?")
    agents = run_json.get("agents", {})
    team_agents = agents.get("team", [])
    sidequest_agents = agents.get("sidequest", [])
    team_reports = run_json.get("team_reports", {})
    sidequest_reports = run_json.get("sidequest_reports", {})

    lines = []
    lines.append(f"# 🌙 Nightly Run Digest — {logical_date}")
    lines.append(f"")
    lines.append(f"**Created:** {created}")
    if done:
        lines.append(f"**Done at:** {done.get('completed_at', '?')}")
    else:
        lines.append(f"**Status:** 🔄 In Progress")
    lines.append(f"")

    # Team tasks
    lines.append(f"## Team Tasks")
    lines.append(f"")
    lines.append(f"| Agent | Stage | Time | Report |")
    lines.append(f"|-------|-------|------|--------|")
    completed_team = 0
    for agent in team_agents:
        info = agent_stage_summary(status_entries, agent)
        report_path = team_reports.get(agent, "")
        report_exists = Path(report_path).exists() if report_path else False
        report_icon = "✅" if report_exists else "—"
        if info:
            stage_icon = {"start": "🟡", "artifact": "🔵", "done": "✅"}.get(info["stage"], "⚪")
            lines.append(f"| {agent} | {stage_icon} {info['stage']} | {info['ts']} | {report_icon} |")
            if info["stage"] == "done":
                completed_team += 1
        else:
            lines.append(f"| {agent} | ⚪ not started | — | {report_icon} |")
    lines.append(f"")
    lines.append(f"**Team completion:** {completed_team}/{len(team_agents)}")
    lines.append(f"")

    # Sidequests
    lines.append(f"## Sidequests")
    lines.append(f"")
    lines.append(f"| Agent | Stage | Time | Artifact |")
    lines.append(f"|-------|-------|------|----------|")
    completed_sq = 0
    for agent in sidequest_agents:
        info = sidequest_summary(status_entries, agent)
        report_path = sidequest_reports.get(agent, "")
        report_exists = Path(report_path).exists() if report_path else False
        report_icon = "✅" if report_exists else "—"
        if info:
            stage_icon = {"start": "🟡", "artifact": "🔵", "done": "✅"}.get(info["stage"], "⚪")
            artifact = info.get("artifact", "")
            artifact_name = Path(artifact).name if artifact else "—"
            lines.append(f"| {agent} | {stage_icon} {info['stage']} | {info['ts']} | {artifact_name} |")
            if info["stage"] == "done":
                completed_sq += 1
        else:
            lines.append(f"| {agent} | ⚪ not started | — | {report_icon} |")
    lines.append(f"")
    lines.append(f"**Sidequest completion:** {completed_sq}/{len(sidequest_agents)}")
    lines.append(f"")

    # Overall
    total = len(team_agents) + len(sidequest_agents)
    completed = completed_team + completed_sq
    pct = int(completed / total * 100) if total else 0
    bar_len = 20
    filled = int(bar_len * pct / 100)
    bar = "█" * filled + "░" * (bar_len - filled)
    lines.append(f"## Overall Progress")
    lines.append(f"")
    lines.append(f"`{bar}` {pct}% ({completed}/{total})")
    lines.append(f"")

    return "\n".join(lines)


def main():
    if len(sys.argv) > 1:
        run_dir = Path(sys.argv[1])
    else:
        current = load_json(NIGHTLY_LAB / "current-run.json")
        if not current:
            print("❌ No current-run.json found", file=sys.stderr)
            sys.exit(1)
        run_dir = Path(current["run_root"])

    digest = build_digest(run_dir)
    print(digest)


if __name__ == "__main__":
    main()
