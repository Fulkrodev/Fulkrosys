/**
 * PROBE 02 · /admin/projects (selector) · 12-criteria empirical sweep.
 *
 * Sesión 3B-2B.2 Path B · PROBE batch 2/5 P1 pages.
 *
 * Special: handles single-project auto-redirect from Sesión 3A Phase A.2 ·
 * tests run when N > 1 projects OR explicit interception.
 */
import {
  test,
  expect,
  runFullPolishSweep,
} from "../_helpers/polish-test-fixture";

test.describe("PROBE · /admin/projects (selector)", () => {
  test("12-criteria empirical sweep", async ({ authedPage }, testInfo) => {
    // Intercept /api/v1/clients to return MORE than 1 client · avoid auto-redirect.
    await authedPage.route("**/api/v1/clients", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([
          {
            id: "11111111-1111-1111-1111-111111111111",
            nombre: "Cliente Test 1",
            cif: "A11111111",
            sector: "aapp",
            rag: "green",
            contacto_email: "c1@test.com",
            contacto_telefono: null,
            created_at: "2025-01-01T00:00:00Z",
          },
          {
            id: "22222222-2222-2222-2222-222222222222",
            nombre: "Cliente Test 2",
            cif: "B22222222",
            sector: "finanzas",
            rag: "amber",
            contacto_email: "c2@test.com",
            contacto_telefono: null,
            created_at: "2025-01-15T00:00:00Z",
          },
        ]),
      });
    });

    await authedPage.goto("/admin/projects");
    await authedPage.waitForLoadState("domcontentloaded");
    // Wait for client cards to render
    await authedPage.locator("[data-testid='projects-grid']").waitFor({
      timeout: 5000,
    }).catch(() => {});

    const result = await runFullPolishSweep(authedPage, {
      pageUrl: "/admin/projects",
      pageName: "admin-projects-selector",
      isProjectScoped: false,
    });

    // Attach evidence FIRST (Path B 3-point commitment EMPIRICAL).
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
    expect(result.criteria.titleBreadcrumb, "title visible").toBe(true);

    expect(result.passCount).toBeGreaterThanOrEqual(9);
  });
});
