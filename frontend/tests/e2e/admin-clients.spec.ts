/**
 * E2E test admin clients (FASE 5 sub-fase 5.C · remodelado R23).
 *
 * El panel cross-cliente /admin/clients (listado + wizard 3 pasos + detalle con
 * 7 tabs) se consolidó en vistas project-scoped (Sesión 3B-2B.3 Phase X.3/X.4):
 *   - /admin/clients       → redirect /admin/projects
 *   - /admin/clients/new   → redirect /admin/projects/new
 *   - /admin/clients/[id]  → resuelve cliente→proyecto → /admin/projects/[id]/cliente-info
 * Los datos del cliente (DatosTab) y el SuspendDialog viven ahora en
 * /admin/projects/[id]/cliente-info. Esta spec cubre eso.
 *
 * Pattern: loginAsMarcos(context) + mockProjectShell + page.route mocks.
 */
import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";

import { loginAsMarcos } from "./_helpers/auth-real";
import { mockProjectShell } from "./_helpers/project-shell";

const CLIENT_ID = "11111111-1111-1111-1111-111111111111";
const PROJECT_ID = "33333333-3333-4333-8333-333333333333";

const MOCK_CLIENT_LIST = [
  {
    id: CLIENT_ID,
    nombre: "Ayuntamiento Test E2E",
    cif: "P1234567A",
    sector: "publico",
    contacto_email: "test@example.com",
    contacto_telefono: null,
    created_at: "2026-04-29T10:00:00Z",
    deleted_at: null,
  },
  {
    id: "22222222-2222-2222-2222-222222222222",
    nombre: "Cliente Suspendido SL",
    cif: "B98765432",
    sector: "privado",
    contacto_email: null,
    contacto_telefono: null,
    created_at: "2026-04-20T10:00:00Z",
    deleted_at: "2026-04-25T10:00:00Z",
  },
];

const MOCK_CLIENT_DETAIL = {
  id: CLIENT_ID,
  nombre: "Ayuntamiento Test E2E",
  cif: "P1234567A",
  sector: "publico",
  provincia: "Madrid",
  numero_empleados: 250,
  contacto_email: "test@example.com",
  contacto_telefono: null,
  lead_source: null,
  logo_path: null,
  created_at: "2026-04-29T10:00:00Z",
  updated_at: "2026-04-29T10:00:00Z",
  deleted_at: null,
  projects_count: 2,
  users_count: 3,
  last_activity_at: "2026-04-29T11:00:00Z",
};

async function stubClientsBackend(page: Page) {
  // IMPORTANTE: registrar mocks del más específico al menos específico.
  // Playwright page.route matches en orden de registro inverso (último
  // registered handler wins) — registramos primero el genérico (lista)
  // para que el específico ({id}, {id}/audit, etc.) se evalúe primero.

  // GET /api/v1/clients (listado + sidebar feed) — el menos específico.
  await page.route(/\/api\/v1\/clients\/?(\?.*)?$/, async (route) => {
    if (route.request().method() === "GET") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(MOCK_CLIENT_LIST),
      });
    } else {
      await route.continue();
    }
  });

  // GET /api/v1/clients/{id} detalle — más específico (registrado después
  // → matchea primero por LIFO de Playwright).
  await page.route(`**/api/v1/clients/${CLIENT_ID}`, async (route) => {
    if (route.request().method() === "GET") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(MOCK_CLIENT_DETAIL),
      });
    } else {
      await route.continue();
    }
  });

  // GET /api/v1/clients/{id}/projects (router legacy /admin/clients/[id])
  await page.route(
    `**/api/v1/clients/${CLIENT_ID}/projects`,
    async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([
          {
            id: PROJECT_ID,
            client_id: CLIENT_ID,
            nombre: "Proyecto ENS Test",
            categoria_objetivo: "MEDIA",
            created_at: "2026-04-29T10:00:00Z",
          },
        ]),
      });
    },
  );

  // Layout project-scoped (header + feature-flags) del proyecto sintético.
  await mockProjectShell(page, {
    projectId: PROJECT_ID,
    clientId: CLIENT_ID,
    clientName: MOCK_CLIENT_DETAIL.nombre,
  });

  // GET /api/v1/clients/{id}/audit (Tab Audit Log)
  await page.route(
    `**/api/v1/clients/${CLIENT_ID}/audit*`,
    async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          items: [],
          total: 0,
          page: 1,
          size: 25,
        }),
      });
    },
  );

  // GET /api/v1/clients/{id}/users (Tab Usuarios — cockpit)
  await page.route(
    `**/api/v1/clients/${CLIENT_ID}/users`,
    async (route) => {
      if (route.request().method() === "GET") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify([]),
        });
      } else {
        await route.continue();
      }
    },
  );

  // GET /api/v1/billing/clients/{id}/invoices (Tab Facturas)
  await page.route(
    `**/api/v1/billing/clients/${CLIENT_ID}/invoices`,
    async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([]),
      });
    },
  );
}

test.describe("Admin Clients · redirects legacy + cliente-info", () => {
  test.beforeEach(async ({ context, page }) => {
    await loginAsMarcos(context);
    await stubClientsBackend(page);
  });

  test("rutas legacy /admin/clients redirigen a las vistas project-scoped", async ({
    page,
  }) => {
    await page.goto("/admin/clients");
    await expect(page).toHaveURL(/\/admin\/projects$/);

    await page.goto("/admin/clients/new");
    await expect(page).toHaveURL(/\/admin\/projects\/new$/);

    // El detalle legacy resuelve el proyecto del cliente y abre su cliente-info.
    await page.goto(`/admin/clients/${CLIENT_ID}`);
    await expect(page).toHaveURL(
      new RegExp(`/admin/projects/${PROJECT_ID}/cliente-info$`),
    );
    await expect(
      page.getByRole("heading", { name: /ayuntamiento test e2e/i, level: 1 }),
    ).toBeVisible();
    await expect(page.getByText("P1234567A")).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Datos identificativos" }),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Contactos cliente" }),
    ).toBeVisible();
  });

  test("Datos cliente edits + saves with toast success", async ({ page }) => {
    let patchBody: Record<string, unknown> | null = null;
    await page.route(`**/api/v1/clients/${CLIENT_ID}`, async (route) => {
      if (route.request().method() === "PATCH") {
        patchBody = route.request().postDataJSON() as Record<string, unknown>;
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            ...MOCK_CLIENT_DETAIL,
            nombre: "Ayuntamiento Test EDITADO",
          }),
        });
      } else if (route.request().method() === "GET") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(MOCK_CLIENT_DETAIL),
        });
      } else {
        await route.continue();
      }
    });

    await page.goto(`/admin/projects/${PROJECT_ID}/cliente-info`);

    const nombreInput = page.locator('input[id="nombre"]');
    await expect(nombreInput).toHaveValue("Ayuntamiento Test E2E");
    await nombreInput.fill("Ayuntamiento Test EDITADO");

    await page.getByRole("button", { name: /guardar cambios/i }).click();

    await expect(
      page.getByText(/datos cliente actualizados/i),
    ).toBeVisible({ timeout: 5000 });
    expect(patchBody).toMatchObject({ nombre: "Ayuntamiento Test EDITADO" });
  });

  test("SuspendDialog type-to-confirm gating + submit", async ({ page }) => {
    let suspendCalled = false;
    await page.route(
      `**/api/v1/clients/${CLIENT_ID}/suspend`,
      async (route) => {
        suspendCalled = true;
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            ...MOCK_CLIENT_DETAIL,
            deleted_at: "2026-04-29T13:00:00Z",
          }),
        });
      },
    );

    await page.goto(`/admin/projects/${PROJECT_ID}/cliente-info`);

    await page.getByRole("button", { name: /^suspender$/i }).click();

    await expect(
      page.getByRole("heading", { name: /suspender cliente/i }),
    ).toBeVisible();

    const confirmBtn = page.getByRole("button", {
      name: /^suspender cliente$/i,
    });
    await expect(confirmBtn).toBeDisabled();

    const confirmInput = page.locator('input[id="suspend-confirm-input"]');
    await confirmInput.fill("wrong text");
    await expect(confirmBtn).toBeDisabled();

    await confirmInput.fill("Ayuntamiento Test E2E");
    await expect(confirmBtn).toBeEnabled();

    await confirmBtn.click();

    await expect(
      page.getByText(/cliente suspendido/i).first(),
    ).toBeVisible({ timeout: 5000 });
    expect(suspendCalled).toBe(true);
  });
});
