/**
 * E2E tests NotificationOrchestrator UI MB-16.5 (ADR-039).
 *
 * Cobertura 8 tests:
 * 1. Cliente preferences page renderiza Card + form con defaults
 * 2. Cliente toggle email_enabled actualiza state local
 * 3. Cliente DND single field validation cliente-side
 * 4. Cliente save preferences exitoso muestra success message
 * 5. Admin notifications center renderiza stat cards + tabla
 * 6. Admin filter por status filtra eventos
 * 7. Admin redispatch button visible solo en eventos failed
 * 8. Admin redispatch action dispara API call
 *
 * Pattern stack real (MB-13/14/15/17 acumulado):
 * - loginAsMarcos(context) cookies reales backend
 * - loginAsClient(page) form fill real /client-portal/login
 * - page.route mocks API responses específicas para isolation
 */
import { expect, test } from "@playwright/test";
import type { Page, BrowserContext } from "@playwright/test";

import {
  loginAsClient,
  loginAsMarcos,
} from "./_helpers/auth-real";

const PREF_DEFAULT = {
  id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
  client_user_id: "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
  email_enabled: true,
  portal_sse_enabled: true,
  dnd_start_local: null,
  dnd_end_local: null,
  timezone: "Europe/Madrid",
  digest_mode: "immediate",
  created_at: "2026-05-06T10:00:00Z",
  updated_at: null,
};

const MOCK_EVENTS = [
  {
    id: "11111111-1111-1111-1111-111111111111",
    event_type: "task_assigned",
    recipient_user_id: "cccccccc-cccc-cccc-cccc-cccccccccccc",
    recipient_email: "ana@example.com",
    project_id: "dddddddd-dddd-dddd-dddd-dddddddddddd",
    channels_attempted: ["email", "portal_sse"],
    channels_succeeded: ["email", "portal_sse"],
    channels_failed: [],
    status: "delivered",
    error: null,
    template_used: "task_assigned",
    retry_count: 0,
    payload_jsonb: { task_id: "abc" },
    created_at: "2026-05-06T11:00:00Z",
    dispatched_at: "2026-05-06T11:00:01Z",
    delivered_at: "2026-05-06T11:00:02Z",
  },
  {
    id: "22222222-2222-2222-2222-222222222222",
    event_type: "chat_admin_reply",
    recipient_user_id: "cccccccc-cccc-cccc-cccc-cccccccccccc",
    recipient_email: "carlos@example.com",
    project_id: "dddddddd-dddd-dddd-dddd-dddddddddddd",
    channels_attempted: ["email"],
    channels_succeeded: [],
    channels_failed: ["email"],
    status: "failed",
    error: "postmark 5xx · retry exhausted",
    template_used: "chat_admin_reply",
    retry_count: 3,
    payload_jsonb: {},
    created_at: "2026-05-06T11:30:00Z",
    dispatched_at: "2026-05-06T11:30:01Z",
    delivered_at: null,
  },
];


async function stubClientPrefsBackend(page: Page): Promise<void> {
  await page.route(
    "**/api/v1/portal/notifications/preferences",
    async (route) => {
      const method = route.request().method();
      if (method === "GET") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(PREF_DEFAULT),
        });
        return;
      }
      if (method === "PUT") {
        const body = JSON.parse(route.request().postData() ?? "{}");
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ ...PREF_DEFAULT, ...body }),
        });
        return;
      }
      await route.continue();
    },
  );
}


async function stubAdminEventsBackend(page: Page): Promise<void> {
  await page.route(
    "**/api/v1/admin/notifications/events**",
    async (route) => {
      const method = route.request().method();
      const url = new URL(route.request().url());
      if (method === "GET") {
        const statusFilter = url.searchParams.get("status");
        const filtered = statusFilter
          ? MOCK_EVENTS.filter((e) => e.status === statusFilter)
          : MOCK_EVENTS;
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            items: filtered,
            total: filtered.length,
            limit: 100,
            offset: 0,
          }),
        });
        return;
      }
      await route.continue();
    },
  );
  await page.route(
    "**/api/v1/admin/notifications/events/*/redispatch",
    async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          status: "delivered",
          event_id: "redispatched-id",
          channels_succeeded: ["email"],
          channels_failed: [],
        }),
      });
    },
  );
}


test.describe("MB-16.5 · Cliente notification preferences", () => {
  test.beforeEach(async ({ page }) => {
    await stubClientPrefsBackend(page);
  });

  test("renderiza form con defaults backend", async ({ page }) => {
    await loginAsClient(page);
    await page.goto("/client-portal/account/notifications");
    await expect(
      page.getByTestId("notifications-prefs-card"),
    ).toBeVisible();
    await expect(
      page.getByTestId("notifications-preferences-form"),
    ).toBeVisible();
    const emailToggle = page.getByTestId("toggle-email-enabled");
    await expect(emailToggle).toHaveAttribute("data-state", "checked");
  });

  test("toggle email_enabled actualiza state local", async ({ page }) => {
    await loginAsClient(page);
    await page.goto("/client-portal/account/notifications");
    await page.getByTestId("notifications-preferences-form").waitFor();
    await page.getByTestId("toggle-email-enabled").click();
    await expect(
      page.getByTestId("toggle-email-enabled"),
    ).toHaveAttribute("data-state", "unchecked");
  });

  test("DND single field rejected client-side", async ({ page }) => {
    await loginAsClient(page);
    await page.goto("/client-portal/account/notifications");
    await page.getByTestId("input-dnd-start").fill("22:00");
    await page.getByTestId("btn-save-prefs").click();
    await expect(page.getByTestId("prefs-error")).toBeVisible();
    await expect(page.getByTestId("prefs-error")).toContainText(
      /ventana de silencio/i,
    );
  });

  test("save preferences successful muestra confirmation", async ({
    page,
  }) => {
    await loginAsClient(page);
    await page.goto("/client-portal/account/notifications");
    await page.getByTestId("input-dnd-start").fill("22:00");
    await page.getByTestId("input-dnd-end").fill("08:00");
    await page.getByTestId("btn-save-prefs").click();
    await expect(page.getByTestId("prefs-success")).toBeVisible();
  });
});


test.describe("MB-16.5 · Admin notifications center", () => {
  test.beforeEach(async ({ page, context }) => {
    await stubAdminEventsBackend(page);
    await loginAsMarcos(context);
  });

  test("renderiza stat cards + tabla eventos", async ({ page }) => {
    await page.goto("/admin/notifications");
    for (const status of [
      "queued",
      "dispatching",
      "delivered",
      "failed",
      "suppressed_dnd",
    ]) {
      await expect(
        page.getByTestId(`stat-card-${status}`),
      ).toBeVisible();
    }
    await expect(page.getByTestId("events-table")).toBeVisible();
    for (const event of MOCK_EVENTS) {
      await expect(
        page.getByTestId(`event-row-${event.id}`),
      ).toBeVisible();
    }
  });

  test("filter por status filtra eventos", async ({ page }) => {
    await page.goto("/admin/notifications");
    await page.getByTestId("select-status-filter").click();
    await page.getByRole("option", { name: "failed" }).click();
    await expect(
      page.getByTestId(`event-row-${MOCK_EVENTS[1].id}`),
    ).toBeVisible();
    await expect(
      page.getByTestId(`event-row-${MOCK_EVENTS[0].id}`),
    ).toHaveCount(0);
  });

  test("redispatch button visible solo eventos failed", async ({ page }) => {
    await page.goto("/admin/notifications");
    await expect(
      page.getByTestId(`btn-redispatch-${MOCK_EVENTS[1].id}`),
    ).toBeVisible();
    await expect(
      page.getByTestId(`btn-redispatch-${MOCK_EVENTS[0].id}`),
    ).toHaveCount(0);
  });

  test("redispatch action dispara API call y muestra feedback", async ({
    page,
  }) => {
    await page.goto("/admin/notifications");
    await page
      .getByTestId(`btn-redispatch-${MOCK_EVENTS[1].id}`)
      .click();
    await expect(
      page.getByTestId(`feedback-${MOCK_EVENTS[1].id}`),
    ).toBeVisible();
    await expect(
      page.getByTestId(`feedback-${MOCK_EVENTS[1].id}`),
    ).toContainText(/redispatch/i);
  });
});
