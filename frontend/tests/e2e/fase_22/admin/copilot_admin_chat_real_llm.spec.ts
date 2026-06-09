/**
 * E2E · Test 1 fase_22 · admin · Copilot LLM real chat render.
 *
 * Sub-atom 1.D.B.2 v3.11 · swap-in admin LLM real Sonnet 4.6.
 *
 * Verifica:
 *   - Admin sidebar render · mode badge "Tutor" default
 *   - QuickAction "que_hago" trigger chat request
 *   - Response LLM Sonnet render (is_stub=false · LLM badge upgrade)
 *   - History entry data-testid copiloto-admin-entry-llm
 */
import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "../../_helpers/auth-real";
import {
  mockCopilotoAdminChatLLM,
  mockCronologicaForCopilotAdmin,
  PROJECT_DDD_ID,
} from "../_fixtures";

test.describe("fase_22 admin · Copilot admin LLM real chat", () => {
  test("QuickAction trigger · LLM response render · LLM badge upgrade", async ({
    context,
    page,
  }) => {
    await loginAsMarcos(context);
    await mockCronologicaForCopilotAdmin(page);
    await mockCopilotoAdminChatLLM(page);

    // FIX ruta UI evolucionada: el CopilotoAdminSidebar (con estos test-ids)
    // se renderiza en la vista cronológica del proyecto · /workflow (vía
    // ProjectCronologicaView), NO en /workspace (que ahora monta WorkspacePanel).
    await page.goto(`/admin/projects/${PROJECT_DDD_ID}/workflow`);

    const sidebar = page.getByTestId("copiloto-admin-sidebar");
    await expect(sidebar).toBeVisible();

    // Initial state · "Tutor" badge default (NO history yet)
    await expect(
      page.getByTestId("copiloto-admin-mode-badge"),
    ).toHaveText(/Tutor/i);

    // QuickAction "que_hago" trigger
    await page.getByRole("button", { name: /Qué hago ahora/i }).click();

    // History entry LLM rendered
    await expect(page.getByTestId("copiloto-admin-history")).toBeVisible({
      timeout: 5000,
    });
    await expect(
      page.getByTestId("copiloto-admin-entry-llm").first(),
    ).toBeVisible();

    // Mode badge upgraded to "LLM" post-response
    await expect(
      page.getByTestId("copiloto-admin-mode-badge"),
    ).toHaveText(/LLM/i);

    // Response text includes DICAT con definition trigger (R30 OK)
    await expect(page.getByText(/DICAT/i).first()).toBeVisible();
  });
});
