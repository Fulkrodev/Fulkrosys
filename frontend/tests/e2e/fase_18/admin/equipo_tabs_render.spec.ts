/**
 * E2E · Test 1 fase_18 · admin · Equipo del proyecto · 4 Tabs render.
 *
 * Sub-atom 1.C.F.5 v3.10 (cierre 1.C.F) · 1.C.F.1 baseline · 1.C.F.2/3/4 wired.
 *
 * Verifica:
 *   - Login admin · /admin/projects/{id}/equipo/ render OK
 *   - Header "Equipo del proyecto" visible
 *   - 4 TabsTrigger visibles: Usuario portal · Empleados · Áreas · Roles ENS
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

test.describe("fase_18 admin · /equipo/ render 4 tabs", () => {
  test("renders header + 4 Tabs + button nuevo empleado", async ({
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

    await expect(
      page.getByRole("heading", { name: /Equipo del proyecto/i }),
    ).toBeVisible();

    // 4 Tabs como triggers
    await expect(
      page.getByRole("tab", { name: /Usuario portal/i }),
    ).toBeVisible();
    await expect(
      page.getByRole("tab", { name: /Empleados/i }),
    ).toBeVisible();
    await expect(page.getByRole("tab", { name: /^Áreas$/i })).toBeVisible();
    await expect(
      page.getByRole("tab", { name: /Roles ENS/i }),
    ).toBeVisible();

    // Tab Empleados activable
    await page.getByRole("tab", { name: /Empleados/i }).click();
    await expect(
      page.getByRole("button", { name: /\+ Nuevo empleado/i }),
    ).toBeVisible();
  });
});
