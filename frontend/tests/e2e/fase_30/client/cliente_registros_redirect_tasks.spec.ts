/**
 * E2E · fase_30 cliente · /registros REDIRECT /tasks.
 *
 * Sub-atom 1.D.F.bis.III.B v3.11.
 *
 * Verifica:
 *  - /registros muestra UI transitoria explicativa
 *  - useRouter.replace dispara navegación a /tasks (asserted via final URL pattern)
 *  - Link manual fallback visible para click directo
 */
import { expect, test } from "@playwright/test";

import { loginAsClient } from "../../_helpers/auth-real";
import { mockClienteIndispensable } from "../_fixtures";

test.describe("fase_30 cliente · /registros redirect /tasks", () => {
  test("UI transitoria + redirect automatico + link manual", async ({
    page,
  }) => {
    await loginAsClient(page);
    await mockClienteIndispensable(page);

    await page.goto("/client-portal/registros");

    // UI transitoria render
    await expect(
      page.getByTestId("cliente-registros-redirect"),
    ).toBeVisible();
    await expect(
      page.getByText(/Los registros los lleva tu consultor/i),
    ).toBeVisible();
    await expect(
      page.getByText(/Redirigiendo a/i).first(),
    ).toBeVisible();

    // Link manual fallback
    await expect(
      page.getByTestId("cliente-registros-redirect-link"),
    ).toBeVisible();

    // Redirect automatic (setTimeout 2.5s → router.replace). El portal cliente
    // monta SSE (useClientProject) en /tasks · "load" nunca settlea (EventSource
    // vivo) y waitForURL con waitUntil:"load" (default) hacía timeout aunque la
    // URL SÍ cambia. Usamos waitUntil:"commit" (solo cambio de URL) · timeout
    // generoso (>2.5s del setTimeout + margen).
    await page.waitForURL("**/client-portal/tasks", {
      timeout: 8000,
      waitUntil: "commit",
    });
    await expect(page).toHaveURL(/\/client-portal\/tasks/);
  });
});
