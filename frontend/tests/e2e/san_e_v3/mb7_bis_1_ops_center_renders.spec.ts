/**
 * SAN-E v3.MB-7.bis.1 · /admin/retainers Ops Center renders.
 *
 * Verifica:
 *  - /admin/retainers (legacy) → redirige a /admin/projects (el Ops Center
 *    cross-cliente se retiró · retainer per-project R23)
 *  - Sub-route /admin/retainers/churn-risk → redirige a /admin/dashboard
 *    (migrada a widget · Sesión 3B-2B.3 Phase X.4d)
 */
import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "../_helpers/auth-real";


test.use({ viewport: { width: 1280, height: 800 } });


test.describe("SAN-E v3.MB-7.bis.1 · RetainerOpsCenter plural route", () => {
  // La consola cross-cliente "Consola Retainer" + CapacityTile se eliminó a
  // propósito (Sesión 3B-2B.3 Phase X.3 · R23: el retainer es per-project).
  // /admin/retainers es hoy un redirect server-side a /admin/projects
  // (app/(admin)/admin/retainers/page.tsx) y el retainer vive en
  // /admin/projects/[id]/retainer (cubierto por fase_9/02-retainer.spec.ts).
  test("/admin/retainers (legacy) redirige a /admin/projects", async ({
    context, page,
  }) => {
    await loginAsMarcos(context);
    await page.goto("/admin/retainers");
    await expect(page).toHaveURL(/\/admin\/projects$/, { timeout: 10_000 });
  });

  test("/admin/retainers/churn-risk redirige a /admin/dashboard", async ({
    context, page,
  }) => {
    await loginAsMarcos(context);
    await page.goto("/admin/retainers/churn-risk");
    // `load` y no `networkidle`: el portal mantiene abierta la conexion SSE de
    // eventos, y con ella la red nunca queda inactiva (la espera no acaba nunca).
    await page.waitForLoadState("load");
    // La ruta standalone fue migrada a widget en el dashboard (Sesión 3B-2B.3
    // Phase X.4d) · server-side redirect inmediato a /admin/dashboard.
    await expect(page).toHaveURL(/\/admin\/dashboard/, { timeout: 10_000 });
  });
});
