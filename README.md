# Open Skills

Open Skills contains installable skills for Claude Code and Codex.
The same source powers both plugin formats.

These skills help you understand a change, measure its complexity, and remove
code that does not earn its place. Use them together for a focused review, or
use one skill when you need a specific check.

## Included skills

### PR Learning Path

PR Learning Path turns a GitHub pull request or local code change into one
self-contained HTML learning page. It asks hard multiple-choice questions
about the problem, prior behavior, design, flow, boundaries, risks, and impact.

It is useful when reading a diff is not enough. The questions test whether you
understand why the change exists, how it works, and what could break. This makes
review preparation and knowledge sharing more active than a written summary.

The page grades each answer at once, explains every option, links to the exact
source revision after an answer, and saves progress in the browser. It does not
need a review product or server at runtime.

Read [the learning-skill goals](docs/learning-skills.md) for the design contract.

### Complexity Evaluator

Complexity Evaluator exposes `$complexity-cli` only when you invoke it. It
checks changed JavaScript, TypeScript, PHP, Rust, and Python before handoff.
On first use, `$setup-complexity-cli` installs the required native executable.
The plugin enables lifecycle hooks that record the task baseline and check
supported code before Codex or Claude Code stops. Platform-specific examples
remain in `plugins/andrea-open-skills/hooks/`.

It is useful before review or handoff because complex code costs more to read,
test, and change. The skill checks only supported changed code, so it keeps the
signal tied to the work in scope.

### Setup Complexity CLI

Setup Complexity CLI installs or updates the pinned native executable used by
Complexity Evaluator. It detects the current platform, downloads the matching
release archive and SHA-256 file, and verifies the archive before installation.

Use it on the first run or after the plugin raises its supported CLI version.
If `$complexity-cli` finds no compatible executable, it routes through setup
before it checks code. Lifecycle hooks block with the same setup instruction;
they never download software in the background.

### Remove Unneeded Code

Remove Unneeded Code reviews a change one file at a time and removes code that
the task does not need.

It is useful after implementation, when defensive branches, helpers, and
assumptions can remain even though the final design does not need them. The
skill protects existing behavior while looking for a smaller, clearer change.

## Requirements

- Python 3.10 or later
- Git
- GitHub CLI (`gh`) for pull request inputs
- An authenticated `gh` session for repositories that need authentication

The installed skill has no Python or Node package dependency. Node packages are
used only for development evals and browser checks.

## Install in Claude Code

Install the plugin:

```sh
claude plugin marketplace add andrea-sdl/open-skills
claude plugin install andrea-open-skills@open-skills
```

Start a new Claude Code session after installation.

## Install in Codex

Install the plugin:

```sh
codex plugin marketplace add andrea-sdl/open-skills --ref main
codex plugin add andrea-open-skills@open-skills
```

Start a new Codex task after installation.

## Upgrade from separate plugins

If you installed the old combined plugin or the earlier separate plugins,
remove them before you install the renamed plugin:

The old `remove-unneded-coded` identifier below keeps its original misspelling
because it names the plugin that must be removed.

Claude Code:

```sh
claude plugin uninstall pr-learning-path@open-skills
claude plugin uninstall complexity-evaluator@open-skills
claude plugin uninstall remove-unneded-coded@open-skills
claude plugin uninstall andreas-open-skills@open-skills
```

Codex:

```sh
codex plugin remove pr-learning-path@open-skills
codex plugin remove complexity-evaluator@open-skills
codex plugin remove remove-unneded-coded@open-skills
codex plugin remove andreas-open-skills@open-skills
```

The plugin keeps direct skill folders under `plugins/andrea-open-skills/skills/`
for tools that import skills without a marketplace.

## Use

Ask Claude Code or Codex:

```text
Build a learning path for https://github.com/owner/repository/pull/123.
```

To check complexity, invoke:

```text
Use $complexity-cli to check the changed supported code.
```

To install or update its executable directly, invoke:

```text
Use $setup-complexity-cli to install or update complexity.
```

To simplify a change, invoke:

```text
Use $remove-unneeded-code to simplify these changes.
```

For a local change, ask from the repository you want to study:

```text
Build a learning path for my current branch diff.
```

The skill returns paths to the gathered raw context, validated learning JSON,
and shareable HTML file.

## Development

Run the deterministic suite:

```sh
python3 -m unittest discover -s plugins/andrea-open-skills/tests -p 'test_*.py'
```

Run fixture checks, the deterministic suite, and the browser smoke test through
the eval runner:

```sh
cd plugins/andrea-open-skills/evals
npm ci
npm run check
```

Provider-backed consistency runs require a working Codex SDK runtime or an
authenticated Claude Code session:

```sh
npm run eval:codex
npm run eval:claude
npm run eval:both
npm run eval:explanations
```

Model-based grading is a consistency check. It is not an independent judge of
learning quality.

The authoring evals check post-answer explanations against the raw diff and PR
context. `eval:explanations` tests that shared rubric with two known good answers
and five bad answers: restated feedback, reversed flow, an invented guarantee,
missing evidence links, and one false example among otherwise valid content.
Both commands run fixture, unit, and browser checks first.

## License

GPL-2.0-only. See [LICENSE](LICENSE).
