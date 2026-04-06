#!/usr/bin/env python3
"""
Nightly Lab Run Dashboard
Reads current-run.json + status.jsonl + team reports → human-readable summary.

Usage:
    python3 run_dashboard.py                          # auto-detect current run
    python3 run_dashboard.py --run /path/to/run.json  # specify run
    python3 run_dashboard.py --json                   # machine-readable output
    python3 run_dashboard.py --watch 10               # refresh every N seconds
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# ── helpers ──────────────────────────────────────────────────────────────────

NIGHTLY_LAB = Path(__file__).resolve().parent.parent.parent / "nightly-lab"

STAGE_ORDER = ["start", "artifact", "done", "error"]
STAGE_EMOJI = {
    "start":   "🔄",
    "artifact": "📦",
    "done":    "✅",
    "error":   "❌",
}
AGENT_COLORS = {
    "commander": "🔵",
    "maker":     "🟢",
    "vibe":      "🟣",
    "killjoy":   "🔴",
    "main":      "⚪",
}

def load_json(path):
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None

def load_status_lines(status_file):
    lines = []
    try:
        with open(status_file) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        lines.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    except FileNotFoundError:
        pass
    return lines

def load_report(path):
    try:
        with open(path) as f:
            return f.read()
    except FileNotFoundError:
        return None

def latest_stage_for_agent(events, agent, task):
    """Return the latest (stage, timestamp) for an agent+task combo."""
    relevant = [
        e for e in events
        if e.get("agent") == agent and e.get("task") == task
    ]
    if not relevant:
        return None, None
    # events are appended chronologically, last is newest
    last = relevant[-1]
    return last.get("stage"), last.get("ts")

def read_sidequest_report(path):
    """Extract key fields from a sidequest report markdown."""
    content = load_report(path)
    if not content:
        return None
    fields = {}
    for line in content.splitlines():
        if line.startswith("- **"):
            key = line.split("**")[1].strip(": ")
            val = line.split("**")[2].strip() if "**" in line[3:] else ""
            fields[key] = val
        elif line.startswith("- "):
            parts = line[2:].split(": ", 1)
            if len(parts) == 2:
                fields[parts[0]] = parts[1]
    return fields

# ── main dashboard ───────────────────────────────────────────────────────────

def build_dashboard(run_json_path=None):
    if run_json_path:
        run_data = load_json(run_json_path)
    else:
        # auto-detect from current-run.json
        cr = NIGHTLY_LAB / "current-run.json"
        run_data = load_json(cr)
        if run_data:
            run_json_path = Path(run_data["run_root"]) / "run.json"
            run_data = load_json(run_json_path) or run_data

    if not run_data:
        return {"error": "No current run found"}

    run_id = run_data.get("run_id", "unknown")
    logical_date = run_data.get("logical_date", "unknown")
    status_file = run_data.get("status_file", "")
    roots = run_data.get("roots", {})
    team_reports = run_data.get("team_reports", {})
    sq_reports = run_data.get("sidequest_reports", {})
    agents = run_data.get("agents", {})
    budgets = run_data.get("budgets", {})

    events = load_status_lines(status_file)
    now = datetime.now(timezone.utc)

    # ── team tasks ───────────────────────────────────────────────────────
    team = []
    for agent in agents.get("team", []):
        report_path = team_reports.get(agent, "")
        stage, ts = latest_stage_for_agent(events, agent, "team")
        report_content = load_report(report_path)
        has_report = bool(report_content and report_content.strip())

        entry = {
            "agent": agent,
            "emoji": AGENT_COLORS.get(agent, "⚫"),
            "stage": stage or "pending",
            "ts": ts,
            "has_report": has_report,
            "report_path": report_path,
        }
        team.append(entry)

    # ── sidequest tasks ──────────────────────────────────────────────────
    sidequests = []
    for agent in agents.get("sidequest", []):
        report_path = sq_reports.get(agent, "")
        stage, ts = latest_stage_for_agent(events, agent, "sidequest")
        sq_data = read_sidequest_report(report_path)

        entry = {
            "agent": agent,
            "emoji": AGENT_COLORS.get(agent, "⚫"),
            "stage": stage or "pending",
            "ts": ts,
            "report_path": report_path,
            "report_data": sq_data,
        }
        sidequests.append(entry)

    return {
        "run_id": run_id,
        "logical_date": logical_date,
        "now": now.isoformat(),
        "budgets": budgets,
        "team": team,
        "sidequests": sidequests,
        "event_count": len(events),
        "run_root": run_data.get("run_root", ""),
        "roots": roots,
    }

def render_text(dash):
    if "error" in dash:
        return f"❌ {dash['error']}"

    lines = []
    lines.append("═" * 60)
    lines.append(f"  NIGHTLY LAB DASHBOARD — {dash['logical_date']}")
    lines.append("═" * 60)
    lines.append(f"  Run ID: {dash['run_id']}")
    lines.append(f"  Events: {dash['event_count']}")
    budgets = dash.get("budgets", {})
    if budgets:
        lines.append(f"  Budgets: team={budgets.get('team_minutes','?')}min  "
                      f"sidequest={budgets.get('sidequest_minutes','?')}min")
    lines.append("")

    # Team section
    lines.append("─" * 60)
    lines.append("  TEAM TASKS")
    lines.append("─" * 60)
    for t in dash.get("team", []):
        emoji = t["emoji"]
        stage = t["stage"]
        stage_icon = STAGE_EMOJI.get(stage, "⏳")
        report_icon = "📄" if t["has_report"] else "  "
        ts_str = f"  @ {t['ts'][-8:]}" if t.get("ts") else ""
        lines.append(f"  {emoji} {t['agent']:<12} {stage_icon} {stage:<10}{ts_str} {report_icon}")
    lines.append("")

    # Sidequest section
    lines.append("─" * 60)
    lines.append("  SIDEQUESTS")
    lines.append("─" * 60)
    for sq in dash.get("sidequests", []):
        emoji = sq["emoji"]
        stage = sq["stage"]
        stage_icon = STAGE_EMOJI.get(stage, "⏳")
        ts_str = f"  @ {sq['ts'][-8:]}" if sq.get("ts") else ""
        lines.append(f"  {emoji} {sq['agent']:<12} {stage_icon} {stage:<10}{ts_str}")
        rd = sq.get("report_data")
        if rd:
            built = rd.get("Built / explored", rd.get("Built", ""))
            if built:
                lines.append(f"     ↳ {built}")
    lines.append("")

    # Summary counts
    all_entries = dash.get("team", []) + dash.get("sidequests", [])
    done = sum(1 for e in all_entries if e["stage"] == "done")
    errors = sum(1 for e in all_entries if e["stage"] == "error")
    pending = sum(1 for e in all_entries if e["stage"] == "pending")
    active = len(all_entries) - done - errors - pending

    lines.append("─" * 60)
    lines.append(f"  Summary: {done} done  {active} active  {pending} pending  {errors} errors")
    lines.append("═" * 60)
    return "\n".join(lines)

# ── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Nightly Lab Run Dashboard")
    parser.add_argument("--run", help="Path to run.json")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--watch", type=int, metavar="SEC",
                        help="Auto-refresh every N seconds")
    args = parser.parse_args()

    if args.watch:
        try:
            while True:
                dash = build_dashboard(args.run)
                # clear screen
                os.system("clear" if os.name != "nt" else "cls")
                if args.json:
                    print(json.dumps(dash, indent=2, default=str))
                else:
                    print(render_text(dash))
                print(f"\n  Refreshing every {args.watch}s  |  Ctrl+C to stop")
                time.sleep(args.watch)
        except KeyboardInterrupt:
            pass
    else:
        dash = build_dashboard(args.run)
        if args.json:
            print(json.dumps(dash, indent=2, default=str))
        else:
            print(render_text(dash))

if __name__ == "__main__":
    main()
