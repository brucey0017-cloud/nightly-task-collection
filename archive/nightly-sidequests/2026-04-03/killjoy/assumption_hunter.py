#!/usr/bin/env python3
"""
Assumption Hunter - Find hidden assumptions and risks in project files
A killjoy special tool for surfacing potential project-killers before they happen.
"""

import os
import re
import sys
import argparse
from pathlib import Path
from typing import List, Dict, Tuple


class AssumptionHunter:
    def __init__(self):
        self.risk_keywords = [
            # Uncertainty words
            'assume', 'assume', 'suppose', 'presume', 'expect', 'anticipate',
            'hopefully', 'probably', 'likely', 'maybe', 'perhaps',
            
            # Risk indicators  
            'should', 'would', 'could', 'might', 'may', 'possibly',
            
            # Dangerous confidence
            'obviously', 'clearly', 'certainly', 'definitely', 'surely',
            'without doubt', 'of course', 'naturally',
            
            # Time pressure
            'quickly', 'fast', 'immediately', 'asap', 'urgent',
            'rushing', 'deadline', 'crunch',
            
            # Scale words
            'simple', 'easy', 'trivial', 'straightforward',
            'just', 'only', 'merely', 'barely',
        ]
        
        self.assumption_patterns = [
            r'\bwe assume\b',
            r'\bassuming\b',
            r'\bsuppose\b',
            r'\bwe expect\b',
            r'\banticipate\b',
            r'\bhoping\b',
            r'\bshould work\b',
            r'\bwould work\b',
            r'\bcould work\b',
            r'\bwe think\b',
            r'\bprobably\b',
            r'\blikely\b',
        ]
        
        self.danger_files = [
            'README.md', 'PLAN.md', 'PROPOSAL.md', 'DESIGN.md',
            'requirements.txt', 'package.json', 'config.yaml',
            'architecture.md', 'technical-spec.md'
        ]
    
    def scan_file(self, filepath: Path) -> List[Dict]:
        """Scan a single file for assumptions and risks"""
        results = []
        
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                
            for line_num, line in enumerate(lines, 1):
                line_lower = line.lower()
                
                # Check for risk keywords
                for keyword in self.risk_keywords:
                    if keyword in line_lower:
                        results.append({
                            'file': str(filepath),
                            'line': line_num,
                            'content': line.strip(),
                            'type': 'risk_word',
                            'keyword': keyword,
                            'severity': 'medium'
                        })
                
                # Check for assumption patterns
                for pattern in self.assumption_patterns:
                    if re.search(pattern, line_lower):
                        results.append({
                            'file': str(filepath),
                            'line': line_num,
                            'content': line.strip(),
                            'type': 'assumption',
                            'pattern': pattern,
                            'severity': 'high'
                        })
                        
        except Exception as e:
            results.append({
                'file': str(filepath),
                'line': 0,
                'content': f'ERROR reading file: {e}',
                'type': 'error',
                'severity': 'high'
            })
        
        return results
    
    def scan_directory(self, directory: str, extensions: List[str] = None) -> List[Dict]:
        """Scan directory for assumptions and risks"""
        if extensions is None:
            extensions = ['.md', '.txt', '.yaml', '.yml', '.json', '.py', '.js', '.ts']
        
        all_results = []
        directory_path = Path(directory)
        
        if not directory_path.exists():
            return [{
                'file': str(directory),
                'line': 0,
                'content': 'Directory does not exist',
                'type': 'error',
                'severity': 'high'
            }]
        
        # Get all files with specified extensions
        for ext in extensions:
            for file_path in directory_path.rglob(f'*{ext}'):
                # Always scan the file, but prioritize danger files by scanning them first
                all_results.extend(self.scan_file(file_path))
        
        return all_results
    
    def generate_report(self, results: List[Dict]) -> str:
        """Generate a human-readable report"""
        if not results:
            return "No assumptions or risks found."
        
        report = []
        report.append("# Assumption Hunter Report")
        report.append("")
        
        # Count by severity
        high_severity = [r for r in results if r.get('severity') == 'high']
        medium_severity = [r for r in results if r.get('severity') == 'medium']
        
        report.append(f"## Summary")
        report.append(f"- High severity findings: {len(high_severity)}")
        report.append(f"- Medium severity findings: {len(medium_severity)}")
        report.append(f"- Total findings: {len(results)}")
        report.append("")
        
        # High severity findings
        if high_severity:
            report.append("## 🔴 HIGH SEVERITY - ASSUMPTIONS FOUND")
            report.append("")
            for finding in high_severity:
                report.append(f"**{finding['file']}:{finding['line']}**")
                report.append(f"> {finding['content']}")
                if finding.get('keyword'):
                    report.append(f"  - Keyword: `{finding['keyword']}`")
                elif finding.get('pattern'):
                    report.append(f"  - Pattern: `{finding['pattern']}`")
                report.append("")
        
        # Medium severity findings
        if medium_severity:
            report.append("## 🟡 MEDIUM SEVERITY - RISK INDICATORS")
            report.append("")
            for finding in medium_severity:
                report.append(f"**{finding['file']}:{finding['line']}**")
                report.append(f"> {finding['content']}")
                report.append(f"  - Keyword: `{finding['keyword']}`")
                report.append("")
        
        # Warnings
        report.append("## ⚠️  WARNING")
        report.append("These findings represent potential project risks.")
        report.append("High severity items indicate unvalidated assumptions that could kill the project.")
        report.append("Medium severity items suggest areas that need validation.")
        report.append("")
        
        return "\n".join(report)


def main():
    parser = argparse.ArgumentParser(description='Find hidden assumptions and risks in project files')
    parser.add_argument('directory', nargs='?', default='.', help='Directory to scan (default: current)')
    parser.add_argument('--extensions', nargs='*', help='File extensions to scan')
    parser.add_argument('--output', help='Output file for report')
    
    args = parser.parse_args()
    
    hunter = AssumptionHunter()
    results = hunter.scan_directory(args.directory, args.extensions)
    report = hunter.generate_report(results)
    
    if args.output:
        with open(args.output, 'w') as f:
            f.write(report)
        print(f"Report saved to {args.output}")
    else:
        print(report)


if __name__ == '__main__':
    main()