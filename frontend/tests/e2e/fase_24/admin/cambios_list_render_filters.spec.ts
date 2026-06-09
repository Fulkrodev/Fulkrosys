/**
 * E2E · Test 3 fase_24 · admin · ChangesList render + filters.
 *
 * Sub-atom 1.D.D.B v3.11 · M28 Change Governance refactor page.
 *
 * Verifica:
 *   - Login admin · /admin/projects/{id}/changes render ChangesList (NEW)
 *   - 2 mock changes visibles (1 assessed · 1 intake)
 *   - Filters estado (Todos · Intake · Evaluados · etc)
 *   - Filter "intake" reduces a 1
 *   - Botón "Solicitar cambio" abre wizard 5 steps
 */
import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "../../_helpers/auth-real";
import {
  CHANGE_ID,
  PROJECT_DD_ID,
  mockChangesListBase,
} from "../_fixtures";

test.describe("fase_24 admin · ChangesList render + filters", () => {
  test("2 changes mock visible + filtros + wizard abrible", async ({
    context,
    page,
  }) => {
    await loginAsMarcos(context);
    await mockChangesListBase(page);

    await page.goto(`/admin/projects/${PROJECT_DD_ID}/changes`);

    // List visible
    await expect(page.getByTestId("changes-list")).toBeVisible();

    // 2 mock rows
    await expect(page.getByTestId(`changes-row-${CHANGE_ID}`)).toBeVisible();
    await expect(
      page.getByTestId(`changes-row-ch000002-aaaa-bbbb-cccc-000000000002`),
    ).toBeVisible();

    // Filters
    await expect(page.getByTestId("changes-filters")).toBeVisible();
    await expect(page.getByTestId("changes-filter-all")).toBeVisible();
    await expect(page.getByTestId("changes-filter-intake")).toBeVisible();
    await expect(page.getByTestId("changes-filter-assessed")).toBeVisible();

    // Click "intake" filter reduces a 1
    await page.getByTestId("changes-filter-intake").click();
    await expect(
      page.getByTestId(`changes-row-ch000002-aaaa-bbbb-cccc-000000000002`),
    ).toBeVisible();
    await expect(
      page.getByTestId(`changes-row-${CHANGE_ID}`),
    ).not.toBeVisible();

    // Botón "Solicitar cambio" abre wizard
    await page.getByTestId("changes-request-button").click();
    await expect(page.getByTestId("change-request-wizard")).toBeVisible();
  });
});
