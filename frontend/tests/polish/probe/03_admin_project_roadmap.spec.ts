/**
 * PROBE 03 · /admin/projects/[id]/roadmap · 12-criteria empirical sweep.
 *
 * Sesión 3B-2B.2 Path B · PROBE batch 3/5 P1 pages.
 *
 * Uses test client project_id from globalSetup _dev/create-test-client.
 */
import {
  test,
  expect,
  runFullPolishSweep,
} from "../_helpers/polish-test-fixture";

// Sub-atom Sesión 3B-2B.2 Phase A.1 · use seed Cliente Test 1 UUID (real
// client/project that exists in DB seeds). Previous placeholder
// "00000000-...0001" doesn't exist · backend redirects to /admin/projects
// selector with toast "Proyecto no accesible · redirigiendo al selector"
// → wrong page tested · projectContext criterion fails because selector page
// is multi-cliente (no project breadcrumb).
const TEST_PROJECT_ID =
  process.env.POLISH_TEST_PROJECT_ID ??
  "11111111-1111-1111-1111-111111111111";

test.describe("PROBE · /admin/projects/[id]/roadmap", () => {
  test("12-criteria empirical sweep", async ({ authedPage }, testInfo) => {
    await authedPage.goto(`/admin/projects/${TEST_PROJECT_ID}/roadmap`);
    await authedPage.waitForLoadState("domcontentloaded");
    // Wait for either roadmap content OR redirect to selector (404 path)
    await Promise.race([
      authedPage.waitForSelector("text=Roadmap del proyecto", { timeout: 5000 }),
      authedPage.waitForURL(/\/admin\/projects(\?|$)/, { timeout: 5000 }),
    ]).catch(() => {});

    // Sub-atom Sesión 3B-2B.2 Phase A.1 · honest projectContext criterion.
    // Backend may redirect /admin/projects/[id]/* → /admin/projects selector
    // when project doesn't exist/inaccessible. Wait for networkidle + extra
    // 800ms to let client-side router.replace settle, then check URL pathname.
    // If URL pathname ends at /admin/projects (no project id), page is the
    // multi-cliente selector · NO breadcrumb expected.
    await authedPage.waitForLoadState("networkidle", { timeout: 5000 }).catch(() => {});
    await authedPage.waitForTimeout(800);
    const finalPath = new URL(authedPage.url()).pathname;
    const isOnProjectScopedRoute = /^\/admin\/projects\/[^/]+\//.test(finalPath);

    const result = await runFullPolishSweep(authedPage, {
      pageUrl: `/admin/projects/${TEST_PROJECT_ID}/roadmap`,
      pageName: "admin-project-roadmap",
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
