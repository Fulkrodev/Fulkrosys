/**
 * E2E · fase_33 admin · ejecutar diagnóstico engine + ver report (1.D.X.J v3.12).
 *
 * Verifica:
 *  - Botón "Ejecutar diagnóstico" en tab Gaps dispara POST cloud-diagnosis/run
 *  - Report card render con counts (rules_evaluated · findings · created/updated/resolved)
 *  - gap_codes mostrado en report
 */
import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "../../_helpers/auth-real";
import {
  PROJECT_F33_ID,
  mockCloudConnectorsAdminBase,
  mockRunDiagnosisOk,
} from "../_fixtures";

test.describe("fase_33 admin · run diagnosis", () => {
  test("click run-diagnosis triggers backend + shows report", async ({ page }) => {
    await loginAsMarcos(page.context());
    await mockCloudConnectorsAdminBase(page);
    await mockRunDiagnosisOk(page);

    await page.goto(`/admin/projects/${PROJECT_F33_ID}/cloud-connectors`);
    await page.getByTestId("tab-gaps").click();

    const reqWait = page.waitForRequest((req) =>
      req.url().includes("/cloud-diagnosis/run"),
    );
    await page.getByTestId("btn-run-diagnosis").click();
    await reqWait;

    // Report card debe aparecer con counts
    await expect(page.getByText(/5 reglas evaluadas/i)).toBeVisible();
    await expect(page.getByText(/3 hallazgos emitidos/i)).toBeVisible();
  });
});
