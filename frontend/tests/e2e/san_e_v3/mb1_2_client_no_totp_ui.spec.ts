/**
 * SAN-E v3.MB-1.2 · Client portal sin TOTP UI.
 *
 * Verifica que post-1.1.C (backend TOTP cliente eliminado · commit 4e2eda9)
 * el client portal frontend tampoco renderiza UI TOTP:
 *   1. /client-portal/login · NO input "Código TOTP" jamás visible.
 *   2. /client-portal/login · tras submit con credenciales inválidas,
 *      NO surface step TOTP intermedio (era el bug post-1.1.C: 401
 *      con detail "TOTP requerido" disparaba setNeedsTotp(true)).
 *   3. /client-portal/account · NO Card "Autenticación en dos pasos".
 *
 * Admin login (/login con LoginForm.tsx) NO afectado por este atom.
 * Regression admin TOTP cubierta por suite m21/auth backend (commits
 * 4e2eda9 + a9f37b4) + V-CHECK MB-1 final atom 1.4.
 *
 * Selectors siguen patrón loginAsClient (auth-real.ts · seed
 * test-client-e2e@example.com / TestP@ssw0rd123!).
 */
import { expect, test } from "@playwright/test";

import { loginAsClient } from "../_helpers/auth-real";

test.use({ viewport: { width: 1280, height: 800 } });

test.describe("SAN-E v3.MB-1.2 · client portal sin TOTP UI", () => {
  test("login page · 0 input TOTP · 0 label código autenticador", async ({
    page,
  }) => {
    await page.goto("/client-portal/login");

    await expect(page.locator('input[pattern="[0-9]{6}"]')).toHaveCount(0);
    await expect(page.getByLabel(/Código TOTP/i)).toHaveCount(0);
  });

  test("login page · submit credenciales inválidas · NO surface step TOTP", async ({
    page,
  }) => {
    await page.goto("/client-portal/login");

    // Scope al form: el FulkroFooter (root layout) expone un mailto con
    // aria-label "Enviar email a …" que también matchea getByLabel(/Email/i),
    // provocando strict-mode 2 elementos. Usamos los id reales del form.
    await page.locator("#email").fill("inexistente@cliente.com");
    await page.locator("#password").fill("WrongPassword123!");
    await page.getByRole("button", { name: /Entrar/i }).click();

    // Espera al error (UI muestra mensaje sin step intermedio)
    await page.waitForTimeout(1500);

    await expect(page.locator('input[pattern="[0-9]{6}"]')).toHaveCount(0);
    await expect(page.getByLabel(/Código TOTP/i)).toHaveCount(0);
  });

  test("account page · 0 Card 'Autenticación en dos pasos' · cards esperadas presentes", async ({
    page,
  }) => {
    await loginAsClient(page);

    await page.goto("/client-portal/account");
    await page.waitForLoadState("networkidle");

    // 0 referencias UI TOTP
    await expect(page.getByText(/Autenticación en dos pasos/i)).toHaveCount(0);
    await expect(page.getByText(/Activar TOTP/i)).toHaveCount(0);
    await expect(page.getByText(/Desactivar TOTP/i)).toHaveCount(0);

    // Cards mantenidas (regresión sanity): Notificaciones, Mis facturas, Cambiar contraseña
    await expect(page.getByText(/Notificaciones/i).first()).toBeVisible();
    await expect(page.getByText(/Mis facturas/i).first()).toBeVisible();
    await expect(page.getByText(/Cambiar contraseña/i).first()).toBeVisible();
  });
});
