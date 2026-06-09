/**
 * E2E · Test 5 fase_25 · admin · Evidence Vault auto-attach verify.
 *
 * Sub-atom 1.D.E v3.11 · backend auto-attach al IDMS folder
 * "13_Informes_Tecnicos" (clasificación informe · STANDARD_FOLDERS code
 * "13"). Briefing nomenclature "K.6 Pentest" se refiere a WBS phase
 * m17_planning · NO a folder IDMS · adaptación audit-first.
 */
import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "../../_helpers/auth-real";
import {
  EVIDENCE_DOC_ID,
  PROJECT_EE_ID,
  mockMcpCatalog,
  mockMcpExecuteAndGet,
  mockMcpExecutionsHistoryWithItem,
} from "../_fixtures";

test.describe("fase_25 admin · Evidence Vault auto-attach", () => {
  test("execution completed con evidence_document_id render link IDMS + folder 13_Informes_Tecnicos mention", async ({
    context,
    page,
  }) => {
    await loginAsMarcos(context);
    await mockMcpCatalog(page);
    await mockMcpExecutionsHistoryWithItem(page);
    await mockMcpExecuteAndGet(page, "vulnscan", "nuclei_scan");

    await page.goto(`/admin/projects/${PROJECT_EE_ID}/mcps`);

    // Historial muestra ejecución completed
    await expect(page.getByTestId("mcp-executions-history")).toBeVisible();
    await expect(
      page.getByTestId(/mcp-history-row-/).first(),
    ).toBeVisible();

    // Click en la ejecución del historial · abre active panel con result
    await page.getByTestId(/mcp-history-row-/).first().click();

    // Active execution panel + result rendered
    await expect(
      page.getByTestId("mcp-active-execution-panel"),
    ).toBeVisible({ timeout: 10000 });

    // Evidence alert con mención folder 13_Informes_Tecnicos
    const evidence = page.getByTestId("mcp-execution-evidence");
    await expect(evidence).toBeVisible();
    await expect(evidence).toContainText("13_Informes_Tecnicos");
    await expect(evidence).toContainText(EVIDENCE_DOC_ID.slice(0, 12));

    // Link IDMS visible
    await expect(
      page.getByTestId("mcp-execution-evidence-link"),
    ).toBeVisible();
  });
});
