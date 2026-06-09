/**
 * Fixtures compartidos · fase_26 sub-atom 1.D.F.0.E v3.11 · CIERRE quality
 * completeness pre-piloto.
 *
 * Cubre:
 *  - Director admin AHORA pin-to-top sticky + toggle vista localStorage (1.D.F.0.C)
 *  - Copiloto admin context-aware button-level screen-references (1.D.F.0.D)
 *
 * Pattern reuse · OPS-045 sostenido · fase_17 helpers + fase_22 mock patterns +
 * fase_25 spec-as-code ARTIFACT.
 *
 * Mocks page.route · execution diferida CI full backend.
 */
import type { Page } from "@playwright/test";

export const PROJECT_F26_ID = "ff261122-3344-5566-7788-99aabbccddff";

// ============================================================
// Cronológica mock · AHORA + 2 completados + 3 proximos7d + 2 proximos30d
// (suficiente para verificar pin-to-top sticky · toggle ahora-only oculta resto)
// ============================================================

const MOCK_STEP_AHORA = {
  template_id: "ENR_AD_03_FORMACION",
  phase: "adecuacion",
  order_within_phase: 3,
  title: "Formación G1 empleados",
  description_detailed_es:
    "Todos los empleados (25 personas) deben completar un curso online de " +
    "1 hora sobre seguridad básica ENS. Coordina con RRHH.",
  rationale_es:
    "Es obligatorio para certificación ENS Anexo II mp.per.* (formación).",
  cta_label: "Subir evidencias asistencia",
  cta_url: null,
  priority: 1,
  estimated_days: 14,
  deliverable_codes: ["E-500", "E-501"],
  prerequisite_template_ids: [],
  actors: ["CISO", "RRHH"],
  completion_criteria_detailed: [
    "Plan formación E-500 firmado CISO",
    ">=80% asistencia 25 empleados",
  ],
  adaptation_notes_es: null,
  tooltips_ens: {},
  is_enriched: true,
  variant_extra_focus: null,
  variant_reference_norms: [],
  task_id: null,
  status: "pending",
  due_date_iso: null,
  started_at_iso: null,
  completed_at_iso: null,
  blocked_reason: null,
  urgency_score: 85,
};

const MOCK_STEP_COMPLETED_1 = {
  ...MOCK_STEP_AHORA,
  template_id: "ENR_AD_01_DICAT",
  title: "DICAT categorización",
  status: "completed",
  urgency_score: 0,
};

const MOCK_STEP_COMPLETED_2 = {
  ...MOCK_STEP_AHORA,
  template_id: "ENR_AD_02_DDA",
  title: "DdA Declaración Aplicabilidad",
  status: "completed",
  urgency_score: 0,
};

const MOCK_STEP_PROX_7D_1 = {
  ...MOCK_STEP_AHORA,
  template_id: "ENR_AD_04_REGISTROS",
  title: "Arrancar registros vivos",
  status: "pending",
  urgency_score: 50,
};
const MOCK_STEP_PROX_7D_2 = {
  ...MOCK_STEP_AHORA,
  template_id: "ENR_AD_05_POLITICAS",
  title: "Políticas firmadas",
  status: "pending",
  urgency_score: 45,
};
const MOCK_STEP_PROX_7D_3 = {
  ...MOCK_STEP_AHORA,
  template_id: "ENR_AD_06_MAGERIT",
  title: "MAGERIT inicial",
  status: "pending",
  urgency_score: 40,
};

const MOCK_STEP_PROX_30D_1 = {
  ...MOCK_STEP_AHORA,
  template_id: "ENR_AD_07_PRE_AUDIT",
  title: "Pre-auditoría interna",
  status: "pending",
  urgency_score: 20,
};
const MOCK_STEP_PROX_30D_2 = {
  ...MOCK_STEP_AHORA,
  template_id: "ENR_AD_08_DOSSIER",
  title: "Dossier ENAC borrador",
  status: "pending",
  urgency_score: 15,
};

export const MOCK_CRONOLOGICA_FULL = {
  project_id: PROJECT_F26_ID,
  project_nombre: "Test Cliente F26",
  dims: {
    categoria_objetivo: "MEDIA",
    archetype: "proveedor_financiero",
    fase: "adecuacion",
    tamano_empleados: "pequeno",
    madurez_ens_actual: "L1",
    horas_cliente_semana: "5_15h",
  },
  current_phase: "adecuacion",
  progress: {
    global_pct: 50,
    global_completed: 4,
    global_total: 8,
    per_phase: {
      diagnostico: { completed: 2, total: 2, pct: 100 },
      adecuacion: { completed: 2, total: 6, pct: 33 },
    },
  },
  completed: [MOCK_STEP_COMPLETED_1, MOCK_STEP_COMPLETED_2],
  ahora: MOCK_STEP_AHORA,
  proximos_7d: [MOCK_STEP_PROX_7D_1, MOCK_STEP_PROX_7D_2, MOCK_STEP_PROX_7D_3],
  proximos_30d: [MOCK_STEP_PROX_30D_1, MOCK_STEP_PROX_30D_2],
};

const MOCK_PROJECT_INFO = {
  id: PROJECT_F26_ID,
  nombre: "Test Cliente F26",
  client_id: "client-f26",
};

export async function mockAdminCronologicaFull(page: Page) {
  await page.route(
    "**/api/v1/admin/workflow-command-center",
    async (route) => {
      await route.fulfill({
        status: 200,
        json: {
          urgentes_hoy: [],
          esta_semana: [],
          en_marcha: [],
          proximos_30d: [],
        },
      });
    },
  );
  await page.route(
    `**/api/v1/admin/workflow-command-center/projects/${PROJECT_F26_ID}`,
    async (route) => {
      await route.fulfill({ status: 200, json: MOCK_CRONOLOGICA_FULL });
    },
  );
  await page.route(
    `**/api/v1/clients/projects/${PROJECT_F26_ID}`,
    async (route) => {
      await route.fulfill({ status: 200, json: MOCK_PROJECT_INFO });
    },
  );
}

// ============================================================
// Copilot admin · screen-aware mocks (1.D.F.0.D)
// ============================================================

/**
 * Mock copilot admin chat · responde según current_screen propagado.
 * Permite verify cambio de pantalla actualiza referencias botones.
 */
export async function mockCopilotoAdminScreenAware(page: Page) {
  await page.route("**/api/v1/admin/copilot/chat", async (route) => {
    const body = JSON.parse(route.request().postData() ?? "{}") as {
      action_id: string;
      current_screen?: string;
    };
    const screen = body.current_screen ?? "";

    if (screen.includes("/dda")) {
      await route.fulfill({
        status: 200,
        json: {
          action_id: body.action_id ?? "que_hago",
          response_text:
            "Estás en la Declaración de Aplicabilidad (DdA · es decir el " +
            "documento donde defines qué medidas ENS Anexo II aplicas). " +
            "Pulsa [Marcar medida implementada] arriba derecha en cada " +
            "medida · luego [Subir evidencia] con el justificante. " +
            "Cita: RD 311/2022 Anexo II · CCN-STIC-803.",
          is_stub: false,
          next_action_hint: "Marca medida implementada · sube evidencia",
          citations: [],
        },
      });
      return;
    }

    if (screen.includes("/mcps")) {
      await route.fulfill({
        status: 200,
        json: {
          action_id: body.action_id ?? "que_hago",
          response_text:
            "Estás en Pentest MCPs project-scoped. Pulsa [Lanzar Nuclei] " +
            "para vulnscan template-driven · [Lanzar Prowler] para cloud " +
            "AWS/GCP · [Lanzar CLARA] para hardening config. El stream " +
            "SSE muestra progreso real-time. Evidence auto-attach IDMS " +
            "folder 13_Informes_Tecnicos.",
          is_stub: false,
          next_action_hint: "Lanzar Nuclei · descargar reporte",
          citations: [],
        },
      });
      return;
    }

    if (screen.includes("/contratos")) {
      await route.fulfill({
        status: 200,
        json: {
          action_id: body.action_id ?? "que_hago",
          response_text:
            "Estás en Contratos M14. Pulsa [Generar C-001 servicios] " +
            "para crear contrato servicios estándar · wizard 3 steps. " +
            "Luego [Marcar firmado] cuando cliente devuelva firmado.",
          is_stub: false,
          next_action_hint: "Generar C-001 servicios",
          citations: [],
        },
      });
      return;
    }

    // Default · sin screen identifica
    await route.fulfill({
      status: 200,
      json: {
        action_id: body.action_id ?? "que_hago",
        response_text:
          "Te ayudo con cualquier cliente · sin pantalla activa " +
          "identificada · dame contexto sobre dónde estás.",
        is_stub: false,
        next_action_hint: null,
        citations: [],
      },
    });
  });
}
