/**
 * E2E test workflow phase derivation · admin + cliente (FASE 8 sub-bloque 8.B.7
 * + SAN-C MB-11.1 extensión 10 fases canonical).
 *
 * Cobertura:
 * 1. /admin/projects/[id]/roadmap renders RoadmapView (10 PhaseCards) +
 *    NextActions list (top 5 priorizados)
 * 2. NextActionCard render correcto (motor badge + priority + estimated time)
 *    con mock /workflow/next-actions
 * (La vista cliente /client-portal/workflow ya no usa RoadmapView: se remodeló
 *  a workflow-guide y la cubre fase_17/client/cliente_step_enriched_friendly.spec.ts.)
 *
 * Pattern post-MF3.5 sostenido: loginAsMarcos / loginAsClient + page.route mocks.
 */
import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";

import { loginAsMarcos } from "./_helpers/auth-real";

const PROJECT_A_ID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee";

const MOCK_ROADMAP_ADMIN = {
  project_id: PROJECT_A_ID,
  current_phase: "diagnostico",
  phases: [
    { phase: "pre_venta", status: "done", pct_completed: 100, is_current: false },
    { phase: "onboarding", status: "done", pct_completed: 100, is_current: false },
    { phase: "diagnostico", status: "in_progress", pct_completed: 50, is_current: true },
    { phase: "analisis_riesgos", status: "pending", pct_completed: 0, is_current: false },
    { phase: "adecuacion", status: "pending", pct_completed: 0, is_current: false },
    { phase: "implantacion", status: "pending", pct_completed: 0, is_current: false },
    { phase: "dda_final", status: "pending", pct_completed: 0, is_current: false },
    { phase: "verificacion", status: "pending", pct_completed: 0, is_current: false },
    { phase: "conformidad", status: "pending", pct_completed: 0, is_current: false },
    { phase: "retainer_cierre", status: "pending", pct_completed: 0, is_current: false },
  ],
};

const MOCK_NEXT_ACTIONS = [
  {
    action_id: "run_diagnosis",
    label: "Ejecutar diagnóstico inicial",
    motor: "M21",
    endpoint: "/admin/diagnosis/runs/new",
    priority: 1,
    estimated_minutes: 45,
  },
  {
    action_id: "review_maturity_report",
    label: "Revisar informe madurez",
    motor: "M21",
    endpoint: "/admin/diagnosis/runs",
    priority: 2,
    estimated_minutes: 25,
  },
];


// ActiveProjectSync (ADR-054, layout /admin/projects/[id]) pide
// /projects/{id}/header y, si falla (404: PROJECT_A_ID no existe en BD),
// limpia el store y hace router.replace al selector /admin/projects. Sin este
// stub el roadmap llegaba a pintarse o no según ganara la carrera contra el
// 404 → test intermitente. Stub = proyecto accesible, flujo determinista.
const MOCK_PROJECT_HEADER = {
  project: {
    id: PROJECT_A_ID,
    nombre: "Proyecto Test FASE 8",
    fase: "diagnostico",
    categoria_objetivo: "MEDIA",
    lifecycle_state: "ACTIVE",
    fecha_kickoff: null,
    fecha_objetivo_certificacion: null,
    certified_at: null,
  },
  cliente: {
    id: "x",
    nombre: "Cliente Test FASE 8",
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

async function stubRoadmapBackend(page: Page) {
  await page.route(
    `**/api/v1/workflow/roadmap/${PROJECT_A_ID}`,
    async (route) => {
      await route.fulfill({ status: 200, json: MOCK_ROADMAP_ADMIN });
    },
  );
  await page.route(
    new RegExp(`/api/v1/workflow/next-actions/${PROJECT_A_ID}`),
    async (route) => {
      await route.fulfill({ status: 200, json: MOCK_NEXT_ACTIONS });
    },
  );
  await page.route(
    `**/api/v1/projects/${PROJECT_A_ID}/header`,
    async (route) => {
      await route.fulfill({ status: 200, json: MOCK_PROJECT_HEADER });
    },
  );
  // ProjectHeader / ProjectTabs query (avoid network failures unrelated)
  await page.route(`**/api/v1/clients/projects/${PROJECT_A_ID}`, async (route) => {
    await route.fulfill({
      status: 200,
      json: { id: PROJECT_A_ID, nombre: "Proyecto Test FASE 8", client_id: "x" },
    });
  });
}


test.describe("FASE 8 · workflow phase derivation", () => {
  test("admin /admin/projects/[id]/roadmap renders 10 phase cards + next actions", async ({
    page,
    context,
  }) => {
    await loginAsMarcos(context);
    await stubRoadmapBackend(page);

    await page.goto(`/admin/projects/${PROJECT_A_ID}/roadmap`);

    // Roadmap heading
    await expect(
      page.getByRole("heading", { name: /Roadmap del proyecto/i }),
    ).toBeVisible();

    // 10 phase cards (one per fase) — buscar labels representativos incluyendo
    // las 2 sub-fases nuevas SAN-C MB-11.1 (analisis_riesgos · dda_final)
    await expect(page.getByText("Diagnóstico", { exact: true }).first()).toBeVisible();
    await expect(page.getByText("Análisis de riesgos", { exact: true }).first()).toBeVisible();
    await expect(page.getByText("DdA final", { exact: true }).first()).toBeVisible();
    await expect(page.getByText("Conformidad", { exact: true }).first()).toBeVisible();

    // Next actions sidebar
    await expect(
      page.getByRole("heading", { name: /Próximas acciones/i }),
    ).toBeVisible();
    await expect(page.getByText(/Ejecutar diagnóstico inicial/i)).toBeVisible();
  });

  test("NextActionCard renders motor badge + priority + estimated time", async ({
    page,
    context,
  }) => {
    await loginAsMarcos(context);
    await stubRoadmapBackend(page);

    await page.goto(`/admin/projects/${PROJECT_A_ID}/roadmap`);

    // Motor badge "M21"
    await expect(page.getByText("M21").first()).toBeVisible();
    // Estimated time
    await expect(page.getByText(/45 min/)).toBeVisible();
    // Priority badge "Prioridad Alta"
    await expect(page.getByText(/Prioridad Alta/i).first()).toBeVisible();
  });
});
