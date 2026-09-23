/**
 * E2E · fase_21 · mientras llega la respuesta hay un indicador, y desaparece.
 */
import { expect, test } from "@playwright/test";

import { loginAsClient } from "../../_helpers/auth-real";
import { RESPUESTA_DOCK_AMABLE, abrirDockYPreguntar, mockCopilotoDockStream } from "../_fixtures";

test.describe("fase_21 client · Copilot cliente typing indicator", () => {
  test("indicador accesible durante la espera · desaparece al responder", async ({ page }) => {
    await loginAsClient(page);
    await mockCopilotoDockStream(page, RESPUESTA_DOCK_AMABLE, { retrasoMs: 1_000 });
    await page.goto("/client-portal/workflow");
    await abrirDockYPreguntar(page);

    await expect(page.getByTestId("copiloto-typing")).toBeVisible();
    await expect(page.getByLabel(/El asistente está pensando/i)).toBeVisible();
    await expect(page.getByTestId("copiloto-typing")).toHaveCount(0, { timeout: 5_000 });
  });
});
