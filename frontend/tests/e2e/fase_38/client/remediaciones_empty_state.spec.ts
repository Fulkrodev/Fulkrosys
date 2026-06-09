/**
 * E2E · Test 1 fase_38 · cliente · /remediaciones empty state R29 friendly.
 *
 * Bloque 3+5 v3.12 · cliente NO tiene propuestas todavía.
 *
 * Verifica:
 *   - Page renderiza header "Mejoras propuestas"
 *   - Sidebar entry "Mejoras propuestas" visible
 *   - EmptyState con copy R29 friendly "Sin prisa por tu parte"
 *   - NO modal abierto
 */
import { expect, test } from "@playwright/test";

import { loginAsClient } from "../../_helpers/auth-real";
import { mockRemediationsEmpty } from "../_fixtures";

test.describe("fase_38 client · /remediaciones empty state", () => {
  test("renderiza header + empty state R29 friendly", async ({ page }) => {
    await loginAsClient(page);
    await mockRemediationsEmpty(page);

    await page.goto("/client-portal/remediaciones");

    // Header visible. UI drift: el h3 del empty state "Sin mejoras propuestas
    // todavía" también matchea /Mejoras propuestas/i → exact-match al h1.
    await expect(
      page.getByRole("heading", { name: "Mejoras propuestas", exact: true }),
    ).toBeVisible();

    // Sidebar entry visible (cement 1.D.F.bis.III + nueva entry)
    await expect(
      page.getByRole("link", { name: /Mejoras propuestas/i }),
    ).toBeVisible();

    // Empty state R29 friendly · NO presión
    await expect(
      page.getByText(/Sin mejoras propuestas todavía/i),
    ).toBeVisible();
    await expect(page.getByText(/Sin prisa por tu parte/i)).toBeVisible();

    // NO modal abierto inicial
    await expect(
      page.getByTestId("approval-modal"),
    ).toHaveCount(0);
  });
});
