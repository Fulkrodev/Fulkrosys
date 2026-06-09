/**
 * Fixtures compartidos · fase_17 sub-atom 1.C.D.E v3.8 tests E2E.
 *
 * Mocks contra backend m_workflow_engine endpoints (1.C.D.A + 1.C.D.B + 1.C.D.D)
 * + copilot stubs (1.C.D.B.3 admin + 1.C.D.C.3 cliente).
 *
 * Pattern reuse · OPS-045 sostenido · existing workflow.spec.ts conventions.
 */
import type { Page } from "@playwright/test";

export const PROJECT_A_ID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee";

// ============================================================
// Workflow Command Center · admin multi-cliente
// ============================================================

export const MOCK_COMMAND_CENTER_RESPONSE = {
  urgentes_hoy: [
    {
      project_id: PROJECT_A_ID,
      project_nombre: "Fintech Plus SL",
      categoria: "MEDIA",
      archetype: "proveedor_financiero",
      current_phase: "adecuacion",
      current_step_title: "Formación G1 empleados",
      current_step_urgency: 85,
      progress_pct: 58,
      progress_completed: 7,
      progress_total: 12,
    },
  ],
  esta_semana: [
    {
      project_id: "bbbbbbbb-cccc-dddd-eeee-ffffffffffff",
      project_nombre: "ConsultoríaTIC Madrid SL",
      categoria: "BASICA",
      archetype: "saas_only",
      current_phase: "diagnostico",
      current_step_title: "DICAT categorización",
      current_step_urgency: 60,
      progress_pct: 40,
      progress_completed: 4,
      progress_total: 10,
    },
  ],
  en_marcha: [],
  proximos_30d: [],
};

// ============================================================
// Per-cliente cronológica enriched (1.C.D.B.2)
// ============================================================

export const MOCK_ENRICHED_STEP_AHORA = {
  template_id: "ENR_IM_03_FORMACION_EMPLEADOS",
  phase: "adecuacion",
  order_within_phase: 3,
  title: "Formación G1 empleados (todos)",
  description_detailed_es:
    "Todos los empleados (25 personas) deben completar un curso online " +
    "de 1 hora sobre seguridad básica ENS. Coordina con RRHH · usa la " +
    "plantilla E-501 para el curso y E-502 para el registro de asistencia.",
  rationale_es:
    "Es obligatorio para certificación ENS Anexo II mp.per.* (formación) · " +
    "sin > 80% asistencia G1 el auditor ENAC marca no conformidad.",
  cta_label: "Subir evidencias asistencia",
  cta_url: "/client-portal/evidencias",
  priority: 1,
  estimated_days: 14,
  deliverable_codes: ["E-500", "E-501", "E-502"],
  prerequisite_template_ids: ["ENR_IM_01_DICAT", "ENR_IM_02_DDA"],
  actors: ["CISO", "RRHH_responsable", "ComitéSeguridad"],
  completion_criteria_detailed: [
    "Plan formación E-500 firmado por CISO",
    "Curso G1 entregado · ≥80% asistencia 25 empleados",
    "Registro asistencia E-502 subido + verificado",
  ],
  adaptation_notes_es:
    "Para fintech 25 empleados: 3 sesiones de 1h en semana laboral · " +
    "DPO debe validar materiales con énfasis DORA.",
  tooltips_ens: {
    "mp.per.1": "Formación obligatoria empleados ENS Anexo II",
    "mp.per.2": "Mantenimiento competencias",
  },
  is_enriched: true,
  variant_extra_focus:
    "Sector fintech: añadir módulo específico DORA art.5 marco gobernanza ICT.",
  variant_reference_norms: ["DORA_art_5", "DORA_art_13"],
  task_id: null,
  status: "pending",
  due_date_iso: null,
  started_at_iso: null,
  completed_at_iso: null,
  blocked_reason: null,
  urgency_score: 85,
};

const MOCK_ENRICHED_STEP_COMPLETED = {
  ...MOCK_ENRICHED_STEP_AHORA,
  template_id: "ENR_IM_01_DICAT",
  title: "DICAT categorización inicial",
  status: "completed",
  completed_at_iso: "2026-05-01T10:00:00Z",
  urgency_score: 0,
  deliverable_codes: ["E-012"],
};

const MOCK_ENRICHED_STEP_PROXIMO = {
  ...MOCK_ENRICHED_STEP_AHORA,
  template_id: "ENR_IM_04_REGISTROS_VIVOS",
  title: "Arrancar registros vivos operativos",
  status: "pending",
  urgency_score: 50,
  deliverable_codes: ["E-300", "E-303"],
};

export const MOCK_CRONOLOGICA_RESPONSE = {
  project_id: PROJECT_A_ID,
  project_nombre: "Fintech Plus SL",
  dims: {
    categoria_objetivo: "MEDIA",
    archetype: "proveedor_financiero",
    fase: "adecuacion",
    tamano_empleados: "pequeno",
    madurez_ens_actual: "L1",
    aplica_dora: "entidad_financiera",
    horas_cliente_semana: "5_15h",
  },
  current_phase: "adecuacion",
  progress: {
    global_pct: 58,
    global_completed: 7,
    global_total: 12,
    per_phase: {
      diagnostico: { completed: 3, total: 3, pct: 100 },
      adecuacion: { completed: 4, total: 9, pct: 44 },
    },
  },
  completed: [MOCK_ENRICHED_STEP_COMPLETED],
  ahora: MOCK_ENRICHED_STEP_AHORA,
  proximos_7d: [MOCK_ENRICHED_STEP_PROXIMO],
  proximos_30d: [],
};

// ============================================================
// Workflow Guide cliente (1.C.D.C subset friendly)
// ============================================================

export const MOCK_WORKFLOW_GUIDE_CLIENT = {
  project_id: PROJECT_A_ID,
  categoria: "MEDIA",
  archetype: "proveedor_financiero",
  fase: "adecuacion",
  progress: MOCK_CRONOLOGICA_RESPONSE.progress,
  current_step: MOCK_ENRICHED_STEP_AHORA,
  completed: [MOCK_ENRICHED_STEP_COMPLETED],
  proximos: [MOCK_ENRICHED_STEP_PROXIMO],
};

// ============================================================
// Deliverables (1.C.D.D)
// ============================================================

export const MOCK_DELIVERABLES_AVAILABLE = {
  project_id: PROJECT_A_ID,
  template_id: "ENR_IM_03_FORMACION_EMPLEADOS",
  template_title: "Formación G1 empleados",
  deliverable_codes: ["E-500", "E-501", "E-502"],
  deliverables: [
    {
      code: "E-500",
      status: "available",
      evidence_id: "evid-aaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
      fichero_nombre_original: "PlanFormacion_FintechPlus.docx",
      fichero_mime_type:
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      fichero_tamano_bytes: 25600,
      hash_sha256: "a".repeat(64),
      fecha_evidencia: "2026-05-10",
      fecha_caducidad: null,
      vigente: true,
    },
    {
      code: "E-501",
      status: "missing",
      evidence_id: null,
      fichero_nombre_original: null,
      fichero_mime_type: null,
      fichero_tamano_bytes: null,
      hash_sha256: null,
      fecha_evidencia: null,
      fecha_caducidad: null,
      vigente: null,
    },
    {
      code: "E-502",
      status: "needs_regen",
      evidence_id: "evid-bbbb-cccc-dddd-eeee-ffffffffffff",
      fichero_nombre_original: "Asistencia_G1_vieja.pdf",
      fichero_mime_type: "application/pdf",
      fichero_tamano_bytes: 12800,
      hash_sha256: "b".repeat(64),
      fecha_evidencia: "2025-12-01",
      fecha_caducidad: "2026-03-01",
      vigente: false,
    },
  ],
  counts: { available: 1, needs_regen: 1, missing: 1 },
};

// ============================================================
// Project metadata (header / ProjectTabs)
// ============================================================

export const MOCK_PROJECT_INFO = {
  id: PROJECT_A_ID,
  nombre: "Fintech Plus SL",
  client_id: "client-fintech-plus",
};

export const MOCK_CLIENT_PORTAL_PROJECT = {
  id: PROJECT_A_ID,
  nombre: "Fintech Plus SL",
};

// ============================================================
// Helpers · mount mocks comunes per scope
// ============================================================

export async function mockAdminWorkflowCommandCenter(page: Page) {
  await page.route(
    "**/api/v1/admin/workflow-command-center",
    async (route) => {
      await route.fulfill({ status: 200, json: MOCK_COMMAND_CENTER_RESPONSE });
    },
  );
  await page.route(
    `**/api/v1/admin/workflow-command-center/projects/${PROJECT_A_ID}`,
    async (route) => {
      await route.fulfill({ status: 200, json: MOCK_CRONOLOGICA_RESPONSE });
    },
  );
  await page.route(
    `**/api/v1/clients/projects/${PROJECT_A_ID}`,
    async (route) => {
      await route.fulfill({ status: 200, json: MOCK_PROJECT_INFO });
    },
  );
}

export async function mockClientWorkflowGuide(page: Page) {
  await page.route(
    "**/api/v1/client-portal/project",
    async (route) => {
      await route.fulfill({ status: 200, json: MOCK_CLIENT_PORTAL_PROJECT });
    },
  );
  await page.route(
    `**/api/v1/projects/${PROJECT_A_ID}/workflow-guide`,
    async (route) => {
      await route.fulfill({ status: 200, json: MOCK_WORKFLOW_GUIDE_CLIENT });
    },
  );
}

export async function mockDeliverables(page: Page) {
  await page.route(
    new RegExp(
      `/api/v1/projects/${PROJECT_A_ID}/workflow-engine/steps/[^/]+/deliverables$`,
    ),
    async (route) => {
      await route.fulfill({ status: 200, json: MOCK_DELIVERABLES_AVAILABLE });
    },
  );
}

export async function mockCopilotoAdminStub(page: Page) {
  await page.route(
    "**/api/v1/admin/copilot/chat",
    async (route) => {
      const body = JSON.parse(route.request().postData() ?? "{}");
      await route.fulfill({
        status: 200,
        json: {
          action_id: body.action_id ?? "que_hago",
          response_text:
            "Próximo step de la cliente \"Fintech Plus\": Formación G1 · " +
            "te ayudo a redactar email convocatoria si lo necesitas.",
          is_stub: true,
          next_action_hint: "Marca el sub-paso completo cuando esté hecho",
          citations: [],
        },
      });
    },
  );
}

export async function mockCopilotoClienteStub(page: Page) {
  await page.route(
    "**/api/v1/client-portal/copilot/chat",
    async (route) => {
      const body = JSON.parse(route.request().postData() ?? "{}");
      await route.fulfill({
        status: 200,
        json: {
          action_id: body.action_id ?? "que_hago",
          response_text:
            "Tu siguiente paso es \"Formación G1 empleados\". Si tienes " +
            "dudas sobre cómo abordarlo · estoy aquí para explicarte. " +
            "Sin prisa · avanzamos a tu ritmo.",
          is_stub: true,
          next_action_hint: "Cuando termines · márcalo como hecho",
          citations: [],
        },
      });
    },
  );
}
