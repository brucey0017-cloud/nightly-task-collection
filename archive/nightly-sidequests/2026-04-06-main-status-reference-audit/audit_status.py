#!/usr/bin/env python3
"""
Workflow visibility audit tool for nightly-lab status files.

Checks status.jsonl and current-run.json for:
- Unresolved placeholder references (e.g., team_reports.killjoy)
- Missing or empty report paths
- Artifact paths that do not exist on disk
- Non-absolute paths where absolute paths are expected
- Stage ordering anomalies (e.g., artifact before start, done before artifact)
"""

import json
import os
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path


def load_status_jsonl(filepath):
    """Load status.jsonl file, returning list of (line_num, record) tuples."""
    records = []
    with open(filepath, 'r') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                records.append((line_num, record))
            except json.JSONDecodeError as e:
                records.append((line_num, {'_error': str(e), '_raw': line}))
    return records


def load_current_run(filepath):
    """Load current-run.json and extract reference mappings."""
    with open(filepath, 'r') as f:
        data = json.load(f)

    # Build reference lookup from team_reports and sidequest_reports
    refs = {
        'team_reports': data.get('team_reports', {}),
        'sidequest_reports': data.get('sidequest_reports', {})
    }
    return refs


def is_placeholder(value):
    """Check if a value is an unresolved placeholder reference."""
    if not value or not isinstance(value, str):
        return False
    # Patterns like "team_reports.agent_name" or "sidequest_reports.agent_name"
    return '.' in value and not value.startswith('/') and not value.startswith('./')


def is_absolute_path(value):
    """Check if value is an absolute path."""
    return isinstance(value, str) and value.startswith('/')


def check_file_exists(path):
    """Check if a file/directory exists (handles both files and dirs)."""
    return os.path.exists(path)


def audit_records(records, current_run_refs):
    """Run all audits on the loaded records."""
    issues = []

    # Track state per agent-task combination
    agent_task_stages = defaultdict(list)  # (agent, task) -> [(line_num, stage, record)]

    valid_stages = {'start', 'artifact', 'done'}
    expected_order = {'start': 0, 'artifact': 1, 'done': 2}

    for line_num, record in records:
        if '_error' in record:
            issues.append({
                'type': 'json_parse_error',
                'line': line_num,
                'message': f"JSON parse error: {record['_error']}",
                'raw': record.get('_raw', '')
            })
            continue

        agent = record.get('agent', '')
        task = record.get('task', '')
        stage = record.get('stage', '')
        artifact = record.get('artifact', '')
        report = record.get('report', '')

        key = (agent, task)
        agent_task_stages[key].append((line_num, stage, record))

        # Check 1: Unresolved placeholder references
        if is_placeholder(report):
            issues.append({
                'type': 'unresolved_placeholder',
                'line': line_num,
                'agent': agent,
                'task': task,
                'stage': stage,
                'field': 'report',
                'value': report,
                'message': f"Unresolved placeholder in report: '{report}'"
            })

        if is_placeholder(artifact):
            issues.append({
                'type': 'unresolved_placeholder',
                'line': line_num,
                'agent': agent,
                'task': task,
                'stage': stage,
                'field': 'artifact',
                'value': artifact,
                'message': f"Unresolved placeholder in artifact: '{artifact}'"
            })

        # Check 2: Missing or empty report paths (only for stages that should have them)
        if stage in ('artifact', 'done') and not report:
            issues.append({
                'type': 'empty_report',
                'line': line_num,
                'agent': agent,
                'task': task,
                'stage': stage,
                'message': f"Empty report path at '{stage}' stage"
            })

        # Check 3: Artifact path does not exist
        if artifact and not is_placeholder(artifact):
            if not is_absolute_path(artifact):
                issues.append({
                    'type': 'non_absolute_path',
                    'line': line_num,
                    'agent': agent,
                    'task': task,
                    'stage': stage,
                    'field': 'artifact',
                    'value': artifact,
                    'message': f"Non-absolute artifact path: '{artifact}'"
                })
            elif not check_file_exists(artifact):
                issues.append({
                    'type': 'missing_artifact',
                    'line': line_num,
                    'agent': agent,
                    'task': task,
                    'stage': stage,
                    'value': artifact,
                    'message': f"Artifact path does not exist: '{artifact}'"
                })

        # Check 4: Report path should be absolute
        if report and not is_placeholder(report):
            if not is_absolute_path(report):
                issues.append({
                    'type': 'non_absolute_path',
                    'line': line_num,
                    'agent': agent,
                    'task': task,
                    'stage': stage,
                    'field': 'report',
                    'value': report,
                    'message': f"Non-absolute report path: '{report}'"
                })
            elif not check_file_exists(report):
                # Report paths are allowed to not exist at 'start' stage
                if stage != 'start':
                    issues.append({
                        'type': 'missing_report',
                        'line': line_num,
                        'agent': agent,
                        'task': task,
                        'stage': stage,
                        'value': report,
                        'message': f"Report path does not exist: '{report}'"
                    })

    # Check 5: Stage ordering anomalies per agent/task
    for (agent, task), stages in agent_task_stages.items():
        seen_stages = set()
        last_stage_idx = -1

        for line_num, stage, record in stages:
            if stage not in valid_stages:
                issues.append({
                    'type': 'invalid_stage',
                    'line': line_num,
                    'agent': agent,
                    'task': task,
                    'stage': stage,
                    'message': f"Invalid stage '{stage}'"
                })
                continue

            current_idx = expected_order.get(stage, 999)

            # Check for going backwards in stage order
            if current_idx < last_stage_idx:
                issues.append({
                    'type': 'stage_order_anomaly',
                    'line': line_num,
                    'agent': agent,
                    'task': task,
                    'stage': stage,
                    'message': f"Stage '{stage}' appears out of order (previous stages: {[s for _, s, _ in stages[:stages.index((line_num, stage, record))]]})"
                })

            # Check for duplicate stages
            if stage in seen_stages:
                issues.append({
                    'type': 'duplicate_stage',
                    'line': line_num,
                    'agent': agent,
                    'task': task,
                    'stage': stage,
                    'message': f"Duplicate '{stage}' stage for {agent}/{task}"
                })

            seen_stages.add(stage)
            last_stage_idx = max(last_stage_idx, current_idx)

        # Check for missing stages
        expected_stages = {'start', 'artifact', 'done'}
        missing = expected_stages - seen_stages
        if missing:
            # Only report if we have at least one stage recorded
            if seen_stages:
                issues.append({
                    'type': 'missing_stages',
                    'agent': agent,
                    'task': task,
                    'stages': sorted(missing),
                    'message': f"Missing stages for {agent}/{task}: {sorted(missing)}"
                })

    return issues


def format_issue(issue):
    """Format a single issue for display."""
    line = issue.get('line', 'N/A')
    agent = issue.get('agent', '')
    task = issue.get('task', '')
    stage = issue.get('stage', '')
    msg = issue['message']

    parts = []
    if line != 'N/A':
        parts.append(f"Line {line:3d}")
    if agent and task:
        parts.append(f"[{agent}/{task}]")
    if stage:
        parts.append(f"({stage})")

    prefix = " | ".join(parts)
    if prefix:
        return f"{prefix}: {msg}"
    return msg


def group_issues_by_type(issues):
    """Group issues by their type for summary."""
    grouped = defaultdict(list)
    for issue in issues:
        grouped[issue['type']].append(issue)
    return grouped


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Audit nightly-lab status files for inconsistencies',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exit codes:
  0 - No issues found
  1 - Issues found
  2 - File or path error
""")
    parser.add_argument('status_jsonl', help='Path to status.jsonl file')
    parser.add_argument('current_run_json', help='Path to current-run.json file')
    parser.add_argument('-o', '--output', help='Write JSON output to file')
    parser.add_argument('-q', '--quiet', action='store_true', help='Quiet mode (only errors)')
    parser.add_argument('-s', '--summary-only', action='store_true', help='Only show summary')

    args = parser.parse_args()

    # Validate input files exist
    if not os.path.exists(args.status_jsonl):
        print(f"Error: status.jsonl not found: {args.status_jsonl}", file=sys.stderr)
        sys.exit(2)

    if not os.path.exists(args.current_run_json):
        print(f"Error: current-run.json not found: {args.current_run_json}", file=sys.stderr)
        sys.exit(2)

    # Load data
    try:
        records = load_status_jsonl(args.status_jsonl)
        if not args.quiet and not args.summary_only:
            print(f"Loaded {len(records)} records from {args.status_jsonl}")
    except Exception as e:
        print(f"Error loading status.jsonl: {e}", file=sys.stderr)
        sys.exit(2)

    try:
        refs = load_current_run(args.current_run_json)
    except Exception as e:
        print(f"Error loading current-run.json: {e}", file=sys.stderr)
        sys.exit(2)

    # Run audit
    issues = audit_records(records, refs)

    # Output
    if args.output:
        output_data = {
            'audited_at': datetime.now().isoformat(),
            'status_file': args.status_jsonl,
            'current_run_file': args.current_run_json,
            'total_issues': len(issues),
            'issues': issues
        }
        with open(args.output, 'w') as f:
            json.dump(output_data, f, indent=2)
        if not args.quiet:
            print(f"Output written to {args.output}")

    # Print results
    if not args.summary_only:
        for issue in issues:
            print(format_issue(issue))

    # Summary
    if issues:
        grouped = group_issues_by_type(issues)
        if not args.quiet:
            print(f"\n--- Summary ---")
            print(f"Total issues: {len(issues)}")
            for issue_type, items in sorted(grouped.items()):
                print(f"  {issue_type}: {len(items)}")
        sys.exit(1)
    else:
        if not args.quiet:
            print("No issues found.")
        sys.exit(0)


if __name__ == '__main__':
    main()
