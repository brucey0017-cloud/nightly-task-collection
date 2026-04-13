#!/usr/bin/env python3
"""disk-triage: quick disk hotspot finder (stdlib only)."""

import argparse
import json
import os
import sys
import time


MB = 1024 * 1024
GB = 1024 * MB


def human_size(num_bytes):
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    value = float(num_bytes)
    for unit in units:
        if value < 1024.0 or unit == units[-1]:
            if unit == "B":
                return "%d%s" % (int(value), unit)
            return "%.1f%s" % (value, unit)
        value /= 1024.0
    return "%.1fPB" % value


def classify(size_bytes, warn_bytes):
    if size_bytes > GB:
        return "CRIT"
    if size_bytes > warn_bytes:
        return "WARN"
    return "OK"


def label_text(label):
    return "[%s]" % label


def colorize(text, label, enable_color):
    if not enable_color:
        return text
    colors = {
        "CRIT": "\033[31m",  # red
        "WARN": "\033[33m",  # yellow
        "OK": "\033[32m",    # green
    }
    start = colors.get(label, "")
    end = "\033[0m" if start else ""
    return "%s%s%s" % (start, text, end)


def safe_stat_size(path):
    try:
        return os.stat(path, follow_symlinks=False).st_size, None
    except PermissionError:
        return 0, "permission-denied"
    except OSError as exc:
        return 0, "%s" % exc.__class__.__name__


def scan_dir_size(path, depth, stats):
    """Return cumulative size of files under path.

    depth=0 means: scan direct children files only; do not recurse into child dirs.
    depth=1 means: recurse one more directory level, etc.
    """
    total = 0
    try:
        with os.scandir(path) as it:
            for entry in it:
                stats["entries_scanned"] += 1
                try:
                    if entry.is_symlink():
                        stats["symlinks_skipped"] += 1
                        continue

                    if entry.is_file(follow_symlinks=False):
                        st = entry.stat(follow_symlinks=False)
                        total += st.st_size
                    elif entry.is_dir(follow_symlinks=False):
                        if depth > 0:
                            total += scan_dir_size(entry.path, depth - 1, stats)
                    else:
                        st = entry.stat(follow_symlinks=False)
                        total += st.st_size
                except PermissionError:
                    stats["permission_denied"] += 1
                except FileNotFoundError:
                    stats["vanished"] += 1
                except OSError:
                    stats["errors"] += 1
    except PermissionError:
        stats["permission_denied"] += 1
        return 0
    except FileNotFoundError:
        stats["vanished"] += 1
        return 0
    except OSError:
        stats["errors"] += 1
        return 0
    return total


def collect_top_level(target_dir, depth, warn_bytes, top_n):
    stats = {
        "entries_scanned": 0,
        "permission_denied": 0,
        "symlinks_skipped": 0,
        "vanished": 0,
        "errors": 0,
    }
    rows = []

    with os.scandir(target_dir) as it:
        for entry in it:
            stats["entries_scanned"] += 1
            row = {
                "path": entry.path,
                "name": entry.name,
                "type": "other",
                "size_bytes": 0,
                "note": "",
            }

            try:
                if entry.is_symlink():
                    stats["symlinks_skipped"] += 1
                    row["type"] = "symlink"
                    row["note"] = "skipped-symlink"
                    rows.append(row)
                    continue

                if entry.is_file(follow_symlinks=False):
                    row["type"] = "file"
                    st = entry.stat(follow_symlinks=False)
                    row["size_bytes"] = st.st_size
                elif entry.is_dir(follow_symlinks=False):
                    row["type"] = "dir"
                    row["size_bytes"] = scan_dir_size(entry.path, max(depth - 1, 0), stats)
                else:
                    row["type"] = "other"
                    sz, note = safe_stat_size(entry.path)
                    row["size_bytes"] = sz
                    row["note"] = note or ""
            except PermissionError:
                stats["permission_denied"] += 1
                row["note"] = "permission-denied"
            except FileNotFoundError:
                stats["vanished"] += 1
                row["note"] = "vanished"
            except OSError as exc:
                stats["errors"] += 1
                row["note"] = exc.__class__.__name__

            rows.append(row)

    for row in rows:
        label = classify(row["size_bytes"], warn_bytes)
        row["label"] = label
        row["status"] = label_text(label)
        row["warning"] = row["size_bytes"] > warn_bytes
        row["size_human"] = human_size(row["size_bytes"])

    rows.sort(key=lambda x: x["size_bytes"], reverse=True)
    return rows[:top_n], stats


def parse_args():
    parser = argparse.ArgumentParser(
        description="Find what is eating disk quickly (read-only)."
    )
    parser.add_argument("path", nargs="?", default="/", help="Target directory (default: /)")
    parser.add_argument("--top", type=int, default=15, help="Show top N entries (default: 15)")
    parser.add_argument("--depth", type=int, default=1, help="Directory scan depth (default: 1, max: 3)")
    parser.add_argument("--warn-mb", type=float, default=100.0, help="Warn threshold in MB (default: 100)")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    parser.add_argument("--no-color", action="store_true", help="Disable ANSI colors")
    args = parser.parse_args()

    if args.top <= 0:
        parser.error("--top must be > 0")
    if args.depth < 0:
        parser.error("--depth must be >= 0")
    if args.depth > 3:
        parser.error("--depth max is 3")
    if args.warn_mb < 0:
        parser.error("--warn-mb must be >= 0")

    return args


def print_human(rows, stats, target_dir, depth, elapsed, warn_bytes, use_color):
    print("Hotspots under %s (depth=%d, top=%d)" % (target_dir, depth, len(rows)))
    print("Threshold: WARN > %s" % human_size(warn_bytes))

    if not rows:
        print("No entries found.")
    else:
        size_w = max(len(r["size_human"]) for r in rows)
        status_w = len("[CRIT]")
        type_w = max(len(r["type"]) for r in rows)

        header = "%-*s  %-*s  %*s  %-*s  %s" % (
            40,
            "PATH",
            type_w,
            "TYPE",
            size_w,
            "SIZE",
            status_w,
            "STATUS",
            "NOTE",
        )
        print(header)
        print("-" * len(header))

        for row in rows:
            status = row["status"]
            status_colored = colorize(status, row["label"], use_color)
            note = row.get("note") or ("⚠️" if row["warning"] else "")
            path_display = row["path"]
            if len(path_display) > 40:
                path_display = "..." + path_display[-37:]
            print(
                "%-*s  %-*s  %*s  %-*s  %s"
                % (
                    40,
                    path_display,
                    type_w,
                    row["type"],
                    size_w,
                    row["size_human"],
                    status_w,
                    status_colored,
                    note,
                )
            )

    print("Scanned %d entries in %.1fs." % (stats["entries_scanned"], elapsed))
    if stats["permission_denied"]:
        print("Skipped %d entries due to permission denied." % stats["permission_denied"])
    if stats["symlinks_skipped"]:
        print("Skipped %d symlink entries." % stats["symlinks_skipped"])


def main():
    args = parse_args()
    target_dir = os.path.abspath(args.path)

    if not os.path.exists(target_dir):
        print("Target does not exist: %s" % target_dir, file=sys.stderr)
        return 2
    if not os.path.isdir(target_dir):
        print("Target is not a directory: %s" % target_dir, file=sys.stderr)
        return 2

    warn_bytes = int(args.warn_mb * MB)
    use_color = (not args.no_color) and sys.stdout.isatty() and (not args.json)

    start = time.time()
    try:
        rows, stats = collect_top_level(target_dir, args.depth, warn_bytes, args.top)
    except PermissionError:
        print("Permission denied opening target: %s" % target_dir, file=sys.stderr)
        return 1
    except OSError as exc:
        print("Scan failed: %s" % exc, file=sys.stderr)
        return 1
    elapsed = time.time() - start

    if args.json:
        out = []
        for row in rows:
            out.append(
                {
                    "path": row["path"],
                    "name": row["name"],
                    "type": row["type"],
                    "size_bytes": row["size_bytes"],
                    "size_human": row["size_human"],
                    "label": row["status"],
                    "warning": row["warning"],
                    "note": row.get("note", ""),
                }
            )
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print_human(rows, stats, target_dir, args.depth, elapsed, warn_bytes, use_color)

    return 0


if __name__ == "__main__":
    sys.exit(main())
