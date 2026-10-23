import { expect, test, type Page } from "@playwright/test";

const API = "http://localhost:8100";

function trackErrors(page: Page): string[] {
  const errors: string[] = [];
  page.on("console", (m) => m.type() === "error" && errors.push(m.text()));
  page.on("pageerror", (e) => errors.push(e.message));
  return errors;
}

const clockMinute = async (page: Page) => Number((await page.getByTestId("clock").textContent())!.slice(0, 2));

test.beforeEach(async ({ request }) => {
  await request.post(`${API}/matches/demo_01/simulation/reset`);
});

test("Start streams a live clock, score and stats from the backend", async ({ page }) => {
  const errors = trackErrors(page);
  await page.goto("/match/demo_01");
  await expect(page.getByTestId("ai-badge")).toHaveText("AI: Mock");
  await expect(page.getByTestId("clock")).toHaveText(/^00:00/);
  await expect(page.getByTestId("stats-rows")).toContainText("n/a");

  await page.getByRole("button", { name: "Speed 60x" }).click();
  await page.getByTestId("primary-control").click();
  await expect(page.getByTestId("status-pill")).toHaveText(/Live replay/);
  await expect.poll(() => clockMinute(page), { timeout: 15_000 }).toBeGreaterThanOrEqual(2);
  await expect(page.getByTestId("stats-rows")).toContainText("%"); // possession is computed now
  await expect(page.getByTestId("ball")).toBeVisible();

  await page.getByTestId("primary-control").click();
  await expect(page.getByTestId("status-pill")).toHaveText("Paused");
  expect(errors).toEqual([]);
});

test("seek and timeline clicks rebuild the view; reset clears it", async ({ page, request }) => {
  const errors = trackErrors(page);
  await page.goto("/match/demo_01");
  await expect(page.getByTestId("clock")).toHaveText(/^00:00/);

  await request.post(`${API}/matches/demo_01/simulation/seek`, { data: { match_second: 2820 + 25 * 60 } }); // 70:00
  await expect(page.getByTestId("score")).toContainText("1–1");
  await expect(page.getByTestId("clock")).toHaveText(/^70:00/);
  // Phase 8 detectors: the live intelligence strip and the timeline show the 66' sustained-pressure spell.
  await expect(page.getByTestId("intel-strip")).toContainText("Northbridge sustained pressure since 61'");
  await expect(page.getByTestId("intel-strip")).toContainText("Signal strength (rule-based)");
  await expect(page.getByRole("button", { name: /^66' Sustained pressure/ })).toBeVisible();

  await page.getByRole("button", { name: /Goal: Andrei Kovalski/ }).click();
  await expect(page.getByTestId("score")).toContainText("0–1");
  await expect(page.getByTestId("clock")).toHaveText(/^23:/);
  await expect(page.getByRole("button", { name: /Goal: Tomas Reyes/ })).toHaveCount(0); // no future on the timeline

  await page.getByRole("button", { name: "Reset" }).click();
  await expect(page.getByTestId("clock")).toHaveText(/^00:00/);
  await expect(page.getByTestId("score")).toContainText("0–0");
  expect(errors).toEqual([]);
});

test("the stream retries with backoff and resyncs when it comes back", async ({ page, request }) => {
  await page.route("**/stream**", (route) => route.abort()); // the live stream is unreachable
  await page.goto("/match/demo_01");
  await expect(page.getByTestId("clock")).toHaveText(/^00:00/); // state still loads over REST
  await expect(page.getByText("Live connection lost. Reconnecting…")).toBeVisible({ timeout: 10_000 });
  await request.post(`${API}/matches/demo_01/simulation/seek`, { data: { match_second: 600 } }); // happens while down
  await page.unroute("**/stream**");
  await expect(page.getByText("Live connection lost. Reconnecting…")).toBeHidden({ timeout: 20_000 });
  await expect(page.getByTestId("clock")).toHaveText(/^10:00/); // resynced from REST on reconnect
});

test("Demo mode walks the storyline: live insights with a grounding check, then the full-time recap", async ({ page }) => {
  test.setTimeout(120_000);
  const errors = trackErrors(page);
  await page.goto("/match/demo_01");
  await expect(page.getByTestId("clock")).toHaveText(/^00:00/);
  const started = Date.now();
  await page.getByTestId("demo-button").click();

  const card = page.getByTestId("insight-card").first();
  await expect(card).toBeVisible({ timeout: 40_000 });
  await expect(card).toContainText("Mock");
  await card.getByText(/Evidence/).click();
  await expect(card.getByTestId("grounding-check")).toContainText("Passed first time");

  await expect(page.getByTestId("status-pill")).toHaveText("Full time", { timeout: 90_000 });
  await expect(page.getByTestId("recap").first()).toContainText("At full-time it is Northbridge FC 1-1 Riverside Athletic");
  expect(Date.now() - started).toBeLessThan(90_000); // demo mode finishes in under 90 s
  await expect(page.getByTestId("score")).toContainText("1–1");
  expect(errors).toEqual([]);
});
