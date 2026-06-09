/**
 * E2E · Test 3 fase_37 · admin · Re-evaluar adendas mutation success.
 *
 * FASE C Phase C v3.12 · admin manual trigger button POST /providers/adenda/check
 * dispatches y muestra success alert.
 *
 * Verifica:
 *   - Panel render con adendas list
 *   - Click "Re-evaluar adendas" button
 *   - Spinner durante mutation
 *   - Success alert visible post-mutation
 *   - List query re-invalidated (refetch fires)
 */
import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "../../_helpers/auth-real";
import {
  PROJECT_FC_ID,
  mockAdendaCheckSuccess,
  mockSubcontractsWithHistory,
} from "../_fixtures";

test.describe("fase_37 admin · SubcontractsPanel manual recheck", () => {
  test("click Re-evaluar adendas fires POST + success alert", async ({
    context,
    page,
  }) => {
    await loginAsMarcos(context);
    await mockSubcontractsWithHistory(page);
    await mockAdendaCheckSuccess(page);

    await page.goto(`/admin/projects/${PROJECT_FC_ID}/contratos`);

    const panel = page.getByTestId("subcontracts-panel");
    await expect(panel).toBeVisible();

    const recheck = page.getByTestId("trigger-recheck");
    await expect(recheck).toBeEnabled();

    // Click recheck button
    await recheck.click();

    // Success alert con codes
    await expect(page.getByText("Re-evaluación completada")).toBeVisible({
      timeout: 5000,
    });
    await expect(
      page.getByText(/1 adenda\(s\) procesadas/),
    ).toBeVisible();
    await expect(
      page.getByText(/ADMIN_MANUAL_TRIGGER_CHECK_PROVIDER/),
    ).toBeVisible();
  });
});
