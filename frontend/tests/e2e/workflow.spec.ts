/**
 * E2E test workflow phase derivation · admin + cliente (FASE 8 sub-bloque 8.B.7
 * + SAN-C MB-11.1 extensión 10 fases canonical).
 *
 * Cobertura 3 tests:
 * 1. /admin/projects/[id]/roadmap renders RoadmapView (10 PhaseCards) +
 *    NextActions list (top 5 priorizados)
 * 2. NextActionCard render correcto (motor badge + priority + estimated time)
 *    con mock /workflow/next-actions
 * 3. /client-portal/workflow renders RoadmapView con mock
 *    /portal/workflow/roadmap (cross-pool RBAC)
 *
 * Pattern post-MF3.5 sostenido: loginAsMarcos / loginAsClient + page.route mocks.
 */
import { expect, test } from "@playwright/test";

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


test.describe("FASE 8 · workflow phase derivation", () => {
  test("admin /admin/projects/[id]/roadmap renders 10 phase cards + next actions", async ({
    page,
    context,
  }) => {
    await loginAsMarcos(context);

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
    // ProjectHeader / ProjectTabs query (avoid network failures unrelated)
    await page.route(`**/api/v1/clients/projects/${PROJECT_A_ID}`, async (route) => {
      await route.fulfill({
        status: 200,
        json: { id: PROJECT_A_ID, nombre: "Proyecto Test FASE 8", client_id: "x" },
      });
    });

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
    await page.route(`**/api/v1/clients/projects/${PROJECT_A_ID}`, async (route) => {
      await route.fulfill({
        status: 200,
        json: { id: PROJECT_A_ID, nombre: "Proyecto Test FASE 8", client_id: "x" },
      });
    });

    await page.goto(`/admin/projects/${PROJECT_A_ID}/roadmap`);

    // Motor badge "M21"
    await expect(page.getByText("M21").first()).toBeVisible();
    // Estimated time
    await expect(page.getByText(/45 min/)).toBeVisible();
    // Priority badge "Prioridad Alta"
    await expect(page.getByText(/Prioridad Alta/i).first()).toBeVisible();
  });

  // SKIP: feature eliminada/remodelada (la vista cliente /client-portal/workflow
  // dejó de usar RoadmapView + endpoints /portal/workflow/roadmap|next-actions).
  // REMODELADO v3.8 (sub-atom 1.C.D.C.1): ahora consume `useClientWorkflowGuide`
  // (endpoint workflow-guide) y renderiza WorkflowGuideTimelineClient +
  // WorkflowProgressBarClient en lugar de PhaseCards. Por eso los mocks
  // /portal/workflow/roadmap ya no se invocan, no hay heading "Workflow del
  // proyecto" ni PhaseCard "Conformidad". El roadmap admin (tests 1/2) sigue vivo.
  // Candidata a borrar/reescribir contra workflow-guide tras contraste (Marcos).
  test.skip("client portal /client-portal/workflow renders roadmap (cross-pool RBAC)", async ({
    page,
  }) => {
    // Note: loginAsClient requires globalSetup E2E client + dev backend
    // Aquí mock-only sin login real (verifica route render fallback)
    await page.route("**/api/v1/auth/me", async (route) => {
      await route.fulfill({ status: 401, json: { detail: "Not authenticated" } });
    });
    await page.route(
      "**/client-portal/me",
      async (route) => {
        await route.fulfill({
          status: 200,
          json: {
            id: "client-id",
            email: "test@cliente.com",
            full_name: "Cliente Test",
            role: "rseg",
            scopes: ["view_project_full"],
            must_change_password: false,
          },
        });
      },
    );
    await page.route(
      "**/client-portal/project",
      async (route) => {
        await route.fulfill({
          status: 200,
          json: {
            id: PROJECT_A_ID,
            nombre: "Proyecto Cliente Test",
            categoria_objetivo: "MEDIA",
            estado: "active",
            lifecycle_state: "ACTIVE",
          },
        });
      },
    );
    await page.route(
      `**/api/v1/portal/workflow/roadmap/${PROJECT_A_ID}`,
      async (route) => {
        await route.fulfill({ status: 200, json: MOCK_ROADMAP_ADMIN });
      },
    );
    await page.route(
      new RegExp(`/api/v1/portal/workflow/next-actions/${PROJECT_A_ID}`),
      async (route) => {
        await route.fulfill({ status: 200, json: MOCK_NEXT_ACTIONS });
      },
    );

    await page.goto("/client-portal/workflow");

    // Heading "Mi proyecto" + project name
    await expect(
      page.getByRole("heading", { name: /Proyecto Cliente Test|Workflow del proyecto/i }),
    ).toBeVisible();

    // RoadmapView visible (PhaseCards render)
    await expect(page.getByText("Conformidad", { exact: true }).first()).toBeVisible();
  });
});
