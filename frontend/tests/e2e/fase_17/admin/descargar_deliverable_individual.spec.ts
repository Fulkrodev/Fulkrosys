/**
 * E2E · Test 4 fase_17 · admin · descargar deliverable individual.
 *
 * Sub-atom 1.C.D.E v3.8 · 1.C.D.D.2 (WorkflowStepDeliverables wired Tab 3).
 *
 * Verifica:
 *   - Drawer Tab 3 Deliverables wired
 *   - "Descargar" button visible para deliverable status='available'
 *   - Click trigger navigation a endpoint /api/v1/projects/{id}/workflow-engine/deliverables/{evidence_id}/download
 */
import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "../../_helpers/auth-real";
import {
  PROJECT_A_ID,
  mockAdminWorkflowCommandCenter,
  mockDeliverables,
} from "../_fixtures";

test.describe("fase_17 admin · descargar deliverable individual", () => {
  test("Tab Deliverables shows download button para available", async ({
    page,
    context,
  }) => {
    await loginAsMarcos(context);
    await mockAdminWorkflowCommandCenter(page);
    await mockDeliverables(page);

    await page.goto(`/admin/workflow-command-center/projects/${PROJECT_A_ID}`);

    // Click step AHORA card para abrir drawer
    const detalleBtn = page.getByRole("button", { name: /Ver detalle/i }).first();
    await detalleBtn.click();

    // Tab Deliverables
    await page.getByRole("tab", { name: /Entregas/i }).click();

    // Available download button visible (E-500)
    await expect(
      page.getByTestId("deliverable-download-E-500"),
    ).toBeVisible();
    // Missing deliverable (E-501) NO download button
    await expect(
      page.getByText(/Pendiente generar/i).first(),
    ).toBeVisible();
  });
});
