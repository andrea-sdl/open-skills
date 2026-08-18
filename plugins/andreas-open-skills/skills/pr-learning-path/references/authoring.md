# Learning authoring contract

## Build the brief first

Privately summarize these supported facts before writing questions:

- problem and intent;
- prior behavior and root cause;
- design choices and rejected or weaker alternatives;
- changed control or data flow;
- assumptions, ownership, boundaries, and preserved behavior;
- direct consumers, risks, and downstream impact.

Use PR or issue prose for stated intent and the production diff for behavior.
If they conflict, test the mismatch only when it matters. Do not invent a fact.

## Select sections

- Use Problem first when evidence supports two useful objectives. Otherwise add
  the fixed `problem` notice.
- Add only coherent concept sections. Merge related facts before questions.
- Use Impact last when evidence supports two useful objectives. Otherwise add
  the fixed `impact` notice.
- Normal changes allow up to 4 sections and 12 questions.
- Broad changes allow up to 6 sections and 18 questions.
- Very large changes allow up to 9 sections and 27 questions.
- Use 2–3 questions for most sections. Use 4–5 only for one complex area that
  would become less clear if split. Do not pad.

## Write hard questions

- Map each question to one objective.
- Test a scenario, prediction, tradeoff, consequence, or boundary when useful.
- Use `transfer` for questions that connect two or more facts.
- A section with 4–5 questions needs a transfer question.
- A complex path with valid Problem and Impact sections ends with one
  `synthesis` question. It connects the problem, chosen design, changed flow,
  and downstream effect.
- Vary the correct option position.
- Derive wrong options from old behavior, reversed order or ownership, missed
  invariants, alternate branches, or rejected designs.
- Give each option short feedback that explains the key match or gap.
- Keep expected answers short and specific.
- Add one or more changed production files that directly support each answer.
  Link the files with `sourcePaths`; do not copy or quote their contents.

## Exclude

Do not ask about tests, docs, QA steps, symbols, helper names, file names, exact
lines, JSON fields, numeric limits, or minor implementation details. Do not put
code, diffs, PR prose, issue prose, or source excerpts in a question, option,
answer, or feedback.
