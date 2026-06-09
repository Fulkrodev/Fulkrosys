/**
 * E2E · fase_32 cliente onboarding cloud-first (1.D.X.I v3.12).
 *
 * Verifica:
 *  - Tab "Conecta sistemas" es el primer tab + activo por default
 *  - Hero "Conecta tus sistemas" visible con copy R29 friendly
 *  - Grid de 6 provider cards rendered (M365 · Google · Azure · AWS · GitHub · Manual)
 *  - Click "Conectar" en M365 dispara POST connect/microsoft_365 + redirect M16
 */
import { expect, test } from "@playwright/test";

import { loginAsClient } from "../../_helpers/auth-real";
import { mockCloudConnectClientBase, mockCloudConnectInitFlow } from "../_fixtures";

test.describe("fase_32 · cliente onboarding cloud-first", () => {
  test("first tab 'Conecta sistemas' active by default + grid rendered", async ({
    page,
  }) => {
    await loginAsClient(page);
    await mockCloudConnectClientBase(page);

    await page.goto("/client-portal/onboarding");

    // Tab "Conecta sistemas" debe ser visible primero
    await expect(
      page.getByRole("tab", { name: /Conecta sistemas/i }),
    ).toBeVisible();

    // Hero R29 + tip super mega fácil (scope al hero · evita strict-mode con
    // el header de página que tiene copy similar "5 min · solo lectura")
    const hero = page.getByTestId("cloud-connect-first-step");
    await expect(hero).toBeVisible();
    await expect(
      hero.getByText("Conecta tus sistemas", { exact: true }),
    ).toBeVisible();
    // Copy hero real (CloudConnectFirstStep.tsx CardDescription): "Para hacer un
    // diagnóstico ENS verdadero · ... Tranquilo · solo lectura · 5 minutos.
    // Puedes saltar y conectar después." UI drift: "solo lectura" + "5 minutos"
    // ahora aparecen también en los 6 blurbs de proveedor → anclamos a la frase
    // única del hero ("diagnóstico ENS verdadero") para evitar strict-mode.
    await expect(
      hero.getByText(/diagnóstico ENS verdadero/i),
    ).toBeVisible();
    await expect(
      hero.getByText(/Puedes saltar y conectar después/i),
    ).toBeVisible();

    // Tooltips help + security
    await expect(page.getByTestId("cloud-connect-help-btn")).toBeVisible();
    await expect(page.getByTestId("cloud-connect-security-btn")).toBeVisible();
    await expect(page.getByTestId("cloud-connect-skip-btn")).toBeVisible();

    // Grid con 6 cards (espera al menos al grid · cards lazy)
    await expect(page.getByTestId("cloud-connect-grid")).toBeVisible();
    await expect(page.getByTestId("cloud-connect-card-microsoft_365")).toBeVisible();
    await expect(page.getByTestId("cloud-connect-card-google_workspace")).toBeVisible();
    await expect(page.getByTestId("cloud-connect-card-azure")).toBeVisible();
    await expect(page.getByTestId("cloud-connect-card-aws")).toBeVisible();
    await expect(page.getByTestId("cloud-connect-card-github")).toBeVisible();
    await expect(page.getByTestId("cloud-connect-card-manual_import")).toBeVisible();
  });

  test("click M365 connect triggers init flow + redirect (oauth)", async ({
    page,
  }) => {
    await loginAsClient(page);
    await mockCloudConnectClientBase(page);
    await mockCloudConnectInitFlow(page, {
      provider: "microsoft_365",
      nextStep: "oauth_redirect",
    });

    await page.goto("/client-portal/onboarding");
    await expect(page.getByTestId("cloud-connect-card-microsoft_365")).toBeVisible();

    // Click "Conectar" en M365
    const navWait = page.waitForRequest(
      (req) =>
        req.url().includes("/api/v1/portal/connectors/microsoft_365/authorize")
        || req.url().includes("/api/v1/client-portal/cloud-connectors/connect/microsoft_365"),
    );

    await page.getByTestId("cloud-connect-action-microsoft_365").click();
    await navWait;
  });
});
