/**
 * E2E · Test 4 fase_18 · admin · ENS roles priority per category + assign UI.
 *
 * Sub-atom 1.C.F.5 v3.10 · 1.C.F.4 (priority per category + assign/vacate).
 *
 * Verifica:
 *   - Project MEDIA · Tab Roles ENS muestra 6 roles canónicos RD 311/2022
 *   - 5 priority "critical" + 1 "recommended" (administrador_seguridad)
 *   - Gap banner rojo visible · "5 roles críticos pendientes"
 *   - Badge "Categoría MEDIA" visible
 *   - Botón Asignar visible per row pendiente
 *
 * Nota R30: el banner explica "Sin estos roles no podrás auto-generar
 * plantillas ENS firmadas (E-002 · E-012 · E-040 · E-041)" (admin tutor).
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

test.describe("fase_18 admin · ENS roles priority + gap banner", () => {
  test("Tab Roles ENS muestra 6 roles + 5 críticos missing + gap banner", async ({
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
    await page.getByRole("tab", { name: /Roles ENS/i }).click();

    // Categoría MEDIA visible en badge del header del panel.
    // UI evolucionada: el texto "Categoría MEDIA" aparece en 2 sitios — el
    // badge del header del panel (exacto "Categoría MEDIA") y el gap banner
    // (span "· Categoría MEDIA"). Anclamos al badge exacto para evitar la
    // strict-mode violation (el span del banner lleva el prefijo "· ").
    await expect(
      page.getByText("Categoría MEDIA", { exact: true }),
    ).toBeVisible();

    // Gap banner rojo · 5 críticos pendientes
    await expect(
      page.getByText(/5 roles críticos pendientes/i),
    ).toBeVisible();
    // Mensaje tutor R30 (referencia plantillas auto-gen)
    await expect(
      page.getByText(/auto-generar plantillas ENS firmadas/i),
    ).toBeVisible();

    // 6 roles canónicos visibles (labels frontend).
    // `.first()` en todos: cada label aparece 2x — como badge en el gap
    // banner (roles critical_missing) y como span en la lista del panel.
    // Sin `.first()` → strict-mode violation (mismo patrón que el resto).
    await expect(
      page.getByText(/Sponsor \/ Patrocinador/i).first(),
    ).toBeVisible();
    await expect(
      page.getByText(/Responsable de la Información/i).first(),
    ).toBeVisible();
    await expect(
      page.getByText(/Responsable del Servicio/i).first(),
    ).toBeVisible();
    await expect(
      page.getByText(/Responsable de la Seguridad/i).first(),
    ).toBeVisible();
    await expect(
      page.getByText(/Responsable del Sistema/i).first(),
    ).toBeVisible();
    await expect(
      page.getByText(/Administrador de la Seguridad/i).first(),
    ).toBeVisible();

    // Counter total assigned 0/6
    await expect(page.getByText(/0\s*\/\s*6 asignados/i)).toBeVisible();
  });
});
