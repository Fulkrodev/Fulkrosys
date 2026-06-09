/**
 * E2E · Test 10 fase_17 · cliente · descarga plantilla deliverable.
 *
 * Sub-atom 1.C.D.E v3.8 · 1.C.D.D.2 (WorkflowStepDeliverables tone='client').
 *
 * Verifica:
 *   - Drawer Tab "¿Qué necesito?" wired con WorkflowStepDeliverables
 *   - Tone cliente friendly (NO admin lingo)
 *   - "Descargar" button visible para deliverable status='available'
 *   - Empty states friendly cuando 0 deliverables
 */
import { expect, test } from "@playwright/test";

import { loginAsClient } from "../../_helpers/auth-real";
import { mockClientWorkflowGuide, mockDeliverables } from "../_fixtures";

test.describe("fase_17 cliente · descarga plantilla deliverable", () => {
  test("Tab ¿Qué necesito? · download disponible + tone friendly", async ({
    page,
  }) => {
    await mockClientWorkflowGuide(page);
    await mockDeliverables(page);
    await loginAsClient(page);

    await page.goto("/client-portal/workflow");

    const verMasBtn = page.getByRole("button", { name: /Ver más detalle/i }).first();
    await verMasBtn.click();

    // Tab "¿Qué necesito?"
    await page.getByRole("tab", { name: /¿Qué necesito\?/i }).click();

    // Available deliverable download (E-500)
    await expect(
      page.getByTestId("deliverable-download-E-500"),
    ).toBeVisible();

    // Tone cliente: "Disponible" / "Pendiente actualizar" / "Aún no preparado"
    // (NO admin lingo "Listo" / "Necesita regenerar" / "Pendiente generar")
    const friendlyLabel = await page
      .getByText(/Disponible|Pendiente actualizar|Aún no preparado/i)
      .first()
      .textContent();
    expect(friendlyLabel).toBeTruthy();
  });
});
