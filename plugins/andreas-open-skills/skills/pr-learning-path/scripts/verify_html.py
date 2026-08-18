#!/usr/bin/env python3
"""Verify required static behavior in generated Learning HTML."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


REQUIRED_MARKERS = [
    'id="stage-nav"',
    'id="reset"',
    'id="theme"',
    "localStorage",
    "memoryStore",
    "source.revision",
    "woven-loop-title",
    "--background:",
    "--primary:",
    "--brand-warm:",
    "Color theme:",
    "source-project",
    "overflow-wrap: anywhere",
    "Review the sources",
    'target="_blank" rel="noopener noreferrer"',
    "Continue anyway",
    "data-option-index",
    "keydown",
    "prefers-color-scheme",
    "@media (max-width: 760px)",
]
FORBIDDEN_LABELS = ["Snapshot", "Walkthrough", "Validate", "readiness", "review tabs"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("html", type=Path)
    args = parser.parse_args()
    try:
        text = args.html.read_text(encoding="utf-8")
    except OSError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    errors = []
    for marker in REQUIRED_MARKERS:
        if marker not in text:
            errors.append(f"missing HTML behavior marker: {marker}")
    for label in FORBIDDEN_LABELS:
        if re.search(rf">\s*{re.escape(label)}\s*<", text, re.IGNORECASE):
            errors.append(f"forbidden UI label: {label}")
    match = re.search(r'<script id="learning-data" type="application/json">(.*?)</script>', text, re.DOTALL)
    if not match:
        errors.append("missing embedded learning data")
    else:
        try:
            json.loads(match.group(1))
        except json.JSONDecodeError as error:
            errors.append(f"invalid embedded learning data: {error}")
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 1
    print(f"Valid self-contained Learning HTML: {args.html}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
