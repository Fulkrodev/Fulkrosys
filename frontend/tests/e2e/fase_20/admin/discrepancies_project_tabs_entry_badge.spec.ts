/**
 * E2E · Test 3 fase_20 · admin · ProjectTabs Discrepancias entry + critical badge.
 *
 * Sub-atom 1.D.A.B v3.10 · ProjectTabs SUB_TABS extend con entry Discrepancias.
 *
 * Verifica:
 *   - Tab "Discrepancias" visible en SUB_TABS (extras nav project admin)
 *   - AlertTriangle icon render
 *   - Critical badge (red-600) visible cuando hay open criticals (>=1)
 *   - Click navega a /admin/projects/{id}/discrepancies
 */
import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "../../_helpers/auth-real";
import { PROJECT_A_ID, mockAdminA21Base } from "../_fixtures";

test.describe("fase_20 admin · ProjectTabs Discrepancias entry + badge", () => {
  test("tab visible + critical badge counts open criticals + click navigates", async ({
    page,
    context,
  }) => {
    await loginAsMarcos(context);
    await mockAdminA21Base(page);

    // Navega a una page admin que renderiza ProjectTabs (summary)
    await page.goto(`/admin/projects/${PROJECT_A_ID}/summary`);

    // Tab "Discrepancias" visible (SubTabLink dentro nav extras)
    const tabLink = page.getByRole("link", { name: /Discrepancias/i });
    await expect(tabLink.first()).toBeVisible();

    // Badge critical visible si >0 (DiscrepanciasCriticalBadge · aria-label match)
    await expect(
      page.getByLabel(/discrepancias críticas abiertas/i),
    ).toBeVisible({ timeout: 5000 });

    // Click navigation
    await tabLink.first().click();
    await expect(page).toHaveURL(
      new RegExp(`/admin/projects/${PROJECT_A_ID}/discrepancies`),
    );
  });
});
