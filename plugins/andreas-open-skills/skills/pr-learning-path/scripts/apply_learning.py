#!/usr/bin/env python3
"""Apply candidate Learning JSON to gathered context as one transaction."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from learning_core import LearningError, atomic_write_json, canonicalize, validate_learning


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("context", type=Path)
    parser.add_argument("candidate", type=Path, nargs="?")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        context = json.loads(args.context.read_text(encoding="utf-8"))
        candidate = json.loads(args.candidate.read_text(encoding="utf-8")) if args.candidate else None
        learning = canonicalize(context, candidate)
        errors = validate_learning(learning)
        if errors:
            raise LearningError("\n".join(errors))
        atomic_write_json(args.output, learning)
    except (LearningError, OSError, json.JSONDecodeError, IndexError, KeyError, TypeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    if "skip" in learning:
        print(f"Wrote {args.output}: skipped ({learning['skip']['reason']})")
    else:
        questions = sum(len(stage["questions"]) for stage in learning["stages"])
        print(f"Wrote {args.output}: {len(learning['stages'])} stages, {questions} questions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
