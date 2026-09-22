# Lifecycle hooks

The plugin enables these hooks through `hooks/hooks.json`. The configuration
examples below are for direct skill installations without the plugin.

Use `UserPromptSubmit` to record the task's starting Git and file state. Use
`PostToolUse` after file edits and shell commands to send complexity advice to
the agent through `hookSpecificOutput.additionalContext`. Hooks never return a
blocking decision or a nonzero exit code for findings or check errors.

The checker filters unsupported files before it starts `complexity`. It compares
supported file contents with the last check, so reads and test runs do not
repeat analysis. It also suppresses unchanged findings when other file contents
change. Each user prompt starts a fresh baseline and advice cache.

An unchanged supported file that was already dirty before the prompt is outside
the task scope. Changes committed during the task remain in scope. Without a
baseline, the hook falls back to Git-changed supported files. Without a session
ID or valid working directory, it stays silent.

Findings ask the agent to consider scoped improvements, preserve behavior, and
continue when a refactor would make the code worse. Missing tools or failed
analysis produce advice that the check is unavailable, never a pass. The agent
must not install tools just because an automatic check failed. Use
`$setup-complexity-cli` when you want to install the tool.

The explicit CLI and skill keep their strict outcomes and exit codes. Existing
Stop hook configurations become silent with the updated wrapper; replace them
with the PostToolUse configuration below to receive advice.

## Scope decision

Keep the core CLI strict for unsupported explicit files. The hook wrapper owns
file filtering because it knows the task lifecycle and Git state. This keeps
manual CLI mistakes visible without making AI hooks noisy.

Scope is file-based. The CLI still reports old complex functions inside a file
that the task changed. The agent must separate those old findings from changes
made for the task. Function-level diff tracking is outside this small hook.

## Codex

Merge this into the repository's `.codex/hooks.json`:

```json
{
  "description": "Advise on changed JS, TS, PHP, Rust, and Python after edits.",
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 \"$HOME/.agents/skills/complexity-cli/scripts/check_complexity.py\" --baseline-hook",
            "timeout": 30
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Bash|Edit|Write|apply_patch",
        "hooks": [
          {
            "type": "command",
            "command": "python3 \"$HOME/.agents/skills/complexity-cli/scripts/check_complexity.py\" --hook",
            "timeout": 120,
            "statusMessage": "Checking code complexity"
          }
        ]
      }
    ]
  }
}
```

Project hooks run only in a trusted project. Review and trust the exact hook in
Codex with `/hooks`.

## Claude Code

Merge this into the repository's `.claude/settings.json`:

```json
{
  "skillOverrides": {
    "complexity-cli": "user-invocable-only"
  },
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 \"$HOME/.claude/skills/complexity-cli/scripts/check_complexity.py\" --baseline-hook",
            "timeout": 30
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Bash|Edit|Write|apply_patch",
        "hooks": [
          {
            "type": "command",
            "command": "python3 \"$HOME/.claude/skills/complexity-cli/scripts/check_complexity.py\" --hook",
            "timeout": 120,
            "statusMessage": "Checking code complexity"
          }
        ]
      }
    ]
  }
}
```

The `user-invocable-only` override keeps the skill out of Claude's model
context while leaving `/complexity-cli` available. Use `/hooks` to inspect the
loaded hook.
