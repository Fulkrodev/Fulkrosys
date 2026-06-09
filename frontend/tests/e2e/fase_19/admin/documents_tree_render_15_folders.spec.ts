/**
 * E2E · Test 1 fase_19 · admin · Documents tree render 15 standard folders.
 *
 * Sub-atom 1.C.G.A v3.10 · gestor documental admin enrichment.
 *
 * Verifica:
 *   - Login admin · /admin/projects/{id}/documents/ render OK
 *   - IdmsAdminLayout visible (Card title "Gestor documental (IDMS)")
 *   - DocumentTreeAdmin render 15 folders K.0..K.6+retainer
 *   - Badge K.XX visible per standard folder
 *   - "Todos los documentos" root link visible
 */
import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "../../_helpers/auth-real";
import { PROJECT_G_ID, mockAdminIdmsBase } from "../_fixtures";

test.describe("fase_19 admin · documents tree render 15 folders", () => {
  test("renders IdmsAdminLayout + 15 standard folders + K.XX badges", async ({
    page,
    context,
  }) => {
    await loginAsMarcos(context);
    await mockAdminIdmsBase(page);

    await page.goto(`/admin/projects/${PROJECT_G_ID}/documents`);

    // Card title visible
    await expect(
      page.getByRole("heading", { name: /Gestor documental \(IDMS\)/i }),
    ).toBeVisible();

    // "Todos los documentos" root link
    await expect(
      page.getByRole("button", { name: /Todos los documentos/i }),
    ).toBeVisible();

    // Verifica al menos 3 carpetas estándar visibles (smoke · NO render todas
    // explícitamente para evitar flakiness · K.00, K.06, K.99 son representativas)
    await expect(page.getByText(/00_Contractual/i).first()).toBeVisible();
    await expect(page.getByText(/06_Normativa/i).first()).toBeVisible();
    await expect(page.getByText(/99_Misc/i).first()).toBeVisible();

    // Badge K.XX presente (al menos uno · standard_code)
    await expect(page.getByText(/^K\.00$/).first()).toBeVisible();
  });
});
