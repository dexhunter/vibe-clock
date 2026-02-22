#!/usr/bin/env python3
"""Bump vibe-clock version in pyproject.toml and propagate to all files.

Usage: python scripts/bump_version.py 1.5.0
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = ROOT / "pyproject.toml"

# Files that contain `dexhunter/vibe-clock@vX.Y.Z` references
README_FILES = [
    ROOT / "README.md",
    ROOT / "README.zh-CN.md",
    ROOT / "README.ja.md",
    ROOT / "README.es.md",
]

VERSION_RE = re.compile(r"^version\s*=\s*\"(.+?)\"", re.MULTILINE)
ACTION_REF_RE = re.compile(r"dexhunter/vibe-clock@v[\d.]+")


def read_current_version() -> str:
    text = PYPROJECT.read_text()
    m = VERSION_RE.search(text)
    if not m:
        print("Could not find version in pyproject.toml", file=sys.stderr)
        sys.exit(1)
    return m.group(1)


def bump(new_version: str) -> None:
    old_version = read_current_version()
    if old_version == new_version:
        print(f"Already at {new_version}")
        return

    # 1. Update pyproject.toml
    text = PYPROJECT.read_text()
    text = text.replace(f'version = "{old_version}"', f'version = "{new_version}"', 1)
    PYPROJECT.write_text(text)
    print(f"  pyproject.toml: {old_version} -> {new_version}")

    # 2. Update action refs in READMEs
    new_ref = f"dexhunter/vibe-clock@v{new_version}"
    for readme in README_FILES:
        if not readme.exists():
            continue
        content = readme.read_text()
        updated = ACTION_REF_RE.sub(new_ref, content)
        if updated != content:
            readme.write_text(updated)
            print(f"  {readme.name}: updated action ref to v{new_version}")

    print(f"\nBumped to {new_version}. Review changes, then commit.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <new-version>")
        print(f"Current version: {read_current_version()}")
        sys.exit(1)
    bump(sys.argv[1])
