/**
 * E2E · fase_26 admin · Director · toggle Vista AHORA only vs Completa.
 *
 * Sub-atom 1.D.F.0.C v3.11 · toggle UI top-bar + persistence localStorage.
 *
 * Verifica:
 *  - Toggle Vista AHORA · sólo AHORA section visible · otras hidden
 *  - Toggle Vista Completa · 4 secciones visibles otra vez
 *  - localStorage persistence clave wcc-view-mode:{projectId}
 *  - aria-pressed actualiza correctamente
 */
import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "../../_helpers/auth-real";
import { mockAdminCronologicaFull, PROJECT_F26_ID } from "../_fixtures";

test.describe("fase_26 admin · Director toggle Vista AHORA only", () => {
  test("Vista AHORA oculta resto · Vista Completa restaura · persistence", async ({
    context,
    page,
  }) => {
    await loginAsMarcos(context);
    await mockAdminCronologicaFull(page);

    await page.goto(
      `/admin/workflow-command-center/projects/${PROJECT_F26_ID}`,
    );

    // Verifica botones toggle render
    const ahoraOnlyBtn = page.getByTestId("view-mode-ahora-only");
    const completaBtn = page.getByTestId("view-mode-complete");
    await expect(ahoraOnlyBtn).toBeVisible();
    await expect(completaBtn).toBeVisible();

    // Vista Completa por default · otras secciones visible
    await expect(completaBtn).toHaveAttribute("aria-pressed", "true");
    await expect(page.getByTestId("completed-section")).toBeVisible();
    await expect(page.getByTestId("proximos7d-section")).toBeVisible();

    // Click Vista AHORA · otras secciones desaparecen
    await ahoraOnlyBtn.click();
    await expect(ahoraOnlyBtn).toHaveAttribute("aria-pressed", "true");
    await expect(completaBtn).toHaveAttribute("aria-pressed", "false");

    // AHORA siempre visible
    await expect(page.getByTestId("ahora-section")).toBeVisible();

    // Otras secciones hidden (no render en DOM)
    await expect(page.getByTestId("completed-section")).toHaveCount(0);
    await expect(page.getByTestId("proximos7d-section")).toHaveCount(0);
    await expect(page.getByTestId("proximos30d-section")).toHaveCount(0);

    // localStorage persistence verify
    const stored = await page.evaluate((pid) => {
      return window.localStorage.getItem(`wcc-view-mode:${pid}`);
    }, PROJECT_F26_ID);
    expect(stored).toBe("ahora-only");

    // Click Vista Completa · restaura
    await completaBtn.click();
    await expect(completaBtn).toHaveAttribute("aria-pressed", "true");
    await expect(page.getByTestId("completed-section")).toBeVisible();
  });
});
