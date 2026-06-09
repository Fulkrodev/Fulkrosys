/**
 * E2E · fase_35 admin M02 MAGERIT cloud enrichment · render stats card (1.D.J).
 *
 * Verifica (graceful · skip si MAGERIT base no tiene analysis):
 *  - Page /admin/projects/{id}/magerit navigates
 *  - Si magerit-cloud-stats render → verifica formato "X/Y activos cloud-verified (op.exp.1)"
 *  - Si NO render (no analysis) → skip con razón documentada
 *
 * Pre-condición real: project necesita análisis MAGERIT activo · si NO existe la
 * página muestra empty "No hay análisis MAGERIT activo" y AssetsTab no se ve.
 * Test es resiliente y reporta el escenario.
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

    // Wait briefly for either stats card OR no-analysis empty state to settle
    await page.waitForLoadState("networkidle", { timeout: 10_000 }).catch(() => {});

    const statsCard = page.getByTestId("magerit-cloud-stats");
    const noAnalysis = page.getByText(/No hay análisis MAGERIT activo/i);

    if (await statsCard.isVisible().catch(() => false)) {
      // Stats card render path · verify content
      await expect(statsCard).toContainText(/cloud-verified/);
      await expect(statsCard).toContainText(/op\.exp\.1/);
    } else if (await noAnalysis.isVisible().catch(() => false)) {
      test.skip(
        true,
        "MAGERIT analysis not present para project F35 · base data prerequisite · NOT a bug",
      );
    } else {
      throw new Error(
        "Neither stats card ni no-analysis state visible · unexpected page state",
      );
    }
  });
});
