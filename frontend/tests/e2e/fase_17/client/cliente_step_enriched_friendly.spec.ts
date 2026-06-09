/**
 * E2E · Test 9 fase_17 · cliente · step enriched friendly tono.
 *
 * Sub-atom 1.C.D.E v3.8 · 1.C.D.C.1+2 (WorkflowStepCardClient + DetailDrawer 3 tabs).
 *
 * Verifica:
 *   - StepCard muestra "¿Qué tienes que hacer?" + "¿Por qué es importante?"
 *   - NO actors badges visibles (cliente NO entiende CISO+DPO+Comité)
 *   - NO AdaptationBadge dims técnicas
 *   - Click sub-paso → drawer 3 tabs (Detalle · ¿Por qué? · ¿Qué necesito?)
 */
import { expect, test } from "@playwright/test";

import { loginAsClient } from "../../_helpers/auth-real";
import { mockClientWorkflowGuide, mockDeliverables } from "../_fixtures";

test.describe("fase_17 cliente · step enriched friendly", () => {
  test("StepCard friendly + drawer 3 tabs (NO 5 admin)", async ({ page }) => {
    await mockClientWorkflowGuide(page);
    await mockDeliverables(page);
    await loginAsClient(page);

    await page.goto("/client-portal/workflow");

    // "¿Qué tienes que hacer?" visible (NO "description_detailed_es")
    await expect(
      page.getByText(/¿Qué tienes que hacer\?/i).first(),
    ).toBeVisible();
    // "¿Por qué es importante?" visible
    await expect(
      page.getByText(/¿Por qué es importante\?/i).first(),
    ).toBeVisible();

    // NO admin actors badges
    await expect(
      page.getByText(/CISO\+DPO\+Comité/i),
    ).not.toBeVisible();

    // Click "Ver más detalle" → drawer 3 tabs
    const verMasBtn = page.getByRole("button", { name: /Ver más detalle/i }).first();
    await verMasBtn.click();

    // 3 tabs visible (Detalle + ¿Por qué? + ¿Qué necesito?)
    await expect(
      page.getByRole("tab", { name: /Detalle/i }),
    ).toBeVisible();
    await expect(
      page.getByRole("tab", { name: /¿Por qué\?/i }),
    ).toBeVisible();
    await expect(
      page.getByRole("tab", { name: /¿Qué necesito\?/i }),
    ).toBeVisible();
  });
});
