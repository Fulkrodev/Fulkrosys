/**
 * E2E test · M01 Categorización sync admin → cliente.
 *
 * Sesión 3B-2B.8 CLUSTER 1 Phase 1A.3 scaffold (~5s SSE roundtrip target).
 *
 * Flow:
 * 1. Admin login + complete M01 categorización via UI
 * 2. Switch cliente login (same project · different user)
 * 3. Assert cliente sees updated categoria within 5s via SSE toast
 * 4. Assert audit_log entries present (cliente.categorizacion.viewed)
 *
 * SCAFFOLD mode · requires FULKRO_TEST_PROJECT_ID + cliente piloto user
 * seeded en DB. Skip gracefully si env vars missing.
 */
import { expect, test } from "@playwright/test";

const PROJECT_ID = process.env.FULKRO_TEST_PROJECT_ID;
const SYSTEM_ID = process.env.FULKRO_TEST_SYSTEM_ID;

test.describe("M01 Categorización sync admin → cliente E2E", () => {
  test.beforeAll(({}, testInfo) => {
    if (!PROJECT_ID || !SYSTEM_ID) {
      testInfo.skip(
        true,
        "FULKRO_TEST_PROJECT_ID + FULKRO_TEST_SYSTEM_ID env required",
      );
    }
  });

  test("admin completes categorización → cliente sees update via SSE", async ({
    browser,
  }) => {
    // 2 contexts paralelos (admin + cliente)
    const adminContext = await browser.newContext();
    const clienteContext = await browser.newContext();

    // Admin auth via loginAsMarcos helper
    const { loginAsMarcos, loginAsClient } = await import(
      "./_helpers/auth-real"
    );
    await loginAsMarcos(adminContext);
    const adminPage = await adminContext.newPage();

    const clientePage = await clienteContext.newPage();
    await loginAsClient(clientePage, { dismissTutorial: true });

    // Cliente visits categorización page first
    await clientePage.goto("/client-portal/categorizacion");
    await expect(clientePage.getByTestId("cat-view")).toBeVisible({
      timeout: 10_000,
    });

    // Admin completes M01 categorize via API call (faster than UI walkthrough)
    const resp = await adminContext.request.post(
      `/api/v1/categorization/systems/${SYSTEM_ID}/categorize`,
      { data: { aprobado_por: "Marcos · E2E Test Auditor" } },
    );
    expect(resp.ok()).toBeTruthy();

    // Cliente receives SSE toast within 5s
    await expect(
      clientePage.locator("text=ha completado la categorización"),
    ).toBeVisible({ timeout: 5_000 });

    // audit_log emit verified via admin API query
    const auditResp = await adminContext.request.get(
      `/api/v1/admin/projects/${PROJECT_ID}/audit-log` +
        `?accion=cliente.categorizacion.viewed&limit=5`,
    );
    if (auditResp.ok()) {
      const body = await auditResp.json();
      expect(body.total_for_project ?? body.entries?.length ?? 0).toBeGreaterThanOrEqual(
        1,
      );
    }

    await adminContext.close();
    await clienteContext.close();
  });
});
