/**
 * E2E · fase_21 · R29 en el copiloto de cliente: ni presion ni jerga interna.
 */
import { expect, test } from "@playwright/test";

import { loginAsClient } from "../../_helpers/auth-real";
import {
  ADMIN_LINGO_PATTERNS,
  COERCITIVE_PATTERNS,
  RESPUESTA_DOCK_AMABLE,
  abrirDockYPreguntar,
  mockCopilotoDockStream,
} from "../_fixtures";

test.describe("fase_21 client · R29 boundary audit empírico", () => {
  test("la conversacion no contiene patrones coercitivos ni jerga de administracion", async ({ page }) => {
    await loginAsClient(page);
    await mockCopilotoDockStream(page, RESPUESTA_DOCK_AMABLE);
    await page.goto("/client-portal/workflow");
    await abrirDockYPreguntar(page);

    const log = page.getByTestId("copiloto-messages");
    await expect(page.getByTestId("copiloto-msg-assistant").last()).toContainText(/categorización/i);
    const texto = (await log.innerText()).toLowerCase();
    for (const patron of COERCITIVE_PATTERNS) {
      expect(texto.includes(patron.toLowerCase()), `R29 · '${patron}' en: ${texto}`).toBeFalsy();
    }
    for (const patron of ADMIN_LINGO_PATTERNS) {
      expect(texto.includes(patron.toLowerCase()), `R30 inverso · '${patron}' en: ${texto}`).toBeFalsy();
    }
  });
});
