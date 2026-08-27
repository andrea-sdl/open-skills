#!/usr/bin/env python3
"""Gather raw GitHub PR or local Git change context."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from learning_core import LearningError, atomic_write_json, context_from_raw, context_revision, run


PR_URL = re.compile(r"^https?://(?P<host>[^/]+)/(?P<owner>[^/]+)/(?P<repo>[^/]+)/pull/(?P<number>\d+)/?$")
PR_SHORT = re.compile(r"^(?P<owner>[^/\s]+)/(?P<repo>[^#\s]+)#(?P<number>\d+)$")
ISSUE_URL = re.compile(r"https?://[^/\s]+/[^/\s]+/[^/\s]+/issues/\d+")
ISSUE_SHORT = re.compile(r"(?i)\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\s+#(\d+)\b")


def parse_pr(value: str) -> dict[str, object] | None:
    match = PR_URL.match(value) or PR_SHORT.match(value)
    if not match:
        return None
    values = match.groupdict()
    return {
        "host": values.get("host") or "github.com",
        "owner": values["owner"],
        "repo": values["repo"],
        "number": int(values["number"]),
    }


def github_environment(host: str) -> dict[str, str]:
    environment = os.environ.copy()
    environment["GH_HOST"] = host
    return environment


def gather_issues(body: str, identity: dict[str, object], environment: dict[str, str]) -> list[dict[str, object]]:
    references: list[tuple[str, str | None]] = []
    for url in ISSUE_URL.findall(body):
        references.append((url.rstrip(".,;)"), None))
    for number in ISSUE_SHORT.findall(body):
        references.append((number, f"{identity['owner']}/{identity['repo']}"))
    unique: list[tuple[str, str | None]] = []
    for item in references:
        if item not in unique:
            unique.append(item)
    issues = []
    for reference, repo in unique[:5]:
        command = ["gh", "issue", "view", reference, "--json", "number,title,body,url,state"]
        if repo:
            command.extend(["--repo", repo])
        try:
            issues.append(json.loads(run(command, env=environment)))
        except LearningError as error:
            issues.append({"reference": reference, "available": False, "error": str(error)})
    return issues


def gather_github(identity: dict[str, object]) -> dict[str, object]:
    environment = github_environment(str(identity["host"]))
    repo = f"{identity['owner']}/{identity['repo']}"
    fields = "number,title,body,url,headRefOid,baseRefName,headRefName,commits,files,additions,deletions,changedFiles"
    metadata = json.loads(run([
        "gh", "pr", "view", str(identity["number"]), "--repo", repo, "--json", fields
    ], env=environment))
    diff = run(["gh", "pr", "diff", str(identity["number"]), "--repo", repo], env=environment)
    commits = [
        {
            "sha": commit.get("oid", ""),
            "title": commit.get("messageHeadline", ""),
            "body": commit.get("messageBody", ""),
        }
        for commit in metadata.get("commits", [])
    ]
    issues = gather_issues(metadata.get("body") or "", identity, environment)
    return context_from_raw(
        mode="github",
        identity=identity,
        title=metadata["title"],
        description=metadata.get("body") or "",
        commits=commits,
        issues=issues,
        diff=diff,
        revision=metadata["headRefOid"],
        source_url=metadata["url"],
    )


def untracked_diff(root: Path, requested_paths: list[str] | None) -> str:
    command = ["git", "ls-files", "--others", "--exclude-standard"]
    if requested_paths:
        command.extend(["--", *requested_paths])
    paths = [path for path in run(command, cwd=root).splitlines() if path]
    patches = []
    for path in paths:
        result = subprocess.run(
            [
                "git",
                "diff",
                "--no-ext-diff",
                "--no-index",
                "--src-prefix=a/",
                "--dst-prefix=b/",
                "--",
                "/dev/null",
                path,
            ],
            cwd=root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if result.returncode not in {0, 1}:
            detail = result.stderr.strip() or result.stdout.strip()
            raise LearningError(f"git diff for untracked file failed: {detail}")
        patches.append(result.stdout)
    return "".join(patches)


def local_diff(root: Path, args: argparse.Namespace) -> tuple[str, str, list[dict[str, str]]]:
    if args.range:
        selector = args.range
        diff_command = ["git", "diff", "--no-ext-diff", selector]
        log_selector = selector
    elif args.base:
        selector = f"{args.base}...HEAD"
        diff_command = ["git", "diff", "--no-ext-diff", selector]
        log_selector = selector
    elif args.files:
        selector = "changed files"
        diff_command = ["git", "diff", "--no-ext-diff", "HEAD", "--", *args.files]
        log_selector = "HEAD"
        include_untracked = True
    else:
        selector = "working tree"
        diff_command = ["git", "diff", "--no-ext-diff", "HEAD"]
        log_selector = "HEAD"
        include_untracked = True
    if args.range or args.base:
        include_untracked = False
    diff = run(diff_command, cwd=root)
    if include_untracked:
        diff += untracked_diff(root, args.files)
    if not diff.strip():
        raise LearningError(f"no changes found for {selector}")
    log = run(["git", "log", "--format=%H%x09%s", "-20", log_selector], cwd=root)
    commits = []
    for line in log.splitlines():
        sha, _, title = line.partition("\t")
        commits.append({"sha": sha, "title": title, "body": ""})
    return diff, selector, commits


def gather_local(value: str, args: argparse.Namespace) -> dict[str, object]:
    requested = Path(value).expanduser().resolve()
    root = Path(run(["git", "rev-parse", "--show-toplevel"], cwd=requested).strip()).resolve()
    head = run(["git", "rev-parse", "HEAD"], cwd=root).strip()
    diff, selector, commits = local_diff(root, args)
    revision = context_revision(head, diff)
    identity = {"root": str(root), "selector": selector}
    return context_from_raw(
        mode="local",
        identity=identity,
        title=f"{root.name}: {selector}",
        description="",
        commits=commits,
        issues=[],
        diff=diff,
        revision=revision,
        source_url=root.as_uri(),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", help="PR URL, owner/repo#number, or local repository")
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--range", help="Git commit range or diff selector")
    selection.add_argument("--base", help="Diff base ref, compared with HEAD")
    selection.add_argument("--files", nargs="+", help="Changed paths in a local repo")
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        identity = parse_pr(args.source)
        if identity:
            if args.range or args.base or args.files:
                raise LearningError("local diff selectors cannot be used with a PR")
            context = gather_github(identity)
        else:
            context = gather_local(args.source, args)
        atomic_write_json(args.output, context)
    except (LearningError, OSError, json.JSONDecodeError, KeyError, TypeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    stats = context["source"]["stats"]
    limits = context["source"]["limits"]
    print(
        f"Wrote {args.output}: {context['eligibility']['decision']}, "
        f"{stats['productionFiles']} production files, "
        f"{stats['productionChangedLines']} changed lines, {limits['tier']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
