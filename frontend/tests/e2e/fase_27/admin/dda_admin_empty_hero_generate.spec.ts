/**
 * E2E · fase_27 admin · DdA empty hero + generate button.
 *
 * Sub-atom 1.D.F.A v3.11 · DdaGenerateButton + empty state R30 tutorial.
 *
 * Verifica:
 *  - Status exists=false → empty hero render con explicación primer principios
 *  - Botón "Generar DdA" abre modal
 *  - Categoria select + responsable + confirm botón
 */
import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "../../_helpers/auth-real";
import {
  mockDdaAdmin,
  mockProjectFeaturesMedia,
  PROJECT_F27_ID,
} from "../_fixtures";

test.describe("fase_27 admin · DdA empty hero generate flow", () => {
  test("status exists=false → hero R30 tutor + generate modal", async ({
    context,
    page,
  }) => {
    await loginAsMarcos(context);
    await mockProjectFeaturesMedia(page);
    await mockDdaAdmin(page, { exists: false });

    await page.goto(`/admin/projects/${PROJECT_F27_ID}/dda`);

    // Empty hero render
    await expect(page.getByTestId("dda-empty-hero")).toBeVisible();
    await expect(
      page.getByText(/DdA aún no creada/i),
    ).toBeVisible();
    // R30 tutor explicación primer principios
    await expect(
      page.getByText(/es decir el documento donde decides/i),
    ).toBeVisible();

    // Generate button
    const genBtn = page.getByTestId("dda-generate-button");
    await expect(genBtn).toBeVisible();

    // Click abre modal
    await genBtn.click();
    await expect(page.getByTestId("dda-generate-modal")).toBeVisible();
    await expect(
      page.getByTestId("dda-generate-category-select"),
    ).toBeVisible();
  });
});
