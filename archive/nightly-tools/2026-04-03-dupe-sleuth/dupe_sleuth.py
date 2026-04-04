#!/usr/bin/env python3
"""
DupeSleuth - Fast duplicate file finder using SHA256 content hashing.
Identifies exact duplicates only. Never deletes files.
"""

import argparse
import hashlib
import os
import sys
from collections import defaultdict
from pathlib import Path


def hash_file(filepath: Path, block_size: int = 65536) -> str | None:
    """Return SHA256 hash of file content, or None if unreadable."""
    sha256 = hashlib.sha256()
    try:
        with open(filepath, 'rb') as f:
            while chunk := f.read(block_size):
                sha256.update(chunk)
        return sha256.hexdigest()
    except (IOError, OSError, PermissionError):
        return None


def scan_directory(directory: Path, verbose: bool = False) -> tuple[dict[str, list[Path]], int, int]:
    """
    Recursively scan directory and group files by content hash.
    Returns (hash->paths, total_scanned_files, unreadable_files).
    """
    files_by_hash = defaultdict(list)
    total_scanned = 0
    errors = 0

    for root, _, files in os.walk(directory):
        for filename in files:
            filepath = Path(root) / filename
            total_scanned += 1

            # Skip symlinks to avoid double-counting and cycles
            if filepath.is_symlink():
                if verbose:
                    print(f"[skip symlink] {filepath}")
                continue

            if verbose:
                print(f"[scan] {filepath}")

            file_hash = hash_file(filepath)
            if file_hash is None:
                errors += 1
                if verbose:
                    print(f"[unreadable] {filepath}")
                continue

            files_by_hash[file_hash].append(filepath)

    return files_by_hash, total_scanned, errors


def format_size(size_bytes: int) -> str:
    """Convert bytes to human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"


def find_duplicates(files_by_hash: dict[str, list[Path]]) -> list[tuple[str, list[Path], int]]:
    """
    Filter to only hashes with multiple files.
    Returns list of (hash, file_list, size_bytes) sorted by total wasted space (desc).
    """
    duplicates = []
    for file_hash, paths in files_by_hash.items():
        if len(paths) > 1:
            # Get size from first file (all duplicates have same size)
            try:
                size = paths[0].stat().st_size
            except OSError:
                size = 0
            duplicates.append((file_hash, paths, size))

    # Sort by total wasted space (size * (count - 1))
    duplicates.sort(key=lambda x: x[2] * (len(x[1]) - 1), reverse=True)
    return duplicates


def print_results(duplicates: list[tuple[str, list[Path], int]], total_scanned: int, errors: int):
    """Print duplicate groups with recommendations."""
    if not duplicates:
        print("=" * 60)
        print("NO DUPLICATES FOUND")
        print("=" * 60)
        print(f"Scanned {total_scanned} files ({errors} unreadable)")
        return

    total_duplicate_groups = len(duplicates)
    total_duplicate_files = sum(len(paths) for _, paths, _ in duplicates)
    total_wasted_bytes = sum(size * (len(paths) - 1) for _, paths, size in duplicates)

    print("=" * 60)
    print(f"FOUND {total_duplicate_groups} DUPLICATE GROUP(S)")
    print("=" * 60)
    print(f"Total files scanned: {total_scanned}")
    print(f"Files in duplicate groups: {total_duplicate_files}")
    print(f"Unreadable files: {errors}")
    print()

    for i, (file_hash, paths, size) in enumerate(duplicates, 1):
        print(f"Group {i}/{total_duplicate_groups} — {format_size(size)} each")
        print(f"Hash: {file_hash[:16]}...")
        print("-" * 40)

        # Sort by path length (shorter paths often indicate "original" location)
        sorted_paths = sorted(paths, key=lambda p: (len(str(p)), str(p)))

        for j, filepath in enumerate(sorted_paths):
            marker = "[KEEP]" if j == 0 else "[DEL] "
            print(f"  {marker} {filepath}")

        wasted = size * (len(paths) - 1)
        print(f"  -> Reclaimable: {format_size(wasted)} if {len(paths) - 1} duplicate(s) removed")
        print()

    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Potential space savings: {format_size(total_wasted_bytes)}")
    print()
    print("⚠️  NO FILES WERE DELETED")
    print("   Review the [DEL] markers above and manually remove files if desired.")
    print("   [KEEP] = Suggested to keep (shortest path)")
    print("   [DEL]  = Consider deleting (duplicate content)")


def main():
    parser = argparse.ArgumentParser(
        description="DupeSleuth - Find duplicate files by content hash (SHA256).",
        epilog="Safety: This tool only identifies duplicates. No files are deleted."
    )
    parser.add_argument(
        "directory",
        help="Directory to scan for duplicates"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show progress during scanning"
    )

    args = parser.parse_args()

    target_dir = Path(args.directory).expanduser().resolve()

    if not target_dir.exists():
        print(f"Error: Directory does not exist: {target_dir}", file=sys.stderr)
        sys.exit(1)

    if not target_dir.is_dir():
        print(f"Error: Not a directory: {target_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"Scanning: {target_dir}")
    print("Computing SHA256 hashes... (this may take a while for large files)")
    print()

    files_by_hash, total_scanned, errors = scan_directory(target_dir, verbose=args.verbose)
    duplicates = find_duplicates(files_by_hash)

    print_results(duplicates, total_scanned, errors)


if __name__ == "__main__":
    main()
