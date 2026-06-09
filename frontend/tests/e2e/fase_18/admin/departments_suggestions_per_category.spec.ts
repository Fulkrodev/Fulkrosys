/**
 * E2E · Test 2 fase_18 · admin · Departments suggestions per category MEDIA.
 *
 * Sub-atom 1.C.F.5 v3.10 · 1.C.F.2.1 (suggestions ENS-aware) +
 * 1.C.F.2.2 (admin Tab Áreas + sub-route).
 *
 * Verifica:
 *   - Project MEDIA · 0 departments → SuggestionsBanner visible
 *   - Banner muestra 2 suggestions canónicas (TI · COMPLIANCE)
 *   - R28 materializado · adaptación per categoría ENS visible empíricamente
 */
import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "../../_helpers/auth-real";
import {
  PROJECT_F_ID,
  mockDepartmentsEmptyMedia,
  mockEnsRolesEmptyMedia,
  mockEquipoCommon,
  mockPortalUserEmpty,
  mockProjectContactsEmployees,
} from "../_fixtures";

test.describe("fase_18 admin · departments suggestions per category MEDIA", () => {
  test("renders suggestions banner with 2 items (TI + COMPLIANCE)", async ({
    page,
    context,
  }) => {
    await loginAsMarcos(context);
    await mockEquipoCommon(page);
    await mockPortalUserEmpty(page);
    await mockProjectContactsEmployees(page);
    await mockDepartmentsEmptyMedia(page);
    await mockEnsRolesEmptyMedia(page);

    await page.goto(`/admin/projects/${PROJECT_F_ID}/equipo`);

    // Activar Tab Áreas
    await page.getByRole("tab", { name: /^Áreas$/i }).click();

    // Banner suggestions visible · MEDIA suggestions = 2 (TI + COMPLIANCE)
    await expect(
      page.getByText(/Tecnologías de la Información/i).first(),
    ).toBeVisible();
    await expect(
      page.getByText(/Compliance \+ RGPD/i).first(),
    ).toBeVisible();

    // Botón crear manual visible
    await expect(
      page.getByRole("button", { name: /\+ Nueva área/i }),
    ).toBeVisible();
  });
});
