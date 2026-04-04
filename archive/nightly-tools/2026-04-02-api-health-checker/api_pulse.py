#!/usr/bin/env python3
"""api_pulse.py - Minimal API health checker (HTTP 200 + JSON + latency)."""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass
class CheckResult:
    url: str
    ok: bool
    slow: bool
    status_code: int | None
    latency_ms: int | None
    message: str


def colorize(text: str, code: str, enabled: bool) -> str:
    if not enabled:
        return text
    return f"\033[{code}m{text}\033[0m"


def load_urls(file_path: str | None, cli_urls: List[str]) -> List[str]:
    urls: List[str] = []

    if file_path:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"URL file not found: {file_path}")
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            urls.append(line)

    urls.extend([u.strip() for u in cli_urls if u.strip()])

    # Deduplicate while preserving order
    seen = set()
    unique_urls = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            unique_urls.append(u)

    return unique_urls


def check_url(url: str, timeout_s: float, slow_ms: int) -> CheckResult:
    start = time.perf_counter()
    req = urllib.request.Request(url, method="GET", headers={"Accept": "application/json"})

    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            status = resp.getcode()
            body = resp.read(1024 * 1024)
            latency = int((time.perf_counter() - start) * 1000)

            if status != 200:
                return CheckResult(
                    url=url,
                    ok=False,
                    slow=False,
                    status_code=status,
                    latency_ms=latency,
                    message=f"HTTP {status} (expected 200)",
                )

            try:
                json.loads(body.decode("utf-8", errors="replace"))
            except Exception as e:
                return CheckResult(
                    url=url,
                    ok=False,
                    slow=False,
                    status_code=status,
                    latency_ms=latency,
                    message=f"Invalid JSON: {e}",
                )

            is_slow = latency > slow_ms
            return CheckResult(
                url=url,
                ok=True,
                slow=is_slow,
                status_code=status,
                latency_ms=latency,
                message="OK",
            )

    except urllib.error.HTTPError as e:
        latency = int((time.perf_counter() - start) * 1000)
        return CheckResult(
            url=url,
            ok=False,
            slow=False,
            status_code=e.code,
            latency_ms=latency,
            message=f"HTTPError: {e.code}",
        )
    except Exception as e:
        latency = int((time.perf_counter() - start) * 1000)
        return CheckResult(
            url=url,
            ok=False,
            slow=False,
            status_code=None,
            latency_ms=latency,
            message=f"Request failed: {e}",
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check APIs for HTTP 200 + JSON + response latency."
    )
    parser.add_argument("urls", nargs="*", help="API URLs to check")
    parser.add_argument(
        "--file",
        help="Optional text file with one URL per line (# comments allowed)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=5.0,
        help="Per-request timeout in seconds (default: 5.0)",
    )
    parser.add_argument(
        "--slow-ms",
        type=int,
        default=800,
        help="Latency threshold in ms for SLOW (default: 800)",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable ANSI colors",
    )

    args = parser.parse_args()

    try:
        urls = load_urls(args.file, args.urls)
    except Exception as e:
        print(f"Input error: {e}", file=sys.stderr)
        return 2

    if not urls:
        print("No URLs provided. Use positional URLs or --file.", file=sys.stderr)
        return 2

    use_color = (not args.no_color) and sys.stdout.isatty()

    results = [check_url(url, timeout_s=args.timeout, slow_ms=args.slow_ms) for url in urls]

    failures = [r for r in results if not r.ok]
    slows = [r for r in results if r.ok and r.slow]
    healthy = [r for r in results if r.ok and not r.slow]

    print(f"API Pulse | checked={len(results)} timeout={args.timeout}s slow>{args.slow_ms}ms")
    print("=" * 72)

    print(colorize(f"FAILURES ({len(failures)})", "31", use_color))
    if failures:
        for r in failures:
            print(f"  ❌ {r.url}")
            print(f"     -> {r.message} | latency={r.latency_ms}ms")
    else:
        print("  (none)")

    print()
    print(colorize(f"SLOW ({len(slows)})", "33", use_color))
    if slows:
        for r in slows:
            print(f"  ⚠️  {r.url}")
            print(f"     -> HTTP {r.status_code}, {r.latency_ms}ms")
    else:
        print("  (none)")

    print()
    print(colorize(f"HEALTHY ({len(healthy)})", "32", use_color))
    if healthy:
        for r in healthy:
            print(f"  ✅ {r.url} -> {r.latency_ms}ms")
    else:
        print("  (none)")

    print("=" * 72)
    print(
        f"Summary: fail={len(failures)} slow={len(slows)} healthy={len(healthy)} total={len(results)}"
    )

    if failures:
        return 2
    if slows:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
