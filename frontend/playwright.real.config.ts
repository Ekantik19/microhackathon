import { defineConfig, devices } from "@playwright/test";

const API_PORT = 8100;
const WEB_PORT = 3200;

// End-to-end against the real FastAPI backend (mock AI provider, local synthetic events). No cloud needed.
export default defineConfig({
  testDir: "./tests/real",
  timeout: 90_000,
  workers: 1, // one shared backend simulator
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? "github" : "list",
  use: { baseURL: `http://localhost:${WEB_PORT}`, trace: "retain-on-failure", viewport: { width: 1280, height: 900 } },
  projects: [{ name: "desktop", use: { ...devices["Desktop Chrome"], viewport: { width: 1280, height: 900 } } }],
  webServer: [
    {
      command: `uv run uvicorn app.main:app --port ${API_PORT}`,
      cwd: "../backend",
      url: `http://localhost:${API_PORT}/health`,
      reuseExistingServer: false,
      timeout: 120_000,
      env: { WEB_ORIGIN: `http://localhost:${WEB_PORT}`, AI_PROVIDER: "mock", EVENT_SOURCE: "local" },
    },
    {
      command: `pnpm exec next dev --port ${WEB_PORT}`,
      url: `http://localhost:${WEB_PORT}/match/demo_01`,
      reuseExistingServer: false,
      timeout: 120_000,
      env: {
        NEXT_PUBLIC_USE_MOCK_API: "false",
        NEXT_PUBLIC_API_BASE_URL: `http://localhost:${API_PORT}`,
        NEXT_DIST_DIR: ".next-e2e-real",
      },
    },
  ],
});
