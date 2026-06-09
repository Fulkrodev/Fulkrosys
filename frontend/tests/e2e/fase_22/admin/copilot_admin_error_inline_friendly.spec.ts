/**
 * E2E · Test 3 fase_22 · admin · Error inline friendly (NO red alarm).
 *
 * Sub-atom 1.D.B.2.2 v3.11 · UX enrichment admin error fallback.
 *
 * Verifica:
 *   - Backend error 500 → frontend onError handler
 *   - History entry data-testid copiloto-admin-entry-error visible
 *   - Tone profesional admin friendly (NO brusco · m_observability ref)
 *   - Amber color border NO red alarm
 *   - Mode badge sostiene "Tutor" (error NO promueve a LLM badge)
 */
import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "../../_helpers/auth-real";
import {
  mockCopilotoAdminChatError,
  mockCronologicaForCopilotAdmin,
  PROJECT_DDD_ID,
} from "../_fixtures";

test.describe("fase_22 admin · Error inline friendly admin", () => {
  test("backend error → entry-error friendly tone · NO red alarm", async ({
    context,
    page,
  }) => {
    await loginAsMarcos(context);
    await mockCronologicaForCopilotAdmin(page);
    await mockCopilotoAdminChatError(page);

    // FIX ruta UI evolucionada: el CopilotoAdminSidebar vive en /workflow
    // (ProjectCronologicaView), NO en /workspace (ahora WorkspacePanel).
    await page.goto(`/admin/projects/${PROJECT_DDD_ID}/workflow`);

    // QuickAction trigger error response
    await page.getByRole("button", { name: /Draft email/i }).click();

    // History entry error visible
    const errorEntry = page
      .getByTestId("copiloto-admin-entry-error")
      .first();
    await expect(errorEntry).toBeVisible({ timeout: 5000 });

    // Tone profesional admin · sugiere m_observability log
    const text = await errorEntry.innerText();
    expect(text.toLowerCase()).toContain("problema técnico");
    expect(text.toLowerCase()).toContain("intenta de nuevo");

    // Amber color (NO red alarm) · class includes amber
    const classes = (await errorEntry.getAttribute("class")) ?? "";
    expect(classes).toMatch(/amber/i);

    // Mode badge sostiene "Tutor" (NO upgrade · error NO marca LLM real)
    await expect(
      page.getByTestId("copiloto-admin-mode-badge"),
    ).toHaveText(/Tutor/i);
  });
});
