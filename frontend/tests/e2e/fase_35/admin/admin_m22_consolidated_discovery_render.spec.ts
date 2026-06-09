/**
 * E2E · fase_35 admin M22 consolidated discovery · render (1.D.J K-full v3.12).
 *
 * Verifica:
 *  - Page /admin/projects/{id}/discovery renderiza
 *  - Click Tab "Consolidado" muestra ConsolidatedTab
 *  - KPI cards 4 bucket (total · manual_only · cloud_only · both)
 *  - Asset list rendered con badges per provenance
 */
import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "../../_helpers/auth-real";
import { PROJECT_F35_ID, mockM22ConsolidatedBase } from "../_fixtures";

test.describe("fase_35 admin · M22 consolidated discovery render", () => {
  test("Tab Consolidado renders KPI cards + asset list", async ({ page }) => {
    await loginAsMarcos(page.context());
    await mockM22ConsolidatedBase(page);

    await page.goto(`/admin/projects/${PROJECT_F35_ID}/discovery`);

    // Click "Consolidado" tab (default tab is "Activos")
    await page.getByRole("tab", { name: /Consolidado/i }).click();

    // ConsolidatedTab rendered
    await expect(page.getByTestId("consolidated-tab")).toBeVisible();

    // KPI counts container
    await expect(page.getByTestId("consolidated-counts")).toBeVisible();
    await expect(page.getByTestId("consolidated-counts")).toContainText("4"); // total
    await expect(page.getByTestId("consolidated-counts")).toContainText("1"); // manual_only

    // Asset list rendered (4 rows: 1 manual + 1 cloud + 2 both)
    await expect(page.getByTestId("consolidated-list")).toBeVisible();
    await expect(page.getByTestId("consolidated-row-manual")).toBeVisible();
    await expect(page.getByTestId("consolidated-row-cloud")).toBeVisible();
    // both appears 2x · check at least one visible
    await expect(page.getByTestId("consolidated-row-both").first()).toBeVisible();
  });
});
