#!/usr/bin/env python3
"""
Simple API Testing Tool
Commander's Sidequest - Zero dependency HTTP API tester
"""

import json
import sys
import time
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from http.client import IncompleteRead


class APITester:
    def __init__(self):
        self.results = []
    
    def make_request(self, url, method='GET', headers=None, data=None, timeout=30):
        """Make HTTP request and return result"""
        start_time = time.time()
        
        try:
            # Prepare request
            req = Request(url, method=method.upper())
            
            # Add headers
            if headers:
                for key, value in headers.items():
                    req.add_header(key, value)
            
            # Add data for POST/PUT requests
            if data and method.upper() in ['POST', 'PUT']:
                if isinstance(data, dict):
                    data = json.dumps(data).encode('utf-8')
                    req.add_header('Content-Type', 'application/json')
                else:
                    data = data.encode('utf-8')
            
            # Make request
            print(f"🔍 Testing {method.upper()} {url}")
            response = urlopen(req, data=data, timeout=timeout)
            
            # Read response
            try:
                response_data = response.read().decode('utf-8')
            except IncompleteRead:
                response_data = ""
            
            # Calculate timing
            end_time = time.time()
            duration = end_time - start_time
            
            # Parse JSON if possible
            try:
                json_response = json.loads(response_data)
            except json.JSONDecodeError:
                json_response = None
            
            result = {
                'url': url,
                'method': method.upper(),
                'status_code': response.getcode(),
                'duration': round(duration, 3),
                'success': response.getcode() < 400,
                'headers': dict(response.headers),
                'data': response_data,
                'json_data': json_response,
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time))
            }
            
            return result
            
        except HTTPError as e:
            return self._handle_error(e, url, method, start_time)
        except URLError as e:
            return self._handle_error(e, url, method, start_time)
        except Exception as e:
            return self._handle_error(e, url, method, start_time)
    
    def _handle_error(self, error, url, method, start_time):
        """Handle various error types"""
        end_time = time.time()
        duration = end_time - start_time
        
        result = {
            'url': url,
            'method': method.upper(),
            'status_code': None,
            'duration': round(duration, 3),
            'success': False,
            'error': str(error),
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time))
        }
        
        if hasattr(error, 'code'):
            result['status_code'] = error.code
        
        return result
    
    def run_tests(self, test_config):
        """Run a series of API tests"""
        self.results = []
        
        for test in test_config.get('tests', []):
            result = self.make_request(
                url=test['url'],
                method=test.get('method', 'GET'),
                headers=test.get('headers'),
                data=test.get('data'),
                timeout=test.get('timeout', 30)
            )
            
            self.results.append(result)
            
            # Print result immediately
            status = "✅" if result['success'] else "❌"
            print(f"{status} {result['method']} {result['url']} - {result.get('status_code', 'ERROR')} ({result['duration']}s)")
        
        return self.results
    
    def generate_report(self):
        """Generate a simple report of test results"""
        if not self.results:
            return "No test results available"
        
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r['success'])
        failed_tests = total_tests - passed_tests
        
        report = f"""
API Testing Report
=================
Total Tests: {total_tests}
Passed: {passed_tests}
Failed: {failed_tests}
Success Rate: {(passed_tests/total_tests)*100:.1f}%

Detailed Results:
----------------"""
        
        for i, result in enumerate(self.results, 1):
            status = "✅ PASS" if result['success'] else "❌ FAIL"
            report += f"\n{i}. {status} - {result['method']} {result['url']}"
            
            if result['status_code']:
                report += f" - Status: {result['status_code']}"
            
            if not result['success']:
                report += f" - Error: {result.get('error', 'Unknown error')}"
            
            report += f" - Duration: {result['duration']}s"
            
            if result.get('json_data'):
                preview = str(result['json_data'])[:100]
                if len(str(result['json_data'])) > 100:
                    preview += "..."
                report += f" - Response: {preview}"
        
        return report


def load_config(config_path):
    """Load test configuration from JSON file"""
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ Config file not found: {config_path}")
        return None
    except json.JSONDecodeError:
        print(f"❌ Invalid JSON in config file: {config_path}")
        return None


def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python3 api_tester.py <config_file>")
        sys.exit(1)
    
    config_path = sys.argv[1]
    config = load_config(config_path)
    
    if not config:
        sys.exit(1)
    
    tester = APITester()
    results = tester.run_tests(config)
    
    # Generate and print report
    report = tester.generate_report()
    print(report)
    
    # Save report to file
    report_path = config_path.replace('.json', '_report.txt')
    with open(report_path, 'w') as f:
        f.write(report)
    print(f"📄 Report saved to: {report_path}")


if __name__ == "__main__":
    main()