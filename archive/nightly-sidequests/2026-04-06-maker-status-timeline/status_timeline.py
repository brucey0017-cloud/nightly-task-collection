#!/usr/bin/env python3
"""Compact timeline viewer for nightly-lab status.jsonl."""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, List


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Print a compact timeline from nightly-lab status.jsonl",
    )
    p.add_argument("--input", required=True, help="Path to status.jsonl")
    p.add_argument("--agent", help="Filter by agent (exact match)")
    p.add_argument("--task", help="Filter by task (exact match)")
    p.add_argument("--last", type=int, default=0, help="Show last N matched rows")
    return p.parse_args()


def load_rows(path: str) -> tuple[List[Dict[str, Any]], int]:
    rows: List[Dict[str, Any]] = []
    bad_lines = 0

    with open(path, "r", encoding="utf-8") as f:
        for idx, raw in enumerate(f, start=1):
            line = raw.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                bad_lines += 1
                print(f"[warn] skipped invalid JSON at line {idx}", file=sys.stderr)
                continue
            if isinstance(obj, dict):
                rows.append(obj)
            else:
                bad_lines += 1
                print(f"[warn] skipped non-object JSON at line {idx}", file=sys.stderr)
    return rows, bad_lines


def clip(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"


def extras(row: Dict[str, Any]) -> str:
    bits: List[str] = []
    artifact = str(row.get("artifact", "") or "").strip()
    error_code = str(row.get("error_code", "") or "").strip()

    if artifact:
        bits.append(f"artifact={clip(artifact, 56)}")
    if error_code:
        bits.append(f"error={error_code}")
    return " | ".join(bits)


def main() -> int:
    args = parse_args()
    input_path = args.input

    if not os.path.exists(input_path):
        print(f"[error] file not found: {input_path}", file=sys.stderr)
        return 2

    try:
        rows, bad = load_rows(input_path)
    except OSError as e:
        print(f"[error] failed to read file: {e}", file=sys.stderr)
        return 2

    if args.agent:
        rows = [r for r in rows if str(r.get("agent", "")) == args.agent]
    if args.task:
        rows = [r for r in rows if str(r.get("task", "")) == args.task]

    if args.last and args.last > 0:
        rows = rows[-args.last :]

    if not rows:
        print("No matching records.")
        if bad:
            print(f"[warn] invalid lines skipped: {bad}", file=sys.stderr)
        return 0

    print(f"Rows: {len(rows)}")
    print("-" * 120)
    print(f"{'ts':<28} {'agent':<10} {'task':<10} {'stage':<10} extras")
    print("-" * 120)

    for r in rows:
        ts = clip(str(r.get("ts", "")), 28)
        agent = clip(str(r.get("agent", "")), 10)
        task = clip(str(r.get("task", "")), 10)
        stage = clip(str(r.get("stage", "")), 10)
        print(f"{ts:<28} {agent:<10} {task:<10} {stage:<10} {extras(r)}")

    if bad:
        print("-" * 120)
        print(f"[warn] invalid lines skipped: {bad}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
