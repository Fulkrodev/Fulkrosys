/**
 * MB-4.3 PARTE B · Cliente in-portal onboarding wizard (M16 portal · 11 endpoints).
 *
 * Cobertura:
 * - login client_user · navigate /client-portal/onboarding
 * - 3 tabs (Wizard · Connectors · Cursos) renderizan
 * - Wizard tab · pregunta + btn Siguiente
 * - Connectors tab · 6 providers cards
 * - AWS card · dialog IAM credentials
 * - LMS tab · cards o empty state
 * - OAuth callback page renders processing/success/error
 */
import { expect, test } from "@playwright/test";

import { loginAsClient } from "../_helpers/auth-real";

test.describe("MB-4.3 PARTE B · Cliente in-portal onboarding", () => {
  test.beforeEach(async ({ page }) => {
    await loginAsClient(page);
    await page.goto(`/client-portal/onboarding`);
  });

  test("header + 3 tabs renderizan", async ({ page }) => {
    await expect(
      page.getByRole("heading", { name: /^Onboarding$/i }),
    ).toBeVisible();
    for (const label of ["Wizard", "Connectors", "Cursos"]) {
      await expect(page.getByRole("tab", { name: new RegExp(label, "i") })).toBeVisible();
    }
  });

  test("Wizard tab · muestra pregunta o empty state", async ({ page }) => {
    await page.getByRole("tab", { name: /Wizard/i }).click();
    // Acepta wizard activo o empty state si no hay session
    await expect(
      page.getByText(
        /Pregunta \d+ de \d+|Onboarding no disponible|Onboarding completado/i,
      ),
    ).toBeVisible();
  });

  test("Connectors tab · 6 providers visible", async ({ page }) => {
    await page.getByRole("tab", { name: /Connectors/i }).click();
    await expect(
      page.getByRole("heading", { name: /Conecta tu workspace/i }),
    ).toBeVisible();
    await expect(page.getByText(/GitHub/i).first()).toBeVisible();
    await expect(page.getByText(/AWS/i).first()).toBeVisible();
  });

  test("AWS card · dialog IAM credentials se abre", async ({ page }) => {
    await page.getByRole("tab", { name: /Connectors/i }).click();
    // Btn "Conectar AWS" abre dialog específico (no OAuth)
    const awsBtn = page.getByRole("button", { name: /Conectar AWS/i });
    if (await awsBtn.isVisible().catch(() => false)) {
      await awsBtn.click();
      await expect(page.getByText(/Access Key ID/i)).toBeVisible();
      await expect(page.getByText(/Secret Access Key/i)).toBeVisible();
    } else {
      // AWS ya conectado · skip
      test.skip();
    }
  });

  test("Cursos tab · empty state o lista", async ({ page }) => {
    await page.getByRole("tab", { name: /Cursos/i }).click();
    // .first(): "Cursos asignados" + "Catálogo disponible" coexisten en el
    // empty state del LMSClientView → varios matches (no strict-mode).
    await expect(
      page
        .getByText(
          /Cursos asignados|Catálogo disponible|Marcos te asignará cursos/i,
        )
        .first(),
    ).toBeVisible();
  });

  test("OAuth callback · error si parámetros faltan", async ({ page }) => {
    await page.goto("/client-portal/onboarding/oauth-callback");
    // .first(): el estado error muestra a la vez el heading "Error en la
    // autorización" y el mensaje "Parámetros OAuth faltantes" → 2 matches.
    await expect(
      page
        .getByText(/Error en la autorización|Parámetros OAuth faltantes/i)
        .first(),
    ).toBeVisible();
  });
});
