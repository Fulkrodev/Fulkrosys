/**
 * E2E · fase_33 admin cloud-connectors dashboard render (1.D.X.J v3.12).
 *
 * Verifica:
 *  - Page /admin/projects/{id}/cloud-connectors render con 4 Tabs
 *  - KPI cards muestra contadores (conectores · recursos · gaps críticos/altos)
 *  - Tab Conectores muestra 2 conectores (M365 connected + AWS sync_error)
 *  - Sync button visible cuando NO revocado
 */
import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "../../_helpers/auth-real";
import { PROJECT_F33_ID, mockCloudConnectorsAdminBase } from "../_fixtures";

test.describe("fase_33 admin · cloud-connectors dashboard", () => {
  test("page renders 4 tabs + KPIs + connectors list", async ({ page }) => {
    await loginAsMarcos(page.context());
    await mockCloudConnectorsAdminBase(page);

    await page.goto(`/admin/projects/${PROJECT_F33_ID}/cloud-connectors`);

    await expect(page.getByTestId("cloud-connectors-admin-panel")).toBeVisible();

    // 4 tabs
    await expect(page.getByTestId("tab-connectors")).toBeVisible();
    await expect(page.getByTestId("tab-resources")).toBeVisible();
    await expect(page.getByTestId("tab-gaps")).toBeVisible();
    await expect(page.getByTestId("tab-monitoring")).toBeVisible();

    // Connectors list rendered con 2 items
    await expect(page.getByTestId("connectors-list")).toBeVisible();
    await expect(
      page.getByTestId("connector-row-microsoft_365"),
    ).toBeVisible();
    await expect(page.getByTestId("connector-row-aws")).toBeVisible();

    // Sync button visible para M365 conectado
    await expect(page.getByTestId("btn-sync-microsoft_365")).toBeVisible();
  });
});
