#!/usr/bin/env python3
"""
pulse - API rapid health checker
Single-file Python 3 tool with zero external dependencies.
"""

import argparse
import json
import sys
import time
import urllib.request
import urllib.error
from urllib.parse import urlparse


# ANSI color codes
class Colors:
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


def color(text, color_code):
    """Wrap text in color codes if stdout is a tty."""
    if sys.stdout.isatty():
        return f"{color_code}{text}{Colors.RESET}"
    return text


def check_endpoint(url, timeout=5):
    """
    Check a single endpoint.
    Returns: (status, response_time_ms, error_message)
    status: 'healthy', 'slow', or 'failed'
    """
    start_time = time.time()
    try:
        req = urllib.request.Request(url, method="GET")
        req.add_header("User-Agent", "pulse/1.0")
        req.add_header("Accept", "application/json")

        with urllib.request.urlopen(req, timeout=timeout) as response:
            elapsed_ms = (time.time() - start_time) * 1000
            body = response.read().decode("utf-8", errors="ignore")

            # Check HTTP status
            if response.status != 200:
                return "failed", elapsed_ms, f"HTTP {response.status}"

            # Check JSON validity
            try:
                json.loads(body)
            except json.JSONDecodeError:
                return "failed", elapsed_ms, "Invalid JSON"

            # Determine if slow (threshold configurable)
            if elapsed_ms > timeout * 1000 * 0.8:  # >80% of timeout = slow
                return "slow", elapsed_ms, None

            return "healthy", elapsed_ms, None

    except urllib.error.HTTPError as e:
        elapsed_ms = (time.time() - start_time) * 1000
        return "failed", elapsed_ms, f"HTTP {e.code}"
    except urllib.error.URLError as e:
        elapsed_ms = (time.time() - start_time) * 1000
        return "failed", elapsed_ms, str(e.reason)
    except TimeoutError:
        elapsed_ms = timeout * 1000
        return "failed", elapsed_ms, "Timeout"
    except Exception as e:
        elapsed_ms = (time.time() - start_time) * 1000
        return "failed", elapsed_ms, str(e)


def format_status(status, elapsed_ms, error=None):
    """Format a status line for output."""
    elapsed_str = f"{elapsed_ms:.0f}ms"

    if status == "healthy":
        indicator = color("✓", Colors.GREEN)
        status_text = color("HEALTHY", Colors.GREEN)
    elif status == "slow":
        indicator = color("⚠", Colors.YELLOW)
        status_text = color("SLOW", Colors.YELLOW)
    else:
        indicator = color("✗", Colors.RED)
        status_text = color("FAILED", Colors.RED)

    if error:
        return f"{indicator} {status_text:12} {elapsed_str:>8}  {error}"
    return f"{indicator} {status_text:12} {elapsed_str:>8}"


def load_endpoints(config_path):
    """Load endpoints from a simple config file."""
    endpoints = []
    with open(config_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # Format: URL or NAME=URL
            if "=" in line:
                name, url = line.split("=", 1)
                endpoints.append((name.strip(), url.strip()))
            else:
                endpoints.append((None, line))
    return endpoints


def run_checks(endpoints, timeout=5):
    """Run checks on all endpoints and return grouped results."""
    results = {
        "healthy": [],
        "slow": [],
        "failed": []
    }

    for name, url in endpoints:
        status, elapsed_ms, error = check_endpoint(url, timeout)
        display_name = name if name else url
        results[status].append((display_name, url, elapsed_ms, error))

    return results


def print_report(results):
    """Print grouped report with failures first, then slow, then healthy."""
    print()

    # Print failures first (most important)
    for name, url, elapsed_ms, error in results["failed"]:
        print(f"{name}")
        print(f"  {format_status('failed', elapsed_ms, error)}")
        print()

    # Print slow responses
    for name, url, elapsed_ms, error in results["slow"]:
        print(f"{name}")
        print(f"  {format_status('slow', elapsed_ms)}")
        print()

    # Print healthy
    for name, url, elapsed_ms, error in results["healthy"]:
        print(f"{name}")
        print(f"  {format_status('healthy', elapsed_ms)}")
        print()

    # Summary line
    healthy_count = len(results["healthy"])
    slow_count = len(results["slow"])
    failed_count = len(results["failed"])
    total = healthy_count + slow_count + failed_count

    if failed_count == 0 and slow_count == 0:
        summary = color("All systems green.", Colors.GREEN)
    else:
        parts = []
        if healthy_count:
            parts.append(f"{healthy_count}/{total} healthy")
        if slow_count:
            parts.append(f"{slow_count} slow")
        if failed_count:
            parts.append(color(f"{failed_count} failed", Colors.RED))
        summary = ", ".join(parts)

    print(color("─" * 50, Colors.BOLD))
    print(f"Summary: {summary}")


def main():
    parser = argparse.ArgumentParser(
        description="API rapid health checker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  pulse https://api.example.com/health
  pulse -c endpoints.txt
  pulse -c endpoints.txt -t 10
        """
    )
    parser.add_argument("urls", nargs="*", help="URLs to check")
    parser.add_argument("-c", "--config", help="Config file with endpoints (one per line)")
    parser.add_argument("-t", "--timeout", type=int, default=5, help="Response timeout in seconds (default: 5)")

    args = parser.parse_args()

    # Collect endpoints
    endpoints = []

    if args.config:
        try:
            endpoints.extend(load_endpoints(args.config))
        except FileNotFoundError:
            print(f"Error: Config file not found: {args.config}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Error reading config: {e}", file=sys.stderr)
            sys.exit(1)

    for url in args.urls:
        endpoints.append((None, url))

    if not endpoints:
        parser.print_help()
        sys.exit(1)

    # Run checks
    results = run_checks(endpoints, args.timeout)
    print_report(results)

    # Exit with error code if any failures
    if results["failed"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
