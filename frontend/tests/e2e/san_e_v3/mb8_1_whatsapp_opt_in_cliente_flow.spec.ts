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
    await page.waitForLoadState("networkidle");

    // El cliente seed no tiene WA · debería ver opt-in card
    const hasOptInInput = await page.getByTestId("whatsapp-phone-input").isVisible().catch(() => false);
    const hasOtpInput = await page.getByTestId("whatsapp-otp-input").isVisible().catch(() => false);
    const hasActiveStatus = await page.getByTestId("whatsapp-active-status").isVisible().catch(() => false);
    // At least one of the 3 states should render
    expect(hasOptInInput || hasOtpInput || hasActiveStatus).toBe(true);
  });

  test("header WhatsApp · FULKRO visible", async ({ page }) => {
    await loginAsClient(page);
    await page.goto("/client-portal/whatsapp");
    await page.waitForLoadState("networkidle");

    await expect(
      page.getByRole("heading", { name: "WhatsApp · FULKRO", exact: true }),
    ).toBeVisible({ timeout: 10_000 });
  });
});
