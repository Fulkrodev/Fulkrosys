/**
 * E2E /client-portal/retainer-checkin · SAN-E v3.MB-6 atom 4.
 *
 * Validates cliente UX cliente trimestral checkin:
 *  1. Login → /client-portal/retainer-checkin
 *  2. Header + intro CCN-STIC 805 visible
 *  3. Empty state cuando sin checkins (Q5)
 *
 * (El enlace "Comité Retainer" del sidebar cliente se retiró a propósito en
 *  1.D.F.bis.III.D: el cliente llega por tareas contextuales, no navegando.)
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
});
