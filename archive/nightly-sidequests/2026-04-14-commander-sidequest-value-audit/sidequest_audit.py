#!/usr/bin/env python3
"""
sidequest_audit.py — Audit nightly-lab sidequests for real value.

Scans all sidequest folders, reads REPORT.md, inspects actual artifacts,
and produces a quality/value assessment.

Usage:
    python3 sidequest_audit.py [--sidequest-dir DIR] [--json] [--by-agent]

Output: markdown report (or JSON) with per-agent stats, quality flags,
        and overall system health.
"""

import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

DEFAULT_SQ_DIR = Path("/root/.openclaw/workspace/nightly-sidequests")

# Patterns for extracting metadata from REPORT.md
RE_DATE = re.compile(r"Date:\s*(.+)")
RE_AGENT = re.compile(r"Agent:\s*(.+)")
RE_STATUS = re.compile(r"Status:\s*(.+)")
RE_TEST_CMD = re.compile(r"Test command:\s*`?([^`\n]+)`?")
RE_FOLDER = re.compile(r"Folder:\s*(.+)")
RE_FILES = re.compile(r"Files:\s*(.+)")


def fmt_size(n: int) -> str:
    """Bytes → human readable."""
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f}{unit}"
        n /= 1024
    return f"{n:.0f}TB"


def classify_file(fname: str) -> str:
    """Classify a file by extension."""
    ext = Path(fname).suffix.lower()
    if ext in (".py", ".sh", ".js", ".ts"):
        return "code"
    if ext == ".md":
        return "doc"
    if ext in (".json", ".yaml", ".yml", ".toml"):
        return "config"
    if ext in (".txt", ".log", ".csv"):
        return "data"
    return "other"


def score_sidequest(sq_dir: Path) -> dict:
    """Analyze a single sidequest directory. Returns a score dict."""
    result = {
        "path": str(sq_dir),
        "name": sq_dir.name,
        "exists": sq_dir.is_dir(),
        "report_found": False,
        "report_parsed": False,
        "date": None,
        "agent": None,
        "status": None,
        "test_command": None,
        "artifact_folder": None,
        "listed_files": [],
        "actual_files": [],
        "actual_file_details": [],
        "total_bytes": 0,
        "code_files": 0,
        "doc_files": 0,
        "config_files": 0,
        "other_files": 0,
        "has_code": False,
        "code_bytes": 0,
        "quality_flags": [],
        "quality_score": 0,  # 0-100
    }

    if not sq_dir.is_dir():
        result["quality_flags"].append("MISSING_DIR")
        return result

    # Parse date and agent from directory name first (needed for centralized report lookup)
    m = re.match(r"(\d{4}-\d{2}-\d{2})", sq_dir.name)
    if m:
        result["date"] = m.group(1)
    known = {"commander", "maker", "vibe", "killjoy", "main"}
    for p in sq_dir.name.split("-"):
        if p.lower() in known:
            result["agent"] = p.lower()
            break

    # Find REPORT.md — check inside the artifact dir AND the centralized sidequest reports
    report_path = None
    for candidate in ("REPORT.md", "report.md"):
        if (sq_dir / candidate).exists():
            report_path = sq_dir / candidate
            break

    # Also check centralized reports: /root/.openclaw/workspace/nightly-lab/sidequests/<date>/<agent>.md
    if not report_path and result.get("date") and result.get("agent"):
        centralized = Path("/root/.openclaw/workspace/nightly-lab/sidequests") / result["date"] / f"{result['agent']}.md"
        if centralized.exists():
            report_path = centralized

    if report_path:
        result["report_found"] = True
        try:
            text = report_path.read_text(errors="replace")
            result["report_parsed"] = True

            m = RE_DATE.search(text)
            if m:
                result["date"] = m.group(1).strip()
            m = RE_AGENT.search(text)
            if m:
                result["agent"] = m.group(1).strip()
            m = RE_STATUS.search(text)
            if m:
                result["status"] = m.group(1).strip()
            m = RE_TEST_CMD.search(text)
            if m:
                result["test_command"] = m.group(1).strip()
            m = RE_FOLDER.search(text)
            if m:
                result["artifact_folder"] = m.group(1).strip()
            m = RE_FILES.search(text)
            if m:
                result["listed_files"] = [f.strip() for f in m.group(1).split(",") if f.strip()]
        except Exception as e:
            result["quality_flags"].append(f"REPORT_READ_ERROR:{e}")
    else:
        result["quality_flags"].append("NO_REPORT")

    # Scan actual files in directory (non-recursive for top-level, then 1 level)
    all_files = []
    for item in sq_dir.rglob("*"):
        if item.is_file():
            stat = item.stat()
            rel = item.relative_to(sq_dir)
            ftype = classify_file(item.name)
            all_files.append({
                "name": str(rel),
                "size": stat.st_size,
                "type": ftype,
            })
            result["total_bytes"] += stat.st_size
            if ftype == "code":
                result["code_files"] += 1
                result["code_bytes"] += stat.st_size
                result["has_code"] = True
            elif ftype == "doc":
                result["doc_files"] += 1
            elif ftype == "config":
                result["config_files"] += 1
            else:
                result["other_files"] += 1

    result["actual_files"] = [f["name"] for f in all_files]
    result["actual_file_details"] = all_files

    # --- Quality Scoring ---
    score = 0
    flags = result["quality_flags"]

    # Has report (+15)
    if result["report_found"]:
        score += 15
    else:
        if "NO_REPORT" not in flags:
            flags.append("NO_REPORT")

    # Report was parseable (+5)
    if result["report_parsed"]:
        score += 5

    # Has actual code files (+30)
    if result["has_code"]:
        score += 30
        # Code is substantial (>500 bytes) (+10)
        if result["code_bytes"] > 500:
            score += 10
        # Code is meaningful (>2KB) (+5)
        if result["code_bytes"] > 2048:
            score += 5
    else:
        flags.append("NO_CODE")

    # Has test command in report (+10)
    if result["test_command"]:
        score += 10
    else:
        flags.append("NO_TEST_CMD")

    # Has status marked done (+5)
    if result["status"] and "done" in result["status"].lower():
        score += 5

    # Artifact folder listed and exists (+10)
    if result["artifact_folder"]:
        af = Path(result["artifact_folder"])
        if af.exists():
            score += 10
        else:
            flags.append("ARTIFACT_MISSING")

    # Has multiple files (+5, indicates real work)
    if len(all_files) >= 2:
        score += 5

    # Report lists files that actually exist (+5)
    if result["listed_files"]:
        found = 0
        for f in result["listed_files"]:
            if (sq_dir / f).exists():
                found += 1
        if found > 0:
            score += 5
        else:
            flags.append("LISTED_FILES_MISSING")

    # Penalty: empty directory (only REPORT.md, no real artifact)
    non_report = [f for f in all_files if f["name"].lower() not in ("report.md",)]
    if not non_report:
        score -= 20
        flags.append("EMPTY_BESIDES_REPORT")

    # Penalty: very small total size (<200 bytes total)
    if result["total_bytes"] < 200:
        score -= 10
        flags.append("VERY_SMALL")

    result["quality_score"] = max(0, min(100, score))
    result["quality_flags"] = flags
    return result


def grade(score: int) -> str:
    """Score → grade."""
    if score >= 80:
        return "A"
    if score >= 60:
        return "B"
    if score >= 40:
        return "C"
    if score >= 20:
        return "D"
    return "F"


def build_report(results: list, by_agent: bool = False) -> str:
    """Build markdown report from scored results."""
    lines = []
    lines.append("# 📊 Sidequest Value Audit")
    lines.append("")

    total = len(results)
    scored = [r for r in results if r["exists"]]
    if not scored:
        lines.append("No sidequest directories found.")
        return "\n".join(lines)

    avg_score = sum(r["quality_score"] for r in scored) / len(scored)
    has_code = sum(1 for r in scored if r["has_code"])
    no_code = sum(1 for r in scored if not r["has_code"])
    no_report = sum(1 for r in scored if "NO_REPORT" in r["quality_flags"])

    # Overall stats
    lines.append("## Overall")
    lines.append("")
    lines.append(f"- **Total sidequests:** {total}")
    lines.append(f"- **Average quality score:** {avg_score:.1f}/100 (Grade: {grade(int(avg_score))})")
    lines.append(f"- **With code:** {has_code} ({has_code*100//max(len(scored),1)}%)")
    lines.append(f"- **No code:** {no_code} ({no_code*100//max(len(scored),1)}%)")
    lines.append(f"- **Missing report:** {no_report}")
    lines.append("")

    # Score distribution
    dist = defaultdict(int)
    for r in scored:
        dist[grade(r["quality_score"])] += 1
    lines.append("## Grade Distribution")
    lines.append("")
    for g in ("A", "B", "C", "D", "F"):
        cnt = dist.get(g, 0)
        bar = "█" * cnt + "░" * max(0, 20 - cnt)
        lines.append(f"- **{g}:** {cnt} `{bar}`")
    lines.append("")

    # Per-agent breakdown
    by_agent_map = defaultdict(list)
    for r in scored:
        agent = r.get("agent") or "unknown"
        by_agent_map[agent].append(r)

    lines.append("## Per-Agent Summary")
    lines.append("")
    lines.append("| Agent | Count | Avg Score | Grade | Has Code | No Code |")
    lines.append("|-------|-------|-----------|-------|----------|---------|")
    for agent in sorted(by_agent_map.keys()):
        items = by_agent_map[agent]
        cnt = len(items)
        avg = sum(r["quality_score"] for r in items) / cnt
        hc = sum(1 for r in items if r["has_code"])
        nc = cnt - hc
        lines.append(f"| {agent} | {cnt} | {avg:.0f} | {grade(int(avg))} | {hc} | {nc} |")
    lines.append("")

    # Red flags — sidequests that score poorly
    low = [r for r in scored if r["quality_score"] < 40]
    if low:
        lines.append("## ⚠️ Low-Value Sidequests (Score < 40)")
        lines.append("")
        for r in sorted(low, key=lambda x: x["quality_score"]):
            flags = ", ".join(r["quality_flags"]) if r["quality_flags"] else "—"
            lines.append(f"- **{r['name']}** (Score: {r['quality_score']}, Agent: {r.get('agent', '?')})")
            lines.append(f"  - Flags: {flags}")
            lines.append(f"  - Files: {len(r['actual_files'])}, Size: {fmt_size(r['total_bytes'])}")
            if r["has_code"]:
                lines.append(f"  - Code: {r['code_files']} files, {fmt_size(r['code_bytes'])}")
            lines.append("")

    # Top performers — sidequests that score well
    high = [r for r in scored if r["quality_score"] >= 70]
    if high:
        lines.append("## ✅ High-Value Sidequests (Score ≥ 70)")
        lines.append("")
        for r in sorted(high, key=lambda x: -x["quality_score"]):
            lines.append(f"- **{r['name']}** (Score: {r['quality_score']}, Agent: {r.get('agent', '?')})")
            lines.append(f"  - Files: {len(r['actual_files'])}, Size: {fmt_size(r['total_bytes'])}")
            if r["has_code"]:
                lines.append(f"  - Code: {r['code_files']} files, {fmt_size(r['code_bytes'])}")
            lines.append("")

    # Duplicate detection (same agent, similar name pattern)
    lines.append("## 🔄 Potential Duplicates")
    lines.append("")
    seen = {}
    dupes_found = False
    for r in sorted(scored, key=lambda x: (x.get("agent") or "") + x["name"]):
        agent = r.get("agent", "?")
        # Extract slug (everything after agent name)
        slug = r["name"]
        name_parts = slug.split("-")
        # Find where agent name appears
        slug_part = ""
        for i, p in enumerate(name_parts):
            if p == agent and i + 1 < len(name_parts):
                slug_part = "-".join(name_parts[i + 1:])
                break
        if not slug_part:
            slug_part = slug

        key = f"{agent or 'unknown'}:{slug_part}"
        if key in seen:
            if not dupes_found:
                dupes_found = True
            lines.append(f"- **{agent}** `{slug_part}`: appears {seen[key]+1}× ({r['date']})")
        seen[key] = seen.get(key, 0) + 1
    if not dupes_found:
        lines.append("No obvious duplicates detected.")
    lines.append("")

    # Trend: quality over time
    lines.append("## 📈 Quality Trend (by date)")
    lines.append("")
    by_date = defaultdict(list)
    for r in scored:
        d = r.get("date", "?")
        if d and d != "?":
            by_date[d].append(r)
    if by_date:
        lines.append("| Date | Count | Avg Score | Grade |")
        lines.append("|------|-------|-----------|-------|")
        for d in sorted(by_date.keys()):
            items = by_date[d]
            cnt = len(items)
            avg = sum(r["quality_score"] for r in items) / cnt
            lines.append(f"| {d} | {cnt} | {avg:.0f} | {grade(int(avg))} |")
    lines.append("")

    return "\n".join(lines)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Audit sidequest value")
    parser.add_argument("--sidequest-dir", default=str(DEFAULT_SQ_DIR),
                        help="Root sidequest directory")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    parser.add_argument("--by-agent", action="store_true", help="Group by agent")
    args = parser.parse_args()

    sq_dir = Path(args.sidequest_dir)
    if not sq_dir.is_dir():
        print(f"❌ Directory not found: {sq_dir}", file=sys.stderr)
        sys.exit(1)

    # Scan all subdirectories that look like sidequests (YYYY-MM-DD-* or YYYY-MM-DD/*)
    results = []
    for entry in sorted(sq_dir.iterdir()):
        if entry.is_dir():
            # Check if it's a direct sidequest dir or a date dir
            if re.match(r"\d{4}-\d{2}-\d{2}-", entry.name):
                results.append(score_sidequest(entry))
            elif re.match(r"\d{4}-\d{2}-\d{2}$", entry.name):
                # Date directory — scan children
                for child in sorted(entry.iterdir()):
                    if child.is_dir():
                        results.append(score_sidequest(child))

    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        print(build_report(results, by_agent=args.by_agent))


if __name__ == "__main__":
    main()
