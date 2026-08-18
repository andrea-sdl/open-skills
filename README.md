# Open Skills

Open Skills contains installable skills for Claude Code and Codex.
The same source powers both plugin formats.

## Included skills

### PR Learning Path

PR Learning Path turns a GitHub pull request or local code change into one
self-contained HTML learning page. It asks hard multiple-choice questions
about the problem, prior behavior, design, flow, boundaries, risks, and impact.

The page grades each answer at once, explains every option, links to the exact
source revision after an answer, and saves progress in the browser. It does not
need a review product or server at runtime.

Read [the learning-skill goals](docs/learning-skills.md) for the design contract.

### Complexity Evaluator

Complexity Evaluator exposes `$complexity-cli` only when you invoke it. It
checks changed JavaScript, TypeScript, PHP, Rust, and Python before handoff.
Install the separate `complexity` binary first. The hook samples are opt-in at
`plugins/andreas-open-skills/hooks/`.

### Remove Unneded Coded

Remove Unneded Coded reviews a change one file at a time and removes code that
the task does not need.

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
claude plugin install andreas-open-skills@open-skills
```

Start a new Claude Code session after installation.

## Install in Codex

Install the plugin:

```sh
codex plugin marketplace add andrea-sdl/open-skills --ref main
codex plugin add andreas-open-skills@open-skills
```

Start a new Codex task after installation.

## Upgrade from separate plugins

If you installed the earlier separate plugins, remove them before you install
the combined plugin:

Claude Code:

```sh
claude plugin uninstall pr-learning-path@open-skills
claude plugin uninstall complexity-evaluator@open-skills
claude plugin uninstall remove-unneded-coded@open-skills
```

Codex:

```sh
codex plugin remove pr-learning-path@open-skills
codex plugin remove complexity-evaluator@open-skills
codex plugin remove remove-unneded-coded@open-skills
```

The plugin keeps direct skill folders under `plugins/andreas-open-skills/skills/`
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

To simplify a change, invoke:

```text
Use $remove-unneded-coded to simplify these changes.
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
python3 -m unittest discover -s plugins/andreas-open-skills/tests -p 'test_*.py'
```

Run fixture checks, the deterministic suite, and the browser smoke test through
the eval runner:

```sh
cd plugins/andreas-open-skills/evals
npm ci
npm run check
```

Provider-backed consistency runs require a working Codex SDK runtime or an
authenticated Claude Code session:

```sh
npm run eval:codex
npm run eval:claude
npm run eval:both
```

Model-based grading is a consistency check. It is not an independent judge of
learning quality.

## License

GPL-2.0-only. See [LICENSE](LICENSE).
