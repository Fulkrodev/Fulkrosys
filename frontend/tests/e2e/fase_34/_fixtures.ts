/**
 * Fixtures fase_34 · Cloud digest manual trigger + monitoring UI (1.D.X.VERIFY 2a).
 */
import type { Page } from "@playwright/test";

import { mockProjectShell } from "../_helpers/project-shell";

export const PROJECT_F34_ID = "f34f34f3-4f34-4f34-bf34-f34f34f34f34";

const DIGEST_LATEST = {
  id: "d1111111-1111-1111-1111-111111111111",
  project_id: PROJECT_F34_ID,
  generated_at: "2026-05-21T15:00:00Z",
  triggered_by: "admin_manual",
  triggered_by_user_id: "u1111111-1111-1111-1111-111111111111",
  compliance_score: 88,
  open_gaps_total: 2,
  open_gaps_by_severity: { critical: 1, medium: 1 },
  snapshot_jsonb: { generated_at: "2026-05-21T15:00:00Z" },
};

const DIGEST_GENERATE_RESPONSE = {
  snapshot: {
    ...DIGEST_LATEST,
    id: "d2222222-2222-2222-2222-222222222222",
    generated_at: "2026-05-21T15:05:00Z",
    triggered_by: "admin_manual",
  },
  message: "Digest generado manualmente · cliente notificado automáticamente.",
};

export async function mockCloudMonitoringAdminBase(
  page: Page,
  opts: { latest?: typeof DIGEST_LATEST | null } = {},
) {
  // Layout shell (header + feature-flags) · evita el redirect de
  // ActiveProjectSync al selector cuando el projectId es sintético.
  await mockProjectShell(page, { projectId: PROJECT_F34_ID });

  // Mocks panel base (connectors + gaps) para que tabs Monitoring renderize sin
  // errores cross-section · pattern reuse fase_33 fixtures.
  await page.route(
    /\/api\/v1\/cloud-connectors\/providers\/catalog/,
    async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ items: [] }),
      });
    },
  );
  await page.route(
    /\/api\/v1\/admin\/projects\/[^/]+\/cloud-connectors\?include_revoked=/,
    async (route) => {
      if (route.request().method() === "GET") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ items: [], total: 0 }),
        });
      } else {
        await route.continue();
      }
    },
  );
  await page.route(
    /\/api\/v1\/admin\/projects\/[^/]+\/cloud-gaps/,
    async (route) => {
      if (route.request().method() === "GET") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ items: [], total: 0 }),
        });
      } else {
        await route.continue();
      }
    },
  );

  // Latest digest endpoint
  const latest = opts.latest === undefined ? DIGEST_LATEST : opts.latest;
  await page.route(
    /\/api\/v1\/admin\/projects\/[^/]+\/cloud-monitoring\/digest\/latest/,
    async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: latest === null ? "null" : JSON.stringify(latest),
      });
    },
  );
}

export async function mockTriggerDigestOk(page: Page) {
  await page.route(
    /\/api\/v1\/admin\/projects\/[^/]+\/cloud-monitoring\/digest\/generate/,
    async (route) => {
      await route.fulfill({
        status: 201,
        contentType: "application/json",
        body: JSON.stringify(DIGEST_GENERATE_RESPONSE),
      });
    },
  );
}

// === Cliente fixtures (1.D.X.VERIFY 2b) ===

const CLIENT_DIGEST_VIEW_MEJORA = {
  digest: {
    has_snapshot: true,
    compliance_score: 92,
    trend_label: "mejora" as const,
    trend_emoji: "↑",
    trend_color_hint: "verde" as const,
    last_review_at: "2026-05-21T15:05:00Z",
    changes_reviewed_count: 3,
    consultant_name: "Marcos",
    summary_friendly:
      "Marcos revisó 3 elemento(s) este mes · vamos mejorando.",
  },
};

const CLIENT_DIGEST_VIEW_BAJA = {
  digest: {
    has_snapshot: true,
    compliance_score: 68,
    trend_label: "baja" as const,
    trend_emoji: "↓",
    trend_color_hint: "naranja_suave" as const,
    last_review_at: "2026-05-21T15:05:00Z",
    changes_reviewed_count: 7,
    consultant_name: "Marcos",
    summary_friendly:
      "Marcos revisó 7 elemento(s) este mes · podemos comentarlos en la próxima reunión.",
  },
};

const CLIENT_DIGEST_VIEW_EMPTY = {
  digest: {
    has_snapshot: false,
    compliance_score: 100,
    trend_label: "primer_resumen" as const,
    trend_emoji: "✨",
    trend_color_hint: "neutral" as const,
    last_review_at: null,
    changes_reviewed_count: 0,
    consultant_name: "Marcos",
    summary_friendly:
      "Tu primer resumen mensual estará listo pronto. Marcos lo revisará y te avisará cuando esté disponible.",
  },
};

export async function mockClientDigestBase(
  page: Page,
  variant: "mejora" | "baja" | "empty" = "mejora",
) {
  // Mock retainer-checkin base endpoints (avoid 404 cascada)
  await page.route(
    "**/api/v1/client-portal/retainer-checkin/checkins",
    async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ items: [] }),
      });
    },
  );

  const payload =
    variant === "baja"
      ? CLIENT_DIGEST_VIEW_BAJA
      : variant === "empty"
      ? CLIENT_DIGEST_VIEW_EMPTY
      : CLIENT_DIGEST_VIEW_MEJORA;

  await page.route(
    "**/api/v1/client-portal/cloud-monitoring/digest/latest",
    async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(payload),
      });
    },
  );
}

export {
  CLIENT_DIGEST_VIEW_BAJA,
  CLIENT_DIGEST_VIEW_EMPTY,
  CLIENT_DIGEST_VIEW_MEJORA,
  DIGEST_GENERATE_RESPONSE,
  DIGEST_LATEST,
};
