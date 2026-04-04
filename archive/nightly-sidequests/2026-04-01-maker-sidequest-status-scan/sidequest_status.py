#!/usr/bin/env python3
"""Nightly sidequest report status scanner (stdlib-only)."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Dict, Any

DEFAULT_ROOT = "/root/.openclaw/workspace/nightly-lab/sidequests"
FIELD_RE = re.compile(r"^\s*-\s*([^:]+):\s*(.*)\s*$")


@dataclass
class Report:
    date: str
    agent: str
    path: str
    status: str
    built: str
    valid_template: bool


@dataclass
class ScanError:
    path: str
    error: str


def parse_report(path: Path) -> Report:
    text = path.read_text(encoding="utf-8", errors="replace")
    fields: Dict[str, str] = {}

    for line in text.splitlines():
        m = FIELD_RE.match(line)
        if not m:
            continue
        key = m.group(1).strip().lower()
        value = m.group(2).strip()
        fields[key] = value

    built = fields.get("built / explored", "")
    status = fields.get("status", "")
    valid_template = "# Sidequest Report" in text

    return Report(
        date=path.parent.name,
        agent=path.stem,
        path=str(path),
        status=status or "(missing)",
        built=built or "(missing)",
        valid_template=valid_template,
    )


def iter_report_files(root: Path, date_filter: str | None) -> Iterable[Path]:
    if date_filter:
        d = root / date_filter
        if not d.exists() or not d.is_dir():
            return []
        return sorted(p for p in d.glob("*.md") if p.is_file())

    files: List[Path] = []
    for d in sorted(p for p in root.iterdir() if p.is_dir()):
        files.extend(sorted(p for p in d.glob("*.md") if p.is_file()))
    return files


def scan(root: Path, date_filter: str | None) -> Dict[str, Any]:
    reports: List[Report] = []
    errors: List[ScanError] = []

    if not root.exists() or not root.is_dir():
        return {
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "root": str(root),
            "dateFilter": date_filter,
            "totalReports": 0,
            "statusCounts": {},
            "reports": [],
            "errors": [{"path": str(root), "error": "root directory not found"}],
        }

    for p in iter_report_files(root, date_filter):
        try:
            reports.append(parse_report(p))
        except Exception as exc:  # defensive
            errors.append(ScanError(path=str(p), error=str(exc)))

    status_counts = Counter(r.status for r in reports)

    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "root": str(root),
        "dateFilter": date_filter,
        "totalReports": len(reports),
        "statusCounts": dict(status_counts),
        "reports": [asdict(r) for r in reports],
        "errors": [asdict(e) for e in errors],
    }


def render_text(result: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append("Sidequest Status Summary")
    lines.append(f"- Root: {result['root']}")
    lines.append(f"- Date filter: {result['dateFilter'] or '(all)'}")
    lines.append(f"- Total reports: {result['totalReports']}")

    if result["statusCounts"]:
        lines.append("- Status counts:")
        for status, count in sorted(result["statusCounts"].items(), key=lambda x: (-x[1], x[0])):
            lines.append(f"  - {status}: {count}")
    else:
        lines.append("- Status counts: (none)")

    if result["reports"]:
        lines.append("- Reports:")
        for r in sorted(result["reports"], key=lambda x: (x["date"], x["agent"])):
            built = r["built"]
            if len(built) > 80:
                built = built[:77] + "..."
            tpl = "ok" if r["valid_template"] else "template-missing"
            lines.append(
                f"  - {r['date']} / {r['agent']}: status={r['status']} | template={tpl} | built={built}"
            )
    else:
        lines.append("- Reports: (none)")

    if result["errors"]:
        lines.append("- Errors:")
        for e in result["errors"]:
            lines.append(f"  - {e['path']}: {e['error']}")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize nightly sidequest markdown reports.")
    parser.add_argument("--root", default=DEFAULT_ROOT, help="Report root directory.")
    parser.add_argument("--date", default=None, help="Optional date filter: YYYY-MM-DD")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()

    result = scan(Path(args.root), args.date)

    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(render_text(result))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
