"""Regression tests for the same candidate gate used by provider evals."""

import copy
import json
import sys
import unittest
from pathlib import Path

from test_learning import normal_candidate


EVALS = Path(__file__).resolve().parents[1] / "evals"
sys.path.insert(0, str(EVALS))
from assertions import validate_candidate  # noqa: E402


class EvalAssertionTests(unittest.TestCase):
    def setUp(self):
        fixture = json.loads((EVALS / "fixtures" / "auth-boundary.json").read_text())
        self.context = {"vars": {"fixture": fixture}}
        self.candidate = normal_candidate()
        for stage in self.candidate["stages"]:
            for question in stage["questions"]:
                question["sourcePaths"] = ["src/reports.py", "src/permissions.py"]

    def grade(self, candidate):
        return validate_candidate(json.dumps(candidate), self.context)

    def test_complete_explanations_pass_the_structural_gate(self):
        # Content truth belongs to the separate grounding rubric, not this gate.
        self.assertTrue(self.grade(self.candidate)["pass"])

    def test_one_bad_explanation_fails_even_when_all_other_questions_are_valid(self):
        original = self.candidate["stages"][-1]["questions"][-1]["explanation"]
        mutations = [None, {}, "Right"]
        for field in ("why", "flow", "example", "boundary"):
            missing = copy.deepcopy(original)
            del missing[field]
            mutations.append(missing)
            blank = copy.deepcopy(original)
            blank[field] = [] if field == "flow" else " "
            mutations.append(blank)
        mutations.append({**original, "flow": ["Input only"]})
        mutations.append({**original, "flow": ["Input", None]})
        mutations.append({**original, "example": "```python\nreturn True\n```"})
        for explanation in mutations:
            with self.subTest(explanation=explanation):
                candidate = copy.deepcopy(self.candidate)
                candidate["stages"][-1]["questions"][-1]["explanation"] = explanation
                result = self.grade(candidate)
                self.assertFalse(result["pass"])
                self.assertIn("explanation", result["reason"])

    def test_old_right_only_candidate_cannot_use_legacy_final_compatibility(self):
        for stage in self.candidate["stages"]:
            for question in stage["questions"]:
                del question["explanation"]
        self.assertFalse(self.grade(self.candidate)["pass"])

    def test_explanation_cannot_link_unavailable_evidence(self):
        for paths in ([], ["src/not-in-the-diff.py"], ["tests/test_reports.py"]):
            with self.subTest(paths=paths):
                self.candidate["stages"][0]["questions"][0]["sourcePaths"] = paths
                self.assertFalse(self.grade(self.candidate)["pass"])

    def test_non_json_provider_output_fails_closed(self):
        self.assertFalse(validate_candidate("Right", self.context)["pass"])


if __name__ == "__main__":
    unittest.main()
