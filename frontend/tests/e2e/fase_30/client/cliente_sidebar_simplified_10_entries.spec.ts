/**
 * E2E · fase_30 cliente · Sidebar simplified en 4 secciones.
 *
 * Sub-atom 1.D.F.bis.III.D v3.11 · actualizado auditoría 2026-06-07.
 *
 * El sidebar PRINCIPAL se amplió (auditoría 2026-06-07): páginas antes
 * huérfanas en el nav (Incidentes · Actas · DPC anual · Mi certificación ·
 * Mejoras propuestas · Mi plan ENS · Cumplimiento) ahora SÍ tienen entrada,
 * para que el cliente las alcance sin URL directa. Ver ClientSidebar.tsx.
 *
 * Verifica:
 *  - 4 sections rendered (Principal sin label + Mi empresa + Comunicación + Mi cuenta)
 *  - Entries clave presentes (incl. las re-añadidas al nav)
 *  - Label de subida = "Subir documentos" (NO "Subir evidencias"/"Mi proyecto")
 *  - Logout footer separate
 */
import { expect, test } from "@playwright/test";

import { loginAsClient } from "../../_helpers/auth-real";
import { mockClienteIndispensable } from "../_fixtures";

test.describe("fase_30 cliente · sidebar simplified", () => {
  test("entries clave en 4 secciones + label subida correcto", async ({
    page,
  }) => {
    await loginAsClient(page);
    await mockClienteIndispensable(page);

    await page.goto("/client-portal/dashboard");

    await expect(page.getByTestId("cliente-sidebar")).toBeVisible();

    // Sección PRINCIPAL (no label · primer bloque)
    await expect(page.getByTestId("cliente-nav-inicio")).toBeVisible();
    await expect(page.getByTestId("cliente-nav-mis-tareas")).toBeVisible();
    await expect(
      page.getByTestId("cliente-nav-firmas-pendientes"),
    ).toBeVisible();
    // Label real de subida = "Subir documentos" (NO "Subir evidencias").
    await expect(
      page.getByTestId("cliente-nav-subir-documentos"),
    ).toBeVisible();
    // Páginas re-añadidas al nav (auditoría 2026-06-07): ahora SÍ alcanzables.
    await expect(page.getByTestId("cliente-nav-incidentes")).toBeVisible();
    await expect(page.getByTestId("cliente-nav-actas")).toBeVisible();
    await expect(page.getByTestId("cliente-nav-dpc-anual")).toBeVisible();

    // Sección MI EMPRESA
    await expect(
      page.getByTestId("cliente-nav-section-mi-empresa"),
    ).toBeVisible();
    await expect(page.getByTestId("cliente-nav-onboarding")).toBeVisible();
    await expect(page.getByTestId("cliente-nav-facturación")).toBeVisible();

    // Sección COMUNICACIÓN
    await expect(
      page.getByTestId("cliente-nav-section-comunicación"),
    ).toBeVisible();
    await expect(page.getByTestId("cliente-nav-chat-con-marcos")).toBeVisible();
    await expect(page.getByTestId("cliente-nav-mensajes")).toBeVisible();
    await expect(page.getByTestId("cliente-nav-whatsapp")).toBeVisible();

    // Sección MI CUENTA + logout footer
    await expect(
      page.getByTestId("cliente-nav-section-mi-cuenta"),
    ).toBeVisible();
    await expect(page.getByTestId("cliente-nav-mi-cuenta")).toBeVisible();
    await expect(page.getByTestId("cliente-nav-logout")).toBeVisible();

    // "Mi proyecto" fue renombrado/eliminado · ya NO existe como entrada.
    await expect(page.getByText(/^Mi proyecto$/)).not.toBeVisible();
  });
});
