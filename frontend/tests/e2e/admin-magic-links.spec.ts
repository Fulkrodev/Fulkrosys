/**
 * E2E admin magic-links (FASE 4.5 sub-bloque B.2 · remodelado Phase X.4e).
 *
 * El panel cross-cliente /admin/magic-links es hoy un redirect a /admin/projects:
 * el generador manual + el histórico se movieron a la vista project-scoped
 * /admin/projects/[id]/auditor-handoff ("Entrega al auditor"). Esta spec cubre
 * el mismo generador en su ubicación actual:
 * 1. /admin/magic-links redirige · auditor-handoff muestra los 2 tabs
 * 2. El select de purposes se agrupa por categorías (sin "Deprecated")
 * 3. Generación de un INVITACION_REUNION con campos mínimos · success state
 *
 * Pattern: loginAsMarcos(context) + mockProjectShell + page.route mocks.
 */
import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "./_helpers/auth-real";
import { mockProjectShell } from "./_helpers/project-shell";

const PROJECT_ID = "11111111-1111-4111-8111-111111111111";
const CLIENT_ID = "22222222-2222-4222-8222-222222222222";

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

test.describe("Admin Magic Links · entrega al auditor", () => {
  let generateBody: Record<string, unknown> | null = null;

  test.beforeEach(async ({ context, page }) => {
    generateBody = null;
    await loginAsMarcos(context);
    await mockProjectShell(page, { projectId: PROJECT_ID, clientId: CLIENT_ID });
    // Histórico vacío por defecto; /generate devuelve el enlace mock.
    await page.route("**/api/v1/magic-links**", async (route) => {
      const url = route.request().url();
      if (url.includes("/generate")) {
        generateBody = route.request().postDataJSON() as Record<string, unknown>;
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

  test("/admin/magic-links redirige y auditor-handoff muestra ambos tabs", async ({
    page,
  }) => {
    await page.goto("/admin/magic-links");
    await expect(page).toHaveURL(/\/admin\/projects$/);

    await page.goto(`/admin/projects/${PROJECT_ID}/auditor-handoff`);
    await expect(
      page.getByRole("heading", { name: "Entrega al auditor", level: 1 }),
    ).toBeVisible();
    await expect(
      page.getByRole("tab", { name: "Generar enlace auditor" }),
    ).toBeVisible();
    await page.getByRole("tab", { name: "Histórico enlaces" }).click();
    await expect(page.getByText("Histórico de enlaces")).toBeVisible();
  });

  test("generator form opens and shows purposes grouped by category", async ({
    page,
  }) => {
    await page.goto(`/admin/projects/${PROJECT_ID}/auditor-handoff`);
    await expect(page.getByText("Generar enlace seguro")).toBeVisible();

    await page.getByRole("combobox", { name: /tipo de operación/i }).click();
    const listbox = page.getByRole("listbox");
    for (const cat of [
      "Onboarding y acceso",
      "Firma documental",
      "Evidencias y verificación",
      "Comunicación y reporting",
      "Cierre y descargas",
    ]) {
      await expect(listbox.getByText(cat, { exact: true })).toBeVisible();
    }
    await expect(listbox.getByText("Deprecated", { exact: true })).toHaveCount(0);
  });

  test("admin generates magic link for INVITACION_REUNION", async ({ page }) => {
    await page.goto(`/admin/projects/${PROJECT_ID}/auditor-handoff`);
    await page.getByLabel("Proyecto (UUID)").fill(PROJECT_ID);
    await page.getByLabel("Cliente (UUID)").fill(CLIENT_ID);
    await page.getByRole("combobox", { name: /tipo de operación/i }).click();
    await page
      .getByRole("option", { name: "Confirmar asistencia a reunion" })
      .click();
    await page.getByLabel(/email destinatario/i).fill("test@example.com");
    await page.getByRole("button", { name: /generar \(copiar enlace\)/i }).click();

    const result = page.getByRole("alert").filter({ hasText: "Enlace generado" });
    await expect(result).toBeVisible({ timeout: 10_000 });
    await expect(result.getByText(MOCK_GENERATED_LINK.id)).toBeVisible();
    expect(generateBody).toMatchObject({
      project_id: PROJECT_ID,
      purpose: "invitacion_reunion",
      recipient_email: "test@example.com",
    });
  });
});
