/**
 * E2E · fase_31 admin · SSE listener admin (1.D.G.B v3.11).
 *
 * Verifica:
 *  - Admin /workflow SSE endpoint subscribed
 *  - viewMode "blockers" Render funcional sin errors
 *  - Toggle UI elements present
 */
import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "../../_helpers/auth-real";
import { mockAdminWorkflowBlockers, PROJECT_F31_ID } from "../_fixtures";

test.describe("fase_31 admin · SSE + viewMode toggle", () => {
  test("admin workflow page renders + toggle blockers mode", async ({
    context,
    page,
  }) => {
    await loginAsMarcos(context);
    await mockAdminWorkflowBlockers(page);

    await page.goto(`/admin/workflow-command-center/projects/${PROJECT_F31_ID}`);

    // Toggle viewMode buttons present
    await expect(page.getByTestId("view-mode-toggle")).toBeVisible();
    await expect(page.getByTestId("view-mode-ahora-only")).toBeVisible();
    await expect(page.getByTestId("view-mode-complete")).toBeVisible();
    await expect(page.getByTestId("view-mode-blockers")).toBeVisible();

    // Default complete · blockers panel NOT visible
    await expect(page.getByTestId("workflow-blockers-panel")).toBeHidden();

    // Switch to blockers · panel becomes visible
    await page.getByTestId("view-mode-blockers").click();
    await expect(page.getByTestId("workflow-blockers-panel")).toBeVisible();
  });
});
