#!/usr/bin/env python3
"""
CronFlow: zero-dependency cron visibility CLI.

- Lists user-accessible cron jobs
- Computes a simple next run time
- Groups jobs by near-term buckets
- Detects same-minute overlaps
"""

from __future__ import annotations

import argparse
import datetime as dt
import getpass
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple


@dataclass
class CronEntry:
    source: str
    raw_line: str
    schedule: str
    command: str
    enabled: bool
    next_run: Optional[dt.datetime]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="CronFlow - cron visibility in one glance")
    p.add_argument("--demo", action="store_true", help="run with embedded sample cron data")
    p.add_argument("--test", action="store_true", help="alias of --demo")
    p.add_argument("--limit", type=int, default=40, help="max rows to print (default: 40)")
    return p.parse_args()


def read_user_crontab() -> List[Tuple[str, str]]:
    rows: List[Tuple[str, str]] = []

    # 1) crontab -l (most portable user path)
    try:
        proc = subprocess.run(
            ["crontab", "-l"],
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            for line in proc.stdout.splitlines():
                rows.append(("crontab -l", line))
    except FileNotFoundError:
        pass

    # 2) ~/.crontab (some teams keep local file snapshots)
    home_cron = Path.home() / ".crontab"
    if home_cron.exists() and home_cron.is_file():
        try:
            for line in home_cron.read_text(encoding="utf-8", errors="replace").splitlines():
                rows.append((str(home_cron), line))
        except OSError:
            pass

    # 3) /var/spool/cron/$USER when readable (no sudo required)
    user = getpass.getuser()
    spool = Path("/var/spool/cron") / user
    if spool.exists() and spool.is_file() and os.access(spool, os.R_OK):
        try:
            for line in spool.read_text(encoding="utf-8", errors="replace").splitlines():
                rows.append((str(spool), line))
        except OSError:
            pass

    return rows


def demo_rows() -> List[Tuple[str, str]]:
    return [
        ("demo", "# Demo cron file"),
        ("demo", "*/15 * * * * /usr/local/bin/heartbeat"),
        ("demo", "30 2 * * * /usr/local/bin/nightly_backup"),
        ("demo", "30 2 * * * /usr/local/bin/cleanup_tmp"),
        ("demo", "# 0 4 * * 1 /usr/local/bin/disabled_weekly"),
        ("demo", "@daily /usr/local/bin/daily_report"),
        ("demo", "MAILTO=ops@example.com"),
    ]


def is_env_assignment(line: str) -> bool:
    return bool(re.match(r"^[A-Za-z_][A-Za-z0-9_]*\s*=", line.strip()))


def parse_cron_line(source: str, line: str, now: dt.datetime) -> Optional[CronEntry]:
    raw = line.rstrip("\n")
    stripped = raw.strip()
    if not stripped:
        return None

    enabled = True
    candidate = stripped
    if stripped.startswith("#"):
        enabled = False
        candidate = stripped[1:].strip()
        if not candidate:
            return None

    if is_env_assignment(candidate):
        return None

    # @daily / @hourly style
    if candidate.startswith("@"):
        parts = candidate.split(None, 1)
        if len(parts) < 2:
            return None
        schedule = parts[0]
        command = parts[1]
        next_run = next_run_for_macro(schedule, now) if enabled else None
        return CronEntry(source, raw, schedule, command, enabled, next_run)

    parts = candidate.split()
    if len(parts) < 6:
        return None

    minute, hour, dom, month, dow = parts[0:5]
    command = " ".join(parts[5:])
    schedule = " ".join(parts[:5])

    next_run = None
    if enabled:
        next_run = next_run_for_fields(minute, hour, dom, month, dow, now)

    return CronEntry(source, raw, schedule, command, enabled, next_run)


def next_run_for_macro(macro: str, now: dt.datetime) -> Optional[dt.datetime]:
    base = now.replace(second=0, microsecond=0)
    m = macro.lower()

    if m == "@hourly":
        cand = base.replace(minute=0) + dt.timedelta(hours=1)
        return cand
    if m in {"@daily", "@midnight"}:
        cand = base.replace(hour=0, minute=0) + dt.timedelta(days=1)
        return cand
    if m == "@weekly":
        # Sunday 00:00
        days_ahead = (6 - base.weekday()) % 7  # Python Mon=0...Sun=6
        cand = base.replace(hour=0, minute=0) + dt.timedelta(days=days_ahead)
        if cand <= base:
            cand += dt.timedelta(days=7)
        return cand
    if m == "@monthly":
        y, mo = base.year, base.month
        if mo == 12:
            y, mo = y + 1, 1
        else:
            mo += 1
        return dt.datetime(y, mo, 1, 0, 0)
    if m == "@yearly" or m == "@annually":
        return dt.datetime(base.year + 1, 1, 1, 0, 0)
    if m == "@reboot":
        return None
    return None


def parse_field(field: str, min_v: int, max_v: int, sunday_alias: bool = False) -> Optional[set]:
    values = set()

    def normalize(v: int) -> int:
        if sunday_alias and v == 7:
            return 0
        return v

    for part in field.split(","):
        part = part.strip()
        if not part:
            return None

        if "/" in part:
            base, step_s = part.split("/", 1)
            if not step_s.isdigit() or int(step_s) <= 0:
                return None
            step = int(step_s)
        else:
            base, step = part, 1

        if base == "*":
            start, end = min_v, max_v
        elif "-" in base:
            a_s, b_s = base.split("-", 1)
            if not (a_s.isdigit() and b_s.isdigit()):
                return None
            start, end = int(a_s), int(b_s)
        elif base.isdigit():
            start = end = int(base)
        else:
            return None

        if start < min_v or end > max_v or start > end:
            return None

        for v in range(start, end + 1, step):
            values.add(normalize(v))

    return values


def next_run_for_fields(minute: str, hour: str, dom: str, month: str, dow: str, now: dt.datetime) -> Optional[dt.datetime]:
    mins = parse_field(minute, 0, 59)
    hrs = parse_field(hour, 0, 23)
    doms = parse_field(dom, 1, 31)
    months = parse_field(month, 1, 12)
    dows = parse_field(dow, 0, 7, sunday_alias=True)
    if None in (mins, hrs, doms, months, dows):
        return None

    probe = (now.replace(second=0, microsecond=0) + dt.timedelta(minutes=1))
    horizon = probe + dt.timedelta(days=8)

    while probe <= horizon:
        py_weekday = probe.weekday()  # Mon=0..Sun=6
        cron_dow = (py_weekday + 1) % 7  # Sun=0
        if (
            probe.minute in mins
            and probe.hour in hrs
            and probe.day in doms
            and probe.month in months
            and cron_dow in dows
        ):
            return probe
        probe += dt.timedelta(minutes=1)

    return None


def bucket_for(now: dt.datetime, when: Optional[dt.datetime]) -> str:
    if when is None:
        return "Unknown"
    delta = when - now
    if delta <= dt.timedelta(hours=1):
        return "Next Hour"
    if when.date() == now.date():
        return "Today"
    if delta <= dt.timedelta(days=7):
        return "This Week"
    return "Later"


def format_rel(now: dt.datetime, when: Optional[dt.datetime]) -> str:
    if when is None:
        return "unknown"
    delta = when - now
    mins = int(delta.total_seconds() // 60)
    if mins < 0:
        return "passed"
    if mins < 60:
        return f"in {mins}m"
    hrs = mins // 60
    rem = mins % 60
    if hrs < 48:
        return f"in {hrs}h{rem:02d}m"
    days = hrs // 24
    return f"in {days}d"


def collect_entries(rows: Sequence[Tuple[str, str]], now: dt.datetime) -> List[CronEntry]:
    entries: List[CronEntry] = []
    for source, line in rows:
        parsed = parse_cron_line(source, line, now)
        if parsed:
            entries.append(parsed)
    return entries


def find_conflicts(entries: Sequence[CronEntry]) -> List[Tuple[str, List[CronEntry]]]:
    buckets = {}
    for e in entries:
        if not e.enabled or e.next_run is None:
            continue
        k = e.next_run.strftime("%Y-%m-%d %H:%M")
        buckets.setdefault(k, []).append(e)

    conflicts = [(k, v) for k, v in buckets.items() if len(v) > 1]
    conflicts.sort(key=lambda x: x[0])
    return conflicts


def print_table(entries: Sequence[CronEntry], now: dt.datetime, limit: int) -> None:
    ordered = sorted(
        entries,
        key=lambda e: (e.next_run is None, e.next_run or dt.datetime.max),
    )

    print("\nJobs")
    print("-" * 96)
    print(f"{'Next Run':<18} {'Relative':<10} {'State':<9} {'Bucket':<10} {'Schedule':<18} Command")
    print("-" * 96)

    for e in ordered[: max(1, limit)]:
        nxt = e.next_run.strftime("%m-%d %H:%M") if e.next_run else "(unknown)"
        rel = format_rel(now, e.next_run)
        state = "enabled" if e.enabled else "disabled"
        bucket = bucket_for(now, e.next_run)
        cmd = e.command
        if len(cmd) > 42:
            cmd = cmd[:39] + "..."
        print(f"{nxt:<18} {rel:<10} {state:<9} {bucket:<10} {e.schedule:<18} {cmd}")

    print("-" * 96)


def main() -> int:
    args = parse_args()
    now = dt.datetime.now().replace(second=0, microsecond=0)

    use_demo = args.demo or args.test
    rows = demo_rows() if use_demo else read_user_crontab()

    # dedupe same source+line combos
    deduped: List[Tuple[str, str]] = []
    seen = set()
    for item in rows:
        if item not in seen:
            seen.add(item)
            deduped.append(item)

    entries = collect_entries(deduped, now)
    enabled = [e for e in entries if e.enabled]
    disabled = [e for e in entries if not e.enabled]
    conflicts = find_conflicts(entries)

    mode = "DEMO" if use_demo else "LIVE"
    print(f"CronFlow [{mode}] — scanned {len(set(s for s, _ in deduped))} source(s)")
    print(
        f"Summary: {len(entries)} jobs, {len(enabled)} enabled, {len(disabled)} disabled, "
        f"{len(conflicts)} same-minute conflict(s)"
    )

    if not entries:
        print("No parsable cron jobs found. Try --demo to preview output.")
        return 0

    print_table(entries, now, args.limit)

    if conflicts:
        print("\n⚠️ Potential same-minute overlaps")
        for stamp, jobs in conflicts:
            names = [j.command.split()[0] if j.command.split() else j.command for j in jobs]
            print(f"- {stamp}: {len(jobs)} jobs -> {', '.join(names)}")
    else:
        print("\n✓ All clear — no overlapping jobs")

    # Show provenance to help trust output
    print("\nSources")
    for src in sorted(set(s for s, _ in deduped)):
        print(f"- {src}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
