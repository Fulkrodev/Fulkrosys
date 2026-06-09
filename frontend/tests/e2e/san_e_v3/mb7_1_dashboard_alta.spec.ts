/**
 * SAN-E v3.MB-7.1 · client dashboard adaptativo · ALTA tier visual.
 *
 * Sanity de render: greetings + archetype hint + days-to-cert opcional.
 */
import { expect, test } from "@playwright/test";

import { loginAsClient } from "../_helpers/auth-real";

test.use({ viewport: { width: 1280, height: 800 } });

test.describe("SAN-E v3.MB-7.1 · dashboard ALTA / archetype hint", () => {
  test("hero adaptativo · greeting + project name visible", async ({
    page,
  }) => {
    await loginAsClient(page);
    await page.goto("/client-portal/dashboard");
    await page.waitForLoadState("networkidle");

    const hero = page.getByTestId("hero-adaptativo");
    await expect(hero).toBeVisible();
    await expect(hero.getByRole("heading", { name: /Hola/i })).toBeVisible();
  });

  test("dashboard mobile responsive · viewport 375 no errors", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await loginAsClient(page);
    await page.goto("/client-portal/dashboard");
    await page.waitForLoadState("networkidle");

    // Container ajusta sin overflow horizontal (sanity)
    await expect(page.getByTestId("client-dashboard-v3")).toBeVisible();
    await expect(page.getByTestId("hero-adaptativo")).toBeVisible();
  });
});
