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

## Explain the answer after grading

Give every question an `explanation`, shown inline after any answer, including
a correct one. Keep option feedback short; use this shared explanation to build
the learner's mental model, not to repeat the expected answer.

- `why`: connect the question's condition to the decision and its result.
- `flow`: ordered steps from the relevant input through the code's decisions
  or state changes to the observable result. Use actual roles and ownership,
  not a generic sequence such as "validate, process, return".
- `example`: walk one concrete input or scenario through that flow. Label
  invented sample values as illustrative; derive the result from production
  evidence. Do not present a worked example as a test you ran.
- `boundary`: explain the decisive condition, preserved behavior, or contrast
  with a plausible wrong answer. State evidence limits when they matter.

Ground behavior in the gathered production diff and intent in PR or issue
context. The question's `sourcePaths` must cover the code claims in its
explanation. Trace each claim back to that evidence before delivery. If the
context does not show a caller, cache, error path, or downstream effect, do not
invent it. Narrow the explanation or state what the source does not establish.
Use plain-language steps and examples, not copied source or PR prose. Keep
details specific to the question; do not paste the same explanation throughout
the path. Scripts check structure and links, not whether these claims are true.

## Exclude

Do not ask about tests, docs, QA steps, symbols, helper names, file names, exact
lines, JSON fields, numeric limits, or minor implementation details. Do not put
code, diffs, PR prose, issue prose, or source excerpts in a question, option,
answer, or feedback.
