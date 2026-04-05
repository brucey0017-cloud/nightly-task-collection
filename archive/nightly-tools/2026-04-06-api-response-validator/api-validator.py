#!/usr/bin/env python3
"""
API Response Validator - A zero-dependency CLI tool for validating HTTP JSON API responses.
"""

import argparse
import json
import sys
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional


class ValidationError(Exception):
    """Raised when a validation check fails."""
    pass


def validate_type(value: Any, expected_type: str, field_path: str) -> None:
    """Validate that a value matches the expected type."""
    type_map = {
        'string': str,
        'number': (int, float),
        'boolean': bool,
        'array': list,
        'object': dict,
        'null': type(None)
    }

    if expected_type not in type_map:
        raise ValidationError(f"Unknown type '{expected_type}' for field '{field_path}'")

    expected = type_map[expected_type]
    if not isinstance(value, expected):
        actual_type = type(value).__name__
        raise ValidationError(
            f"Type mismatch for field '{field_path}': expected {expected_type}, got {actual_type}"
        )


def validate_field(data: Any, field: str, rules: Dict[str, Any], field_path: str) -> None:
    """Validate a single field against its rules."""
    full_path = f"{field_path}.{field}" if field_path else field

    # Check required field exists
    if field not in data:
        raise ValidationError(f"Missing required field: '{full_path}'")

    value = data[field]

    # Check type if specified
    if 'type' in rules:
        validate_type(value, rules['type'], full_path)

    # Check allowed values if specified
    if 'enum' in rules:
        if value not in rules['enum']:
            raise ValidationError(
                f"Invalid value for field '{full_path}': got '{value}', expected one of {rules['enum']}"
            )


def validate_response(data: Dict[str, Any], endpoint_config: Dict[str, Any]) -> None:
    """Validate response data against endpoint configuration."""
    required = endpoint_config.get('required', [])
    types = endpoint_config.get('types', {})
    enums = endpoint_config.get('enums', {})

    for field in required:
        rules = {}
        if field in types:
            rules['type'] = types[field]
        if field in enums:
            rules['enum'] = enums[field]
        validate_field(data, field, rules, '')


def fetch_response(url: str) -> Dict[str, Any]:
    """Fetch and parse JSON response from URL."""
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            content = response.read().decode('utf-8')
            return json.loads(content)
    except urllib.error.HTTPError as e:
        raise ValidationError(f"HTTP error {e.code}: {e.reason}")
    except urllib.error.URLError as e:
        raise ValidationError(f"Network error: {e.reason}")
    except json.JSONDecodeError as e:
        raise ValidationError(f"Invalid JSON response: {e}")
    except Exception as e:
        raise ValidationError(f"Request failed: {e}")


def run_validation(config_path: str, endpoint_filter: Optional[str] = None) -> bool:
    """Run validation for all endpoints or a specific one."""
    # Load config
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        print(f"Error: Config file not found: {config_path}", file=sys.stderr)
        return False
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in config file: {e}", file=sys.stderr)
        return False

    endpoints = config.get('endpoints', {})

    if not endpoints:
        print("Error: No endpoints defined in config", file=sys.stderr)
        return False

    # Filter endpoints if specified
    if endpoint_filter:
        if endpoint_filter not in endpoints:
            print(f"Error: Endpoint '{endpoint_filter}' not found in config", file=sys.stderr)
            return False
        endpoints = {endpoint_filter: endpoints[endpoint_filter]}

    all_passed = True

    for name, endpoint in endpoints.items():
        url = endpoint.get('url')
        if not url:
            print(f"✗ {name}: Missing URL in config", file=sys.stderr)
            all_passed = False
            if config.get('fail_fast', True):
                break
            continue

        print(f"→ Testing {name}: {url}")

        try:
            data = fetch_response(url)
            validate_response(data, endpoint)
            print(f"✓ {name}: Passed")
        except ValidationError as e:
            print(f"✗ {name}: {e}", file=sys.stderr)
            all_passed = False
            if config.get('fail_fast', True):
                print("\nFail-fast enabled, stopping validation.", file=sys.stderr)
                break

    return all_passed


def main():
    parser = argparse.ArgumentParser(
        description='Validate HTTP JSON API responses against simple expectations.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Config file format (JSON):
{
  "fail_fast": true,
  "endpoints": {
    "endpoint_name": {
      "url": "https://api.example.com/endpoint",
      "required": ["id", "name", "status"],
      "types": {
        "id": "number",
        "name": "string",
        "status": "string",
        "active": "boolean",
        "tags": "array"
      },
      "enums": {
        "status": ["active", "inactive"]
      }
    }
  }
}

Supported types: string, number, boolean, array, object, null
        """
    )
    parser.add_argument('config', help='Path to JSON config file')
    parser.add_argument('-e', '--endpoint', help='Validate only a specific endpoint')
    parser.add_argument('--version', action='version', version='%(prog)s 1.0.0')

    args = parser.parse_args()

    success = run_validation(args.config, args.endpoint)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
