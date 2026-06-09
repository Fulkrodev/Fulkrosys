/**
 * Playwright config dedicated for admin polish empirical verification.
 *
 * Sesión 3B-2B.2 Path B · OPS-052 15ª PREVENTED · empirical runtime
 * verification 12-criteria per page (NOT inferred from cumulative sub-atoms).
 *
 * Key differences vs main playwright.config.ts:
 * - testDir: ./tests/polish (separate from ./tests/e2e existing 190 specs)
 * - 6 viewports per test (mobile-sm/md · tablet/L · laptop · desktop)
 * - HTML reporter to polish-report/ (separate from existing reports)
 * - Screenshots always-on (NOT only-on-failure · empirical evidence)
 * - axe-core/playwright integration via tests/polish/_helpers/audit-helpers.ts
 *
 * Cómo ejecutar:
 *   cd frontend
 *   npm install                                  # install axe-core/playwright
 *   npx playwright install --with-deps chromium  # browser binaries
 *   npm run test:polish:probe                    # smoke 5 PROBE pages first
 *   npm run test:polish:p1                       # all P1 (17 pages)
 *   npm run test:polish:p2                       # all P2 (28 pages)
 *   npm run test:polish:report                   # show HTML report
 */
import { defineConfig, devices } from "@playwright/test";

/**
 * Port resolution (Marcos common scenarios):
 *
 *  1. Marcos runs `npm run dev` (default port 3000) and wants Playwright to
 *     reuse that server · set PLAYWRIGHT_PORT=3000 and PLAYWRIGHT_DEV=1 (skip
 *     spawning own server).
 *
 *  2. Marcos has nothing running · Playwright spawns `npx next start -p 3100`
 *     using existing prod build (.next/) · default behavior.
 *
 *  3. CI runs `npm run build` then this config spawns `next start` · default
 *     behavior with PLAYWRIGHT_PORT=3100 (or CI override).
 *
 * To use dev server (faster · hot reload friendly):
 *    PLAYWRIGHT_PORT=3000 PLAYWRIGHT_USE_DEV=1 npm run test:polish:probe
 */
const PORT = Number(process.env.PLAYWRIGHT_PORT ?? 3100);
const BASE_URL = `http://localhost:${PORT}`;
const USE_DEV_SERVER = process.env.PLAYWRIGHT_USE_DEV === "1";
const SKIP_WEB_SERVER = process.env.PLAYWRIGHT_SKIP_WEB_SERVER === "1";

// Viewports per page · 6 breakpoints for mobile responsive verification.
// Mobile-sm = 375x812 (iPhone 13 mini · smallest commonly supported).
// Desktop = 1920x1080 (most common workstation resolution).
const POLISH_VIEWPORTS = [
  { name: "mobile-sm", width: 375, height: 812 },
  { name: "mobile-md", width: 414, height: 896 },
  { name: "tablet", width: 768, height: 1024 },
  { name: "tablet-l", width: 1024, height: 768 },
  { name: "laptop", width: 1280, height: 800 },
  { name: "desktop", width: 1920, height: 1080 },
] as const;

export default defineConfig({
  testDir: "./tests/polish",
  globalSetup: require.resolve("./tests/e2e/_helpers/global-setup.ts"),
  timeout: 60_000,
  expect: { timeout: 10_000 },
  // Polish tests are independent · safe to parallelize.
  fullyParallel: true,
  // Empirical: 0 retries (results deterministic OR flake exposed).
  retries: 0,
  // 4 parallel workers · adjust per machine capacity.
  workers: 4,
  reporter: [
    ["html", { outputFolder: "polish-report", open: "never" }],
    ["list"],
  ],
  outputDir: "polish-test-results",
  use: {
    baseURL: BASE_URL,
    trace: "retain-on-failure",
    // Always-on screenshot per test (NOT only-on-failure · empirical evidence).
    screenshot: "on",
    video: "retain-on-failure",
  },
  // Single chromium project · multi-viewport handled inside test specs
  // (NOT via playwright projects · keeps per-test artifact grouping clean).
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  // webServer config:
  //  - SKIP_WEB_SERVER=1: skip entirely (Marcos manages dev server manually)
  //  - USE_DEV_SERVER=1: spawn `npm run dev -- -p PORT` (slower compile · hot reload)
  //  - default: spawn `npx next start -p PORT` (requires `.next/` prod build)
  webServer: SKIP_WEB_SERVER
    ? undefined
    : {
        command: USE_DEV_SERVER
          ? `npm run dev -- -p ${PORT}`
          : `npx next start -p ${PORT}`,
        port: PORT,
        reuseExistingServer: true,
        timeout: 180_000,
        stdout: "pipe",
        stderr: "pipe",
      },
});

// Export viewports for use in test specs.
export { POLISH_VIEWPORTS };
