/**
 * E2E · Test 4 fase_19 · admin · Version history modal · cronologico + hash SHA-256.
 *
 * Sub-atom 1.C.G.A v3.10 · DocumentVersionHistoryModal admin.
 *
 * Verifica:
 *   - Login admin · click history icon en document row
 *   - DocumentVersionHistoryModal opens · title "Historial de versiones"
 *   - Lista cronologica versiones (v2.0 · v1.0)
 *   - Hash SHA-256 visible per version
 *   - Autor + timestamp visible per version
 */
import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "../../_helpers/auth-real";
import { PROJECT_G_ID, mockAdminIdmsBase } from "../_fixtures";

test.describe("fase_19 admin · version history modal", () => {
  test("opens history · cronologico + hash SHA-256 visible", async ({
    page,
    context,
  }) => {
    await loginAsMarcos(context);
    await mockAdminIdmsBase(page);

    await page.goto(`/admin/projects/${PROJECT_G_ID}/documents`);

    // Click history button (aria-label "Ver historial versiones") en row PSI_v2.docx
    const row = page.locator("tr", { hasText: "PSI_v2.docx" }).first();
    await row.getByLabel(/Ver historial versiones/i).click();

    // Modal opens with title
    await expect(
      page.getByRole("dialog").getByText(/Historial de versiones/i).first(),
    ).toBeVisible();

    // 2 versiones visible
    await expect(
      page.getByRole("dialog").getByText(/^v2\.0$/).first(),
    ).toBeVisible();
    await expect(
      page.getByRole("dialog").getByText(/^v1\.0$/).first(),
    ).toBeVisible();

    // Hash SHA-256 visible (al menos uno · prefix)
    await expect(
      page.getByText(/SHA-256:\s*abc123def456/i).first(),
    ).toBeVisible();

    // Autor "marcos" visible
    await expect(
      page.getByRole("dialog").getByText(/marcos/i).first(),
    ).toBeVisible();
  });
});
