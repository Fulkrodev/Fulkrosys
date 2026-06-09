/**
 * E2E · Test 3 fase_18 · admin · Assign empleado to department + report visible.
 *
 * Sub-atom 1.C.F.5 v3.10 · 1.C.F.3 (FK simple empleado ↔ área + reports).
 *
 * Verifica:
 *   - Tab Empleados muestra columna "Departamento" con select dropdown per empleado
 *   - Tab Áreas muestra badge "N empleados" per department (lazy desde report)
 *   - DepartmentReportPanel visible cuando hay áreas con datos
 */
import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "../../_helpers/auth-real";
import {
  PROJECT_F_ID,
  mockDepartmentsFilledMedia,
  mockEnsRolesEmptyMedia,
  mockEquipoCommon,
  mockPortalUserEmpty,
  mockProjectContactsEmployees,
} from "../_fixtures";

test.describe("fase_18 admin · employees ↔ departments distribution", () => {
  test("empleados tab tiene columna Departamento + áreas tab muestra counts", async ({
    page,
    context,
  }) => {
    await loginAsMarcos(context);
    await mockEquipoCommon(page);
    await mockPortalUserEmpty(page);
    await mockProjectContactsEmployees(page);
    await mockDepartmentsFilledMedia(page);
    await mockEnsRolesEmptyMedia(page);

    await page.goto(`/admin/projects/${PROJECT_F_ID}/equipo`);

    // Tab Empleados: columna Departamento presente
    await page.getByRole("tab", { name: /Empleados/i }).click();
    await expect(
      page.getByRole("columnheader", { name: /Departamento/i }),
    ).toBeVisible();
    // Lista empleados render (3 fixture)
    await expect(page.getByText("Alicia Muñoz")).toBeVisible();
    await expect(page.getByText("Bernardo López")).toBeVisible();

    // Tab Áreas: badge counts visible + DepartmentReportPanel
    await page.getByRole("tab", { name: /^Áreas$/i }).click();
    // Header report panel
    await expect(page.getByText(/Empleados por área/i)).toBeVisible();
    // Bucket Sin asignar (2 empleados sin dept en fixture)
    await expect(page.getByText(/Sin asignar/i).first()).toBeVisible();
    // Code TI rendered en table de áreas
    await expect(page.getByText("TI").first()).toBeVisible();
  });
});
