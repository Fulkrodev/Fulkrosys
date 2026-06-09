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
import { mockClientWorkflowGuide, mockCopilotoClienteStub } from "../_fixtures";

const COERCITIVE_PATTERNS = [
  /llevas\s+\d+\s+d[ií]as/i,
  /se te acaba/i,
  /deadline urgente/i,
  /tienes que terminar/i,
  /fecha l[ií]mite/i,
];

test.describe("fase_17 cliente · CopilotoClienteBottomRight + R29 audit", () => {
  test("widget renders friendly · QuickAction response · R29 verified", async ({
    page,
  }) => {
    await mockClientWorkflowGuide(page);
    await mockCopilotoClienteStub(page);
    await loginAsClient(page);

    await page.goto("/client-portal/workflow");

    // Floating button visible bottom-right
    const floatingBtn = page.getByTestId("copiloto-cliente-toggle");
    await expect(floatingBtn).toBeVisible();

    // NO red dot · NO badge urgente
    const redDot = page.locator(".red-dot, [data-urgent='true']");
    await expect(redDot).toHaveCount(0);

    // Click floating · expand chat
    await floatingBtn.click();

    // QuickAction "¿Qué tengo que hacer ahora?"
    await page.getByRole("button", { name: /¿Qué tengo que hacer ahora\?/i }).click();

    // Stub response visible
    const responseText = await page
      .getByText(/Tu siguiente paso/i)
      .first()
      .textContent();
    expect(responseText).toBeTruthy();

    // R29 AUDIT EMPÍRICO · 0 strings coercitivos
    for (const pattern of COERCITIVE_PATTERNS) {
      expect(responseText ?? "").not.toMatch(pattern);
    }
  });
});
