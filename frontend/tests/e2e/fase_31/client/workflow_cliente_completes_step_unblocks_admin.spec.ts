/**
 * E2E · fase_31 cliente · ClientNextActionCard render + CTA (1.D.G.E v3.11).
 *
 * Verifica:
 *  - Card "Tu siguiente acción" prominent CTA rendered
 *  - Step actor=cliente status=available muestra correctly
 *  - CTA button con cta_url Link funcional
 */
import { expect, test } from "@playwright/test";

import { loginAsClient } from "../../_helpers/auth-real";
import { mockClientWorkflowCrossActor } from "../_fixtures";

test.describe("fase_31 cliente · next action card", () => {
  test("renders 'Tu siguiente acción' card cliente actor available", async ({
    page,
  }) => {
    await loginAsClient(page);
    await mockClientWorkflowCrossActor(page);

    await page.goto("/client-portal/workflow");

    await expect(page.getByTestId("client-next-action-card")).toBeVisible();
    await expect(page.getByTestId("next-action-title")).toContainText(
      "Subir documento autoridad",
    );
    await expect(page.getByTestId("next-action-cta")).toBeVisible();
    await expect(page.getByTestId("next-action-cta")).toHaveAttribute(
      "href",
      "/client-portal/files",
    );
  });
});
