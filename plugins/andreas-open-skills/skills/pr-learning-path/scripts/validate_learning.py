#!/usr/bin/env python3
"""Validate final PR Learning Path JSON."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from learning_core import validate_learning


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("learning", type=Path)
    args = parser.parse_args()
    try:
        data = json.loads(args.learning.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    errors = validate_learning(data)
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 1
    print(f"Valid PR Learning Path: {args.learning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
