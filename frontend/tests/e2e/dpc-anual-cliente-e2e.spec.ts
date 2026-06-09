/**
 * E2E /client-portal/dpc-anual · SAN-E v3.MB-6 atom 2.
 *
 * Valida flujo cliente DPC anual:
 *  1. Login → /client-portal/dpc-anual
 *  2. Verify header + countdown · si NO conformidad firmada → empty state
 *  3. Verify sidebar nav "DPC anual" item visible
 *  4. Firmas-hub muestra 6-link (con dpc_anual card pending_creation)
 */
import { expect, test } from "@playwright/test";

import { loginAsClient } from "./_helpers/auth-real";
import { seedConformidadReady } from "./_helpers/conformidad-seed";
import { seedDdaAltaProject } from "./_helpers/dda-seed";

test.describe("Client Portal · DPC anual · MB-6 atom 2", () => {
  test("Cliente VE DPC anual page · empty state (sin conformidad firmada)", async ({
    page,
  }) => {
    await loginAsClient(page);
    await page.goto("/client-portal/dpc-anual");

    await expect(
      page.getByRole("heading", {
        name: "Declaración Protección Continuidad anual",
      }),
    ).toBeVisible();

    await expect(page.getByText(/Art\.?25 del RD 311\/2022/i)).toBeVisible();
    await expect(page.getByText(/CCN-STIC 806/i)).toBeVisible();

    // Sin conformidad firmada · empty state
    await expect(
      page.getByText(/Todavía no hay DPC anual programada/i),
    ).toBeVisible();
  });

  test("Sidebar nav 'DPC anual' visible · firmas-hub incluye dpc_anual", async ({
    page,
    request,
  }) => {
    // Sembrar chain para que firmas-hub muestre el progreso + las cards.
    await seedDdaAltaProject(request);
    await seedConformidadReady(request, "MEDIA");

    await loginAsClient(page);
    await page.goto("/client-portal/dpc-anual");

    const nav = page.getByRole("link", { name: "DPC anual" });
    await expect(nav).toBeVisible();

    await page.goto("/client-portal/firmas-hub");
    // Contador robusto (no hardcodear 6 · la chain puede crecer).
    await expect(page.getByText(/de \d+ firmas completadas/i)).toBeVisible();
    await expect(
      page.locator("[data-signable-type='dpc_anual']"),
    ).toBeVisible();
    await expect(
      page.locator("[data-signable-type='dpc_anual']"),
    ).toHaveAttribute("data-status", "pending_creation");
  });
});
