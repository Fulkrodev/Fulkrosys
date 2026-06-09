/**
 * E2E · Test 2 fase_21 · client · R29 boundary audit empírico LLM response.
 *
 * Sub-atom 1.D.B.1 v3.11 · CRÍTICO sostener R29.
 *
 * Verifica:
 *   - LLM response NO contiene patrones coercitivos (llevas · deadline urgente ·
 *     se acaba tiempo · tienes que ahora)
 *   - LLM response NO contiene admin lingo (evidence_type_id · audit trail · rbac)
 *   - Tono empático · 0 violations
 */
import { expect, test } from "@playwright/test";

import { loginAsClient } from "../../_helpers/auth-real";
import {
  ADMIN_LINGO_PATTERNS,
  COERCITIVE_PATTERNS,
  mockCopilotoClienteChatLLM,
} from "../_fixtures";

test.describe("fase_21 client · R29 boundary audit empírico", () => {
  test("LLM response NO contiene patrones coercitivos ni admin lingo", async ({
    page,
  }) => {
    await loginAsClient(page);
    await mockCopilotoClienteChatLLM(page);

    await page.goto("/client-portal/workflow");
    await page.getByTestId("copiloto-cliente-toggle").click();

    // Trigger "porque_importa" quick action
    await page.getByRole("button", { name: /Por qué es importante/i }).click();

    // Espera render response
    const log = page.getByTestId("copiloto-cliente-log");
    await expect(log).toBeVisible();
    await page.waitForTimeout(500);

    // Audit empírico texto completo log
    const logText = await log.innerText();
    const logTextLower = logText.toLowerCase();

    // R29 audit · 0 coercitive patterns
    for (const pattern of COERCITIVE_PATTERNS) {
      expect(
        logTextLower.includes(pattern.toLowerCase()),
        `R29 violation · coercitive pattern '${pattern}' found in: ${logText}`,
      ).toBeFalsy();
    }

    // R30 inverso · 0 admin lingo patterns cliente-facing
    for (const pattern of ADMIN_LINGO_PATTERNS) {
      expect(
        logTextLower.includes(pattern.toLowerCase()),
        `R30-inverso violation · admin lingo '${pattern}' found in: ${logText}`,
      ).toBeFalsy();
    }
  });
});
