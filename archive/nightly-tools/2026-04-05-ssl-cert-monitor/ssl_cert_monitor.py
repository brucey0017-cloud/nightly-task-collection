#!/usr/bin/env python3
"""Quick SSL/TLS certificate expiration checker.

Zero-dependency (Python stdlib only) CLI that checks certificates from:
- HTTPS endpoints (https://...)
- Local certificate files (.pem/.crt/.cer)
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import socket
import ssl
import tempfile
from typing import Iterable, List, Optional, Tuple
from urllib.parse import urlparse


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check SSL certificate expiration for HTTPS endpoints and cert files.",
    )
    parser.add_argument("targets", nargs="*", help="HTTPS URLs or local cert file paths")
    parser.add_argument(
        "-i",
        "--input-file",
        help="File containing one target per line (# comments and blank lines ignored)",
    )
    parser.add_argument(
        "-w",
        "--warn-days",
        type=int,
        default=30,
        help="Mark as EXPIRING when days_left <= warn-days (default: 30)",
    )
    parser.add_argument(
        "-t",
        "--timeout",
        type=float,
        default=5.0,
        help="Network timeout in seconds for HTTPS checks (default: 5)",
    )
    return parser.parse_args()


def load_targets(cli_targets: List[str], input_file: Optional[str]) -> List[str]:
    targets = list(cli_targets)
    if input_file:
        with open(input_file, "r", encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                targets.append(line)

    # keep order, de-duplicate
    seen = set()
    unique = []
    for t in targets:
        if t not in seen:
            seen.add(t)
            unique.append(t)
    return unique


def parse_not_after(not_after: str) -> dt.datetime:
    # OpenSSL cert date format from Python ssl.getpeercert / _test_decode_cert
    # Example: "Jun 15 12:00:00 2026 GMT"
    parsed = dt.datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z")
    return parsed.replace(tzinfo=dt.timezone.utc)


def classify(expiry: dt.datetime, warn_days: int) -> Tuple[str, int]:
    now = dt.datetime.now(dt.timezone.utc)
    days_left = int((expiry - now).total_seconds() // 86400)
    if days_left < 0:
        return "EXPIRED", days_left
    if days_left <= warn_days:
        return "EXPIRING", days_left
    return "VALID", days_left


def decode_file_cert(path: str) -> dict:
    # stdlib helper; supports PEM-formatted cert files.
    # For malformed/non-cert files, this raises.
    return ssl._ssl._test_decode_cert(path)  # type: ignore[attr-defined]


def fetch_url_cert(hostname: str, port: int, timeout: float, verify: bool = True, binary_form: bool = False):
    context = ssl.create_default_context() if verify else ssl._create_unverified_context()
    with socket.create_connection((hostname, port), timeout=timeout) as sock:
        with context.wrap_socket(sock, server_hostname=hostname) as tls:
            return tls.getpeercert(binary_form=binary_form)


def decode_der_not_after(der_cert: bytes) -> Optional[str]:
    pem = ssl.DER_cert_to_PEM_cert(der_cert)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".pem", delete=False, encoding="utf-8") as tmp:
            tmp.write(pem)
            temp_path = tmp.name
        cert = decode_file_cert(temp_path)
        return cert.get("notAfter")
    finally:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)


def check_url(target: str, warn_days: int, timeout: float) -> Tuple[str, str, str, str]:
    parsed = urlparse(target)
    if parsed.scheme != "https" or not parsed.hostname:
        return "ERROR", "-", "-", "invalid_https_url"

    host = parsed.hostname
    port = parsed.port or 443

    try:
        cert = fetch_url_cert(host, port, timeout, verify=True, binary_form=False)
        not_after = cert.get("notAfter")
        if not not_after:
            return "ERROR", "-", "-", "missing_notAfter"
        expiry = parse_not_after(not_after)
        status, days_left = classify(expiry, warn_days)
        return status, expiry.isoformat(), str(days_left), "ok"

    except ssl.SSLCertVerificationError:
        # Verification failed (self-signed/expired/hostname mismatch/etc).
        # Try unverified handshake to inspect expiration only.
        try:
            der_cert = fetch_url_cert(host, port, timeout, verify=False, binary_form=True)
            if not isinstance(der_cert, (bytes, bytearray)):
                return "UNKNOWN", "-", "-", "verify_failed_no_cert"
            not_after = decode_der_not_after(bytes(der_cert))
            if not not_after:
                return "UNKNOWN", "-", "-", "verify_failed_no_notAfter"
            expiry = parse_not_after(not_after)
            status, days_left = classify(expiry, warn_days)
            if status == "EXPIRED":
                return "EXPIRED", expiry.isoformat(), str(days_left), "verify_failed_but_expired"
            return "UNKNOWN", expiry.isoformat(), str(days_left), "verify_failed"
        except Exception as e:  # noqa: BLE001
            return "UNKNOWN", "-", "-", f"verify_failed:{type(e).__name__}"

    except socket.timeout:
        return "ERROR", "-", "-", "timeout"
    except Exception as e:  # noqa: BLE001
        return "ERROR", "-", "-", type(e).__name__


def check_file(path: str, warn_days: int) -> Tuple[str, str, str, str]:
    if not os.path.isfile(path):
        return "ERROR", "-", "-", "file_not_found"

    try:
        cert = decode_file_cert(path)
        not_after = cert.get("notAfter")
        if not not_after:
            return "ERROR", "-", "-", "missing_notAfter"
        expiry = parse_not_after(not_after)
        status, days_left = classify(expiry, warn_days)
        return status, expiry.isoformat(), str(days_left), "ok"
    except Exception as e:  # noqa: BLE001
        return "ERROR", "-", "-", type(e).__name__


def iter_results(targets: Iterable[str], warn_days: int, timeout: float):
    for target in targets:
        if target.startswith("https://"):
            status, expires_at, days_left, note = check_url(target, warn_days, timeout)
        else:
            status, expires_at, days_left, note = check_file(target, warn_days)
        yield status, target, expires_at, days_left, note


def main() -> int:
    args = parse_args()
    targets = load_targets(args.targets, args.input_file)

    if not targets:
        print("ERROR\t-\texpires_at=-\tdays_left=-\tnote=no_targets")
        return 2

    # parseable, no ANSI control chars
    # format: STATUS<TAB>TARGET<TAB>expires_at=<iso|-><TAB>days_left=<int|-><TAB>note=<text>
    seen_error = False
    seen_expired = False
    for status, target, expires_at, days_left, note in iter_results(targets, args.warn_days, args.timeout):
        print(
            f"{status}\t{target}\texpires_at={expires_at}\tdays_left={days_left}\tnote={note}"
        )
        if status == "ERROR":
            seen_error = True
        if status == "EXPIRED":
            seen_expired = True

    if seen_error:
        return 2
    if seen_expired:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
