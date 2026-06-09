/**
 * Fixtures fase_33 · Cloud Connectors admin UI (sub-atom 1.D.X.J v3.12).
 */
import type { Page } from "@playwright/test";

import { mockProjectShell } from "../_helpers/project-shell";

export const PROJECT_F33_ID = "f33f33f3-3f33-4f33-bf33-f33f33f33f33";

const CONNECTORS_BASE = {
  items: [
    {
      id: "c1111111-1111-1111-1111-111111111111",
      project_id: PROJECT_F33_ID,
      provider: "microsoft_365",
      status: "connected",
      m16_connector_config_id: "m1111111-1111-1111-1111-111111111111",
      scopes: "User.Read Group.Read.All",
      last_sync_at: "2026-05-21T14:00:00Z",
      last_sync_resources_count: 42,
      revoked_at: null,
      metadata_extra: null,
      created_at: "2026-05-20T10:00:00Z",
      updated_at: "2026-05-21T14:00:00Z",
    },
    {
      id: "c2222222-2222-2222-2222-222222222222",
      project_id: PROJECT_F33_ID,
      provider: "aws",
      status: "sync_error",
      m16_connector_config_id: "m2222222-2222-2222-2222-222222222222",
      scopes: "eu-west-1",
      last_sync_at: null,
      last_sync_resources_count: 0,
      revoked_at: null,
      metadata_extra: null,
      created_at: "2026-05-20T11:00:00Z",
      updated_at: "2026-05-20T11:00:00Z",
    },
  ],
  total: 2,
};

const GAPS_BASE = {
  items: [
    {
      id: "g1111111-1111-1111-1111-111111111111",
      project_id: PROJECT_F33_ID,
      connector_id: null,
      gap_type: "structural",
      severity: "critical",
      ens_measure_code: "op.acc.6",
      title: "5 usuarios sin MFA · op.acc.6 nuclear ENS",
      explanation_es: "Detectamos 5 usuarios sin MFA…",
      suggested_action: "Activar MFA en los 5 usuarios sin segundo factor.",
      estimated_effort_days: 1,
      auto_fixable: false,
      cliente_can_see: true,
      resolved_at: null,
      resolution_note: null,
      evidence_link_id: null,
      detected_at: "2026-05-21T14:05:00Z",
    },
    {
      id: "g2222222-2222-2222-2222-222222222222",
      project_id: PROJECT_F33_ID,
      connector_id: null,
      gap_type: "documental",
      severity: "medium",
      ens_measure_code: "org.1",
      title: "Política de seguridad firmada · org.1 nuclear documental",
      explanation_es: "org.1 exige política de seguridad firmada y comunicada.",
      suggested_action: "Subir política de seguridad firmada por dirección.",
      estimated_effort_days: 1,
      auto_fixable: false,
      cliente_can_see: true,
      resolved_at: null,
      resolution_note: null,
      evidence_link_id: null,
      detected_at: "2026-05-21T14:05:00Z",
    },
  ],
  total: 2,
};

const PROVIDERS_CATALOG = [
  {
    provider: "microsoft_365",
    display_name: "Microsoft 365 / Entra ID",
    icon_emoji: "🔵",
    requires_oauth: true,
    cliente_friendly_blurb: "Cuentas y MFA.",
  },
  {
    provider: "aws",
    display_name: "AWS",
    icon_emoji: "🟧",
    requires_oauth: false,
    cliente_friendly_blurb: "IAM y buckets.",
  },
];

const RESOURCES_M365 = {
  items: [
    {
      id: "r1111111-1111-1111-1111-111111111111",
      project_id: PROJECT_F33_ID,
      connector_id: "c1111111-1111-1111-1111-111111111111",
      resource_type: "identity.user",
      resource_external_id: "ext_user_001",
      resource_name: "Alice Admin",
      attributes: { mfa_enabled: false, is_privileged: true },
      checksum: "abc123",
      detected_at: "2026-05-21T14:00:00Z",
      last_seen_at: "2026-05-21T14:00:00Z",
    },
  ],
  total: 1,
};

const DIAGNOSIS_REPORT = {
  project_id: PROJECT_F33_ID,
  category: "BASICA",
  rules_evaluated: 5,
  findings_emitted: 3,
  gaps_created: 1,
  gaps_updated: 2,
  gaps_resolved: 0,
  gap_codes: ["op.acc.6", "mp.info.3", "org.1"],
  no_cloud_data: false,
};

export async function mockCloudConnectorsAdminBase(page: Page) {
  // Layout shell (header + feature-flags) · evita el redirect de
  // ActiveProjectSync al selector cuando el projectId es sintético.
  await mockProjectShell(page, { projectId: PROJECT_F33_ID });

  // Catalog
  await page.route(
    "**/api/v1/cloud-connectors/providers/catalog",
    async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ items: PROVIDERS_CATALOG }),
      });
    },
  );
  await page.route(
    "**/api/v1/cloud-connectors/supported-measures",
    async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          measures: ["op.acc.6", "mp.info.3", "org.1", "op.exp.8"],
        }),
      });
    },
  );

  // Connectors list (both include_revoked variants)
  await page.route(
    /\/api\/v1\/admin\/projects\/[^/]+\/cloud-connectors\?include_revoked=/,
    async (route) => {
      if (route.request().method() === "GET") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(CONNECTORS_BASE),
        });
      } else {
        await route.continue();
      }
    },
  );

  // Gaps list
  await page.route(
    /\/api\/v1\/admin\/projects\/[^/]+\/cloud-gaps/,
    async (route) => {
      if (route.request().method() === "GET") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(GAPS_BASE),
        });
      } else {
        await route.continue();
      }
    },
  );

  // Resources for connector c1
  await page.route(
    /\/admin\/projects\/[^/]+\/cloud-connectors\/c1111111[^/]+\/resources/,
    async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(RESOURCES_M365),
      });
    },
  );
}

export async function mockRunDiagnosisOk(page: Page) {
  await page.route(
    /\/api\/v1\/admin\/projects\/[^/]+\/cloud-diagnosis\/run/,
    async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(DIAGNOSIS_REPORT),
      });
    },
  );
}

export async function mockResolveGapOk(page: Page) {
  await page.route(
    /\/api\/v1\/admin\/projects\/[^/]+\/cloud-gaps\/[^/]+\/resolve/,
    async (route) => {
      const body = JSON.parse(route.request().postData() ?? "{}");
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          ...GAPS_BASE.items[0],
          resolved_at: "2026-05-21T15:00:00Z",
          resolution_note: body.resolution_note ?? null,
        }),
      });
    },
  );
}

export { CONNECTORS_BASE, DIAGNOSIS_REPORT, GAPS_BASE, RESOURCES_M365 };
