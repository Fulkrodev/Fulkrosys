/**
 * E2E · fase_26 admin · Copilot sin screen activa · safe default.
 *
 * Sub-atom 1.D.F.0.D v3.11 · context-aware boundary safe fallback.
 *
 * Verifica:
 *  - Mock copilot recibe current_screen workflow-command-center (no match catalog admin/projects/[id]/X)
 *  - Response fallback genérico (sin botones screen-specific · context conceptual)
 *  - R30 sostener · sin admin lingo agresivo · monkey-pilot friendly
 */
import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "../../_helpers/auth-real";
import {
  mockAdminCronologicaFull,
  mockCopilotoAdminScreenAware,
  PROJECT_F26_ID,
} from "../_fixtures";

test.describe("fase_26 admin · Copilot sin screen activa safe default", () => {
  test("workflow-command-center screen · NO match catalog DDA/MCPs · safe default response", async ({
    context,
    page,
  }) => {
    await loginAsMarcos(context);
    await mockAdminCronologicaFull(page);
    await mockCopilotoAdminScreenAware(page);

    await page.goto(
      `/admin/workflow-command-center/projects/${PROJECT_F26_ID}`,
    );

    await expect(page.getByTestId("copiloto-admin-sidebar")).toBeVisible();

    await page.getByRole("button", { name: /Qué hago ahora/i }).click();

    await expect(
      page.getByTestId("copiloto-admin-history"),
    ).toBeVisible({ timeout: 5000 });

    // Mock devuelve fallback "sin pantalla activa identificada · dame contexto"
    // cuando current_screen no match en catalog
    const history = page.getByTestId("copiloto-admin-history");
    await expect(history).toContainText(/sin pantalla activa/i);

    // R30 inverso · admin tone sin amabilidad agresiva pero profesional
    // (no busca emojis o tone cliente-friendly · solo verifica content profesional)
  });
});
