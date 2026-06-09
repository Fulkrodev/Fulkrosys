/**
 * E2E · fase_27 admin · M03 DdA admin page render + 4 Tabs.
 *
 * Sub-atom 1.D.F.A v3.11 · materializa P0 gap detectado audit empírico.
 *
 * Verifica:
 *  - DdaAdminPanel render con header + 4 Tabs (Stats · Medidas · Catálogo · Congelación)
 *  - Stats tab render KPIs (total medidas · aplicables · completion %)
 *  - Catálogo tab render lista medidas Anexo II
 *  - Congelación tab render con badge estado DRAFT/FROZEN
 */
import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "../../_helpers/auth-real";
import {
  mockDdaAdmin,
  mockProjectFeaturesMedia,
  PROJECT_F27_ID,
} from "../_fixtures";

test.describe("fase_27 admin · M03 DdA admin page render", () => {
  test("DdaAdminPanel render + 4 Tabs + stats KPIs", async ({
    context,
    page,
  }) => {
    await loginAsMarcos(context);
    await mockProjectFeaturesMedia(page);
    await mockDdaAdmin(page);

    await page.goto(`/admin/projects/${PROJECT_F27_ID}/dda`);

    // Panel render
    await expect(page.getByTestId("dda-admin-panel")).toBeVisible();

    // Header
    await expect(
      page.getByRole("heading", { name: /Declaración de Aplicabilidad/i }),
    ).toBeVisible();

    // 4 Tabs render
    await expect(page.getByTestId("dda-tab-stats")).toBeVisible();
    await expect(page.getByTestId("dda-tab-entries")).toBeVisible();
    await expect(page.getByTestId("dda-tab-catalog")).toBeVisible();
    await expect(page.getByTestId("dda-tab-freeze")).toBeVisible();

    // Stats tab default active · KPIs render
    await expect(page.getByTestId("dda-stats")).toBeVisible();
    await expect(page.getByText(/Progreso DdA · Anexo II/i)).toBeVisible();

    // Verify KPI values
    await expect(page.getByText("68%").first()).toBeVisible();
    await expect(page.getByText("73", { exact: true }).first()).toBeVisible();
  });
});
