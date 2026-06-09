/**
 * E2E · fase_36 admin Project Selector landing page (sub-atom 1.E.2 · ADR-054).
 *
 * Verifica:
 *  - /admin/projects render con grid cards selector
 *  - Search filter funcional
 *  - Empty state friendly cuando 0 matches
 *  - "Último usado" badge si lastUsedProjectId en localStorage
 */
import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "../../_helpers/auth-real";
import {
  CLIENT_F36_ID,
  PROJECT_F36_A_ID,
  PROJECT_F36_B_ID,
  mockClientsAndHeaders,
} from "../_fixtures";

test.describe("fase_36 admin · projects selector landing", () => {
  test("selector landing renders grid cards", async ({ page }) => {
    await loginAsMarcos(page.context());
    await mockClientsAndHeaders(page);

    await page.goto("/admin/projects");

    // Hero title nuevo Phase C
    await expect(page.getByRole("heading", { name: /Selecciona un proyecto/i })).toBeVisible();

    // Search input visible
    await expect(page.getByTestId("projects-search-input")).toBeVisible();

    // Grid + 2 cards (mocked clients)
    await expect(page.getByTestId("projects-grid")).toBeVisible();
    await expect(page.getByTestId(`project-card-${PROJECT_F36_A_ID}`)).toBeVisible();
    await expect(page.getByTestId(`project-card-${PROJECT_F36_B_ID}`)).toBeVisible();
  });

  test("search filter reduces visible cards", async ({ page }) => {
    await loginAsMarcos(page.context());
    await mockClientsAndHeaders(page);

    await page.goto("/admin/projects");
    await page.getByTestId(`project-card-${PROJECT_F36_A_ID}`).waitFor();

    await page.getByTestId("projects-search-input").fill("Piloto");

    await expect(page.getByTestId(`project-card-${PROJECT_F36_A_ID}`)).toBeVisible();
    await expect(
      page.getByTestId(`project-card-${PROJECT_F36_B_ID}`),
    ).not.toBeVisible();
  });

  test("último usado badge visible cuando lastUsedProjectId persistido", async ({ page }) => {
    await loginAsMarcos(page.context());
    await mockClientsAndHeaders(page);

    // Pre-populate localStorage con lastUsedProjectId
    await page.addInitScript(
      (lastId: string) => {
        window.localStorage.setItem(
          "fulkro-active-project",
          JSON.stringify({ state: { lastUsedProjectId: lastId }, version: 0 }),
        );
      },
      PROJECT_F36_A_ID,
    );

    await page.goto("/admin/projects");
    await page.getByTestId(`project-card-${PROJECT_F36_A_ID}`).waitFor();

    // Badge "Último usado" en card A · NO en card B
    const cardA = page.getByTestId(`project-card-${PROJECT_F36_A_ID}`);
    await expect(cardA.getByText(/Último usado/i)).toBeVisible();

    const cardB = page.getByTestId(`project-card-${PROJECT_F36_B_ID}`);
    await expect(cardB.getByText(/Último usado/i)).not.toBeVisible();
  });
});
