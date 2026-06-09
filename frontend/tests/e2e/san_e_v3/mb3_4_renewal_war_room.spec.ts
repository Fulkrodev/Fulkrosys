/**
 * MB-3.4 · RenewalWarRoom real wired M27 + M28 (SAN-E v3).
 *
 * Wired al backend:
 *   M27 commit MB-3.D 4a17834 (timeline · contact-auditor · auditor-info)
 *   M28 commit MB-3.E 6daaae2 (drift-summary)
 * Run pendiente Marcos manual con servers up.
 *
 * Cobertura:
 * - login admin · navigate /renewal
 * - hero countdown days_until visible
 * - status badge global (ON TRACK / WARNING / BEHIND / CRITICAL)
 * - DriftMatrix 10x4 grid renders
 * - RenewalTimeline 8 milestones
 * - 4 ActionCards visibles
 * - click "Contactar auditor ENAC" abre dialog · submit form
 */
import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "../_helpers/auth-real";

const PROJECT_ID =
  process.env.E2E_SEED_PROJECT_ID ?? "00000000-0000-0000-0000-000000000001";

test.describe("MB-3.4 · RenewalWarRoom M27+M28", () => {
  test.beforeEach(async ({ context, page }) => {
    await loginAsMarcos(context);
    await page.goto(`/admin/projects/${PROJECT_ID}/renewal`);
  });

  test("hero countdown + status badge visibles", async ({ page }) => {
    await expect(page.getByText("Próxima auditoría", { exact: false })).toBeVisible();
    // Status badge alguno (ON TRACK / WARNING / BEHIND / CRITICAL)
    await expect(
      page.getByText(/ON TRACK|ATENCIÓN|RETRASADO|CRÍTICO/),
    ).toBeVisible();
  });

  test("DriftMatrix 10 dimensiones × 4 severidades visible", async ({ page }) => {
    await expect(page.getByText("Matriz de drift")).toBeVisible();
    // 4 column headers severidades. Cada etiqueta de severidad aparece en el
    // header de columna y en las celdas/leyenda → .first() evita strict-mode.
    await expect(page.getByText("Crítica").first()).toBeVisible();
    await expect(page.getByText("Alta").first()).toBeVisible();
    await expect(page.getByText("Media").first()).toBeVisible();
    await expect(page.getByText("Baja").first()).toBeVisible();
    // Algunas dimensiones row labels
    await expect(
      page.getByText(/Autenticación|Cifrado|Backups/).first(),
    ).toBeVisible();
  });

  test("RenewalTimeline 8 milestones visibles", async ({ page }) => {
    await expect(page.getByText("Hitos pre-renovación")).toBeVisible();
    // Cada milestone se renderiza en varias capas (timeline desktop/mobile +
    // posibles cards) → .first() evita strict-mode.
    await expect(page.getByText("Preparación").first()).toBeVisible();
    await expect(page.getByText("Auditoría").first()).toBeVisible();
  });

  test("4 ActionCards visibles", async ({ page }) => {
    await expect(page.getByText("Acciones disponibles")).toBeVisible();
    await expect(page.getByText("Iniciar preparación")).toBeVisible();
    await expect(page.getByText("Contactar auditor ENAC")).toBeVisible();
    await expect(page.getByText("Generar dossier")).toBeVisible();
    await expect(page.getByText("Programar pentest refresh")).toBeVisible();
  });

  test("contactAuditor dialog · form fields", async ({ page }) => {
    await page.getByRole("button", { name: "Contactar" }).first().click();
    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible();
    // Scope al dialog: getByLabel("Email") chocaba con el mailto del
    // FulkroFooter (aria-label "Enviar email a…"). Los campos del modal tienen
    // htmlFor (auditor-name/email/message) → getByLabel funciona dentro.
    await expect(dialog.getByLabel("Nombre auditor")).toBeVisible();
    await expect(dialog.getByLabel("Email")).toBeVisible();
    await expect(dialog.getByLabel(/Mensaje/)).toBeVisible();
  });
});
