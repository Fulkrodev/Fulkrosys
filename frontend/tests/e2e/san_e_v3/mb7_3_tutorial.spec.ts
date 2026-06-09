/**
 * SAN-E v3.MB-7.3 · OnboardingTutorial · MB-7 atom 7.3 plan v6.
 *
 * Verifica el tutorial de 5 pasos:
 *  - Auto-trigger en primer login (localStorage flag missing)
 *  - Navegación siguiente/atrás
 *  - Skip option · persiste flag · NO se re-abre en navegación
 *
 * Limpia localStorage antes de cada test para asegurar el auto-trigger.
 */
import { expect, test } from "@playwright/test";

import { loginAsClient } from "../_helpers/auth-real";

test.use({ viewport: { width: 1280, height: 800 } });

test.describe("SAN-E v3.MB-7.3 · onboarding tutorial", () => {
  // NOTA: el contexto Playwright arranca con localStorage vacío, así que el
  // tutorial auto-dispara de forma natural. Usamos loginAsClient con
  // dismissTutorial:false para que el helper NO siembre la flag
  // `fulkro_tutorial_completed` tras el login. ANTES se limpiaba la flag con
  // context.addInitScript, pero ese script corre en CADA carga de documento —
  // incluido el page.reload() del test de persistencia del skip — y borraba la
  // flag que el skip acababa de persistir → el overlay reaparecía (falso fallo).

  test("first-login · tutorial overlay aparece", async ({ page }) => {
    await loginAsClient(page, { dismissTutorial: false });
    await page.goto("/client-portal/dashboard");

    // Tutorial overlay visible
    await expect(page.getByTestId("tutorial-overlay")).toBeVisible({
      timeout: 10_000,
    });
    await expect(page.getByText(/Paso 1 de 5/i)).toBeVisible();
    await expect(page.getByText(/Bienvenido a tu portal FULKRO/i)).toBeVisible();
  });

  test("navegar siguiente · paso 2 · paso 3 · finish", async ({ page }) => {
    await loginAsClient(page, { dismissTutorial: false });
    await page.goto("/client-portal/dashboard");

    await expect(page.getByTestId("tutorial-overlay")).toBeVisible();

    // Avanzar 4 veces hasta paso 5
    for (let i = 0; i < 4; i++) {
      await page.getByTestId("tutorial-next").click();
    }
    await expect(page.getByText(/Paso 5 de 5/i)).toBeVisible();
    await expect(page.getByTestId("tutorial-finish")).toBeVisible();

    // Finish cierra el overlay
    await page.getByTestId("tutorial-finish").click();
    await expect(page.getByTestId("tutorial-overlay")).not.toBeVisible();
  });

  test("skip · tutorial flag persiste · no re-aparece reload", async ({
    page,
  }) => {
    await loginAsClient(page, { dismissTutorial: false });
    await page.goto("/client-portal/dashboard");

    await expect(page.getByTestId("tutorial-overlay")).toBeVisible();
    await page.getByRole("button", { name: /Saltar tutorial/i }).click();
    await expect(page.getByTestId("tutorial-overlay")).not.toBeVisible();

    await page.reload();
    await page.waitForLoadState("networkidle");

    // No se vuelve a abrir
    await expect(page.getByTestId("tutorial-overlay")).not.toBeVisible();
  });
});
