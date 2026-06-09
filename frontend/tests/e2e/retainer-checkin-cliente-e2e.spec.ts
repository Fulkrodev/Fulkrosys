/**
 * E2E /client-portal/retainer-checkin · SAN-E v3.MB-6 atom 4.
 *
 * Validates cliente UX cliente trimestral checkin:
 *  1. Login → /client-portal/retainer-checkin
 *  2. Header + intro CCN-STIC 805 visible
 *  3. Empty state cuando sin checkins (Q5)
 *  4. Sidebar nav "Comité Retainer" link visible
 */
import { expect, test } from "@playwright/test";

import { loginAsClient } from "./_helpers/auth-real";

test.describe("Client Portal · Retainer Checkin · MB-6 atom 4", () => {
  test("Cliente VE page · header + empty state", async ({ page }) => {
    await loginAsClient(page);
    await page.goto("/client-portal/retainer-checkin");

    await expect(
      page.getByRole("heading", { name: "Comités trimestrales Retainer" }),
    ).toBeVisible();

    await expect(page.getByText(/Revisión trimestral del estado/i)).toBeVisible();

    // Empty state (sin retainer activo seedeado)
    await expect(
      page.getByText(/Sin comités retainer programados/i),
    ).toBeVisible();
  });

  // SKIP: feature eliminada (entrada de sidebar "Comité Retainer") — la página
  // /client-portal/retainer-checkin sigue existiendo y se prueba arriba, pero
  // el enlace en el ClientSidebar fue retirado deliberadamente en el refactor
  // 1.D.F.bis.III.D "indispensable-cliente-only" (ver ClientSidebar.tsx líneas
  // 33-37: /retainer-checkin es página NO-sidebar · el cliente llega vía tareas
  // contextuales que Marcos asigna, no navegando manualmente). Candidata a
  // borrar tras contraste (Marcos).
  test.skip("Sidebar nav 'Comité Retainer' visible", async ({ page }) => {
    await loginAsClient(page);
    await page.goto("/client-portal/retainer-checkin");

    const nav = page.getByRole("link", { name: "Comité Retainer" });
    await expect(nav).toBeVisible();
  });
});
