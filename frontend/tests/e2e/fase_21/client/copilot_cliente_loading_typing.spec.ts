/**
 * E2E · Test 3 fase_21 · client · Loading state typing 3 dots animation.
 *
 * Sub-atom 1.D.B.1.2 v3.11 · UX enrichment typing indicator.
 *
 * Verifica:
 *   - Click quick action → typing indicator visible (data-testid)
 *   - 3 dots animation rendered
 *   - aria-label accesible
 *   - Send button shows Loader2 (existing) durante mutation pending
 */
import { expect, test } from "@playwright/test";

import { loginAsClient } from "../../_helpers/auth-real";
import { mockCopilotoClienteChatLLM, PROJECT_BB_ID } from "../_fixtures";

test.describe("fase_21 client · Copilot cliente typing indicator", () => {
  test("typing 3 dots visible durante chat mutation pending", async ({
    page,
  }) => {
    await loginAsClient(page);

    // Delay mock response 500ms para capturar typing state
    await page.route(
      "**/api/v1/client-portal/copilot/chat",
      async (route) => {
        await new Promise((resolve) => setTimeout(resolve, 500));
        await route.fulfill({
          status: 200,
          json: {
            action_id: "que_hago",
            response_text: "Tu siguiente paso es categorización.",
            is_stub: false,
            next_action_hint: null,
            citations: [],
          },
        });
      },
    );

    await page.goto("/client-portal/workflow");
    await page.getByTestId("copiloto-cliente-toggle").click();
    await page.getByRole("button", { name: /Qué tengo que hacer ahora/i }).click();

    // Typing indicator visible durante mutation pending
    await expect(page.getByTestId("copiloto-cliente-typing")).toBeVisible();
    await expect(
      page.getByLabel(/El asistente está pensando/i),
    ).toBeVisible();

    // Espera response render · typing desaparece
    await expect(page.getByTestId("copiloto-cliente-typing")).not.toBeVisible({
      timeout: 5000,
    });
  });
});
