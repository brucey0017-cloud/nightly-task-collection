#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

DEFAULT_CURRENT_RUN = Path('/root/.openclaw/workspace/nightly-lab/current-run.json')
STAGE_ORDER = {'start': 0, 'artifact': 1, 'done': 2, 'error': 2}
KNOWN_STAGES = set(STAGE_ORDER)


def add_finding(findings: list[dict[str, Any]], severity: str, code: str, message: str, **context: Any) -> None:
    findings.append({
        'severity': severity,
        'code': code,
        'message': message,
        'context': context,
    })


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def is_symbolic_ref(value: Any) -> bool:
    if not isinstance(value, str) or not value:
        return False
    if value.startswith('/'):
        return False
    parts = value.split('.')
    if len(parts) < 2:
        return False
    allowed = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-'
    return all(part and all(ch in allowed for ch in part) for part in parts)


def expected_report_map(current_run: dict[str, Any]) -> dict[tuple[str, str], str]:
    mapping: dict[tuple[str, str], str] = {}
    for task_key, task_name in (('team_reports', 'team'), ('sidequest_reports', 'sidequest')):
        entries = current_run.get(task_key, {}) or {}
        for agent, path in entries.items():
            if isinstance(path, str):
                mapping[(agent, task_name)] = path
    return mapping


def parse_status_file(status_path: Path, findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    if not status_path.exists():
        add_finding(findings, 'error', 'missing_status_file', 'status.jsonl does not exist', path=str(status_path))
        return events

    for lineno, raw in enumerate(status_path.read_text().splitlines(), start=1):
        if not raw.strip():
            continue
        try:
            event = json.loads(raw)
        except json.JSONDecodeError as exc:
            add_finding(
                findings,
                'error',
                'malformed_jsonl',
                'Malformed JSONL line in status file',
                path=str(status_path),
                line=lineno,
                error=str(exc),
            )
            continue
        if not isinstance(event, dict):
            add_finding(
                findings,
                'error',
                'malformed_event',
                'Status event is not a JSON object',
                path=str(status_path),
                line=lineno,
                value=event,
            )
            continue
        event['_line'] = lineno
        events.append(event)
    return events


def check_event_fields(events: list[dict[str, Any]], expected_reports: dict[tuple[str, str], str], findings: list[dict[str, Any]]) -> None:
    for event in events:
        line = event.get('_line')
        agent = event.get('agent')
        task = event.get('task')
        stage = event.get('stage')
        report = event.get('report', '')
        artifact = event.get('artifact', '')

        if not all(isinstance(v, str) and v for v in (agent, task, stage)):
            add_finding(findings, 'error', 'missing_required_fields', 'Event missing required string fields', line=line, event=event)
            continue

        if stage not in KNOWN_STAGES:
            add_finding(findings, 'warning', 'unknown_stage', 'Event uses an unknown stage', line=line, stage=stage, agent=agent, task=task)

        if is_symbolic_ref(report):
            add_finding(
                findings,
                'error',
                'unresolved_report_reference',
                'Report field contains an unresolved symbolic reference instead of a path',
                line=line,
                agent=agent,
                task=task,
                report=report,
            )
        if is_symbolic_ref(artifact):
            add_finding(
                findings,
                'error',
                'unresolved_artifact_reference',
                'Artifact field contains an unresolved symbolic reference instead of a path',
                line=line,
                agent=agent,
                task=task,
                artifact=artifact,
            )

        expected_report = expected_reports.get((agent, task))
        if expected_report and isinstance(report, str) and report and report.startswith('/') and report != expected_report:
            add_finding(
                findings,
                'error',
                'report_path_mismatch',
                'Report path does not match current-run.json mapping',
                line=line,
                agent=agent,
                task=task,
                report=report,
                expected=expected_report,
            )

        if stage in {'artifact', 'done', 'error'}:
            if isinstance(report, str) and report.startswith('/') and not Path(report).exists():
                add_finding(
                    findings,
                    'error',
                    'missing_report_file',
                    'Report file referenced by terminal/progress event does not exist',
                    line=line,
                    agent=agent,
                    task=task,
                    report=report,
                )
            if isinstance(artifact, str) and artifact.startswith('/') and not Path(artifact).exists():
                add_finding(
                    findings,
                    'error',
                    'missing_artifact_path',
                    'Artifact path referenced by event does not exist',
                    line=line,
                    agent=agent,
                    task=task,
                    artifact=artifact,
                )


def check_stage_sequences(events: list[dict[str, Any]], findings: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        agent = event.get('agent')
        task = event.get('task')
        if isinstance(agent, str) and isinstance(task, str):
            grouped[(agent, task)].append(event)

    summary: dict[str, Any] = {}
    for (agent, task), items in sorted(grouped.items()):
        stages = [item.get('stage') for item in items if isinstance(item.get('stage'), str)]
        latest = items[-1] if items else None
        terminal_count = sum(1 for stage in stages if stage in {'done', 'error'})
        summary[f'{agent}:{task}'] = {
            'stages': stages,
            'latest_stage': latest.get('stage') if latest else None,
            'latest_line': latest.get('_line') if latest else None,
            'event_count': len(items),
        }

        if stages and stages[0] != 'start':
            add_finding(findings, 'warning', 'sequence_missing_start', 'Sequence does not begin with start', agent=agent, task=task, stages=stages)

        highest_seen = -1
        for idx, stage in enumerate(stages):
            if stage not in STAGE_ORDER:
                continue
            order = STAGE_ORDER[stage]
            if order < highest_seen:
                add_finding(findings, 'error', 'sequence_out_of_order', 'Stage sequence moves backward', agent=agent, task=task, stages=stages, index=idx)
                break
            highest_seen = max(highest_seen, order)

        if terminal_count > 1:
            add_finding(findings, 'warning', 'multiple_terminal_events', 'Sequence has multiple terminal events', agent=agent, task=task, stages=stages)

        if stages and stages[-1] not in {'done', 'error'}:
            add_finding(findings, 'warning', 'missing_terminal_stage', 'Sequence has no terminal stage yet', agent=agent, task=task, stages=stages)

        if 'done' in stages and 'artifact' not in stages:
            add_finding(findings, 'warning', 'done_without_artifact', 'Sequence reached done without artifact stage', agent=agent, task=task, stages=stages)

    return summary


def build_report(current_run_path: Path, current_run: dict[str, Any], status_path: Path, events: list[dict[str, Any]], findings: list[dict[str, Any]], sequence_summary: dict[str, Any]) -> dict[str, Any]:
    counts = Counter(item['severity'] for item in findings)
    return {
        'ok': not findings,
        'current_run': str(current_run_path),
        'status_file': str(status_path),
        'run_id': current_run.get('run_id'),
        'logical_date': current_run.get('logical_date'),
        'event_count': len(events),
        'finding_counts': {'error': counts.get('error', 0), 'warning': counts.get('warning', 0)},
        'sequence_summary': sequence_summary,
        'findings': findings,
    }


def print_human(report: dict[str, Any]) -> None:
    print('Run Integrity Audit')
    print(f"- Run: {report.get('run_id')} ({report.get('logical_date')})")
    print(f"- current-run: {report.get('current_run')}")
    print(f"- status file: {report.get('status_file')}")
    print(f"- events parsed: {report.get('event_count')}")
    counts = report.get('finding_counts', {})
    print(f"- findings: {counts.get('error', 0)} error(s), {counts.get('warning', 0)} warning(s)")
    print('')
    if report['findings']:
        print('Findings:')
        for item in report['findings']:
            ctx = item.get('context', {})
            bits = []
            for key in ('line', 'agent', 'task', 'report', 'artifact', 'expected'):
                if key in ctx and ctx[key] not in ('', None):
                    bits.append(f'{key}={ctx[key]}')
            extra = f" [{' | '.join(bits)}]" if bits else ''
            print(f"- {item['severity'].upper()} {item['code']}: {item['message']}{extra}")
    else:
        print('Findings: none')

    print('')
    print('Latest sequences:')
    for key, value in sorted(report.get('sequence_summary', {}).items()):
        stages = ' -> '.join(value.get('stages', [])) or '(none)'
        print(f"- {key}: {stages}")


def exit_code(report: dict[str, Any]) -> int:
    counts = report.get('finding_counts', {})
    if counts.get('error', 0):
        return 2
    if counts.get('warning', 0):
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description='Audit nightly-lab run integrity from current-run.json and status.jsonl.')
    parser.add_argument('path', nargs='?', help='Optional path to current-run.json')
    parser.add_argument('--current-run', dest='current_run', help='Path to current-run.json')
    parser.add_argument('--status-file', dest='status_file', help='Path to status.jsonl')
    parser.add_argument('--json', action='store_true', help='Emit JSON output')
    args = parser.parse_args()

    current_run_path = Path(args.current_run or args.path or DEFAULT_CURRENT_RUN)
    findings: list[dict[str, Any]] = []

    if not current_run_path.exists():
        add_finding(findings, 'error', 'missing_current_run', 'current-run.json does not exist', path=str(current_run_path))
        report = {
            'ok': False,
            'current_run': str(current_run_path),
            'status_file': args.status_file or '',
            'run_id': None,
            'logical_date': None,
            'event_count': 0,
            'finding_counts': {'error': 1, 'warning': 0},
            'sequence_summary': {},
            'findings': findings,
        }
        if args.json:
            print(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            print_human(report)
        return exit_code(report)

    try:
        current_run = load_json(current_run_path)
    except Exception as exc:
        add_finding(findings, 'error', 'invalid_current_run', 'Failed to parse current-run.json', path=str(current_run_path), error=str(exc))
        report = {
            'ok': False,
            'current_run': str(current_run_path),
            'status_file': args.status_file or '',
            'run_id': None,
            'logical_date': None,
            'event_count': 0,
            'finding_counts': {'error': 1, 'warning': 0},
            'sequence_summary': {},
            'findings': findings,
        }
        if args.json:
            print(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            print_human(report)
        return exit_code(report)

    status_path = Path(args.status_file or current_run.get('status_file') or '')
    if not str(status_path):
        add_finding(findings, 'error', 'missing_status_reference', 'No status_file configured in args or current-run.json')
        report = build_report(current_run_path, current_run, Path(''), [], findings, {})
        if args.json:
            print(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            print_human(report)
        return exit_code(report)

    events = parse_status_file(status_path, findings)
    expected_reports = expected_report_map(current_run)
    check_event_fields(events, expected_reports, findings)
    sequence_summary = check_stage_sequences(events, findings)
    report = build_report(current_run_path, current_run, status_path, events, findings, sequence_summary)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_human(report)
    return exit_code(report)


if __name__ == '__main__':
    sys.exit(main())
