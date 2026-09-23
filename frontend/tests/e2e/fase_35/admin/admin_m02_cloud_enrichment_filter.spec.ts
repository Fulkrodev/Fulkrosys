/**
 * E2E · fase_35 admin M02 MAGERIT cloud enrichment · filter "Solo cloud-verified" (1.D.J).
 *
 * Verifica (análisis MAGERIT + vista enriquecida mockeados · 2 cloud + 1 manual):
 *  - Checkbox magerit-filter-cloud-verified visible con la stats card
 *  - Toggle ON oculta las filas manuales y deja las cloud-verified
 *  - Toggle OFF restaura la tabla completa
 */
import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "../../_helpers/auth-real";
import { PROJECT_F35_ID, mockM02EnrichedBase } from "../_fixtures";

test.describe("fase_35 admin · M02 MAGERIT cloud enrichment filter", () => {
  test("Solo cloud-verified toggle changes table visibility", async ({ page }) => {
    await loginAsMarcos(page.context());
    await mockM02EnrichedBase(page);

    await page.goto(`/admin/projects/${PROJECT_F35_ID}/magerit`);

    const filter = page.getByTestId("magerit-filter-cloud-verified");
    const manualRows = page.getByTestId("magerit-row-manual");
    const cloudRows = page.getByTestId("magerit-row-cloud-verified");

    await expect(filter).toBeVisible();
    await expect(cloudRows).toHaveCount(2);
    await expect(manualRows).toHaveCount(1);

    // Toggle ON · solo cloud-verified
    await filter.check();
    await expect(filter).toBeChecked();
    await expect(manualRows).toHaveCount(0);
    await expect(cloudRows).toHaveCount(2);

    // Toggle OFF · vuelve la fila manual
    await filter.uncheck();
    await expect(filter).not.toBeChecked();
    await expect(manualRows).toHaveCount(1);
    await expect(cloudRows).toHaveCount(2);
  });
});
