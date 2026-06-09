/**
 * E2E · Test 1 fase_21 · client · Copilot chat LLM real render.
 *
 * Sub-atom 1.D.B.1 v3.11 · swap-in cliente LLM real.
 *
 * Verifica:
 *   - Login cliente · /client-portal/workflow render OK
 *   - Click bottom-right toggle abre Sheet
 *   - Quick action "que_hago" trigger chat request
 *   - Response LLM real render (is_stub=false · NO "asistente en preparación")
 *   - Response text friendly · sin jerga admin
 */
import { expect, test } from "@playwright/test";

import { loginAsClient } from "../../_helpers/auth-real";
import { mockCopilotoClienteChatLLM } from "../_fixtures";

test.describe("fase_21 client · Copilot cliente LLM real chat", () => {
  test("trigger quick action · LLM response friendly render NO stub disclaimer", async ({
    page,
  }) => {
    await loginAsClient(page);
    await mockCopilotoClienteChatLLM(page);

    await page.goto("/client-portal/workflow");

    // Toggle abre Sheet
    await page.getByTestId("copiloto-cliente-toggle").click();
    await expect(page.getByTestId("copiloto-cliente-chat")).toBeVisible();

    // Quick action "que_hago"
    await page.getByRole("button", { name: /Qué tengo que hacer ahora/i }).click();

    // Response LLM render
    await expect(page.getByTestId("copiloto-cliente-log")).toBeVisible();
    await expect(
      page.getByText(/DNI de tu proyecto ENS|categorización/i).first(),
    ).toBeVisible({ timeout: 5000 });

    // Disclaimer "asistente en preparación" NO presente (LLM real · is_stub=false)
    await expect(
      page.getByText(/asistente en preparación/i),
    ).not.toBeVisible();
  });
});
