#!/usr/bin/env python3
"""SSL/TLS certificate expiration checker.

Checks expiration dates for HTTPS endpoints and local certificate files.
Zero dependencies - uses only Python standard library.
"""

import argparse
import ssl
import socket
import sys
from datetime import datetime, timezone
from pathlib import Path


def get_cert_from_url(hostname: str, port: int, timeout: float) -> dict:
    """Fetch certificate from HTTPS endpoint."""
    try:
        context = ssl.create_default_context()
        with socket.create_connection((hostname, port), timeout=timeout) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert = ssock.getpeercert()
                return {"cert": cert, "error": None}
    except ssl.SSLCertVerificationError as e:
        # Self-signed or verification failure
        return {"cert": None, "error": "verification_failed"}
    except socket.timeout:
        return {"cert": None, "error": "timeout"}
    except socket.gaierror:
        return {"cert": None, "error": "resolve_failed"}
    except Exception as e:
        return {"cert": None, "error": f"connection_failed: {e}"}


def get_cert_from_file(path: str) -> dict:
    """Load certificate from local file."""
    try:
        cert_path = Path(path)
        if not cert_path.exists():
            return {"cert": None, "error": "file_not_found"}

        cert_data = cert_path.read_bytes()
        cert = ssl.load_pem_x509_certificate(cert_data)
        return {"cert": cert, "error": None}
    except Exception as e:
        return {"cert": None, "error": f"parse_failed: {e}"}


def parse_cert_expiry(cert) -> datetime:
    """Extract notAfter date from certificate."""
    # Handle dict from ssl.getpeercert()
    if isinstance(cert, dict):
        not_after_str = cert.get("notAfter")
        if not_after_str:
            # Format: 'Jan 15 12:00:00 2025 GMT'
            return datetime.strptime(not_after_str, "%b %d %H:%M:%S %Y GMT").replace(tzinfo=timezone.utc)
        return None

    # Handle cryptography certificate object (from file)
    if hasattr(cert, "not_valid_after"):
        not_after = cert.not_valid_after
        if not_after.tzinfo is None:
            not_after = not_after.replace(tzinfo=timezone.utc)
        return not_after
    if hasattr(cert, "not_valid_after_utc"):
        return cert.not_valid_after_utc

    return None


def check_target(target: str, warning_days: int, timeout: float) -> dict:
    """Check a single target and return result."""
    result = {
        "target": target,
        "status": "UNKNOWN",
        "expires": None,
        "days_remaining": None,
        "error": None
    }

    # Determine target type
    if target.startswith("https://"):
        # URL
        from urllib.parse import urlparse
        parsed = urlparse(target)
        hostname = parsed.hostname
        port = parsed.port or 443

        if not hostname:
            result["status"] = "ERROR"
            result["error"] = "invalid_url"
            return result

        fetch_result = get_cert_from_url(hostname, port, timeout)
    else:
        # Assume file path
        fetch_result = get_cert_from_file(target)

    if fetch_result["error"]:
        error = fetch_result["error"]
        if "verification_failed" in error:
            result["status"] = "UNKNOWN"
            result["error"] = "verification_failed"
        elif error in ("timeout", "resolve_failed") or "connection_failed" in error:
            result["status"] = "ERROR"
            result["error"] = error
        else:
            result["status"] = "ERROR"
            result["error"] = error
        return result

    cert = fetch_result["cert"]
    if not cert:
        result["status"] = "ERROR"
        result["error"] = "no_certificate"
        return result

    # Parse expiration
    expiry = parse_cert_expiry(cert)
    if not expiry:
        result["status"] = "ERROR"
        result["error"] = "could_not_parse_expiry"
        return result

    result["expires"] = expiry.strftime("%Y-%m-%d %H:%M:%S UTC")

    # Calculate days remaining
    now = datetime.now(timezone.utc)
    delta = expiry - now
    days = delta.days
    result["days_remaining"] = days

    # Determine status
    if days < 0:
        result["status"] = "EXPIRED"
    elif days <= warning_days:
        result["status"] = "EXPIRING"
    else:
        result["status"] = "VALID"

    return result


def format_output(result: dict) -> str:
    """Format result as parseable line."""
    parts = [
        result["target"],
        result["status"],
        result["expires"] or "N/A",
        str(result["days_remaining"]) if result["days_remaining"] is not None else "N/A"
    ]
    if result["error"]:
        parts.append(f"error={result['error']}")
    return " | ".join(parts)


def main():
    parser = argparse.ArgumentParser(
        description="SSL/TLS certificate expiration checker"
    )
    parser.add_argument(
        "targets",
        nargs="*",
        help="Target(s) to check: HTTPS URLs or certificate file paths"
    )
    parser.add_argument(
        "-w", "--warning-days",
        type=int,
        default=30,
        help="Warning threshold in days (default: 30)"
    )
    parser.add_argument(
        "-t", "--timeout",
        type=float,
        default=5.0,
        help="Network timeout in seconds (default: 5)"
    )
    parser.add_argument(
        "-f", "--file",
        help="Read targets from file (one per line)"
    )

    args = parser.parse_args()

    # Collect targets
    targets = list(args.targets) if args.targets else []

    if not targets and not args.file:
        parser.error("No targets specified. Provide targets as arguments or use -f/--file")
    if args.file:
        try:
            with open(args.file) as f:
                targets.extend(line.strip() for line in f if line.strip())
        except Exception as e:
            print(f"ERROR | failed to read file: {e}", file=sys.stderr)
            sys.exit(1)

    # Check each target
    exit_code = 0
    for target in targets:
        result = check_target(target, args.warning_days, args.timeout)
        print(format_output(result))
        if result["status"] in ("EXPIRED", "ERROR"):
            exit_code = 1

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
