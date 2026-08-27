#!/usr/bin/env python3
"""Shared deterministic logic for PR Learning Path."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import quote


DOC_NAMES = {"readme", "changelog", "license", "contributing", "code-of-conduct"}
DOC_PARTS = {"doc", "docs", "documentation"}
TEST_PARTS = {"test", "tests", "spec", "specs", "__tests__", "fixtures"}
SKIP_REASON = "repeated-presentation-literal-change"
PRESENTATION_PATTERN = re.compile(
    r"(?:__\s*\(|_x\s*\(|label|title|placeholder|tooltip|help|description|"
    r"button|aria[-_]?label|accessible|\bname\s*=)",
    re.IGNORECASE,
)
TRIVIA_PATTERN = re.compile(
    r"(?:which (?:test|file|line|symbol|helper)|exact line|helper name|symbol name|"
    r"test (?:name|file)|documentation file)",
    re.IGNORECASE,
)
SOURCE_EXCERPT_PATTERN = re.compile(r"(?:```|diff --git|@@ -\d|<pre\b)", re.IGNORECASE)


class LearningError(ValueError):
    """A user-fixable learning data error."""


def run(command: list[str], cwd: Path | None = None, env: dict[str, str] | None = None) -> str:
    result = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip()
        raise LearningError(f"{' '.join(command[:3])} failed: {detail}")
    return result.stdout


def is_nonproduction(path: str) -> bool:
    normalized = path.lower().replace("\\", "/")
    parts = [part for part in normalized.split("/") if part]
    name = parts[-1] if parts else normalized
    stem = name.rsplit(".", 1)[0]
    if any(part in DOC_PARTS for part in parts[:-1]):
        return True
    if any(part in TEST_PARTS for part in parts[:-1]):
        return True
    if re.search(r"(?:^|[._-])(?:test|tests|spec|specs)(?:[._-]|$)", name):
        return True
    if stem in DOC_NAMES or name.endswith((".md", ".mdx", ".rst", ".txt")):
        return True
    if name in {"package-lock.json", "yarn.lock", "pnpm-lock.yaml", "cargo.lock"}:
        return True
    return False


def split_diff(diff: str) -> list[dict[str, str]]:
    markers = list(re.finditer(r"(?m)^diff --git a/(.+?) b/(.+?)$", diff))
    blocks: list[dict[str, str]] = []
    for index, marker in enumerate(markers):
        end = markers[index + 1].start() if index + 1 < len(markers) else len(diff)
        blocks.append({"path": marker.group(2), "text": diff[marker.start():end].rstrip() + "\n"})
    return blocks


def production_diff(diff: str) -> str:
    return "".join(block["text"] for block in split_diff(diff) if not is_nonproduction(block["path"]))


def changed_lines(block: str) -> tuple[int, int]:
    additions = 0
    deletions = 0
    for line in block.splitlines():
        if line.startswith("+++") or line.startswith("---"):
            continue
        additions += line.startswith("+")
        deletions += line.startswith("-")
    return additions, deletions


def first_changed_line(block: str) -> int | None:
    current = None
    for line in block.splitlines():
        match = re.match(r"@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@", line)
        if match:
            current = int(match.group(1))
            continue
        if current is None:
            continue
        if line.startswith("+") and not line.startswith("+++"):
            return current
        if not line.startswith("-"):
            current += 1
    return None


def limits_for(file_count: int, changed_line_count: int) -> dict[str, Any]:
    if file_count >= 100 or changed_line_count >= 10000:
        return {"tier": "very-large", "maxStages": 9, "maxQuestions": 27}
    if file_count >= 30 or changed_line_count >= 2000:
        return {"tier": "broad", "maxStages": 6, "maxQuestions": 18}
    return {"tier": "normal", "maxStages": 4, "maxQuestions": 12}


def extract_literal_change(old: str, new: str) -> tuple[str, str] | None:
    literal = re.compile(r"(?P<quote>['\"])(?P<value>(?:\\.|(?!\1).)*)(?P=quote)")
    old_matches = list(literal.finditer(old))
    new_matches = list(literal.finditer(new))
    if len(old_matches) != len(new_matches):
        return None
    changed = []
    for old_match, new_match in zip(old_matches, new_matches):
        if old_match.group("value") != new_match.group("value"):
            changed.append((old_match, new_match))
    if len(changed) != 1:
        return None
    old_match, new_match = changed[0]
    old_shape = old[:old_match.start()] + "<literal>" + old[old_match.end():]
    new_shape = new[:new_match.start()] + "<literal>" + new[new_match.end():]
    if old_shape != new_shape or not PRESENTATION_PATTERN.search(old_shape):
        return None
    return old_match.group("value"), new_match.group("value")


def presentation_skip(diff: str) -> bool:
    blocks = [block for block in split_diff(diff) if not is_nonproduction(block["path"])]
    if not 1 <= len(blocks) <= 3:
        return False
    total = sum(sum(changed_lines(block["text"])) for block in blocks)
    if total > 12:
        return False
    replacements: list[tuple[str, str]] = []
    for block in blocks:
        hunks = re.split(r"(?m)(?=^@@ )", block["text"])
        hunks = [hunk for hunk in hunks if hunk.startswith("@@ ")]
        if not hunks:
            return False
        for hunk in hunks:
            removed = [line[1:] for line in hunk.splitlines() if line.startswith("-") and not line.startswith("---")]
            added = [line[1:] for line in hunk.splitlines() if line.startswith("+") and not line.startswith("+++")]
            if len(removed) != 1 or len(added) != 1:
                return False
            replacement = extract_literal_change(removed[0], added[0])
            if replacement is None:
                return False
            replacements.append(replacement)
    return bool(replacements) and len(set(replacements)) == 1


def github_source_url(host: str, owner: str, repo: str, revision: str, path: str, line: int | None) -> str:
    encoded_path = "/".join(quote(part) for part in path.split("/"))
    url = f"https://{host}/{owner}/{repo}/blob/{revision}/{encoded_path}"
    return f"{url}#L{line}" if line else url


def local_source_url(root: Path, path: str, line: int | None) -> str:
    url = (root / path).resolve().as_uri()
    return f"{url}#L{line}" if line else url


def source_files(diff: str, mode: str, identity: dict[str, Any], revision: str) -> list[dict[str, Any]]:
    files = []
    for block in split_diff(diff):
        path = block["path"]
        additions, deletions = changed_lines(block["text"])
        line = first_changed_line(block["text"])
        if mode == "github":
            url = github_source_url(identity["host"], identity["owner"], identity["repo"], revision, path, line)
        else:
            url = local_source_url(Path(identity["root"]), path, line)
        files.append({
            "path": path,
            "kind": "support" if is_nonproduction(path) else "production",
            "additions": additions,
            "deletions": deletions,
            "url": url,
        })
    return files


def context_from_raw(
    *,
    mode: str,
    identity: dict[str, Any],
    title: str,
    description: str,
    commits: list[dict[str, str]],
    issues: list[dict[str, Any]],
    diff: str,
    revision: str,
    source_url: str,
) -> dict[str, Any]:
    files = source_files(diff, mode, identity, revision)
    prod_files = [item for item in files if item["kind"] == "production"]
    prod_lines = sum(item["additions"] + item["deletions"] for item in prod_files)
    eligibility = (
        {"decision": "skip", "reason": SKIP_REASON}
        if presentation_skip(diff)
        else {"decision": "required"}
    )
    return {
        "version": 1,
        "source": {
            "mode": mode,
            "identity": identity,
            "title": title,
            "description": description,
            "url": source_url,
            "revision": revision,
            "commits": commits,
            "issues": issues,
            "files": files,
            "stats": {"productionFiles": len(prod_files), "productionChangedLines": prod_lines},
            "limits": limits_for(len(prod_files), prod_lines),
        },
        "eligibility": eligibility,
        "productionDiff": production_diff(diff),
    }


def canonicalize(context: dict[str, Any], candidate: dict[str, Any] | None) -> dict[str, Any]:
    source = copy.deepcopy(context["source"])
    if context["eligibility"]["decision"] == "skip":
        if candidate is not None:
            raise LearningError("candidate must be omitted for a deterministic skip")
        return {
            "version": 1,
            "source": source,
            "skip": {
                "reason": SKIP_REASON,
                "message": "Learning path skipped: this change only repeats the same presentation-text update.",
            },
        }
    if not isinstance(candidate, dict):
        raise LearningError("candidate JSON is required for this change")
    notices = copy.deepcopy(candidate.get("coverageNotices", []))
    stages = copy.deepcopy(candidate.get("stages", []))
    file_map = {item["path"]: item for item in source["files"] if item["kind"] == "production"}
    answer_map: dict[str, str] = {}
    canonical_stages = []
    for stage_index, stage in enumerate(stages, 1):
        stage_id = f"stage-{stage_index:02d}"
        objectives = stage.get("objectives", [])
        canonical_objectives = [
            {"id": f"{stage_id}-objective-{index:02d}", "text": text}
            for index, text in enumerate(objectives, 1)
        ]
        canonical_questions = []
        for question_index, question in enumerate(stage.get("questions", []), 1):
            question_id = f"{stage_id}-question-{question_index:02d}"
            options = []
            for option_index, option in enumerate(question.get("options", [])):
                option_id = f"{question_id}-option-{chr(ord('a') + option_index)}"
                options.append({"id": option_id, "text": option.get("text"), "feedback": option.get("feedback")})
            correct_index = question.get("correctOption")
            correct_id = options[correct_index]["id"] if isinstance(correct_index, int) and 0 <= correct_index < len(options) else "invalid"
            answer_map[question_id] = correct_id
            paths = question.get("sourcePaths", [])
            if not isinstance(paths, list):
                raise LearningError(f"{question_id}.sourcePaths must be an array")
            unknown_paths = [path for path in paths if path not in file_map]
            if unknown_paths:
                raise LearningError(f"{question_id} has unknown production source paths: {', '.join(unknown_paths)}")
            sources = [copy.deepcopy(file_map[path]) for path in paths]
            objective_index = question.get("objective")
            objective_id = (
                canonical_objectives[objective_index]["id"]
                if isinstance(objective_index, int) and 0 <= objective_index < len(canonical_objectives)
                else "invalid"
            )
            canonical_questions.append({
                "id": question_id,
                "objectiveId": objective_id,
                "intent": question.get("intent"),
                "prompt": question.get("prompt"),
                "options": options,
                "correctOptionId": correct_id,
                "expectedAnswer": question.get("expectedAnswer"),
                "explanation": question.get("explanation"),
                "sources": sources,
            })
        canonical_stages.append({
            "id": stage_id,
            "kind": stage.get("kind"),
            "title": stage.get("title"),
            "objectives": canonical_objectives,
            "questions": canonical_questions,
        })
    return {
        "version": 1,
        "source": source,
        "coverageNotices": notices,
        "stages": canonical_stages,
        "answerMap": answer_map,
    }


def _need(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def validate_learning(data: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["root must be an object"]
    _need(data.get("version") == 1, "version must be 1", errors)
    source = data.get("source")
    _need(isinstance(source, dict), "source must be an object", errors)
    if not isinstance(source, dict):
        return errors
    required_source = {"mode", "identity", "title", "description", "url", "revision", "commits", "issues", "files", "stats", "limits"}
    _need(required_source <= set(source), "source is missing required fields", errors)
    _need(source.get("mode") in {"github", "local"}, "source.mode must be github or local", errors)
    revision = source.get("revision")
    _need(isinstance(revision, str) and bool(revision), "source.revision must be non-empty", errors)
    if "skip" in data:
        _need(set(data) == {"version", "source", "skip"}, "skip output has extra fields", errors)
        skip = data.get("skip")
        _need(isinstance(skip, dict) and skip.get("reason") == SKIP_REASON, "skip reason is invalid", errors)
        return errors
    files = source.get("files")
    _need(isinstance(files, list), "source.files must be an array", errors)
    limits = source.get("limits")
    _need(isinstance(limits, dict), "source.limits must be an object", errors)
    if not isinstance(limits, dict):
        limits = {}
    stages = data.get("stages")
    notices = data.get("coverageNotices")
    answer_map = data.get("answerMap")
    _need(isinstance(stages, list) and bool(stages), "stages must be a non-empty array", errors)
    _need(isinstance(notices, list), "coverageNotices must be an array", errors)
    _need(isinstance(answer_map, dict), "answerMap must be an object", errors)
    if not isinstance(stages, list) or not isinstance(notices, list):
        return errors
    notice_kinds = []
    for index, notice in enumerate(notices):
        _need(isinstance(notice, dict) and set(notice) == {"kind"}, f"coverageNotices[{index}] must contain only kind", errors)
        if isinstance(notice, dict):
            notice_kinds.append(notice.get("kind"))
    _need(len(notice_kinds) == len(set(notice_kinds)), "coverage notices must be unique", errors)
    _need(set(notice_kinds) <= {"problem", "impact"}, "coverage notice kind is invalid", errors)
    _need(len(stages) <= limits.get("maxStages", 0), "stage count exceeds source limit", errors)
    kinds = [stage.get("kind") if isinstance(stage, dict) else None for stage in stages]
    _need(kinds.count("problem") + notice_kinds.count("problem") == 1, "require one Problem stage or notice", errors)
    _need(kinds.count("impact") + notice_kinds.count("impact") == 1, "require one Impact stage or notice", errors)
    if "problem" in kinds:
        _need(kinds[0] == "problem", "Problem stage must be first", errors)
    if "impact" in kinds:
        _need(kinds[-1] == "impact", "Impact stage must be last", errors)
    _need(all(kind in {"problem", "concept", "impact"} for kind in kinds), "stage kind is invalid", errors)
    question_count = 0
    all_ids: list[str] = []
    correct_positions: list[int] = []
    source_paths = {
        item.get("path")
        for item in files or []
        if isinstance(item, dict) and item.get("kind") == "production"
    }
    for stage_index, stage in enumerate(stages):
        prefix = f"stages[{stage_index}]"
        if not isinstance(stage, dict):
            errors.append(f"{prefix} must be an object")
            continue
        _need(set(stage) == {"id", "kind", "title", "objectives", "questions"}, f"{prefix} fields are invalid", errors)
        _need(stage.get("id") == f"stage-{stage_index + 1:02d}", f"{prefix}.id is not canonical", errors)
        _need(isinstance(stage.get("title"), str) and bool(stage.get("title", "").strip()), f"{prefix}.title is required", errors)
        objectives = stage.get("objectives")
        questions = stage.get("questions")
        if not isinstance(objectives, list) or not isinstance(questions, list):
            errors.append(f"{prefix} objectives and questions must be arrays")
            continue
        _need(2 <= len(objectives) <= 5, f"{prefix} must have 2-5 objectives", errors)
        _need(len(objectives) == len(questions), f"{prefix} needs one question per objective", errors)
        objective_ids = []
        for objective_index, objective in enumerate(objectives):
            objective_prefix = f"{prefix}.objectives[{objective_index}]"
            expected_id = f"stage-{stage_index + 1:02d}-objective-{objective_index + 1:02d}"
            _need(isinstance(objective, dict) and set(objective) == {"id", "text"}, f"{objective_prefix} fields are invalid", errors)
            if isinstance(objective, dict):
                objective_ids.append(objective.get("id"))
                _need(objective.get("id") == expected_id, f"{objective_prefix}.id is not canonical", errors)
                _need(isinstance(objective.get("text"), str) and bool(objective.get("text", "").strip()), f"{objective_prefix}.text is required", errors)
        used_objectives = []
        intents = []
        for question_index, question in enumerate(questions):
            question_count += 1
            question_prefix = f"{prefix}.questions[{question_index}]"
            if not isinstance(question, dict):
                errors.append(f"{question_prefix} must be an object")
                continue
            expected_qid = f"stage-{stage_index + 1:02d}-question-{question_index + 1:02d}"
            expected_fields = {"id", "objectiveId", "intent", "prompt", "options", "correctOptionId", "expectedAnswer", "sources"}
            _need(set(question) in (expected_fields, expected_fields | {"explanation"}), f"{question_prefix} fields are invalid", errors)
            if "explanation" in question:
                explanation = question["explanation"]
                explanation_prefix = f"{question_prefix}.explanation"
                _need(isinstance(explanation, dict) and set(explanation) == {"why", "flow", "example", "boundary"}, f"{explanation_prefix} fields are invalid", errors)
                if isinstance(explanation, dict):
                    flow = explanation.get("flow")
                    _need(isinstance(flow, list) and len(flow) >= 2, f"{explanation_prefix}.flow needs at least two steps", errors)
                    texts = [explanation.get(field) for field in ("why", "example", "boundary")]
                    if isinstance(flow, list):
                        texts.extend(flow)
                    for text in texts:
                        _need(isinstance(text, str) and bool(text.strip()), f"{explanation_prefix} needs non-empty text", errors)
                        if isinstance(text, str):
                            _need(not SOURCE_EXCERPT_PATTERN.search(text), f"{explanation_prefix} contains a source excerpt", errors)
            _need(question.get("id") == expected_qid, f"{question_prefix}.id is not canonical", errors)
            all_ids.append(question.get("id"))
            used_objectives.append(question.get("objectiveId"))
            intent = question.get("intent")
            intents.append(intent)
            _need(intent in {"concept", "transfer", "synthesis"}, f"{question_prefix}.intent is invalid", errors)
            for field in ("prompt", "expectedAnswer"):
                text = question.get(field)
                _need(isinstance(text, str) and bool(text.strip()), f"{question_prefix}.{field} is required", errors)
                if isinstance(text, str):
                    _need(not SOURCE_EXCERPT_PATTERN.search(text), f"{question_prefix}.{field} contains a source excerpt", errors)
                    if field == "prompt":
                        _need(not TRIVIA_PATTERN.search(text), f"{question_prefix}.prompt asks trivia", errors)
            options = question.get("options")
            if not isinstance(options, list):
                errors.append(f"{question_prefix}.options must be an array")
                continue
            _need(3 <= len(options) <= 4, f"{question_prefix} must have 3-4 options", errors)
            option_ids = []
            option_texts = []
            for option_index, option in enumerate(options):
                option_prefix = f"{question_prefix}.options[{option_index}]"
                expected_oid = f"{expected_qid}-option-{chr(ord('a') + option_index)}"
                _need(isinstance(option, dict) and set(option) == {"id", "text", "feedback"}, f"{option_prefix} fields are invalid", errors)
                if isinstance(option, dict):
                    option_ids.append(option.get("id"))
                    option_texts.append(option.get("text"))
                    _need(option.get("id") == expected_oid, f"{option_prefix}.id is not canonical", errors)
                    for field in ("text", "feedback"):
                        text = option.get(field)
                        _need(isinstance(text, str) and bool(text.strip()), f"{option_prefix}.{field} is required", errors)
                        if isinstance(text, str):
                            _need(not SOURCE_EXCERPT_PATTERN.search(text), f"{option_prefix}.{field} contains a source excerpt", errors)
            _need(len(option_texts) == len(set(option_texts)), f"{question_prefix} option texts must be unique", errors)
            correct_id = question.get("correctOptionId")
            _need(correct_id in option_ids, f"{question_prefix}.correctOptionId is invalid", errors)
            if correct_id in option_ids:
                correct_positions.append(option_ids.index(correct_id))
            _need(isinstance(answer_map, dict) and answer_map.get(expected_qid) == correct_id, f"answerMap mismatch for {expected_qid}", errors)
            sources = question.get("sources")
            _need(isinstance(sources, list), f"{question_prefix}.sources must be an array", errors)
            if isinstance(sources, list):
                _need(bool(sources), f"{question_prefix} needs at least one source link", errors)
                linked_paths = []
                for source_index, item in enumerate(sources):
                    item_path = item.get("path") if isinstance(item, dict) else None
                    valid_source = (
                        isinstance(item_path, str)
                        and item_path in source_paths
                        and isinstance(item.get("url"), str)
                        and bool(item.get("url"))
                    )
                    _need(valid_source, f"{question_prefix}.sources[{source_index}] is invalid", errors)
                    if isinstance(item_path, str):
                        linked_paths.append(item_path)
                _need(len(linked_paths) == len(set(linked_paths)), f"{question_prefix} source links must be unique", errors)
        _need(sorted(used_objectives) == sorted(objective_ids), f"{prefix} must map each objective once", errors)
        if len(questions) >= 4:
            _need("transfer" in intents, f"{prefix} needs a transfer question", errors)
    _need(question_count <= limits.get("maxQuestions", 0), "question count exceeds source limit", errors)
    _need(len(all_ids) == len(set(all_ids)), "question IDs must be unique", errors)
    if question_count >= 4:
        _need(len(set(correct_positions)) >= 2, "correct option positions must vary", errors)
    complex_path = limits.get("tier") != "normal" or kinds.count("concept") > 1
    if complex_path and "problem" in kinds and "impact" in kinds:
        final_questions = stages[-1].get("questions", [])
        _need(bool(final_questions) and final_questions[-1].get("intent") == "synthesis", "complex path must end with synthesis", errors)
        synthesis_count = sum(
            question.get("intent") == "synthesis"
            for stage in stages
            for question in stage.get("questions", [])
        )
        _need(synthesis_count == 1, "complex path needs exactly one synthesis question", errors)
    return errors


def atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(data, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def context_revision(head: str, diff: str) -> str:
    digest = hashlib.sha256(diff.encode("utf-8")).hexdigest()[:16]
    return f"{head}-{digest}"
