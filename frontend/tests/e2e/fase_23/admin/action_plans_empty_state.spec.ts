/**
 * E2E · Test 2 fase_23 · admin · Empty state cuando 0 findings.
 *
 * Sub-atom 1.D.C v3.11 · Dashboard K.3 empty state.
 *
 * Verifica:
 *   - Backend returns total_count=0 items=[] · panel render
 *   - Empty state visible "Sin findings prioritarios"
 *   - Counts summary NO visible (NO total)
 */
import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "../../_helpers/auth-real";
import { mockActionPlansEmpty, PROJECT_EE_ID } from "../_fixtures";

test.describe("fase_23 admin · ActionPlansPanel empty state", () => {
  test("0 findings · empty state friendly visible", async ({
    context,
    page,
  }) => {
    await loginAsMarcos(context);
    await mockActionPlansEmpty(page);

    await page.goto(`/admin/projects/${PROJECT_EE_ID}/planes-accion`);

    await expect(page.getByTestId("action-plans-panel")).toBeVisible();

    // Empty state title visible
    await expect(
      page.getByText(/Sin findings prioritarios/i),
    ).toBeVisible();

    // List NO visible (vacía)
    await expect(page.getByTestId("action-plans-list")).not.toBeVisible();
  });
});
