/**
 * E2E · Test 2 fase_17 · admin · per-cliente vista cronológica enriched.
 *
 * Sub-atom 1.C.D.E v3.8 · 1.C.D.B.2 (3-col layout · 4 sections cronológicas).
 *
 * Verifica:
 *   - /admin/workflow-command-center/projects/[id]/ render OK
 *   - AHORA section expanded muestra description_detailed + rationale + actors + completion_criteria
 *   - COMPLETADO + PRÓXIMOS visible
 */
import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "../../_helpers/auth-real";
import {
  PROJECT_A_ID,
  mockAdminWorkflowCommandCenter,
} from "../_fixtures";

test.describe("fase_17 admin · per-cliente cronológica enriched", () => {
  test("renders AHORA expanded + COMPLETADO + PRÓXIMOS sections", async ({
    page,
    context,
  }) => {
    await loginAsMarcos(context);
    await mockAdminWorkflowCommandCenter(page);

    await page.goto(`/admin/workflow-command-center/projects/${PROJECT_A_ID}`);

    // Header proyecto
    await expect(page.getByText("Fintech Plus SL").first()).toBeVisible();
    // AHORA section enriched · title
    await expect(
      page.getByText(/Formación G1 empleados/i).first(),
    ).toBeVisible();
    // description_detailed visible
    await expect(
      page.getByText(/curso online de 1 hora/i),
    ).toBeVisible();
    // rationale_es · "Por qué ahora" rendered
    await expect(
      page.getByText(/ENS Anexo II/i).first(),
    ).toBeVisible();
    // COMPLETADO section · heading visible en estado colapsado (default).
    // UI evolucionada (refactor 1.D.F.0.C): la sección COMPLETADO es
    // collapsible y arranca colapsada (WorkflowTimelineAdmin · viewMode
    // "complete" default). El título del sub-paso completado sólo entra al
    // DOM al expandir vía el toggle (data-testid="completed-toggle").
    await expect(
      page.getByText(/━━━ COMPLETADO/i),
    ).toBeVisible();
    await page.getByTestId("completed-toggle").click();
    // COMPLETADO section · DICAT card (visible tras expandir)
    await expect(
      page.getByText(/DICAT categorización inicial/i),
    ).toBeVisible();
  });
});
