/**
 * E2E · Test 11 fase_17 · cliente · CopilotoClienteBottomRight + R29 audit empírico.
 *
 * Sub-atom 1.C.D.E v3.8 · 1.C.D.C.3 + R29 sostener.
 *
 * Verifica:
 *   - CopilotoClienteBottomRight floating visible bottom-right
 *   - Color SUAVE (azul · NO rojo urgente)
 *   - NO red dot · NO badge urgente · NO popup intrusivo auto-open
 *   - Click floating · expand chat panel
 *   - QuickAction "¿Qué tengo que hacer ahora?" → POST stub
 *   - R29 AUDIT EMPÍRICO: response_text 0 coercitivos
 */
import { expect, test } from "@playwright/test";

import { loginAsClient } from "../../_helpers/auth-real";
import { mockClientWorkflowGuide } from "../_fixtures";
import {
  RESPUESTA_DOCK_AMABLE,
  abrirDockYPreguntar,
  mockCopilotoDockStream,
} from "../../fase_21/_fixtures";

const COERCITIVE_PATTERNS = [
  /llevas\s+\d+\s+d[ií]as/i,
  /se te acaba/i,
  /deadline urgente/i,
  /tienes que terminar/i,
  /fecha l[ií]mite/i,
];

test.describe("fase_17 cliente · CopilotoClienteBottomRight + R29 audit", () => {
  test("dock sin alarma · accion rapida · respuesta sin presion (R29)", async ({ page }) => {
    await mockClientWorkflowGuide(page);
    await loginAsClient(page);
    await mockCopilotoDockStream(page, RESPUESTA_DOCK_AMABLE);
    await page.goto("/client-portal/workflow");

    await expect(page.getByTestId("copiloto-dock-toggle")).toBeVisible();
    // Sin punto rojo ni distintivo de urgencia.
    await expect(page.locator(".red-dot, [data-urgent='true']")).toHaveCount(0);

    await abrirDockYPreguntar(page);
    const respuesta = page.getByTestId("copiloto-msg-assistant").last();
    await expect(respuesta).toContainText(/siguiente paso/i);
    const texto = (await respuesta.textContent()) ?? "";
    for (const pattern of COERCITIVE_PATTERNS) {
      expect(texto).not.toMatch(pattern);
    }
  });
});
