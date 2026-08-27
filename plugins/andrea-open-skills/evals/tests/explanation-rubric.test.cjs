const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const {test} = require("node:test");
const rubric = require("../explanation-rubric.cjs");

for (const name of ["auth-boundary", "cache-flow"]) {
  test(`${name}: judge receives source data and oracle, not unresolved file references`, () => {
    const fixture = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "fixtures", `${name}.json`), "utf8"));
    const expectations = fs.readFileSync(path.join(__dirname, "..", "fixtures", `${name}.expectations.md`), "utf8");
    const fromFiles = rubric("candidate", {vars: {
      fixture: `file://fixtures/${name}.json`,
      expectations: `file://fixtures/${name}.expectations.md`,
    }});
    for (const value of [fixture, JSON.stringify(fixture)]) {
      assert.equal(rubric("candidate", {vars: {fixture: value, expectations}}), fromFiles);
    }
    assert.ok(fromFiles.includes(JSON.stringify(fixture, null, 2)));
    assert.ok(fromFiles.includes(expectations));
    assert.ok(!fromFiles.includes("{{ fixture"));
    assert.ok(!fromFiles.includes("file://fixtures/"));
  });
}

test("missing evidence stops grading instead of asking the judge to guess", () => {
  assert.throws(() => rubric("candidate", {vars: {fixture: {}, expectations: "oracle"}}), /evidence/);
  assert.throws(() => rubric("candidate", {vars: {fixture: {diff: "diff", description: "intent"}, expectations: ""}}), /oracle/);
});
