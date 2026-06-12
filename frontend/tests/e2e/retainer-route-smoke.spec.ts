/**
 * Smoke del defecto P0: la ruta /client-portal/retainer existe y renderiza
 * (oferta si CERTIFIED · empty si no) — NUNCA un 404.
 */
import { expect, test } from "@playwright/test";

import { loginAsClient, loginAsMarcos } from "./_helpers/auth-real";

const BACKEND = process.env.PLAYWRIGHT_BACKEND_URL ?? "http://localhost:8000";

test("/client-portal/retainer renderiza (oferta o empty, no 404)", async ({
  browser,
}) => {
  // Certificar el proyecto del cliente de test (para ver la OFERTA).
  const adminCtx = await browser.newContext();
  await loginAsMarcos(adminCtx);
  const tc = await adminCtx.request.post(`${BACKEND}/api/v1/_dev/create-test-client`);
  const { project_id } = await tc.json();
  const cookies = await adminCtx.cookies();
  const csrf = cookies.find((c) => c.name === "fulkro_csrf")?.value ?? "";
  await adminCtx.request.post(
    `${BACKEND}/api/v1/projects/${project_id}/audit/mark-passed`,
    {
      headers: { "x-csrf-token": csrf },
      data: { result: "passed", audit_report_ref: "E-702-SMOKE", cascade_certify: true, cascade_retainer_offer: true },
    },
  );
  await adminCtx.close();

  const page = await (await browser.newContext()).newPage();
  await loginAsClient(page, { dismissTutorial: true });
  await page.goto("/client-portal/retainer", { waitUntil: "domcontentloaded" });
  await page.waitForLoadState("networkidle", { timeout: 6000 }).catch(() => {});

  // alguna de las 3 superficies debe estar visible (NO 404)
  const anyState = page.locator(
    '[data-testid="retainer-offer-page"], [data-testid="retainer-offer-empty"], [data-testid="retainer-offer-accepted"]',
  );
  await expect(anyState.first()).toBeVisible({ timeout: 10_000 });
  await page.screenshot({ path: "../out/sim_medio_e2e/48_cliente_retainer.png", fullPage: true });

  // Si renderiza la oferta, comprobar que hay tier cards (R_STD recomendado MEDIA)
  const offer = page.getByTestId("retainer-offer-page");
  if (await offer.isVisible().catch(() => false)) {
    await expect(page.getByTestId("retainer-tier-R_STD")).toBeVisible();
    // eslint-disable-next-line no-console
    console.log("[SMOKE] oferta de retainer renderizada con tier cards");
  } else {
    // eslint-disable-next-line no-console
    console.log("[SMOKE] estado empty/accepted renderizado (ruta OK, sin 404)");
  }
});
