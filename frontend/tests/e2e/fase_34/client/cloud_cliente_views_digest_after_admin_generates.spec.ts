/**
 * E2E · fase_34 cliente · digest visibility R29 firmísimo (1.D.X.VERIFY 2b).
 *
 * Verifica:
 *  - ClientDigestCard render en /client-portal/retainer-checkin con score + trend
 *  - Trend baja USA color naranja_suave · NUNCA rojo (R29 sin alarma)
 *  - Empty state friendly cuando has_snapshot=false (1er resumen)
 *  - Summary_friendly server-side · sin jerga admin
 */
import { expect, test } from "@playwright/test";

import { loginAsClient } from "../../_helpers/auth-real";
import { mockClientDigestBase } from "../_fixtures";

test.describe("fase_34 cliente · digest visibility R29", () => {
  test("ClientDigestCard renders with mejora trend (verde · no alarma)", async ({
    page,
  }) => {
    await loginAsClient(page);
    await mockClientDigestBase(page, "mejora");

    await page.goto("/client-portal/retainer-checkin");
    await expect(page.getByTestId("client-digest-card")).toBeVisible();
    await expect(page.getByTestId("client-digest-score")).toContainText("92");
    await expect(page.getByTestId("client-digest-trend")).toContainText(/Vamos mejorando/i);
    await expect(page.getByTestId("client-digest-summary")).toContainText(
      /vamos mejorando/i,
    );

    // R29 CRITICAL: NUNCA color rojo aunque haya trend negative
    // (verde aquí · pero sanity check en CSS class)
    const card = page.getByTestId("client-digest-card");
    const classes = await card.getAttribute("class");
    expect(classes ?? "").not.toMatch(/red-|destructive/);
  });

  test("Trend baja uses naranja_suave NUNCA rojo (R29 firmísimo)", async ({
    page,
  }) => {
    await loginAsClient(page);
    await mockClientDigestBase(page, "baja");

    await page.goto("/client-portal/retainer-checkin");
    await expect(page.getByTestId("client-digest-card")).toBeVisible();

    // CRITICAL R29: bajada NO debe mostrarse en rojo · solo naranja suave
    const card = page.getByTestId("client-digest-card");
    const classes = await card.getAttribute("class");
    expect(classes ?? "").not.toMatch(/red-|destructive|bg-red/);
    // Summary debe ser amable · NO "preocupante" "urgente" "crítico"
    const summary = await page.getByTestId("client-digest-summary").textContent();
    expect((summary ?? "").toLowerCase()).not.toMatch(
      /preocup|urgente|crítico|alarmante/,
    );
    // Sí debe sugerir comentarlo en próxima reunión (tono positivo R29)
    expect((summary ?? "").toLowerCase()).toMatch(/próxima reunión|comentarlos/);
  });

  test("Empty state friendly when no snapshot yet", async ({ page }) => {
    await loginAsClient(page);
    await mockClientDigestBase(page, "empty");

    await page.goto("/client-portal/retainer-checkin");
    await expect(page.getByTestId("client-digest-empty")).toBeVisible();
    await expect(page.getByText(/Tu primer resumen mensual/i)).toBeVisible();
  });
});
