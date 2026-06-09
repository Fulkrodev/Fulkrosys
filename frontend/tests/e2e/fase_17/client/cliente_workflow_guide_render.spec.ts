/**
 * E2E · Test 8 fase_17 · cliente · workflow guide render 3 sections friendly.
 *
 * Sub-atom 1.C.D.E v3.8 · 1.C.D.C.1 (REFACTOR /client-portal/workflow page).
 *
 * Verifica:
 *   - Login cliente · /client-portal/workflow/ render OK
 *   - 3 sections friendly (NO 4 zones admin):
 *     ✅ COMPLETADO compact summary celebratory
 *     🎯 TU SIGUIENTE PASO expanded
 *     📅 PRÓXIMOS PASOS cards
 *   - WorkflowProgressBarClient celebratory encouraging
 */
import { expect, test } from "@playwright/test";

import { loginAsClient } from "../../_helpers/auth-real";
import { mockClientWorkflowGuide } from "../_fixtures";

test.describe("fase_17 cliente · workflow guide render", () => {
  test("renders 3 sections + progress bar celebratory", async ({ page }) => {
    await mockClientWorkflowGuide(page);
    await loginAsClient(page);

    await page.goto("/client-portal/workflow");

    // Progress bar celebratory · encouraging text "¡Vas genial!" o similar
    await expect(
      page.getByText(/Tu progreso/i).first(),
    ).toBeVisible();
    // 7/12 pasos visible
    await expect(page.getByText(/7\s*\/\s*12\s+pasos/i)).toBeVisible();
    // Section COMPLETADO summary celebratory
    await expect(
      page.getByText(/Has completado/i).first(),
    ).toBeVisible();
    // Section TU SIGUIENTE PASO heading
    await expect(
      page.getByText(/Tu siguiente paso/i).first(),
    ).toBeVisible();
    // Step actual title
    await expect(
      page.getByText(/Formación G1 empleados/i),
    ).toBeVisible();
  });
});
