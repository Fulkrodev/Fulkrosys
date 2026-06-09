/**
 * Fixtures compartidos · fase_23 sub-atom 1.D.C v3.11 · Dashboard K.3
 * Planes Acción cross-motor.
 *
 * Cubre Dashboard K.3 cross-motor aggregator (M04 gap + M09 audit + A21
 * discrepancias). Schema response ActionPlansResponse + items con drill-down.
 *
 * Pattern reuse · OPS-045 17ª aplicación consecutiva: mocks page.route
 * spec-as-code ARTIFACT · execution diferida CI full backend.
 */
import type { Page } from "@playwright/test";

// FIX specs UI evolucionada: el UUID hardcodeado viejo nunca se siembra. El
// proyecto fijo E2E sembrado por globalSetup (seed-rich-demo-project) usa el
// UUID determinista 00000000-…-001 (ALTA). Apuntamos ahí para que el layout
// project-scoped resuelva el proyecto real · el endpoint action-plans sigue
// mockeado. Mismo patrón que san_e_v3.
export const PROJECT_EE_ID =
  process.env.E2E_SEED_PROJECT_ID ?? "00000000-0000-0000-0000-000000000001";

// ============================================================
// Mock action plans responses
// ============================================================

export const MOCK_ACTION_PLANS_EMPTY = {
  project_id: PROJECT_EE_ID,
  total_count: 0,
  counts_by_source: {},
  counts_by_severity: {},
  items: [],
};

export const MOCK_ACTION_PLANS_WITH_FINDINGS = {
  project_id: PROJECT_EE_ID,
  total_count: 4,
  counts_by_source: {
    m04_gap: 2,
    a21_discrepancy: 1,
    m09_audit_prep: 1,
  },
  counts_by_severity: {
    critica: 2,
    alta: 2,
  },
  items: [
    {
      id: "aaaa1111-2222-3333-4444-555555555501",
      source: "m04_gap",
      severity: "critica",
      familia: "op",
      medida_afectada: "op.acc.1",
      description:
        "Control accesos privilegiados crítico sin implementar · 0 evidencia",
      responsable: "CISO",
      estado: "abierto",
      fecha_objetivo: "2026-06-15",
      project_id: PROJECT_EE_ID,
      motor_link: `/admin/projects/${PROJECT_EE_ID}/plan`,
    },
    {
      id: "aaaa1111-2222-3333-4444-555555555502",
      source: "a21_discrepancy",
      severity: "critica",
      familia: "cross",
      medida_afectada: null,
      description:
        "3 finding(s) crítico(s) abierto(s) sin remediation_plan asignado",
      responsable: null,
      estado: "abierto",
      fecha_objetivo: null,
      project_id: PROJECT_EE_ID,
      motor_link: `/admin/projects/${PROJECT_EE_ID}/discrepancies`,
    },
    {
      id: "aaaa1111-2222-3333-4444-555555555503",
      source: "m09_audit_prep",
      severity: "alta",
      familia: "mp",
      medida_afectada: "mp.if.2",
      description: "Protección instalaciones · acceso físico sin segregación",
      responsable: null,
      estado: "en_curso",
      fecha_objetivo: "2026-07-01",
      project_id: PROJECT_EE_ID,
      motor_link: `/admin/projects/${PROJECT_EE_ID}/dossier`,
    },
    {
      id: "aaaa1111-2222-3333-4444-555555555504",
      source: "m04_gap",
      severity: "alta",
      familia: "org",
      medida_afectada: "org.3",
      description: "Política de seguridad sin firmar por RSEG",
      responsable: "RSEG",
      estado: "abierto",
      fecha_objetivo: null,
      project_id: PROJECT_EE_ID,
      motor_link: `/admin/projects/${PROJECT_EE_ID}/plan`,
    },
  ],
};

export const MOCK_ACTION_PLANS_ERROR_500 = {
  detail: "Internal server error · action-plans aggregator",
};

// ============================================================
// Mock route helpers
// ============================================================

export async function mockActionPlansEmpty(page: Page) {
  await page.route(
    `**/api/v1/projects/${PROJECT_EE_ID}/action-plans*`,
    async (route) => {
      await route.fulfill({ status: 200, json: MOCK_ACTION_PLANS_EMPTY });
    },
  );
}

export async function mockActionPlansWithFindings(page: Page) {
  await page.route(
    `**/api/v1/projects/${PROJECT_EE_ID}/action-plans*`,
    async (route) => {
      await route.fulfill({
        status: 200,
        json: MOCK_ACTION_PLANS_WITH_FINDINGS,
      });
    },
  );
}

export async function mockActionPlansError(page: Page) {
  await page.route(
    `**/api/v1/projects/${PROJECT_EE_ID}/action-plans*`,
    async (route) => {
      await route.fulfill({
        status: 500,
        json: MOCK_ACTION_PLANS_ERROR_500,
      });
    },
  );
}
