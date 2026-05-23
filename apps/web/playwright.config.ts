import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright config for Krytsia frontend E2E.
 *
 * Tests run against `npm run dev` (no production build required).
 * The web app makes API calls to NEXT_PUBLIC_API_BASE (default
 * http://localhost:8000); the API does NOT need to be up — tests are
 * written to assert the page skeleton, not live data, so a missing API
 * just leaves placeholders ("—") on KPI tiles.
 */
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false, // single-server dev cycle is faster sequential
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: process.env.CI ? [["list"], ["github"]] : "list",

  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:3000",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    locale: "en-US",
  },

  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],

  webServer: {
    command: "npm run dev",
    url: "http://localhost:3000",
    reuseExistingServer: !process.env.CI,
    timeout: 120 * 1000,
    stdout: "pipe",
    stderr: "pipe",
  },
});
