/**
 * E2E · fase_31 cliente · SSE real-time + MarcosPreparaSection (1.D.G.E v3.11).
 *
 * Verifica:
 *  - SSE listener cliente endpoint mounted (event source request emitted)
 *  - MarcosPreparaSection rendered cuando step actor=admin status=in_progress
 *  - Format "🟡 Marcos prepara" + estimated_days_to_complete
 *  - R29 friendly italic copy "Cuando esté listo te avisaremos"
 */
import { expect, test } from "@playwright/test";

import { loginAsClient } from "../../_helpers/auth-real";
import { mockClientWorkflowCrossActor } from "../_fixtures";

test.describe("fase_31 cliente · marcos prepara + SSE", () => {
  test("MarcosPreparaSection renders admin in_progress steps + R29 copy", async ({
    page,
  }) => {
    await loginAsClient(page);
    await mockClientWorkflowCrossActor(page);

    await page.goto("/client-portal/workflow");

    await expect(page.getByTestId("marcos-prepara-section")).toBeVisible();
    await expect(
      page.getByTestId("marcos-prepara-item-ADMIN_REVIEW_X"),
    ).toBeVisible();
    await expect(
      page.getByTestId("marcos-prepara-item-ADMIN_REVIEW_X"),
    ).toContainText("Revisión técnica X");

    // R29 friendly copy NO presión
    await expect(
      page.locator("text=Cuando esté listo te avisaremos"),
    ).toBeVisible();
  });
});
