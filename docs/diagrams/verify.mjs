/** Browser contract checks and Chrome PNG exports. See README for setup. */
import assert from "node:assert/strict";
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
const root = path.dirname(fileURLToPath(import.meta.url));
const { chromium } = await import(
  process.env.PLAYWRIGHT_MODULE || "playwright"
);
const browser = await chromium.launch({ channel: "chrome", headless: true });
const context = await browser.newContext({
  viewport: { width: 1360, height: 980 },
  deviceScaleFactor: 2,
});
const page = await context.newPage();
const errors = [];
page.on("pageerror", (error) => errors.push(error.message));
await context.route(/^https?:/, (route) => {
  errors.push("Unexpected remote request: " + route.request().url());
  return route.abort();
});
const url = (name) => pathToFileURL(path.join(root, name + ".html")).href;
const visible = () => page.locator("[data-view]:visible");
const view = async (id) => {
  await page.waitForFunction(
    (id) => document.querySelector(`[data-view="${id}"]`)?.hidden === false,
    id,
  );
  await page.waitForFunction(
    () =>
      !document.querySelector(".flight") && !document.getAnimations().length,
  );
  assert.equal(await visible().getAttribute("data-view"), id);
};
const go = async (route, id) => {
  await visible().locator(`[data-route="${route}"]`).click();
  await view(id);
};
const back = async (id) => {
  await page.locator("#up").click();
  await view(id);
};
const overview = async () => {
  await page.locator("#overview").click();
  await view("overview");
};
const report = { diagrams: [], checks: [] };

try {
  for (const id of ["overview", "analysis", "fold", "estimation", "config"]) {
    await page.goto(url(id));
    await page.evaluate(() => document.fonts.ready);
    assert.equal((await page.locator(".node").count()) <= 9, true);
    assert.equal((await page.locator(".connector").count()) <= 12, true);
    // Check actual font bounds, not guessed character widths.
    const geometry = await page.evaluate(() => {
      const problems = [];
      for (const node of document.querySelectorAll(".node")) {
        if (node.querySelector("path.node-box")) continue;
        const rect = node.querySelector(".node-box").getBBox();
        for (const text of node.querySelectorAll("text")) {
          const box = text.getBBox();
          if (
            box.x < rect.x + 4 ||
            box.x + box.width > rect.x + rect.width - 4 ||
            box.y < rect.y + 2 ||
            box.y + box.height > rect.y + rect.height - 2
          )
            problems.push(`${node.id}: text exceeds node: ${text.textContent}`);
        }
      }
      for (const caption of document.querySelectorAll(".edge-caption")) {
        const a = caption.querySelector("rect").getBBox();
        for (const line of document.querySelectorAll(".connector")) {
          for (
            let distance = 0;
            distance <= line.getTotalLength();
            distance += 2
          ) {
            const p = line.getPointAtLength(distance);
            if (
              p.x > a.x - 6 &&
              p.x < a.x + a.width + 6 &&
              p.y > a.y - 6 &&
              p.y < a.y + a.height + 6
            ) {
              problems.push(
                `Connector is too close to label: ${caption.textContent}`,
              );
              break;
            }
          }
        }
        for (const node of document.querySelectorAll(".node-box")) {
          const b = node.getBBox();
          if (
            a.x < b.x + b.width &&
            a.x + a.width > b.x &&
            a.y < b.y + b.height &&
            a.y + a.height > b.y
          )
            problems.push(`Label overlaps node: ${caption.textContent}`);
        }
      }
      return problems;
    });
    assert.deepEqual(geometry, [], `${id} geometry`);
    await page.addStyleTag({ content: ".evidence { display:none }" });
    await page
      .locator("main")
      .screenshot({ path: path.join(root, id + ".png") });
    report.diagrams.push({ id, geometry: "passed", exported: id + ".png" });
  }
  await page.goto(url("index"));
  await view("overview");
  assert.equal(await page.locator("#up").isVisible(), false);
  await page.screenshot({ path: path.join(root, "index.png"), fullPage: true });
  await go("overview:analysis", "analysis");
  await go("analysis:folds", "fold");
  await go("fold:train", "source-fold");
  assert.match(
    await visible().locator("pre").textContent(),
    /def finetune_fold/,
  );
  await back("fold");
  assert.equal(
    await page.evaluate(() => document.activeElement.dataset.route),
    "fold:train",
  );
  await back("analysis");
  assert.equal(
    await page.evaluate(() => document.activeElement.dataset.route),
    "analysis:folds",
  );
  await go("analysis:estimate", "estimation");
  await go("estimation:dispatch", "source-estimator");
  assert.match(
    await visible().locator("pre").textContent(),
    /def _estimate_effects/,
  );
  await back("estimation");
  await page.goBack();
  await view("analysis");
  await page.goForward();
  await view("estimation");
  await page.screenshot({
    path: path.join(root, "interaction.png"),
    fullPage: true,
  });
  report.checks.push(
    "Both drill-down paths reach pinned source; Up and browser Back/Forward restore parent and focus",
  );

  await go("estimation:config", "config");
  assert.match(
    await page.locator(".context-anchor small").textContent(),
    /Related view/,
  );
  await back("estimation");
  await go("estimation:fold", "fold");
  await go("fold:config", "config");
  await back("fold");
  await go("fold:estimation", "estimation");
  await back("fold");
  await back("estimation");
  await page
    .locator(".breadcrumbs button")
    .filter({ hasText: "One analysis" })
    .click();
  await view("analysis");
  await go("analysis:config", "config");
  await back("analysis");
  await overview();
  await go("overview:config", "config");
  await back("overview");
  report.checks.push(
    "Every related link, all four configuration entry points, breadcrumbs and Overview",
  );

  // Keyboard enters the same native SVG links and restores focus after return.
  const rootLink = visible().locator('[data-route="overview:analysis"]');
  await rootLink.focus();
  await page.keyboard.press("Enter");
  await view("analysis");
  await page.locator("#up").focus();
  await page.keyboard.press("Enter");
  await view("overview");
  assert.equal(
    await page.evaluate(() => document.activeElement.dataset.route),
    "overview:analysis",
  );
  await page.keyboard.press("Tab");
  assert.equal(
    await page.evaluate(() => document.activeElement.dataset.route),
    "overview:config",
  );
  report.checks.push(
    "Keyboard Enter, Tab order, visible focus and focus restoration",
  );

  await page.emulateMedia({ reducedMotion: "reduce" });
  await rootLink.click();
  await view("analysis");
  assert.equal(await page.locator(".flight").count(), 0);
  assert.equal(await page.evaluate(() => document.getAnimations().length), 0);
  await go("analysis:estimate", "estimation");
  await page.reload();
  await view("estimation");
  await back("analysis");
  await overview();
  report.checks.push("Reduced motion and reload preserve navigation");

  await page.setViewportSize({ width: 390, height: 844 });
  await visible()
    .locator(".diagram-scroll")
    .evaluate((el) => {
      el.scrollLeft = 400;
    });
  await visible().locator("summary").click();
  await go("overview:analysis", "analysis");
  await back("overview");
  assert(
    Math.abs(
      (await visible()
        .locator(".diagram-scroll")
        .evaluate((el) => el.scrollLeft)) - 400,
    ) <= 1,
    "horizontal position restored within a CSS pixel",
  );
  assert.equal(
    await visible()
      .locator("details")
      .evaluate((el) => el.open),
    true,
  );
  assert.equal(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
    true,
  );
  await page.screenshot({
    path: path.join(root, "narrow.png"),
    fullPage: true,
  });
  report.checks.push(
    "390px screen: diagram scroll and expanded evidence restored, no page overflow",
  );

  const deep = await context.newPage();
  await deep.goto(
    url("index") + "#overview/analysis/estimation/source-estimator",
  );
  await deep.waitForSelector('[data-view="source-estimator"]:visible');
  await deep.locator("#up").click();
  await deep.waitForSelector('[data-view="estimation"]:visible');
  await deep.close();
  report.checks.push("Direct deep link seeds parent history");

  await page.setViewportSize({ width: 1360, height: 980 });
  await page.emulateMedia({ reducedMotion: "no-preference" });
  await page.goto(url("index"));
  await view("overview");
  await visible().locator('[data-route="overview:analysis"]').click();
  await page.waitForFunction(() =>
    document
      .getAnimations()
      .some((a) => a.effect.target.classList.contains("flight")),
  );
  await page.evaluate(() => {
    for (const a of document.getAnimations()) {
      a.pause();
      a.currentTime = 140;
    }
  });
  await page.screenshot({
    path: path.join(root, "transition.png"),
    fullPage: true,
  });
  await page.evaluate(() =>
    document.getAnimations().forEach((a) => a.finish()),
  );
  await view("analysis");
  await page.locator("#up").click();
  await page.waitForFunction(() =>
    document
      .getAnimations()
      .some((a) => a.effect.target.classList.contains("flight")),
  );
  await page.evaluate(() =>
    document.getAnimations().forEach((a) => a.finish()),
  );
  await view("overview");
  await go("overview:analysis", "analysis");
  await go("analysis:estimate", "estimation");
  await go("estimation:dispatch", "source-estimator");
  await page.screenshot({
    path: path.join(root, "source.png"),
    fullPage: true,
  });
  await visible()
    .locator("pre")
    .evaluate((el) => {
      el.scrollTop = 300;
    });
  await back("estimation");
  await page.goForward();
  await view("source-estimator");
  assert.equal(
    await visible()
      .locator("pre")
      .evaluate((el) => el.scrollTop),
    300,
  );
  await page.emulateMedia({ media: "print" });
  assert.equal(await page.locator(".toolbar").isVisible(), false);
  await page.emulateMedia({ media: "screen" });
  report.checks.push(
    "Forward and reverse node-anchor animation, source scroll restoration and print chrome",
  );

  const staticContext = await browser.newContext({ javaScriptEnabled: false });
  const staticPage = await staticContext.newPage();
  await staticPage.goto(url("index"));
  await staticPage
    .locator('[data-view="overview"] [data-destination="analysis"]')
    .click();
  assert.match(staticPage.url(), /analysis.html$/);
  assert.equal(await staticPage.locator(".node").count(), 6);
  await staticContext.close();
  report.checks.push("No-JavaScript fallback follows standalone diagram links");

  // The entry point embeds precisely the same SVG bytes as the standalone pages.
  const index = await fs.readFile(path.join(root, "index.html"), "utf8");
  for (const id of ["overview", "analysis", "fold", "estimation", "config"]) {
    const standalone = await fs.readFile(path.join(root, id + ".html"), "utf8");
    const svg = standalone.match(/<svg[\s\S]*?<\/svg>/)[0];
    assert(index.includes(svg), `${id}: standalone/viewer divergence`);
  }
  const evidence = JSON.parse(
    await fs.readFile(path.join(root, "evidence.json"), "utf8"),
  );
  for (const item of evidence.snippets) {
    const { execFileSync } = await import("node:child_process");
    const source = execFileSync(
      "git",
      [
        "show",
        `${evidence.repositories["bonsai-causal"].sha}:${item.filename}`,
      ],
      { cwd: path.join(root, "../.."), encoding: "utf8" },
    )
      .split("\n")
      .slice(item.start - 1, item.end)
      .join("\n");
    assert.equal(source, item.source);
  }
  report.checks.push(
    "Exact standalone/viewer SVG reuse and source snippets match recorded revision",
  );
  assert.deepEqual(errors, []);
  report.checks.push("No browser errors or remote asset requests");
  console.log(JSON.stringify(report, null, 2));
} finally {
  await browser.close();
}
