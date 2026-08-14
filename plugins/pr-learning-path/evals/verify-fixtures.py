"""Check that eval fixtures contain raw source data and route as intended."""

from __future__ import annotations

import json
from pathlib import Path

import assertions


HERE = Path(__file__).resolve().parent


def load(name):
    data = json.loads((HERE / "fixtures" / name).read_text(encoding="utf-8"))
    forbidden = {"learning", "stages", "changeGroups", "walkthrough", "snapshot", "progress"}
    leaked = forbidden & set(data)
    if leaked:
        raise AssertionError(f"{name}: generated artifact fields found: {sorted(leaked)}")
    if not data.get("description") or not data.get("diff"):
        raise AssertionError(f"{name}: raw description and diff are required")
    return data


def main():
    for name in ("auth-boundary.json", "cache-flow.json"):
        context = assertions.build_context(load(name))
        if context["eligibility"]["decision"] != "required":
            raise AssertionError(f"{name}: expected required route")
    skip = assertions.build_context(load("presentation-skip.json"))
    if skip["eligibility"] != {"decision": "skip", "reason": "repeated-presentation-literal-change"}:
        raise AssertionError(f"presentation-skip.json: unexpected route {skip['eligibility']}")
    print("3/3 raw fixtures passed route and isolation checks")


if __name__ == "__main__":
    main()
