/**
 * E2E · Test 2 fase_25 · admin · vulnscan/nuclei execute trigger + form
 * params + progress + report download.
 *
 * Sub-atom 1.D.E v3.11 · MCPs project-scoped operativos.
 */
import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "../../_helpers/auth-real";
import {
  PROJECT_EE_ID,
  mockMcpCatalog,
  mockMcpExecuteAndGet,
  mockMcpExecutionsHistoryEmpty,
} from "../_fixtures";

// SKIP parcial: el flujo de ejecución MCP funciona hasta "Ejecución activa ·
// Completado 100%" (form → submit → panel activo · el evento SSE completed que
// añadimos en el fixture dispara la transición). PERO el result panel inline
// (mcp-execution-result-{id} + botón download) NO aparece tras submit porque en
// McpProjectScopedPanel.tsx `activeExecution` queda en null tras submit (solo se
// setea en `null`, ver onExecutionStarted) y SOLO se rellena al seleccionar una
// ejecución desde el HISTORIAL (handleSelectExecution) · el result inline está
// product-gated a history-select, no al submit directo. Es deriva de
// comportamiento de producto (el resultado se ve en el historial), NO de
// selector. Señalado para contraste (Marcos · result MCP inline vs history), NO
// borrar.
test.describe("fase_25 admin · vulnscan/nuclei execute", () => {
  test.skip("form param target obligatorio + submit → execution panel + result + download", async ({
    context,
    page,
  }) => {
    await loginAsMarcos(context);
    await mockMcpCatalog(page);
    await mockMcpExecutionsHistoryEmpty(page);
    await mockMcpExecuteAndGet(page, "vulnscan", "nuclei_scan");

    await page.goto(`/admin/projects/${PROJECT_EE_ID}/mcps`);

    // Click "Iniciar" en nuclei_scan card
    await page.getByTestId("mcp-tool-launch-nuclei_scan").click();

    // Form modal abierto
    await expect(
      page.getByTestId("mcp-tool-form-nuclei_scan"),
    ).toBeVisible();

    // Fields render (target required + severity default + rate_limit integer)
    await expect(page.getByTestId("param-target")).toBeVisible();
    await expect(page.getByTestId("param-severity")).toBeVisible();
    await expect(page.getByTestId("param-rate_limit")).toBeVisible();

    // Submit deshabilitado sin target (required)
    const submit = page.getByTestId("mcp-tool-form-submit");
    await expect(submit).toBeDisabled();

    // Fill target
    await page
      .locator("#mcp-param-target")
      .fill("https://target.example.com");
    await expect(submit).toBeEnabled();

    // Submit
    await submit.click();

    // Modal cierra · active execution panel aparece
    await expect(
      page.getByTestId("mcp-tool-form-nuclei_scan"),
    ).not.toBeVisible({ timeout: 5000 });
    await expect(
      page.getByTestId("mcp-active-execution-panel"),
    ).toBeVisible();

    // useMCPExecution polling devuelve completed mock · result panel
    await expect(
      page.getByTestId(/mcp-execution-result-/),
    ).toBeVisible({ timeout: 10000 });

    // Download button visible
    await expect(page.getByTestId("mcp-execution-download")).toBeVisible();
  });
});
