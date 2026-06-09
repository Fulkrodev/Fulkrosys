/**
 * E2E · fase_30 cliente · /magerit SIMPLIFIED indispensable-only.
 *
 * Sub-atom 1.D.F.bis.III.A v3.11.
 *
 * Verifica:
 *  - Banner R30 inverso "Marcos opera análisis técnico" visible
 *  - Lista activos read-only (NO filters review/tipo/severidad)
 *  - Form "Aportar info adicional" textarea + submit
 *  - NO tabs assets/risks (removed)
 *  - Sign final button NO visible (ready_for_validation_sign=false in mock)
 */
import { expect, test } from "@playwright/test";

import { loginAsClient } from "../../_helpers/auth-real";
import { mockClienteIndispensable } from "../_fixtures";

test.describe("fase_30 cliente · /magerit simplified indispensable", () => {
  test("banner + activos read-only + aportar info form", async ({ page }) => {
    await loginAsClient(page);
    await mockClienteIndispensable(page);

    await page.goto("/client-portal/magerit");

    // Header + banner R30 inverso
    await expect(
      page.getByRole("heading", { name: /Activos del análisis de riesgos/i }),
    ).toBeVisible();
    await expect(
      page.getByText(/Marcos opera el análisis técnico/i),
    ).toBeVisible();

    // Lista activos read-only · NO filters complex
    await expect(
      page.getByTestId("magerit-cliente-assets-list"),
    ).toBeVisible();

    // Assets mock visibles (asset codes S-001 + D-001)
    await expect(page.getByTestId("magerit-asset-row-S-001")).toBeVisible();
    await expect(page.getByTestId("magerit-asset-row-D-001")).toBeVisible();

    // Form aportar info
    await expect(
      page.getByTestId("magerit-cliente-aportar-info"),
    ).toBeVisible();
    await expect(page.getByTestId("magerit-info-textarea")).toBeVisible();
    await expect(page.getByTestId("magerit-info-submit")).toBeVisible();

    // Filters/tabs analytic REMOVED · NO visible
    await expect(
      page.getByRole("tab", { name: /Análisis riesgos/i }),
    ).not.toBeVisible();
    await expect(page.getByText(/Severidad:/i)).not.toBeVisible();
  });
});
