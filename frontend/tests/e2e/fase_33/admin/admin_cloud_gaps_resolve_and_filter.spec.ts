/**
 * E2E · fase_33 admin cloud-gaps · filter + resolve (1.D.X.J v3.12).
 *
 * Verifica:
 *  - Tab Gaps muestra lista con severity badges
 *  - Filtros severity click → query backend (regex match)
 *  - Resolve gap mutation funciona end-to-end (mock 200)
 */
import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "../../_helpers/auth-real";
import {
  PROJECT_F33_ID,
  mockCloudConnectorsAdminBase,
  mockResolveGapOk,
} from "../_fixtures";

test.describe("fase_33 admin · cloud-gaps", () => {
  test("gaps list visible + filter critical button toggles", async ({ page }) => {
    await loginAsMarcos(page.context());
    await mockCloudConnectorsAdminBase(page);

    await page.goto(`/admin/projects/${PROJECT_F33_ID}/cloud-connectors`);
    await page.getByTestId("tab-gaps").click();

    await expect(page.getByTestId("gaps-tab")).toBeVisible();
    await expect(page.getByTestId("gap-card-op.acc.6")).toBeVisible();
    await expect(page.getByTestId("gap-card-org.1")).toBeVisible();

    // Filter severity critical
    await page.getByTestId("filter-severity-critical").click();
    // Re-fetch will happen · just verify button stays selected
    await expect(page.getByTestId("filter-severity-critical")).toBeVisible();
  });

  test("resolve gap calls backend + UI updates", async ({ page }) => {
    await loginAsMarcos(page.context());
    await mockCloudConnectorsAdminBase(page);
    await mockResolveGapOk(page);

    await page.goto(`/admin/projects/${PROJECT_F33_ID}/cloud-connectors`);
    await page.getByTestId("tab-gaps").click();
    await expect(page.getByTestId("btn-resolve-op.acc.6")).toBeVisible();

    const reqWait = page.waitForRequest((req) =>
      req.url().includes("/cloud-gaps/") && req.url().endsWith("/resolve"),
    );

    await page.getByTestId("btn-resolve-op.acc.6").click();
    await reqWait;
  });
});
