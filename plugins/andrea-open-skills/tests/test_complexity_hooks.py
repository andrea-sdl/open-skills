import argparse
import contextlib
import importlib.util
import io
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


PLUGIN = Path(__file__).parents[1]
SCRIPT = PLUGIN / "skills/complexity-cli/scripts/check_complexity.py"
SPEC = importlib.util.spec_from_file_location("complexity_hooks", SCRIPT)
assert SPEC and SPEC.loader
checker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checker)


class ComplexityHookTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "repo"
        self.root.mkdir()
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        self.environment = patch.dict(os.environ, {
            "COMPLEXITY_STATE_DIR": str(Path(self.temporary.name) / "state")
        })
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.original_cwd = Path.cwd()
        self.addCleanup(os.chdir, self.original_cwd)
        self.args = argparse.Namespace(paths=[], binary=None)
        self.hook = {
            "hook_event_name": "PostToolUse",
            "cwd": str(self.root),
            "session_id": "test-session",
        }
        checker.record_baseline(self.root, "test-session")

    def run_hook(self):
        output = io.StringIO()
        with patch.object(checker.sys, "stdin", io.StringIO(json.dumps(self.hook))):
            with contextlib.redirect_stdout(output):
                self.assertEqual(checker.run_advice_hook(self.args), 0)
        result = json.loads(output.getvalue())
        self.assertNotIn("decision", result)
        self.assertNotIn("continue", result)
        self.assertNotIn("systemMessage", result)
        return result

    def test_findings_guide_without_blocking_or_repeating(self):
        source = self.root / "app.py"
        source.write_text("x = 1\n")
        report = "FAIL complexity: 1 of 1 functions exceed policy.\nCHECKED app.py\nFAIL app.py:1 work score=20"
        with patch.object(checker, "check", return_value=("FAIL", 1, report)) as check:
            result = self.run_hook()["hookSpecificOutput"]
            self.assertEqual(result["hookEventName"], "PostToolUse")
            self.assertIn("Preserve behavior", result["additionalContext"])
            self.assertIn("app.py:1", result["additionalContext"])
            self.assertEqual(self.run_hook(), {})
            check.assert_called_once()
            source.write_text("x = 2\n")
            self.assertEqual(self.run_hook(), {})
            self.assertEqual(check.call_count, 2)
            check.return_value = ("FAIL", 1, report.replace("score=20", "score=18"))
            source.write_text("x = 3\n")
            self.assertIn("score=18", self.run_hook()["hookSpecificOutput"]["additionalContext"])

    def test_unavailable_check_does_not_stop_work_or_claim_a_pass(self):
        (self.root / "app.py").write_text("x = 1\n")
        with patch.object(checker, "check", side_effect=RuntimeError("binary missing")) as check:
            advice = self.run_hook()["hookSpecificOutput"]["additionalContext"]
            self.assertIn("check unavailable", advice)
            self.assertIn("Continue the task", advice)
            self.assertNotIn("PASS", advice)
            self.assertEqual(self.run_hook(), {})
            check.assert_called_once()

    def test_existing_dirty_files_and_unsupported_edits_stay_silent(self):
        (self.root / "existing.py").write_text("x = 1\n")
        checker.record_baseline(self.root, "test-session")
        (self.root / "notes.md").write_text("notes\n")
        with patch.object(checker, "check") as check:
            self.assertEqual(self.run_hook(), {})
            check.assert_not_called()

    def test_new_prompt_resets_advice_and_preserves_task_scope(self):
        source = self.root / "app.py"
        source.write_text("x = 1\n")
        report = "REVISE complexity\nCHECKED app.py\nREVISE app.py:1 work score=11"
        with patch.object(checker, "check", return_value=("REVISE", 1, report)):
            self.assertIn("hookSpecificOutput", self.run_hook())
            checker.record_baseline(self.root, "test-session")
            self.assertEqual(self.run_hook(), {})
            source.write_text("x = 2\n")
            self.assertIn("hookSpecificOutput", self.run_hook())

    def test_pass_stays_silent(self):
        (self.root / "app.py").write_text("x = 1\n")
        with patch.object(checker, "check", return_value=("PASS", 0, "PASS complexity")):
            self.assertEqual(self.run_hook(), {})

    def test_old_stop_hook_is_silent(self):
        self.hook["hook_event_name"] = "Stop"
        with patch.object(checker, "check") as check:
            self.assertEqual(self.run_hook(), {})
            check.assert_not_called()

    def test_invalid_input_does_not_block(self):
        self.hook = []
        self.assertIn("check unavailable", self.run_hook()["hookSpecificOutput"]["additionalContext"])

    def test_corrupt_advice_cache_does_not_prevent_check(self):
        (self.root / "app.py").write_text("x = 1\n")
        checker.advice_state_file(self.root, "test-session").write_text("broken")
        with patch.object(checker, "check", return_value=("PASS", 0, "PASS")) as check:
            self.assertEqual(self.run_hook(), {})
            check.assert_called_once()

    def test_direct_cli_preserves_strict_exit_codes(self):
        for code in (0, 1, 2):
            with self.subTest(code=code):
                args = argparse.Namespace(hook=False, baseline_hook=False)
                with patch.object(checker, "parse_args", return_value=args):
                    with patch.object(checker, "checked_result", return_value=(code, "report")):
                        with contextlib.redirect_stdout(io.StringIO()):
                            self.assertEqual(checker.main(), code)

    def test_all_plugin_configs_use_advisory_hooks(self):
        for path in (PLUGIN / "hooks").glob("*.json"):
            with self.subTest(path=path.name):
                hooks = json.loads(path.read_text())["hooks"]
                self.assertNotIn("Stop", hooks)
                self.assertIn("UserPromptSubmit", hooks)
                self.assertEqual(hooks["PostToolUse"][0]["matcher"], "Bash|Edit|Write|apply_patch")


if __name__ == "__main__":
    unittest.main()
