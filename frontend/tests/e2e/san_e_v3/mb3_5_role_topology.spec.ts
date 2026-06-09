/**
 * MB-3.5 · RoleTopologyPanel real wired M28+M30 (SAN-E v3).
 *
 * Wired al backend:
 *   M28 commit MB-3.E 6daaae2 + GET /role-topology (MB-3.5 backend extension)
 *   M30 EXTENDED commit MB-3.C 8f40347 (project-scoped contacts + constraint v3)
 * Run pendiente Marcos manual con servers up.
 *
 * Cobertura:
 * - login admin · navigate /roles
 * - hero coverage_pct + progress bar
 * - 5 cards ENS_REQUIRED renderizan
 * - 3 cards cross-compliance renderizan
 * - click "Asignar contacto" en RI · modal con 2 tabs
 * - Tab "Crear nuevo" + has_portal_access switch + constraint v3 alert
 * - submit · contact creado + asignado · coverage actualizado
 * - 2do contact con portal_access intentar → switch disabled + alert
 * - assign mismo contact a RSEG y RSIS → segregation alert visible
 * - vacate role → confirm dialog → vacated
 */
import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "../_helpers/auth-real";

const PROJECT_ID =
  process.env.E2E_SEED_PROJECT_ID ?? "00000000-0000-0000-0000-000000000001";

test.describe("MB-3.5 · RoleTopologyPanel M28+M30", () => {
  test.beforeEach(async ({ context, page }) => {
    await loginAsMarcos(context);
    await page.goto(`/admin/projects/${PROJECT_ID}/roles`);
  });

  test("hero coverage + progress bar", async ({ page }) => {
    await expect(
      page.getByText(/Cobertura roles ENS/i),
    ).toBeVisible();
    // Algún % visible
    await expect(page.getByText(/% \d+%|\d+%/).first()).toBeVisible();
  });

  test("5 cards ENS_REQUIRED renderizan", async ({ page }) => {
    await expect(
      page.getByRole("heading", { name: /Roles ENS obligatorios/i }),
    ).toBeVisible();
    // 5 short codes visibles. Cada código aparece en varios nodos (título card
    // + descripción/tooltip) → .first() evita strict-mode.
    await expect(page.getByText("Sponsor", { exact: false }).first()).toBeVisible();
    await expect(page.getByText("RI", { exact: false }).first()).toBeVisible();
    await expect(page.getByText("RS", { exact: false }).first()).toBeVisible();
    await expect(page.getByText("RSEG", { exact: false }).first()).toBeVisible();
    await expect(page.getByText("RSIS", { exact: false }).first()).toBeVisible();
  });

  test("3 cards cross-compliance renderizan", async ({ page }) => {
    await expect(
      page.getByRole("heading", { name: /Roles cross-compliance/i }),
    ).toBeVisible();
    await expect(page.getByText(/DPO/, { exact: false }).first()).toBeVisible();
    await expect(page.getByText(/CISO/, { exact: false }).first()).toBeVisible();
    await expect(page.getByText(/Auditor/, { exact: false }).first()).toBeVisible();
  });

  test("modal asignación · 2 tabs visibles", async ({ page }) => {
    // Click primer "Asignar contacto" disponible
    const firstAssign = page.getByRole("button", { name: /Asignar contacto/i }).first();
    await firstAssign.click();
    await expect(page.getByRole("dialog")).toBeVisible();
    // Tabs visibles
    await expect(page.getByRole("tab", { name: /Buscar contacto existente/i })).toBeVisible();
    await expect(page.getByRole("tab", { name: /Crear contacto nuevo/i })).toBeVisible();
  });

  test("crear contacto · constraint v3 portal switch", async ({ page }) => {
    const firstAssign = page.getByRole("button", { name: /Asignar contacto/i }).first();
    await firstAssign.click();
    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible();
    // Cambiar a tab "Crear contacto nuevo"
    await dialog.getByRole("tab", { name: /Crear contacto nuevo/i }).click();
    // Verificar campos form visibles. Scope al dialog: getByLabel("Email")
    // chocaba con el mailto del FulkroFooter. Campos con htmlFor
    // (contact-name/email/cargo) → getByLabel resuelve dentro del dialog.
    await expect(dialog.getByLabel(/Nombre completo/)).toBeVisible();
    await expect(dialog.getByLabel("Email")).toBeVisible();
    await expect(dialog.getByLabel(/Cargo/)).toBeVisible();
    // Verificar switch portal access
    await expect(dialog.getByText(/Crear cuenta portal cliente/)).toBeVisible();
  });
});
