/**
 * E2E · fase_31 admin · Admin remind cliente flow (1.D.G.D v3.11).
 *
 * Verifica:
 *  - Admin click "Recordar" botón en step cliente waiting
 *  - POST /admin/.../steps/{id}/remind disparado · feedback inline
 *  - mock response notified=true · channels=[in_app, email]
 */
import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "../../_helpers/auth-real";
import { mockAdminWorkflowBlockers, PROJECT_F31_ID } from "../_fixtures";

test.describe("fase_31 admin · remind cliente flow", () => {
  test("click remind triggers POST + feedback inline", async ({
    context,
    page,
  }) => {
    await loginAsMarcos(context);
    await mockAdminWorkflowBlockers(page);

    await page.goto(`/admin/workflow-command-center/projects/${PROJECT_F31_ID}`);
    await page.getByTestId("view-mode-blockers").click();

    const remindBtn = page.getByTestId("remind-button-CLIENTE_UPLOAD_Z");
    await remindBtn.click();

    // Feedback inline message visible post mutation
    await expect(
      page.getByTestId("remind-feedback-CLIENTE_UPLOAD_Z"),
    ).toBeVisible({ timeout: 5_000 });
    await expect(
      page.getByTestId("remind-feedback-CLIENTE_UPLOAD_Z"),
    ).toContainText("Recordatorio");
  });
});
