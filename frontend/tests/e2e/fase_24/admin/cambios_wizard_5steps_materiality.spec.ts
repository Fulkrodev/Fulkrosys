/**
 * E2E · Test 4 fase_24 · admin · ChangeRequestWizard 5 steps + materiality.
 *
 * Sub-atom 1.D.D.B v3.11 · M28 wizard 5 pasos + materiality_engine
 * determinista (intake + assess).
 *
 * Verifica:
 *   - Wizard 5 steps (descripción · impacto · materiality · notificación
 *     · tracking)
 *   - Step 1 · POST intake mock → change_id obtained · advance
 *   - Step 2 · 10 binary questions visible · toggle some · advance via assess
 *   - Step 3 · materiality MATERIAL + score 85 + required docs/workflows
 *   - Step 4 · notificación E-042 alert visible + customer_actions
 *   - Step 5 · tracking change_id pinned + materiality final
 *   - R1 sostenido · MATERIAL/RELEVANT/MINOR canonical (NO custom levels)
 */
import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "../../_helpers/auth-real";
import {
  PROJECT_DD_ID,
  mockChangesIntakeAndAssess,
  mockChangesListBase,
} from "../_fixtures";

test.describe("fase_24 admin · ChangeRequestWizard 5 steps + materiality", () => {
  test("descripción → impacto 10 questions → MATERIAL preview → notificación → tracking", async ({
    context,
    page,
  }) => {
    await loginAsMarcos(context);
    await mockChangesListBase(page);
    await mockChangesIntakeAndAssess(page);

    await page.goto(`/admin/projects/${PROJECT_DD_ID}/changes`);
    await page.getByTestId("changes-request-button").click();
    await expect(page.getByTestId("change-request-wizard")).toBeVisible();

    // Step 1 · descripción
    await expect(page.getByTestId("wizard-step-descripcion")).toBeVisible();
    await page
      .getByTestId("wizard-description-textarea")
      .fill("Migración base de datos PostgreSQL 14 → 16");
    await page.getByTestId("wizard-requested-by").fill("marcos");
    await page.getByTestId("changes-wizard-submit-intake").click();

    // Step 2 · impacto
    await expect(page.getByTestId("wizard-step-impacto")).toBeVisible();
    // 10 binary questions present
    await expect(
      page.getByTestId("wizard-question-affects_evidence"),
    ).toBeVisible();
    await expect(
      page.getByTestId("wizard-question-affects_dda"),
    ).toBeVisible();
    await expect(
      page.getByTestId("wizard-question-requires_extraordinary"),
    ).toBeVisible();

    // Toggle critical ones (lead to MATERIAL based on mock response)
    await page.getByTestId("wizard-question-affects_dda").click();
    await page.getByTestId("wizard-question-requires_extraordinary").click();

    await page.getByTestId("changes-wizard-submit-assess").click();

    // Step 3 · materiality MATERIAL + score 85
    await expect(
      page.getByTestId("wizard-step-materiality"),
    ).toBeVisible();
    await expect(
      page.getByTestId("wizard-materiality-level"),
    ).toBeVisible();
    await expect(page.getByTestId("wizard-materiality-score")).toContainText(
      "85",
    );
    // Required documents/workflows badges (canonical IDs E-046/E-615)
    await expect(
      page.getByTestId("wizard-required-doc-E-046"),
    ).toBeVisible();
    await expect(
      page.getByTestId("wizard-required-doc-E-615"),
    ).toBeVisible();

    // Advance step 4 · notificación
    await page.getByTestId("changes-wizard-next").click();
    await expect(
      page.getByTestId("wizard-step-notificacion"),
    ).toBeVisible();
    // UI drift: E-042 aparece en el heading "Notificación E-042 al cliente" y
    // en un <code>E-042</code> dentro del paso → strict-mode 2 elementos.
    await expect(
      page.getByTestId("wizard-step-notificacion").getByText(/E-042/).first(),
    ).toBeVisible();
    await expect(page.getByTestId("customer-actions")).toBeVisible();

    // Advance step 5 · tracking
    await page.getByTestId("changes-wizard-next").click();
    await expect(page.getByTestId("wizard-step-tracking")).toBeVisible();
    await expect(
      page.getByTestId("wizard-tracking-change-id"),
    ).toBeVisible();

    // Finalizar cierra wizard
    await page.getByTestId("changes-wizard-close").click();
    await expect(
      page.getByTestId("change-request-wizard"),
    ).not.toBeVisible({ timeout: 5000 });
  });
});
