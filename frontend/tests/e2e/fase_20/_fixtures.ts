/**
 * Fixtures compartidos · fase_20 sub-atom 1.D.A v3.10 tests E2E A21
 * Detector Discrepancias.
 *
 * Cubre sub-atom 1.D.A v3.10 ENS-only (NO cross-marco · sostiene R1):
 *   - 1.D.A.A backend service determinista (5 detectores ENS-only)
 *   - 1.D.A.B ProjectTabs Discrepancias entry + critical badge
 *   - Admin entry page /admin/projects/[id]/discrepancies
 *
 * Pattern reuse · OPS-045 sostenido (13ª aplicación consecutiva): mocks
 * page.route spec-as-code ARTIFACT · execution diferida CI full backend
 * (paridad fase_17/18/19).
 *
 * Decisión arquitectural: A21 production-grade existing reveal audit-first.
 * NO LLM promote (sostiene R1 inviolable motores deterministas) · POLISH
 * detectores diferidos ENS-only + admin tab.
 */
import type { Page } from "@playwright/test";

export const PROJECT_A_ID = "eeeeffff-1111-2222-3333-444444444444";
export const CLIENT_A_ID = "eeeeffff-aaaa-bbbb-cccc-555555555555";

const SCAN_RUN_ID = "11111111-2222-3333-4444-aaaaaaaaaaaa";
const DISC_CRITICAL_1 = "22222222-3333-4444-5555-aaaaaaaaaa01";
const DISC_HIGH_1 = "22222222-3333-4444-5555-aaaaaaaaaa02";
const DISC_MEDIUM_1 = "22222222-3333-4444-5555-aaaaaaaaaa03";
const DISC_LOW_1 = "22222222-3333-4444-5555-aaaaaaaaaa04";

// ============================================================
// Mock scan run + discrepancies (post-1.D.A.A 5 detectores ENS-only)
// ============================================================

export const MOCK_SCAN_RUN_COMPLETED = {
  id: SCAN_RUN_ID,
  project_id: PROJECT_A_ID,
  run_status: "completed",
  motors_scanned: ["m02", "m03", "m04", "m06", "m07", "m19"],
  discrepancies_found: 4,
  started_at: "2026-05-20T10:00:00Z",
  completed_at: "2026-05-20T10:00:05Z",
  error_message: null,
};

export const MOCK_DISCREPANCY_CRITICAL = {
  id: DISC_CRITICAL_1,
  scan_run_id: SCAN_RUN_ID,
  project_id: PROJECT_A_ID,
  discrepancy_type: "findings_vs_remediation",
  severity: "critical" as const,
  motor_a: "m04",
  motor_b: "m19",
  description:
    "3 finding(s) crítico(s) abierto(s) sin remediation_plan asignado. " +
    "Auditor ENAC marca NC severa por gestión de no conformidades sin tracking.",
  evidence_a: {
    findings_critical_unplanned_count: 3,
    severidad_filter: "critica",
  },
  evidence_b: { remediation_plans_count: 0 },
  resolution_status: "open" as const,
  resolution_notes: null,
  resolved_at: null,
  created_at: "2026-05-20T10:00:03Z",
};

export const MOCK_DISCREPANCY_HIGH = {
  id: DISC_HIGH_1,
  scan_run_id: SCAN_RUN_ID,
  project_id: PROJECT_A_ID,
  discrepancy_type: "dda_vs_documents",
  severity: "high" as const,
  motor_a: "m03",
  motor_b: "m06",
  description:
    "12 medida(s) DdA aplicable(s) · 0 documentos política/procedimiento " +
    "approved. Cobertura documental ENS ausente · NC severa auditoría ENAC.",
  evidence_a: { dda_aplicable_count: 12 },
  evidence_b: {
    documents_approved_count: 0,
    clasificacion_filter: ["politica", "procedimiento"],
  },
  resolution_status: "open" as const,
  resolution_notes: null,
  resolved_at: null,
  created_at: "2026-05-20T10:00:02Z",
};

export const MOCK_DISCREPANCY_MEDIUM = {
  id: DISC_MEDIUM_1,
  scan_run_id: SCAN_RUN_ID,
  project_id: PROJECT_A_ID,
  discrepancy_type: "dda_vs_evidence",
  severity: "medium" as const,
  motor_a: "m03",
  motor_b: "m07",
  description: "Cobertura insuficiente · 24 medidas vs 4 evidencias (6x ratio).",
  evidence_a: { dda_aplicable_count: 24 },
  evidence_b: { evidence_vigente_count: 4 },
  resolution_status: "acknowledged" as const,
  resolution_notes: "Marcos revisará próxima reunión",
  resolved_at: null,
  created_at: "2026-05-20T10:00:01Z",
};

export const MOCK_DISCREPANCY_LOW_RESOLVED = {
  id: DISC_LOW_1,
  scan_run_id: SCAN_RUN_ID,
  project_id: PROJECT_A_ID,
  discrepancy_type: "magerit_vs_dda",
  severity: "low" as const,
  motor_a: "m02",
  motor_b: "m03",
  description: "Discrepancia previa resuelta · histórico audit.",
  evidence_a: {},
  evidence_b: {},
  resolution_status: "resolved" as const,
  resolution_notes: "Resuelta tras añadir medidas DdA",
  resolved_at: "2026-05-19T15:00:00Z",
  created_at: "2026-05-19T10:00:00Z",
};

export const MOCK_DISCREPANCIES_ALL = [
  MOCK_DISCREPANCY_CRITICAL,
  MOCK_DISCREPANCY_HIGH,
  MOCK_DISCREPANCY_MEDIUM,
  MOCK_DISCREPANCY_LOW_RESOLVED,
];

export const MOCK_DISCREPANCIES_CRITICAL_OPEN = [MOCK_DISCREPANCY_CRITICAL];

// ============================================================
// Mock route helpers
// ============================================================

/**
 * Mock A21 admin endpoints baseline · scan + list + resolve.
 *
 * Endpoints:
 *   POST   /api/v1/projects/{id}/a21/scan
 *   GET    /api/v1/projects/{id}/a21/scans?limit=5
 *   GET    /api/v1/projects/{id}/a21/discrepancies
 *   GET    /api/v1/projects/{id}/a21/discrepancies?severity=critical&resolution_status=open
 *   PATCH  /api/v1/projects/{id}/a21/discrepancies/{did}/resolve
 *
 * Sostiene R23 + R31 + R24 admin-only project-scoped.
 */
export async function mockAdminA21Base(page: Page) {
  // Project features context (ProjectFeaturesContext usado en ProjectTabs)
  await page.route(
    `**/api/v1/projects/${PROJECT_A_ID}/feature-flags`,
    async (route) => {
      await route.fulfill({
        status: 200,
        json: {
          project_id: PROJECT_A_ID,
          categoria: "MEDIA",
          archetype: "saas_tech",
          features: {},
        },
      });
    },
  );

  // List scans
  await page.route(
    `**/api/v1/projects/${PROJECT_A_ID}/a21/scans*`,
    async (route) => {
      await route.fulfill({
        status: 200,
        json: [MOCK_SCAN_RUN_COMPLETED],
      });
    },
  );

  // List discrepancies (with optional filter params)
  await page.route(
    `**/api/v1/projects/${PROJECT_A_ID}/a21/discrepancies*`,
    async (route) => {
      const url = new URL(route.request().url());
      const severity = url.searchParams.get("severity");
      const status = url.searchParams.get("resolution_status");

      let result = MOCK_DISCREPANCIES_ALL;
      if (severity) {
        result = result.filter((d) => d.severity === severity);
      }
      if (status) {
        result = result.filter((d) => d.resolution_status === status);
      }
      await route.fulfill({ status: 200, json: result });
    },
  );

  // Trigger scan
  await page.route(
    `**/api/v1/projects/${PROJECT_A_ID}/a21/scan`,
    async (route) => {
      if (route.request().method() === "POST") {
        await route.fulfill({
          status: 200,
          json: MOCK_SCAN_RUN_COMPLETED,
        });
      } else {
        await route.fallback();
      }
    },
  );
}
