/**
 * Fixtures fase_30 · sub-atom 1.D.F.bis.III v3.11 · cliente indispensable-only.
 *
 * Cubre:
 *  - SIMPLIFY pages core (magerit · dda · policies · files) banners R30 inverso
 *  - REDIRECT /registros → /tasks
 *  - /tasks categorías indispensable 7 buckets
 *  - Sidebar 10 entries agrupado 4 secciones
 *
 * Pattern reuse OPS-045 26ª aplicación · mocks page.route spec-as-code.
 */
import type { Page } from "@playwright/test";

export const PROJECT_F30_ID = "ff301122-3344-5566-7788-99aabbccddff";

const MOCK_CLIENT_PROJECT = {
  id: PROJECT_F30_ID,
  nombre: "Test Cliente Indispensable",
};

const MOCK_MAGERIT_SUMMARY = {
  project_id: PROJECT_F30_ID,
  total_assets: 12,
  total_risks: 18,
  reviewed_count: 0,
  pending_review_count: 12,
  questions_count: 0,
  suggestions_count: 0,
  ready_for_validation_sign: false,
  last_signed_at: null,
  // UI drift: MageritSummaryCard ahora destructura estos campos del summary.
  // Sin assets_by_type, Object.keys(undefined) crashea (error boundary "4
  // errors") → la página nunca pinta el heading. Completamos la forma actual.
  completion_percentage: 0,
  analysis_name: "AR-2026-E2E",
  analysis_status: "completed",
  assets_by_type: { S: 1, D: 1 },
};

const MOCK_MAGERIT_ASSETS = [
  {
    id: "asset-1",
    analysis_id: "ana-1",
    code: "S-001",
    name: "Servicio web corporativo",
    asset_type_code: "S",
    description: null,
    owner: null,
    value_d: 7,
    value_i: 8,
    value_c: 6,
    value_a: 7,
    value_t: 5,
    accumulated_d: 7,
    accumulated_i: 8,
    accumulated_c: 6,
    accumulated_a: 7,
    accumulated_t: 5,
    client_review_status: null,
    client_review_note: null,
    client_reviewed_at: null,
  },
  {
    id: "asset-2",
    analysis_id: "ana-1",
    code: "D-001",
    name: "Base de datos clientes",
    asset_type_code: "D",
    description: null,
    owner: null,
    value_d: 6,
    value_i: 9,
    value_c: 9,
    value_a: 8,
    value_t: 7,
    accumulated_d: 6,
    accumulated_i: 9,
    accumulated_c: 9,
    accumulated_a: 8,
    accumulated_t: 7,
    client_review_status: null,
    client_review_note: null,
    client_reviewed_at: null,
  },
];

const MOCK_DDA_SUMMARY = {
  project_id: PROJECT_F30_ID,
  categoria_objetivo: "MEDIA",
  total_measures: 44,
  reviewed_count: 0,
  pending_review_count: 44,
  questions_count: 0,
  suggestions_count: 0,
  completion_percentage: 0,
  is_frozen: false,
  frozen_at: null,
  last_signed_at: null,
  ready_for_final_sign: false,
};

const MOCK_DDA_MEASURES = [
  {
    id: "dda-entry-1",
    measure_codigo: "org.1",
    measure_nombre: "Política de seguridad",
    measure_familia: "org",
    measure_subfamilia: null,
    measure_descripcion: null,
    requisito_base: null,
    ccn_stic_reference: null,
    categoria_minima: "BASICA",
    tier_required_for: ["BASICA", "MEDIA", "ALTA"],
    dimensiones_aplicables: null,
    aplicabilidad: "aplica",
    justificacion_no_aplica: null,
    estado_implementacion: "implantada",
    observaciones: null,
    aprobado_por: null,
    fecha_aprobacion: null,
    evidence_count: 0,
    evidence_list: [],
    client_review_status: null,
    client_review_note: null,
    client_reviewed_at: null,
  },
];

const MOCK_TASKS_INDISPENSABLE = [
  {
    id: "task-firma-dda",
    project_id: PROJECT_F30_ID,
    template_id: "client_sign_dda",
    phase: "adecuacion",
    title: "Firma DdA · Declaración de Aplicabilidad",
    description: "Tu consultor terminó la DdA · revisa y firma cuando estés conforme.",
    cta_label: "Firmar",
    cta_url: "/client-portal/dda",
    expected_evidence_type: null,
    expected_evidence_count: 0,
    priority: 1,
    status: "pending",
    due_date: null,
    started_at: null,
    completed_at: null,
    blocked_reason: null,
  },
  {
    id: "task-upload-dni",
    project_id: PROJECT_F30_ID,
    template_id: "client_upload_dni",
    phase: "diagnostico",
    title: "Sube el DNI del representante legal",
    description: "Marcos lo necesita para el alta del Comité de Seguridad.",
    cta_label: "Subir",
    cta_url: "/client-portal/files",
    expected_evidence_type: "dni_representante",
    expected_evidence_count: 1,
    priority: 2,
    status: "pending",
    due_date: null,
    started_at: null,
    completed_at: null,
    blocked_reason: null,
  },
  {
    id: "task-lms-g1",
    project_id: PROJECT_F30_ID,
    template_id: "client_lms_g1_attendance",
    phase: "adecuacion",
    title: "Formación G1 empleados · LMS",
    description: "Coordina la asistencia ≥80% de tu equipo.",
    cta_label: "Ver cursos",
    cta_url: "/client-portal/onboarding",
    expected_evidence_type: "lms_attendance",
    expected_evidence_count: 25,
    priority: 3,
    status: "in_progress",
    due_date: null,
    started_at: "2026-05-15T10:00:00Z",
    completed_at: null,
    blocked_reason: null,
  },
  {
    id: "task-implement-mp1",
    project_id: PROJECT_F30_ID,
    template_id: "client_implement_medida_mp_per_1",
    phase: "adecuacion",
    title: "Implementar medida mp.per.1 · Formación obligatoria",
    description: "Marca como hecho cuando termines la formación inicial.",
    cta_label: "Marcar hecho",
    cta_url: null,
    expected_evidence_type: null,
    expected_evidence_count: 0,
    priority: 4,
    status: "pending",
    due_date: null,
    started_at: null,
    completed_at: null,
    blocked_reason: null,
  },
  {
    id: "task-pentest-auth",
    project_id: PROJECT_F30_ID,
    template_id: "client_pentest_authorize_window",
    phase: "verificacion",
    title: "Autoriza la ventana de pentest",
    description: "Revisa scope + ventana + plan + IR + compromisos · firma OTP.",
    cta_label: "Autorizar",
    cta_url: "/client-portal/pentest-authorization",
    expected_evidence_type: null,
    expected_evidence_count: 0,
    priority: 5,
    status: "pending",
    due_date: null,
    started_at: null,
    completed_at: null,
    blocked_reason: null,
  },
];

export async function mockClienteIndispensable(page: Page) {
  await page.route("**/api/v1/client-portal/project", async (route) => {
    await route.fulfill({ status: 200, json: MOCK_CLIENT_PROJECT });
  });
  await page.route(
    new RegExp("/api/v1/portal/magerit/projects/[^/]+/summary"),
    async (route) => {
      await route.fulfill({ status: 200, json: MOCK_MAGERIT_SUMMARY });
    },
  );
  await page.route(
    new RegExp("/api/v1/portal/magerit/projects/[^/]+/assets"),
    async (route) => {
      await route.fulfill({ status: 200, json: MOCK_MAGERIT_ASSETS });
    },
  );
  await page.route(
    new RegExp("/api/v1/portal/magerit/projects/[^/]+/risks"),
    async (route) => {
      await route.fulfill({ status: 200, json: [] });
    },
  );
  await page.route(
    new RegExp("/api/v1/portal/dda/projects/[^/]+/measures"),
    async (route) => {
      await route.fulfill({ status: 200, json: MOCK_DDA_MEASURES });
    },
  );
  await page.route(
    new RegExp("/api/v1/portal/dda/projects/[^/]+$"),
    async (route) => {
      await route.fulfill({ status: 200, json: MOCK_DDA_SUMMARY });
    },
  );
  await page.route(
    new RegExp("/api/v1/client-portal/tasks"),
    async (route) => {
      if (route.request().method() === "GET") {
        await route.fulfill({ status: 200, json: MOCK_TASKS_INDISPENSABLE });
      } else {
        await route.continue();
      }
    },
  );
}
