/**
 * E2E PhaseProgressWizard 10 fases (MB-13.2 · ADR-035).
 *
 * Cobertura:
 *   1. Stepper renderiza 10 fases + counter "Fase X de 10"
 *   2. Fase actual highlighted (ring) · pasadas check verde · futuras lock
 *   3. Tooltip muestra nombre completo + descripción
 *
 * Pattern post-MF3.5: loginAsMarcos(context) + page.route mocks.
 */
import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "./_helpers/auth-real";

const PROJECT_ID = "11111111-2222-3333-4444-666666666666";

const DASHBOARD_PHASE_5 = {
  project_id: PROJECT_ID,
  project_name: "Proyecto E2E MB-13.2",
  category: "MEDIA",
  archetype: null,
  current_phase: "implantacion",
  current_phase_label: "Implantación",
  phase_index: 5,
  phase_total: 10,
  next_actions: [],
  readiness_score: 60,
  active_alerts: [],
  active_alerts_count: 0,
  estimated_days_to_certification: 18,
  blocking_issues: [],
  last_updated: new Date().toISOString(),
};

// El layout project-scoped monta ProjectFeaturesProvider + ProjectHeader +
// ProjectTabs, que llaman /feature-flags y /header. Stubeamos ambas para que
// la página summary renderice de forma determinista (la spec original solo
// stubea /dashboard, dejando esas llamadas contra el backend real).
const LAYOUT_FEATURE_FLAGS = {
  categoria: "MEDIA",
  archetype: null,
  employee_count: null,
  features: {},
};

const LAYOUT_HEADER = {
  project: {
    id: "stub",
    nombre: "Proyecto E2E MB-13.2",
    fase: "implantacion",
    categoria_objetivo: "MEDIA",
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

test.describe("MB-13.2 · PhaseProgressWizard", () => {
  test.beforeEach(async ({ context, page }) => {
    await loginAsMarcos(context);
    await page.route(`**/api/v1/projects/*/feature-flags`, (route) =>
      route.fulfill({ status: 200, json: LAYOUT_FEATURE_FLAGS }),
    );
    await page.route(`**/api/v1/projects/*/header`, (route) =>
      route.fulfill({ status: 200, json: LAYOUT_HEADER }),
    );
    await page.route(
      `**/api/v1/projects/${PROJECT_ID}/dashboard`,
      async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(DASHBOARD_PHASE_5),
        });
      },
    );
  });

  test("stepper renderiza header + counter + 10 fases", async ({ page }) => {
    await page.goto(`/admin/projects/${PROJECT_ID}/summary`);

    const wizard = page.getByTestId("phase-progress-wizard");
    await expect(wizard).toBeVisible({ timeout: 10_000 });

    await expect(wizard.getByText(/Progreso del proyecto/)).toBeVisible();
    await expect(wizard.getByText(/Fase 6 de 10/)).toBeVisible();

    // 10 phases (short labels visibles)
    const items = wizard.getByRole("listitem");
    await expect(items).toHaveCount(10);
  });

  test("fase actual marcada con aria-current + future bloqueadas", async ({
    page,
  }) => {
    await page.goto(`/admin/projects/${PROJECT_ID}/summary`);

    const wizard = page.getByTestId("phase-progress-wizard");
    await expect(wizard).toBeVisible({ timeout: 10_000 });

    // Solo 1 step con aria-current="step"
    const currentSteps = wizard.locator('[aria-current="step"]');
    await expect(currentSteps).toHaveCount(1);

    // Steps con aria-disabled="true" (idx 6..9 = 4 futuras)
    const lockedSteps = wizard.locator('[aria-disabled="true"]');
    await expect(lockedSteps).toHaveCount(4);
  });

  test("tooltip muestra descripción de la fase al hover", async ({ page }) => {
    await page.goto(`/admin/projects/${PROJECT_ID}/summary`);

    const wizard = page.getByTestId("phase-progress-wizard");
    await expect(wizard).toBeVisible({ timeout: 10_000 });

    // Hover en step de Diagnostico (idx 2) · ya completed · clickable
    const diagStep = wizard
      .getByRole("link", { name: /Diagnóstico/i })
      .first();
    await diagStep.hover();

    // Tooltip aparece con descripción
    await expect(
      page.getByRole("tooltip").getByText(/maturity scoring/i),
    ).toBeVisible({ timeout: 3_000 });
  });
});
