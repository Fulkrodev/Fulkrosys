/**
 * Sesión 3B-2B.10 Phase 10.4 · SimulacroPreEnacTab embedded in AuditDryRunDashboard.
 *
 * Verifica:
 *   - Tabs render: "Dry-Run M10+A11" + "Simulacro Pre-ENAC" both visible
 *   - Click tab Simulacro: button "Ejecutar simulacro Pre-ENAC" visible
 *   - Click ejecutar: spinner + report render con métricas + integrity OK
 *   - Last report (404 → empty state): friendly "Sin simulacros previos"
 */
import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "./_helpers/auth-real";

const PROJECT_ID = "aaaa1111-2222-3333-4444-555555555555";

const SUMMARY_EMPTY = {
  last_executed_at: null,
  overall_readiness_score: 0,
  gaps_detected: 0,
  critical_gaps: 0,
  history: [],
};

const SIMULACRO_REPORT_PAYLOAD = {
  project_id: PROJECT_ID,
  executed_at: "2026-05-27T15:00:00Z",
  overall_readiness_score: 72,
  total_gaps: 14,
  critical_gaps: 3,
  high_gaps: 5,
  coverage_pct: 65.2,
  current_phase: "dossier",
  integrity_ok: true,
  integrity_first_bad_seq: null,
  corrective_loops_opened: 3,
  pdf_sha256: "a".repeat(64),
  signature_hex: "b".repeat(128),
  signed_at: "2026-05-27T15:01:30Z",
  pdf_size_bytes: 12345,
  loops_metadata: [
    { loop_id: "11111111-1111-1111-1111-111111111111", gap_id: "op.acc.6", severity: "critical" },
    { loop_id: "22222222-2222-2222-2222-222222222222", gap_id: "mp.s.2", severity: "critical" },
    { loop_id: "33333333-3333-3333-3333-333333333333", gap_id: "op.exp.8", severity: "high" },
  ],
};

// El layout project-scoped llama /feature-flags + /header al montar
// ProjectFeaturesProvider/Header/Tabs. La spec original no las stubeaba.
// Stubeamos para render determinista del AuditDryRunDashboard (tabs).
const LAYOUT_FEATURE_FLAGS = {
  categoria: "MEDIA",
  archetype: null,
  employee_count: null,
  features: {},
};

const LAYOUT_HEADER = {
  project: {
    id: "stub",
    nombre: "Proyecto E2E MB-15 simulacro",
    fase: "conformidad",
    categoria_objetivo: "MEDIA",
    lifecycle_state: "ACTIVE",
    fecha_kickoff: null,
    fecha_objetivo_certificacion: null,
    certified_at: null,
  },
  cliente: {
    id: "client-stub",
    nombre: "Cliente E2E",
    cif: "B12345678",
    sector: null,
    provincia: null,
  },
  rseg_contact: null,
  ciso_contact: null,
  conformity: {
    route_status: null,
    route_type: null,
    expiration_date: null,
    submissions_count: 0,
    renewals_count: 0,
    material_changes_count: 0,
  },
};

test.describe("Audit-Prep Dashboard · tabs Dry-Run + Simulacro Pre-ENAC", () => {
  test.beforeEach(async ({ page }) => {
    await page.route(`**/api/v1/projects/*/feature-flags`, (route) =>
      route.fulfill({ status: 200, json: LAYOUT_FEATURE_FLAGS }),
    );
    await page.route(`**/api/v1/projects/*/header`, (route) =>
      route.fulfill({ status: 200, json: LAYOUT_HEADER }),
    );
  });

  test("tabs render · ambas pestañas visibles", async ({ page, context }) => {
    await loginAsMarcos(context);
    await page.route(
      `**/api/v1/projects/${PROJECT_ID}/audit-dry-run/summary`,
      (route) => route.fulfill({ status: 200, json: SUMMARY_EMPTY }),
    );
    await page.route(
      `**/api/v1/admin/projects/${PROJECT_ID}/simulacro-pre-enac/last-report`,
      (route) => route.fulfill({ status: 404, json: { detail: "No simulacro" } }),
    );

    await page.goto(`/admin/projects/${PROJECT_ID}/audit-dry-run`);

    await expect(page.getByTestId("audit-prep-tab-dry-run")).toBeVisible();
    await expect(page.getByTestId("audit-prep-tab-simulacro")).toBeVisible();
  });

  test("click tab Simulacro · button ejecutar visible · empty state", async ({
    page,
    context,
  }) => {
    await loginAsMarcos(context);
    await page.route(
      `**/api/v1/projects/${PROJECT_ID}/audit-dry-run/summary`,
      (route) => route.fulfill({ status: 200, json: SUMMARY_EMPTY }),
    );
    await page.route(
      `**/api/v1/admin/projects/${PROJECT_ID}/simulacro-pre-enac/last-report`,
      (route) => route.fulfill({ status: 404, json: { detail: "No simulacro" } }),
    );

    await page.goto(`/admin/projects/${PROJECT_ID}/audit-dry-run`);
    await page.getByTestId("audit-prep-tab-simulacro").click();

    await expect(page.getByTestId("simulacro-pre-enac-execute-btn")).toBeVisible();
    await expect(page.getByText(/Sin simulacros previos/i)).toBeVisible();
  });

  test("ejecutar simulacro · spinner + report render integrity OK", async ({
    page,
    context,
  }) => {
    await loginAsMarcos(context);
    await page.route(
      `**/api/v1/projects/${PROJECT_ID}/audit-dry-run/summary`,
      (route) => route.fulfill({ status: 200, json: SUMMARY_EMPTY }),
    );
    await page.route(
      `**/api/v1/admin/projects/${PROJECT_ID}/simulacro-pre-enac/last-report`,
      (route) => route.fulfill({ status: 404, json: { detail: "No simulacro" } }),
    );

    let executeRequestSeen = false;
    await page.route(
      `**/api/v1/admin/projects/${PROJECT_ID}/simulacro-pre-enac/execute`,
      async (route) => {
        executeRequestSeen = true;
        await new Promise((r) => setTimeout(r, 600));
        await route.fulfill({ status: 200, json: SIMULACRO_REPORT_PAYLOAD });
      },
    );

    await page.goto(`/admin/projects/${PROJECT_ID}/audit-dry-run`);
    await page.getByTestId("audit-prep-tab-simulacro").click();
    await page.getByTestId("simulacro-pre-enac-execute-btn").click();

    await expect(page.getByText(/Ejecutando simulacro Pre-ENAC/i)).toBeVisible();

    await expect(page.getByTestId("simulacro-report-display")).toBeVisible({
      timeout: 10_000,
    });
    await expect(page.getByText(/72% madurez/i)).toBeVisible();
    await expect(page.getByText(/audit_log integridad: OK/i)).toBeVisible();
    await expect(page.getByText(/op.acc.6/)).toBeVisible();
    await expect(page.getByText(/mp.s.2/)).toBeVisible();
    await expect(page.getByText(/Bucles correctivos abiertos: 3/)).toBeVisible();

    expect(executeRequestSeen).toBe(true);
  });
});
