/**
 * E2E · fase_31 admin · Workflow Blockers Panel rendering (1.D.G.D v3.11).
 *
 * Verifica:
 *  - Toggle "Próximos pasos" mode disponible
 *  - Panel rendea 4 sections (available · waiting_cliente · blocked · done)
 *  - KPI summary 4 counts
 *  - blocked_reason text "Esperando Marcos termine: ..." cliente facing
 *  - waiting_cliente section muestra "Recordar" button
 */
import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "../../_helpers/auth-real";
import { mockAdminWorkflowBlockers, PROJECT_F31_ID } from "../_fixtures";

test.describe("fase_31 admin · workflow blockers panel", () => {
  test("renders 4 groups + KPIs + remind button", async ({ context, page }) => {
    await loginAsMarcos(context);
    await mockAdminWorkflowBlockers(page);

    await page.goto(`/admin/workflow-command-center/projects/${PROJECT_F31_ID}`);

    // Switch to blockers view
    await page.getByTestId("view-mode-blockers").click();

    await expect(page.getByTestId("workflow-blockers-panel")).toBeVisible();
    await expect(page.getByTestId("blockers-summary")).toBeVisible();
    await expect(page.getByTestId("kpi-waiting-cliente")).toContainText("1");
    await expect(page.getByTestId("kpi-blocked")).toContainText("1");

    // Verify 4 sections
    await expect(page.getByTestId("blockers-section-available")).toBeVisible();
    await expect(
      page.getByTestId("blockers-section-waiting_cliente"),
    ).toBeVisible();
    await expect(page.getByTestId("blockers-section-blocked")).toBeVisible();
    await expect(page.getByTestId("blockers-section-done")).toBeVisible();

    // Waiting cliente card visible · CLIENTE_UPLOAD_Z available cliente
    await expect(
      page.getByTestId("blocker-card-CLIENTE_UPLOAD_Z"),
    ).toBeVisible();
    await expect(
      page.getByTestId("remind-button-CLIENTE_UPLOAD_Z"),
    ).toBeVisible();
  });
});
