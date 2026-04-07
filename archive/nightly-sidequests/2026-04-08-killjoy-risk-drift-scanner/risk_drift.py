#!/usr/bin/env python3
"""
risk_drift.py — Risk Drift Scanner
Scans daily memory/decision files for unvalidated assumptions and stale decisions.
KILLJOY's early warning system: "You decided WHAT without checking?"

Usage:
    python3 risk_drift.py /path/to/memory/
    python3 risk_drift.py /path/to/memory/ --since 7
    python3 risk_drift.py /path/to/memory/ --json

Zero dependencies. Pure Python 3.
"""

import sys
import os
import re
import json
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict


# ── Decision / Assumption Detectors ──────────────────────────────────────────

DECISION_MARKERS = [
    r"(?:decided|decision|agreed|confirmed|finalized|locked in|signed off|approved)\b",
    r"\b(?:will|shall|going to)\s+(?:use|go with|adopt|deploy|launch|ship|build|implement)",
    r"\b(?:chose|selected|picked|opted for)\b",
    r"\b(?:no longer|dropped|removed|deprecated|killed)\b",
]

ASSUMPTION_MARKERS = [
    r"\b(?:assume|assuming|assumption)\b",
    r"\b(?:should|probably|likely|expected|expecting|estimate|estimated)\b",
    r"\b(?:assume[sd]? that|assuming that)\b",
    r"\b(?:roughly|approximately|around|about)\s+\d",
    r"\b(?:baseline|given that|premise)\b",
]

VALIDATION_MARKERS = [
    r"\b(?:validated|verified|confirmed|tested|checked|measured|proved|data shows)\b",
    r"\b(?:user research|user test|A/B test|survey|interview|analytics)\b",
    r"\b(?:benchmark|metric|KPI|monitoring)\b",
]

# Risk amplifiers — patterns that make a decision/assumption scarier
RISK_AMPLIFIERS = [
    (r"\b(?:all|everyone|entire|complete|full|total|every)\b", "absolute"),
    (r"\b(?:never|always|impossible|guaranteed|definitely)\b", "overconfident"),
    (r"\b(?:simple|easy|straightforward|just|trivial|minor)\b", "hidden_complexity"),
    (r"\b(?:soon|quickly|ASAP|immediately|by \w+ \d)\b", "time_pressure"),
    (r"\b(?:no risk|safe|secure|stable|reliable)\b", "complacency"),
    (r"\b(?:TODO|FIXME|HACK|XXX|TBD|TBC)\b", "incomplete"),
]


def parse_date_from_filename(fname: str) -> datetime | None:
    """Try to extract a date from a filename like 2026-04-05.md or 2026-04-05-something.md."""
    m = re.search(r"(\d{4}-\d{2}-\d{2})", fname)
    if m:
        try:
            return datetime.strptime(m.group(1), "%Y-%m-%d")
        except ValueError:
            pass
    return None


def find_files(directory: str, since_days: int | None = None) -> list[tuple[Path, datetime | None]]:
    """Find .md files in directory, optionally filtered by date."""
    p = Path(directory)
    if not p.exists():
        print(f"ERROR: Directory not found: {directory}", file=sys.stderr)
        sys.exit(1)

    results = []
    cutoff = datetime.utcnow() - timedelta(days=since_days) if since_days else None

    for f in sorted(p.glob("*.md")):
        fdate = parse_date_from_filename(f.name)
        if cutoff and fdate and fdate < cutoff:
            continue
        results.append((f, fdate))

    return results


def extract_blocks(text: str) -> list[dict]:
    """Split text into lines/blocks and tag them."""
    lines = text.split("\n")
    blocks = []
    for i, raw in enumerate(lines):
        stripped = raw.strip()
        if not stripped or len(stripped) < 15:
            continue
        blocks.append({"line_num": i + 1, "text": stripped})
    return blocks


def classify_block(text: str) -> dict:
    """Classify a line/block as decision, assumption, validation, or neutral."""
    text_lower = text.lower()

    has_decision = any(re.search(p, text_lower) for p in DECISION_MARKERS)
    has_assumption = any(re.search(p, text_lower) for p in ASSUMPTION_MARKERS)
    has_validation = any(re.search(p, text_lower) for p in VALIDATION_MARKERS)

    amplifiers = []
    for pattern, label in RISK_AMPLIFIERS:
        if re.search(pattern, text_lower):
            amplifiers.append(label)

    kind = "neutral"
    if has_validation:
        kind = "validation"
    elif has_decision:
        kind = "decision"
    elif has_assumption:
        kind = "assumption"

    return {
        "kind": kind,
        "amplifiers": amplifiers,
        "has_decision": has_decision,
        "has_assumption": has_assumption,
        "has_validation": has_validation,
    }


def compute_risk_score(item: dict) -> int:
    """Compute a risk score 0-10 for an item."""
    score = 0
    kind = item["kind"]

    if kind == "assumption":
        score += 4
    elif kind == "decision":
        score += 2
    elif kind == "validation":
        score -= 3  # validated things are less risky
        return max(score, 0)

    # Risk amplifiers
    amp_weights = {
        "absolute": 2,
        "overconfident": 3,
        "hidden_complexity": 2,
        "time_pressure": 2,
        "complacency": 3,
        "incomplete": 2,
    }
    for amp in item["amplifiers"]:
        score += amp_weights.get(amp, 1)

    return min(score, 10)


def scan_file(filepath: Path, file_date: datetime | None) -> dict:
    """Scan a single file for decisions, assumptions, and validations."""
    try:
        text = filepath.read_text(encoding="utf-8")
    except Exception as e:
        return {"file": filepath.name, "error": str(e), "items": []}

    blocks = extract_blocks(text)
    items = []

    for block in blocks:
        classification = classify_block(block["text"])
        if classification["kind"] == "neutral":
            continue

        item = {
            "file": filepath.name,
            "file_date": file_date.isoformat() if file_date else None,
            "line": block["line_num"],
            "text": block["text"][:200],
            "kind": classification["kind"],
            "amplifiers": classification["amplifiers"],
            "risk_score": 0,
        }
        item["risk_score"] = compute_risk_score(item)
        items.append(item)

    return {"file": filepath.name, "date": file_date, "items": items}


def find_unvalidated(all_items: list[dict]) -> list[dict]:
    """Find decisions/assumptions that don't have nearby validations."""
    # Group by file proximity — if a decision appears in a file with no
    # validation markers, it's unvalidated
    file_has_validation = set()
    for item in all_items:
        if item["kind"] == "validation":
            file_has_validation.add(item["file"])

    unvalidated = []
    for item in all_items:
        if item["kind"] in ("decision", "assumption") and item["file"] not in file_has_validation:
            unvalidated.append(item)

    return sorted(unvalidated, key=lambda x: -x["risk_score"])


def format_report(directory: str, file_results: list[dict], all_items: list[dict], since_days: int | None) -> str:
    """Format the full risk drift report."""
    lines = []

    lines.append("=" * 70)
    lines.append("🔪 RISK DRIFT SCANNER — KILLJOY EDITION")
    lines.append(f"   Target: {directory}")
    lines.append(f"   Scanned: {len(file_results)} files, {len(all_items)} flagged items")
    if since_days:
        lines.append(f"   Window: last {since_days} days")
    lines.append(f"   Generated: {datetime.utcnow().isoformat()}Z")
    lines.append("=" * 70)

    # Stats
    decisions = [i for i in all_items if i["kind"] == "decision"]
    assumptions = [i for i in all_items if i["kind"] == "assumption"]
    validations = [i for i in all_items if i["kind"] == "validation"]
    unvalidated = find_unvalidated(all_items)
    high_risk = [i for i in all_items if i["risk_score"] >= 6]

    # Section 1: Executive Summary
    lines.append("")
    lines.append("━" * 70)
    lines.append("📋 EXECUTIVE SUMMARY")
    lines.append("━" * 70)
    lines.append("")
    lines.append(f"   Decisions found:      {len(decisions)}")
    lines.append(f"   Assumptions flagged:  {len(assumptions)}")
    lines.append(f"   Validations found:    {len(validations)}")
    lines.append(f"   Unvalidated items:    {len(unvalidated)}")
    lines.append(f"   High-risk (≥6):       {len(high_risk)}")
    lines.append("")

    if len(validations) > 0 and len(decisions) + len(assumptions) > 0:
        ratio = len(validations) / (len(decisions) + len(assumptions))
        if ratio < 0.2:
            verdict = "💀 Validation desert — almost nothing has been checked."
        elif ratio < 0.5:
            verdict = "🔴 Under-validated — more than half of decisions/assumptions lack evidence."
        elif ratio < 0.8:
            verdict = "🟡 Partially validated — some evidence, but gaps remain."
        else:
            verdict = "🟢 Well-validated — most decisions have supporting evidence."
        lines.append(f"   Validation ratio:     {ratio:.0%}")
        lines.append(f"   Verdict: {verdict}")
    elif len(decisions) + len(assumptions) > 0:
        lines.append("   ⚠️  Zero validations found for nonzero decisions/assumptions.")
    lines.append("")

    # Section 2: Top Unvalidated Items (the kill list)
    if unvalidated:
        lines.append("━" * 70)
        lines.append("🎯 UNVALIDATED ITEMS (ranked by risk)")
        lines.append("━" * 70)
        lines.append("")
        for i, item in enumerate(unvalidated[:15], 1):
            score_bar = "🔪" * min(item["risk_score"], 10)
            kind_label = {"decision": "📝 DECISION", "assumption": "⚠️  ASSUMPTION"}.get(item["kind"], item["kind"])
            date_str = f" [{item['file_date'][:10]}]" if item.get("file_date") else ""
            amps = f" ⚡{', '.join(item['amplifiers'])}" if item["amplifiers"] else ""
            lines.append(f"   {i:2d}. {score_bar} {kind_label}{date_str}{amps}")
            lines.append(f"       {item['text'][:120]}")
            lines.append(f"       → {item['file']}:{item['line']}")
            lines.append("")
        if len(unvalidated) > 15:
            lines.append(f"   ... and {len(unvalidated) - 15} more")
            lines.append("")

    # Section 3: Risk Amplifiers Detected
    amp_items = defaultdict(list)
    for item in all_items:
        for amp in item["amplifiers"]:
            amp_items[amp].append(item)

    if amp_items:
        lines.append("━" * 70)
        lines.append("🚨 RISK AMPLIFIERS (words that should scare you)")
        lines.append("━" * 70)
        lines.append("")
        amp_labels = {
            "absolute": "Absolutes (all, every, never) — no room for error",
            "overconfident": "Overconfidence (guaranteed, impossible) — famous last words",
            "hidden_complexity": "Hidden complexity (simple, easy, just) — it never is",
            "time_pressure": "Time pressure (soon, ASAP, by X) — rush breeds bugs",
            "complacency": "Complacency (safe, stable, no risk) — denial isn't a strategy",
            "incomplete": "Incomplete (TODO, FIXME, TBD) — known unknowns left hanging",
        }
        for amp, items in sorted(amp_items.items(), key=lambda x: -len(x[1])):
            label = amp_labels.get(amp, amp)
            lines.append(f"   {label}")
            lines.append(f"   Found {len(items)} time(s):")
            for item in items[:3]:
                lines.append(f"      • {item['text'][:100]}")
            if len(items) > 3:
                lines.append(f"      ... and {len(items) - 3} more")
            lines.append("")

    # Section 4: File-by-file breakdown
    lines.append("━" * 70)
    lines.append("📁 FILE BREAKDOWN")
    lines.append("━" * 70)
    lines.append("")
    for fr in file_results:
        if not fr["items"]:
            continue
        d = sum(1 for i in fr["items"] if i["kind"] == "decision")
        a = sum(1 for i in fr["items"] if i["kind"] == "assumption")
        v = sum(1 for i in fr["items"] if i["kind"] == "validation")
        max_risk = max(i["risk_score"] for i in fr["items"])
        date_str = f" ({fr['date'].isoformat()[:10]})" if fr.get("date") else ""
        risk_icon = "💀" if max_risk >= 7 else "🔴" if max_risk >= 5 else "🟡" if max_risk >= 3 else "🟢"
        lines.append(f"   {risk_icon} {fr['file']}{date_str}")
        lines.append(f"      decisions: {d} | assumptions: {a} | validations: {v} | max risk: {max_risk}")
        lines.append("")

    # Footer
    lines.append("=" * 70)
    lines.append("   \"Decisions without validation are just wishes with confidence.\"")
    lines.append("    — KILLJOY, Chief Skeptic Officer")
    lines.append("=" * 70)

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Risk Drift Scanner — KILLJOY Edition")
    parser.add_argument("directory", help="Directory to scan for .md files")
    parser.add_argument("--since", type=int, default=None, help="Only scan files from last N days")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    args = parser.parse_args()

    files = find_files(args.directory, args.since)
    if not files:
        print(f"No .md files found in {args.directory}", file=sys.stderr)
        sys.exit(1)

    file_results = []
    all_items = []

    for filepath, file_date in files:
        result = scan_file(filepath, file_date)
        file_results.append(result)
        all_items.extend(result["items"])

    if args.json:
        unvalidated = find_unvalidated(all_items)
        output = {
            "directory": args.directory,
            "files_scanned": len(file_results),
            "total_items": len(all_items),
            "decisions": len([i for i in all_items if i["kind"] == "decision"]),
            "assumptions": len([i for i in all_items if i["kind"] == "assumption"]),
            "validations": len([i for i in all_items if i["kind"] == "validation"]),
            "unvalidated_count": len(unvalidated),
            "high_risk_count": len([i for i in all_items if i["risk_score"] >= 6]),
            "unvalidated": unvalidated[:20],
            "all_items": all_items,
        }
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        report = format_report(args.directory, file_results, all_items, args.since)
        print(report)


if __name__ == "__main__":
    main()
