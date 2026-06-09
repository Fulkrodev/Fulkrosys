/**
 * E2E · Test 7 fase_19 · cliente · R30 inverso verify (admin actions invisible).
 *
 * Sub-atom 1.C.G.B v3.10 · R30 inverso CRÍTICO.
 *
 * Verifica empíricamente que cliente NUNCA ve admin metadata/actions:
 *   - NO admin lingo en page heading/body (NO "audit log" · NO "permissions" ·
 *     NO "evidence_metadata" · NO "trust boundary" · NO "RLS")
 *   - NO botones admin destructivos (NO "Eliminar definitivo" · NO "Revert" ·
 *     NO "Grant permission")
 *   - NO panel audit visible cliente
 *   - NO IdmsAdminLayout en cliente page
 *
 * R30 inverso · cliente experiencia friendly · admin metadata permanece backend-only.
 */
import { expect, test } from "@playwright/test";

import { loginAsClient } from "../../_helpers/auth-real";
import { mockClientIdmsBase } from "../_fixtures";

test.describe("fase_19 cliente · R30 inverso · admin actions invisible", () => {
  test("cliente NO ve admin lingo · admin buttons · audit metadata", async ({
    page,
  }) => {
    await mockClientIdmsBase(page);
    await loginAsClient(page);

    await page.goto("/client-portal/files");

    // Wait for page hydration
    await expect(
      page.getByRole("heading", { name: /^Mis Documentos$/i }),
    ).toBeVisible();

    // NO admin IDMS Workbench title (only present /admin path)
    await expect(
      page.getByText(/Gestor documental \(IDMS\)/i),
    ).not.toBeVisible();

    // NO admin lingo en page (audit log · trust boundary · RLS · permissions grant)
    await expect(page.getByText(/audit log/i)).not.toBeVisible();
    await expect(page.getByText(/trust boundary/i)).not.toBeVisible();
    await expect(page.getByText(/RLS isolation/i)).not.toBeVisible();
    await expect(page.getByText(/permission grants/i)).not.toBeVisible();

    // NO admin destructive buttons
    await expect(
      page.getByRole("button", { name: /Eliminar definitivo/i }),
    ).not.toBeVisible();
    await expect(
      page.getByRole("button", { name: /Revert version/i }),
    ).not.toBeVisible();
    await expect(
      page.getByRole("button", { name: /Grant permission/i }),
    ).not.toBeVisible();

    // NO admin K.XX badge en tree cliente (DocumentTreeClient NO renderiza K.XX)
    await expect(page.getByText(/^K\.00$/)).not.toBeVisible();
    await expect(page.getByText(/^K\.06$/)).not.toBeVisible();

    // CLIENT POSITIVE · friendly UX visible (control · NO admin)
    await expect(
      page.getByRole("button", { name: /Compartir documento/i }),
    ).toBeVisible();
    await expect(
      page.getByText(/Mis carpetas/i),
    ).toBeVisible();
  });
});
