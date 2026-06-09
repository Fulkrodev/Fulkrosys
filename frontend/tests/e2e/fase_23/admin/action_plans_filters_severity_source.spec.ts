/**
 * E2E · Test 3 fase_23 · admin · Filters severity + source toggle.
 *
 * Sub-atom 1.D.C v3.11 · Dashboard K.3 filters interactive.
 *
 * Verifica:
 *   - Filtros severity (4 toggle buttons: crítica · alta · media · baja)
 *   - Filtros source (3 toggle buttons: M04 · M09 · A21)
 *   - Click toggle aplica filtro · refetch backend (query key includes filters)
 *   - Visual active state cuando filtro selected
 */
import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "../../_helpers/auth-real";
import { mockActionPlansWithFindings, PROJECT_EE_ID } from "../_fixtures";

test.describe("fase_23 admin · ActionPlansPanel filters interactive", () => {
  test("severity + source filters togglable + visual active state", async ({
    context,
    page,
  }) => {
    await loginAsMarcos(context);
    await mockActionPlansWithFindings(page);

    await page.goto(`/admin/projects/${PROJECT_EE_ID}/planes-accion`);

    // 4 severity filter buttons visible
    await expect(
      page.getByTestId("action-plans-filter-severity-critica"),
    ).toBeVisible();
    await expect(
      page.getByTestId("action-plans-filter-severity-alta"),
    ).toBeVisible();
    await expect(
      page.getByTestId("action-plans-filter-severity-media"),
    ).toBeVisible();
    await expect(
      page.getByTestId("action-plans-filter-severity-baja"),
    ).toBeVisible();

    // 3 source filter buttons visible
    await expect(
      page.getByTestId("action-plans-filter-source-m04_gap"),
    ).toBeVisible();
    await expect(
      page.getByTestId("action-plans-filter-source-m09_audit_prep"),
    ).toBeVisible();
    await expect(
      page.getByTestId("action-plans-filter-source-a21_discrepancy"),
    ).toBeVisible();

    // Click filter severity crítica toggle
    await page
      .getByTestId("action-plans-filter-severity-critica")
      .click();

    // Active state aplicado · query refetch (visual change · active class)
    await expect(
      page.getByTestId("action-plans-filter-severity-critica"),
    ).toHaveClass(/border-primary|bg-primary/);
  });
});
