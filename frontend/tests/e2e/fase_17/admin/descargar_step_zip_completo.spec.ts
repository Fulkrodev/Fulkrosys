/**
 * E2E · Test 5 fase_17 · admin · descargar bulk ZIP per step.
 *
 * Sub-atom 1.C.D.E v3.8 · 1.C.D.D.1 (endpoint bulk-zip StreamingResponse).
 *
 * Verifica:
 *   - Drawer Tab Deliverables visible "Descargar todos (ZIP)" cuando counts.available > 0
 *   - Anchor href apunta a endpoint bulk-zip correcto
 *   - StreamingResponse contiene ZIP attachment (verificado vía endpoint URL)
 */
import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "../../_helpers/auth-real";
import {
  PROJECT_A_ID,
  mockAdminWorkflowCommandCenter,
  mockDeliverables,
} from "../_fixtures";

test.describe("fase_17 admin · descargar step ZIP completo", () => {
  test("bulk ZIP button visible + href apunta a backend endpoint", async ({
    page,
    context,
  }) => {
    await loginAsMarcos(context);
    await mockAdminWorkflowCommandCenter(page);
    await mockDeliverables(page);

    await page.goto(`/admin/workflow-command-center/projects/${PROJECT_A_ID}`);

    const detalleBtn = page.getByRole("button", { name: /Ver detalle/i }).first();
    await detalleBtn.click();

    await page.getByRole("tab", { name: /Entregas/i }).click();

    // Bulk ZIP button visible · data-testid="deliverables-bulk-zip"
    const bulkAnchor = page.getByTestId("deliverables-bulk-zip");
    await expect(bulkAnchor).toBeVisible();

    // Href apunta a backend endpoint bulk-zip
    const href = await bulkAnchor.getAttribute("href");
    expect(href).toContain("workflow-engine/steps/");
    expect(href).toContain("/deliverables/bulk-zip");
    expect(href).toContain(PROJECT_A_ID);
  });
});
