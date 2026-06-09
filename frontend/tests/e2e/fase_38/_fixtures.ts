/**
 * Fixtures compartidos · fase_38 Bloque 3+5 v3.12 · Cliente Cloud Remediations UI.
 *
 * Cubre:
 *  - List remediations 3 secciones (pendientes/en progreso/resueltas)
 *  - Empty state friendly cuando NO remediations
 *  - Approval modal happy path approve + reject
 *  - Severity + status badges R29 friendly
 *
 * Pattern reuse · OPS-045 51a aplicacion · spec-as-code ARTIFACT execution
 * diferida CI infra full per OPS-050.
 */
import type { Page } from "@playwright/test";

export const PROJECT_B35_ID = "b35aaaaa-bbbb-cccc-dddd-eeff00112233";

// ============================================================
// Cloud Remediations cliente mocks
// ============================================================

export const MOCK_REMEDIATIONS_EMPTY = {
  project_id: PROJECT_B35_ID,
  count: 0,
  gaps: [],
};

export const MOCK_REMEDIATIONS_WITH_3_SECTIONS = {
  project_id: PROJECT_B35_ID,
  count: 4,
  gaps: [
    // Pendiente de decisión cliente
    {
      id: "gap00001-aaaa-bbbb-cccc-000000000001",
      project_id: PROJECT_B35_ID,
      ens_measure_code: "op.acc.6",
      severity: "critical",
      title: "Activar segundo factor para todos los usuarios",
      explanation_es:
        "Hemos detectado 12 personas en tu Microsoft 365 sin segundo factor (MFA). Sin esto, basta con una contraseña filtrada para entrar en tu correo.",
      suggested_action:
        "Marcos activará la política de MFA obligatoria para todos los usuarios. Tarda 5 minutos.",
      approval_status: "proposed_to_cliente",
      proposed_to_cliente_at: "2026-05-24T10:00:00Z",
      cliente_approval_at: null,
      resolved_at: null,
      evidence_link_id: null,
    },
    // En progreso · approved
    {
      id: "gap00002-aaaa-bbbb-cccc-000000000002",
      project_id: PROJECT_B35_ID,
      ens_measure_code: "op.exp.8",
      severity: "high",
      title: "Activar registro de auditoría en Azure",
      explanation_es:
        "Tu Azure no guarda quién hace cambios. Sin esto no podemos demostrar nada en una auditoría.",
      suggested_action: "Marcos activará Azure Activity Log.",
      approval_status: "approved",
      proposed_to_cliente_at: "2026-05-23T09:00:00Z",
      cliente_approval_at: "2026-05-23T11:00:00Z",
      resolved_at: null,
      evidence_link_id: null,
    },
    // Resuelta · executed
    {
      id: "gap00003-aaaa-bbbb-cccc-000000000003",
      project_id: PROJECT_B35_ID,
      ens_measure_code: "mp.s.2",
      severity: "medium",
      title: "Cerrar bucket público en AWS S3",
      explanation_es:
        "Un bucket S3 estaba abierto al mundo. Lo cerramos.",
      suggested_action: "Marcos cerró bucket.",
      approval_status: "executed",
      proposed_to_cliente_at: "2026-05-20T08:00:00Z",
      cliente_approval_at: "2026-05-20T10:00:00Z",
      resolved_at: "2026-05-21T14:00:00Z",
      evidence_link_id: "evi00003-aaaa-bbbb-cccc-000000000003",
    },
    // Resuelta · failed
    {
      id: "gap00004-aaaa-bbbb-cccc-000000000004",
      project_id: PROJECT_B35_ID,
      ens_measure_code: "op.cont.3",
      severity: "low",
      title: "Activar backup automático",
      explanation_es: "Intentamos activar el backup pero falló.",
      suggested_action: "Marcos revisará el problema.",
      approval_status: "failed",
      proposed_to_cliente_at: "2026-05-19T08:00:00Z",
      cliente_approval_at: "2026-05-19T10:00:00Z",
      resolved_at: null,
      evidence_link_id: null,
    },
  ],
};

export const MOCK_APPROVE_SUCCESS = {
  gap_id: "gap00001-aaaa-bbbb-cccc-000000000001",
  approval_status: "approved",
  friendly_message: "¡Gracias! Marcos comenzará a ejecutar pronto.",
};

export const MOCK_REJECT_SUCCESS = {
  gap_id: "gap00001-aaaa-bbbb-cccc-000000000001",
  approval_status: "rejected",
  friendly_message: "Entendido · Marcos lo tendrá en cuenta.",
};

// ============================================================
// Mock helpers
// ============================================================

export async function mockRemediationsEmpty(page: Page) {
  await page.route(
    "**/api/v1/client-portal/cloud-gaps",
    async (route) => {
      if (route.request().method() === "GET") {
        return route.fulfill({ json: MOCK_REMEDIATIONS_EMPTY });
      }
      return route.fallback();
    },
  );
}

export async function mockRemediationsWith3Sections(page: Page) {
  await page.route(
    "**/api/v1/client-portal/cloud-gaps",
    async (route) => {
      if (route.request().method() === "GET") {
        return route.fulfill({
          json: MOCK_REMEDIATIONS_WITH_3_SECTIONS,
        });
      }
      return route.fallback();
    },
  );
}

export async function mockApproveAndReject(page: Page) {
  await page.route(
    "**/api/v1/client-portal/cloud-gaps/*/approve",
    async (route) => route.fulfill({ json: MOCK_APPROVE_SUCCESS }),
  );
  await page.route(
    "**/api/v1/client-portal/cloud-gaps/*/reject",
    async (route) => route.fulfill({ json: MOCK_REJECT_SUCCESS }),
  );
}
