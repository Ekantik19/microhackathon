// Visual check helper: runs Demo mode in a real browser and saves desktop + mobile screenshots.
//   node scripts/screenshots.mjs [baseUrl=http://localhost:3000] [outDir=./screenshots]
// Start the app first (`make dev`, or a mock-mode `next dev`). Screenshots are git-ignored.
import { mkdirSync } from "node:fs";
import { chromium, devices } from "@playwright/test";

const base = process.argv[2] ?? "http://localhost:3000";
const out = process.argv[3] ?? "./screenshots";
mkdirSync(out, { recursive: true });

const browser = await chromium.launch();
for (const [name, opts] of [
  ["desktop", { viewport: { width: 1280, height: 900 } }],
  ["mobile", devices["Pixel 7"]],
]) {
  const page = await browser.newPage(opts);
  await page.goto(`${base}/match/demo_01`);
  await page.getByTestId("demo-button").click();
  await page.waitForTimeout(25_000);
  await page.screenshot({ path: `${out}/${name}-mid.png`, fullPage: true });
  await page.getByTestId("recap").first().waitFor({ timeout: 90_000 });
  await page.screenshot({ path: `${out}/${name}-end.png`, fullPage: true });
  await page.close();
}
await browser.close();
console.log(`saved screenshots to ${out}`);
