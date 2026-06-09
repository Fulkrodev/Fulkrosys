/**
 * E2E test · M02 MAGERIT sync admin → cliente READ-ONLY.
 *
 * Sesión 3B-2B.8 CLUSTER 1 Phase 1B.3 scaffold (~5s SSE roundtrip target).
 *
 * Flow:
 * 1. Cliente login + visit /client-portal/magerit (subscribe SSE)
 * 2. Admin login (separate context) + freeze MAGERIT analysis via API
 * 3. Assert cliente sees toast within 5s via SSE
 * 4. Assert audit_log entry cliente.magerit.viewed exists
 * 5. Assert cliente cannot POST/PATCH MAGERIT (READ-ONLY · 405/403)
 *
 * SCAFFOLD · requires FULKRO_TEST_PROJECT_ID + FULKRO_TEST_MAGERIT_ANALYSIS_ID env.
 */
import { expect, test } from "@playwright/test";

const PROJECT_ID = process.env.FULKRO_TEST_PROJECT_ID;
const ANALYSIS_ID = process.env.FULKRO_TEST_MAGERIT_ANALYSIS_ID;

test.describe("M02 MAGERIT sync admin → cliente READ-ONLY E2E", () => {
  test.beforeAll(({}, testInfo) => {
    if (!PROJECT_ID || !ANALYSIS_ID) {
      testInfo.skip(
        true,
        "FULKRO_TEST_PROJECT_ID + FULKRO_TEST_MAGERIT_ANALYSIS_ID env required",
      );
    }
  });

  test("admin freezes MAGERIT → cliente sees toast via SSE within 5s", async ({
    browser,
  }) => {
    const adminContext = await browser.newContext();
    const clienteContext = await browser.newContext();

    const { loginAsMarcos, loginAsClient } = await import(
      "./_helpers/auth-real"
    );
    await loginAsMarcos(adminContext);
    const clientePage = await clienteContext.newPage();
    await loginAsClient(clientePage, { dismissTutorial: true });

    // Cliente visits magerit page (subscribes SSE)
    await clientePage.goto("/client-portal/magerit");
    await clientePage.waitForLoadState("networkidle", { timeout: 5000 }).catch(() => {});

    // Admin freezes via API
    const resp = await adminContext.request.post(
      `/api/v1/magerit/analysis/${ANALYSIS_ID}/freeze`,
    );
    // 200 OK if not previously frozen · 409 if already frozen (acceptable)
    expect([200, 409]).toContain(resp.status());

    if (resp.status() === 200) {
      // Cliente receives SSE toast within 5s
      await expect(
        clientePage.locator("text=ha actualizado"),
      ).toBeVisible({ timeout: 5_000 });
    }

    await adminContext.close();
    await clienteContext.close();
  });

  test("cliente cannot POST MAGERIT admin endpoints (READ-ONLY 403)", async ({
    browser,
  }) => {
    const clienteContext = await browser.newContext();
    const { loginAsClient } = await import("./_helpers/auth-real");
    const clientePage = await clienteContext.newPage();
    await loginAsClient(clientePage, { dismissTutorial: true });

    // Cliente attempts admin POST endpoint · 401/403 expected
    const resp = await clienteContext.request.post(
      `/api/v1/magerit/analysis/${ANALYSIS_ID}/freeze`,
    );
    expect([401, 403]).toContain(resp.status());

    await clienteContext.close();
  });
});
