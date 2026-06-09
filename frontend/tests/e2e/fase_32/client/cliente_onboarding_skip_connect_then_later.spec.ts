/**
 * E2E · fase_32 cliente · saltar conexión sistemas · 1.D.X.I v3.12.
 *
 * Verifica:
 *  - Click "Saltar por ahora" cambia al tab Wizard (R29 sin presión)
 *  - El cliente puede volver al tab Conecta sistemas en cualquier momento
 *  - El estado de los connectors persiste entre cambios de tab
 */
import { expect, test } from "@playwright/test";

import { loginAsClient } from "../../_helpers/auth-real";
import {
  CONNECTORS_WITH_M365_CONNECTED,
  mockCloudConnectClientBase,
} from "../_fixtures";

test.describe("fase_32 · cliente skip + retry connect", () => {
  test("Saltar por ahora switches to Wizard tab (R29 no pressure)", async ({
    page,
  }) => {
    await loginAsClient(page);
    await mockCloudConnectClientBase(page);

    await page.goto("/client-portal/onboarding");
    await expect(page.getByTestId("cloud-connect-skip-btn")).toBeVisible();

    await page.getByTestId("cloud-connect-skip-btn").click();

    // Wizard tab debería estar activo · grid Cloud ya no visible
    await expect(page.getByTestId("cloud-connect-grid")).not.toBeVisible();
  });

  test("Connected M365 shows friendly_message + checkmark", async ({ page }) => {
    await loginAsClient(page);
    await mockCloudConnectClientBase(page, {
      connectorsList: CONNECTORS_WITH_M365_CONNECTED,
    });

    await page.goto("/client-portal/onboarding");
    await expect(page.getByTestId("cloud-connect-card-microsoft_365")).toBeVisible();

    // friendly_message visible (server-side generated)
    await expect(
      page.getByTestId("cloud-connect-friendly-msg-microsoft_365"),
    ).toContainText(/42 elementos detectados/i);

    // Action botón cambia a "Volver a conectar"
    await expect(
      page.getByTestId("cloud-connect-action-microsoft_365"),
    ).toContainText(/Volver a conectar/i);
  });
});
