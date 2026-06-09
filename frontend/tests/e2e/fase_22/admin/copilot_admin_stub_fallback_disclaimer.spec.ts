/**
 * E2E · Test 4 fase_22 · admin · Stub fallback disclaimer visible.
 *
 * Sub-atom 1.D.B.2 v3.11 · graceful fallback cuando LLM disabled/fail.
 *
 * Verifica:
 *   - Backend retorna is_stub=true (fallback stub) · frontend distingue
 *   - History entry data-testid copiloto-admin-entry-stub
 *   - Disclaimer inline "stub fallback" visible (sostener honest tracking)
 *   - Mode badge sostiene "Tutor" (NO upgrade LLM)
 */
import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "../../_helpers/auth-real";
import {
  mockCopilotoAdminChatStubFallback,
  mockCronologicaForCopilotAdmin,
  PROJECT_DDD_ID,
} from "../_fixtures";

test.describe("fase_22 admin · Stub fallback disclaimer", () => {
  test("is_stub=true response · disclaimer 'stub fallback' visible", async ({
    context,
    page,
  }) => {
    await loginAsMarcos(context);
    await mockCronologicaForCopilotAdmin(page);
    await mockCopilotoAdminChatStubFallback(page);

    // FIX ruta UI evolucionada: el CopilotoAdminSidebar vive en /workflow
    // (ProjectCronologicaView), NO en /workspace (ahora WorkspacePanel).
    await page.goto(`/admin/projects/${PROJECT_DDD_ID}/workflow`);

    // QuickAction trigger
    await page.getByRole("button", { name: /Briefing reunión/i }).click();

    // History entry stub visible
    await expect(
      page.getByTestId("copiloto-admin-entry-stub").first(),
    ).toBeVisible({ timeout: 5000 });

    // Disclaimer "stub fallback" inline visible
    await expect(page.getByText(/stub fallback/i).first()).toBeVisible();

    // Mode badge sostiene "Tutor" (NO upgrade · stub fallback NO marca LLM)
    await expect(
      page.getByTestId("copiloto-admin-mode-badge"),
    ).toHaveText(/Tutor/i);
  });
});
