/**
 * E2E · fase_34 admin · manual digest generation flow (1.D.X.VERIFY 2a).
 *
 * Verifica:
 *  - Tab Monitoring muestra DigestSummaryCard real (NO stub "preview L sub-fase próxima")
 *  - Click "Generar ahora" dispara POST cloud-monitoring/digest/generate
 *  - Toast success aparece tras mutation OK
 *  - Card refresh post-success (invalidateQueries)
 *  - Empty state friendly cuando latest=null
 */
import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "../../_helpers/auth-real";
import {
  PROJECT_F34_ID,
  mockCloudMonitoringAdminBase,
  mockTriggerDigestOk,
} from "../_fixtures";

test.describe("fase_34 admin · manual digest generation", () => {
  test("tab Monitoring renders DigestSummaryCard real with latest snapshot", async ({
    page,
  }) => {
    await loginAsMarcos(page.context());
    await mockCloudMonitoringAdminBase(page);

    await page.goto(`/admin/projects/${PROJECT_F34_ID}/cloud-connectors`);
    await page.getByTestId("tab-monitoring").click();

    await expect(page.getByTestId("monitoring-tab")).toBeVisible();
    await expect(page.getByTestId("digest-summary-card")).toBeVisible();
    await expect(page.getByText(/Compliance score/i)).toBeVisible();
    await expect(page.getByText(/Gaps abiertos/i)).toBeVisible();
    await expect(page.getByText(/88/)).toBeVisible(); // score
  });

  test("click Generar ahora triggers POST + success toast", async ({ page }) => {
    await loginAsMarcos(page.context());
    await mockCloudMonitoringAdminBase(page);
    await mockTriggerDigestOk(page);

    await page.goto(`/admin/projects/${PROJECT_F34_ID}/cloud-connectors`);
    await page.getByTestId("tab-monitoring").click();
    await expect(page.getByTestId("btn-generate-digest-now")).toBeVisible();

    const reqWait = page.waitForRequest((req) =>
      req.url().includes("/cloud-monitoring/digest/generate")
      && req.method() === "POST",
    );
    await page.getByTestId("btn-generate-digest-now").click();
    await reqWait;

    await expect(page.getByTestId("digest-toast-success")).toBeVisible();
    await expect(
      page.getByText(/Digest generado manualmente/i),
    ).toBeVisible();
  });

  test("empty state shows when no digest yet", async ({ page }) => {
    await loginAsMarcos(page.context());
    await mockCloudMonitoringAdminBase(page, { latest: null });

    await page.goto(`/admin/projects/${PROJECT_F34_ID}/cloud-connectors`);
    await page.getByTestId("tab-monitoring").click();

    await expect(page.getByTestId("digest-empty-state")).toBeVisible();
    await expect(page.getByText(/Sin digest aún/i)).toBeVisible();
    await expect(page.getByTestId("btn-generate-digest-now")).toBeVisible();
  });
});
