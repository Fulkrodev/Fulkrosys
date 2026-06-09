/**
 * E2E admin magic-links panel (FASE 4.5 sub-bloque B.2).
 *
 * Cobertura smoke 3 specs (los 35 specs FR14.8/FR18.9 completos van a FASE 14):
 * 1. Navegación a /admin/magic-links · header + tabs (Generar / Histórico)
 * 2. Tab Generar renderiza el select agrupado por categorías de purposes
 * 3. Generación de un INVITACION_REUNION con campos mínimos · success state
 *
 * Pattern post-MF3.5: mockAuthenticated(page) + page.route mocks · canónico
 * con admin-clients.spec.ts y verification.spec.ts.
 */
import { expect, test } from "@playwright/test";

import { mockAuthenticated } from "./helpers";

const PROJECT_ID = "11111111-1111-1111-1111-111111111111";

const MOCK_GENERATED_LINK = {
  id: "00000000-0000-0000-0000-aaaaaaaaaaaa",
  project_id: PROJECT_ID,
  tipo_operacion: "invitacion_reunion",
  recipient_email: "test@example.com",
  cc_emails: null,
  custom_subject: null,
  expira_at: "2026-12-31T00:00:00Z",
  max_usos: 1,
  usos: 0,
  revocado: false,
  revoked_at: null,
  sent_to_contact_id: null,
  created_at: "2026-05-01T10:00:00Z",
};

// SKIP: feature eliminada (panel cross-cliente /admin/magic-links con generador
// de 35 purposes + tabs Generar/Histórico). La ruta /admin/magic-links ahora hace
// redirect() server-side hacia /admin/projects (consolidación · Sesión 3B-2B.3
// Phase X.4e). El generador manual se redujo a 3 auditor-purposes bajo
// /admin/projects/[id]/auditor-handoff; el resto de purposes los auto-generan los
// motores. Ningún heading "Enlaces seguros"/"Generar enlace seguro" ni los tabs
// existen ya en /admin/magic-links. Candidata a borrar tras contraste (Marcos).
test.describe.skip("Admin Magic Links", () => {
  test.beforeEach(async ({ page }) => {
    await mockAuthenticated(page);
    // Lista vacía por defecto (tab Histórico no necesita data en B.2 smoke).
    await page.route("**/api/v1/magic-links*", async (route) => {
      const url = route.request().url();
      if (url.includes("/generate")) {
        return route.fulfill({
          status: 201,
          contentType: "application/json",
          body: JSON.stringify(MOCK_GENERATED_LINK),
        });
      }
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([]),
      });
    });
  });

  test("admin navigates to /admin/magic-links and sees both tabs", async ({
    page,
  }) => {
    await page.goto("/admin/magic-links");
    await expect(page.getByRole("heading", { name: "Enlaces seguros" })).toBeVisible();
    await expect(page.getByRole("tab", { name: "Generar nuevo" })).toBeVisible();
    await expect(page.getByRole("tab", { name: "Histórico" })).toBeVisible();
  });

  test("generator form opens and shows purposes grouped by category", async ({
    page,
  }) => {
    await page.goto("/admin/magic-links");
    await expect(
      page.getByRole("heading", { name: "Generar enlace seguro" }),
    ).toBeVisible();

    // Open the purpose select
    await page.getByRole("combobox", { name: /tipo de operación/i }).click();

    // 5 categorías visibles (Onboarding · Firma · Evidencias · Comunicación ·
    // Cierre); "Deprecated" filtrada del select.
    for (const cat of [
      "Onboarding y acceso",
      "Firma documental",
      "Evidencias y verificación",
      "Comunicación y reporting",
      "Cierre y descargas",
    ]) {
      await expect(page.getByText(cat, { exact: true })).toBeVisible();
    }
    // Deprecated NO visible
    await expect(page.getByText("Deprecated", { exact: true })).not.toBeVisible();
  });

  test("admin generates magic link for INVITACION_REUNION", async ({ page }) => {
    await page.goto("/admin/magic-links");
    await page.getByLabel(/proyecto/i).fill(PROJECT_ID);
    await page.getByRole("combobox", { name: /tipo de operación/i }).click();
    await page.getByRole("option", { name: "Confirmar asistencia a reunion" }).click();
    await page.getByLabel(/email destinatario/i).fill("test@example.com");
    await page.getByRole("button", { name: /generar enlace/i }).click();

    await expect(page.getByText("Enlace generado")).toBeVisible({
      timeout: 10_000,
    });
    await expect(
      page.getByText(MOCK_GENERATED_LINK.id),
    ).toBeVisible();
  });
});
