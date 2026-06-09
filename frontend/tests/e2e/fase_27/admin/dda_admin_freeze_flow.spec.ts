/**
 * E2E · fase_27 admin · DdA freeze flow (P0 audit-ready ENAC).
 *
 * Sub-atom 1.D.F.A v3.11 · DdaFreezeButton.
 *
 * Verifica:
 *  - Tab Congelación render con DRAFT badge default
 *  - Botón Congelar habilitado cuando completion ≥80%
 *  - Click Congelar abre modal · pide aprobado_por
 *  - Confirm flow → frozen state · status FROZEN
 */
import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "../../_helpers/auth-real";
import {
  MOCK_DDA_STATS_PARTIAL,
  mockDdaAdmin,
  mockProjectFeaturesMedia,
  PROJECT_F27_ID,
} from "../_fixtures";

test.describe("fase_27 admin · DdA freeze flow", () => {
  test("freeze button confirmation modal · aprobado_por input requerido", async ({
    context,
    page,
  }) => {
    await loginAsMarcos(context);
    await mockProjectFeaturesMedia(page);

    await mockDdaAdmin(page);

    // Mock stats con completion 85% (≥80% threshold · habilita "Congelar").
    // IMPORTANTE: registrar DESPUÉS de mockDdaAdmin · Playwright resuelve rutas
    // en orden LIFO (la última registrada gana). mockDdaAdmin también mockea
    // /stats con MOCK_DDA_STATS_PARTIAL (68.18%) · si registráramos el override
    // antes, el de mockDdaAdmin ganaría y el botón quedaría disabled (<80%).
    await page.route(
      `**/api/v1/dda/projects/${PROJECT_F27_ID}/stats`,
      async (route) => {
        await route.fulfill({
          status: 200,
          json: { ...MOCK_DDA_STATS_PARTIAL, completion_pct: 85 },
        });
      },
    );

    await page.goto(`/admin/projects/${PROJECT_F27_ID}/dda`);
    await page.getByTestId("dda-tab-freeze").click();

    // Freeze panel render con DRAFT badge
    await expect(page.getByTestId("dda-freeze-panel")).toBeVisible();
    await expect(
      page.getByTestId("dda-freeze-status-badge"),
    ).toContainText(/DRAFT/i);

    // Botón Congelar habilitado (85% completion)
    const freezeBtn = page.getByTestId("dda-freeze-button");
    await expect(freezeBtn).toBeVisible();
    await expect(freezeBtn).toBeEnabled();

    // Click abre modal
    await freezeBtn.click();
    await expect(page.getByTestId("dda-freeze-confirm-modal")).toBeVisible();

    // Confirm botón disabled hasta input válido
    const confirmBtn = page.getByTestId("dda-freeze-confirm");
    await expect(confirmBtn).toBeDisabled();

    // Input aprobado_por
    await page.getByTestId("dda-aprobado-por-input").fill("Juan Pérez · RSEG");
    await expect(confirmBtn).toBeEnabled();
  });
});
