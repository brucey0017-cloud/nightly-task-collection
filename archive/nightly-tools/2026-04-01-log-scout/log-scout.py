#!/usr/bin/env python3
"""
log-scout: Fast morning triage for scattered logs.
Scans a directory, extracts WARN/ERROR lines, groups similar issues,
and prints a concise summary with hot spots and recent examples.
"""

import argparse
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


SEVERITY_PATTERNS = [
    re.compile(r"\bERROR\b", re.IGNORECASE),
    re.compile(r"\bWARN(ING)?\b", re.IGNORECASE),
    re.compile(r"\bCRITICAL\b", re.IGNORECASE),
    re.compile(r"\bFATAL\b", re.IGNORECASE),
    re.compile(r"\bEXCEPTION\b", re.IGNORECASE),
]

LOG_EXTENSIONS = {".log", ".txt", ".out", ".err"}

# Normalize variable content so similar lines group together
NORMALIZERS = [
    (re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.IGNORECASE), "<UUID>"),
    (re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}(?::\d+)?\b"), "<IP>"),
    (re.compile(r"/[^\s:]+"), "<PATH>"),
    (re.compile(r"\b0x[0-9a-f]+\b", re.IGNORECASE), "<HEX>"),
    (re.compile(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?"), "<DATETIME>"),
    (re.compile(r"\b\d{4}-\d{2}-\d{2}\b"), "<DATE>"),
    (re.compile(r"\b\d{2}:\d{2}:\d{2}(?:\.\d+)?\b"), "<TIME>"),
    (re.compile(r"\b\d+\.\d+\.\d+[a-z\-]*\b", re.IGNORECASE), "<VERSION>"),
    (re.compile(r"\b\d+\.\d+\b"), "<FLOAT>"),
    (re.compile(r"\b\d+\b"), "<NUM>"),
]


def has_severity(line: str) -> bool:
    return any(p.search(line) for p in SEVERITY_PATTERNS)


def normalize(line: str) -> str:
    # Strip common log prefixes (timestamp, level) for cleaner grouping
    text = line.strip()
    for pat, repl in NORMALIZERS:
        text = pat.sub(repl, text)
    # Collapse repeated whitespace
    text = " ".join(text.split())
    return text


def parse_timestamp(line: str):
    """Try to extract a timestamp from a log line for recency sorting."""
    # ISO-8601-ish
    m = re.search(r"(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)", line)
    if m:
        ts_str = m.group(1).replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(ts_str)
            if dt.tzinfo is not None:
                dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
            return dt
        except ValueError:
            pass
    # Common syslog-ish: Mar 31 14:23:01
    m = re.search(r"([A-Z][a-z]{2}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\b", line)
    if m:
        try:
            return datetime.strptime(m.group(1), "%b %d %H:%M:%S").replace(year=datetime.now().year)
        except ValueError:
            pass
    return None


def gather_files(target_dir: Path):
    for root, _, files in os.walk(target_dir):
        for name in files:
            p = Path(root) / name
            if p.suffix.lower() in LOG_EXTENSIONS:
                yield p


def scan_file(path: Path, max_lines_per_file: int = 50_000):
    hits = []
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as f:
            for i, line in enumerate(f):
                if i >= max_lines_per_file:
                    break
                line = line.rstrip("\n")
                if not line:
                    continue
                if has_severity(line):
                    hits.append((path, line))
    except OSError as exc:
        print(f"[warn] could not read {path}: {exc}", file=sys.stderr)
    return hits


def severity_score(line: str) -> int:
    upper = line.upper()
    if "FATAL" in upper or "CRITICAL" in upper:
        return 3
    if "ERROR" in upper or "EXCEPTION" in upper:
        return 2
    if "WARN" in upper:
        return 1
    return 0


def summarize(target_dir: Path):
    if not target_dir.exists() or not target_dir.is_dir():
        print(f"Error: {target_dir} is not a directory", file=sys.stderr)
        sys.exit(1)

    files = list(gather_files(target_dir))
    all_hits = []
    for f in files:
        all_hits.extend(scan_file(f))

    if not all_hits:
        print("No WARN/ERROR lines found.")
        return

    # Group by normalized signature
    sig_data = defaultdict(lambda: {"count": 0, "severity": 0, "examples": [], "files": set(), "latest_ts": None})
    for path, line in all_hits:
        sig = normalize(line)
        entry = sig_data[sig]
        entry["count"] += 1
        entry["severity"] = max(entry["severity"], severity_score(line))
        entry["files"].add(path)
        ts = parse_timestamp(line)
        if ts is not None:
            if entry["latest_ts"] is None or ts > entry["latest_ts"]:
                entry["latest_ts"] = ts
        # Keep a few recent-ish examples (prefer ones with timestamps)
        if len(entry["examples"]) < 3:
            entry["examples"].append(line)
        elif ts is not None and entry["latest_ts"] is not None and ts >= entry["latest_ts"]:
            entry["examples"][-1] = line

    # Sort groups: severity desc, then count desc, then recency desc
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    def sort_key(item):
        sig, data = item
        age = (now - data["latest_ts"]).total_seconds() if data["latest_ts"] else 999999999
        return (-data["severity"], -data["count"], age)

    sorted_sigs = sorted(sig_data.items(), key=sort_key)

    # Print summary
    total_hits = len(all_hits)
    total_files_scanned = len(files)
    unique_sigs = len(sorted_sigs)

    print("=" * 60)
    print(f"  LOG-SCOUT SUMMARY  |  {target_dir}")
    print("=" * 60)
    print(f"Files scanned : {total_files_scanned}")
    print(f"Issue lines   : {total_hits}")
    print(f"Unique groups : {unique_sigs}")
    print("-" * 60)

    # Top hot spots
    print("\nTOP HOT SPOTS (by severity + frequency)\n")
    for i, (sig, data) in enumerate(sorted_sigs[:15], start=1):
        sev_label = {3: "FATAL", 2: "ERROR", 1: "WARN", 0: "INFO"}.get(data["severity"], "?")
        files_str = ", ".join(str(p.relative_to(target_dir)) for p in sorted(data["files"])[:3])
        if len(data["files"]) > 3:
            files_str += f" (+{len(data['files']) - 3} more)"
        age_str = ""
        if data["latest_ts"]:
            secs = (now - data["latest_ts"]).total_seconds()
            if secs < 3600:
                age_str = f"  [latest {max(1, int(secs/60))}m ago]"
            elif secs < 86400:
                age_str = f"  [latest {max(1, int(secs/3600))}h ago]"
            else:
                age_str = f"  [latest {max(1, int(secs/86400))}d ago]"
        print(f"  {i}. [{sev_label}] x{data['count']}  {age_str}")
        print(f"     Signature: {sig[:100]}{'...' if len(sig) > 100 else ''}")
        print(f"     Files    : {files_str}")

    # Recent examples
    print("\nRECENT EXAMPLES\n")
    recent = sorted(
        [(sig, data) for sig, data in sorted_sigs if data["latest_ts"] is not None],
        key=lambda x: x[1]["latest_ts"],
        reverse=True,
    )[:10]
    for sig, data in recent:
        sev_label = {3: "FATAL", 2: "ERROR", 1: "WARN", 0: "INFO"}.get(data["severity"], "?")
        ex = data["examples"][0] if data["examples"] else sig
        print(f"  [{sev_label}] {ex[:120]}{'...' if len(ex) > 120 else ''}")

    print("\n" + "=" * 60)
    print("  End of report")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="log-scout: quick morning triage for log files")
    parser.add_argument("directory", help="Directory to scan")
    args = parser.parse_args()
    summarize(Path(args.directory))


if __name__ == "__main__":
    main()
