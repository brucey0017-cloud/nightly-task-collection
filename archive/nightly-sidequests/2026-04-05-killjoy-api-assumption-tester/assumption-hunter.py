#!/usr/bin/env python3
"""
Assumption Hunter - API Assumption Testing Tool
KILLJOY Edition: Tests your API assumptions against reality

A simple tool that validates API assumptions documented in YAML/JSON files
by making actual API calls and checking if reality matches expectations.
"""

import json
import yaml
import sys
import time
import argparse
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, List, Any, Optional


class AssumptionHunter:
    """Main class for testing API assumptions"""
    
    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.results = []
        self.passed = 0
        self.failed = 0
        
    def load_assumptions(self, file_path: str) -> List[Dict[str, Any]]:
        """Load assumptions from YAML or JSON file"""
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Assumptions file not found: {file_path}")
            
        with open(path, 'r', encoding='utf-8') as f:
            if path.suffix.lower() in ['.yaml', '.yml']:
                data = yaml.safe_load(f)
            elif path.suffix.lower() == '.json':
                data = json.load(f)
            else:
                raise ValueError(f"Unsupported file format: {path.suffix}")
        
        # Normalize data to list format
        if isinstance(data, dict):
            if 'assumptions' in data:
                assumptions = data['assumptions']
            elif 'tests' in data:
                assumptions = data['tests']
            else:
                assumptions = [{'name': k, 'url': v} for k, v in data.items()]
        else:
            assumptions = data
            
        return assumptions
    
    def test_api_assumption(self, assumption: Dict[str, Any]) -> Dict[str, Any]:
        """Test a single API assumption"""
        result = {
            'name': assumption.get('name', 'unnamed'),
            'url': assumption.get('url', ''),
            'method': assumption.get('method', 'GET').upper(),
            'expected_status': assumption.get('expected_status', 200),
            'expected_keys': assumption.get('expected_keys', []),
            'forbidden_keys': assumption.get('forbidden_keys', []),
            'timeout': assumption.get('timeout', self.timeout),
            'timestamp': time.time(),
            'passed': False,
            'error': None,
            'actual_status': None,
            'actual_keys': [],
            'response_size': 0
        }
        
        try:
            # Make the API request
            req = urllib.request.Request(
                result['url'],
                method=result['method'],
                headers={'User-Agent': 'AssumptionHunter/1.0'}
            )
            
            with urllib.request.urlopen(req, timeout=result['timeout']) as response:
                result['actual_status'] = response.status
                content = response.read()
                result['response_size'] = len(content)
                
                # Check if response is JSON
                content_type = response.getheader('Content-Type', '')
                if 'application/json' in content_type:
                    try:
                        response_data = json.loads(content.decode('utf-8'))
                        result['actual_keys'] = list(response_data.keys()) if isinstance(response_data, dict) else []
                    except json.JSONDecodeError:
                        result['actual_keys'] = ['invalid_json']
                else:
                    result['actual_keys'] = ['non_json_response']
                
        except urllib.error.HTTPError as e:
            result['actual_status'] = e.code
            result['error'] = f"HTTP {e.code}: {e.reason}"
        except urllib.error.URLError as e:
            result['error'] = f"URL Error: {e.reason}"
        except Exception as e:
            result['error'] = f"Unexpected error: {str(e)}"
        
        # Evaluate the result
        passed = True
        
        # Check status code
        if result['actual_status'] != result['expected_status']:
            passed = False
            
        # Check expected keys
        if result['expected_keys']:
            missing_keys = set(result['expected_keys']) - set(result['actual_keys'])
            if missing_keys:
                result['error'] = f"Missing expected keys: {missing_keys}"
                passed = False
                
        # Check forbidden keys
        if result['forbidden_keys']:
            forbidden_found = set(result['forbidden_keys']) & set(result['actual_keys'])
            if forbidden_found:
                result['error'] = f"Found forbidden keys: {forbidden_found}"
                passed = False
        
        result['passed'] = passed
        return result
    
    def run_tests(self, assumptions_file: str, verbose: bool = False) -> Dict[str, Any]:
        """Run all assumption tests"""
        assumptions = self.load_assumptions(assumptions_file)
        
        print(f"🔍 Testing {len(assumptions)} API assumptions...")
        print("=" * 60)
        
        for assumption in assumptions:
            if verbose:
                print(f"\n🧪 Testing: {assumption.get('name', 'unnamed')}")
                
            result = self.test_api_assumption(assumption)
            self.results.append(result)
            
            if result['passed']:
                self.passed += 1
                status = "✅ PASS"
                if verbose:
                    print(f"  {status}: {result['url']}")
            else:
                self.failed += 1
                status = "❌ FAIL"
                if verbose:
                    print(f"  {status}: {result['url']}")
                    if result['error']:
                        print(f"    Error: {result['error']}")
                    if result['actual_status'] != result.get('expected_status'):
                        print(f"    Status: Expected {result.get('expected_status')}, Got {result['actual_status']}")
        
        return self.get_summary()
    
    def get_summary(self) -> Dict[str, Any]:
        """Get test summary"""
        return {
            'total_tests': len(self.results),
            'passed': self.passed,
            'failed': self.failed,
            'pass_rate': (self.passed / len(self.results)) * 100 if self.results else 0,
            'results': self.results
        }
    
    def print_report(self, summary: Dict[str, Any], json_output: bool = False):
        """Print test report"""
        if json_output:
            print(json.dumps(summary, indent=2, default=str))
            return
            
        print(f"\n📊 Assumption Hunter Report")
        print("=" * 60)
        print(f"Total Tests: {summary['total_tests']}")
        print(f"Passed: {summary['passed']} ✅")
        print(f"Failed: {summary['failed']} ❌")
        print(f"Pass Rate: {summary['pass_rate']:.1f}%")
        
        if summary['failed'] > 0:
            print(f"\n❌ Failed Assumptions:")
            for result in summary['results']:
                if not result['passed']:
                    print(f"  • {result['name']}: {result['url']}")
                    if result['error']:
                        print(f"    Error: {result['error']}")


def create_sample_assumptions(filename: str = "sample_assumptions.yaml"):
    """Create a sample assumptions file"""
    sample_data = {
        'assumptions': [
            {
                'name': 'GitHub API Basic Test',
                'url': 'https://api.github.com',
                'method': 'GET',
                'expected_status': 200,
                'expected_keys': ['current_user_url', 'emojis_url', 'search_url']
            },
            {
                'name': 'JSONPlaceholder Test',
                'url': 'https://jsonplaceholder.typicode.com/posts/1',
                'method': 'GET',
                'expected_status': 200,
                'expected_keys': ['userId', 'id', 'title', 'body']
            },
            {
                'name': 'HTTPBin Test',
                'url': 'https://httpbin.org/get',
                'method': 'GET',
                'expected_status': 200,
                'expected_keys': ['args', 'headers', 'url']
            }
        ]
    }
    
    with open(filename, 'w') as f:
        yaml.dump(sample_data, f, default_flow_style=False)
    
    print(f"📝 Created sample assumptions file: {filename}")


def main():
    parser = argparse.ArgumentParser(description='Test API assumptions against reality')
    parser.add_argument('assumptions_file', nargs='?', help='Path to assumptions file (YAML/JSON)')
    parser.add_argument('--create-sample', action='store_true', help='Create a sample assumptions file')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--json', action='store_true', help='Output JSON format')
    parser.add_argument('--timeout', type=int, default=10, help='Request timeout in seconds')
    
    args = parser.parse_args()
    
    # Create sample file if requested
    if args.create_sample:
        create_sample_assumptions()
        return
    
    # Load assumptions file
    if not args.assumptions_file:
        print("❌ Error: Please specify an assumptions file or use --create-sample")
        parser.print_help()
        sys.exit(1)
    
    # Run the hunter
    hunter = AssumptionHunter(timeout=args.timeout)
    try:
        summary = hunter.run_tests(args.assumptions_file, args.verbose)
        hunter.print_report(summary, args.json)
        
        # Exit with appropriate code
        sys.exit(0 if summary['failed'] == 0 else 1)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()