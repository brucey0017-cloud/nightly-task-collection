#!/usr/bin/env python3
"""
workspace_health.py — One-command workspace health check.
Zero dependencies. Python 3.8+.

Usage:
    python3 workspace_health.py [--workspace PATH] [--json] [--quiet]

Scans the workspace and reports:
  1. Disk usage summary (top-level dirs)
  2. Git status (uncommitted, unpushed, stale branches)
  3. Memory freshness (MEMORY.md, daily notes)
  4. Large files (>10 MB)
  5. Stale files (not modified in 30+ days)
  6. Broken symlinks
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ── Thresholds ──────────────────────────────────────────────
LARGE_FILE_MB = 10
STALE_DAYS = 30
MEMORY_FRESH_DAYS = 7
DAILY_NOTE_FRESH_DAYS = 2

# ── Colours (disabled if not a tty) ────────────────────────
_USE_COLOR = sys.stdout.isatty()

def _c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _USE_COLOR else text

GREEN  = lambda t: _c("32", t)
YELLOW = lambda t: _c("33", t)
RED    = lambda t: _c("31", t)
BOLD   = lambda t: _c("1", t)
DIM    = lambda t: _c("2", t)


def _run(cmd, cwd=None, fallback=""):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                           cwd=cwd, timeout=15)
        return r.stdout.strip() if r.returncode == 0 else fallback
    except Exception:
        return fallback


def _days_ago(ts: float) -> int:
    return (datetime.now(tz=timezone.utc) - datetime.fromtimestamp(ts, tz=timezone.utc)).days


# ── Checks ─────────────────────────────────────────────────

def check_disk(workspace: Path) -> list:
    """Top-level directory sizes."""
    items = []
    for child in sorted(workspace.iterdir()):
        if child.is_dir():
            size = int(_run(f"du -sb '{child}' 2>/dev/null | cut -f1", cwd=workspace) or "0")
            if size > 0:
                items.append({"path": child.name, "bytes": size, "mb": round(size / 1048576, 1)})
    items.sort(key=lambda x: x["bytes"], reverse=True)
    return items[:15]


def check_git(workspace: Path) -> dict:
    """Git status for the workspace repo."""
    result = {"is_git_repo": False, "uncommitted": None, "unpushed": None,
              "stale_branches": [], "current_branch": None}

    if not (workspace / ".git").exists():
        return result
    result["is_git_repo"] = True

    result["current_branch"] = _run("git rev-parse --abbrev-ref HEAD", cwd=workspace)
    result["uncommitted"] = _run("git status --porcelain | wc -l", cwd=workspace) or "0"

    # Unpushed commits (current branch vs its upstream)
    unpushed = _run("git log @{upstream}.. --oneline 2>/dev/null | wc -l", cwd=workspace)
    result["unpushed"] = unpushed if unpushed else "0"

    # Stale branches (not modified in 60 days, not current)
    branches_raw = _run("git for-each-ref --sort=-committerdate --format='%(refname:short) %(committerdate:unix)' refs/heads/", cwd=workspace)
    for line in branches_raw.splitlines():
        parts = line.strip().split()
        if len(parts) < 2:
            continue
        branch, ts = parts[0], float(parts[1])
        if branch == result["current_branch"]:
            continue
        if _days_ago(ts) > 60:
            result["stale_branches"].append({"branch": branch, "days": _days_ago(ts)})

    return result


def check_memory_freshness(workspace: Path) -> list:
    """Check MEMORY.md and daily note freshness."""
    findings = []

    mem = workspace / "MEMORY.md"
    if mem.exists():
        days = _days_ago(mem.stat().st_mtime)
        findings.append({"file": "MEMORY.md", "days_ago": days,
                         "stale": days > MEMORY_FRESH_DAYS})
    else:
        findings.append({"file": "MEMORY.md", "days_ago": None, "stale": True, "missing": True})

    mem_dir = workspace / "memory"
    if mem_dir.is_dir():
        notes = sorted(mem_dir.glob("*.md"))
        if notes:
            latest = notes[-1]
            days = _days_ago(latest.stat().st_mtime)
            findings.append({"file": f"memory/{latest.name}", "days_ago": days,
                             "stale": days > DAILY_NOTE_FRESH_DAYS})

    return findings


def check_large_files(workspace: Path) -> list:
    """Find files larger than threshold."""
    threshold = LARGE_FILE_MB * 1048576
    found = []
    try:
        raw = _run(f"find '{workspace}' -type f -size +{LARGE_FILE_MB}M -not -path '*/node_modules/*' -not -path '*/.git/*' -printf '%s %p\\n' 2>/dev/null | sort -rn | head -20", cwd=workspace)
        for line in raw.splitlines():
            parts = line.strip().split(" ", 1)
            if len(parts) == 2:
                size, path = int(parts[0]), parts[1]
                found.append({"path": os.path.relpath(path, workspace), "mb": round(size / 1048576, 1)})
    except Exception:
        pass
    return found


def check_stale_files(workspace: Path) -> list:
    """Find files not modified in 30+ days (excluding known inactive dirs)."""
    cutoff = (datetime.now(tz=timezone.utc) - timedelta(days=STALE_DAYS)).timestamp()
    found = []
    exclude = {".git", "node_modules", "__pycache__", ".cache"}
    for root, dirs, files in os.walk(workspace):
        dirs[:] = [d for d in dirs if d not in exclude]
        for f in files:
            fp = Path(root) / f
            try:
                if fp.stat().st_mtime < cutoff:
                    found.append(os.path.relpath(fp, workspace))
            except OSError:
                pass
        if len(found) > 50:
            break
    return found[:50]


def check_broken_symlinks(workspace: Path) -> list:
    """Find broken symlinks."""
    found = []
    try:
        raw = _run(f"find '{workspace}' -xtype l -printf '%p\\n' 2>/dev/null | head -20", cwd=workspace)
        for line in raw.splitlines():
            found.append(os.path.relpath(line.strip(), workspace))
    except Exception:
        pass
    return found


# ── Formatter ──────────────────────────────────────────────

def fmt_report(workspace: Path, data: dict) -> str:
    lines = []
    L = lines.append

    L(BOLD("═" * 60))
    L(BOLD(f"  Workspace Health: {workspace}"))
    L(BOLD("═" * 60))

    # Disk
    L(BOLD("\n💾 Disk Usage (top dirs)"))
    for d in data["disk"]:
        bar = "█" * min(int(d["mb"] / 5), 40)
        L(f"  {bar} {d['mb']:>8.1f} MB  {d['path']}")

    # Git
    git = data["git"]
    if git["is_git_repo"]:
        L(BOLD("\n📦 Git"))
        L(f"  Branch: {git['current_branch']}")
        uncommitted = int(git["uncommitted"])
        unpushed = int(git["unpushed"])
        if uncommitted > 0:
            L(f"  {YELLOW(f'⚠ {uncommitted} uncommitted files')}")
        else:
            L(f"  {GREEN('✓ clean working tree')}")
        if unpushed > 0:
            L(f"  {YELLOW(f'⚠ {unpushed} unpushed commits')}")
        else:
            L(f"  {GREEN('✓ up to date with upstream')}")
        if git["stale_branches"]:
            n = len(git['stale_branches'])
            L(f"  {DIM(f'  ({n} stale branches >60d)')}")

    # Memory
    L(BOLD("\n🧠 Memory Freshness"))
    for m in data["memory"]:
        if m.get("missing"):
            L(f"  {RED('✗ MEMORY.md missing!')}")
        elif m["stale"]:
            fname = m['file']
            dago = m['days_ago']
            L(f"  {YELLOW(f'⚠ {fname} — {dago}d old')}")
        else:
            fname = m['file']
            dago = m['days_ago']
            L(f"  {GREEN(f'✓ {fname} — {dago}d old')}")

    # Large files
    if data["large_files"]:
        L(BOLD(f"\n📦 Large Files (>{LARGE_FILE_MB}MB)"))
        for f in data["large_files"]:
            L(f"  {f['mb']:>8.1f} MB  {f['path']}")

    # Stale files
    stale_count = len(data["stale_files"])
    if stale_count > 0:
        L(BOLD(f"\n🕸️ Stale Files (>{STALE_DAYS}d, showing max 50)"))
        L(f"  {stale_count} files not modified in {STALE_DAYS}+ days")
        for f in data["stale_files"][:10]:
            L(f"    {DIM(f)}")
        if stale_count > 10:
            L(f"    {DIM(f'... and {stale_count - 10} more')}")

    # Broken symlinks
    if data["broken_symlinks"]:
        L(BOLD(f"\n🔗 Broken Symlinks ({len(data['broken_symlinks'])})"))
        for s in data["broken_symlinks"]:
            L(f"  {RED(f'✗ {s}')}")

    # Summary
    L(BOLD("\n" + "═" * 60))
    issues = []
    if int(git.get("uncommitted", "0")) > 0:
        issues.append("uncommitted files")
    if int(git.get("unpushed", "0")) > 0:
        issues.append("unpushed commits")
    if any(m["stale"] for m in data["memory"]):
        issues.append("stale memory")
    if data["large_files"]:
        issues.append(f"{len(data['large_files'])} large files")
    if data["broken_symlinks"]:
        issues.append(f"{len(data['broken_symlinks'])} broken symlinks")

    if issues:
        L(YELLOW(f"  ⚠ Issues: {', '.join(issues)}"))
    else:
        L(GREEN("  ✓ Workspace looks healthy"))

    L("═" * 60)
    return "\n".join(lines)


# ── Main ───────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Workspace health check")
    parser.add_argument("--workspace", default="/root/.openclaw/workspace-commander",
                        help="Path to workspace root")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    parser.add_argument("--quiet", action="store_true", help="Only show issues")
    args = parser.parse_args()

    ws = Path(args.workspace).resolve()
    if not ws.is_dir():
        print(f"Error: {ws} is not a directory", file=sys.stderr)
        sys.exit(1)

    data = {
        "disk": check_disk(ws),
        "git": check_git(ws),
        "memory": check_memory_freshness(ws),
        "large_files": check_large_files(ws),
        "stale_files": check_stale_files(ws),
        "broken_symlinks": check_broken_symlinks(ws),
    }

    if args.json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print(fmt_report(ws, data))


if __name__ == "__main__":
    main()
