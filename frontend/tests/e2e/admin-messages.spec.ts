/**
 * E2E test admin messages panel + ContactQuickPicker M30 reuse
 * (FASE 6 sub-bloque 6.B.3 sesión 11).
 *
 * Cobertura 4 tests:
 * 1. Listado /admin/messages renders header + DataTable cross-cliente +
 *    filter Cliente Select
 * 2. Open thread Sheet con mensajes cronológico + reply inline
 * 3. MensajesTab embed en /admin/clients/[id] funcional (filter aplicado)
 * 4. AdminMessageComposer ContactQuickPicker M30 cross-motor integration
 *
 * Pattern post-MF3.5: loginAsMarcos(context) + page.route mocks
 * (canónico admin-clients.spec.ts y admin-settings.spec.ts).
 */
import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";

import { loginAsMarcos } from "./_helpers/auth-real";

const CLIENT_A_ID = "11111111-1111-1111-1111-111111111111";
const CLIENT_B_ID = "22222222-2222-2222-2222-222222222222";
const THREAD_A_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa";
const THREAD_B_ID = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb";
const MSG_A1_ID = "aa111111-aaaa-aaaa-aaaa-aaaaaaaaaaaa";
const MSG_A2_ID = "aa222222-aaaa-aaaa-aaaa-aaaaaaaaaaaa";
const CONTACT_ID = "cccccccc-cccc-cccc-cccc-cccccccccccc";

const MOCK_CLIENTS = [
  {
    id: CLIENT_A_ID,
    nombre: "Cliente Alfa",
    cif: "B11111111",
    sector: "publico",
    contacto_email: "alfa@example.com",
    contacto_telefono: null,
    created_at: "2026-04-29T10:00:00Z",
    deleted_at: null,
  },
  {
    id: CLIENT_B_ID,
    nombre: "Cliente Beta",
    cif: "B22222222",
    sector: "privado",
    contacto_email: "beta@example.com",
    contacto_telefono: null,
    created_at: "2026-04-28T10:00:00Z",
    deleted_at: null,
  },
];

const MOCK_THREAD_LIST = [
  {
    thread_id: THREAD_A_ID,
    client_id: CLIENT_A_ID,
    last_message_id: MSG_A2_ID,
    last_message_excerpt:
      "Necesitamos revisar la categorización ENS antes del kickoff.",
    last_message_at: "2026-04-29T11:00:00Z",
    last_message_from_role: "client",
    total_messages: 2,
    unread_for_admin: 1,
    unread_for_client: 0,
    has_attachments: true,
    last_to_contact_id: null,
  },
  {
    thread_id: THREAD_B_ID,
    client_id: CLIENT_B_ID,
    last_message_id: "bb111111-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
    last_message_excerpt: "Confirmamos la reunión del lunes.",
    last_message_at: "2026-04-28T15:00:00Z",
    last_message_from_role: "admin",
    total_messages: 3,
    unread_for_admin: 0,
    unread_for_client: 1,
    has_attachments: false,
    last_to_contact_id: null,
  },
];

const MOCK_THREAD_A_DETAIL = [
  {
    id: MSG_A1_ID,
    thread_id: THREAD_A_ID,
    client_id: CLIENT_A_ID,
    project_id: null,
    from_role: "admin",
    from_user_id: "marcos-id",
    to_contact_id: null,
    body_markdown: "Hola, **bienvenido** al onboarding ENS.",
    body_html: "Hola, <strong>bienvenido</strong> al onboarding ENS.",
    is_read_by_admin: true,
    is_read_by_client: true,
    forwarded_to_email: null,
    forwarded_at: null,
    email_forward_status: null,
    created_at: "2026-04-29T10:00:00Z",
    attachments: [],
  },
  {
    id: MSG_A2_ID,
    thread_id: THREAD_A_ID,
    client_id: CLIENT_A_ID,
    project_id: null,
    from_role: "client",
    from_user_id: "client-user-a",
    to_contact_id: null,
    body_markdown:
      "Necesitamos revisar la categorización ENS antes del kickoff.",
    body_html:
      "Necesitamos revisar la categorización ENS antes del kickoff.",
    is_read_by_admin: false,
    is_read_by_client: true,
    forwarded_to_email: null,
    forwarded_at: null,
    email_forward_status: null,
    created_at: "2026-04-29T11:00:00Z",
    attachments: [],
  },
];

const MOCK_CONTACTS = [
  {
    id: CONTACT_ID,
    full_name: "Ana López (CFO)",
    email: "ana@cliente-alfa.com",
    role_title: "CFO",
    role_category: "sponsor",
    is_primary: true,
    is_signatory: true,
    is_active: true,
    has_portal_access: false,
    inactive_since: null,
    created_at: "2026-04-15T10:00:00Z",
  },
];

async function stubMessagesBackend(page: Page) {
  // GET /api/v1/clients (sidebar + filters Select)
  await page.route(/\/api\/v1\/clients\/?(\?.*)?$/, async (route) => {
    if (route.request().method() === "GET") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(MOCK_CLIENTS),
      });
    } else {
      await route.continue();
    }
  });

  // GET /api/v1/admin/messages (lista threads cross-cliente + filtered)
  await page.route(
    /\/api\/v1\/admin\/messages(\?.*)?$/,
    async (route) => {
      const url = route.request().url();
      if (route.request().method() === "GET") {
        // Filter ?client_id=
        const params = new URL(url).searchParams;
        const cidFilter = params.get("client_id");
        const filtered = cidFilter
          ? MOCK_THREAD_LIST.filter((t) => t.client_id === cidFilter)
          : MOCK_THREAD_LIST;
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(filtered),
        });
      } else if (route.request().method() === "POST") {
        const reqBody = await route.request().postDataJSON();
        const newMsg = {
          id: "new-msg-id",
          thread_id: reqBody.thread_id ?? "new-thread-id",
          client_id: reqBody.client_id ?? CLIENT_A_ID,
          project_id: null,
          from_role: "admin",
          from_user_id: "marcos-id",
          to_contact_id: reqBody.to_contact_id ?? null,
          body_markdown: reqBody.body_markdown,
          body_html: reqBody.body_markdown,
          is_read_by_admin: true,
          is_read_by_client: false,
          forwarded_to_email: null,
          forwarded_at: null,
          email_forward_status: null,
          created_at: "2026-04-29T12:00:00Z",
          attachments: [],
        };
        await route.fulfill({
          status: 201,
          contentType: "application/json",
          body: JSON.stringify(newMsg),
        });
      } else {
        await route.continue();
      }
    },
  );

  // GET /api/v1/admin/messages/unread-count
  await page.route(
    /\/api\/v1\/admin\/messages\/unread-count(\?.*)?$/,
    async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ unread_total: 1, unread_threads: 1 }),
      });
    },
  );

  // GET /api/v1/admin/messages/{thread_id}
  await page.route(
    new RegExp(`/api/v1/admin/messages/${THREAD_A_ID}$`),
    async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(MOCK_THREAD_A_DETAIL),
      });
    },
  );

  // POST mark-read genérico
  await page.route(
    /\/api\/v1\/admin\/messages\/[^/]+\/mark-read$/,
    async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          message_id: "any",
          is_read_by_admin: true,
          is_read_by_client: false,
        }),
      });
    },
  );

  // GET /api/v1/clients/{client_id}/contacts (ContactQuickPicker fetch)
  await page.route(
    new RegExp(`/api/v1/clients/${CLIENT_A_ID}/contacts(\\?.*)?$`),
    async (route) => {
      if (route.request().method() === "GET") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(MOCK_CONTACTS),
        });
      } else {
        await route.continue();
      }
    },
  );

  // GET /api/v1/clients/{client_id} (detail page MensajesTab)
  await page.route(
    new RegExp(`/api/v1/clients/${CLIENT_A_ID}$`),
    async (route) => {
      if (route.request().method() === "GET") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            ...MOCK_CLIENTS[0],
            provincia: "Madrid",
            numero_empleados: 100,
            updated_at: "2026-04-29T10:00:00Z",
            projects_count: 1,
            users_count: 2,
            last_activity_at: "2026-04-29T11:00:00Z",
            logo_path: null,
          }),
        });
      } else {
        await route.continue();
      }
    },
  );
}

test.describe("Admin Messages Panel", () => {
  test.beforeEach(async ({ context, page }) => {
    await loginAsMarcos(context);
    await stubMessagesBackend(page);
  });

  test("inbox cross-cliente render + filter Cliente Select", async ({
    page,
  }) => {
    await page.goto("/admin/messages");

    await expect(
      page.getByRole("heading", { name: /^Mensajes$/, level: 1 }),
    ).toBeVisible();

    await expect(
      page.getByRole("button", { name: /Nuevo mensaje/i }),
    ).toBeVisible();

    // 2 threads visibles
    await expect(page.getByText("Cliente Alfa").first()).toBeVisible();
    await expect(page.getByText("Cliente Beta").first()).toBeVisible();

    // Filtro Cliente Select existe
    await expect(
      page.getByRole("combobox", { name: /Filtrar por cliente/i }),
    ).toBeVisible();

    // Filtro only_unread button
    await expect(
      page.getByRole("button", { name: /Solo no leídos/i }),
    ).toBeVisible();
  });

  test("open thread Sheet con mensajes + reply inline", async ({ page }) => {
    await page.goto("/admin/messages");

    // Click row thread A → Sheet abre
    await page.getByText(
      /Necesitamos revisar la categorización ENS/,
    ).click();

    // Sheet "Conversación" visible
    await expect(
      page.getByRole("heading", { name: /Conversación/i }),
    ).toBeVisible();

    // 2 mensajes cronológico
    await expect(page.getByText(/bienvenido/i)).toBeVisible();
    // UI drift: el texto del mensaje aparece tanto en la preview de la lista
    // (line-clamp) como dentro del thread abierto → strict-mode 2 elementos.
    await expect(
      page.getByText(/Necesitamos revisar la categorización/).first(),
    ).toBeVisible();

    // Composer reply visible al final
    await expect(
      page.getByRole("textbox", { name: /Cuerpo del mensaje/i }),
    ).toBeVisible();

    // Fill body + submit reply
    await page
      .getByRole("textbox", { name: /Cuerpo del mensaje/i })
      .fill("Reply test E2E");

    await page.getByRole("button", { name: /^Enviar$/i }).click();

    // Toast success (sonner)
    await expect(page.getByText(/Mensaje enviado/i)).toBeVisible({
      timeout: 5_000,
    });
  });

  // SKIP: feature eliminada (MensajesTab embebida en el detalle cross-cliente
  // /admin/clients/[id] · tab "Mensajes"). La ruta /admin/clients/[id] ahora hace
  // redirect() server-side (resuelve cliente→project → /admin/projects/[id]/...
  // · Sesión 3B-2B.3 Phase X.4b), así que ni el tab "Mensajes" ni el heading
  // "Mensajes con este cliente" se renderizan en esa ruta. El inbox cross-cliente
  // (/admin/messages, tests 1/2/4) sigue vivo. Candidata a borrar tras contraste (Marcos).
  test.skip("MensajesTab embed en /admin/clients/[id] filtered", async ({
    page,
  }) => {
    await page.goto(`/admin/clients/${CLIENT_A_ID}`);

    // Click tab Mensajes
    await page.getByRole("tab", { name: /^Mensajes$/i }).click();

    // Embed AdminInboxList con clientIdFilter — solo thread Alfa
    await expect(
      page.getByText(/Necesitamos revisar la categorización/),
    ).toBeVisible();

    // Cliente Beta NO visible (filtered)
    await expect(
      page.getByText(/Confirmamos la reunión del lunes/),
    ).not.toBeVisible();

    // Header tab indica filtered scope
    await expect(
      page.getByRole("heading", {
        name: /Mensajes con este cliente/i,
        level: 3,
      }),
    ).toBeVisible();
  });

  test("AdminMessageComposer ContactQuickPicker M30 integration", async ({
    page,
  }) => {
    await page.goto("/admin/messages");

    // Click "Nuevo mensaje" → Dialog open
    await page.getByRole("button", { name: /Nuevo mensaje/i }).click();

    await expect(
      page.getByRole("dialog").getByText(/Nuevo mensaje/i).first(),
    ).toBeVisible();

    // Cliente Select disponible en composer
    const clientSelect = page.locator('select#composer-client');
    await expect(clientSelect).toBeVisible();

    // ContactQuickPicker placeholder antes seleccionar cliente
    await expect(
      page.getByText(/Selecciona un cliente primero/i),
    ).toBeVisible();

    // Seleccionar Cliente Alfa
    await clientSelect.selectOption(CLIENT_A_ID);

    // Tras seleccionar cliente, ContactQuickPicker visible
    await expect(
      page.getByRole("button", { name: /Selecciona contacto del cliente/i }),
    ).toBeVisible();

    // Fill body
    await page
      .getByRole("textbox", { name: /Cuerpo del mensaje/i })
      .fill("Mensaje test M30 picker");

    // Submit (sin seleccionar contacto explícito — to_contact_id=null OK)
    await page.getByRole("button", { name: /^Enviar$/i }).click();

    await expect(page.getByText(/Mensaje enviado/i)).toBeVisible({
      timeout: 5_000,
    });
  });
});
