/**
 * E2E · fase_35 admin M02 MAGERIT cloud enrichment · render stats card (1.D.J).
 *
 * Verifica (análisis MAGERIT + vista enriquecida mockeados · 2 de 3 cloud):
 *  - Page /admin/projects/{id}/magerit navega y pinta la tabla de activos
 *  - magerit-cloud-stats muestra "2/3 activos cloud-verified (op.exp.1)"
 *  - La celda Cloud muestra el proveedor detectado
 */
import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "../../_helpers/auth-real";
import { PROJECT_F35_ID, mockM02EnrichedBase } from "../_fixtures";

test.describe("fase_35 admin · M02 MAGERIT cloud enrichment render", () => {
  test("stats card visible cuando MAGERIT analysis exists · format X/Y cloud-verified", async ({
    page,
  }) => {
    await loginAsMarcos(page.context());
    await mockM02EnrichedBase(page);

    await page.goto(`/admin/projects/${PROJECT_F35_ID}/magerit`);

    const statsCard = page.getByTestId("magerit-cloud-stats");
    await expect(statsCard).toBeVisible();
    await expect(statsCard).toContainText("2/3");
    await expect(statsCard).toContainText(/activos cloud-verified \(op\.exp\.1\)/);

    const table = page.getByTestId("magerit-assets-table");
    await expect(table.getByText("Servidor de aplicaciones")).toBeVisible();
    await expect(
      page.getByTestId("magerit-row-cloud-verified").filter({ hasText: "aws" }),
    ).toHaveCount(1);
  });
});
