/**
 * Fixtures fase_35 · Cloud Integrations K-full admin UI (sub-atom 1.D.J v3.12).
 *
 * Cubre 5 motores cloud integration con 3 helpers FULL (M22 · M02 · M27):
 *  - M22 Discovery consolidated · /discovery-consolidated endpoint
 *  - M02 MAGERIT enriched inventory · /magerit-enriched-inventory endpoint
 *  - M27 Conformity cloud score · /conformity-cloud-score endpoint
 *
 * Pattern reuse fase_33 cloud-connectors fixtures.
 */
import type { Page } from "@playwright/test";

import { mockProjectShell } from "../_helpers/project-shell";

export const PROJECT_F35_ID = "f35f35f3-5f35-4f35-bf35-f35f35f35f35";
export const ANALYSIS_F35_ID = "a35a35a3-5a35-4a35-ba35-a35a35a35a35";

// ============================================================
// M22 Discovery consolidated fixtures
// ============================================================

const CONSOLIDATED_BASE = {
  project_id: PROJECT_F35_ID,
  generated_at: "2026-05-22T10:00:00Z",
  counts: {
    total: 4,
    manual_only: 1,
    cloud_only: 1,
    both: 2,
  },
  assets: [
    {
      manual_asset_id: "ma111111-1111-1111-1111-111111111111",
      cloud_resource_id: null,
      name: "Servidor backup local",
      resource_type_normalized: "server",
      provenance: "manual",
      provider: null,
      criticidad: "ALTA",
    },
    {
      manual_asset_id: null,
      cloud_resource_id: "cr222222-2222-2222-2222-222222222222",
      name: "EC2 i-0a1b2c3d4e5f6",
      resource_type_normalized: "server",
      provenance: "cloud",
      provider: "aws",
      criticidad: null,
    },
    {
      manual_asset_id: "ma333333-3333-3333-3333-333333333333",
      cloud_resource_id: "cr333333-3333-3333-3333-333333333333",
      name: "Servidor de aplicaciones",
      resource_type_normalized: "server",
      provenance: "both",
      provider: "microsoft_365",
      criticidad: "MEDIA",
    },
    {
      manual_asset_id: "ma444444-4444-4444-4444-444444444444",
      cloud_resource_id: "cr444444-4444-4444-4444-444444444444",
      name: "Base de datos clientes",
      resource_type_normalized: "database",
      provenance: "both",
      provider: "aws",
      criticidad: "ALTA",
    },
  ],
};

const CONSOLIDATED_EMPTY = {
  project_id: PROJECT_F35_ID,
  generated_at: "2026-05-22T10:00:00Z",
  counts: { total: 0, manual_only: 0, cloud_only: 0, both: 0 },
  assets: [],
};

const CONSOLIDATED_MANUAL_ONLY = {
  project_id: PROJECT_F35_ID,
  generated_at: "2026-05-22T10:00:00Z",
  counts: { total: 1, manual_only: 1, cloud_only: 0, both: 0 },
  assets: [
    {
      manual_asset_id: "ma555555-5555-5555-5555-555555555555",
      cloud_resource_id: null,
      name: "Servidor backup local",
      resource_type_normalized: "server",
      provenance: "manual",
      provider: null,
      criticidad: "MEDIA",
    },
  ],
};

// ============================================================
// M02 MAGERIT enriched inventory fixtures
// ============================================================

const MAGERIT_ENRICHED_BASE = {
  project_id: PROJECT_F35_ID,
  analysis_id: ANALYSIS_F35_ID,
  generated_at: "2026-05-22T10:00:00Z",
  counts: {
    total: 3,
    cloud_verified: 2,
    manual_only: 1,
  },
  assets: [
    {
      asset_id: "ast11111-1111-1111-1111-111111111111",
      asset_code: "A-001",
      asset_name: "Servidor de aplicaciones",
      cloud_verified: true,
      cloud_provider: "microsoft_365",
      cloud_detected_at: "2026-05-22T09:00:00Z",
    },
    {
      asset_id: "ast22222-2222-2222-2222-222222222222",
      asset_code: "A-002",
      asset_name: "Base de datos clientes",
      cloud_verified: true,
      cloud_provider: "aws",
      cloud_detected_at: "2026-05-22T09:00:00Z",
    },
    {
      asset_id: "ast33333-3333-3333-3333-333333333333",
      asset_code: "A-003",
      asset_name: "Servidor backup local",
      cloud_verified: false,
      cloud_provider: null,
      cloud_detected_at: null,
    },
  ],
};

// ============================================================
// M27 Conformity cloud score fixtures
// ============================================================

const CONFORMITY_SCORE_BASE = {
  project_id: PROJECT_F35_ID,
  category: "MEDIA",
  measures_cloud_verified: 5,
  measures_total_aplicable: 8,
  score_percentage: 62.5,
  per_familia_breakdown: [
    { familia: "op.acc", verified: 2, total: 3 },
    { familia: "op.exp", verified: 1, total: 2 },
    { familia: "mp.s", verified: 1, total: 1 },
    { familia: "mp.info", verified: 1, total: 1 },
    { familia: "op.cont", verified: 0, total: 1 },
    { familia: "org", verified: 0, total: 0 },
  ],
};

const CONFORMITY_SCORE_EMPTY = {
  project_id: PROJECT_F35_ID,
  category: "MEDIA",
  measures_cloud_verified: 0,
  measures_total_aplicable: 8,
  score_percentage: 0,
  per_familia_breakdown: [],
};

// ============================================================
// Mock helpers · M22 consolidated
// ============================================================

export async function mockM22ConsolidatedBase(page: Page) {
  await mockProjectShell(page, { projectId: PROJECT_F35_ID });
  await page.route(
    /\/api\/v1\/admin\/projects\/[^/]+\/cloud-integrations\/discovery-consolidated/,
    async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(CONSOLIDATED_BASE),
      });
    },
  );
}

export async function mockM22ConsolidatedEmpty(page: Page) {
  await mockProjectShell(page, { projectId: PROJECT_F35_ID });
  await page.route(
    /\/api\/v1\/admin\/projects\/[^/]+\/cloud-integrations\/discovery-consolidated/,
    async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(CONSOLIDATED_EMPTY),
      });
    },
  );
}

export async function mockM22ConsolidatedManualOnly(page: Page) {
  await mockProjectShell(page, { projectId: PROJECT_F35_ID });
  await page.route(
    /\/api\/v1\/admin\/projects\/[^/]+\/cloud-integrations\/discovery-consolidated/,
    async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(CONSOLIDATED_MANUAL_ONLY),
      });
    },
  );
}

// ============================================================
// Mock helpers · M02 MAGERIT enriched
// ============================================================

export async function mockM02EnrichedBase(page: Page) {
  await mockProjectShell(page, { projectId: PROJECT_F35_ID });
  await page.route(
    /\/api\/v1\/admin\/projects\/[^/]+\/cloud-integrations\/magerit-enriched-inventory/,
    async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(MAGERIT_ENRICHED_BASE),
      });
    },
  );
}

// ============================================================
// Mock helpers · M27 Conformity score
// ============================================================

export async function mockM27ScoreBase(page: Page) {
  await mockProjectShell(page, { projectId: PROJECT_F35_ID });
  await page.route(
    /\/api\/v1\/admin\/projects\/[^/]+\/cloud-integrations\/conformity-cloud-score/,
    async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(CONFORMITY_SCORE_BASE),
      });
    },
  );
}

export async function mockM27ScoreEmpty(page: Page) {
  await mockProjectShell(page, { projectId: PROJECT_F35_ID });
  await page.route(
    /\/api\/v1\/admin\/projects\/[^/]+\/cloud-integrations\/conformity-cloud-score/,
    async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(CONFORMITY_SCORE_EMPTY),
      });
    },
  );
}

export {
  CONSOLIDATED_BASE,
  CONSOLIDATED_EMPTY,
  CONSOLIDATED_MANUAL_ONLY,
  MAGERIT_ENRICHED_BASE,
  CONFORMITY_SCORE_BASE,
  CONFORMITY_SCORE_EMPTY,
};
