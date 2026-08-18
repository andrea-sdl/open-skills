"""Promptfoo assertions backed by the standalone deterministic validator."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


PROJECT = Path(__file__).resolve().parents[1]
SCRIPTS = PROJECT / "skills" / "pr-learning-path" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from learning_core import LearningError, canonicalize, context_from_raw, validate_learning  # noqa: E402


def parsed(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    text = value.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines[-1].strip() == "```":
            text = "\n".join(lines[1:-1])
    return json.loads(text)


def build_context(fixture: dict[str, Any]) -> dict[str, Any]:
    return context_from_raw(
        mode="github",
        identity=fixture["identity"],
        title=fixture["title"],
        description=fixture["description"],
        commits=fixture["commits"],
        issues=fixture.get("issues", []),
        diff=fixture["diff"],
        revision=fixture["revision"],
        source_url=fixture["url"],
    )


def validate_candidate(output: Any, context: dict[str, Any]) -> dict[str, Any]:
    try:
        candidate = parsed(output)
        fixture = parsed(context["vars"]["fixture"])
        learning = canonicalize(build_context(fixture), candidate)
        errors = validate_learning(learning)
    except (KeyError, ValueError, TypeError, LearningError, json.JSONDecodeError) as error:
        return {"pass": False, "score": 0, "reason": str(error)}
    if errors:
        return {"pass": False, "score": 0, "reason": "\n".join(errors)}
    return {
        "pass": True,
        "score": 1,
        "reason": "The candidate passes the standalone deterministic contract.",
    }
