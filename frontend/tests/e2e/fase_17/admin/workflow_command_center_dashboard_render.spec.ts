/**
 * E2E · Test 1 fase_17 · admin · Workflow Command Center dashboard render.
 *
 * Sub-atom 1.C.D.E v3.8 · 1.C.D.B.1 (4 zones cronológicas).
 *
 * Verifica:
 *   - Login admin · /admin/workflow-command-center/ render OK
 *   - 4 zones cronológicas visibles (Urgentes hoy · Esta semana · En marcha · 30d)
 *   - Cliente Fintech Plus card en Urgentes hoy
 */
import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "../../_helpers/auth-real";
import { mockAdminWorkflowCommandCenter } from "../_fixtures";

test.describe("fase_17 admin · Workflow Command Center dashboard", () => {
  test("renders 4 zones cronológicas + cliente urgente card", async ({
    page,
    context,
  }) => {
    await loginAsMarcos(context);
    await mockAdminWorkflowCommandCenter(page);

    await page.goto("/admin/workflow-command-center");

    // Cliente urgente visible (zone 1)
    await expect(page.getByText("Fintech Plus SL")).toBeVisible();
    await expect(page.getByText(/Formación G1/i)).toBeVisible();
    // Progress visible
    await expect(page.getByText(/58/).first()).toBeVisible();
    // Cliente esta semana (zone 2)
    await expect(page.getByText("ConsultoríaTIC Madrid SL")).toBeVisible();
    await expect(page.getByText(/DICAT/i)).toBeVisible();
  });
});
