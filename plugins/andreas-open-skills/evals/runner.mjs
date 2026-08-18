import { spawnSync } from "node:child_process";
import { mkdirSync, mkdtempSync, rmSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const project = path.resolve(here, "..");
const mode = process.argv[2];
const configs = {codex: "promptfooconfig.codex.yaml", claude: "promptfooconfig.claude.yaml"};

function run(command, args, options = {}) {
  const result = spawnSync(command, args, {
    cwd: options.cwd || here,
    env: options.env || process.env,
    stdio: "inherit",
  });
  if (result.error) throw result.error;
  return result.status === null ? 1 : result.status;
}

function checks() {
  const browserEnvironment = {...process.env, PR_LEARNING_BROWSER_SMOKE: "1"};
  const commands = [
    ["python3", ["verify-fixtures.py"], here, process.env],
    ["python3", ["-m", "unittest", "discover", "-s", "tests", "-v"], project, browserEnvironment],
  ];
  for (const [command, args, cwd, env] of commands) {
    const status = run(command, args, {cwd, env});
    if (status !== 0) return status;
  }
  return 0;
}

function evaluate(provider) {
  const temporaryDirectory = mkdtempSync(path.join(os.tmpdir(), `pr-learning-path-${provider}-`));
  const promptfooDirectory = path.join(temporaryDirectory, "promptfoo");
  const workspaceDirectory = path.join(temporaryDirectory, "workspace");
  const resultsDirectory = path.join(project, "results", "evals");
  mkdirSync(promptfooDirectory, {recursive: true});
  mkdirSync(workspaceDirectory, {recursive: true});
  mkdirSync(resultsDirectory, {recursive: true});
  try {
    return run(
      path.join(here, "node_modules", ".bin", "promptfoo"),
      [
        "eval", "--config", configs[provider], "--no-cache", "--no-share",
        "--output", path.join(resultsDirectory, `${provider}.json`),
        path.join(resultsDirectory, `${provider}.html`),
      ],
      {env: {
        ...process.env,
        PROMPTFOO_CACHE_PATH: path.join(promptfooDirectory, "cache"),
        PROMPTFOO_CONFIG_DIR: promptfooDirectory,
        PROMPTFOO_DISABLE_WAL_MODE: "true",
        PROMPTFOO_LOG_DIR: path.join(promptfooDirectory, "logs"),
        PROMPTFOO_PASS_RATE_THRESHOLD: "100",
        PROMPTFOO_PYTHON: "python3",
        PR_LEARNING_EVAL_WORKSPACE: workspaceDirectory,
      }},
    );
  } finally {
    rmSync(temporaryDirectory, {recursive: true, force: true});
  }
}

if (!["check", "codex", "claude", "both"].includes(mode)) {
  console.error("Use check, codex, claude, or both.");
  process.exit(2);
}
const checkStatus = checks();
if (checkStatus !== 0 || mode === "check") process.exit(checkStatus);
let failed = false;
for (const provider of mode === "both" ? ["codex", "claude"] : [mode]) {
  console.log(`\nRunning ${provider} authoring and self-consistency checks...\n`);
  if (evaluate(provider) !== 0) failed = true;
}
process.exit(failed ? 1 : 0);
