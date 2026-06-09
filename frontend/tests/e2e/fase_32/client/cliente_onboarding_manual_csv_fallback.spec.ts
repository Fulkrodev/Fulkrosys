/**
 * E2E · fase_32 cliente · manual_import CSV fallback · 1.D.X.I v3.12.
 *
 * Verifica:
 *  - Click "Subir Excel" en card manual_import dispara POST connect/manual_import
 *  - Respuesta next_step=manual_upload muestra modal con link /client-portal/files
 *  - Modal R29 friendly · NO presión técnica
 *  - Help + Security tooltips abren modal con explanation primer-principios
 */
import { expect, test } from "@playwright/test";

import { loginAsClient } from "../../_helpers/auth-real";
import { mockCloudConnectClientBase, mockCloudConnectInitFlow } from "../_fixtures";

test.describe("fase_32 · cliente manual fallback + tooltips R29", () => {
  test("click Subir Excel manual_import opens upload hint modal", async ({
    page,
  }) => {
    await loginAsClient(page);
    await mockCloudConnectClientBase(page);
    await mockCloudConnectInitFlow(page, {
      provider: "manual_import",
      nextStep: "manual_upload",
    });

    await page.goto("/client-portal/onboarding");
    await expect(page.getByTestId("cloud-connect-card-manual_import")).toBeVisible();

    await page.getByTestId("cloud-connect-action-manual_import").click();

    // Modal con link to /client-portal/files
    await expect(page.getByTestId("cloud-connect-modal")).toBeVisible();
    const link = page.getByTestId("cloud-connect-manual-upload-link");
    await expect(link).toBeVisible();
    await expect(link).toHaveAttribute("href", "/client-portal/files");
  });

  test("Help tooltip opens primer-principios modal", async ({ page }) => {
    await loginAsClient(page);
    await mockCloudConnectClientBase(page);

    await page.goto("/client-portal/onboarding");
    await page.getByTestId("cloud-connect-help-btn").click();

    // Scope al modal · "¿Qué hago aquí?" también es el label del botón trigger
    // (strict-mode si no se acota). HelpModal title + cuerpo R29.
    const modal = page.getByTestId("cloud-connect-modal");
    await expect(modal).toBeVisible();
    await expect(modal.getByText(/qué hago aquí/i)).toBeVisible();
    await expect(modal.getByText(/diagnóstico verdadero/i)).toBeVisible();
  });

  test("Security tooltip explains read-only + Fernet + revocable", async ({
    page,
  }) => {
    await loginAsClient(page);
    await mockCloudConnectClientBase(page);

    await page.goto("/client-portal/onboarding");
    await page.getByTestId("cloud-connect-security-btn").click();

    // Scope al modal · "Solo lectura" también aparece en los blurbs de las
    // cards del grid (strict-mode si no se acota). SecurityModal R29 list.
    const modal = page.getByTestId("cloud-connect-modal");
    await expect(modal).toBeVisible();
    await expect(modal.getByText(/Solo lectura/i)).toBeVisible();
    await expect(modal.getByText(/Revocable en 1 click/i)).toBeVisible();
    await expect(modal.getByText(/Tokens cifrados/i)).toBeVisible();
  });
});
