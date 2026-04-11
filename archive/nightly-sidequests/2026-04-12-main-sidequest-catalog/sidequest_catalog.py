#!/usr/bin/env python3
"""
sidequest_catalog.py — Scan all nightly-sidequests, extract metadata, produce a unified index.

Zero-dependency (Python 3 stdlib only).

Usage:
  python3 sidequest_catalog.py /root/.openclaw/workspace/nightly-sidequests/
  python3 sidequest_catalog.py /root/.openclaw/workspace/nightly-sidequests/ --json
  python3 sidequest_catalog.py /root/.openclaw/workspace/nightly-sidequests/ --by agent
  python3 sidequest_catalog.py /root/.openclaw/workspace/nightly-sidequests/ --output catalog.md
"""

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# Pattern: YYYY-MM-DD-<agent>-<slug>
DIR_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})-([a-z]+)-(.+)$")


def parse_dirname(name: str):
    """Parse a sidequest directory name into (date, agent, slug)."""
    m = DIR_RE.match(name)
    if not m:
        return None
    return m.group(1), m.group(2), m.group(3)


def extract_description(dirpath: Path) -> str:
    """Extract a one-line description from README.md or first .py file."""
    readme = dirpath / "README.md"
    if readme.exists():
        for line in readme.read_text(encoding="utf-8", errors="replace").splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                return stripped[:120]
        # Fallback: use first heading
        for line in readme.read_text(encoding="utf-8", errors="replace").splitlines():
            stripped = line.strip().lstrip("#").strip()
            if stripped:
                return stripped[:120]

    # Try first .py file docstring
    for py in sorted(dirpath.glob("*.py")):
        try:
            text = py.read_text(encoding="utf-8", errors="replace")
            for line in text.splitlines():
                stripped = line.strip()
                if stripped.startswith('"""') or stripped.startswith("'''"):
                    desc = stripped[3:].rstrip('"\'').strip()
                    if desc:
                        return desc[:120]
        except Exception:
            pass

    return ""


def extract_files(dirpath: Path) -> list[str]:
    """List notable files (skip __pycache__, .pyc)."""
    return sorted(
        f.name
        for f in dirpath.iterdir()
        if f.is_file()
        and not f.name.startswith(".")
        and "__pycache__" not in str(f)
        and not f.name.endswith(".pyc")
    )


def scan_sidequests(root: str) -> list[dict]:
    """Scan root directory and return list of sidequest metadata dicts."""
    root_path = Path(root)
    if not root_path.is_dir():
        print(f"Error: {root} is not a directory", file=sys.stderr)
        sys.exit(1)

    entries = []
    for d in sorted(root_path.iterdir()):
        if not d.is_dir():
            continue
        parsed = parse_dirname(d.name)
        if not parsed:
            continue
        date_str, agent, slug = parsed
        desc = extract_description(d)
        files = extract_files(d)
        entries.append(
            {
                "dir": d.name,
                "date": date_str,
                "agent": agent,
                "slug": slug,
                "description": desc,
                "files": files,
                "file_count": len(files),
                "has_readme": (d / "README.md").exists(),
                "has_test": any("test" in f.lower() for f in files),
            }
        )
    return entries


def render_table(entries: list[dict]) -> str:
    """Render entries as a markdown table."""
    lines = []
    lines.append("| Date | Agent | Slug | Description | Files | README | Test |")
    lines.append("|------|-------|------|-------------|-------|--------|------|")
    for e in entries:
        lines.append(
            f"| {e['date']} | {e['agent']} | {e['slug']} "
            f"| {e['description'][:60]} | {e['file_count']} "
            f"| {'✅' if e['has_readme'] else '❌'} "
            f"| {'✅' if e['has_test'] else '❌'} |"
        )
    return "\n".join(lines)


def render_by_group(entries: list[dict], key: str) -> str:
    """Group entries by a field and render."""
    groups = defaultdict(list)
    for e in entries:
        groups[e[key]].append(e)

    lines = []
    for group_key in sorted(groups.keys()):
        items = groups[group_key]
        lines.append(f"\n## {group_key} ({len(items)} sidequests)\n")
        for e in items:
            desc = f" — {e['description'][:80]}" if e["description"] else ""
            lines.append(f"- **{e['date']}** `{e['slug']}`{desc}")
    return "\n".join(lines)


def render_stats(entries: list[dict]) -> str:
    """Render summary statistics."""
    if not entries:
        return "No sidequests found."

    dates = set(e["date"] for e in entries)
    agents = set(e["agent"] for e in entries)
    with_readme = sum(1 for e in entries if e["has_readme"])
    with_test = sum(1 for e in entries if e["has_test"])

    lines = [
        f"**Total sidequests:** {len(entries)}",
        f"**Date range:** {min(dates)} → {max(dates)}",
        f"**Active days:** {len(dates)}",
        f"**Agents:** {', '.join(sorted(agents))}",
        f"**With README:** {with_readme}/{len(entries)} ({100*with_readme//len(entries)}%)",
        f"**With tests:** {with_test}/{len(entries)} ({100*with_test//len(entries)}%)",
    ]

    # Per-agent breakdown
    agent_counts = defaultdict(int)
    for e in entries:
        agent_counts[e["agent"]] += 1
    lines.append("\n**Per agent:**")
    for a in sorted(agent_counts):
        lines.append(f"  - {a}: {agent_counts[a]}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Sidequest catalog indexer")
    parser.add_argument("root", help="Root directory of nightly-sidequests/")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    parser.add_argument("--by", choices=["agent", "date"], help="Group output")
    parser.add_argument("--output", "-o", help="Write markdown to file instead of stdout")
    parser.add_argument("--stats", action="store_true", help="Show summary statistics")
    args = parser.parse_args()

    entries = scan_sidequests(args.root)

    if not entries:
        print("No sidequests found.", file=sys.stderr)
        sys.exit(0)

    if args.json:
        print(json.dumps(entries, indent=2, ensure_ascii=False))
        return

    parts = []
    parts.append(f"# Sidequest Catalog\n")
    parts.append(f"_Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}_\n")

    if args.stats or not args.by:
        parts.append("## Statistics\n")
        parts.append(render_stats(entries))
        parts.append("")

    if args.by:
        parts.append(f"## Grouped by {args.by}\n")
        parts.append(render_by_group(entries, args.by))
        parts.append("")

    parts.append("## Full Index\n")
    parts.append(render_table(entries))
    parts.append("")

    md = "\n".join(parts)

    if args.output:
        Path(args.output).write_text(md, encoding="utf-8")
        print(f"Wrote {len(entries)} entries to {args.output}")
    else:
        print(md)


if __name__ == "__main__":
    main()
