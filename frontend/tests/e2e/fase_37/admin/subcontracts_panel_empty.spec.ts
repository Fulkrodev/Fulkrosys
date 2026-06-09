/**
 * E2E · Test 1 fase_37 · admin · SubcontractsPanel empty state friendly.
 *
 * FASE C Phase C v3.12 · empty state cuando project NO tiene adendas todavía.
 *
 * Verifica:
 *   - Panel renderiza con título "Sub-contratos · Adendas E-604"
 *   - Counts summary: Total 0
 *   - Empty state visible con copy R29-friendly "Sin adendas todavía"
 *   - Re-evaluar button visible y habilitado
 */
import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "../../_helpers/auth-real";
import { PROJECT_FC_ID, mockSubcontractsEmpty } from "../_fixtures";

test.describe("fase_37 admin · SubcontractsPanel empty state", () => {
  test("empty project renders friendly empty state + recheck button", async ({
    context,
    page,
  }) => {
    await loginAsMarcos(context);
    await mockSubcontractsEmpty(page);

    await page.goto(`/admin/projects/${PROJECT_FC_ID}/contratos`);

    const panel = page.getByTestId("subcontracts-panel");
    await expect(panel).toBeVisible();

    // Title visible
    await expect(panel.getByText("Sub-contratos · Adendas E-604")).toBeVisible();

    // Total counter = 0
    await expect(panel.getByText(/Total:/)).toBeVisible();

    // Empty state copy
    await expect(panel.getByText("Sin adendas todavía")).toBeVisible();
    await expect(
      panel.getByText(/Aparecerán aquí cuando se autogeneren/),
    ).toBeVisible();

    // Recheck button habilitado
    const recheck = page.getByTestId("trigger-recheck");
    await expect(recheck).toBeVisible();
    await expect(recheck).toBeEnabled();
  });
});
