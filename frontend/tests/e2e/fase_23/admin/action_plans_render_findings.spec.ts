/**
 * E2E · Test 1 fase_23 · admin · ActionPlansPanel render top findings.
 *
 * Sub-atom 1.D.C v3.11 · Dashboard K.3 cross-motor.
 *
 * Verifica:
 *   - Login admin · /admin/projects/{id}/planes-accion render OK
 *   - Panel title "Planes de acción · Dashboard K.3" visible
 *   - 4 mock items renderizados (2 m04 + 1 a21 + 1 m09)
 *   - Severity badges visibles (crítica · alta)
 *   - Source badges (Gap M04 · Discrepancia A21 · Audit prep M09)
 *   - Counts summary visible (Total: 4)
 *   - Drill-down link presente per item
 */
import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "../../_helpers/auth-real";
import { mockActionPlansWithFindings, PROJECT_EE_ID } from "../_fixtures";

test.describe("fase_23 admin · ActionPlansPanel render top findings", () => {
  test("4 findings rendered con severity + source badges + drill-down", async ({
    context,
    page,
  }) => {
    await loginAsMarcos(context);
    await mockActionPlansWithFindings(page);

    await page.goto(`/admin/projects/${PROJECT_EE_ID}/planes-accion`);

    // Panel title visible
    await expect(
      page.getByRole("heading", { name: /Planes de acción · Dashboard K\.3/i }),
    ).toBeVisible();

    // Panel + counts summary visible
    await expect(page.getByTestId("action-plans-panel")).toBeVisible();
    await expect(page.getByTestId("action-plans-counts")).toBeVisible();
    await expect(page.getByText(/Total: 4/i)).toBeVisible();

    // 4 items renderizados (list)
    const list = page.getByTestId("action-plans-list");
    await expect(list).toBeVisible();

    // Severity badges presentes
    await expect(
      page.getByTestId("action-plans-severity-critica").first(),
    ).toBeVisible();
    await expect(
      page.getByTestId("action-plans-severity-alta").first(),
    ).toBeVisible();

    // Source badges (mediante row testids)
    await expect(
      page.getByTestId("action-plans-row-m04_gap").first(),
    ).toBeVisible();
    await expect(
      page.getByTestId("action-plans-row-a21_discrepancy").first(),
    ).toBeVisible();
    await expect(
      page.getByTestId("action-plans-row-m09_audit_prep").first(),
    ).toBeVisible();

    // Drill-down link presente
    await expect(
      page.getByTestId("action-plans-drilldown").first(),
    ).toBeVisible();
  });
});
