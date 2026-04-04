#!/usr/bin/env python3
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

STATUS_FILE = Path("/root/.openclaw/workspace/nightly-lab/runs/2026-04-04/status.jsonl")
OUT_FILE = Path(__file__).resolve().parent / "STATUS_DIGEST.md"


def load_events(path: Path):
    events = []
    if not path.exists():
        return events

    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue

        events.append(
            {
                "lineno": lineno,
                "ts": obj.get("ts", ""),
                "agent": obj.get("agent", ""),
                "task": obj.get("task", ""),
                "stage": obj.get("stage", ""),
                "artifact": obj.get("artifact", ""),
                "report": obj.get("report", ""),
                "error_code": obj.get("error_code", ""),
            }
        )
    return events


def build_markdown(events):
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    total_events = len(events)

    per_agent = Counter(e["agent"] or "(unknown)" for e in events)

    latest_stage = {}
    for e in events:
        key = (e["agent"] or "(unknown)", e["task"] or "(unknown)")
        latest_stage[key] = (e["ts"], e["stage"] or "(empty)")

    recent = events[-12:]

    lines = []
    lines.append("# Nightly Run Status Digest")
    lines.append("")
    lines.append(f"- Generated: {generated_at}")
    lines.append(f"- Source: `{STATUS_FILE}`")
    lines.append(f"- Total events: **{total_events}**")
    lines.append("")

    lines.append("## Per-agent event counts")
    if per_agent:
        for agent, count in sorted(per_agent.items(), key=lambda x: (-x[1], x[0])):
            lines.append(f"- `{agent}`: {count}")
    else:
        lines.append("- (no events)")
    lines.append("")

    lines.append("## Latest stage by agent-task")
    if latest_stage:
        for (agent, task), (ts, stage) in sorted(latest_stage.items()):
            lines.append(f"- `{agent}` / `{task}` -> `{stage}` ({ts or 'no-ts'})")
    else:
        lines.append("- (no data)")
    lines.append("")

    lines.append("## Latest 12 events")
    if recent:
        lines.append("- `ts | agent | task | stage | error_code`")
        for e in recent:
            lines.append(
                f"- `{e['ts'] or 'no-ts'} | {e['agent'] or '-'} | {e['task'] or '-'} | {e['stage'] or '-'} | {e['error_code'] or '-'}`"
            )
    else:
        lines.append("- (no events)")
    lines.append("")

    return "\n".join(lines)


def main():
    events = load_events(STATUS_FILE)
    md = build_markdown(events)
    OUT_FILE.write_text(md, encoding="utf-8")
    print(str(OUT_FILE))


if __name__ == "__main__":
    main()
