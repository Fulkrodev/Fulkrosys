/**
 * E2E test admin settings panel (FASE 4 sub-fase 4.B.5).
 *
 * Cobertura:
 * - 5 tabs visibles + clickables
 * - Branding: edit primary_color via input + save + toast
 * - SMTP: button "Test envío" → mock response → Alert visible
 * - About: 4 Cards visibles + corpus gauge gated por show_corpus_metric
 *
 * Pattern post-MF3.5 (alineado verification.spec.ts):
 * - loginAsMarcos(context) emite cookies JWT Ed25519 reales que pasan
 *   middleware server-side en /admin/* (mockAuthenticated puro fallaría
 *   tras BLOQUE 7 MF3.5 — middleware verifica firma).
 * - page.route mocks endpoints /admin/settings/* + /clients para
 *   hermeticidad de UI flow (no requiere fixtures DB para settings).
 */
import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";

import { loginAsMarcos } from "./_helpers/auth-real";

const MOCK_ADMIN_SETTINGS = {
  id: "00000000-0000-0000-0000-000000000001",
  branding: {
    logo_url: null,
    primary_color: "#7c3aed",
    secondary_color: "#0c0a09",
    footer_text: "FULKRO Test",
  },
  notifications: {
    client_messages_forward_enabled: true,
    client_messages_forward_to: "marcos@fulkro.es",
    smtp_custom: null,
    digest_enabled: false,
    digest_time_local: "08:00",
    magic_link_default_sender: "noreply@fulkro.es",
    magic_link_per_purpose_overrides: null,
  },
  smtp: {
    host: null,
    port: 587,
    username: null,
    password: null,
  },
  general: {
    timezone: "Europe/Madrid",
    locale: "es-ES",
    date_format: "DD/MM/YYYY",
  },
  analytics_prefs: {
    show_corpus_metric: true,
  },
  created_at: "2026-04-28T15:00:00Z",
  updated_at: null,
};

const MOCK_ABOUT = {
  version: "0.1.0",
  commit_hash: "62602d9abc1234567890",
  uptime_days: 0,
  active_clients_count: 12,
  corpus_sources_count: 0,
  corpus_sources_target: 50,
  corpus_chunks_total: 0,
  corpus_last_updated: null,
  corpus_completion_pct: 0,
  suite_passing: 100,
  test_loc_ratio_avg: 1.5,
};

async function stubSettingsBackend(page: Page) {
  // Sidebar feed — empty list para hermeticidad (no DB fixtures).
  await page.route("**/api/v1/clients", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: "[]",
    });
  });

  await page.route("**/api/v1/admin/settings", async (route) => {
    if (route.request().method() === "GET") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(MOCK_ADMIN_SETTINGS),
      });
    } else {
      await route.continue();
    }
  });

  await page.route("**/api/v1/admin/settings/about", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(MOCK_ABOUT),
    });
  });
}

test.describe("Admin Settings Panel", () => {
  test.beforeEach(async ({ context, page }) => {
    await loginAsMarcos(context);
    await stubSettingsBackend(page);
  });

  test("renders 5 tabs and switches between them", async ({ page }) => {
    await page.goto("/admin/settings");

    await expect(
      page.getByRole("heading", { name: /ajustes/i, level: 1 }),
    ).toBeVisible();

    await expect(page.getByRole("tab", { name: /branding/i })).toBeVisible();
    await expect(
      page.getByRole("tab", { name: /notificaciones/i }),
    ).toBeVisible();
    await expect(page.getByRole("tab", { name: /^smtp$/i })).toBeVisible();
    await expect(page.getByRole("tab", { name: /general/i })).toBeVisible();
    await expect(page.getByRole("tab", { name: /acerca/i })).toBeVisible();

    await expect(page.getByText("Logo corporativo")).toBeVisible();

    await page.getByRole("tab", { name: /general/i }).click();
    await expect(page.getByText(/zona horaria/i)).toBeVisible();

    await page.getByRole("tab", { name: /acerca/i }).click();
    await expect(
      page.getByRole("heading", { name: /información del sistema/i }),
    ).toBeVisible();
    await expect(
      page.getByRole("tabpanel").getByText(/clientes activos/i),
    ).toBeVisible();
  });

  test("PATCH branding shows toast on save", async ({ page }) => {
    await page.route(
      "**/api/v1/admin/settings/branding",
      async (route) => {
        if (route.request().method() === "PATCH") {
          const updated = {
            ...MOCK_ADMIN_SETTINGS,
            branding: {
              ...MOCK_ADMIN_SETTINGS.branding,
              primary_color: "#10b981",
            },
          };
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify(updated),
          });
        } else {
          await route.continue();
        }
      },
    );

    await page.goto("/admin/settings");
    await expect(page.getByText("Logo corporativo")).toBeVisible();

    const colorInput = page.locator('input[id="primary_color"]');
    await colorInput.fill("#10b981");

    await page
      .getByRole("button", { name: /guardar branding/i })
      .click();

    await expect(
      page.getByText(/branding actualizado/i),
    ).toBeVisible({ timeout: 3000 });
  });

  test("SMTP Test envío button shows success Alert inline", async ({
    page,
  }) => {
    await page.route(
      "**/api/v1/admin/settings/smtp/test",
      async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            ok: true,
            sent_to: "marcos@fulkro.es",
            backend_used: "smtp",
            error: null,
          }),
        });
      },
    );

    await page.goto("/admin/settings");

    await page.getByRole("tab", { name: /^smtp$/i }).click();
    await expect(
      page.getByText(/configuración smtp custom/i),
    ).toBeVisible();

    await page.getByRole("button", { name: /test envío/i }).click();

    await expect(
      page.getByText(/email enviado a marcos@fulkro\.es/i),
    ).toBeVisible({ timeout: 3000 });
  });

  test("About tab shows corpus gauge gated by show_corpus_metric", async ({
    page,
  }) => {
    await page.goto("/admin/settings");

    await page.getByRole("tab", { name: /acerca/i }).click();

    await expect(
      page.getByRole("heading", { name: /información del sistema/i }),
    ).toBeVisible();

    await expect(
      page.getByRole("heading", { name: /corpus normativo ens/i }),
    ).toBeVisible();
    await expect(page.getByText(/cobertura ingestion/i)).toBeVisible();

    await expect(page.getByText(/suite passing/i)).toBeVisible();

    await expect(page.getByText(/mostrar métrica corpus/i)).toBeVisible();
  });
});
