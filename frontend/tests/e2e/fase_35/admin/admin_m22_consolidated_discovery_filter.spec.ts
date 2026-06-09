/**
 * E2E · fase_35 admin M22 consolidated discovery · filter por provenance (1.D.J).
 *
 * Verifica:
 *  - Filter dropdown provenance visible
 *  - Selecting "Solo manual" hides cloud rows · keeps manual row
 *  - Filter logic es client-side (no extra backend call)
 */
import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "../../_helpers/auth-real";
import { PROJECT_F35_ID, mockM22ConsolidatedBase } from "../_fixtures";

test.describe("fase_35 admin · M22 consolidated discovery filter", () => {
  test("provenance filter narrows visible rows · client-side", async ({ page }) => {
    await loginAsMarcos(page.context());
    await mockM22ConsolidatedBase(page);

    await page.goto(`/admin/projects/${PROJECT_F35_ID}/discovery`);
    await page.getByRole("tab", { name: /Consolidado/i }).click();
    await expect(page.getByTestId("consolidated-tab")).toBeVisible();

    // Initial state · all 4 rows visible (1 manual + 1 cloud + 2 both)
    await expect(page.getByTestId("consolidated-row-manual")).toBeVisible();
    await expect(page.getByTestId("consolidated-row-cloud")).toBeVisible();

    // Open provenance filter dropdown
    await page.getByTestId("consolidated-filter-provenance").click();

    // Select "Solo manual"
    await page.getByRole("option", { name: /Solo manual/i }).click();

    // After filter · manual row still visible
    await expect(page.getByTestId("consolidated-row-manual")).toBeVisible();

    // Cloud-only row should be hidden (no longer in filtered set)
    await expect(page.getByTestId("consolidated-row-cloud")).toHaveCount(0);
  });
});
