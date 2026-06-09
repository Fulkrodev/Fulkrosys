/**
 * SAN-E v3.MB-7.2 · CopilotoDock global · MB-7 atom 7.2 plan v6.
 *
 * Verifica que el dock flotante esté siempre disponible en cualquier
 * página del portal cliente autenticada (toggle + open + close).
 *
 * Q1.D cement: dock global single instance via ClientPortalChrome.
 */
import { expect, test } from "@playwright/test";

import { loginAsClient } from "../_helpers/auth-real";

test.use({ viewport: { width: 1280, height: 800 } });

test.describe("SAN-E v3.MB-7.2 · CopilotoDock global", () => {
  test("dock toggle visible en dashboard · click expande", async ({ page }) => {
    await loginAsClient(page);
    await page.goto("/client-portal/dashboard");
    await page.waitForLoadState("networkidle");

    // Dock collapsed visible
    const toggle = page.getByTestId("copiloto-dock-toggle");
    await expect(toggle).toBeVisible();

    // Click expande
    await toggle.click();
    await expect(page.getByTestId("copiloto-dock-open")).toBeVisible();
    await expect(page.getByText(/Copiloto FULKRO/i)).toBeVisible();
    await expect(page.getByTestId("copiloto-input")).toBeVisible();
    await expect(page.getByTestId("copiloto-send")).toBeVisible();
  });

  test("dock persiste en /files (segunda ruta autenticada)", async ({
    page,
  }) => {
    await loginAsClient(page);
    await page.goto("/client-portal/files");
    await page.waitForLoadState("networkidle");

    await expect(page.getByTestId("copiloto-dock-toggle")).toBeVisible();
  });

  test("dock cerrar · close icon devuelve a estado collapsed", async ({
    page,
  }) => {
    await loginAsClient(page);
    await page.goto("/client-portal/dashboard");
    await page.waitForLoadState("networkidle");

    await page.getByTestId("copiloto-dock-toggle").click();
    await expect(page.getByTestId("copiloto-dock-open")).toBeVisible();

    await page.getByRole("button", { name: /Cerrar copiloto/i }).click();
    await expect(page.getByTestId("copiloto-dock-open")).not.toBeVisible();
    await expect(page.getByTestId("copiloto-dock-toggle")).toBeVisible();
  });
});
