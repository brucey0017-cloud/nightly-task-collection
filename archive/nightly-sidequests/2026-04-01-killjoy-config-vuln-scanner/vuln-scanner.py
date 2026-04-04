#!/usr/bin/env python3
"""
Config Vulnerability Scanner
A simple zero-dependency scanner to find potential security issues in config files
"""

import re
import sys
import os
from pathlib import Path

# Common vulnerable patterns
VULNERABILITY_PATTERNS = {
    'hardcoded_secrets': [
        r'password\s*[:=]\s*[\'"][^\'"]{8,}[\'"]',
        r'secret\s*[:=]\s*[\'"][^\'"]{8,}[\'"]',
        r'api[_-]?key\s*[:=]\s*[\'"][^\'"]{8,}[\'"]',
        r'token\s*[:=]\s*[\'"][^\'"]{8,}[\'"]',
    ],
    'insecure_configs': [
        r'allow[_-]?from\s*[:=]\s*0\.0\.0\.0',
        r'listen[_-]?address\s*[:=]\s*0\.0\.0\.0',
        r'bind\s*[:=]\s*0\.0\.0\.0',
        r'trusted[_-]?proxy\s*[:=]\s*\*',
    ],
    'dangerous_permissions': [
        r'chmod\s*[0-7]{3}\s*777',
        r'chmod\s*[0-7]{3}\s*666',
        r'permission\s*[:=]\s*777',
        r'ownership\s*[:=]\s*root.*root',
    ],
    'insecure_http': [
        r'http://[^/]',
        r'protocol\s*[:=]\s*http',
        r'force[_-]?http\s*[:=]\s*true',
    ],
    'debug_configs': [
        r'debug\s*[:=]\s*true',
        r'verbose\s*[:=]\s*true',
        r'log[_-]?level\s*[:=]\s*debug',
        r'trace\s*[:=]\s*true',
    ]
}

SEVERITY_LEVELS = {
    'hardcoded_secrets': 'CRITICAL',
    'insecure_configs': 'HIGH', 
    'dangerous_permissions': 'MEDIUM',
    'insecure_http': 'HIGH',
    'debug_configs': 'LOW'
}

def scan_file(file_path):
    """Scan a single file for vulnerabilities"""
    vulnerabilities = []
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
    except Exception as e:
        return [{
            'type': 'read_error',
            'line': 0,
            'match': str(e),
            'severity': 'ERROR'
        }]
    
    for line_num, line in enumerate(lines, 1):
        for vuln_type, patterns in VULNERABILITY_PATTERNS.items():
            for pattern in patterns:
                matches = re.finditer(pattern, line, re.IGNORECASE)
                for match in matches:
                    vulnerabilities.append({
                        'type': vuln_type,
                        'line': line_num,
                        'match': match.group(),
                        'context': line.strip(),
                        'severity': SEVERITY_LEVELS.get(vuln_type, 'MEDIUM')
                    })
    
    return vulnerabilities

def scan_directory(directory):
    """Scan all config files in a directory"""
    config_extensions = ['.conf', '.config', '.cfg', '.ini', '.env', '.yaml', '.yml', '.json', '.toml']
    all_vulnerabilities = []
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            if any(file.endswith(ext) for ext in config_extensions):
                file_path = Path(root) / file
                vulnerabilities = scan_file(file_path)
                all_vulnerabilities.extend({
                    'file': str(file_path),
                    **vuln
                } for vuln in vulnerabilities)
    
    return all_vulnerabilities

def generate_report(vulnerabilities):
    """Generate a human-readable report"""
    if not vulnerabilities:
        return "No vulnerabilities found."
    
    report = []
    report.append("=" * 50)
    report.append("CONFIG VULNERABILITY SCANNER REPORT")
    report.append("=" * 50)
    
    # Group by severity
    by_severity = {}
    for vuln in vulnerabilities:
        severity = vuln['severity']
        if severity not in by_severity:
            by_severity[severity] = []
        by_severity[severity].append(vuln)
    
    # Sort by severity
    severity_order = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'ERROR']
    for severity in severity_order:
        if severity in by_severity:
            report.append(f"\n🚨 {severity} VULNERABILITIES ({len(by_severity[severity])})")
            report.append("-" * 30)
            
            for vuln in by_severity[severity]:
                report.append(f"\nFile: {vuln['file']}")
                report.append(f"Line: {vuln['line']}")
                report.append(f"Type: {vuln['type']}")
                report.append(f"Found: {vuln['match']}")
                report.append(f"Context: {vuln['context']}")
                report.append("")
    
    report.append("=" * 50)
    report.append(f"Total vulnerabilities found: {len(vulnerabilities)}")
    report.append("=" * 50)
    
    return "\n".join(report)

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 vuln-scanner.py <directory_or_file>")
        sys.exit(1)
    
    target = sys.argv[1]
    
    if os.path.isfile(target):
        vulnerabilities = []
        for vuln in scan_file(target):
            vulnerabilities.append({
                'file': target,
                **vuln
            })
    elif os.path.isdir(target):
        vulnerabilities = scan_directory(target)
    else:
        print(f"Error: {target} is not a valid file or directory")
        sys.exit(1)
    
    print(generate_report(vulnerabilities))
    
    # Exit with error code if vulnerabilities found
    critical_high_count = len([v for v in vulnerabilities if v['severity'] in ['CRITICAL', 'HIGH']])
    if critical_high_count > 0:
        print(f"\n⚠️  Found {critical_high_count} critical/high severity vulnerabilities!")
        sys.exit(1)
    else:
        print(f"\n✅ Scan completed. No critical/high severity issues found.")
        sys.exit(0)

if __name__ == "__main__":
    main()