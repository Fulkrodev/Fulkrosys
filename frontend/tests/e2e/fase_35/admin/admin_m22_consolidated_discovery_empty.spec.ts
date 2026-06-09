/**
 * E2E · fase_35 admin M22 consolidated discovery · empty state R29 friendly (1.D.J).
 *
 * Verifica:
 *  - Empty state visible cuando NO hay activos manuales ni cloud
 *  - R29 firmísimo · NO clases red/destructive/bg-red (NUNCA presión)
 *  - Texto invita acción sin alarma
 */
import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "../../_helpers/auth-real";
import { PROJECT_F35_ID, mockM22ConsolidatedEmpty } from "../_fixtures";

test.describe("fase_35 admin · M22 consolidated discovery empty R29", () => {
  test("empty state renders friendly · NO red/destructive classes", async ({ page }) => {
    await loginAsMarcos(page.context());
    await mockM22ConsolidatedEmpty(page);

    await page.goto(`/admin/projects/${PROJECT_F35_ID}/discovery`);
    await page.getByRole("tab", { name: /Consolidado/i }).click();
    await expect(page.getByTestId("consolidated-tab")).toBeVisible();

    // Empty state component visible
    await expect(page.getByTestId("consolidated-empty")).toBeVisible();

    // R29 CSS guard · NUNCA rojo
    const emptyClasses = await page
      .getByTestId("consolidated-empty")
      .getAttribute("class");
    expect(emptyClasses ?? "").not.toMatch(/red-|destructive|bg-red/);

    // Texto incentiva acción · NO alarma
    await expect(page.getByText(/Sin activos manuales ni cloud/i)).toBeVisible();
  });

  test("manual-only state shows no-cloud-hint warning (ámbar · NO rojo)", async ({
    page,
  }) => {
    await loginAsMarcos(page.context());
    const { mockM22ConsolidatedManualOnly } = await import("../_fixtures");
    await mockM22ConsolidatedManualOnly(page);

    await page.goto(`/admin/projects/${PROJECT_F35_ID}/discovery`);
    await page.getByRole("tab", { name: /Consolidado/i }).click();

    // Hint visible when manual_only > 0 + no cloud
    await expect(page.getByTestId("consolidated-no-cloud-hint")).toBeVisible();

    // R29 CSS guard · ámbar/warning sí permitido · rojo NO
    const hintClasses = await page
      .getByTestId("consolidated-no-cloud-hint")
      .getAttribute("class");
    expect(hintClasses ?? "").not.toMatch(/red-|destructive|bg-red/);
  });
});
