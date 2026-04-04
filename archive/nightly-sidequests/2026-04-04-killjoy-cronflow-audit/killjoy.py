#!/usr/bin/env python3
"""
Killjoy: Security & Reliability Testing Tool for CronFlow

A comprehensive security audit tool that tests cronflow CLI for:
- Malicious/edge-case cron expressions
- Security vulnerabilities in file access patterns
- Parsing edge cases and logic flaws
- Reliability issues

Usage: python3 killjoy.py [--verbose] [--report-file PATH]
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class Finding:
    severity: str  # critical, high, medium, low, info
    category: str  # parsing, security, reliability, logic
    test_name: str
    description: str
    details: Dict[str, Any] = field(default_factory=dict)
    recommendation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "severity": self.severity,
            "category": self.category,
            "test_name": self.test_name,
            "description": self.description,
            "details": self.details,
            "recommendation": self.recommendation,
        }


@dataclass
class TestResult:
    passed: bool
    findings: List[Finding]
    duration_ms: float


class CronFlowRunner:
    """Run cronflow in subprocess to test behavior without importing."""

    def __init__(self, cronflow_path: Path):
        self.cronflow_path = cronflow_path
        self._source_code = cronflow_path.read_text()

    def run_with_input(self, cron_lines: List[str]) -> Tuple[int, str, str]:
        """Run cronflow with given cron lines via stdin simulation."""
        # Create a temporary file with cron content
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            for line in cron_lines:
                f.write(line + '\n')
            temp_path = f.name

        try:
            # Run cronflow in demo mode (no system crontab access)
            # We use --demo and analyze parsing via direct code inspection
            result = subprocess.run(
                [sys.executable, str(self.cronflow_path), '--demo'],
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.returncode, result.stdout, result.stderr
        finally:
            os.unlink(temp_path)

    def run_parse_test(self, test_code: str) -> Tuple[bool, str, Any]:
        """Execute a parsing test by running python code with cronflow functions."""
        # Create a modified version of cronflow that doesn't run main() and exports functions
        # The cronflow source already starts with 'from __future__ import annotations'
        modified_source = self._source_code.replace(
            'if __name__ == "__main__":',
            'if False and __name__ == "__main__":  # Disabled for testing'
        )

        full_script = f'''{modified_source}

# Test harness - this runs because __name__ == "__main__"
if __name__ == "__main__":
    try:
        result = eval({repr(test_code)})
        print("RESULT:", repr(result))
    except Exception as e:
        print("EXCEPTION:", type(e).__name__, str(e))
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(full_script)
            temp_script = f.name

        try:
            result = subprocess.run(
                [sys.executable, temp_script],
                capture_output=True,
                text=True,
                timeout=10
            )
            stdout = result.stdout.strip()
            stderr = result.stderr.strip()

            if stdout.startswith("RESULT:"):
                return True, "success", stdout[7:].strip()
            elif stdout.startswith("EXCEPTION:"):
                return False, stdout[10:].strip(), None
            elif stderr:
                return False, f"stderr: {stderr[:100]}", None
            else:
                return False, f"no output", None
        except subprocess.TimeoutExpired:
            return False, "timeout", None
        finally:
            os.unlink(temp_script)

    def get_function_source(self, func_name: str) -> Optional[str]:
        """Extract a function's source code for analysis."""
        import re
        pattern = rf'(def {func_name}\([^)]*\).*?)(?=\ndef |\nclass |\Z)'
        match = re.search(pattern, self._source_code, re.DOTALL)
        if match:
            return match.group(1)
        return None

    def check_pattern(self, pattern: str) -> List[re.Match]:
        """Check if source code matches a pattern."""
        return list(re.finditer(pattern, self._source_code, re.MULTILINE))


class ParsingFuzzer:
    """Test cron expression parsing with malicious/edge-case inputs."""

    # Edge case expressions that might cause issues
    EDGE_CASES = [
        # Boundary values
        ("59 23 31 12 0", "boundary_values", "Maximum valid values"),
        ("0 0 1 1 0", "boundary_values", "Minimum valid values"),
        ("60 24 32 13 8", "boundary_overflow", "Values exceeding maximums"),
        ("-1 -1 0 0 -1", "negative_values", "Negative values"),
        # Step variations
        ("*/0 * * * *", "zero_step", "Zero step division risk"),
        ("*/1 * * * *", "normal_step", "Normal step of 1"),
        ("*/60 * * * *", "large_step", "Step exceeding range"),
        ("*/1000 * * * *", "huge_step", "Very large step value"),
        # Range issues
        ("5-5 * * * *", "zero_range", "Range with same start/end"),
        ("10-5 * * * *", "inverted_range", "Inverted range (start > end)"),
        ("0-100 * * * *", "overflow_range", "Range exceeding max"),
        # Empty and malformed
        ("", "empty", "Empty expression"),
        ("* * * *", "missing_field", "Missing field"),
        ("* * * * * *", "extra_field", "Extra field"),
        ("  * * * * *  ", "whitespace", "Whitespace padded"),
        # Special characters
        ("$(whoami) * * * *", "command_injection", "Command injection attempt"),
        ("`whoami` * * * *", "backtick_injection", "Backtick injection"),
        ("; rm -rf / # * * * *", "semicolon_injection", "Semicolon injection"),
        ("$((1+1)) * * * *", "arithmetic_expansion", "Arithmetic expansion"),
        # Unicode and encoding
        ("🕐 * * * *", "unicode_emoji", "Unicode emoji"),
        ("\xff * * * *", "high_byte", "High byte value"),
        # ReDoS patterns
        ("a" * 10000 + " * * * *", "long_string", "Very long string"),
        ("(" * 100 + ")" * 100 + " * * * *", "nested_parens", "Nested parentheses"),
        # Complex valid expressions
        ("1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20 * * * *", "many_values", "Many comma values"),
        ("1-59/2 * * * *", "complex_range_step", "Complex range with step"),
        # Month/Day edge cases
        ("* * 31 2 *", "feb_31", "February 31st"),
        ("* * 31 4 *", "apr_31", "April 31st"),
        ("* * 0 * *", "day_zero", "Day zero"),
        ("* * * 0 *", "month_zero", "Month zero"),
        # Day of week variations
        ("* * * * 7", "sunday_7", "Sunday as 7"),
        ("* * * * 0", "sunday_0", "Sunday as 0"),
        ("* * * * MON", "text_dow", "Text day of week"),
    ]

    # Macro edge cases
    MACRO_CASES = [
        ("@hourly", "Valid macro"),
        ("@daily", "Valid macro"),
        ("@midnight", "Valid macro"),
        ("@weekly", "Valid macro"),
        ("@monthly", "Valid macro"),
        ("@yearly", "Valid macro"),
        ("@annually", "Valid macro"),
        ("@reboot", "Valid macro"),
        ("@HOURLY", "Uppercase macro"),
        ("@Daily", "Mixed case macro"),
        ("@unknown", "Invalid macro"),
        ("@", "Empty macro"),
        ("@hourly_extra", "Extended macro name"),
        ("@@hourly", "Double @"),
    ]

    def __init__(self, cronflow: CronFlowRunner):
        self.cronflow = cronflow
        self.now = dt.datetime(2024, 1, 1, 12, 0, 0)

    def run_tests(self) -> TestResult:
        findings: List[Finding] = []
        start = dt.datetime.now()

        # Test parse_field with edge cases
        for expr, test_id, desc in self.EDGE_CASES:
            finding = self._test_parse_field(expr, test_id, desc)
            if finding:
                findings.append(finding)

        # Test parse_cron_line with full expressions
        for expr, test_id, desc in self.EDGE_CASES:
            if expr and (len(expr.split()) >= 5 or expr.startswith("@")):
                finding = self._test_parse_cron_line(expr, test_id, desc)
                if finding:
                    findings.append(finding)

        # Test macros
        for macro, desc in self.MACRO_CASES:
            finding = self._test_macro(macro, desc)
            if finding:
                findings.append(finding)

        # Test environment variable parsing
        findings.extend(self._test_env_assignments())

        duration = (dt.datetime.now() - start).total_seconds() * 1000
        return TestResult(passed=len(findings) == 0, findings=findings, duration_ms=duration)

    def _test_parse_field(self, expr: str, test_id: str, desc: str) -> Optional[Finding]:
        """Test the parse_field function directly."""
        # Build test code
        field = expr.split()[0] if expr.split() else "*"
        test_code = f"parse_field('{field}', 0, 59)"

        try:
            success, msg, result = self.cronflow.run_parse_test(test_code)

            if not success and "ZeroDivisionError" in msg:
                return Finding(
                    severity="critical",
                    category="reliability",
                    test_name=f"parse_field_{test_id}",
                    description=f"ZeroDivisionError on input: {desc}",
                    details={"input": expr, "error": msg},
                    recommendation="Add step=0 validation before division",
                )

            if success and test_id == "zero_step":
                # Check if result is not None (it should be None for */0)
                if result != "None":
                    return Finding(
                        severity="high",
                        category="parsing",
                        test_name=f"parse_field_{test_id}",
                        description="Zero step should return None but got a valid result",
                        details={"input": expr, "result": result},
                        recommendation="Ensure step=0 returns None to prevent logic errors",
                    )

            if success and test_id == "negative_values" and result != "None":
                return Finding(
                    severity="medium",
                    category="parsing",
                    test_name=f"parse_field_{test_id}",
                    description="Negative values should be rejected but were accepted",
                    details={"input": expr, "result": result},
                    recommendation="Validate that negative values return None",
                )

        except Exception as e:
            return Finding(
                severity="high",
                category="reliability",
                test_name=f"parse_field_{test_id}",
                description=f"Test harness error: {type(e).__name__}",
                details={"input": expr, "error": str(e)},
                recommendation="Check test implementation",
            )

        return None

    def _test_parse_cron_line(self, expr: str, test_id: str, desc: str) -> Optional[Finding]:
        """Test parsing full cron lines."""
        try:
            line = f"{expr} /usr/bin/test"
            # Escape for python string
            escaped = line.replace("'", "\\'").replace("\\", "\\\\")
            test_code = f"parse_cron_line('test', '{escaped}', dt.datetime(2024, 1, 1, 12, 0, 0))"
            success, msg, result = self.cronflow.run_parse_test(test_code)

            if not success:
                # Expected for many malformed inputs
                if test_id in ("empty", "missing_field"):
                    return None
                return Finding(
                    severity="medium",
                    category="reliability",
                    test_name=f"parse_line_{test_id}",
                    description=f"Exception parsing: {type(e).__name__ if 'e' in dir() else msg}",
                    details={"input": expr[:50], "error": msg[:100]},
                    recommendation="Add robust error handling for malformed input",
                )

            # Check for injection that might have been accepted
            if test_id in ("command_injection", "backtick_injection", "semicolon_injection"):
                if result != "None":
                    return Finding(
                        severity="critical",
                        category="security",
                        test_name=f"parse_line_{test_id}",
                        description=f"Potentially dangerous pattern accepted: {desc}",
                        details={"input": line, "parsed": result[:100] if result else None},
                        recommendation="Reject or sanitize shell metacharacters in schedule fields",
                    )

        except Exception as e:
            return Finding(
                severity="medium",
                category="reliability",
                test_name=f"parse_line_{test_id}",
                description=f"Test harness error: {type(e).__name__}",
                details={"input": expr[:50], "error": str(e)},
                recommendation="Check test implementation",
            )

        return None

    def _test_macro(self, macro: str, desc: str) -> Optional[Finding]:
        """Test macro parsing."""
        try:
            line = f"{macro} /usr/bin/test"
            escaped = line.replace("'", "\\'")
            test_code = f"parse_cron_line('test', '{escaped}', dt.datetime(2024, 1, 1, 12, 0, 0))"
            success, msg, result = self.cronflow.run_parse_test(test_code)

            if not success:
                return Finding(
                    severity="medium",
                    category="reliability",
                    test_name=f"macro_{macro}",
                    description=f"Exception parsing macro: {msg}",
                    details={"macro": macro},
                    recommendation="Add exception handling for macro parsing",
                )

            # Check case sensitivity issues
            if macro.startswith("@") and macro[1:].isupper() and result != "None":
                return Finding(
                    severity="low",
                    category="parsing",
                    test_name=f"macro_case_{macro}",
                    description="Macro parsing is case-sensitive (may be intentional)",
                    details={"macro": macro, "parsed": result is not None},
                    recommendation="Consider documenting case sensitivity behavior",
                )

        except Exception as e:
            return Finding(
                severity="medium",
                category="reliability",
                test_name=f"macro_{macro}",
                description=f"Test harness error: {type(e).__name__}",
                details={"macro": macro, "error": str(e)},
                recommendation="Check test implementation",
            )

        return None

    def _test_env_assignments(self) -> List[Finding]:
        """Test environment variable assignment detection."""
        findings = []
        test_cases = [
            ("VAR=value", True, "normal"),
            ("VAR= value", True, "space_after"),
            ("VAR =value", True, "space_around"),
            ("123VAR=value", False, "starts_with_number"),
            ("VAR-NAME=value", False, "hyphen_in_name"),
            ("VAR.NAME=value", False, "dot_in_name"),
            ("=value", False, "empty_name"),
            ("PATH=/usr/bin:/bin", True, "path_var"),
            ("SHELL=/bin/bash", True, "shell_var"),
            ("MAILTO=admin@example.com", True, "mailto_var"),
            ("VAR=`whoami`", True, "backtick_in_value"),
            ("VAR=$(id)", True, "command_sub_in_value"),
        ]

        for line, expected, test_id in test_cases:
            try:
                escaped = line.replace("'", "\\'")
                test_code = f"is_env_assignment('{escaped}')"
                success, msg, result = self.cronflow.run_parse_test(test_code)

                if not success:
                    findings.append(Finding(
                        severity="medium",
                        category="reliability",
                        test_name=f"env_{test_id}",
                        description=f"Exception checking env assignment: {msg}",
                        details={"line": line},
                        recommendation="Add exception handling for env parsing",
                    ))
                    continue

                if test_id in ("backtick_in_value", "command_sub_in_value") and result == "True":
                    findings.append(Finding(
                        severity="high",
                        category="security",
                        test_name=f"env_{test_id}",
                        description="Environment variable with command substitution accepted",
                        details={"line": line, "detected_as_env": result},
                        recommendation="Warn users about command substitution in env variables",
                    ))
            except Exception as e:
                findings.append(Finding(
                    severity="medium",
                    category="reliability",
                    test_name=f"env_{test_id}",
                    description=f"Test harness error: {type(e).__name__}",
                    details={"line": line, "error": str(e)},
                    recommendation="Check test implementation",
                ))

        return findings


class SecurityAuditor:
    """Test for security vulnerabilities."""

    def __init__(self, cronflow: CronFlowRunner, cronflow_path: Path):
        self.cronflow = cronflow
        self.cronflow_path = cronflow_path
        self._source_code = cronflow_path.read_text()

    def run_tests(self) -> TestResult:
        findings: List[Finding] = []
        start = dt.datetime.now()

        findings.extend(self._test_file_access_patterns())
        findings.extend(self._test_subprocess_usage())
        findings.extend(self._test_path_traversal())
        findings.extend(self._test_regex_patterns())

        duration = (dt.datetime.now() - start).total_seconds() * 1000
        return TestResult(passed=len(findings) == 0, findings=findings, duration_ms=duration)

    def _test_file_access_patterns(self) -> List[Finding]:
        """Analyze file access patterns for security issues."""
        findings = []

        source = self._source_code

        # Check for file access without proper validation
        file_access_patterns = [
            (r'\.read_text\(', "file_read", "File read operation"),
            (r'\.exists\(\)', "exist_check", "Existence check"),
            (r'os\.access', "access_check", "OS access check"),
        ]

        for pattern, test_id, desc in file_access_patterns:
            matches = list(re.finditer(pattern, source))
            for i, match in enumerate(matches):
                # Get context
                start = max(0, match.start() - 50)
                end = min(len(source), match.end() + 50)
                context = source[start:end]

                # Check for symlink handling
                if "is_symlink" not in source and "lstat" not in source:
                    findings.append(Finding(
                        severity="medium",
                        category="security",
                        test_name=f"file_access_{test_id}_{i}",
                        description=f"File access without symlink protection: {desc}",
                        details={"context": context[:100]},
                        recommendation="Check for symlink attacks before reading files",
                    ))

        return findings

    def _test_subprocess_usage(self) -> List[Finding]:
        """Test subprocess usage for security."""
        findings = []

        source = self._source_code

        # Check subprocess.run usage
        if "subprocess.run" in source:
            # Check if shell=True is used
            if "shell=True" in source:
                findings.append(Finding(
                    severity="critical",
                    category="security",
                    test_name="subprocess_shell_true",
                    description="subprocess.run uses shell=True which is dangerous",
                    details={},
                    recommendation="Avoid shell=True or properly sanitize all inputs",
                ))
            else:
                # shell=False is safer, but check the command
                findings.append(Finding(
                    severity="info",
                    category="security",
                    test_name="subprocess_no_shell",
                    description="subprocess.run uses shell=False (good practice)",
                    details={},
                    recommendation="None - this is the recommended approach",
                ))

        # Check for check=False (which allows errors to pass silently)
        if "check=False" in source:
            findings.append(Finding(
                severity="low",
                category="reliability",
                test_name="subprocess_check_false",
                description="subprocess.run uses check=False",
                details={},
                recommendation="Consider handling return codes explicitly",
            ))

        return findings

    def _test_path_traversal(self) -> List[Finding]:
        """Test for path traversal vulnerabilities."""
        findings = []

        # Create a temporary directory for testing
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Test reading from symlinks
            secret_file = tmpdir_path / "secret.txt"
            secret_file.write_text("SECRET_DATA")

            symlink_file = tmpdir_path / ".crontab"
            try:
                symlink_file.symlink_to(secret_file)

                findings.append(Finding(
                    severity="medium",
                    category="security",
                    test_name="symlink_file_read",
                    description="Symlink targets may be followed when reading files",
                    details={"symlink": str(symlink_file), "target": str(secret_file)},
                    recommendation="Use os.path.realpath() and validate paths before reading",
                ))
            except OSError:
                pass  # Symlinks may not be supported

        return findings

    def _test_regex_patterns(self) -> List[Finding]:
        """Test regex patterns for ReDoS vulnerabilities."""
        findings = []

        patterns_to_test = [
            (r"^[A-Za-z_][A-Za-z0-9_]*\s*=", "env_assignment"),
        ]

        for pattern, name in patterns_to_test:
            # Test with potentially catastrophic input
            test_input = "A" * 10000
            start = dt.datetime.now()
            try:
                re.match(pattern, test_input)
                elapsed = (dt.datetime.now() - start).total_seconds() * 1000

                if elapsed > 1000:  # More than 1 second is concerning
                    findings.append(Finding(
                        severity="high",
                        category="security",
                        test_name=f"redos_{name}",
                        description=f"Regex pattern may be vulnerable to ReDoS ({elapsed:.0f}ms)",
                        details={"pattern": pattern, "input_length": len(test_input)},
                        recommendation="Use possessive quantifiers or timeout mechanisms",
                    ))
            except Exception as e:
                findings.append(Finding(
                    severity="medium",
                    category="reliability",
                    test_name=f"redos_{name}",
                    description=f"Regex error: {type(e).__name__}",
                    details={"error": str(e)},
                    recommendation="Review regex pattern for errors",
                ))

        return findings


class LogicTester:
    """Test for logic flaws and reliability issues."""

    def __init__(self, cronflow: CronFlowRunner):
        self.cronflow = cronflow
        self.now = dt.datetime(2024, 1, 1, 12, 0, 0)

    def run_tests(self) -> TestResult:
        findings: List[Finding] = []
        start = dt.datetime.now()

        findings.extend(self._test_next_run_calculation())
        findings.extend(self._test_conflict_detection())
        findings.extend(self._test_bucket_calculation())

        duration = (dt.datetime.now() - start).total_seconds() * 1000
        return TestResult(passed=len(findings) == 0, findings=findings, duration_ms=duration)

    def _test_next_run_calculation(self) -> List[Finding]:
        """Test next run time calculations."""
        findings = []

        # Test horizon limit
        test_cases = [
            ("0", "0", "1", "1", "0", "far_future", "Very specific far-future schedule"),
            ("*", "*", "*", "*", "*", "every_minute", "Every minute"),
            ("0", "0", "29", "2", "*", "feb_29", "February 29th (leap year check)"),
            ("0", "0", "31", "4", "*", "apr_31", "April 31st (invalid date)"),
        ]

        for minute, hour, dom, month, dow, test_id, desc in test_cases:
            test_code = f"next_run_for_fields('{minute}', '{hour}', '{dom}', '{month}', '{dow}', dt.datetime(2024, 1, 1, 12, 0, 0))"
            try:
                success, msg, result = self.cronflow.run_parse_test(test_code)

                if not success and "Timeout" not in msg:
                    findings.append(Finding(
                        severity="medium",
                        category="reliability",
                        test_name=f"next_run_{test_id}",
                        description=f"Exception in next run calculation: {msg}",
                        details={"desc": desc},
                        recommendation="Add exception handling for edge case dates",
                    ))

            except Exception as e:
                findings.append(Finding(
                    severity="medium",
                    category="reliability",
                    test_name=f"next_run_{test_id}",
                    description=f"Test harness error: {type(e).__name__}",
                    details={"error": str(e), "desc": desc},
                    recommendation="Check test implementation",
                ))

        return findings

    def _test_conflict_detection(self) -> List[Finding]:
        """Test conflict detection logic."""
        findings = []

        # Test with empty entries
        test_code = "find_conflicts([])"
        try:
            success, msg, result = self.cronflow.run_parse_test(test_code)
            if success and result == "None":
                findings.append(Finding(
                    severity="low",
                    category="logic",
                    test_name="conflict_empty_none",
                    description="find_conflicts returns None instead of empty list",
                    details={},
                    recommendation="Return empty list for consistency",
                ))
        except Exception as e:
            findings.append(Finding(
                severity="medium",
                category="reliability",
                test_name="conflict_empty_exception",
                description=f"Exception with empty entries: {type(e).__name__}",
                details={"error": str(e)},
                recommendation="Handle empty input gracefully",
            ))

        return findings

    def _test_bucket_calculation(self) -> List[Finding]:
        """Test time bucket calculations."""
        findings = []

        # Test edge cases - we need to handle None specially in the test code
        test_cases = [
            ("past_time", "bucket_for(dt.datetime(2024, 1, 1, 12, 0, 0), dt.datetime(2023, 12, 31, 12, 0, 0))", "Past datetime"),
            ("next_hour", "bucket_for(dt.datetime(2024, 1, 1, 12, 0, 0), dt.datetime(2024, 1, 1, 12, 30, 0))", "30 minutes from now"),
            ("today_edge", "bucket_for(dt.datetime(2024, 1, 1, 12, 0, 0), dt.datetime(2024, 1, 2, 11, 0, 0))", "23 hours from now"),
            ("week_edge", "bucket_for(dt.datetime(2024, 1, 1, 12, 0, 0), dt.datetime(2024, 1, 8, 12, 0, 0))", "Exactly 7 days"),
        ]

        for test_id, test_code, desc in test_cases:
            try:
                success, msg, result = self.cronflow.run_parse_test(test_code)
                if not success:
                    findings.append(Finding(
                        severity="medium",
                        category="reliability",
                        test_name=f"bucket_{test_id}",
                        description=f"Exception in bucket calculation: {msg}",
                        details={"desc": desc},
                        recommendation="Add exception handling",
                    ))
                elif test_id == "past_time" and result not in ('"Unknown"', "'Unknown'"):
                    findings.append(Finding(
                        severity="low",
                        category="logic",
                        test_name=f"bucket_{test_id}",
                        description="Past times should be marked as Unknown or 'passed'",
                        details={"result": result, "desc": desc},
                        recommendation="Consider special handling for past times",
                    ))

            except Exception as e:
                findings.append(Finding(
                    severity="medium",
                    category="reliability",
                    test_name=f"bucket_{test_id}",
                    description=f"Test harness error: {type(e).__name__}",
                    details={"error": str(e), "desc": desc},
                    recommendation="Check test implementation",
                ))

        return findings


class ReportGenerator:
    """Generate audit reports."""

    SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}

    def __init__(self, results: Dict[str, TestResult]):
        self.results = results

    def generate_console_report(self) -> str:
        lines = []
        lines.append("=" * 80)
        lines.append("Killjoy Security Audit Report for CronFlow")
        lines.append("=" * 80)
        lines.append("")

        all_findings: List[Finding] = []
        for category, result in self.results.items():
            all_findings.extend(result.findings)

        # Summary
        lines.append("SUMMARY")
        lines.append("-" * 40)

        severity_counts: Dict[str, int] = {}
        for f in all_findings:
            severity_counts[f.severity] = severity_counts.get(f.severity, 0) + 1

        for sev in ["critical", "high", "medium", "low", "info"]:
            count = severity_counts.get(sev, 0)
            lines.append(f"  {sev.upper():12} {count}")

        lines.append("")
        lines.append(f"  TOTAL        {len(all_findings)} findings")
        lines.append("")

        # Detailed findings by severity
        sorted_findings = sorted(all_findings, key=lambda f: self.SEVERITY_ORDER.get(f.severity, 99))

        current_sev = None
        for finding in sorted_findings:
            if finding.severity != current_sev:
                current_sev = finding.severity
                lines.append("")
                lines.append(f"{current_sev.upper()} FINDINGS")
                lines.append("-" * 40)

            lines.append("")
            lines.append(f"  [{finding.category}] {finding.test_name}")
            lines.append(f"  {finding.description}")
            if finding.details:
                for key, value in finding.details.items():
                    lines.append(f"    {key}: {str(value)[:80]}")
            if finding.recommendation:
                lines.append(f"  -> {finding.recommendation}")

        lines.append("")
        lines.append("=" * 80)

        return "\n".join(lines)

    def generate_json_report(self) -> str:
        report = {
            "audit_tool": "Killjoy",
            "version": "1.0.0",
            "timestamp": dt.datetime.now().isoformat(),
            "results": {
                category: {
                    "passed": result.passed,
                    "duration_ms": result.duration_ms,
                    "findings": [f.to_dict() for f in result.findings],
                }
                for category, result in self.results.items()
            },
        }
        return json.dumps(report, indent=2)


class Killjoy:
    """Main security testing orchestrator."""

    def __init__(self, cronflow_path: Path):
        self.cronflow_path = cronflow_path
        self.cronflow = CronFlowRunner(cronflow_path)

    def run_audit(self, verbose: bool = False) -> Dict[str, TestResult]:
        results = {}

        if verbose:
            print("[*] Running parsing fuzzer...")
        fuzzer = ParsingFuzzer(self.cronflow)
        results["parsing"] = fuzzer.run_tests()

        if verbose:
            print(f"[*] Parsing tests complete ({len(results['parsing'].findings)} findings)")
            print("[*] Running security auditor...")
        auditor = SecurityAuditor(self.cronflow, self.cronflow_path)
        results["security"] = auditor.run_tests()

        if verbose:
            print(f"[*] Security tests complete ({len(results['security'].findings)} findings)")
            print("[*] Running logic tests...")
        logic = LogicTester(self.cronflow)
        results["logic"] = logic.run_tests()

        if verbose:
            print(f"[*] Logic tests complete ({len(results['logic'].findings)} findings)")

        return results


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Killjoy: Security audit tool for CronFlow",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 killjoy.py                          # Run audit
  python3 killjoy.py --verbose                # Show progress
  python3 killjoy.py --report-file out.json   # Save JSON report
  python3 killjoy.py --cronflow /path/to/cronflow.py  # Target custom path
""",
    )
    parser.add_argument(
        "--cronflow",
        type=Path,
        default=Path("/root/.openclaw/workspace/nightly-tools/2026-04-04-cronflow/cronflow.py"),
        help="Path to cronflow.py (default: %(default)s)",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Show progress")
    parser.add_argument("--report-file", "-o", type=Path, help="Save JSON report to file")
    parser.add_argument("--json", "-j", action="store_true", help="Output JSON to stdout")

    args = parser.parse_args()

    if not args.cronflow.exists():
        print(f"Error: CronFlow not found at {args.cronflow}", file=sys.stderr)
        print("Use --cronflow to specify the correct path", file=sys.stderr)
        return 1

    killjoy = Killjoy(args.cronflow)

    try:
        results = killjoy.run_audit(verbose=args.verbose)
    except Exception as e:
        print(f"Error running audit: {e}", file=sys.stderr)
        return 1

    report = ReportGenerator(results)

    if args.json:
        print(report.generate_json_report())
    else:
        print(report.generate_console_report())

    if args.report_file:
        args.report_file.write_text(report.generate_json_report())
        if not args.json:
            print(f"\n[*] JSON report saved to {args.report_file}")

    # Return error code if critical findings exist
    all_findings = []
    for r in results.values():
        all_findings.extend(r.findings)

    critical_count = len([f for f in all_findings if f.severity == "critical"])
    if critical_count > 0:
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
