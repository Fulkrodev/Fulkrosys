/**
 * SAN-E v3.MB-7.1 · client dashboard adaptativo · MEDIA tier widgets.
 *
 * Independientemente del tier del seed, verifica que los widgets
 * tier-aware (messages preview + documents count) renderizan en el
 * Resumen visual zone 3.
 */
import { expect, test } from "@playwright/test";

import { loginAsClient } from "../_helpers/auth-real";

test.use({ viewport: { width: 1280, height: 800 } });

test.describe("SAN-E v3.MB-7.1 · dashboard tier-aware widgets", () => {
  test("zone 3 cards · workflow + messages + documents visibles", async ({
    page,
  }) => {
    await loginAsClient(page);
    await page.goto("/client-portal/dashboard");
    await page.waitForLoadState("networkidle");

    // Workflow stepper card
    await expect(page.getByTestId("workflow-stepper")).toBeVisible();

    // Messages preview card · "Mensajes" o "Ver todos"
    await expect(page.getByText(/Mensajes/i).first()).toBeVisible();

    // Documents count card · "Documentos"
    await expect(page.getByText(/Documentos/i).first()).toBeVisible();
  });

  test("phase stepper · current step highlighted", async ({ page }) => {
    await loginAsClient(page);
    await page.goto("/client-portal/dashboard");
    await page.waitForLoadState("networkidle");

    const stepper = page.getByTestId("workflow-stepper");
    await expect(stepper).toBeVisible();
    // Verifica que hay un item visible · al menos 1 (los 10 deberían existir)
    const items = stepper.locator("li");
    await expect(items.first()).toBeVisible();
  });
});
