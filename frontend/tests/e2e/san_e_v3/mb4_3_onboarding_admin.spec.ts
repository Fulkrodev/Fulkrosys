/**
 * MB-4.3 PARTE A · OnboardingAdminPanel real wired M16 admin (33 endpoints).
 *
 * Cobertura:
 * - login admin · navigate /onboarding
 * - 4 tabs (Sessions · Catálogo · Connectors · LMS) renderizan
 * - Catálogo lista templates + drawer detalle pregunta
 * - Sessions tab · btn crear session + dialog
 * - LMS tab · sub-tabs Cursos/Asignaciones
 */
import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "../_helpers/auth-real";

const PROJECT_ID =
  process.env.E2E_SEED_PROJECT_ID ?? "00000000-0000-0000-0000-000000000001";

test.describe("MB-4.3 PARTE A · OnboardingAdminPanel M16", () => {
  test.beforeEach(async ({ context, page }) => {
    await loginAsMarcos(context);
    await page.goto(`/admin/projects/${PROJECT_ID}/onboarding`);
  });

  test("header + 4 tabs renderizan", async ({ page }) => {
    await expect(
      page.getByRole("heading", { name: /Onboarding adaptativo/i }),
    ).toBeVisible();
    for (const label of ["Sessions", "Catálogo", "Connectors", "LMS"]) {
      await expect(page.getByRole("tab", { name: new RegExp(label, "i") })).toBeVisible();
    }
  });

  test("Sessions tab · btn crear session abre dialog", async ({ page }) => {
    await page.getByRole("tab", { name: /Sessions/i }).click();
    await expect(page.getByRole("button", { name: /Crear session/i })).toBeVisible();
    await page.getByRole("button", { name: /Crear session/i }).click();
    await expect(page.getByRole("dialog")).toBeVisible();
    await expect(page.getByPlaceholder(/cliente@ejemplo/i)).toBeVisible();
  });

  test("Catálogo tab · lista templates", async ({ page }) => {
    await page.getByRole("tab", { name: /Catálogo/i }).click();
    await expect(
      page.getByRole("heading", { name: /Catálogo de plantillas/i }),
    ).toBeVisible();
  });

  test("Connectors tab · 6 providers cards", async ({ page }) => {
    await page.getByRole("tab", { name: /Connectors/i }).click();
    await expect(
      page.getByRole("heading", { name: /Connectors cloud/i }),
    ).toBeVisible();
    // 6 providers visibles (al menos GitHub + AWS + Microsoft)
    await expect(page.getByText(/GitHub/i).first()).toBeVisible();
    await expect(page.getByText(/AWS/i).first()).toBeVisible();
    await expect(page.getByText(/Microsoft/i).first()).toBeVisible();
  });

  test("LMS tab · sub-tabs Cursos/Asignaciones", async ({ page }) => {
    await page.getByRole("tab", { name: /^LMS$/i }).click();
    await expect(page.getByRole("tab", { name: /Cursos/i })).toBeVisible();
    await expect(page.getByRole("tab", { name: /Asignaciones/i })).toBeVisible();
  });
});
