/**
 * E2E · fase_21 · copiloto de cliente (CopilotoDock) · la respuesta llega y se lee.
 *
 * La respuesta del modelo se simula (el test mide la interfaz, no el modelo):
 * llega por SSE, se pinta como Markdown (sin "**" literales) y no hay aviso de
 * asistente en preparacion.
 */
import { expect, test } from "@playwright/test";

import { loginAsClient } from "../../_helpers/auth-real";
import { RESPUESTA_DOCK_AMABLE, abrirDockYPreguntar, mockCopilotoDockStream } from "../_fixtures";

test.describe("fase_21 client · copiloto de cliente responde", () => {
  test("accion rapida → respuesta visible, en Markdown renderizado", async ({ page }) => {
    await loginAsClient(page);
    await mockCopilotoDockStream(page, RESPUESTA_DOCK_AMABLE);
    await page.goto("/client-portal/workflow");
    await abrirDockYPreguntar(page);

    const respuesta = page.getByTestId("copiloto-msg-assistant").last();
    await expect(respuesta).toContainText(/DNI de tu proyecto ENS/i, { timeout: 5_000 });
    // Markdown renderizado: la negrita es <strong>, no asteriscos.
    await expect(respuesta.locator("strong")).toHaveText(/categorización/i);
    await expect(respuesta).not.toContainText("**");
    await expect(page.getByText(/asistente en preparación/i)).toHaveCount(0);
  });
});
