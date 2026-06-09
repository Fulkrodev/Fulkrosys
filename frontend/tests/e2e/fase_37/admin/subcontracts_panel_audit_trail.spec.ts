/**
 * E2E · Test 2 fase_37 · admin · SubcontractsPanel render con 3 adendas
 * audit trail visible cross-triggers.
 *
 * FASE C Phase C v3.12 · cubre 3 distinct triggers:
 *   - workflow_step_completed + materiality_material_cascade (chain history)
 *   - admin_manual (con admin_user_id)
 *   - manual fallback (legacy sin metadata)
 *
 * Verifica:
 *   - Panel render con counts per trigger
 *   - 3 adenda-row visibles
 *   - Trigger badges distintos visibles
 *   - Audit trail toggle expande triggers_history per row
 *   - Normativas badges visibles (ENS · RGPD · NIS2)
 */
import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "../../_helpers/auth-real";
import {
  PROJECT_FC_ID,
  mockSubcontractsWithHistory,
} from "../_fixtures";

test.describe("fase_37 admin · SubcontractsPanel audit trail visible", () => {
  test("3 adendas distinct triggers + history expandable", async ({
    context,
    page,
  }) => {
    await loginAsMarcos(context);
    await mockSubcontractsWithHistory(page);

    await page.goto(`/admin/projects/${PROJECT_FC_ID}/contratos`);

    const panel = page.getByTestId("subcontracts-panel");
    await expect(panel).toBeVisible();

    // Counts visible
    await expect(panel.getByText(/Total:/)).toBeVisible();
    await expect(panel.getByText("Cambio material M28: 1")).toBeVisible();
    await expect(panel.getByText("Admin manual: 1")).toBeVisible();
    await expect(panel.getByText("Manual (legacy): 1")).toBeVisible();

    // 3 adenda rows visibles
    const rows = page.getByTestId("adenda-row");
    await expect(rows).toHaveCount(3);

    // Codes visibles
    await expect(page.getByText("ADENDA-ENS-2026-0001")).toBeVisible();
    await expect(page.getByText("ADENDA-ENS-2026-0002")).toBeVisible();
    await expect(page.getByText("ADENDA-ENS-2026-0003")).toBeVisible();

    // Normativas badges en primera adenda (ENS + RGPD + NIS2)
    const firstRow = page.locator('[data-adenda-code="ADENDA-ENS-2026-0001"]');
    await expect(firstRow.getByText("ENS").first()).toBeVisible();
    await expect(firstRow.getByText("RGPD").first()).toBeVisible();
    await expect(firstRow.getByText("NIS2").first()).toBeVisible();

    // Firmado cliente badge primera adenda
    await expect(firstRow.getByText("Firmado cliente")).toBeVisible();

    // Click audit trail toggle primera adenda
    const firstToggle = firstRow.getByTestId("audit-trail-toggle");
    await firstToggle.click();

    // History debe ser visible · 2 eventos
    const history = firstRow.getByTestId("audit-trail-history");
    await expect(history).toBeVisible();
    await expect(history.getByText(/Trazabilidad ENAC \(2 eventos\)/)).toBeVisible();

    // Entry 1: workflow_step_completed con template id
    const entries = firstRow.getByTestId("audit-trail-entry");
    await expect(entries).toHaveCount(2);
    await expect(
      history.getByText(/ARCHETYPE_PROVEEDOR_FINANCIERO_DORA_DUAL/),
    ).toBeVisible();

    // Entry 2: materiality_material_cascade con flags
    await expect(history.getByText(/Materialidad/)).toBeVisible();
    await expect(history.getByText(/overlay \+ renewal/)).toBeVisible();
  });
});
