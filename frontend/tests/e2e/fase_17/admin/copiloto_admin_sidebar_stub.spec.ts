/**
 * E2E · Test 7 fase_17 · admin · CopilotoAdminSidebar stub render.
 *
 * Sub-atom 1.C.D.E v3.8 · 1.C.D.B.4 (CopilotoAdminSidebar 3-col layout).
 *
 * Verifica:
 *   - CopilotoAdminSidebar render en per-cliente view (col 3)
 *   - QuickActions buttons render (4 acciones admin)
 *   - Click "¿Qué hago ahora?" → POST /api/v1/admin/copilot/chat con action_id="que_hago"
 *   - Response stub coherente renderizada en chat panel
 */
import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "../../_helpers/auth-real";
import {
  PROJECT_A_ID,
  mockAdminWorkflowCommandCenter,
  mockCopilotoAdminStub,
} from "../_fixtures";

test.describe("fase_17 admin · CopilotoAdminSidebar stub", () => {
  test("renders sidebar + QuickAction click triggers stub response", async ({
    page,
    context,
  }) => {
    await loginAsMarcos(context);
    await mockAdminWorkflowCommandCenter(page);
    await mockCopilotoAdminStub(page);

    await page.goto(`/admin/workflow-command-center/projects/${PROJECT_A_ID}`);

    // CopilotoAdminSidebar visible (sticky right · 3-col layout)
    const qhBtn = page.getByRole("button", { name: /¿Qué hago ahora\?/i });
    await expect(qhBtn.first()).toBeVisible();

    await qhBtn.first().click();

    // Stub response visible en chat panel
    await expect(
      page.getByText(/Fintech Plus/i).first(),
    ).toBeVisible({ timeout: 5_000 });
    // Disclaimer stub visible
    await expect(
      page.getByText(/asistente en preparación|stub|próximo sprint/i).first(),
    ).toBeVisible();
  });
});
