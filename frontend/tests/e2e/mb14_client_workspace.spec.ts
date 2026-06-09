/**
 * MB-14 cliente · workspace pages stack real (ADR-038 SAN-D MB-14.4/6/7).
 *
 * Verifica con loginAsClient existing helper que páginas cliente nuevas
 * renderizan correctamente:
 * - /client-portal/tasks · tasks list page
 * - /client-portal/chat · chat page
 * - /client-portal/evidencias · upload page
 * - Sidebar nav items accesibles
 */
import { expect, test } from "@playwright/test";

import { loginAsClient } from "./_helpers/auth-real";

test.describe("MB-14 cliente · workspace pages stack real", () => {
  test("Tasks page renderiza con filtros + estado vacío", async ({
    page,
  }) => {
    await page.route("**/api/v1/client-portal/tasks**", (route) =>
      route.fulfill({ status: 200, json: [] }),
    );

    await loginAsClient(page);
    await page.goto("/client-portal/tasks");

    // h1 page title + card title both contain "Mis tareas" · usar first
    await expect(
      page.getByRole("heading", { name: /Mis tareas/i }).first(),
    ).toBeVisible();
    // Hay DOS botones "Todas": filtro de categoría ("Todas (N)") y filtro de
    // estado ("Todas"). Apuntamos por testid para evitar strict-mode.
    await expect(page.getByTestId("cliente-cat-filter-all")).toBeVisible();
    await expect(page.getByTestId("cliente-status-filter-pending")).toBeVisible();
    // Empty state celebratory R29 (copy real ClientTasksList.tsx).
    await expect(page.getByTestId("cliente-tasks-empty")).toBeVisible();
    await expect(page.getByText(/Sin tareas pendientes/i)).toBeVisible();
  });

  test("Chat page renderiza con CTA Iniciar chat sin threads", async ({
    page,
  }) => {
    await page.route("**/api/v1/client-portal/chat/threads", (route) =>
      route.fulfill({ status: 200, json: [] }),
    );

    await loginAsClient(page);
    await page.goto("/client-portal/chat");

    await expect(
      page.getByRole("heading", { name: /Chat con Marcos/i }).first(),
    ).toBeVisible();
    await expect(
      page.getByText(/SLA respuesta <2h/i),
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: /Iniciar chat/i }),
    ).toBeVisible();
  });

  test("Evidencias upload page renderiza con file picker + extensiones", async ({
    page,
  }) => {
    await loginAsClient(page);
    await page.goto("/client-portal/evidencias");

    await expect(
      page.getByRole("heading", { name: /Evidencias/i }).first(),
    ).toBeVisible();
    await expect(
      page.getByText(/Formatos aceptados:.*\.pdf/i),
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: /Subir evidencia/i }),
    ).toBeVisible();
  });

  test("Sidebar tiene items MB-14 (Mis tareas · Chat · Subir documentos)", async ({
    page,
  }) => {
    await loginAsClient(page);
    await page.goto("/client-portal/dashboard");

    await expect(
      page.getByRole("link", { name: /Mis tareas/i }),
    ).toBeVisible();
    await expect(
      page.getByRole("link", { name: /Chat con Marcos/i }),
    ).toBeVisible();
    // El enlace de subida real es "Subir documentos" (→ /client-portal/files),
    // NO "Subir evidencias" (ClientSidebar.tsx · 1.D.F.bis.III.D).
    await expect(
      page.getByRole("link", { name: /Subir documentos/i }),
    ).toBeVisible();
  });
});
