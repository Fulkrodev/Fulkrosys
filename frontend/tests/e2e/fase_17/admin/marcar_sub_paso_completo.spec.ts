/**
 * E2E · Test 3 fase_17 · admin · marcar sub-paso completo (advanceStep mutation).
 *
 * Sub-atom 1.C.D.E v3.8 · 1.C.D.B.3 (advance mutation + toast success).
 *
 * Verifica:
 *   - Click "Marcar completo" en sub-paso AHORA
 *   - Mutation POST → /admin/workflow-command-center/projects/{id}/steps/{template_id}/advance
 *   - Toast success "Paso ... marcado completo"
 */
import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "../../_helpers/auth-real";
import {
  MOCK_ENRICHED_STEP_AHORA,
  PROJECT_A_ID,
  mockAdminWorkflowCommandCenter,
} from "../_fixtures";

test.describe("fase_17 admin · marcar sub-paso completo", () => {
  test("click 'Marcar completo' triggers advance mutation + toast", async ({
    page,
    context,
  }) => {
    await loginAsMarcos(context);
    await mockAdminWorkflowCommandCenter(page);

    let advanceCalled = false;
    await page.route(
      new RegExp(
        `/api/v1/admin/workflow-command-center/projects/${PROJECT_A_ID}/steps/.+/advance`,
      ),
      async (route) => {
        advanceCalled = true;
        await route.fulfill({
          status: 200,
          json: {
            task_id: "task-aaaa-bbbb",
            template_id: MOCK_ENRICHED_STEP_AHORA.template_id,
            status: "completed",
            completed_at: "2026-05-20T12:00:00Z",
          },
        });
      },
    );

    await page.goto(`/admin/workflow-command-center/projects/${PROJECT_A_ID}`);

    const marcarBtn = page.getByRole("button", { name: /Marcar completo/i }).first();
    await expect(marcarBtn).toBeVisible();
    await marcarBtn.click();

    // Mutation fired
    await expect.poll(() => advanceCalled).toBe(true);
    // Toast visible
    await expect(page.getByText(/marcado completo/i)).toBeVisible({
      timeout: 5_000,
    });
  });
});
