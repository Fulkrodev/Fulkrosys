/**
 * Auditor portal full E2E flow · CLUSTER 3 Phase C5.1.
 *
 * Comprehensive 9-step empirical flow cross CLUSTER 2 + 3:
 *   1. Auditor entry via magic link AUDITOR_PORTAL_ENAC
 *   2. Navigate 9 read-only views (Phase 5)
 *   3. Create 3 annotations · 3 severities (Phase C1)
 *   4. Request 2 clarifications · 2 priorities (Phase C2)
 *   5. Admin respond clarifications via /admin (Phase C2)
 *   6. Auditor review DdA-evidence gaps heatmap (Phase C3)
 *   7. Auditor generate draft audit report PDF (Phase C4)
 *   8. Admin review draft history (Phase C4)
 *   9. Verify audit_log emit per critical action (R6 hash chain)
 *
 * SCAFFOLD mode (current): spec collect-clean. Runtime requires
 *   AUDITOR_PORTAL_TOKEN env (real magic link generated por backend) +
 *   FULKRO_TEST_PROJECT_ID env (test project con dummy data).
 *
 * Pattern mirror Phase 5.10 polish/auditor-portal/* specs.
 */
import { expect, test } from "@playwright/test";

const TOKEN = process.env.AUDITOR_PORTAL_TOKEN;
const PROJECT_ID = process.env.FULKRO_TEST_PROJECT_ID;

test.describe("Auditor portal · full E2E flow CLUSTER 2 + 3", () => {
  test.beforeAll(({}, testInfo) => {
    if (!TOKEN || !PROJECT_ID) {
      testInfo.skip(
        true,
        "AUDITOR_PORTAL_TOKEN + FULKRO_TEST_PROJECT_ID env required",
      );
    }
  });

  test("step 1: auditor portal entry + branding propagated", async ({
    page,
  }) => {
    await page.goto(`/auditor-portal/${TOKEN}/summary`);
    await expect(page.getByTestId("auditor-summary-view")).toBeVisible({
      timeout: 10_000,
    });
    await expect(page.getByTestId("auditor-summary-categoria")).toBeVisible();
  });

  test("step 2: navigate 9 read-only views", async ({ page }) => {
    const sections = [
      "summary",
      "dda",
      "magerit",
      "plan",
      "evidence",
      "e041",
      "audit-log",
      "pentest",
      "documents",
    ];
    for (const section of sections) {
      await page.goto(`/auditor-portal/${TOKEN}/${section}`);
      // Each view exposes a unique data-testid suffix matching section
      const viewTestId = `auditor-${section.replace("audit-log", "audit-log").replace("-", "-")}-view`;
      await page.waitForLoadState("networkidle", { timeout: 5000 }).catch(() => {});
      // Lenient: at least chrome loaded
      await expect(page.locator('[data-testid="auditor-portal-main"]')).toBeVisible();
    }
  });

  test("step 3: create 3 annotations (one per severity)", async ({ page }) => {
    await page.goto(`/auditor-portal/${TOKEN}/dda`);
    // Use DdA view first medida row · click "Anotar" inline panel
    const severities = ["info", "warning", "critical"];
    for (const severity of severities) {
      const annotateBtn = page
        .getByTestId(/^auditor-annotate-medida-/)
        .first();
      await annotateBtn.click();
      await page.getByTestId("auditor-annotation-severity").click();
      await page.getByRole("option", { name: severity, exact: false }).click();
      await page
        .getByTestId("auditor-annotation-textarea")
        .fill(`Test annotation severity=${severity}`);
      await page.getByTestId("auditor-annotation-submit").click();
      await page.waitForTimeout(500);
    }
  });

  test("step 4: request 2 clarifications (urgent + normal)", async ({
    page,
  }) => {
    await page.goto(`/auditor-portal/${TOKEN}/summary`);
    // Topbar ClarificationButton always available cross-views
    const priorities = ["urgent", "normal"];
    for (const priority of priorities) {
      const clarBtn = page
        .getByTestId(/^auditor-clarification-button-general/)
        .first();
      await clarBtn.click();
      await page.getByTestId("auditor-clarification-priority").click();
      await page.getByRole("option", { name: priority, exact: false }).click();
      await page
        .getByTestId("auditor-clarification-textarea")
        .fill(`Test clarification priority=${priority}`);
      await page.getByTestId("auditor-clarification-submit").click();
      await page.waitForTimeout(500);
    }
  });

  test("step 5: admin responds clarifications", async ({
    browser,
  }) => {
    const context = await browser.newContext();
    // loginAsMarcos para admin endpoints require_owner
    const { loginAsMarcos } = await import("./_helpers/auth-real");
    await loginAsMarcos(context);
    const adminPage = await context.newPage();
    await adminPage.goto(
      `/admin/projects/${PROJECT_ID}/audit/clarifications`,
    );
    await expect(
      adminPage.getByTestId("admin-clarifications-inbox"),
    ).toBeVisible();
    const firstCard = adminPage
      .locator('[data-testid^="admin-clarification-card-"]')
      .first();
    await expect(firstCard).toBeVisible();
    const cardId = await firstCard.getAttribute("data-testid");
    if (cardId) {
      const id = cardId.replace("admin-clarification-card-", "");
      await adminPage
        .getByTestId(`admin-clarification-response-${id}`)
        .fill("Respuesta admin test E2E");
      await adminPage
        .getByTestId(`admin-clarification-submit-${id}`)
        .click();
      await adminPage.waitForTimeout(500);
    }
    await context.close();
  });

  test("step 6: review DdA-evidence gaps heatmap + drawer", async ({
    page,
  }) => {
    await page.goto(`/auditor-portal/${TOKEN}/audit/dda-evidence-gaps`);
    await expect(page.getByTestId("gap-view")).toBeVisible({
      timeout: 10_000,
    });
    await expect(page.getByTestId("gap-coverage-pct")).toBeVisible();
    // Click first medida cell to open drawer
    const firstCell = page.locator('[data-testid^="gap-medida-cell-"]').first();
    await firstCell.click();
    await expect(page.getByTestId("gap-medida-drawer")).toBeVisible();
    await page.getByTestId("gap-drawer-close").click();
  });

  test("step 7: auditor generates draft audit report PDF", async ({
    page,
  }) => {
    await page.goto(`/auditor-portal/${TOKEN}/draft-report`);
    await expect(page.getByTestId("draft-report-view")).toBeVisible({
      timeout: 10_000,
    });
    await expect(page.getByTestId("draft-preview-iframe")).toBeVisible();
    await page
      .getByTestId("draft-opinion-textarea")
      .fill("Opinión preliminar E2E test");
    const downloadPromise = page.waitForEvent("download", { timeout: 30_000 });
    await page.getByTestId("draft-generate-button").click();
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toMatch(/borrador_auditoria.*\.pdf/);
  });

  test("step 8: admin reviews draft report page", async ({ browser }) => {
    const context = await browser.newContext();
    const { loginAsMarcos } = await import("./_helpers/auth-real");
    await loginAsMarcos(context);
    const adminPage = await context.newPage();
    await adminPage.goto(
      `/admin/projects/${PROJECT_ID}/audit/draft-report`,
    );
    await expect(
      adminPage.getByTestId("draft-report-admin-view"),
    ).toBeVisible();
    await expect(
      adminPage.getByTestId("draft-admin-preview-iframe"),
    ).toBeVisible();
    await context.close();
  });

  test("step 9: verify audit_log emit per critical action", async ({
    request,
  }) => {
    // Fetch audit log CSV con auditor token (Phase 6 endpoint)
    const csvResp = await request.get(
      `/api/v1/public/auditor-portal/${TOKEN}/audit-log.csv?limit=500`,
    );
    expect(csvResp.ok()).toBeTruthy();
    const csvBody = await csvResp.text();
    const expectedEvents = [
      "auditor.session.start",
      "auditor_portal.view",
      "auditor.annotation.created",
      "auditor.clarification.requested",
      "admin.clarification.responded",
      "auditor.view.dda_evidence_gaps",
      "auditor.draft_report.generated",
    ];
    for (const ev of expectedEvents) {
      expect(csvBody).toContain(ev);
    }
  });
});
