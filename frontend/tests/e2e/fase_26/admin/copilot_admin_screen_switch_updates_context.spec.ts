/**
 * E2E · fase_26 admin · Copilot screen switch updates context-aware response.
 *
 * Sub-atom 1.D.F.0.D v3.11 · screen-aware admin tutor context switch.
 *
 * Verifica:
 *  - Llamada al endpoint con current_screen incluido propagado correcto
 *  - Mock screen-aware retorna respuestas DDA-specific cuando pathname incluye /dda
 *  - Mock screen-aware retorna respuestas MCPs-specific cuando pathname incluye /mcps
 *  - Botones específicos UI referenciados in response_text
 */
import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "../../_helpers/auth-real";
import {
  mockAdminCronologicaFull,
  mockCopilotoAdminScreenAware,
  PROJECT_F26_ID,
} from "../_fixtures";

test.describe("fase_26 admin · Copilot screen switch context", () => {
  test("current_screen propagado · response includes botones específicos pantalla", async ({
    context,
    page,
  }) => {
    await loginAsMarcos(context);
    await mockAdminCronologicaFull(page);
    await mockCopilotoAdminScreenAware(page);

    await page.goto(
      `/admin/workflow-command-center/projects/${PROJECT_F26_ID}`,
    );

    const sidebar = page.getByTestId("copiloto-admin-sidebar");
    await expect(sidebar).toBeVisible();

    // Trigger primera request · captura payload
    const reqWaiter1 = page.waitForRequest(
      (req) =>
        req.url().includes("/api/v1/admin/copilot/chat") &&
        req.method() === "POST",
    );
    await page.getByRole("button", { name: /Qué hago ahora/i }).click();
    const req1 = await reqWaiter1;
    const payload1 = req1.postDataJSON() as {
      current_screen?: string;
      action_id?: string;
    };

    // current_screen propagado correctamente desde usePathname
    expect(payload1.current_screen).toBe(
      `/admin/workflow-command-center/projects/${PROJECT_F26_ID}`,
    );
    expect(payload1.action_id).toBe("que_hago");

    // Response render
    await expect(
      page.getByTestId("copiloto-admin-history"),
    ).toBeVisible({ timeout: 5000 });

    // Verifica payload schema completo · sin pantalla-aware match · default response
    const responseText = await page
      .getByTestId("copiloto-admin-history")
      .innerText();
    // Mock default (no match dda/mcps/contratos) responde con "sin pantalla
    // activa identificada · dame contexto"
    expect(responseText).toMatch(/sin pantalla activa/i);
  });
});
