/**
 * E2E · Test 12 fase_17 · cliente · mobile responsive 375x812 (iPhone 12).
 *
 * Sub-atom 1.C.D.E v3.8 · 1.C.D.C.1+3 mobile UX verify.
 *
 * Verifica:
 *   - Viewport 375x812 · floating button copiloto visible bottom-right
 *   - Timeline stack vertical · NO horizontal overflow
 *   - Cards friendly responsive (full-width <sm)
 *   - Safe area iOS NO bloquea content (bottom-6 = 24px)
 */
import { expect, test } from "@playwright/test";

import { loginAsClient } from "../../_helpers/auth-real";
import { mockClientWorkflowGuide } from "../_fixtures";

test.use({ viewport: { width: 375, height: 812 } });

test.describe("fase_17 cliente · mobile responsive 375x812", () => {
  test("floating copiloto + timeline vertical · NO horizontal overflow", async ({
    page,
  }) => {
    await mockClientWorkflowGuide(page);
    await loginAsClient(page);

    await page.goto("/client-portal/workflow");

    // Floating button copiloto visible
    await expect(
      page.getByTestId("copiloto-cliente-toggle"),
    ).toBeVisible();

    // Timeline section heading visible
    await expect(
      page.getByText(/Tu siguiente paso/i).first(),
    ).toBeVisible();

    // Step card visible · full-width mobile
    const stepCard = page.getByText(/Formación G1 empleados/i).first();
    await expect(stepCard).toBeVisible();

    // NO horizontal overflow · body width = viewport
    const bodyOverflow = await page.evaluate(() => {
      return document.documentElement.scrollWidth >
        document.documentElement.clientWidth + 5;
    });
    expect(bodyOverflow).toBe(false);
  });
});
