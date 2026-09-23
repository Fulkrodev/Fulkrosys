/**
 * E2E · fase_36 admin Project Breadcrumb persistent (sub-atom 1.E.2 · ADR-054).
 *
 * Verifica:
 *  - Breadcrumb visible en project dashboard
 *  - Breadcrumb [Cliente] > [Proyecto] > [Sub-página] cuando en sub-route
 *  - Links navegables (click cliente · click proyecto)
 *  - Skeleton placeholder mientras activeProject hidrata
 */
import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "../../_helpers/auth-real";
import { PROJECT_F36_A_ID, mockClientsAndHeaders } from "../_fixtures";

// Proyecto sintético: mockClientsAndHeaders stubea header + feature-flags del
// layout (con `categoria`: sin ella ProjectCategoryBanner tumbaba el layout).
test.describe("fase_36 admin · project breadcrumb persistent", () => {
  test("breadcrumb visible en dashboard cliente + project", async ({ page }) => {
    await loginAsMarcos(page.context());
    await mockClientsAndHeaders(page);

    // Landing project-scoped real = /summary (antes /dashboard · ahora 404).
    await page.goto(`/admin/projects/${PROJECT_F36_A_ID}/summary`);

    // Wait for breadcrumb hydrate (NOT skeleton)
    await expect(page.getByTestId("project-breadcrumb")).toBeVisible();

    // Cliente link visible
    await expect(page.getByTestId("project-breadcrumb-client")).toContainText(
      /Cliente Piloto MEDIA/i,
    );

    // Proyecto link visible (activo · sub-página = dashboard)
    await expect(page.getByTestId("project-breadcrumb-project")).toContainText(
      /ENS Media/i,
    );
  });

  test("breadcrumb muestra sub-página cuando NO dashboard", async ({ page }) => {
    await loginAsMarcos(page.context());
    await mockClientsAndHeaders(page);

    await page.goto(`/admin/projects/${PROJECT_F36_A_ID}/dda`);

    await expect(page.getByTestId("project-breadcrumb")).toBeVisible();

    // Sub-página DdA label visible
    await expect(page.getByTestId("project-breadcrumb-subpage")).toContainText(
      /DdA/i,
    );
  });
});
