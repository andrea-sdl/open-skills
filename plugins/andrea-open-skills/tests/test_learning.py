#!/usr/bin/env python3
"""Deterministic tests for the standalone PR Learning Path skill."""

from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "pr-learning-path"
SCRIPTS = SKILL / "scripts"
sys.path.insert(0, str(SCRIPTS))

from learning_core import (  # noqa: E402
    LearningError,
    canonicalize,
    context_from_raw,
    is_nonproduction,
    limits_for,
    presentation_skip,
    validate_learning,
)
from gather_context import parse_pr  # noqa: E402
from gather_context import untracked_diff  # noqa: E402


DIFF = """\
diff --git a/src/policy.py b/src/policy.py
index 1111111..2222222 100644
--- a/src/policy.py
+++ b/src/policy.py
@@ -10,3 +10,5 @@ def authorize(request):
-    return request.user.is_admin
+    site = resolve_site(request.site_id)
+    return request.user.can_access(site)
+

diff --git a/tests/test_policy.py b/tests/test_policy.py
index 3333333..4444444 100644
--- a/tests/test_policy.py
+++ b/tests/test_policy.py
@@ -1 +1 @@
-assert authorize(admin_request)
+assert authorize(site_request)
"""

PRESENTATION_DIFF = """\
diff --git a/src/one.jsx b/src/one.jsx
index 1..2 100644
--- a/src/one.jsx
+++ b/src/one.jsx
@@ -1 +1 @@
-<Button label={ __( 'Add track' ) } />
+<Button label={ __( 'Add' ) } />
diff --git a/src/two.jsx b/src/two.jsx
index 1..2 100644
--- a/src/two.jsx
+++ b/src/two.jsx
@@ -1 +1 @@
-<Toolbar title={ __( 'Add track' ) } />
+<Toolbar title={ __( 'Add' ) } />
"""


def make_context(mode="github", file_count=None, changed_lines=None):
    if mode == "github":
        identity = {"host": "github.com", "owner": "acme", "repo": "policy", "number": 7}
        source_url = "https://github.com/acme/policy/pull/7"
    else:
        identity = {"root": "/tmp/acme-policy", "selector": "HEAD~1..HEAD"}
        source_url = "file:///tmp/acme-policy"
    context = context_from_raw(
        mode=mode,
        identity=identity,
        title="Scope access to one site",
        description="Global admin access leaks across site boundaries.",
        commits=[{"sha": "abc", "title": "Scope access", "body": ""}],
        issues=[],
        diff=DIFF,
        revision="abcdef1234567890",
        source_url=source_url,
    )
    if file_count is not None and changed_lines is not None:
        context["source"]["stats"] = {"productionFiles": file_count, "productionChangedLines": changed_lines}
        context["source"]["limits"] = limits_for(file_count, changed_lines)
    return context


def question(objective, correct, intent="concept", source_paths=None, label="access"):
    options = [
        {"text": f"Use the request-wide {label} rule", "feedback": "This keeps the old broad boundary."},
        {"text": f"Resolve the site before checking {label}", "feedback": "This checks the same object the request will use."},
        {"text": f"Trust the display name for {label}", "feedback": "Display text does not prove access."},
    ]
    return {
        "objective": objective,
        "intent": intent,
        "prompt": f"Which policy keeps {label} tied to the requested site?",
        "options": options,
        "correctOption": correct,
        "expectedAnswer": "Resolve the requested site and check access to that site.",
        "explanation": {
            "why": "The changed policy checks access to the resolved site, not global admin status.",
            "flow": [
                "The request supplies a site identifier.",
                "The policy resolves that identifier to a site.",
                "The policy returns the user's access decision for that site.",
            ],
            "example": "Illustrative case: a global admin requests site A but has no access to A. The old check accepts the admin; the new check returns false.",
            "boundary": "Global admin status alone no longer grants access. The diff does not show how a failed site lookup behaves.",
        },
        "sourcePaths": source_paths if source_paths is not None else ["src/policy.py"],
    }


def stage(kind, title, count=2, synthesis_last=False):
    objectives = [f"Understand {title.lower()} point {index + 1}" for index in range(count)]
    questions = []
    for index in range(count):
        intent = "synthesis" if synthesis_last and index == count - 1 else ("transfer" if count >= 4 and index == 1 else "concept")
        questions.append(question(index, index % 2, intent=intent, label=f"{kind}-{index + 1}"))
    return {"kind": kind, "title": title, "objectives": objectives, "questions": questions}


def normal_candidate():
    return {
        "coverageNotices": [],
        "stages": [
            stage("problem", "Why access leaked"),
            stage("concept", "Scoped access flow"),
            stage("impact", "Consumer behavior"),
        ],
    }


class LearningTests(unittest.TestCase):
    def test_explanation_survives_apply_and_requires_a_complete_map(self):
        candidate = normal_candidate()
        learning = canonicalize(make_context(), candidate)
        self.assertEqual([], validate_learning(learning))
        self.assertEqual(candidate["stages"][0]["questions"][0]["explanation"], learning["stages"][0]["questions"][0]["explanation"])
        for invalid in (None, {}, {"why": "Right"},
                        {"why": "Reason", "flow": ["One step"], "example": "Case", "boundary": "Limit"},
                        {"why": "Reason", "flow": ["Input", " "], "example": "Case", "boundary": "Limit"},
                        {"why": "Reason", "flow": ["Input", "Output"], "example": "", "boundary": "Limit"},
                        {"why": "Reason", "flow": ["Input", "Output"], "example": "```python\nreturn True\n```", "boundary": "Limit"}):
            with self.subTest(explanation=invalid):
                broken = copy.deepcopy(candidate)
                broken["stages"][0]["questions"][0]["explanation"] = invalid
                self.assertTrue(validate_learning(canonicalize(make_context(), broken)))
        del candidate["stages"][0]["questions"][0]["explanation"]
        self.assertTrue(validate_learning(canonicalize(make_context(), candidate)))

    def test_older_final_artifacts_without_explanations_still_validate(self):
        learning = canonicalize(make_context(), normal_candidate())
        for section in learning["stages"]:
            for item in section["questions"]:
                del item["explanation"]
        self.assertEqual([], validate_learning(learning))

    def test_github_input_forms(self):
        self.assertEqual(
            {"host": "github.com", "owner": "acme", "repo": "policy", "number": 7},
            parse_pr("acme/policy#7"),
        )
        self.assertEqual(
            {"host": "github.example.test", "owner": "acme", "repo": "policy", "number": 7},
            parse_pr("https://github.example.test/acme/policy/pull/7"),
        )

    def test_local_mode_collects_untracked_changed_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "--quiet"], cwd=root, check=True)
            (root / "new.py").write_text("print('new')\n", encoding="utf-8")
            diff = untracked_diff(root, ["new.py"])
            self.assertIn("diff --git a/new.py b/new.py", diff)
            self.assertIn("+print('new')", diff)

    def test_support_files_do_not_enter_the_production_diff(self):
        self.assertTrue(is_nonproduction("docs/graphql/schema.graphql"))
        self.assertTrue(is_nonproduction("src/example.test.ts"))
        self.assertFalse(is_nonproduction("src/schemas/runtime.graphql"))

    def test_schema_ids_answer_maps_and_stage_order(self):
        learning = canonicalize(make_context(), normal_candidate())
        self.assertEqual([], validate_learning(learning))
        self.assertEqual("stage-01", learning["stages"][0]["id"])
        question_item = learning["stages"][1]["questions"][1]
        self.assertEqual("stage-02-question-02", question_item["id"])
        self.assertEqual(question_item["correctOptionId"], learning["answerMap"][question_item["id"]])
        broken = copy.deepcopy(learning)
        broken["stages"][0], broken["stages"][1] = broken["stages"][1], broken["stages"][0]
        self.assertTrue(any("Problem stage must be first" in error for error in validate_learning(broken)))

    def test_limit_tiers_and_maximum_nine_sections(self):
        self.assertEqual({"tier": "normal", "maxStages": 4, "maxQuestions": 12}, limits_for(29, 1999))
        self.assertEqual({"tier": "broad", "maxStages": 6, "maxQuestions": 18}, limits_for(30, 1999))
        self.assertEqual({"tier": "broad", "maxStages": 6, "maxQuestions": 18}, limits_for(1, 2000))
        self.assertEqual({"tier": "very-large", "maxStages": 9, "maxQuestions": 27}, limits_for(100, 1))
        candidate = {"coverageNotices": [], "stages": [stage("problem", "Problem")]}
        candidate["stages"].extend(stage("concept", f"Concept {index}") for index in range(1, 8))
        candidate["stages"].append(stage("impact", "Impact", synthesis_last=True))
        learning = canonicalize(make_context(file_count=100, changed_lines=10001), candidate)
        self.assertEqual([], validate_learning(learning))
        self.assertEqual(9, len(learning["stages"]))
        candidate["stages"].insert(-1, stage("concept", "Too much"))
        errors = validate_learning(canonicalize(make_context(file_count=100, changed_lines=10001), candidate))
        self.assertIn("stage count exceeds source limit", errors)

    def test_question_ceiling_without_padding(self):
        candidate = normal_candidate()
        candidate["stages"].append(stage("concept", "Extra", count=5))
        candidate["stages"].append(stage("concept", "One more", count=2))
        learning = canonicalize(make_context(), candidate)
        self.assertTrue(any("stage count exceeds" in error for error in validate_learning(learning)))
        candidate = {"coverageNotices": [], "stages": [stage("problem", "Problem", 5), stage("concept", "Flow", 5), stage("impact", "Impact", 5)]}
        learning = canonicalize(make_context(), candidate)
        self.assertIn("question count exceeds source limit", validate_learning(learning))

    def test_problem_and_impact_notices_replace_stages(self):
        candidate = {
            "coverageNotices": [{"kind": "problem"}, {"kind": "impact"}],
            "stages": [stage("concept", "Known flow")],
        }
        self.assertEqual([], validate_learning(canonicalize(make_context(), candidate)))
        candidate["stages"].insert(0, stage("problem", "Duplicate problem"))
        self.assertIn("require one Problem stage or notice", validate_learning(canonicalize(make_context(), candidate)))

    def test_source_links_are_exact_head_and_local(self):
        github = canonicalize(make_context("github"), normal_candidate())
        github_url = github["stages"][0]["questions"][0]["sources"][0]["url"]
        self.assertIn("/blob/abcdef1234567890/src/policy.py#L10", github_url)
        local = canonicalize(make_context("local"), normal_candidate())
        local_url = local["stages"][0]["questions"][0]["sources"][0]["url"]
        self.assertTrue(local_url.endswith("/tmp/acme-policy/src/policy.py#L10"))
        broken = normal_candidate()
        broken["stages"][0]["questions"][0]["sourcePaths"] = ["tests/test_policy.py"]
        with self.assertRaises(LearningError):
            canonicalize(make_context(), broken)

    def test_deterministic_presentation_skip(self):
        self.assertTrue(presentation_skip(PRESENTATION_DIFF))
        context = context_from_raw(
            mode="github",
            identity={"host": "github.com", "owner": "acme", "repo": "ui", "number": 8},
            title="Shorter label",
            description="",
            commits=[], issues=[], diff=PRESENTATION_DIFF,
            revision="123", source_url="https://github.com/acme/ui/pull/8",
        )
        learning = canonicalize(context, None)
        self.assertEqual("repeated-presentation-literal-change", learning["skip"]["reason"])
        self.assertEqual([], validate_learning(learning))
        changed_behavior = PRESENTATION_DIFF.replace("<Toolbar title=", "<Toolbar disabled title=", 1)
        self.assertFalse(presentation_skip(changed_behavior))

    def test_invalid_schema_answer_and_excerpt(self):
        learning = canonicalize(make_context(), normal_candidate())
        learning["answerMap"]["stage-01-question-01"] = "wrong"
        learning["stages"][0]["questions"][0]["prompt"] = "Which exact line in ```code``` changed?"
        errors = validate_learning(learning)
        self.assertTrue(any("answerMap mismatch" in error for error in errors))
        self.assertTrue(any("source excerpt" in error for error in errors))
        self.assertTrue(any("asks trivia" in error for error in errors))

    def test_each_question_requires_a_source_link(self):
        candidate = normal_candidate()
        candidate["stages"][0]["questions"][0]["sourcePaths"] = []
        learning = canonicalize(make_context(), candidate)
        self.assertIn(
            "stages[0].questions[0] needs at least one source link",
            validate_learning(learning),
        )

    def test_transactional_apply_preserves_existing_output_on_error(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            context_path = root / "context.json"
            candidate_path = root / "candidate.json"
            output_path = root / "learning.json"
            context_path.write_text(json.dumps(make_context()), encoding="utf-8")
            candidate = normal_candidate()
            candidate["stages"][0]["questions"][0]["correctOption"] = 99
            candidate_path.write_text(json.dumps(candidate), encoding="utf-8")
            output_path.write_text("keep-me", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(SCRIPTS / "apply_learning.py"), str(context_path), str(candidate_path), "--output", str(output_path)],
                text=True, capture_output=True, check=False,
            )
            self.assertNotEqual(0, result.returncode)
            self.assertEqual("keep-me", output_path.read_text(encoding="utf-8"))

    def test_html_behavior_persistence_and_post_answer_links(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            learning_path = root / "learning.json"
            html_path = root / "learning.html"
            learning_path.write_text(json.dumps(canonicalize(make_context(), normal_candidate())), encoding="utf-8")
            build = subprocess.run(
                [sys.executable, str(SCRIPTS / "build_html.py"), str(learning_path), "--output", str(html_path)],
                text=True, capture_output=True, check=False,
            )
            self.assertEqual(0, build.returncode, build.stderr)
            verify = subprocess.run(
                [sys.executable, str(SCRIPTS / "verify_html.py"), str(html_path)],
                text=True, capture_output=True, check=False,
            )
            self.assertEqual(0, verify.returncode, verify.stderr)
            html = html_path.read_text(encoding="utf-8")
            self.assertIn("source.revision", html)
            self.assertIn("removeStaleRevisions", html)
            self.assertIn("memoryStore", html)
            self.assertIn("woven-loop-title", html)
            self.assertIn("--background:", html)
            self.assertIn("--primary:", html)
            self.assertIn("--brand-warm:", html)
            self.assertIn("Color theme:", html)
            self.assertIn("source-project", html)
            self.assertIn("overflow-wrap: anywhere", html)
            self.assertNotIn("__BRAND_ICON__", html)
            self.assertIn('selected ? `', html)
            self.assertIn("question.sources.length", html)
            self.assertIn("Review the sources", html)
            self.assertIn('target="_blank" rel="noopener noreferrer"', html)
            self.assertNotRegex(html, r">\s*(Snapshot|Walkthrough|Validate)\s*<")
            if os.environ.get("PR_LEARNING_BROWSER_SMOKE") == "1":
                browser = subprocess.run(
                    [
                        "node",
                        str(ROOT / "evals" / "tests" / "browser-smoke.mjs"),
                        str(html_path),
                        str(root / "browser-smoke.png"),
                    ],
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(0, browser.returncode, browser.stdout + browser.stderr)

    def test_learning_text_can_contain_template_tokens(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            learning_path = root / "learning.json"
            html_path = root / "learning.html"
            learning = canonicalize(make_context(), normal_candidate())
            learning["stages"][0]["questions"][0]["prompt"] = (
                "Why can __BRAND_ICON__ and __LEARNING_DATA__ remain literal learning text?"
            )
            learning_path.write_text(json.dumps(learning), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(SCRIPTS / "build_html.py"), str(learning_path), "--output", str(html_path)],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(0, result.returncode, result.stderr)
            html = html_path.read_text(encoding="utf-8")
            self.assertIn("__BRAND_ICON__", html)
            self.assertIn("__LEARNING_DATA__", html)

    def test_option_positions_retry_and_synthesis_contracts(self):
        learning = canonicalize(make_context(), normal_candidate())
        for stage_item in learning["stages"]:
            for question_item in stage_item["questions"]:
                question_item["correctOptionId"] = question_item["options"][0]["id"]
                learning["answerMap"][question_item["id"]] = question_item["options"][0]["id"]
        self.assertIn("correct option positions must vary", validate_learning(learning))
        broad = normal_candidate()
        broad["stages"][-1]["questions"][-1]["intent"] = "synthesis"
        broad_learning = canonicalize(make_context(file_count=30, changed_lines=10), broad)
        self.assertEqual([], validate_learning(broad_learning))
        broad_learning["stages"][-1]["questions"][-1]["intent"] = "concept"
        self.assertTrue(any("synthesis" in error for error in validate_learning(broad_learning)))


if __name__ == "__main__":
    unittest.main(verbosity=2)
