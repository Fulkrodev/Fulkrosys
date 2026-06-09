/**
 * E2E test admin meetings panel + ContactQuickPicker M30 reuse + SSE
 * progressive render (FASE 7 sub-bloque 7.C.1 sesión 11).
 *
 * Cobertura 3 tests:
 * 1. Form admin-meetings/new con submit + redirect a /admin/meetings/{id}
 * 2. MeetingLayoutV2 muestra metadata + status + ContactQuickPicker M30
 *    + complete workflow (toast success)
 * 3. MeetingsHistoryTable embed en /admin/clients/[id]/meetings filter
 *    by client + JOIN interlocutor_name
 *
 * Pattern post-MF3.5: loginAsMarcos(context) + page.route mocks
 * (canónico admin-clients.spec.ts y admin-messages.spec.ts).
 */
import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";

import { loginAsMarcos } from "./_helpers/auth-real";

const CLIENT_A_ID = "11111111-1111-1111-1111-111111111111";
const MEETING_A_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa";
const CONTACT_A_ID = "cccccccc-cccc-cccc-cccc-cccccccccccc";

const MOCK_CLIENTS = [
  {
    id: CLIENT_A_ID,
    nombre: "Ayuntamiento Test FASE 7",
    cif: "P1234567A",
    sector: "publico",
    contacto_email: "test@example.com",
    contacto_telefono: null,
    created_at: "2026-04-30T10:00:00Z",
    deleted_at: null,
  },
];

const MOCK_CONTACTS = [
  {
    id: CONTACT_A_ID,
    full_name: "Ana López (CFO)",
    email: "ana@cliente.com",
    role_title: "CFO",
    role_category: "sponsor",
    is_primary: true,
    is_signatory: true,
    is_active: true,
    has_portal_access: false,
    inactive_since: null,
    created_at: "2026-04-30T10:00:00Z",
  },
];

const MOCK_MEETING_DETAIL = {
  id: MEETING_A_ID,
  client_id: CLIENT_A_ID,
  project_id: null,
  title: "Reunión kickoff ENS",
  platform: "google_meet",
  meeting_url: "https://meet.google.com/abc-defg-hij",
  etapa_k: "K.4",
  interlocutor_contact_id: CONTACT_A_ID,
  interlocutor: {
    contact_id: CONTACT_A_ID,
    full_name: "Ana López (CFO)",
    role_title: "CFO",
    role_category: "sponsor",
    email: "ana@cliente.com",
    notes_excerpt: null,
  },
  meeting_date: null,
  duration_minutes: null,
  status: "scheduled",
  completed_at: null,
  cancelled_at: null,
  notes_markdown: null,
  notes_html_sanitized: null,
  sse_session_id: null,
  outputs_agente_18: null,
  lead_source: null,
  conversion_status: "proposal_pending",
  proposal_generated_id: null,
  created_at: "2026-04-30T10:00:00Z",
};

const MOCK_BY_CLIENT_LIST = [
  {
    id: MEETING_A_ID,
    client_id: CLIENT_A_ID,
    project_id: null,
    title: "Reunión kickoff ENS",
    platform: "google_meet",
    etapa_k: "K.4",
    interlocutor_contact_id: CONTACT_A_ID,
    interlocutor_name: "Ana López (CFO)",
    meeting_date: "2026-04-30T11:00:00Z",
    status: "scheduled",
    duration_minutes: null,
    has_notes: false,
  },
];

async function stubMeetingsBackend(page: Page) {
  // GET /api/v1/clients (sidebar + Select)
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

  // GET /api/v1/clients/{id}/contacts (ContactQuickPicker)
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

  // POST /api/v1/admin/meetings (create)
  await page.route(
    /\/api\/v1\/admin\/meetings(\?.*)?$/,
    async (route) => {
      if (route.request().method() === "POST") {
        await route.fulfill({
          status: 201,
          contentType: "application/json",
          body: JSON.stringify(MOCK_MEETING_DETAIL),
        });
      } else if (route.request().method() === "GET") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify([
            {
              id: MEETING_A_ID,
              client_id: CLIENT_A_ID,
              project_id: null,
              title: "Reunión kickoff ENS",
              platform: "google_meet",
              etapa_k: "K.4",
              interlocutor_contact_id: CONTACT_A_ID,
              interlocutor_name: null,
              meeting_date: null,
              status: "scheduled",
              duration_minutes: null,
              has_notes: false,
            },
          ]),
        });
      } else {
        await route.continue();
      }
    },
  );

  // GET /api/v1/admin/meetings/{id}
  await page.route(
    new RegExp(`/api/v1/admin/meetings/${MEETING_A_ID}$`),
    async (route) => {
      if (route.request().method() === "GET") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(MOCK_MEETING_DETAIL),
        });
      } else if (route.request().method() === "PATCH") {
        const body = await route.request().postDataJSON();
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ ...MOCK_MEETING_DETAIL, ...body }),
        });
      } else {
        await route.continue();
      }
    },
  );

  // POST /api/v1/admin/meetings/{id}/complete
  await page.route(
    new RegExp(`/api/v1/admin/meetings/${MEETING_A_ID}/complete$`),
    async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          ...MOCK_MEETING_DETAIL,
          status: "completed",
          completed_at: "2026-04-30T12:00:00Z",
        }),
      });
    },
  );

  // GET /api/v1/admin/meetings/by-client/{id}
  await page.route(
    new RegExp(`/api/v1/admin/meetings/by-client/${CLIENT_A_ID}.*$`),
    async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(MOCK_BY_CLIENT_LIST),
      });
    },
  );

  // GET /api/v1/clients/{id} (detail page para tabs)
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
            updated_at: "2026-04-30T10:00:00Z",
            projects_count: 0,
            users_count: 0,
            last_activity_at: "2026-04-30T11:00:00Z",
            logo_path: null,
          }),
        });
      } else {
        await route.continue();
      }
    },
  );
}

test.describe("Admin Meetings Panel (FASE 7)", () => {
  test.beforeEach(async ({ context, page }) => {
    await loginAsMarcos(context);
    await stubMeetingsBackend(page);
  });

  test("form /admin/meetings/new submits + redirect a detail", async ({
    page,
  }) => {
    await page.goto("/admin/meetings/new");

    await expect(
      page.getByRole("heading", { name: /Nueva reunión/i }),
    ).toBeVisible();

    // Cliente Select
    const clientSelect = page.locator("select#meeting-client");
    await clientSelect.selectOption(CLIENT_A_ID);

    // Title input
    await page
      .getByLabel(/^Título$/i)
      .fill("Reunión kickoff ENS");

    // Platform Select opcional
    const platformSelect = page.locator("select#meeting-platform");
    await platformSelect.selectOption("google_meet");

    // Etapa K Select opcional
    const etapaSelect = page.locator("select#meeting-etapa");
    await etapaSelect.selectOption("K.4");

    // Submit
    await page.getByRole("button", { name: /Crear reunión/i }).click();

    // Toast success
    await expect(page.getByText(/Reunión creada/i)).toBeVisible({
      timeout: 5_000,
    });

    // Redirect a /admin/meetings/{id}
    await page.waitForURL(new RegExp(`/admin/meetings/${MEETING_A_ID}$`));
  });

  test("MeetingLayoutV2 muestra metadata + interlocutor M30 + complete", async ({
    page,
  }) => {
    await page.goto(`/admin/meetings/${MEETING_A_ID}`);

    // Header h1 con título
    await expect(
      page.getByRole("heading", { name: /Reunión kickoff ENS/i }),
    ).toBeVisible();

    // Status badge "Programada"
    await expect(page.getByText(/Programada/i).first()).toBeVisible();

    // Metadata fields visibles
    await expect(page.getByLabel(/^Título$/i)).toHaveValue(
      "Reunión kickoff ENS",
    );

    // Interlocutor mini-card M30 (Ana López CFO)
    await expect(
      page.getByText(/Ana López \(CFO\)/i).first(),
    ).toBeVisible();
    await expect(
      page.getByText(/CFO · sponsor/i).first(),
    ).toBeVisible();

    // Botones workflow
    const completeBtn = page.getByRole("button", {
      name: /Marcar completada/i,
    });
    await expect(completeBtn).toBeVisible();

    // Click complete + confirm dialog (window.confirm mock)
    page.once("dialog", async (dialog) => {
      await dialog.accept();
    });
    await completeBtn.click();

    // UI drift: tras completar aparecen 2 nodos con /Reunión completada/ — el
    // toast sonner ("M30 timeline actualizado") y el badge read-only del row.
    await expect(
      page.getByText(/Reunión completada/i).first(),
    ).toBeVisible({ timeout: 5_000 });
  });

  // SKIP: feature eliminada (MeetingsHistoryTable embebida en
  // /admin/clients/[id]/meetings · histórico per-cliente). Esa ruta ahora hace
  // redirect() server-side hacia /admin/meetings (cross-cliente · Sesión 3B-2B.3
  // Phase X.4c). El heading "Reuniones del cliente" y el filtro per-cliente no
  // existen ya en esa ruta. Candidata a borrar tras contraste (Marcos).
  test.skip("MeetingsHistoryTable embed /admin/clients/[id]/meetings filtered + JOIN interlocutor", async ({
    page,
  }) => {
    await page.goto(`/admin/clients/${CLIENT_A_ID}/meetings`);

    // Header h1
    await expect(
      page.getByRole("heading", {
        name: /Reuniones del cliente/i,
        level: 1,
      }),
    ).toBeVisible();

    // Tabla con 1 row meeting
    await expect(
      page.getByRole("link", { name: /Reunión kickoff ENS/i }),
    ).toBeVisible();

    // Interlocutor name resolved JOIN
    await expect(
      page.getByText(/Ana López \(CFO\)/i),
    ).toBeVisible();

    // Filter status Select visible
    await expect(
      page.getByRole("combobox", { name: /Filtrar por estado/i }),
    ).toBeVisible();

    // Button Nueva reunión enlaza a /admin/meetings/new?client_id=...
    const newBtn = page.getByRole("link", {
      name: /Nueva reunión para este cliente/i,
    });
    await expect(newBtn).toBeVisible();
    await expect(newBtn).toHaveAttribute(
      "href",
      `/admin/meetings/new?client_id=${CLIENT_A_ID}`,
    );
  });
});
