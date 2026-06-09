/**
 * PROBE 04 · /admin/projects/[id]/summary · 12-criteria empirical sweep.
 *
 * Sesión 3B-2B.2 Path B · PROBE batch 4/5 P1 pages.
 */
import {
  test,
  expect,
  runFullPolishSweep,
} from "../_helpers/polish-test-fixture";

// Sub-atom Sesión 3B-2B.2 Phase A.1 · seed Cliente Test 1 UUID (real client
// in DB seeds) prevents backend redirect to selector → projectContext PASS.
const TEST_PROJECT_ID =
  process.env.POLISH_TEST_PROJECT_ID ??
  "11111111-1111-1111-1111-111111111111";

test.describe("PROBE · /admin/projects/[id]/summary", () => {
  test("12-criteria empirical sweep", async ({ authedPage }, testInfo) => {
    await authedPage.goto(`/admin/projects/${TEST_PROJECT_ID}/summary`);
    await authedPage.waitForLoadState("domcontentloaded");
    await Promise.race([
      authedPage.waitForSelector("[data-testid='phase-progress-wizard']", {
        timeout: 5000,
      }),
      authedPage.waitForURL(/\/admin\/projects(\?|$)/, { timeout: 5000 }),
    ]).catch(() => {});

    // Honest projectContext · URL-based check after redirect settles
    // (networkidle + 800ms · see probe-03 comment for rationale).
    await authedPage.waitForLoadState("networkidle", { timeout: 5000 }).catch(() => {});
    await authedPage.waitForTimeout(800);
    const finalPath = new URL(authedPage.url()).pathname;
    const isOnProjectScopedRoute = /^\/admin\/projects\/[^/]+\//.test(finalPath);

    const result = await runFullPolishSweep(authedPage, {
      pageUrl: `/admin/projects/${TEST_PROJECT_ID}/summary`,
      pageName: "admin-project-summary",
      isProjectScoped: isOnProjectScopedRoute,
    });

    await testInfo.attach("criteria-result.json", {
      body: JSON.stringify(result, null, 2),
      contentType: "application/json",
    });
    await testInfo.attach("axe-violations.json", {
      body: JSON.stringify(result.evidence.axeViolations, null, 2),
      contentType: "application/json",
    });

    expect(
      result.criteria.mobileResponsive,
      `mobile responsive · violations: ${JSON.stringify(result.evidence.horizontalOverflowViolations)}`,
    ).toBe(true);
    expect(
      result.criteria.wcagAA,
      `WCAG AA · ${result.evidence.axeViolations.length} violations: ${result.evidence.axeViolations.map((v) => `[${v.impact}] ${v.id}`).join(", ")}`,
    ).toBe(true);
    expect(result.criteria.keyboardNav, "keyboard navigation").toBe(true);

    expect(result.passCount).toBeGreaterThanOrEqual(9);
  });
});
