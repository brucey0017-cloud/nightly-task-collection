#!/usr/bin/env python3
"""
commit_bs_lint.py — KILLJOY's Git Commit BS Detector.

Scans git commit messages for patterns that hide risk, signal false
confidence, mask scope creep, or indicate problems the committer
doesn't want to admit. Because the commit log is where hope goes
to die quietly.

Usage:
    # Lint recent commits (last 20)
    python3 commit_bs_lint.py --recent 20

    # Lint a specific range
    python3 commit_bs_lint.py --range HEAD~10..HEAD

    # Lint a single message
    python3 commit_bs_lint.py --message "just a quick fix for the auth bug"

    # Lint all commits on current branch vs main
    python3 commit_bs_lint.py --branch main

    # Output as JSON
    python3 commit_bs_lint.py --recent 10 --json

    # Fail CI if high-severity findings
    python3 commit_bs_lint.py --recent 10 --fail-on high

Exit codes:
    0 — no findings above threshold (or --fail-on not set)
    1 — findings exceed --fail-on threshold
    2 — usage / runtime error

Zero dependencies. Python 3.7+. Requires git in PATH.
"""

import argparse
import json
import re
import subprocess
import sys
from collections import defaultdict
from typing import Dict, List, NamedTuple, Optional, Tuple


# ---------------------------------------------------------------------------
# Pattern definitions
# ---------------------------------------------------------------------------

class BSPattern(NamedTuple):
    category: str
    pattern: str
    description: str
    severity: str  # low / medium / high
    diagnosis: str
    remedy: str


PATTERNS: List[BSPattern] = [
    # --- False confidence ---
    BSPattern(
        "false_confidence",
        r"\b(?:just|simply|merely|only|nothing more than)\b",
        "Minimization: diminishes the actual complexity of the change",
        "medium",
        "The author is either genuinely unaware of the complexity or doesn't want you to look closely.",
        "Replace 'just' with a description of what actually changed and why.",
    ),
    BSPattern(
        "false_confidence",
        r"(?:quick|minor|small|tiny|trivial|simple)(?:\s+(?:fix|change|update|tweak|patch|refactor))",
        "Understatement: labels the change as trivial — it rarely is",
        "high",
        "'Quick fixes' are the #1 source of regressions. If it's truly trivial, describe it precisely.",
        "Describe the actual change: what was broken, what was changed, what was tested.",
    ),
    BSPattern(
        "false_confidence",
        r"\b(?:should|hopefully|probably|might|appears to|seems to|looks like)\b",
        "Uncertainty broadcast: the author isn't sure their own change works",
        "high",
        "If you're not confident your code works, it doesn't belong on main.",
        "Add tests. Verify locally. Then commit with a factual description.",
    ),
    BSPattern(
        "false_confidence",
        r"\b(?:works? on my machine|WIP|work in progress|DO NOT MERGE|experimental)\b",
        "Known-bad commit: explicitly marked as unfinished or untested",
        "high",
        "This should be a draft PR, not a commit on a tracked branch.",
        "Use draft PRs or feature flags instead of committing known-broken code.",
    ),

    # --- Scope creep signals ---
    BSPattern(
        "scope_creep",
        r"\b(?:also|additionally|while (?:at|here|I'm? (?:at|here))|since (?:I|we)'(?:re| are) here)\b",
        "Scope creep: sneaking extra changes into an unrelated commit",
        "medium",
        "One thing led to another... and now this 'fix' touches 47 files.",
        "One commit per logical change. Unrelated changes get their own commits.",
    ),
    BSPattern(
        "scope_creep",
        r"(?:and|plus|along with|as well as).{0,40}(?:fix|update|change|add|refactor|clean)",
        "Compound commit: multiple changes bundled together",
        "medium",
        "When you can't describe a commit in one sentence, it's doing too much.",
        "Split into separate commits with clear individual purposes.",
    ),
    BSPattern(
        "scope_creep",
        r"\b(?:cleanup|clean up|tidy|reorganize|misc)\b",
        "Vague umbrella: 'cleanup' is a black hole for unrelated changes",
        "medium",
        "'Cleanup' commits are where reverted features go to hide.",
        "Be specific: what was cleaned up, in which files, and why.",
    ),

    # --- Blame deflection ---
    BSPattern(
        "blame_deflection",
        r"\b(?:legacy|old code|previous implementation|someone(?:'s)? (?:old|previous) code|tech debt)\b",
        "Blame shift: implies the problem was someone else's fault",
        "low",
        "Classic. The code was bad, sure. But you touched it — own the change.",
        "Describe the fix, not the blame. Future readers care about what changed.",
    ),
    BSPattern(
        "blame_deflection",
        r"\b(?:had to|forced to|no choice|couldn't|couldn't avoid|necessary evil|unfortunately)\b",
        "Helplessness narrative: the author had no agency",
        "low",
        "You always have a choice. Document the tradeoff, not your feelings.",
        "State the constraint and the chosen tradeoff explicitly.",
    ),
    BSPattern(
        "blame_deflection",
        r"\b(?:according to|as requested|per|as per)\b",
        "Order-following: commits the change to someone else's authority",
        "low",
        "Not inherently bad, but often used to dodge responsibility for bad code.",
        "Still describe the change and its impact. 'Per X' doesn't excuse bad implementation.",
    ),

    # --- Missing information ---
    BSPattern(
        "missing_info",
        r"^(?:fix|update|change|add|remove|modify|handle|implement)\s*(?:\s|$|\.|,)",
        "Bare verb: says what was done but not why or what it affects",
        "medium",
        "'Fix bug' tells you nothing. In 6 months, nobody will know which bug or why.",
        "Include: what was broken (or needed), what changed, and why.",
    ),
    BSPattern(
        "missing_info",
        r"^(?:wip|todo|tmp|temp|hack|fixme|xxx|fix|stuf|things?)(?:\s|$|\.)",
        "Placeholder commit: barely a description at all",
        "high",
        "This commit message is the author giving up on communication.",
        "If you can't describe it, you don't understand it well enough to commit it.",
    ),
    BSPattern(
        "missing_info",
        r"^.{0,10}$",
        "Too short: commit message is essentially empty",
        "high",
        "The author typed less than 10 characters. That's not a message, that's a grunt.",
        "A commit message should answer: what changed, why, and what's the impact?",
    ),
    BSPattern(
        "missing_info",
        r"(?:\b(?:see|ref|references?|fixes?|closes?)\s+(?:#|issue|ticket|jira|bug)\s*\d+\b)",
        "Reference-only: links an issue but explains nothing about the change",
        "low",
        "Issue links are good, but the commit should still stand on its own.",
        "Add a brief summary of the change alongside the reference.",
    ),

    # --- Risky language ---
    BSPattern(
        "risky_language",
        r"\b(?:temp|temporary|for now|interim|placeholder|stopgap|band.?aid|hotfix|hack|workaround)\b",
        "Temporary permanence: 'temporary' code lives forever",
        "high",
        "'Temp' code has a half-life measured in years. It will outlast your job.",
        "If it's temporary, add a TODO with a deadline and a ticket number.",
    ),
    BSPattern(
        "risky_language",
        r"\b(?:skip|bypass|disable|comment out|ignore|suppress|silence|mute)\b.{0,30}(?:test|check|lint|validation|verify|guard|assert)",
        "Safety bypass: disabling a safety mechanism",
        "high",
        "Someone turned off the alarm instead of fixing the fire.",
        "Document exactly why the safety was bypassed and when it will be re-enabled.",
    ),
    BSPattern(
        "risky_language",
        r"\b(?:TODO|FIXME|HACK|XXX|NOQA|eslint-disable|type:\s*ignore|noinspection)\b",
        "Debt marker: acknowledged technical debt left in place",
        "medium",
        "The author knew it was wrong and did it anyway. At least they left a note.",
        "Each debt marker should have a ticket/issue reference and a deadline.",
    ),

    # --- Optimism patterns ---
    BSPattern(
        "optimism",
        r"\b(?:should (?:now|finally)|now (?:works?|fixed|resolved|properly|correctly)|should be (?:fixed|resolved|working))\b",
        "Hopeful assertion: claims it works without evidence",
        "medium",
        "'Should work' is not the same as 'tested and verified'.",
        "Include test evidence or verification steps in the commit message.",
    ),
    BSPattern(
        "optimism",
        r"\b(?:finally|at last|properly|correctly|right way|for real this? time)\b",
        "Repeat-attempt signal: this has been 'fixed' before",
        "medium",
        "Third time's the charm? Or is the underlying problem still ununderstood?",
        "Explain why previous attempts failed and why this one is different.",
    ),
    BSPattern(
        "optimism",
        r"\b(?:ready|done|complete|finished|shipped|final|last)\b",
        "Finality claim: declaring something complete (often premature)",
        "low",
        "'Final version' is a challenge the universe loves to accept.",
        "Be descriptive instead: 'Adds X feature with Y tests' > 'Feature complete'.",
    ),
]

# Compile patterns
COMPILED = [(bp, re.compile(bp.pattern, re.IGNORECASE)) for bp in PATTERNS]


# ---------------------------------------------------------------------------
# Git interaction
# ---------------------------------------------------------------------------

def get_commits_recent(count: int = 20) -> List[Dict[str, str]]:
    """Get recent commits with their messages."""
    try:
        result = subprocess.run(
            ["git", "log", f"-{count}", "--pretty=format:COMMIT:%H%nSUBJECT:%s%nBODY:%b%nEND_COMMIT"],
            capture_output=True, text=True, timeout=30,
        )
    except FileNotFoundError:
        print("Error: git not found in PATH", file=sys.stderr)
        sys.exit(2)
    except subprocess.TimeoutExpired:
        print("Error: git log timed out", file=sys.stderr)
        sys.exit(2)

    return _parse_git_log(result.stdout)


def get_commits_range(range_spec: str) -> List[Dict[str, str]]:
    """Get commits in a specific range."""
    try:
        result = subprocess.run(
            ["git", "log", range_spec, "--pretty=format:COMMIT:%H%nSUBJECT:%s%nBODY:%b%nEND_COMMIT"],
            capture_output=True, text=True, timeout=30,
        )
    except FileNotFoundError:
        print("Error: git not found in PATH", file=sys.stderr)
        sys.exit(2)

    return _parse_git_log(result.stdout)


def get_commits_vs_branch(branch: str) -> List[Dict[str, str]]:
    """Get commits on current branch that aren't on the target branch."""
    try:
        result = subprocess.run(
            ["git", "log", f"{branch}..HEAD", "--pretty=format:COMMIT:%H%nSUBJECT:%s%nBODY:%b%nEND_COMMIT"],
            capture_output=True, text=True, timeout=30,
        )
    except FileNotFoundError:
        print("Error: git not found in PATH", file=sys.stderr)
        sys.exit(2)

    return _parse_git_log(result.stdout)


def _parse_git_log(raw: str) -> List[Dict[str, str]]:
    """Parse git log output into structured commits."""
    commits = []
    current = None

    for line in raw.split("\n"):
        if line.startswith("COMMIT:"):
            if current:
                commits.append(current)
            current = {"hash": line[7:], "subject": "", "body": ""}
        elif line.startswith("SUBJECT:") and current is not None:
            current["subject"] = line[8:]
        elif line.startswith("BODY:") and current is not None:
            current["body"] = line[5:]
        elif line == "END_COMMIT":
            if current:
                commits.append(current)
                current = None
        elif current is not None and line.strip():
            # Continuation of body
            current["body"] += "\n" + line if current["body"] else line

    if current:
        commits.append(current)

    return commits


# ---------------------------------------------------------------------------
# Scanner
# ---------------------------------------------------------------------------

class Finding(NamedTuple):
    commit_hash: str
    commit_subject: str
    category: str
    severity: str
    description: str
    matched_text: str
    diagnosis: str
    remedy: str
    location: str  # "subject" or "body"


def scan_message(msg: str, location: str, commit_hash: str, commit_subject: str) -> List[Finding]:
    """Scan a single message string for BS patterns."""
    findings = []
    for bp, pat in COMPILED:
        for m in pat.finditer(msg):
            findings.append(Finding(
                commit_hash=commit_hash,
                commit_subject=commit_subject,
                category=bp.category,
                severity=bp.severity,
                description=bp.description,
                matched_text=m.group(0),
                diagnosis=bp.diagnosis,
                remedy=bp.remedy,
                location=location,
            ))
    return findings


def scan_commit(commit: Dict[str, str]) -> List[Finding]:
    """Scan a single commit for BS patterns."""
    findings = []
    short_hash = commit["hash"][:12] if commit["hash"] else "<unknown>"
    subject = commit["subject"]
    body = commit["body"]

    findings.extend(scan_message(subject, "subject", short_hash, subject))
    if body.strip():
        findings.extend(scan_message(body, "body", short_hash, subject))

    return findings


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

SEVERITY_ORDER = {"low": 0, "medium": 1, "high": 2}
SEVERITY_ICON = {"high": "🔴", "medium": "🟡", "low": "🟢"}


def format_report(findings: List[Finding], min_severity: str = "low") -> str:
    """Format findings as a human-readable report."""
    min_level = SEVERITY_ORDER.get(min_severity, 0)
    filtered = [f for f in findings if SEVERITY_ORDER.get(f.severity, 0) >= min_level]

    lines = []

    if not filtered:
        lines.append("🔪 KILLJOY Commit BS Detector")
        lines.append("=" * 50)
        lines.append("")
        lines.append("✅ Clean. Either the commit messages are genuinely good,")
        lines.append("   or the authors have gotten better at hiding their BS.")
        lines.append("")
        lines.append("   I'll be watching.")
        return "\n".join(lines)

    # Sort by severity desc
    filtered.sort(key=lambda f: (-SEVERITY_ORDER.get(f.severity, 0), f.commit_hash))

    lines.append("🔪 KILLJOY Commit BS Detector")
    lines.append("=" * 50)
    lines.append("")

    # Summary
    by_sev: Dict[str, int] = defaultdict(int)
    by_cat: Dict[str, int] = defaultdict(int)
    commits_flagged = set()

    for f in filtered:
        by_sev[f.severity] += 1
        by_cat[f.category] += 1
        commits_flagged.add(f.commit_hash)

    lines.append(f"📊 {len(filtered)} finding(s) across {len(commits_flagged)} commit(s)")
    lines.append("")
    lines.append("Severity:")
    for sev in ("high", "medium", "low"):
        if sev in by_sev:
            lines.append(f"  {SEVERITY_ICON[sev]} {sev}: {by_sev[sev]}")
    lines.append("")
    lines.append("Categories:")
    for cat, count in sorted(by_cat.items(), key=lambda x: -x[1]):
        lines.append(f"  {cat}: {count}")

    lines.append("")
    lines.append("—" * 50)
    lines.append("")

    # Group by commit
    by_commit: Dict[str, List[Finding]] = defaultdict(list)
    for f in filtered:
        by_commit[f.commit_hash].append(f)

    for commit_hash, commit_findings in by_commit.items():
        lines.append(f"📌 Commit {commit_hash}")
        subj = commit_findings[0].commit_subject
        if len(subj) > 80:
            subj = subj[:77] + "..."
        lines.append(f"   \"{subj}\"")
        lines.append("")

        for i, f in enumerate(commit_findings, 1):
            icon = SEVERITY_ICON.get(f.severity, "⚪")
            lines.append(f"   {i}. {icon} [{f.severity.upper()}] {f.category} ({f.location})")
            lines.append(f"      Matched: \"{f.matched_text}\"")
            lines.append(f"      ⚠️  {f.diagnosis}")
            lines.append(f"      💡 {f.remedy}")
            lines.append("")

        lines.append("— · — · — · —")
        lines.append("")

    return "\n".join(lines)


def format_json(findings: List[Finding], min_severity: str = "low") -> str:
    """Format findings as JSON."""
    min_level = SEVERITY_ORDER.get(min_severity, 0)
    filtered = [f for f in findings if SEVERITY_ORDER.get(f.severity, 0) >= min_level]
    return json.dumps([f._asdict() for f in filtered], indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="🔪 KILLJOY's Git Commit BS Detector — because your commit messages are lying to you.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --recent 20              # Lint last 20 commits
  %(prog)s --range HEAD~5..HEAD     # Lint specific range
  %(prog)s --branch main            # Lint commits vs main
  %(prog)s --message "just a fix"   # Lint a single message
  %(prog)s --recent 10 --json       # JSON output
  %(prog)s --recent 10 --fail-on high  # Exit 1 if high-severity findings
        """,
    )

    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--recent", type=int, metavar="N",
                        help="Scan the last N commits")
    source.add_argument("--range", metavar="RANGE",
                        help="Scan a git log range (e.g. HEAD~5..HEAD)")
    source.add_argument("--branch", metavar="BRANCH",
                        help="Scan commits on current branch vs BRANCH")
    source.add_argument("--message", metavar="MSG",
                        help="Scan a single commit message")

    parser.add_argument("--severity", choices=["low", "medium", "high"],
                        default="low",
                        help="Minimum severity to report (default: low)")
    parser.add_argument("--json", action="store_true", dest="json_output",
                        help="Output as JSON")
    parser.add_argument("--fail-on", choices=["low", "medium", "high"],
                        metavar="LEVEL",
                        help="Exit with code 1 if findings at or above LEVEL exist")

    args = parser.parse_args()

    # Get commits
    if args.message:
        commits = [{"hash": "<inline>", "subject": args.message, "body": ""}]
    elif args.recent:
        commits = get_commits_recent(args.recent)
    elif args.range:
        commits = get_commits_range(args.range)
    elif args.branch:
        commits = get_commits_vs_branch(args.branch)
    else:
        # Should not happen due to mutually_exclusive_group
        print("Error: specify --recent, --range, --branch, or --message", file=sys.stderr)
        sys.exit(2)

    if not commits:
        print("No commits found.", file=sys.stderr)
        sys.exit(0)

    # Scan
    all_findings = []
    for commit in commits:
        all_findings.extend(scan_commit(commit))

    # Output
    if args.json_output:
        print(format_json(all_findings, args.severity))
    else:
        print(format_report(all_findings, args.severity))

    # Exit code for --fail-on
    if args.fail_on:
        threshold = SEVERITY_ORDER.get(args.fail_on, 0)
        failing = [f for f in all_findings if SEVERITY_ORDER.get(f.severity, 0) >= threshold]
        if failing:
            sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
