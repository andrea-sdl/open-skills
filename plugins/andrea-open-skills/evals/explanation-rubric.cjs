const fs = require("node:fs");
const path = require("node:path");

function readValue(value) {
  if (typeof value === "string" && value.startsWith("file://")) {
    return fs.readFileSync(path.resolve(__dirname, value.slice(7)), "utf8");
  }
  return value;
}

// Promptfoo reads text-file assertions without rendering their templates.
// Return the full rubric and evidence so the judge never sees placeholders.
module.exports = function explanationRubric(_output, {vars}) {
  const rawFixture = readValue(vars.fixture);
  const fixture = typeof rawFixture === "string" ? JSON.parse(rawFixture) : rawFixture;
  if (!fixture?.diff || !fixture?.description) throw new Error("Rubric needs raw change evidence");
  const expectations = readValue(vars.expectations);
  if (typeof expectations !== "string" || !expectations.trim()) throw new Error("Rubric needs an evidence oracle");
  return [
    fs.readFileSync(path.join(__dirname, "explanation-rubric.txt"), "utf8"),
    "Raw change:", JSON.stringify(fixture, null, 2),
    "Evidence oracle:", expectations,
  ].join("\n\n");
};
