/**
 * E2E /client-portal/actas · SAN-E v3.MB-6 atom 5.
 *
 * Validates cliente UX actas 4 tipos signable:
 *  1. Login → /client-portal/actas
 *  2. Header "Actas reuniones" + intro visible
 *  3. SubtypeFilterChips render 6 chips (Todas + 5 subtypes)
 *  4. Sidebar nav "Actas" link visible
 */
import { expect, test } from "@playwright/test";

import { loginAsClient } from "./_helpers/auth-real";

test.describe("Client Portal · Actas · MB-6 atom 5", () => {
  test("Cliente VE page · header + filter chips render", async ({ page }) => {
    await loginAsClient(page);
    await page.goto("/client-portal/actas");

    await expect(
      page.getByRole("heading", { name: "Actas reuniones" }),
    ).toBeVisible();

    await expect(page.getByText(/Actas de comité, kickoff/i)).toBeVisible();

    // 6 chips: Todas + 5 subtypes (sub-Q3 cement)
    const chipsContainer = page.getByTestId("subtype-filter-chips");
    await expect(chipsContainer).toBeVisible();
    await expect(page.getByTestId("subtype-chip-all")).toBeVisible();
    await expect(page.getByTestId("subtype-chip-kickoff")).toBeVisible();
    await expect(page.getByTestId("subtype-chip-checkpoint")).toBeVisible();
    await expect(page.getByTestId("subtype-chip-audit")).toBeVisible();
    await expect(page.getByTestId("subtype-chip-cierre")).toBeVisible();
    await expect(page.getByTestId("subtype-chip-other")).toBeVisible();
  });

  test("Sidebar nav 'Actas' visible", async ({ page }) => {
    await loginAsClient(page);
    await page.goto("/client-portal/actas");

    const nav = page.getByRole("link", { name: "Actas", exact: true });
    await expect(nav).toBeVisible();
  });
});
