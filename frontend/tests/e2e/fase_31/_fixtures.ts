/**
 * Fixtures fase_31 · sub-atom 1.D.G v3.11 · workflow cross-actor dependencies + real-time sync.
 *
 * Cubre:
 *  - Admin /workflow Tab "Próximos pasos" + 4 groups blockers panel
 *  - Cliente "Tu siguiente acción" + "Lo que Marcos está preparando"
 *  - SSE step_unblocked real-time event flow cross-portal
 *  - Cadena admin→cliente→admin alternating BASICA + MEDIA cycle abbreviated
 *
 * Pattern reuse OPS-045 28ª aplicación · mocks page.route spec-as-code · execution diferida CI full.
 */
import type { Page } from "@playwright/test";

export const PROJECT_F31_ID = "ff311122-3344-5566-7788-99aabbccddff";

// ============ ADMIN cronologica · BLOQUEOS scenario ============

const MOCK_ADMIN_CRONOLOGICA_BLOCKERS = {
  project_id: PROJECT_F31_ID,
  project_nombre: "Cliente cross-actor test",
  current_phase: "implantacion",
  dims: {
    categoria_objetivo: "BASICA",
    archetype: "saas_only",
    fase: "implantacion",
    tamano_empleados: "pequeno",
  },
  progress: {
    global_pct: 35,
    global_completed: 5,
    global_total: 14,
    per_phase: {
      implantacion: { completed: 1, total: 4, pct: 25 },
    },
  },
  completed: [],
  ahora: {
    template_id: "ADMIN_REVIEW_X",
    phase: "implantacion",
    order_within_phase: 1,
    title: "Marcos prepara · revisión técnica X",
    description_detailed_es: "Revisar implementación medida op.exp.5",
    rationale_es: "Necesario antes de firma cliente",
    cta_label: "Continuar",
    cta_url: "/admin/projects/test/dda",
    priority: 9,
    estimated_days: 3,
    deliverable_codes: ["E-001"],
    prerequisite_template_ids: [],
    actors: ["Marcos"],
    completion_criteria_detailed: [],
    adaptation_notes_es: null,
    tooltips_ens: {},
    is_enriched: true,
    variant_extra_focus: null,
    variant_reference_norms: [],
    task_id: "task-admin-x",
    status: "in_progress",
    due_date_iso: null,
    started_at_iso: "2026-05-19T10:00:00Z",
    completed_at_iso: null,
    blocked_reason: null,
    urgency_score: 80,
    primary_actor: "admin",
    dependency_status: "in_progress",
    missing_prerequisites: [],
    estimated_days_to_complete: 3,
  },
  proximos_7d: [
    {
      template_id: "CLIENTE_SIGN_Y",
      phase: "implantacion",
      order_within_phase: 2,
      title: "Cliente firma DdA · medidas",
      description_detailed_es: "Cliente revisa y firma DdA inicial",
      rationale_es: null,
      cta_label: "Firmar",
      cta_url: "/client-portal/dda",
      priority: 10,
      estimated_days: 5,
      deliverable_codes: [],
      prerequisite_template_ids: ["ADMIN_REVIEW_X"],
      actors: ["cliente_PoC", "RSEG_cliente"],
      completion_criteria_detailed: [],
      adaptation_notes_es: null,
      tooltips_ens: {},
      is_enriched: true,
      variant_extra_focus: null,
      variant_reference_norms: [],
      task_id: "task-cli-y",
      status: "pending",
      due_date_iso: null,
      started_at_iso: "2026-05-20T10:00:00Z",
      completed_at_iso: null,
      blocked_reason: "Esperando Marcos termine: Revisión técnica X",
      urgency_score: 65,
      primary_actor: "cliente",
      dependency_status: "blocked",
      missing_prerequisites: ["ADMIN_REVIEW_X"],
      estimated_days_to_complete: 5,
    },
    {
      template_id: "CLIENTE_UPLOAD_Z",
      phase: "implantacion",
      order_within_phase: 3,
      title: "Cliente sube documento autoridad",
      description_detailed_es: "Subir documento aprobación dirección",
      rationale_es: null,
      cta_label: "Subir",
      cta_url: "/client-portal/files",
      priority: 7,
      estimated_days: 2,
      deliverable_codes: [],
      prerequisite_template_ids: [],
      actors: ["cliente_PoC"],
      completion_criteria_detailed: [],
      adaptation_notes_es: null,
      tooltips_ens: {},
      is_enriched: true,
      variant_extra_focus: null,
      variant_reference_norms: [],
      task_id: "task-cli-z",
      status: "pending",
      due_date_iso: null,
      started_at_iso: "2026-05-18T10:00:00Z",
      completed_at_iso: null,
      blocked_reason: null,
      urgency_score: 50,
      primary_actor: "cliente",
      dependency_status: "available",
      missing_prerequisites: [],
      estimated_days_to_complete: 2,
    },
  ],
  proximos_30d: [],
};

// ============ CLIENTE workflow guide scenario ============

const MOCK_CLIENT_PROJECT = {
  id: PROJECT_F31_ID,
  nombre: "Cliente cross-actor test",
};

const MOCK_CLIENT_WORKFLOW_GUIDE = {
  project_id: PROJECT_F31_ID,
  categoria: "BASICA",
  archetype: "saas_only",
  fase: "implantacion",
  progress: {
    project_id: PROJECT_F31_ID,
    global_pct: 35,
    global_completed: 5,
    global_total: 14,
    per_phase: {},
  },
  current_step: {
    template_id: "CLIENTE_UPLOAD_Z",
    phase: "implantacion",
    order_within_phase: 3,
    title: "Subir documento autoridad",
    description_detailed_es: "Necesitamos el documento firmado por dirección",
    rationale_es: null,
    cta_label: "Subir ahora",
    cta_url: "/client-portal/files",
    priority: 7,
    estimated_days: 2,
    deliverable_codes: [],
    prerequisite_template_ids: [],
    actors: ["cliente_PoC"],
    completion_criteria_detailed: [],
    adaptation_notes_es: null,
    tooltips_ens: {},
    is_enriched: true,
    variant_extra_focus: null,
    variant_reference_norms: [],
    task_id: "task-cli-z",
    status: "pending",
    due_date_iso: null,
    started_at_iso: null,
    completed_at_iso: null,
    blocked_reason: null,
    urgency_score: 50,
    primary_actor: "cliente",
    dependency_status: "available",
    missing_prerequisites: [],
    estimated_days_to_complete: 2,
  },
  completed: [],
  proximos: [
    {
      template_id: "ADMIN_REVIEW_X",
      phase: "implantacion",
      order_within_phase: 1,
      title: "Revisión técnica X",
      description_detailed_es: null,
      rationale_es: null,
      cta_label: null,
      cta_url: null,
      priority: 9,
      estimated_days: 3,
      deliverable_codes: [],
      prerequisite_template_ids: [],
      actors: ["Marcos"],
      completion_criteria_detailed: [],
      adaptation_notes_es: null,
      tooltips_ens: {},
      is_enriched: true,
      variant_extra_focus: null,
      variant_reference_norms: [],
      task_id: "task-admin-x",
      status: "in_progress",
      due_date_iso: null,
      started_at_iso: null,
      completed_at_iso: null,
      blocked_reason: null,
      urgency_score: 80,
      primary_actor: "admin",
      dependency_status: "in_progress",
      missing_prerequisites: [],
      estimated_days_to_complete: 3,
    },
  ],
};

// ============ MEDIA cycle abbreviated · alternating chain ============

const MOCK_ADMIN_CRONOLOGICA_MEDIA_CHAIN = {
  ...MOCK_ADMIN_CRONOLOGICA_BLOCKERS,
  dims: { ...MOCK_ADMIN_CRONOLOGICA_BLOCKERS.dims, categoria_objetivo: "MEDIA" },
  proximos_7d: [
    {
      ...MOCK_ADMIN_CRONOLOGICA_BLOCKERS.proximos_7d[0],
      template_id: "STEP1_MARCOS",
      title: "Step1 · Marcos analiza",
      primary_actor: "admin" as const,
      dependency_status: "in_progress" as const,
      blocked_reason: null,
    },
    {
      ...MOCK_ADMIN_CRONOLOGICA_BLOCKERS.proximos_7d[0],
      template_id: "STEP2_CLIENTE",
      title: "Step2 · Cliente confirma",
      primary_actor: "cliente" as const,
      dependency_status: "blocked" as const,
      blocked_reason: "Esperando Marcos termine: Step1 · Marcos analiza",
      prerequisite_template_ids: ["STEP1_MARCOS"],
    },
    {
      ...MOCK_ADMIN_CRONOLOGICA_BLOCKERS.proximos_7d[0],
      template_id: "STEP3_MARCOS",
      title: "Step3 · Marcos redacta",
      primary_actor: "admin" as const,
      dependency_status: "blocked" as const,
      blocked_reason: "Bloqueado por 1 pasos previos pendientes",
      prerequisite_template_ids: ["STEP2_CLIENTE"],
    },
    {
      ...MOCK_ADMIN_CRONOLOGICA_BLOCKERS.proximos_7d[0],
      template_id: "STEP4_CLIENTE",
      title: "Step4 · Cliente firma",
      primary_actor: "cliente" as const,
      dependency_status: "blocked" as const,
      blocked_reason: "Esperando Marcos termine: Step3 · Marcos redacta",
      prerequisite_template_ids: ["STEP3_MARCOS"],
    },
  ],
};

// ============ Mock helpers ============

export async function mockAdminWorkflowBlockers(page: Page): Promise<void> {
  await page.route(
    `**/api/v1/admin/workflow-command-center/projects/${PROJECT_F31_ID}**`,
    (route) => {
      const url = route.request().url();
      if (url.includes("/remind")) {
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            project_id: PROJECT_F31_ID,
            template_id: "CLIENTE_UPLOAD_Z",
            notified: true,
            channels: ["in_app", "email"],
            message: "Recordatorio enviado",
          }),
        });
      }
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(MOCK_ADMIN_CRONOLOGICA_BLOCKERS),
      });
    },
  );
  await page.route("**/api/v1/projects/*/events", (route) => {
    return route.fulfill({
      status: 200,
      contentType: "text/event-stream",
      body: "",
    });
  });
}

export async function mockAdminWorkflowMediaChain(page: Page): Promise<void> {
  await page.route(
    `**/api/v1/admin/workflow-command-center/projects/${PROJECT_F31_ID}**`,
    (route) => {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(MOCK_ADMIN_CRONOLOGICA_MEDIA_CHAIN),
      });
    },
  );
  await page.route("**/api/v1/projects/*/events", (route) =>
    route.fulfill({
      status: 200,
      contentType: "text/event-stream",
      body: "",
    }),
  );
}

export async function mockClientWorkflowCrossActor(page: Page): Promise<void> {
  await page.route("**/api/v1/client-portal/project", (route) => {
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(MOCK_CLIENT_PROJECT),
    });
  });
  await page.route(
    `**/api/v1/projects/${PROJECT_F31_ID}/workflow-guide`,
    (route) => {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(MOCK_CLIENT_WORKFLOW_GUIDE),
      });
    },
  );
  await page.route(
    "**/api/v1/client-portal/projects/*/events",
    (route) => {
      return route.fulfill({
        status: 200,
        contentType: "text/event-stream",
        body: "",
      });
    },
  );
}
