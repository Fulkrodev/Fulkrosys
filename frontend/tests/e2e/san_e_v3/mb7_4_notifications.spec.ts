/**
 * SAN-E v3.MB-7.4 · NotificationsBell · MB-7 atom 7.4 plan v6.
 *
 * Verifica el bell de notificaciones en el header cliente:
 *  - Visible siempre que el portal cliente está autenticado
 *  - Click abre el dropdown
 *  - "Marcar todo como leído" button presente
 *  - Footer "Ver todas →" link a /client-portal/inbox
 *  - Click-outside cierra el dropdown
 */
import { expect, test } from "@playwright/test";

import { loginAsClient } from "../_helpers/auth-real";

test.use({ viewport: { width: 1280, height: 800 } });

test.describe("SAN-E v3.MB-7.4 · NotificationsBell", () => {
  test("bell visible en header · accessible name", async ({ page }) => {
    await loginAsClient(page);
    await page.goto("/client-portal/dashboard");
    await page.waitForLoadState("networkidle");

    await expect(page.getByTestId("notifications-bell")).toBeVisible();
  });

  test("click bell abre dropdown · footer link inbox", async ({ page }) => {
    await loginAsClient(page);
    await page.goto("/client-portal/dashboard");
    await page.waitForLoadState("networkidle");

    await page.getByTestId("notifications-bell").click();
    await expect(page.getByTestId("notifications-dropdown")).toBeVisible();

    // Header "Notificaciones" + "Marcar todo" + footer link
    await expect(
      page.getByRole("heading", { name: /Notificaciones/i }),
    ).toBeVisible();
    await expect(page.getByText(/Marcar todo/i)).toBeVisible();
    await expect(page.getByRole("link", { name: /Ver todas/i })).toBeVisible();
  });

  test("click outside cierra dropdown", async ({ page }) => {
    await loginAsClient(page);
    await page.goto("/client-portal/dashboard");
    await page.waitForLoadState("networkidle");

    await page.getByTestId("notifications-bell").click();
    await expect(page.getByTestId("notifications-dropdown")).toBeVisible();

    // Click en el main content (fuera del dropdown)
    await page.getByTestId("client-dashboard-v3").click({ position: { x: 10, y: 10 } });
    await expect(page.getByTestId("notifications-dropdown")).not.toBeVisible();
  });
});
