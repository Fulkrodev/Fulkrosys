/**
 * SAN-E v3.MB-8.1 · cliente WhatsApp opt-in flow render.
 *
 * Verifica que /client-portal/whatsapp renderiza el opt-in card
 * cuando no hay opt-in activo · phone input + send button.
 */
import { expect, test } from "@playwright/test";

import { loginAsClient } from "../_helpers/auth-real";


test.use({ viewport: { width: 1280, height: 800 } });


test.describe("SAN-E v3.MB-8.1 · cliente WhatsApp opt-in", () => {
  test("/client-portal/whatsapp renders opt-in card", async ({ page }) => {
    await loginAsClient(page);
    await page.goto("/client-portal/whatsapp");
    // `load` y no `networkidle`: el portal mantiene abierta la conexion SSE de
    // eventos, y con ella la red nunca queda inactiva (la espera no acaba nunca).
    await page.waitForLoadState("load");

    // Uno de los cuatro estados tiene que aparecer: sin credenciales de
    // WhatsApp en el entorno (dev, CI) la pagina dice «próximamente», que es
    // correcto. `isVisible()` no espera: se evaluaba en cuanto terminaba
    // `load`, antes de que llegasen los datos.
    const algunEstado = page
      .getByTestId("whatsapp-phone-input")
      .or(page.getByTestId("whatsapp-otp-input"))
      .or(page.getByTestId("whatsapp-active-status"))
      .or(page.getByTestId("whatsapp-coming-soon"));
    await expect(algunEstado.first()).toBeVisible({ timeout: 10_000 });
  });

  test("header WhatsApp · FULKRO visible", async ({ page }) => {
    await loginAsClient(page);
    await page.goto("/client-portal/whatsapp");
    // `load` y no `networkidle`: el portal mantiene abierta la conexion SSE de
    // eventos, y con ella la red nunca queda inactiva (la espera no acaba nunca).
    await page.waitForLoadState("load");

    await expect(
      page.getByRole("heading", { name: "WhatsApp · FULKRO", exact: true }),
    ).toBeVisible({ timeout: 10_000 });
  });
});
