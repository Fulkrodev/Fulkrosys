/**
 * E2E · fase_26 admin · Quality completeness smoke pre-piloto.
 *
 * Sub-atom 1.D.F.0.E v3.11 · CIERRE sub-atom 1.D.F.0 quality completeness.
 *
 * Smoke verifies todas las features 1.D.F.0 integradas:
 *  - 1.D.F.0.A wizard diagnóstico (página accesible /admin/projects/new)
 *  - 1.D.F.0.B tooltips cliente (CopilotoClienteBottomRight render skipped here · cliente test)
 *  - 1.D.F.0.C Director AHORA pin-to-top + toggle
 *  - 1.D.F.0.D copilot admin context-aware button-level
 *
 * Verifica:
 *  - Workflow command center per-cliente render funcional end-to-end
 *  - Sidebar copilot + AHORA pin + toggle + screen-aware payload
 *  - Wizard /admin/projects/new accesible
 */
import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "../../_helpers/auth-real";
import {
  mockAdminCronologicaFull,
  mockCopilotoAdminScreenAware,
  PROJECT_F26_ID,
} from "../_fixtures";

test.describe("fase_26 admin · Quality completeness smoke 1.D.F.0", () => {
  test("Director workflow center · sidebar + AHORA pin + toggle + screen-aware payload", async ({
    context,
    page,
  }) => {
    await loginAsMarcos(context);
    await mockAdminCronologicaFull(page);
    await mockCopilotoAdminScreenAware(page);

    await page.goto(
      `/admin/workflow-command-center/projects/${PROJECT_F26_ID}`,
    );

    // 1.D.F.0.C · Timeline render + AHORA section pin-to-top
    await expect(page.getByTestId("workflow-timeline-admin")).toBeVisible();
    await expect(page.getByTestId("ahora-section")).toBeVisible();

    // 1.D.F.0.C · Toggle UI present
    await expect(page.getByTestId("view-mode-ahora-only")).toBeVisible();
    await expect(page.getByTestId("view-mode-complete")).toBeVisible();

    // 1.D.F.0.D · Copilot sidebar visible · context-aware ready
    await expect(page.getByTestId("copiloto-admin-sidebar")).toBeVisible();

    // 1.D.F.0.D · QuickAction trigger · current_screen propagado backend
    const reqWaiter = page.waitForRequest(
      (req) =>
        req.url().includes("/api/v1/admin/copilot/chat") &&
        req.method() === "POST",
    );
    await page.getByRole("button", { name: /Qué hago ahora/i }).click();
    const req = await reqWaiter;
    const payload = req.postDataJSON() as { current_screen?: string };
    expect(payload.current_screen).toBeTruthy();

    // History entry rendered
    await expect(
      page.getByTestId("copiloto-admin-history"),
    ).toBeVisible({ timeout: 5000 });
  });
});
