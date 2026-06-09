/**
 * PROBE 01 · /admin/dashboard · 12-criteria empirical sweep.
 *
 * Sesión 3B-2B.2 Path B · PROBE batch 1/5 P1 pages.
 *
 * Output evidence:
 *  - polish-test-results/screenshots/admin-dashboard_{viewport}.png × 6
 *  - axe violations captured + asserted critical+serious === 0
 *  - tab order captured
 *  - polish-report/ HTML aggregated
 */
import {
  test,
  expect,
  runFullPolishSweep,
} from "../_helpers/polish-test-fixture";

test.describe("PROBE · /admin/dashboard", () => {
  test("12-criteria empirical sweep", async ({ authedPage }, testInfo) => {
    await authedPage.goto("/admin/dashboard");
    await authedPage.waitForLoadState("domcontentloaded");

    const result = await runFullPolishSweep(authedPage, {
      pageUrl: "/admin/dashboard",
      pageName: "admin-dashboard",
      isProjectScoped: false,
    });

    // Attach evidence FIRST (before any expect can fail and skip attach).
    // Path B 3-point commitment EMPIRICAL · evidence always captured.
    await testInfo.attach("criteria-result.json", {
      body: JSON.stringify(result, null, 2),
      contentType: "application/json",
    });
    await testInfo.attach("axe-violations.json", {
      body: JSON.stringify(result.evidence.axeViolations, null, 2),
      contentType: "application/json",
    });

    // Empirical assertions · concrete pass/fail per criterio.
    expect(
      result.criteria.mobileResponsive,
      `mobile responsive · violations: ${JSON.stringify(result.evidence.horizontalOverflowViolations)}`,
    ).toBe(true);
    expect(
      result.criteria.wcagAA,
      `WCAG AA · ${result.evidence.axeViolations.length} violations: ${result.evidence.axeViolations.map((v) => `[${v.impact}] ${v.id}`).join(", ")}`,
    ).toBe(true);
    expect(
      result.criteria.keyboardNav,
      `keyboard navigation · Tab order length: ${result.evidence.tabOrderLength}`,
    ).toBe(true);
    expect(result.criteria.titleBreadcrumb, "page title h1/h2 visible").toBe(
      true,
    );

    // Overall: at least 9/12 criteria PASS (room for polish iteration)
    expect(
      result.passCount,
      `passCount ${result.passCount}/12 criteria`,
    ).toBeGreaterThanOrEqual(9);
  });
});
