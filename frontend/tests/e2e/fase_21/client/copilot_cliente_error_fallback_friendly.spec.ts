/**
 * E2E · fase_21 · si el backend falla, el cliente recibe un aviso amable.
 */
import { expect, test } from "@playwright/test";

import { loginAsClient } from "../../_helpers/auth-real";
import { abrirDockYPreguntar, mockCopilotoDockError } from "../_fixtures";

test.describe("fase_21 client · Copilot cliente error fallback", () => {
  test("error del backend → aviso amable, sin codigos ni alarmismo", async ({ page }) => {
    await loginAsClient(page);
    await mockCopilotoDockError(page);
    await page.goto("/client-portal/workflow");
    await abrirDockYPreguntar(page);

    const aviso = page.getByTestId("copiloto-msg-error").last();
    await expect(aviso).toBeVisible({ timeout: 5_000 });
    await expect(aviso).toContainText(/intenta de nuevo/i);
    await expect(aviso).not.toContainText(/error 500|internal server error|exception/i);
  });
});
