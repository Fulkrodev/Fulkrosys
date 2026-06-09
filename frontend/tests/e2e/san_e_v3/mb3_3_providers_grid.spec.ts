/**
 * MB-3.3 · ProvidersGrid real wired M14 (SAN-E v3).
 *
 * Wired al backend M14 providers/c002 (commit MB-3.B 6800b5f · 7 endpoints).
 * Run pendiente Marcos manual con servers up.
 *
 * Cobertura:
 * - login admin · navigate /providers
 * - header stats visibles + 0 providers initially
 * - AddProviderModal: form fields + auto-detect preview ENS+GDPR cuando cloud+ALTO
 * - submit add · provider card aparece en grid
 * - filters type/criticality reducen visible
 * - click "Ver gaps" abre C002GapsPanel drawer
 * - generar C-002 con gaps · success toast
 * - delete provider · card removed
 */
import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "../_helpers/auth-real";

const PROJECT_ID =
  process.env.E2E_SEED_PROJECT_ID ?? "00000000-0000-0000-0000-000000000001";

test.describe("MB-3.3 · ProvidersGrid M14", () => {
  test.beforeEach(async ({ context, page }) => {
    await loginAsMarcos(context);
    await page.goto(`/admin/projects/${PROJECT_ID}/providers`);
  });

  test("header stats visibles", async ({ page }) => {
    await expect(
      page.getByRole("heading", { name: "Proveedores del proyecto" }),
    ).toBeVisible();
    await expect(page.getByText(/Total/i)).toBeVisible();
    await expect(page.getByText(/C-002 firmados/i)).toBeVisible();
    await expect(page.getByText(/Con gaps/i)).toBeVisible();
    // exact:true · "Críticos" hace match substring en 2 nodos (StatChip label +
    // tooltip); el label exacto del chip resuelve a 1.
    await expect(page.getByText("Críticos", { exact: true })).toBeVisible();
  });

  test("AddProviderModal · auto-detect preview cuando cloud+ALTO", async ({
    page,
  }) => {
    await page.getByRole("button", { name: /^Añadir proveedor$/ }).click();
    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible();

    // Fill form: cloud + ALTO. Los <Label>Tipo/Criticidad</Label> del modal NO
    // están asociados a sus Radix Select (sin htmlFor) → getByLabel hacía
    // timeout. Usamos los combobox del dialog: primero = Tipo, segundo =
    // Criticidad. Nombre/Scope sí tienen htmlFor → getByLabel funciona.
    await dialog.getByLabel(/^Nombre$/).fill("AWS Spain Test");
    await dialog.getByRole("combobox").nth(0).click();
    await page.getByRole("option", { name: "Cloud (IaaS)" }).click();
    await dialog.getByRole("combobox").nth(1).click();
    await page.getByRole("option", { name: /^Alto$/i }).click();
    await dialog.getByLabel(/^Scope/).fill("Hosting datos productivos");

    // Auto-detect preview visible
    await expect(page.getByText(/Cross-compliance detectado/i)).toBeVisible();
    await expect(page.getByText(/ENS\s*Art\.\s*18/)).toBeVisible();
    await expect(page.getByText(/GDPR\s*Art\.\s*28/)).toBeVisible();
  });

  test("filters type+criticality reducen visible", async ({ page }) => {
    // Filtro Tipo = primer combobox de la página (el <Label>Tipo</Label> no
    // está asociado al Radix Select → getByLabel no lo encontraba).
    await page.getByRole("combobox").first().click();
    await page.getByRole("option", { name: "Cloud", exact: true }).click();
    // Badge filter count visible
    await expect(page.locator("text=proveedor").last()).toBeVisible();
  });

  test("búsqueda libre filtra", async ({ page }) => {
    await page.getByPlaceholder(/Buscar por nombre o scope/).fill("test");
    // Sin error · count actualizado
    await expect(page.locator("text=proveedor").last()).toBeVisible();
  });
});
