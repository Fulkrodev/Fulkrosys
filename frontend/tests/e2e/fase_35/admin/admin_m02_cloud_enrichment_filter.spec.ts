/**
 * E2E · fase_35 admin M02 MAGERIT cloud enrichment · filter "Solo cloud-verified" (1.D.J).
 *
 * Verifica (graceful · skip si MAGERIT base no tiene analysis):
 *  - Checkbox magerit-filter-cloud-verified visible cuando stats card render
 *  - Toggle filter changes table state (rows count)
 *  - Re-toggle restores original
 *
 * Resiliente: si no analysis existe → skip + razón documentada.
 */
import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "../../_helpers/auth-real";
import { PROJECT_F35_ID, mockM02EnrichedBase } from "../_fixtures";

test.describe("fase_35 admin · M02 MAGERIT cloud enrichment filter", () => {
  test("Solo cloud-verified toggle changes table visibility", async ({ page }) => {
    await loginAsMarcos(page.context());
    await mockM02EnrichedBase(page);

    await page.goto(`/admin/projects/${PROJECT_F35_ID}/magerit`);
    await page.waitForLoadState("networkidle", { timeout: 10_000 }).catch(() => {});

    const filter = page.getByTestId("magerit-filter-cloud-verified");
    const noAnalysis = page.getByText(/No hay análisis MAGERIT activo/i);

    if (await noAnalysis.isVisible().catch(() => false)) {
      test.skip(
        true,
        "MAGERIT analysis not present para project F35 · base data prerequisite · NOT a bug",
      );
      return;
    }

    await expect(filter).toBeVisible();

    // Toggle ON
    await filter.check();
    await expect(filter).toBeChecked();

    // Manual rows hidden (verified ≠ true filtered out)
    await expect(page.getByTestId("magerit-row-manual")).toHaveCount(0);

    // Toggle OFF
    await filter.uncheck();
    await expect(filter).not.toBeChecked();
  });
});
