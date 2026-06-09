/**
 * E2E /client-portal/policies · SAN-E v3.MB-6 atom 1 (post atoms 2-7).
 *
 * Valida flujo cliente policies CCN-STIC 805:
 *  1. Login → navega /client-portal/policies
 *  2. Header tier-aware visible (CCN-STIC 805 cita)
 *  3. Page renders sin errores
 *  4. firmas-hub muestra policy_approval card · chain shape flexible post atoms 2-7
 */
import { expect, test } from "@playwright/test";

import { loginAsClient } from "./_helpers/auth-real";

test.describe("Client Portal · Policies · MB-6 atom 1 (post atoms 2-7)", () => {
  test("Cliente VE policies page tier-aware", async ({ page }) => {
    await loginAsClient(page);

    await page.goto("/client-portal/policies");

    await expect(
      page.getByRole("heading", { name: /Mis políticas/i }),
    ).toBeVisible();

    await expect(page.getByText(/CCN-STIC 805/i)).toBeVisible();
  });

  test("Firmas-hub muestra policy_approval card en chain operativa", async ({
    page,
  }) => {
    await loginAsClient(page);

    await page.goto("/client-portal/firmas-hub");

    await expect(
      // El h1 embebe <TooltipENS> → accessible name "Mis firmas Ayuda: ENS".
      // Regex tolerante (auditoría 2026-06-07).
      page.getByRole("heading", { name: /Mis firmas/i }),
    ).toBeVisible();

    // Chain ha crecido (atom 1 era 5-link · atom 2 añadió dpc_anual · chain ahora 6+)
    await expect(page.getByText(/de \d+ firmas completadas/i)).toBeVisible();

    await expect(
      page.locator("[data-signable-type='policy_approval']"),
    ).toBeVisible();
  });
});
