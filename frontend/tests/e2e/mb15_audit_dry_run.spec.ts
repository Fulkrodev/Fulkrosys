/**
 * MB-15 · AuditDryRunDashboard stack real (loginAsMarcos existing).
 *
 * Verifica:
 *   - Sin ejecuciones previas: muestra hint + button "Ejecutar Dry-Run"
 *   - Con histórico: muestra última ejecución + score + gaps + últimos 5
 *   - Click ejecutar muestra spinner Loader2 (mock backend lento)
 *   - Resultado muestra M10 findings + GapAnalysisCard + A11 senior layer
 */
import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "./_helpers/auth-real";

const PROJECT_ID = "aaaa1111-2222-3333-4444-555555555555";

const SUMMARY_EMPTY = {
  last_executed_at: null,
  overall_readiness_score: 0,
  gaps_detected: 0,
  critical_gaps: 0,
  history: [],
};

const SUMMARY_WITH_HISTORY = {
  last_executed_at: "2026-05-01T10:00:00Z",
  overall_readiness_score: 75,
  gaps_detected: 8,
  critical_gaps: 2,
  history: [
    {
      id: "11111111-1111-1111-1111-111111111111",
      executed_at: "2026-05-01T10:00:00Z",
      score: 75,
      gaps: 8,
      critical_gaps: 2,
    },
    {
      id: "22222222-2222-2222-2222-222222222222",
      executed_at: "2026-04-15T10:00:00Z",
      score: 60,
      gaps: 12,
      critical_gaps: 3,
    },
  ],
};

const RESULT_PAYLOAD = {
  id: "33333333-3333-3333-3333-333333333333",
  project_id: PROJECT_ID,
  executed_at: new Date().toISOString(),
  m10_run_id: "44444444-4444-4444-4444-444444444444",
  category_at_execution: "MEDIA",
  archetype_at_execution: null,
  total_questions: 58,
  questions_with_evidence: 40,
  overall_readiness_score: 75,
  gaps_detected: 18,
  critical_gaps: 3,
  execution_time_ms: 35000,
  m10_summary: {
    run_id: "44444444-4444-4444-4444-444444444444",
    score_global: 75,
    nivel_madurez_global: "L3",
    conformes: 40,
    no_conformes_mayores: 3,
    no_conformes_menores: 15,
    observaciones: 0,
    no_aplica: 0,
    contradicciones_count: 0,
    findings: [
      {
        measure_code: "org.1.1",
        measure_name: "Política de seguridad",
        evaluacion: "conforme",
        nivel_madurez: "L4",
        contradiccion_detectada: false,
      },
      {
        measure_code: "op.acc.5",
        measure_name: "Mecanismos de autenticación",
        evaluacion: "no_conforme_mayor",
        nivel_madurez: "L0",
        contradiccion_detectada: false,
      },
    ],
  },
  a11_payload: {
    veredicto: "favorable_con_remediacion",
    probabilidad_certificacion_primera: 0.7,
    narrativa_md: "## Conclusión\n\nEl proyecto...",
    pac: [{ fase: 1, descripcion: "Reforzar autenticación" }],
    preguntas_contextuales: [],
  },
  model_used: "claude-opus-4-7",
};

// El layout project-scoped (app/(admin)/admin/projects/[id]/layout.tsx) llama
// /feature-flags + /header al montar ProjectFeaturesProvider/Header/Tabs. La
// spec original no las stubeaba (iban contra backend real). Las stubeamos para
// render determinista del AuditDryRunDashboard.
const LAYOUT_FEATURE_FLAGS = {
  categoria: "MEDIA",
  archetype: null,
  employee_count: null,
  features: {},
};

const LAYOUT_HEADER = {
  project: {
    id: "stub",
    nombre: "Proyecto E2E MB-15",
    fase: "verificacion",
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

test.describe("MB-15 · AuditDryRunDashboard stack real", () => {
  test.beforeEach(async ({ page }) => {
    await page.route(`**/api/v1/projects/*/feature-flags`, (route) =>
      route.fulfill({ status: 200, json: LAYOUT_FEATURE_FLAGS }),
    );
    await page.route(`**/api/v1/projects/*/header`, (route) =>
      route.fulfill({ status: 200, json: LAYOUT_HEADER }),
    );
  });

  test("sin ejecuciones previas · button visible · sin histórico", async ({
    page,
    context,
  }) => {
    await loginAsMarcos(context);
    await page.route(
      `**/api/v1/projects/${PROJECT_ID}/audit-dry-run/summary`,
      (route) => route.fulfill({ status: 200, json: SUMMARY_EMPTY }),
    );

    await page.goto(`/admin/projects/${PROJECT_ID}/audit-dry-run`);

    await expect(
      page.getByRole("button", { name: /Ejecutar Dry-Run/i }),
    ).toBeVisible();
    await expect(
      page.getByText(/M10 evalúa 58 preguntas ENAC/i),
    ).toBeVisible();
    await expect(page.getByText(/Sin ejecuciones previas/i)).toBeVisible();
    await expect(page.getByText(/Histórico/i)).toHaveCount(0);
  });

  test("con histórico · muestra última ejecución + score + 2 entries", async ({
    page,
    context,
  }) => {
    await loginAsMarcos(context);
    await page.route(
      `**/api/v1/projects/${PROJECT_ID}/audit-dry-run/summary`,
      (route) => route.fulfill({ status: 200, json: SUMMARY_WITH_HISTORY }),
    );

    await page.goto(`/admin/projects/${PROJECT_ID}/audit-dry-run`);

    await expect(page.getByText("Última ejecución:")).toBeVisible();
    await expect(page.getByText(/Score:/)).toBeVisible();
    await expect(page.getByText(/2 críticos/).first()).toBeVisible();
    await expect(page.getByText(/Histórico \(2\)/)).toBeVisible();
  });

  test("click ejecutar · muestra spinner Loader2 · resultado renderiza", async ({
    page,
    context,
  }) => {
    await loginAsMarcos(context);
    await page.route(
      `**/api/v1/projects/${PROJECT_ID}/audit-dry-run/summary`,
      (route) => route.fulfill({ status: 200, json: SUMMARY_EMPTY }),
    );

    let executeRequestSeen = false;
    await page.route(
      `**/api/v1/projects/${PROJECT_ID}/audit-dry-run/execute`,
      async (route) => {
        executeRequestSeen = true;
        await new Promise((r) => setTimeout(r, 800));
        await route.fulfill({ status: 200, json: RESULT_PAYLOAD });
      },
    );

    await page.goto(`/admin/projects/${PROJECT_ID}/audit-dry-run`);
    await page.getByRole("button", { name: /Ejecutar Dry-Run/i }).click();

    await expect(page.getByText(/Ejecutando dry-run/i)).toBeVisible();

    // Espera resultado. El título del resultado es "Dry-run <TooltipENS/>
    // completado · MEDIA" (AuditDryRunDashboard.tsx líneas 202-204): el
    // TooltipENS inyecta un botón-icono entre "Dry-run" y "completado", por lo
    // que NO existe un nodo de texto contiguo "Dry-run completado · MEDIA".
    // Aserto sobre el fragmento contiguo real "completado · MEDIA".
    await expect(
      page.getByText(/completado · MEDIA/i),
    ).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText(/75% madurez/i)).toBeVisible();
    await expect(page.getByText(/Gap analysis/i)).toBeVisible();
    await expect(page.getByText(/A11 senior layer/i)).toBeVisible();

    expect(executeRequestSeen).toBe(true);
  });

  test("M10 findings table muestra evaluación + maturity badges", async ({
    page,
    context,
  }) => {
    await loginAsMarcos(context);
    await page.route(
      `**/api/v1/projects/${PROJECT_ID}/audit-dry-run/summary`,
      (route) => route.fulfill({ status: 200, json: SUMMARY_EMPTY }),
    );
    await page.route(
      `**/api/v1/projects/${PROJECT_ID}/audit-dry-run/execute`,
      (route) => route.fulfill({ status: 200, json: RESULT_PAYLOAD }),
    );

    await page.goto(`/admin/projects/${PROJECT_ID}/audit-dry-run`);
    await page.getByRole("button", { name: /Ejecutar Dry-Run/i }).click();

    await expect(page.getByText(/Findings M10 \(2\)/i)).toBeVisible({
      timeout: 10_000,
    });
    // measure_codes pueden aparecer en GapAnalysisCard + M10FindingsTable
    await expect(page.getByText("org.1.1").first()).toBeVisible();
    await expect(page.getByText("op.acc.5").first()).toBeVisible();
    await expect(page.getByText("Conforme").first()).toBeVisible();
    await expect(page.getByText("NC mayor").first()).toBeVisible();
  });
});
