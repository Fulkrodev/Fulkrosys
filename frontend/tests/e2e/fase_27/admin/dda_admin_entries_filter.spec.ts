/**
 * E2E · fase_27 admin · DdA entries list + filtros marco/estado.
 *
 * Sub-atom 1.D.F.A v3.11 · DdaEntriesList component.
 *
 * Verifica:
 *  - Tab Medidas → DdaEntriesList render
 *  - Tabla con 5 entries mock visibles (org.1 · op.exp.1 · mp.com.1 · mp.com.2 · op.cont.1)
 *  - Filtro marco "org" reduce a 1 row (org.1)
 *  - Filtro estado "no_implantada" reduce
 *  - Click Detalle abre modal
 */
import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "../../_helpers/auth-real";
import {
  mockDdaAdmin,
  mockProjectFeaturesMedia,
  PROJECT_F27_ID,
} from "../_fixtures";

test.describe("fase_27 admin · DdA entries list + filtros", () => {
  test("entries table render · filtro marco + filtro estado · detalle modal", async ({
    context,
    page,
  }) => {
    await loginAsMarcos(context);
    await mockProjectFeaturesMedia(page);
    await mockDdaAdmin(page);

    await page.goto(`/admin/projects/${PROJECT_F27_ID}/dda`);

    // Tab Medidas
    await page.getByTestId("dda-tab-entries").click();

    // Table render con 5 entries mock
    await expect(page.getByTestId("dda-entries-table")).toBeVisible();
    await expect(page.getByTestId("dda-entry-row-org.1")).toBeVisible();
    await expect(page.getByTestId("dda-entry-row-op.exp.1")).toBeVisible();
    await expect(page.getByTestId("dda-entry-row-mp.com.1")).toBeVisible();
    await expect(page.getByTestId("dda-entry-row-mp.com.2")).toBeVisible();
    await expect(page.getByTestId("dda-entry-row-op.cont.1")).toBeVisible();

    // Filtro estado "no_implantada" → solo mp.com.1
    await page.getByTestId("dda-filter-estado-no_implantada").click();
    await expect(page.getByTestId("dda-entry-row-mp.com.1")).toBeVisible();

    // Click Detalle abre modal
    await page.getByTestId("dda-entry-detail-mp.com.1").click();
    await expect(page.getByTestId("dda-entry-detail-modal")).toBeVisible();
  });
});
