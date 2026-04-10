#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Tuple

TERMINAL_STAGES = {"done", "error"}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Summarize latest status per (agent, task) from nightly status.jsonl")
    p.add_argument("--status-file", help="Path to status.jsonl. Defaults to current-run.json -> status_file")
    p.add_argument("--now-utc", help="Override current time with ISO8601 timestamp (UTC recommended)")
    p.add_argument("--stale-min", type=int, default=30, help="Mark non-terminal rows stale when age >= stale-min")
    p.add_argument("--format", choices=["text", "markdown"], default="text")
    return p.parse_args()


def parse_iso(ts: str | None) -> datetime | None:
    if not ts:
        return None
    ts = ts.strip()
    if not ts:
        return None
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(ts)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def default_status_file() -> Path:
    current_run = Path("/root/.openclaw/workspace/nightly-lab/current-run.json")
    data = json.loads(current_run.read_text(encoding="utf-8"))
    return Path(data["status_file"])


def load_latest_rows(status_path: Path) -> Dict[Tuple[str, str], Dict[str, Any]]:
    latest: Dict[Tuple[str, str], Dict[str, Any]] = {}
    if not status_path.exists():
        return latest

    for line in status_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue

        agent = str(row.get("agent", "")).strip().lower() or "?"
        task = str(row.get("task", "")).strip().lower() or "?"
        key = (agent, task)

        new_ts = parse_iso(row.get("ts"))
        old_ts = parse_iso(latest.get(key, {}).get("ts"))
        if key not in latest or (new_ts and (not old_ts or new_ts >= old_ts)):
            latest[key] = row

    return latest


def shorten(s: str, n: int = 40) -> str:
    s = (s or "").replace("\n", " ").strip()
    if len(s) <= n:
        return s
    return s[: n - 1] + "…"


def as_int_age_min(now_utc: datetime, row: Dict[str, Any]) -> int | None:
    ts = parse_iso(row.get("ts"))
    if not ts:
        return None
    return max(0, int((now_utc - ts).total_seconds() // 60))


def render_text(rows: list[dict[str, Any]]) -> str:
    headers = ["agent", "task", "stage", "age_min", "stale", "note", "artifact"]
    widths = {h: len(h) for h in headers}
    for r in rows:
        for h in headers:
            widths[h] = min(60, max(widths[h], len(str(r[h]))))

    def fmt_row(r: dict[str, Any]) -> str:
        return "  ".join(str(r[h]).ljust(widths[h]) for h in headers)

    line = "  ".join("-" * widths[h] for h in headers)
    out = [fmt_row({h: h for h in headers}), line]
    out.extend(fmt_row(r) for r in rows)
    return "\n".join(out)


def render_markdown(rows: list[dict[str, Any]]) -> str:
    headers = ["agent", "task", "stage", "age_min", "stale", "note", "artifact"]
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    for r in rows:
        vals = [str(r[h]).replace("|", "\\|") for h in headers]
        out.append("| " + " | ".join(vals) + " |")
    return "\n".join(out)


def main() -> int:
    args = parse_args()

    status_path = Path(args.status_file) if args.status_file else default_status_file()
    now_utc = parse_iso(args.now_utc) if args.now_utc else datetime.now(timezone.utc)
    if now_utc is None:
        raise SystemExit("Invalid --now-utc format")

    latest = load_latest_rows(status_path)

    rows: list[dict[str, Any]] = []
    counts = {"active": 0, "stale": 0, "done": 0, "error": 0}

    for (agent, task), row in sorted(latest.items()):
        stage = str(row.get("stage", "")).strip().lower() or "?"
        age_min = as_int_age_min(now_utc, row)
        stale = stage not in TERMINAL_STAGES and age_min is not None and age_min >= args.stale_min

        if stage == "done":
            counts["done"] += 1
        elif stage == "error":
            counts["error"] += 1
        else:
            counts["active"] += 1
            if stale:
                counts["stale"] += 1

        rows.append(
            {
                "agent": agent,
                "task": task,
                "stage": stage,
                "age_min": age_min if age_min is not None else "?",
                "stale": "STALE" if stale else "",
                "note": shorten(str(row.get("note", "")), 40),
                "artifact": shorten(str(row.get("artifact", "")), 40),
            }
        )

    if rows:
        if args.format == "markdown":
            print(render_markdown(rows))
        else:
            print(render_text(rows))
    else:
        print(f"No valid rows found in: {status_path}")

    print(
        f"\ncounts: active={counts['active']} stale={counts['stale']} done={counts['done']} error={counts['error']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
