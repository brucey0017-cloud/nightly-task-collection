# Killjoy: CronFlow Security Audit Tool

A comprehensive security testing tool for the CronFlow CLI that identifies potential vulnerabilities, parsing edge cases, and reliability issues.

## Features

### 1. Parsing Fuzzer
Tests cron expression parsing with malicious and edge-case inputs:
- **Boundary values**: Maximum/minimum valid values and overflows
- **Step variations**: Zero step (division risk), large steps, invalid steps
- **Range issues**: Zero ranges, inverted ranges, overflow ranges
- **Injection attempts**: Command substitution, backticks, semicolons
- **Encoding attacks**: Null bytes, Unicode, high-byte values
- **ReDoS patterns**: Catastrophic backtracking in regex
- **Macro variations**: Case sensitivity, invalid macros

### 2. Security Auditor
Analyzes code for security vulnerabilities:
- **File access patterns**: Symlink attacks, path traversal
- **Subprocess usage**: Shell injection risks, error handling
- **Regex patterns**: ReDoS vulnerability detection
- **Input validation**: Missing sanitization checks

### 3. Logic Tester
Tests for logic flaws and reliability issues:
- **Next run calculation**: Horizon limits, leap year handling
- **Conflict detection**: Edge cases with empty/special inputs
- **Bucket calculation**: Time boundary edge cases

## Usage

```bash
# Basic audit
python3 killjoy.py

# Verbose output with progress
python3 killjoy.py --verbose

# Save JSON report
python3 killjoy.py --report-file audit-results.json

# Output JSON to stdout
python3 killjoy.py --json

# Target custom cronflow path
python3 killjoy.py --cronflow /path/to/cronflow.py
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Audit completed, no critical findings |
| 1 | Error (e.g., cronflow not found) |
| 2 | Critical findings detected |

## Report Format

### Console Output
```
================================================================================
Killjoy Security Audit Report for CronFlow
================================================================================

SUMMARY
----------------------------------------
  CRITICAL     0
  HIGH         2
  MEDIUM       4
  LOW          3
  INFO         1

  TOTAL        10 findings

HIGH FINDINGS
----------------------------------------

  [security] parse_line_command_injection
  Potentially dangerous pattern accepted: Command injection attempt
    input: $(whoami) * * * * /usr/bin/test
    parsed: CronEntry(...)
  -> Reject or sanitize shell metacharacters in schedule fields
```

### JSON Output
```json
{
  "audit_tool": "Killjoy",
  "version": "1.0.0",
  "timestamp": "2024-01-01T12:00:00",
  "results": {
    "parsing": {
      "passed": false,
      "duration_ms": 150.2,
      "findings": [...]
    },
    "security": {...},
    "logic": {...}
  }
}
```

## Test Categories

### Parsing Tests
| Test ID | Description | Severity |
|---------|-------------|----------|
| `zero_step` | Zero step division risk | High |
| `negative_values` | Negative value handling | Medium |
| `command_injection` | Shell injection in schedule | Critical |
| `env_backtick_in_value` | Command substitution in env vars | High |
| `null_byte` | Null byte handling | Medium |

### Security Tests
| Test ID | Description | Severity |
|---------|-------------|----------|
| `symlink_file_read` | Symlink attack vectors | Medium |
| `subprocess_shell_true` | Shell injection risk | Critical |
| `redos_env_assignment` | Catastrophic regex backtracking | High |

### Logic Tests
| Test ID | Description | Severity |
|---------|-------------|----------|
| `next_run_feb_29` | Leap year edge cases | Medium |
| `conflict_empty_none` | Empty list handling | Low |
| `bucket_past_time` | Past datetime handling | Low |

## Sample Findings

### Finding: Zero Step Division Risk
```python
# Input: */0 * * * *
# Current behavior: Returns None (correct)
# Risk: Older versions or modifications might raise ZeroDivisionError
```

### Finding: Environment Variable Injection
```python
# Input: VAR=`whoami`
# Current behavior: Detected as env assignment
# Risk: Cron will execute command substitution
# Recommendation: Warn users about this behavior
```

### Finding: Subprocess Safety
```python
# Current behavior: Uses shell=False (safe)
# Good practice: Command as list, not string
# Status: No action needed
```

## Architecture

```
killjoy.py
├── CronFlowImporter      # Safely imports cronflow module
├── ParsingFuzzer         # Tests parsing edge cases
│   ├── EDGE_CASES        # 40+ test expressions
│   ├── MACRO_CASES       # 10+ macro variations
│   └── _test_* methods   # Individual test functions
├── SecurityAuditor       # Analyzes security patterns
│   ├── _test_file_access()
│   ├── _test_subprocess()
│   ├── _test_path_traversal()
│   └── _test_regex()
├── LogicTester          # Tests business logic
│   ├── _test_next_run()
│   ├── _test_conflicts()
│   └── _test_buckets()
├── ReportGenerator      # Formats output
└── Killjoy              # Main orchestrator
```

## Dependencies

- Python 3.8+
- Standard library only (no external dependencies)

## Limitations

1. **Static analysis**: Some tests analyze source code patterns
2. **Demo mode only**: Tests parsing functions directly, not full CLI
3. **Local testing**: File security tests use temporary directories
4. **No fuzzing**: Uses predefined inputs, not random mutation

## Security Considerations

This tool is designed for authorized security testing of the CronFlow CLI. It:
- Does not modify any system files
- Uses temporary directories for file tests
- Does not execute untrusted commands
- Only reads from the specified cronflow.py file

## License

This is a security testing tool provided as-is for educational and defensive purposes.
