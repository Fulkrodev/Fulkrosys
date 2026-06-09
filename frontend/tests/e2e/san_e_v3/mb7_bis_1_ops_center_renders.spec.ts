/**
 * SAN-E v3.MB-7.bis.1 · /admin/retainers Ops Center renders.
 *
 * Verifica:
 *  - Path nuevo /admin/retainers (plural · rename atom 7.bis.1)
 *  - CapacityTile visible (atom 7.bis.1 Q7.C)
 *  - Header "Consola Retainer"
 *  - Sub-route /admin/retainers/churn-risk → redirige a /admin/dashboard
 *    (migrada a widget · Sesión 3B-2B.3 Phase X.4d)
 */
import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "../_helpers/auth-real";


test.use({ viewport: { width: 1280, height: 800 } });


test.describe("SAN-E v3.MB-7.bis.1 · RetainerOpsCenter plural route", () => {
  // SKIP: feature eliminada (RetainerOpsCenter "Consola Retainer" + CapacityTile
  // en /admin/retainers). La ruta se migró a redirect server-side hacia
  // /admin/projects (Sesión 3B-2B.3 Phase X.3 · R23: el retainer es per-project,
  // sin dashboard global cross-cliente · ver app/(admin)/admin/retainers/page.tsx
  // = LegacyRetainersListRedirect). El test 2 de este fichero (churn-risk →
  // /admin/dashboard redirect) sigue válido. Candidata a borrar tras contraste
  // (Marcos).
  test.skip("/admin/retainers renders Ops Center con CapacityTile", async ({
    context, page,
  }) => {
    await loginAsMarcos(context);
    await page.goto("/admin/retainers");
    await page.waitForLoadState("networkidle");

    await expect(
      page.getByRole("heading", { name: /Consola Retainer/i }),
    ).toBeVisible({ timeout: 10_000 });
    await expect(page.getByTestId("capacity-tile")).toBeVisible();
  });

  test("/admin/retainers/churn-risk redirige a /admin/dashboard", async ({
    context, page,
  }) => {
    await loginAsMarcos(context);
    await page.goto("/admin/retainers/churn-risk");
    await page.waitForLoadState("networkidle");
    // La ruta standalone fue migrada a widget en el dashboard (Sesión 3B-2B.3
    // Phase X.4d) · server-side redirect inmediato a /admin/dashboard.
    await expect(page).toHaveURL(/\/admin\/dashboard/, { timeout: 10_000 });
  });
});
