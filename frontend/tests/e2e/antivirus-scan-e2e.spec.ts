/**
 * E2E antivirus scan UI · SAN-E v3.MB-6 atom 6 · ENS mp.s.5.
 *
 * Validates ClamAV transparency UX cliente:
 *  1. Cliente login → /client-portal/evidencias
 *  2. Page renders upload form
 *  3. Sidebar nav 'Subir documentos' link visible
 *
 * Scope minimal · drop-in pattern atom 4/5 (header + sidebar visibility).
 * Full scan flow E2E (real clamd + EICAR) diferido atom 6.bis: requiere
 * clamd ready (~120s cold-start) + Celery worker activo + janitor task.
 */
import { expect, test } from "@playwright/test";

import { loginAsClient } from "./_helpers/auth-real";

test.describe("Client Portal · Antivirus scan UI · MB-6 atom 6", () => {
  test("Cliente VE upload page · header + form", async ({ page }) => {
    await loginAsClient(page);
    await page.goto("/client-portal/evidencias");

    await expect(
      page.getByRole("heading", { name: /Subir evidencia/i }),
    ).toBeVisible();

    await expect(page.getByText(/Formatos aceptados/i)).toBeVisible();

    const fileInput = page.locator('input[type="file"]');
    await expect(fileInput).toBeVisible();
  });

  test("Sidebar nav 'Subir documentos' visible", async ({ page }) => {
    await loginAsClient(page);
    await page.goto("/client-portal/evidencias");

    // El enlace real es "Subir documentos" (→ /client-portal/files).
    const nav = page.getByRole("link", { name: /Subir documentos/i });
    await expect(nav).toBeVisible();
  });
});
