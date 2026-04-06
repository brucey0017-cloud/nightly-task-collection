#!/usr/bin/env python3
"""git-pulse: scan multiple git repositories under a path and report status."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional


@dataclass
class RepoStatus:
    path: str
    branch: str
    upstream: Optional[str]
    ahead: int
    behind: int
    unstaged: int
    staged: int
    untracked: int
    dirty: bool
    error: Optional[str] = None


def run_git(repo_path: str, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", repo_path, *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or f"git {' '.join(args)} failed")
    return proc.stdout


def parse_porcelain_v2(text: str, repo_path: str) -> RepoStatus:
    branch = "(detached)"
    upstream: Optional[str] = None
    ahead = 0
    behind = 0
    unstaged = 0
    staged = 0
    untracked = 0

    for raw in text.splitlines():
        line = raw.strip("\n")
        if line.startswith("# branch.head "):
            head = line[len("# branch.head ") :].strip()
            branch = "(detached)" if head == "(detached)" else head
        elif line.startswith("# branch.upstream "):
            upstream = line[len("# branch.upstream ") :].strip()
        elif line.startswith("# branch.ab "):
            # format: # branch.ab +<ahead> -<behind>
            parts = line.split()
            if len(parts) >= 4:
                try:
                    ahead = int(parts[2].lstrip("+"))
                    behind = int(parts[3].lstrip("-"))
                except ValueError:
                    ahead = 0
                    behind = 0
        elif line.startswith("1 ") or line.startswith("2 "):
            # porcelain v2 tracked entries: "1 XY ..." / "2 XY ..."
            # XY = index/worktree status
            tokens = line.split()
            if len(tokens) >= 2:
                xy = tokens[1]
                if len(xy) >= 2:
                    if xy[0] != ".":
                        staged += 1
                    if xy[1] != ".":
                        unstaged += 1
        elif line.startswith("u "):
            # unmerged entries; count as both staged and unstaged attention
            staged += 1
            unstaged += 1
        elif line.startswith("? "):
            untracked += 1

    dirty = (staged + unstaged + untracked) > 0
    return RepoStatus(
        path=repo_path,
        branch=branch,
        upstream=upstream,
        ahead=ahead,
        behind=behind,
        unstaged=unstaged,
        staged=staged,
        untracked=untracked,
        dirty=dirty,
    )


def repo_status(repo_path: str) -> RepoStatus:
    try:
        out = run_git(repo_path, "status", "--porcelain=2", "--branch")
        return parse_porcelain_v2(out, repo_path)
    except Exception as exc:  # noqa: BLE001
        return RepoStatus(
            path=repo_path,
            branch="(unknown)",
            upstream=None,
            ahead=0,
            behind=0,
            unstaged=0,
            staged=0,
            untracked=0,
            dirty=False,
            error=str(exc),
        )


def find_repos(root: Path, max_depth: int) -> List[str]:
    repos: List[str] = []
    root = root.resolve()

    for dirpath, dirnames, _filenames in os.walk(root, topdown=True, followlinks=False):
        current = Path(dirpath)
        rel_parts = current.relative_to(root).parts if current != root else ()
        depth = len(rel_parts)

        if depth > max_depth:
            dirnames[:] = []
            continue

        git_dir = current / ".git"
        if git_dir.is_dir() or git_dir.is_file():
            repos.append(str(current))
            # do not descend inside a repo; nested repos are out of MVP scope
            dirnames[:] = []
            continue

        if depth == max_depth:
            dirnames[:] = []

    return repos


def severity_key(status: RepoStatus):
    if status.error:
        level = 0
    elif status.dirty and (status.behind > 0 or status.ahead > 0):
        level = 1
    elif status.dirty:
        level = 2
    elif status.behind > 0:
        level = 3
    elif status.ahead > 0:
        level = 4
    else:
        level = 5
    return (level, status.path)


def human_output(statuses: List[RepoStatus]) -> str:
    total = len(statuses)
    dirty = sum(1 for s in statuses if s.dirty)
    clean = sum(1 for s in statuses if not s.dirty and not s.error)
    behind = sum(1 for s in statuses if s.behind > 0)
    errored = sum(1 for s in statuses if s.error)

    lines = []
    lines.append(
        f"Summary: total={total} dirty={dirty} clean={clean} behind={behind} errors={errored}"
    )
    lines.append("Note: ahead/behind is based on local tracking refs only (no remote fetch).")
    lines.append("")
    lines.append(
        "STATUS  BRANCH               A/ B  STAGED  UNSTAGED  UNTRACKED  PATH"
    )
    lines.append(
        "------  -------------------  ----  ------  --------  ---------  ----"
    )

    for s in statuses:
        if s.error:
            lines.append(
                f"ERROR   {'(n/a)':<19}  {'-':>4}  {'-':>6}  {'-':>8}  {'-':>9}  {s.path} ({s.error})"
            )
            continue
        label = "DIRTY" if s.dirty else "CLEAN"
        ab = f"{s.ahead}/{s.behind}"
        lines.append(
            f"{label:<6}  {s.branch[:19]:<19}  {ab:>4}  {s.staged:>6}  {s.unstaged:>8}  {s.untracked:>9}  {s.path}"
        )

    if total > 0 and dirty == 0 and behind == 0 and errored == 0:
        lines.append("")
        lines.append("All repos clean. Morning starts smooth.")

    return "\n".join(lines)


def build_json(root: Path, depth: int, statuses: List[RepoStatus]) -> str:
    payload = {
        "root": str(root),
        "depth": depth,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "ahead_behind_note": "local tracking refs only; no remote fetch",
        "summary": {
            "total": len(statuses),
            "dirty": sum(1 for s in statuses if s.dirty),
            "clean": sum(1 for s in statuses if not s.dirty and not s.error),
            "behind": sum(1 for s in statuses if s.behind > 0),
            "errors": sum(1 for s in statuses if s.error),
        },
        "repos": [asdict(s) for s in statuses],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scan a directory tree for git repos and report repo status."
    )
    parser.add_argument("root", help="Root path to scan")
    parser.add_argument("--depth", type=int, default=3, help="Max recursive depth (default: 3)")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.root)

    if not root.exists() or not root.is_dir():
        print(f"Error: root path is not a directory: {root}", file=sys.stderr)
        return 2

    repos = find_repos(root, max_depth=max(args.depth, 0))
    statuses = [repo_status(p) for p in repos]
    statuses.sort(key=severity_key)

    if args.json:
        print(build_json(root, args.depth, statuses))
    else:
        print(human_output(statuses))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
