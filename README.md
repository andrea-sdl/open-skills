# Open Skills

Open Skills contains installable learning tools for Claude Code and Codex.
The same skill source powers both plugin formats.

## Included plugin

### PR Learning Path

PR Learning Path turns a GitHub pull request or local code change into one
self-contained HTML learning page. It asks hard multiple-choice questions
about the problem, prior behavior, design, flow, boundaries, risks, and impact.

The page grades each answer at once, explains every option, links to the exact
source revision after an answer, and saves progress in the browser. It does not
need a review product or server at runtime.

Read [the learning-skill goals](docs/learning-skills.md) for the design contract.

## Requirements

- Python 3.10 or later
- Git
- GitHub CLI (`gh`) for pull request inputs
- An authenticated `gh` session for repositories that need authentication

The installed skill has no Python or Node package dependency. Node packages are
used only for development evals and browser checks.

## Install in Claude Code

```sh
claude plugin marketplace add andrea-sdl/open-skills
claude plugin install pr-learning-path@open-skills
```

Start a new Claude Code session after installation.

## Install in Codex

```sh
codex plugin marketplace add andrea-sdl/open-skills --ref main
codex plugin add pr-learning-path@open-skills
```

Start a new Codex task after installation.

The direct skill folder is
`plugins/pr-learning-path/skills/pr-learning-path` for tools that import skill
folders without a marketplace.

## Use

Ask Claude Code or Codex:

```text
Build a learning path for https://github.com/owner/repository/pull/123.
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
python3 -m unittest discover -s plugins/pr-learning-path/tests -p 'test_*.py'
```

Run fixture checks, the deterministic suite, and the browser smoke test through
the eval runner:

```sh
cd plugins/pr-learning-path/evals
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
