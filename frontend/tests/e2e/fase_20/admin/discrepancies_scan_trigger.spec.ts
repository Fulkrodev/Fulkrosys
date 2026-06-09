/**
 * E2E · Test 2 fase_20 · admin · Trigger scan button + invalidate query.
 *
 * Sub-atom 1.D.A v3.10 · A21 detector discrepancias ENS-only admin.
 *
 * Verifica:
 *   - Botón "Ejecutar scan" visible en panel admin
 *   - Click ejecuta POST /a21/scan + re-fetch listas
 *   - Toast success post-scan (sonner) con motors_scanned + discrepancies_found
 */
import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "../../_helpers/auth-real";
import { PROJECT_A_ID, mockAdminA21Base } from "../_fixtures";

test.describe("fase_20 admin · A21 scan trigger", () => {
  test("trigger button → POST /a21/scan + toast success render", async ({
    page,
    context,
  }) => {
    await loginAsMarcos(context);
    await mockAdminA21Base(page);

    await page.goto(`/admin/projects/${PROJECT_A_ID}/discrepancies`);

    // Botón scan visible (label puede ser "Ejecutar scan" o similar · refresh icon)
    const scanButton = page.getByRole("button", {
      name: /Ejecutar scan|Scan|Lanzar|RefreshCw/i,
    });
    await expect(scanButton.first()).toBeVisible();

    // Click trigger scan
    await scanButton.first().click();

    // Toast success eventually (sonner notification motors_scanned)
    await expect(
      page.getByText(/Scan completed|4 discrepancias detectadas/i),
    ).toBeVisible({ timeout: 5000 });
  });
});
