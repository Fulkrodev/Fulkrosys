/**
 * SAN-E v3.MB-7.1 · client dashboard adaptativo · BÁSICA tier render.
 *
 * Verifica que un cliente categoría BÁSICA ve el dashboard adaptativo
 * con las 3 zones (Hero · Tu trabajo de hoy · Resumen visual) renderizadas
 * y la categoria badge "BÁSICA" verde.
 *
 * Seed: test-client-e2e@example.com (globalSetup). Si el seed crea un
 * cliente con otra categoría, el test verifica que SE RENDERIZA UN badge
 * de categoría sin assumir el valor específico (E2E focus = render
 * health, NO data correctness per tier).
 */
import { expect, test } from "@playwright/test";

import { loginAsClient } from "../_helpers/auth-real";

test.use({ viewport: { width: 1280, height: 800 } });

test.describe("SAN-E v3.MB-7.1 · dashboard adaptativo render", () => {
  test("dashboard renderiza 3 zones · hero + actions + summary cards", async ({
    page,
  }) => {
    await loginAsClient(page);
    await page.goto("/client-portal/dashboard");
    await page.waitForLoadState("networkidle");

    // Zone 1 · Hero adaptativo
    await expect(page.getByTestId("hero-adaptativo")).toBeVisible({
      timeout: 10_000,
    });

    // Greeting visible
    await expect(page.getByRole("heading", { name: /Hola/i })).toBeVisible();

    // Either today-actions o today-actions-empty (celebratoria) presente
    const hasActions = await page.getByTestId("today-actions").isVisible().catch(() => false);
    const hasEmpty = await page.getByTestId("today-actions-empty").isVisible().catch(() => false);
    expect(hasActions || hasEmpty).toBe(true);

    // Zone 3 · Workflow stepper visible
    await expect(page.getByTestId("workflow-stepper")).toBeVisible();

    // Container principal
    await expect(page.getByTestId("client-dashboard-v3")).toBeVisible();
  });

  test("dashboard categoria badge tier-aware renderiza", async ({ page }) => {
    await loginAsClient(page);
    await page.goto("/client-portal/dashboard");
    await page.waitForLoadState("networkidle");

    await expect(page.getByTestId("hero-adaptativo")).toBeVisible();
    // El badge es "Categoría BÁSICA" o "Categoría MEDIA" o "Categoría ALTA".
    // Verificamos que aparece "Categoría" + uno de los tres tiers, sin fijar
    // cuál (depende del seed).
    const badge = page.getByText(/Categoría (BÁSICA|MEDIA|ALTA)/i);
    await expect(badge).toBeVisible();
  });
});
