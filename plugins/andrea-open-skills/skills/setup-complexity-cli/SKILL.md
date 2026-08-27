---
name: setup-complexity-cli
description: Install or update the complexity executable required by $complexity-cli. Use when setup is requested or the complexity check reports that its executable is missing or incompatible.
---

# Setup Complexity CLI

Install the pinned supported `complexity` release.

1. Run `scripts/setup_complexity.py --check`.
2. If it reports `READY`, return the executable path and version without
   downloading anything.
3. If it reports `SETUP_REQUIRED`, explain that setup downloads version `0.4.0`
   from `andrea-sdl/complexity-evaluator` and installs it in the user's private
   data directory. Private-repository downloads require an authenticated `gh`
   session with access to that repository.
4. Ask for approval immediately before the download and install command.
5. After approval, run `scripts/setup_complexity.py`.
6. Run the check again and report the installed path and version.

Never install an unpinned latest release. A plugin update must change the
pinned supported version. The installer verifies the published SHA-256 file
before it replaces an existing executable.

If setup was entered from `$complexity-cli`, resume the original complexity
check after setup succeeds.
