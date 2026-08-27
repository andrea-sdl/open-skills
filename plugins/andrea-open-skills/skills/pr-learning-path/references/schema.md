# Candidate and final schemas

## Candidate JSON

Author this small shape. Scripts add stable IDs, exact source URLs, limits, and
the source revision.

```json
{
  "coverageNotices": [],
  "stages": [
    {
      "kind": "problem",
      "title": "Why this change exists",
      "objectives": ["Explain the prior gap", "Connect the gap to the design"],
      "questions": [
        {
          "objective": 0,
          "intent": "concept",
          "prompt": "What made the old behavior fail in the stated case?",
          "options": [
            {"text": "Supported answer", "feedback": "This matches the old failure path."},
            {"text": "Plausible wrong answer", "feedback": "This misses the ownership boundary."},
            {"text": "Another plausible wrong answer", "feedback": "This reverses the control flow."}
          ],
          "correctOption": 0,
          "expectedAnswer": "A short explanation of the expected answer.",
          "explanation": {
            "why": "Explain how the condition leads to this result.",
            "flow": ["Relevant input and owner", "Decisive check or state change", "Observable result"],
            "example": "Walk a concrete scenario through the supported behavior.",
            "boundary": "Explain the condition or contrast that makes this answer hold."
          },
          "sourcePaths": ["src/example.py"]
        }
      ]
    }
  ]
}
```

- `coverageNotices`: zero to two items with only `{"kind":"problem"}` or
  `{"kind":"impact"}`.
- Stage `kind`: `problem`, `concept`, or `impact`.
- Each stage has 2–5 distinct objectives and the same number of questions.
- `objective`: zero-based index into that stage's objectives. Use each once.
- `intent`: `concept`, `transfer`, or `synthesis`.
- Each question has 3–4 options and one zero-based `correctOption`.
- `explanation`: required for new candidates. Contains non-empty plain-text
  `why`, `example`, and `boundary`, plus a `flow` array of at least two non-empty
  plain-text steps. Follow the authoring contract for evidence grounding.
  Render it inline only after an answer, for both correct and wrong choices.
- `sourcePaths`: one or more relevant changed production file paths that help
  explain the answer. These become exact-head GitHub links or local file
  links. They appear after an answer only. Do not inline source text.

## Final JSON

`apply_learning.py` creates this shape:

- `version`: `1`
- `source`: copied source identity, revision, links, stats, and limits
- either `skip` or both `coverageNotices` and `stages`
- canonical stage, objective, question, and option IDs based on their order
- `correctOptionId` and `answerMap`
- resolved question `sources` with `path` and `url`
- question `explanation`, copied from the candidate; older final version-1
  artifacts without this field remain readable

Do not author final IDs or URLs. The apply step owns them.
