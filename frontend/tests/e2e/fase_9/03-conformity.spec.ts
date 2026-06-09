import { test, expect } from "@playwright/test";

import { loginAsMarcos } from "../_helpers/auth-real";

const SEED = "842dadbf-3776-40ec-9f04-94cd05d43203";

/**
 * FASE 9.D · canonical regression spec /admin/projects/[id]/conformity.
 *
 * Verifica:
 *  - Página renderiza tras login.
 *  - Sidebar visible con gradient (chrome consistency CONSISTENCY-001).
 *  - 0 console errors críticos (filtra 404 + hydration warnings benignos).
 *
 * No assertions sobre datos específicos · proyecto seed puede tener
 * estados variables y queremos red de seguridad estable.
 */
test("9.D.3 /conformity renders + sidebar gradient + 0 critical errors", async ({
  page,
  context,
}) => {
  await loginAsMarcos(context);

  const errors: string[] = [];
  page.on("console", (msg) => {
    if (msg.type() === "error" && !/404|hydration/i.test(msg.text())) {
      errors.push(msg.text());
    }
  });
  page.on("pageerror", (err) => errors.push(`PAGEERROR: ${err.message}`));

  await page.goto(`/admin/projects/${SEED}/conformity`);
  await page.waitForLoadState("domcontentloaded", { timeout: 15000 });
  await page.waitForTimeout(2500);

  const sidebar = page.locator("aside").first();
  await expect(sidebar).toBeVisible();
  // El gradient vive en el pseudo-elemento `.sidebar-chrome::before`
  // (Pattern #1 axe-core workaround · Sidebar.tsx) · el <aside> sólo lleva
  // background-color sólido #0a1a5c. Leemos el background-image del ::before.
  const beforeBg = await sidebar.evaluate(
    (el) => window.getComputedStyle(el, "::before").backgroundImage,
  );
  expect(beforeBg.toLowerCase()).toContain("linear-gradient");

  expect(errors).toEqual([]);
});
