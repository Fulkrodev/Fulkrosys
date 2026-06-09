/**
 * E2E · fase_31 admin · MEDIA cycle abbreviated · alternating chain (architect ampliación).
 *
 * Verifica:
 *  - Cadena 4 steps admin→cliente→admin→cliente alternating prereqs largos
 *  - Solo STEP1 in_progress · resto blocked cascading
 *  - blocker_reason correcto per cada link cadena
 *  - Pattern escala BASICA → MEDIA confidence sostener
 */
import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "../../_helpers/auth-real";
import { mockAdminWorkflowMediaChain, PROJECT_F31_ID } from "../_fixtures";

test.describe("fase_31 admin · MEDIA cycle abbreviated", () => {
  test("alternating chain admin↔cliente prereqs cascading", async ({
    context,
    page,
  }) => {
    await loginAsMarcos(context);
    await mockAdminWorkflowMediaChain(page);

    await page.goto(`/admin/workflow-command-center/projects/${PROJECT_F31_ID}`);
    await page.getByTestId("view-mode-blockers").click();

    // 4 steps en la cadena MEDIA
    await expect(page.getByTestId("blocker-card-STEP1_MARCOS")).toBeVisible();
    await expect(page.getByTestId("blocker-card-STEP2_CLIENTE")).toBeVisible();
    await expect(page.getByTestId("blocker-card-STEP3_MARCOS")).toBeVisible();
    await expect(page.getByTestId("blocker-card-STEP4_CLIENTE")).toBeVisible();

    // Blocker reason cascading correct per step
    await expect(
      page.getByTestId("blocker-reason-STEP2_CLIENTE"),
    ).toContainText("Esperando Marcos termine");
    await expect(
      page.getByTestId("blocker-reason-STEP3_MARCOS"),
    ).toContainText("1 pasos previos pendientes");
    await expect(
      page.getByTestId("blocker-reason-STEP4_CLIENTE"),
    ).toContainText("Esperando Marcos termine");
  });
});
