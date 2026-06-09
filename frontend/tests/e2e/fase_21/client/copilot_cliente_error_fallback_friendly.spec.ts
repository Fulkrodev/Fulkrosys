/**
 * E2E · Test 4 fase_21 · client · Error fallback friendly system_error.
 *
 * Sub-atom 1.D.B.1.2 v3.11 · UX enrichment graceful error.
 *
 * Verifica:
 *   - Backend error 500 → frontend onError trigger
 *   - system_error entry inline en log (NO solo toast efímero)
 *   - Friendly tone error (R29 sostener · "Sigo aquí cuando me necesites")
 *   - Color amber-50 NO rojo alarma
 */
import { expect, test } from "@playwright/test";

import { loginAsClient } from "../../_helpers/auth-real";
import { mockCopilotoClienteChatError } from "../_fixtures";

test.describe("fase_21 client · Copilot cliente error fallback", () => {
  test("backend error → system_error inline friendly tone R29 sostener", async ({
    page,
  }) => {
    await loginAsClient(page);
    await mockCopilotoClienteChatError(page);

    await page.goto("/client-portal/workflow");
    await page.getByTestId("copiloto-cliente-toggle").click();
    await page.getByRole("button", { name: /Necesito ayuda con algo/i }).click();

    // Espera system_error entry inline en log
    const systemError = page
      .getByTestId("copiloto-cliente-msg-system_error")
      .first();
    await expect(systemError).toBeVisible({ timeout: 5000 });

    // Tono friendly · NO presión · sostener R29
    const text = await systemError.innerText();
    expect(text.toLowerCase()).toContain("dificultades técnicas");
    expect(text.toLowerCase()).toContain("sigo aquí");

    // NO admin alarmismo (NO "Error 500" · NO "Internal Server Error")
    expect(text).not.toMatch(/error 500|internal server error|exception/i);
  });
});
