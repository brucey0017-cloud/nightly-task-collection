#!/usr/bin/env python3
"""Parse a log file and print level counts and recent error-ish lines."""

import argparse
import json
import re
import sys
from collections import Counter

LEVELS = ["TRACE", "DEBUG", "INFO", "WARN", "ERROR", "FATAL", "CRITICAL"]
ERRORISH = {"ERROR", "FATAL", "CRITICAL"}
LEVEL_RE = re.compile(r"\b(" + "|".join(LEVELS) + r")\b")


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Log level digest utility")
    p.add_argument("logfile", help="Path to log file")
    p.add_argument("-n", "--last", type=int, default=10, help="Last N error-ish lines (default: 10)")
    p.add_argument("--json", action="store_true", help="Output as JSON")
    return p.parse_args(argv)


def digest(path):
    counts = Counter({lvl: 0 for lvl in LEVELS})
    error_lines = []
    total = 0

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            total += 1
            match = LEVEL_RE.search(line)
            if match:
                level = match.group(1)
                counts[level] += 1
                if level in ERRORISH:
                    error_lines.append(line.rstrip("\n"))
            else:
                counts["INFO"] += 1

    return {
        "total_lines": total,
        "counts": {lvl: counts[lvl] for lvl in LEVELS},
        "last_errors": error_lines[-(counts["ERROR"] + counts["FATAL"] + counts["CRITICAL"]):],
    }


def main():
    args = parse_args()
    data = digest(args.logfile)
    data["last_errors"] = data["last_errors"][-args.last:]

    if args.json:
        print(json.dumps(data, indent=2))
        return

    print(f"Total lines: {data['total_lines']}")
    print("Counts by level:")
    for lvl in LEVELS:
        print(f"  {lvl}: {data['counts'][lvl]}")
    print(f"\nLast {args.last} error-ish lines:")
    if data["last_errors"]:
        for line in data["last_errors"]:
            print(line)
    else:
        print("  (none)")


if __name__ == "__main__":
    main()
