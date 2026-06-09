/**
 * E2E · fase_35 admin M22 consolidated discovery · refresh button (1.D.J).
 *
 * Verifica:
 *  - Click "Re-consolidar" button triggers refetch
 *  - Backend request observable (waitForRequest)
 *  - Button accesible via data-testid consolidated-refresh
 */
import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "../../_helpers/auth-real";
import { PROJECT_F35_ID, mockM22ConsolidatedBase } from "../_fixtures";

test.describe("fase_35 admin · M22 consolidated discovery refresh", () => {
  test("click Re-consolidar triggers backend refetch", async ({ page }) => {
    await loginAsMarcos(page.context());
    await mockM22ConsolidatedBase(page);

    await page.goto(`/admin/projects/${PROJECT_F35_ID}/discovery`);
    await page.getByRole("tab", { name: /Consolidado/i }).click();
    await expect(page.getByTestId("consolidated-tab")).toBeVisible();

    // Wait for second consolidated request after refresh click
    const reqWait = page.waitForRequest(
      (req) =>
        req.url().includes("/discovery-consolidated") &&
        req.method() === "GET",
      { timeout: 10_000 },
    );

    await page.getByTestId("consolidated-refresh").click();
    await reqWait;

    // Button still visible post-refresh
    await expect(page.getByTestId("consolidated-refresh")).toBeVisible();
  });
});
