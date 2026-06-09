/**
 * E2E /client-portal/incidents · SAN-E v3.MB-6 atom 3.
 *
 * Valida flujo cliente CCN-STIC 817:
 *  1. Login → /client-portal/incidents
 *  2. Header + counters visible
 *  3. Sin incidents · empty state visible
 *  4. Sidebar nav "Incidentes" link visible
 *  5. Header textos CCN-CERT + op.exp.10 visibles
 */
import { expect, test } from "@playwright/test";

import { loginAsClient } from "./_helpers/auth-real";

test.describe("Client Portal · Incidents · MB-6 atom 3", () => {
  test("Cliente VE page · header + counters + empty state", async ({
    page,
  }) => {
    await loginAsClient(page);
    await page.goto("/client-portal/incidents");
    // El portal cliente monta SSE (useClientProject) → 'networkidle' desnudo
    // nunca settlea. Patrón tolerante (igual que magerit-validation): el gate
    // real es el contenido visible. Los counters viven tras !loading && !error
    // (incidents/page.tsx línea 95) · esperamos a que el fetch del proyecto +
    // incidents resuelva antes de aseverarlos.
    await page.waitForLoadState("domcontentloaded");
    await page
      .waitForLoadState("networkidle", { timeout: 5000 })
      .catch(() => {});

    await expect(
      // El h1 embebe <TooltipENS term="CCN_CERT"> → accessible name real
      // "Incidentes y notificaciones …". Regex tolerante.
      page.getByRole("heading", {
        name: /Incidentes y notificaciones/,
      }),
    ).toBeVisible({ timeout: 10_000 });

    await expect(page.getByText(/op\.?exp\.?10/i)).toBeVisible();
    await expect(page.getByText(/Marcos gestiona los incidents/i)).toBeVisible();

    // Counters · copy intacto (incidents/page.tsx líneas 101/117). Timeout
    // generoso porque dependen del fetch del proyecto + lista de incidents.
    await expect(
      page.getByText(/Resueltos pendientes review/i),
    ).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText(/Cerrados \(firmados\)/i)).toBeVisible();

    await expect(
      page.getByText(/Sin incidents visibles/i),
    ).toBeVisible();
  });

  test("Sidebar nav 'Incidentes' link visible", async ({ page }) => {
    await loginAsClient(page);
    await page.goto("/client-portal/incidents");

    const nav = page.getByRole("link", { name: "Incidentes" });
    await expect(nav).toBeVisible();
  });
});
