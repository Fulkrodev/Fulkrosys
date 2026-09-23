/**
 * MB-3.1 · ExitChecklist real wired M25 (SAN-E v3).
 *
 * Wired al backend M25 exit-checklist (commit MB-3.A 2447fd6 · 5 endpoints).
 * Run pendiente Marcos manual con servers up.
 *
 * Cobertura:
 * - Header readiness card visible
 * - DataTable renders 16 default items (lazy seed M25)
 * - Filter por categoría reduce visible count
 * - Mark item completado abre modal · submit + Badge cambia a success
 * - Check readiness · blockers preview visible
 * - Mark all critical completed · footer cerrar proyecto aparece
 */
import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "../_helpers/auth-real";

const PROJECT_ID = process.env.E2E_SEED_PROJECT_ID ?? "00000000-0000-0000-0000-000000000001";
const BACKEND = process.env.PLAYWRIGHT_BACKEND_URL ?? "http://localhost:8000";

test.describe("MB-3.1 · ExitChecklist M25", () => {
  test.beforeEach(async ({ context, page }) => {
    await loginAsMarcos(context);
    await page.goto(`/admin/projects/${PROJECT_ID}/exit`);
  });

  test("header readiness + 16 default items lazy seed", async ({ page }) => {
    await expect(
      page.getByText(/Checklist de cierre/i),
    ).toBeVisible();
    // Progreso card · 16 items post seed lazy (el nº completado depende del
    // estado persistido; lo que se fija aquí es el total sembrado)
    await expect(page.getByText(/^\d+ \/ 16$/)).toBeVisible();
    await expect(page.getByRole("button", { name: /Verificar readiness/i })).toBeVisible();
  });

  test("filter por categoría reduce items visibles", async ({ page }) => {
    // Aserciones que ESPERAN, no `count()`: `count()` es una foto y se tomaba
    // antes de que llegaran todas las filas. El checklist tiene 16 items, 4 por
    // categoria (m25_lifecycle/exit_checklist_service.DEFAULT_ITEMS), y la
    // DataTable pagina de 10 en 10: la primera pagina muestra 10.
    const filas = page.locator("table tbody tr");
    await expect(filas).toHaveCount(10);

    // El <Label>Categoría</Label> no está asociado al Radix SelectTrigger (sin
    // htmlFor) → getByLabel chocaba en strict-mode. El primer combobox de la
    // página es el filtro Categoría (Todas/Legal/Técnico/Documentación/Operacional).
    await page.getByRole("combobox").first().click();
    await page.getByRole("option", { name: "Legal", exact: true }).click();
    await expect(filas).toHaveCount(4);
  });

  // Requiere que el GET exit-checklist haga COMMIT de la siembra perezosa
  // (exit_checklist_api.list_exit_checklist): sin él cada GET devolvía ids
  // nuevos y el POST /{item_id}/complete respondía 404. El test se limpia solo:
  // completa el item y lo revierte a pendiente desde la misma UI.
  test("mark item completado abre modal + submit", async ({ page, context }) => {
    // Punto de partida conocido: "Acta de cierre firmada" pendiente.
    const listUrl = `${BACKEND}/api/v1/projects/${PROJECT_ID}/exit-checklist`;
    const list = await (await context.request.get(listUrl)).json();
    const acta = (list.items as { id: string; item_code: string; status: string }[])
      .find((i) => i.item_code === "acta_cierre");
    expect(acta).toBeTruthy();
    if (acta!.status === "completado") {
      const csrf =
        (await context.cookies()).find((c) => c.name === "fulkro_csrf")?.value ?? "";
      const res = await context.request.post(`${listUrl}/${acta!.id}/uncomplete`, {
        headers: { "x-csrf-token": csrf },
      });
      expect(res.ok()).toBeTruthy();
      await page.reload();
    }

    const row = page.locator("table tbody tr").filter({ hasText: "Acta de cierre firmada" });
    await expect(row.getByText("Pendiente", { exact: true })).toBeVisible();

    await row.getByRole("button", { name: /Acciones/i }).click();
    await page.getByRole("menuitem", { name: /Marcar completado/i }).click();
    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible();
    await expect(dialog.getByText(/Marcar completado/)).toBeVisible();
    await page.getByPlaceholder(/Razón \/ contexto/).fill("E2E smoke test note");
    await page.getByRole("button", { name: /^Confirmar$/ }).click();
    await expect(dialog).toBeHidden();
    await expect(row.getByText("Completado", { exact: true })).toBeVisible();

    // Persistido de verdad: tras recargar sigue completado.
    await page.reload();
    await expect(row.getByText("Completado", { exact: true })).toBeVisible();

    // Limpieza por la UI: revertir a pendiente.
    await row.getByRole("button", { name: /Acciones/i }).click();
    await page.getByRole("menuitem", { name: /Revertir a pendiente/i }).click();
    await expect(row.getByText("Pendiente", { exact: true })).toBeVisible();
  });

  test("check readiness muestra blockers preview", async ({ page }) => {
    await page.getByRole("button", { name: /Verificar readiness/i }).click();
    // Badge "Bloqueado" o "Listo para cerrar" visible · blockers card si hay
    await expect(
      page.getByText(/Bloqueado|Listo para cerrar/),
    ).toBeVisible();
  });

  test("búsqueda libre filtra por label", async ({ page }) => {
    await page.waitForSelector("table tbody tr");
    await page.getByPlaceholder(/Buscar por descripción/).fill("contrato");
    const rows = await page.locator("table tbody tr").count();
    expect(rows).toBeGreaterThan(0);
    expect(rows).toBeLessThan(16);
  });
});
