#!/usr/bin/env python3
"""
Sync nightly artifacts into this repository archive/ tree.

Default source paths:
- /root/.openclaw/workspace/nightly-tools
- /root/.openclaw/workspace/nightly-sidequests

Design goals:
- Incremental: only copy new/changed files.
- Idempotent: repeated runs on unchanged sources produce no file diffs.
- Repeatable: deterministic traversal/order.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import shutil
from dataclasses import dataclass
from pathlib import Path

IGNORE_PATTERNS = [
    "__pycache__",
    "*.pyc",
    "*.pyo",
    ".DS_Store",
]

SYNC_MAP = {
    "nightly-tools": "nightly-tools",
    "nightly-sidequests": "nightly-sidequests",
}


@dataclass
class Stats:
    dirs_created: int = 0
    files_created: int = 0
    files_updated: int = 0
    files_skipped: int = 0
    files_ignored: int = 0
    sources_missing: int = 0


def should_ignore(path: Path) -> bool:
    name = path.name
    for pattern in IGNORE_PATTERNS:
        if fnmatch.fnmatch(name, pattern):
            return True
    return False


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def same_file(src: Path, dst: Path) -> bool:
    if not dst.exists() or not dst.is_file():
        return False
    if src.stat().st_size != dst.stat().st_size:
        return False
    return file_sha256(src) == file_sha256(dst)


def ensure_dir(path: Path, dry_run: bool, stats: Stats) -> None:
    if path.exists():
        return
    if dry_run:
        print(f"[DRY-RUN] mkdir -p {path}")
    else:
        path.mkdir(parents=True, exist_ok=True)
    stats.dirs_created += 1


def sync_tree(src_root: Path, dst_root: Path, dry_run: bool, stats: Stats) -> None:
    try:
        exists = src_root.exists()
    except PermissionError:
        print(f"[WARN] Source not accessible (permission denied), skip: {src_root}")
        stats.sources_missing += 1
        return

    if not exists:
        print(f"[WARN] Source missing, skip: {src_root}")
        stats.sources_missing += 1
        return

    try:
        is_dir = src_root.is_dir()
        # preflight access check
        _ = next(src_root.iterdir(), None)
    except PermissionError:
        print(f"[WARN] Source not accessible (permission denied), skip: {src_root}")
        stats.sources_missing += 1
        return

    if not is_dir:
        print(f"[WARN] Source is not a directory, skip: {src_root}")
        stats.sources_missing += 1
        return

    ensure_dir(dst_root, dry_run, stats)

    try:
        source_dirs = sorted([p for p in src_root.rglob("*") if p.is_dir()])
        source_files = sorted([p for p in src_root.rglob("*") if p.is_file()])
    except PermissionError:
        print(f"[WARN] Source traversal denied, skip: {src_root}")
        stats.sources_missing += 1
        return

    # Ensure source directories exist in destination (including empty dirs)
    for src_dir in source_dirs:
        if should_ignore(src_dir):
            stats.files_ignored += 1
            continue
        rel = src_dir.relative_to(src_root)
        dst_dir = dst_root / rel
        ensure_dir(dst_dir, dry_run, stats)

    # Copy new/changed files
    for src_file in source_files:
        if any(should_ignore(part) for part in [src_file, *src_file.parents]):
            stats.files_ignored += 1
            continue

        rel = src_file.relative_to(src_root)
        dst_file = dst_root / rel
        ensure_dir(dst_file.parent, dry_run, stats)

        if not dst_file.exists():
            if dry_run:
                print(f"[DRY-RUN] COPY new: {src_file} -> {dst_file}")
            else:
                shutil.copy2(src_file, dst_file)
            stats.files_created += 1
            continue

        if same_file(src_file, dst_file):
            stats.files_skipped += 1
            continue

        if dry_run:
            print(f"[DRY-RUN] COPY update: {src_file} -> {dst_file}")
        else:
            shutil.copy2(src_file, dst_file)
        stats.files_updated += 1


def parse_args() -> argparse.Namespace:
    script_path = Path(__file__).resolve()
    default_repo_root = script_path.parents[1]

    parser = argparse.ArgumentParser(description="Sync nightly artifacts into archive/")
    parser.add_argument(
        "--source-root",
        default="/root/.openclaw/workspace",
        help="Root containing nightly-tools and nightly-sidequests (default: /root/.openclaw/workspace)",
    )
    parser.add_argument(
        "--repo-root",
        default=str(default_repo_root),
        help="Repository root containing archive/ (default: script parent repo)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Show planned changes only")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source_root = Path(args.source_root).expanduser().resolve()
    repo_root = Path(args.repo_root).expanduser().resolve()
    archive_root = repo_root / "archive"

    stats = Stats()

    print("== sync_nightly ==")
    print(f"source_root: {source_root}")
    print(f"repo_root:   {repo_root}")
    print(f"dry_run:     {args.dry_run}")

    for src_name, dst_name in SYNC_MAP.items():
        src = source_root / src_name
        dst = archive_root / dst_name
        print(f"\n[SYNC] {src} -> {dst}")
        sync_tree(src, dst, args.dry_run, stats)

    print("\n== summary ==")
    print(f"dirs_created:    {stats.dirs_created}")
    print(f"files_created:   {stats.files_created}")
    print(f"files_updated:   {stats.files_updated}")
    print(f"files_skipped:   {stats.files_skipped}")
    print(f"files_ignored:   {stats.files_ignored}")
    print(f"sources_missing: {stats.sources_missing}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
