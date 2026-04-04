#!/usr/bin/env python3
"""Create a small sample directory with duplicates for DupeSleuth smoke tests."""

from pathlib import Path
import shutil
import sys


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python3 create_sample_input.py /tmp/dupe-sleuth-sample", file=sys.stderr)
        return 1

    root = Path(sys.argv[1]).expanduser().resolve()
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)

    # Duplicate set A (3 copies)
    content_a = "hello duplicate world\n"
    write_text(root / "a" / "alpha.txt", content_a)
    write_text(root / "b" / "alpha-copy.txt", content_a)
    write_text(root / "c" / "nested" / "alpha-copy-2.txt", content_a)

    # Duplicate set B (2 copies)
    content_b = "another duplicated payload\n"
    write_text(root / "x" / "beta.log", content_b)
    write_text(root / "y" / "beta.bak", content_b)

    # Unique files
    write_text(root / "u" / "unique-1.txt", "only once\n")
    write_text(root / "u" / "unique-2.txt", "different content\n")

    print(f"Sample data created at: {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
