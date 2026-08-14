#!/usr/bin/env python3
"""Build one self-contained PR Learning Path HTML file."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from learning_core import validate_learning


def safe_json(data: object) -> str:
    return json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("learning", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        data = json.loads(args.learning.read_text(encoding="utf-8"))
        errors = validate_learning(data)
        if errors:
            raise ValueError("\n".join(errors))
        assets = Path(__file__).resolve().parents[1] / "assets"
        template = (assets / "learning.html").read_text(encoding="utf-8")
        brand_icon = (assets / "woven-loop.svg").read_text(encoding="utf-8").strip()
        for placeholder in ("__BRAND_ICON__", "__LEARNING_DATA__"):
            if template.count(placeholder) != 1:
                raise ValueError(f"template must contain one {placeholder} placeholder")
        html = template.replace("__BRAND_ICON__", brand_icon).replace("__LEARNING_DATA__", safe_json(data))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(html, encoding="utf-8")
    except (OSError, json.JSONDecodeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(f"Wrote self-contained HTML: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
