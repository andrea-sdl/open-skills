import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import {chromium} from "playwright";

const htmlPath = process.argv[2];
const screenshotPath = process.argv[3];
if (!htmlPath || !screenshotPath) {
  console.error("Use: npm run test:browser -- <learning.html> <screenshot.png>");
  process.exit(2);
}
const resolvedHtml = path.resolve(htmlPath);
const resolvedScreenshot = path.resolve(screenshotPath);
assert.ok(fs.existsSync(resolvedHtml), `Missing HTML: ${resolvedHtml}`);
fs.mkdirSync(path.dirname(resolvedScreenshot), {recursive: true});

const browser = await chromium.launch({
  executablePath: process.env.BROWSER_EXECUTABLE || chromium.executablePath(),
  headless: true,
});
try {
  const context = await browser.newContext({viewport: {width: 390, height: 844}, colorScheme: "light"});
  const page = await context.newPage();
  await page.goto(new URL(`file://${resolvedHtml}`).href);
  assert.equal(await page.locator("#stage-nav").count(), 1, "stage navigation is missing");
  assert.equal(await page.locator(".brand-mark svg").count(), 1, "Woven Loop brand mark is missing");
  const source = await page.evaluate(() => JSON.parse(document.getElementById("learning-data").textContent).source);
  if (source.mode === "github") {
    const expectedProject = `${source.identity.owner}/${source.identity.repo}`;
    assert.equal(await page.locator(".source-project").textContent(), expectedProject, "GitHub project name is missing");
    assert.equal(await page.getByRole("link", {name: "Open GitHub PR"}).count(), 1, "GitHub PR link label is wrong");
  } else {
    assert.equal(await page.locator(".source-project").count(), 0, "local changes must not show a GitHub project name");
    assert.equal(await page.getByRole("link", {name: "Open source"}).count(), 1, "local source link label is wrong");
  }
  const lightPalette = await page.evaluate(() => {
    const styles = getComputedStyle(document.documentElement);
    return {
      primary: styles.getPropertyValue("--primary").trim(),
      warm: styles.getPropertyValue("--brand-warm").trim(),
    };
  });
  assert.deepEqual(lightPalette, {primary: "#0f766e", warm: "#f28c28"}, "light brand palette is wrong");
  const themeButton = page.locator("#theme");
  assert.equal(await themeButton.textContent(), "System", "initial theme state is not visible");
  assert.equal(await themeButton.getAttribute("aria-label"), "Color theme: System. Change to Light", "initial theme state is not accessible");
  const lightThemeButton = await themeButton.evaluate(element => {
    const styles = getComputedStyle(element);
    return {appearance: styles.appearance, background: styles.backgroundColor};
  });
  assert.deepEqual(lightThemeButton, {appearance: "none", background: "rgb(255, 255, 255)"}, "light outline button style is wrong");
  assert.ok(await page.locator(".brand strong").evaluate(element => element.getBoundingClientRect().height < 24), "mobile brand title wrapped");
  assert.equal(await page.locator(".feedback").count(), 0, "feedback appeared before an answer");
  assert.equal(await page.locator(".answer-explanation").count(), 0, "explanation appeared before an answer");
  assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), "narrow layout overflows horizontally");

  const stages = page.locator("[data-stage-index]");
  const stageCount = await stages.count();
  assert.ok(stageCount >= 2, "direct stage navigation needs at least two stages");
  await stages.nth(stageCount - 1).click();
  assert.match(await page.locator(".section-head .eyebrow").textContent(), new RegExp(`Section ${stageCount} of ${stageCount}`));
  await page.locator("[data-stage-index]").first().click();

  const correctIndex = await page.evaluate(() => {
    const data = JSON.parse(document.getElementById("learning-data").textContent);
    const question = data.stages[0].questions[0];
    return question.options.findIndex(option => option.id === question.correctOptionId);
  });
  const wrongIndex = correctIndex === 0 ? 1 : 0;
  await page.keyboard.press(String(wrongIndex + 1));
  await page.locator(".feedback.wrong").waitFor();
  const explanation = await page.evaluate(() => JSON.parse(document.getElementById("learning-data").textContent).stages[0].questions[0].explanation);
  if (explanation) {
    assert.deepEqual(await page.locator(".answer-explanation li").allTextContents(), explanation.flow, "flow steps were lost or reordered");
    for (const field of ["why", "example", "boundary"]) {
      assert.ok((await page.locator(".answer-explanation").textContent()).includes(explanation[field]), `missing ${field}`);
    }
  }
  assert.equal(await page.getByText("Review the sources", {exact: true}).count(), 1, "source reference heading is missing");
  assert.equal(await page.locator(".source-links a").count() > 0, true, "post-answer source link is missing");
  assert.equal(await page.locator('.source-links a[target="_blank"]').count() > 0, true, "source link does not open separately");
  assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), "answered view overflows horizontally");
  assert.ok(
    await page.locator(".source-links a").evaluateAll(links => links.every(link => {
      const linkBounds = link.getBoundingClientRect();
      const containerBounds = link.parentElement.getBoundingClientRect();
      return linkBounds.left >= containerBounds.left && linkBounds.right <= containerBounds.right + 1;
    })),
    "source path extends past its feedback container",
  );
  assert.equal(await page.getByRole("button", {name: "Retry"}).count(), 1, "retry is missing after a wrong answer");
  assert.equal(await page.getByRole("button", {name: "Continue anyway"}).count(), 1, "soft completion action is missing");
  await page.getByRole("button", {name: "Retry"}).click();
  assert.equal(await page.locator(".answer-explanation").count(), 0, "retry must hide the answer explanation");
  await page.keyboard.press(String(correctIndex + 1));
  await page.locator(".feedback.correct").waitFor();
  if (explanation) {
    assert.deepEqual(await page.locator(".answer-explanation li").allTextContents(), explanation.flow, "correct answers must still teach the flow");
    assert.ok((await page.locator(".answer-explanation").textContent()).includes(explanation.example), "correct answer lost the worked example");
  }
  await themeButton.click();
  assert.equal(await themeButton.textContent(), "Light", "light theme state is not visible");
  await themeButton.click();
  await page.waitForTimeout(200);
  assert.equal(await page.locator("html").getAttribute("data-theme"), "dark", "dark theme did not apply");
  assert.equal(await themeButton.textContent(), "Dark", "dark theme state is not visible");
  assert.equal(await themeButton.getAttribute("aria-label"), "Color theme: Dark. Change to System", "dark theme state is not accessible");
  const darkPalette = await page.evaluate(() => {
    const styles = getComputedStyle(document.documentElement);
    return {
      primary: styles.getPropertyValue("--primary").trim(),
      warm: styles.getPropertyValue("--brand-warm").trim(),
    };
  });
  assert.deepEqual(darkPalette, {primary: "#5eead4", warm: "#fb923c"}, "dark brand palette is wrong");
  assert.equal(
    await themeButton.evaluate(element => getComputedStyle(element).backgroundColor),
    "rgb(18, 60, 56)",
    "dark outline button style is wrong",
  );
  await page.screenshot({path: resolvedScreenshot, fullPage: true});

  await page.reload();
  await page.locator(".question-top").waitFor();
  assert.match(await page.locator(".question-top").textContent(), /Answered correctly after retry/, "saved retry state did not persist");
  if (explanation) assert.equal(await page.locator(".answer-explanation").count(), 1, "saved correct answer lost its explanation");
  assert.equal(await page.locator("html").getAttribute("data-theme"), "dark", "saved theme did not persist");
  await page.reload();
  assert.equal(await page.locator("html").getAttribute("data-theme"), "dark", "revision cleanup removed the saved theme");
  page.once("dialog", dialog => dialog.accept());
  await page.getByRole("button", {name: "Reset"}).click();
  assert.match(await page.locator(".progress-copy").textContent(), /^0 of /, "reset did not clear progress");
  console.log("Browser behavior, narrow layout, persistence, retry, reset, themes, and post-answer links passed");
} finally {
  await browser.close();
}
