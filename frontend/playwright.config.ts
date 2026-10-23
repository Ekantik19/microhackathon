import { defineConfig, devices } from "@playwright/test";

const PORT = 3100;

// Smoke tests run against the clearly-labeled mock data layer, so they need no backend.
export default defineConfig({
  testDir: "./tests/mock",
  timeout: 90_000,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? "github" : "list",
  use: { baseURL: `http://localhost:${PORT}`, trace: "retain-on-failure" },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"], viewport: { width: 1280, height: 900 } } },
    { name: "mobile", use: { ...devices["Pixel 7"] } },
  ],
  webServer: {
    command: `pnpm exec next dev --port ${PORT}`,
    url: `http://localhost:${PORT}/match/demo_01`,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
    env: { NEXT_PUBLIC_USE_MOCK_API: "true", NEXT_DIST_DIR: ".next-e2e-mock" },
  },
});
