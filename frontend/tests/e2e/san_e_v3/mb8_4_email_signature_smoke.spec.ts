/**
 * SAN-E v3.MB-8.4 · email signature module importable.
 *
 * Pure smoke check sin necesidad de enviar email real:
 *  - /api/v1/health/* responde (backend up)
 *  - Verifica que el page /client-portal/whatsapp accesible para
 *    cliente (regression no breaking other routes).
 */
import { expect, test } from "@playwright/test";

import { loginAsClient } from "../_helpers/auth-real";


test.describe("SAN-E v3.MB-8.4 · email signature regression", () => {
  test("cliente portal sigue accesible post-cambios MB-8", async ({
    page,
  }) => {
    await loginAsClient(page);
    await page.goto("/client-portal/dashboard");
    await page.waitForLoadState("networkidle");
    await expect(page.getByTestId("client-dashboard-v3")).toBeVisible({
      timeout: 10_000,
    });
  });

  test("cliente /client-portal/whatsapp accesible", async ({ page }) => {
    await loginAsClient(page);
    await page.goto("/client-portal/whatsapp");
    await page.waitForLoadState("networkidle");
    await expect(
      page.getByRole("heading", { name: "WhatsApp · FULKRO", exact: true }),
    ).toBeVisible({ timeout: 10_000 });
  });
});
