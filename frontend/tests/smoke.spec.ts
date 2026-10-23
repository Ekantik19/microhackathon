import { expect, test } from "@playwright/test";

test("demo mode shows live insights, the mode switch, and a recap (mock data)", async ({ page }) => {
  const errors: string[] = [];
  page.on("console", (m) => m.type() === "error" && errors.push(m.text()));
  page.on("pageerror", (e) => errors.push(e.message));

  await page.goto("/");
  await expect(page).toHaveURL(/\/match\/demo_01$/);
  await expect(page.getByText("Synthetic data", { exact: true })).toBeVisible();
  await expect(page.getByText(/Clubs and players are fictional/)).toBeVisible();
  await expect(page.getByTestId("ai-badge")).toHaveText("AI: Mock");
  await expect(page.getByTestId("stats-rows")).toBeVisible();

  await page.getByTestId("demo-button").click();
  await expect(page.getByTestId("status-pill")).toHaveText(/Live replay/);
  const card = page.getByTestId("insight-card").first();
  await expect(card).toBeVisible({ timeout: 30_000 });
  const casualText = await card.textContent();

  await page.getByTestId("mode-tactical").click();
  await expect(page.getByTestId("mode-tactical")).toHaveAttribute("aria-checked", "true");
  await expect(page.getByTestId("insight-card").first()).toBeVisible();
  await expect.poll(async () => page.getByTestId("insight-card").first().textContent()).not.toBe(casualText);

  await expect(page.getByTestId("recap").first()).toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId("status-pill")).toHaveText("Recording ended"); // mock slice ends at 70:30
  await expect(page.getByTestId("score")).toContainText("1–1");

  expect(errors).toEqual([]);
});

test("mode choice persists across reloads", async ({ page }) => {
  await page.goto("/match/demo_01");
  await page.getByTestId("mode-tactical").click();
  await page.reload();
  await expect(page.getByTestId("mode-tactical")).toHaveAttribute("aria-checked", "true");
});
