/**
 * E2E · fase_35 admin M27 Conformity cloud score · display + R29 CSS guard (1.D.J).
 *
 * Verifica:
 *  - Page /admin/projects/{id}/conformity renderiza
 *  - ConformityCloudScoreCard visible cuando score > 0
 *  - Percentage + summary mostrados
 *  - Per familia breakdown bars rendered
 *  - R29 firmísimo CSS guard · NUNCA clases red/destructive/bg-red
 *  - Empty state (score=0) usa CloudOff icon · NO alarma
 */
import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "../../_helpers/auth-real";
import {
  PROJECT_F35_ID,
  mockM27ScoreBase,
  mockM27ScoreEmpty,
} from "../_fixtures";

test.describe("fase_35 admin · M27 conformity cloud score display", () => {
  test("score card renders percentage + summary + familia breakdown · R29 NUNCA rojo", async ({
    page,
  }) => {
    await loginAsMarcos(page.context());
    await mockM27ScoreBase(page);

    await page.goto(`/admin/projects/${PROJECT_F35_ID}/conformity`);
    await page.waitForLoadState("networkidle", { timeout: 10_000 }).catch(() => {});

    const scoreCard = page.getByTestId("cloud-score-card");
    await expect(scoreCard).toBeVisible();

    // Percentage shown (62.5%)
    await expect(page.getByTestId("cloud-score-percentage")).toContainText("62");

    // Summary text "5/8 medidas verificadas via cloud"
    await expect(page.getByTestId("cloud-score-summary")).toContainText("5/8");

    // Per familia breakdown bars rendered
    await expect(page.getByTestId("cloud-score-breakdown")).toBeVisible();
    await expect(page.getByTestId("cloud-score-familia-op.acc")).toBeVisible();
    await expect(page.getByTestId("cloud-score-familia-mp.s")).toBeVisible();

    // R29 firmísimo · NUNCA rojo en ningún elemento del score card
    const cardClasses = await scoreCard.getAttribute("class");
    expect(cardClasses ?? "").not.toMatch(/red-|destructive|bg-red/);

    const percentageClasses = await page
      .getByTestId("cloud-score-percentage")
      .getAttribute("class");
    expect(percentageClasses ?? "").not.toMatch(/red-|destructive|bg-red/);
  });

  test("empty state cuando score=0 · CloudOff icon · NO alarma R29", async ({
    page,
  }) => {
    await loginAsMarcos(page.context());
    await mockM27ScoreEmpty(page);

    await page.goto(`/admin/projects/${PROJECT_F35_ID}/conformity`);
    await page.waitForLoadState("networkidle", { timeout: 10_000 }).catch(() => {});

    const emptyCard = page.getByTestId("cloud-score-empty");
    await expect(emptyCard).toBeVisible();

    // R29 CSS guard empty state · NO rojo
    const emptyClasses = await emptyCard.getAttribute("class");
    expect(emptyClasses ?? "").not.toMatch(/red-|destructive|bg-red/);

    // Friendly invitation copy · NO alarma
    await expect(emptyCard).toContainText(/Aún no hay medidas verificadas/i);
    await expect(emptyCard).toContainText(/Conecta un proveedor cloud/i);
  });
});
