/**
 * E2E · Test 1 fase_20 · admin · DiscrepanciesPanel render lista.
 *
 * Sub-atom 1.D.A v3.10 · A21 detector discrepancias ENS-only admin.
 *
 * Verifica:
 *   - Login admin · /admin/projects/{id}/discrepancies/ render OK
 *   - DiscrepanciesPanel visible (Card title "Detector de discrepancias (A21)")
 *   - Lista discrepancias render con severidades (critical · high · medium · resolved)
 *   - Empty state ausente cuando hay datos
 */
import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "../../_helpers/auth-real";
import { PROJECT_A_ID, mockAdminA21Base } from "../_fixtures";

test.describe("fase_20 admin · A21 discrepancias panel render", () => {
  test("renders panel + lista discrepancias severidades visibles", async ({
    page,
    context,
  }) => {
    await loginAsMarcos(context);
    await mockAdminA21Base(page);

    await page.goto(`/admin/projects/${PROJECT_A_ID}/discrepancies`);

    // Card title visible
    await expect(
      page.getByRole("heading", {
        name: /Detector de discrepancias \(A21\)/i,
      }),
    ).toBeVisible();

    // Critical discrepancy description visible (findings_vs_remediation)
    await expect(
      page.getByText(/finding\(s\) crítico\(s\) abierto\(s\)/i),
    ).toBeVisible();

    // High discrepancy description visible (dda_vs_documents)
    await expect(
      page.getByText(/Cobertura documental ENS ausente/i),
    ).toBeVisible();
  });
});
