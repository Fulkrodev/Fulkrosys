/**
 * E2E test admin clients panel (FASE 5 sub-fase 5.C).
 *
 * Cobertura 5 tests:
 * 1. Listado /admin/clients renders header + DataTable + button
 *    "Nuevo cliente"
 * 2. Wizard 3 pasos /admin/clients/new navigation + submit
 *    secuencial (POST /clients + POST /clients/{id}/users)
 * 3. Detalle /admin/clients/[id] 7 tabs visibles + click renderiza
 *    contenido por tab
 * 4. Tab Datos editable: PATCH client + toast success
 * 5. SuspendDialog type-to-confirm gating: button disabled hasta
 *    razón social match, submit dispara POST /suspend
 *
 * Pattern post-MF3.5: loginAsMarcos(context) + page.route mocks
 * (canónico admin-settings.spec.ts y verification.spec.ts).
 */
import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";

import { loginAsMarcos } from "./_helpers/auth-real";

const CLIENT_ID = "11111111-1111-1111-1111-111111111111";

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

  // GET /api/v1/clients/{id}/projects (Tab Proyectos)
  await page.route(
    `**/api/v1/clients/${CLIENT_ID}/projects`,
    async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([]),
      });
    },
  );

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

// SKIP: feature eliminada (panel cross-cliente /admin/clients + /admin/clients/new
// + /admin/clients/[id] tabs). Todas estas rutas ahora hacen redirect() server-side
// hacia /admin/projects (consolidación R23 project-scoped · Sesión 3B-2B.3 Phase X.3/X.4):
//   - /admin/clients          → redirect /admin/projects
//   - /admin/clients/new       → redirect /admin/projects/new
//   - /admin/clients/[id]      → resolve cliente→project → /admin/projects/[id]/cliente-info
// Ningún heading "Clientes"/"datos cliente", DataTable, wizard 3 pasos, 7 tabs ni
// SuspendDialog existen ya en estas rutas. Candidata a borrar tras contraste (Marcos).
test.describe.skip("Admin Clients Panel", () => {
  test.beforeEach(async ({ context, page }) => {
    await loginAsMarcos(context);
    await stubClientsBackend(page);
  });

  test("listado renders header + DataTable + button Nuevo cliente", async ({
    page,
  }) => {
    await page.goto("/admin/clients");

    await expect(
      page.getByRole("heading", { name: /^clientes$/i, level: 1 }),
    ).toBeVisible();

    await expect(
      page.getByRole("link", { name: /nuevo cliente/i }),
    ).toBeVisible();

    // DataTable rows: 2 clientes seed mock (scope a main, sidebar también
    // muestra clientes mock — strict mode violation si no especificamos).
    const main = page.locator("main");
    await expect(
      main.getByRole("link", { name: "Ayuntamiento Test E2E" }),
    ).toBeVisible();
    await expect(
      main.getByRole("link", { name: "Cliente Suspendido SL" }),
    ).toBeVisible();
    await expect(main.getByText("P1234567A")).toBeVisible();

    // Filter chips visibles
    await expect(
      page.getByRole("button", { name: /^todos$/i }),
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: /^activos$/i }),
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: /^suspendidos$/i }),
    ).toBeVisible();
  });

  test("wizard 3 pasos navigates + submit secuencial", async ({ page }) => {
    // Mock POST /clients (step 1 final) + POST /clients/{id}/users (step 2 final)
    let createdClientId = "";
    await page.route("**/api/v1/clients", async (route) => {
      if (route.request().method() === "POST") {
        const created = {
          id: CLIENT_ID,
          nombre: "Cliente Wizard Test",
          cif: "B12345678",
          sector: "publico",
          contacto_email: "wizard@example.com",
          contacto_telefono: null,
          created_at: "2026-04-29T12:00:00Z",
          deleted_at: null,
        };
        createdClientId = created.id;
        await route.fulfill({
          status: 201,
          contentType: "application/json",
          body: JSON.stringify(created),
        });
      } else if (route.request().method() === "GET") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(MOCK_CLIENT_LIST),
        });
      } else {
        await route.continue();
      }
    });

    await page.route(
      `**/api/v1/clients/${CLIENT_ID}/users`,
      async (route) => {
        if (route.request().method() === "POST") {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              user: {
                id: "user-test-id",
                email: "wizard@example.com",
                full_name: "Wizard User",
                role: "rseg",
                is_active: true,
                last_login: null,
                created_at: "2026-04-29T12:00:00Z",
              },
              magic_link_sent: true,
            }),
          });
        } else {
          await route.continue();
        }
      },
    );

    await page.goto("/admin/clients/new");

    // Step 1: datos cliente
    await expect(page.getByText(/datos cliente/i).first()).toBeVisible();
    await page.getByLabel(/razón social/i).fill("Cliente Wizard Test");
    await page.getByLabel(/nif \/ cif/i).fill("B12345678");
    await page.getByLabel(/^sector$/i).fill("publico");
    await page.getByLabel(/email contacto/i).fill("wizard@example.com");
    await page.getByRole("button", { name: /continuar/i }).click();

    // Step 2: primer usuario
    await expect(page.getByText(/primer usuario cliente/i)).toBeVisible();
    await page.getByLabel(/^email$/i).fill("user@example.com");
    await page.getByLabel(/nombre completo/i).fill("Test User");
    await page.getByRole("button", { name: /continuar/i }).click();

    // Step 3: confirmación
    await expect(page.getByText(/confirmación/i).first()).toBeVisible();
    await expect(page.getByText("Cliente Wizard Test")).toBeVisible();
    await expect(page.getByText("user@example.com")).toBeVisible();

    // Submit final → POST + redirect
    await page
      .getByRole("button", { name: /^crear cliente$/i })
      .click();

    // Esperamos redirect a /admin/clients/{id} o toast con éxito
    await expect(
      page.getByText(
        /cliente creado|email invitación enviado|magic link/i,
      ),
    ).toBeVisible({ timeout: 5000 });
    expect(createdClientId).toBe(CLIENT_ID);
  });

  test("detalle renders 7 tabs visibles + click renderiza", async ({
    page,
  }) => {
    await page.goto(`/admin/clients/${CLIENT_ID}`);

    // Header
    await expect(
      page.getByRole("heading", { name: /ayuntamiento test e2e/i }),
    ).toBeVisible();
    await expect(page.getByText("P1234567A")).toBeVisible();

    // 7 tabs visibles
    for (const tabName of [
      /^datos$/i,
      /^usuarios$/i,
      /^proyectos$/i,
      /^mensajes$/i,
      /^facturas$/i,
      /^audit log$/i,
      /^contactos$/i,
    ]) {
      await expect(page.getByRole("tab", { name: tabName })).toBeVisible();
    }

    // Click tab Mensajes → placeholder M29 visible
    await page.getByRole("tab", { name: /^mensajes$/i }).click();
    await expect(page.getByText(/m29 client messaging/i)).toBeVisible();

    // Click tab Contactos → placeholder M30
    await page.getByRole("tab", { name: /^contactos$/i }).click();
    await expect(page.getByText(/m30 client contacts/i)).toBeVisible();
  });

  test("Tab Datos edits + saves with toast success", async ({ page }) => {
    let patchCalled = false;
    await page.route(`**/api/v1/clients/${CLIENT_ID}`, async (route) => {
      if (route.request().method() === "PATCH") {
        patchCalled = true;
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

    await page.goto(`/admin/clients/${CLIENT_ID}`);

    // Tab Datos default
    await expect(page.getByText(/datos cliente/i).first()).toBeVisible();

    // Edit razón social
    const nombreInput = page.locator('input[id="nombre"]');
    await nombreInput.fill("Ayuntamiento Test EDITADO");

    // Save
    await page.getByRole("button", { name: /guardar cambios/i }).click();

    // Toast success
    await expect(
      page.getByText(/datos cliente actualizados/i),
    ).toBeVisible({ timeout: 3000 });

    expect(patchCalled).toBe(true);
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

    await page.goto(`/admin/clients/${CLIENT_ID}`);

    // Click Suspender → AlertDialog opens
    await page.getByRole("button", { name: /^suspender$/i }).click();

    await expect(
      page.getByRole("heading", { name: /suspender cliente/i }),
    ).toBeVisible();

    // Confirm button initial disabled (input vacío)
    const confirmBtn = page.getByRole("button", {
      name: /^suspender cliente$/i,
    });
    await expect(confirmBtn).toBeDisabled();

    // Type wrong text → still disabled
    const confirmInput = page.locator('input[id="suspend-confirm-input"]');
    await confirmInput.fill("wrong text");
    await expect(confirmBtn).toBeDisabled();

    // Type correct razón social → enabled
    await confirmInput.fill("Ayuntamiento Test E2E");
    await expect(confirmBtn).toBeEnabled();

    // Submit
    await confirmBtn.click();

    await expect(
      page.getByText(/cliente suspendido/i),
    ).toBeVisible({ timeout: 3000 });

    expect(suspendCalled).toBe(true);
  });
});
