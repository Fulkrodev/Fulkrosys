/**
 * E2E · fase_36 admin Active Project Banner + Switcher (sub-atom 1.E.2 · ADR-054).
 *
 * Verifica:
 *  - Banner empty state visible cuando NO active project
 *  - Banner con cliente + project + ENS badge cuando active project sync
 *  - ProjectSwitcherDropdown trigger + dropdown content
 *  - Switch project via dropdown navega correctamente
 */
import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "../../_helpers/auth-real";
import {
  CLIENT_F36_B_ID,
  CLIENT_F36_ID,
  PROJECT_F36_A_ID,
  mockClientsAndHeaders,
} from "../_fixtures";

test.describe("fase_36 admin · active project banner + switcher", () => {
  test("empty state banner visible cuando NO active project", async ({ page }) => {
    await loginAsMarcos(page.context());
    await mockClientsAndHeaders(page);

    // Clear localStorage para garantizar empty state
    await page.addInitScript(() => {
      window.localStorage.removeItem("fulkro-active-project");
    });

    await page.goto("/admin/projects");

    // Banner empty visible · "Sin proyecto activo". UI drift: ese texto aparece
    // también en las project-cards del selector → scope al banner empty.
    await expect(page.getByTestId("active-project-banner-empty")).toBeVisible();
    await expect(
      page.getByTestId("active-project-banner-empty").getByText(/Sin proyecto activo/i),
    ).toBeVisible();
  });

  test("banner con metadata después navegación a project", async ({ page }) => {
    await loginAsMarcos(page.context());
    await mockClientsAndHeaders(page);

    // Ruta real del landing project-scoped es /summary (antes /dashboard, que
    // ahora 404 · el index /admin/projects/[id] redirige a /summary).
    await page.goto(`/admin/projects/${PROJECT_F36_A_ID}/summary`);

    // Banner full visible (NO empty)
    await expect(page.getByTestId("active-project-banner")).toBeVisible();

    // Client name visible en banner
    await expect(
      page.getByTestId("active-project-banner").getByText(/Cliente Piloto MEDIA/i),
    ).toBeVisible();

    // ENS category badge MEDIA visible
    await expect(
      page.getByTestId("active-project-category-badge"),
    ).toContainText(/MEDIA/i);
  });

  // Los items del switcher son CLIENTES (testid por client.id) y el activo se
  // marca comparando con el cliente del proyecto activo (header · cliente.id).
  test("switcher dropdown opens y lista clients", async ({ page }) => {
    await loginAsMarcos(page.context());
    await mockClientsAndHeaders(page);

    await page.goto(`/admin/projects/${PROJECT_F36_A_ID}/summary`);
    await page.getByTestId("active-project-banner").waitFor();

    // Trigger dropdown
    await page.getByTestId("project-switcher-trigger").click();

    // Items visible · activo marcado + alternativo presente
    await expect(
      page.getByTestId(`project-switcher-item-${CLIENT_F36_ID}`),
    ).toBeVisible();
    await expect(
      page.getByTestId(`project-switcher-item-${CLIENT_F36_B_ID}`),
    ).toBeVisible();

    // Activo label visible en item A
    const itemA = page.getByTestId(`project-switcher-item-${CLIENT_F36_ID}`);
    await expect(itemA.getByText(/activo/i)).toBeVisible();
    await expect(
      page.getByTestId(`project-switcher-item-${CLIENT_F36_B_ID}`).getByText(/activo/i),
    ).toHaveCount(0);
  });
});
