/**
 * E2E NextActionCard home admin proyecto (MB-13.1 · ADR-035).
 *
 * Cobertura:
 *   1. NextActionCard renderiza con badge fase + readiness score
 *   2. CTA primary action es link clickable con href endpoint
 *   3. Sin acciones (placeholder) muestra "Sin acciones pendientes"
 *
 * Pattern post-MF3.5: loginAsMarcos(context) + page.route mocks.
 */
import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "./_helpers/auth-real";

const PROJECT_ID = "11111111-2222-3333-4444-555555555555";

const DASHBOARD_WITH_ACTIONS = {
  project_id: PROJECT_ID,
  project_name: "Proyecto E2E MB-13.1",
  category: "BASICA",
  archetype: null,
  current_phase: "diagnostico",
  current_phase_label: "Diagnóstico",
  phase_index: 2,
  phase_total: 10,
  next_actions: [
    {
      action_id: "run_diagnosis",
      label: "Ejecutar diagnóstico inicial",
      motor: "M21",
      cta: "Ejecutar diagnóstico inicial",
      action_url: "/admin/diagnosis/runs/new",
      estimated_minutes: 45,
      priority: 1,
      urgent: true,
      blocking: false,
    },
    {
      action_id: "review_maturity_report",
      label: "Revisar informe madurez",
      motor: "M21",
      cta: "Revisar informe madurez",
      action_url: "/admin/diagnosis/runs",
      estimated_minutes: 25,
      priority: 2,
      urgent: true,
      blocking: false,
    },
  ],
  readiness_score: 42,
  active_alerts: [],
  active_alerts_count: 0,
  estimated_days_to_certification: 28,
  blocking_issues: ["RSEG no asignado", "Sin DdA inicial"],
  last_updated: new Date().toISOString(),
};

const DASHBOARD_EMPTY = {
  ...DASHBOARD_WITH_ACTIONS,
  next_actions: [],
  blocking_issues: [],
  current_phase: "conformidad",
  current_phase_label: "Conformidad",
  phase_index: 8,
  estimated_days_to_certification: 0,
};

// El layout project-scoped (app/(admin)/admin/projects/[id]/layout.tsx) monta
// ProjectFeaturesProvider + ProjectHeader + ProjectTabs + ProjectCategoryBanner,
// que llaman /feature-flags y /header. La spec original solo stubea /dashboard,
// dejando esas llamadas contra el backend real (proyecto inexistente → ruido /
// render no determinista). Stubeamos el layout para aislar el NextActionCard.
const LAYOUT_FEATURE_FLAGS = {
  categoria: "BASICA",
  archetype: null,
  employee_count: null,
  features: {},
};

const LAYOUT_HEADER = {
  project: {
    id: "stub",
    nombre: "Proyecto E2E MB-13.1",
    fase: "diagnostico",
    categoria_objetivo: "BASICA",
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

test.describe("MB-13.1 · NextActionCard home admin", () => {
  test.beforeEach(async ({ context, page }) => {
    await loginAsMarcos(context);
    await page.route(`**/api/v1/projects/*/feature-flags`, (route) =>
      route.fulfill({ status: 200, json: LAYOUT_FEATURE_FLAGS }),
    );
    await page.route(`**/api/v1/projects/*/header`, (route) =>
      route.fulfill({ status: 200, json: LAYOUT_HEADER }),
    );
  });

  test("renderiza NextActionCard con badge fase + readiness + CTA", async ({
    page,
  }) => {
    await page.route(
      `**/api/v1/projects/${PROJECT_ID}/dashboard`,
      async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(DASHBOARD_WITH_ACTIONS),
        });
      },
    );

    await page.goto(`/admin/projects/${PROJECT_ID}/summary`);

    const card = page.getByTestId("next-action-card");
    await expect(card).toBeVisible({ timeout: 10_000 });

    await expect(card.getByText(/Fase 3 de 10: Diagnóstico/)).toBeVisible();
    await expect(card.getByText(/Siguiente acción/)).toBeVisible();
    await expect(card.getByText("42%")).toBeVisible();
    await expect(card.getByText(/Madurez ENS/)).toBeVisible();

    const cta = card.getByRole("link", {
      name: /Ejecutar diagnóstico inicial/,
    });
    await expect(cta).toBeVisible();
    await expect(cta).toHaveAttribute("href", "/admin/diagnosis/runs/new");
  });

  test("muestra bloqueantes activos con role=alert", async ({ page }) => {
    await page.route(
      `**/api/v1/projects/${PROJECT_ID}/dashboard`,
      async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(DASHBOARD_WITH_ACTIONS),
        });
      },
    );

    await page.goto(`/admin/projects/${PROJECT_ID}/summary`);

    const card = page.getByTestId("next-action-card");
    await expect(card).toBeVisible({ timeout: 10_000 });

    const blockers = card.getByRole("alert");
    await expect(blockers).toBeVisible();
    await expect(blockers.getByText(/RSEG no asignado/)).toBeVisible();
    await expect(blockers.getByText(/Sin DdA inicial/)).toBeVisible();
  });

  test("estado sin acciones en fase conformidad", async ({ page }) => {
    await page.route(
      `**/api/v1/projects/${PROJECT_ID}/dashboard`,
      async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(DASHBOARD_EMPTY),
        });
      },
    );

    await page.goto(`/admin/projects/${PROJECT_ID}/summary`);

    const card = page.getByTestId("next-action-card");
    await expect(card).toBeVisible({ timeout: 10_000 });
    await expect(card.getByText(/Sin acciones pendientes/)).toBeVisible();
    await expect(card.getByText(/Conformidad alcanzada/)).toBeVisible();
  });
});
