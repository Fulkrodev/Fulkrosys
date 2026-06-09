/**
 * E2E · Test 1 fase_25 · admin · MCPs project-scoped render + tabs + NO
 * sidebar global verify.
 *
 * Sub-atom 1.D.E v3.11 · R23 sostener firmísimo (directiva Marcos):
 *   - Page /admin/projects/{id}/mcps renderiza panel + 4 family tabs +
 *     13 tools cards (vulnscan 4 + cloud 4 + config 4 + phishing 1)
 *   - /admin/mcps global redirect/404 (page eliminada)
 *   - Sidebar global NO contiene entry "MCPs"
 */
import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "../../_helpers/auth-real";
import {
  PROJECT_EE_ID,
  mockMcpCatalog,
  mockMcpExecutionsHistoryEmpty,
} from "../_fixtures";

test.describe("fase_25 admin · MCPs project-scoped render", () => {
  test("4 family tabs + 13 tools + sidebar NO MCPs + project-scoped only", async ({
    context,
    page,
  }) => {
    await loginAsMarcos(context);
    await mockMcpCatalog(page);
    await mockMcpExecutionsHistoryEmpty(page);

    await page.goto(`/admin/projects/${PROJECT_EE_ID}/mcps`);

    // Panel principal render
    await expect(
      page.getByTestId("mcp-project-scoped-panel"),
    ).toBeVisible();

    // 4 family tabs
    await expect(page.getByTestId("mcp-family-tabs")).toBeVisible();
    await expect(
      page.getByTestId("mcp-family-tab-vulnscan"),
    ).toBeVisible();
    await expect(page.getByTestId("mcp-family-tab-cloud")).toBeVisible();
    await expect(page.getByTestId("mcp-family-tab-config")).toBeVisible();
    await expect(
      page.getByTestId("mcp-family-tab-phishing"),
    ).toBeVisible();

    // Tab vulnscan activa por default · 4 tools cards
    await expect(
      page.getByTestId("mcp-tool-card-nuclei_scan"),
    ).toBeVisible();
    await expect(
      page.getByTestId("mcp-tool-card-openvas_scan"),
    ).toBeVisible();
    await expect(
      page.getByTestId("mcp-tool-card-trivy_scan"),
    ).toBeVisible();
    await expect(
      page.getByTestId("mcp-tool-card-grype_sbom_scan"),
    ).toBeVisible();

    // History render (empty state)
    await expect(page.getByTestId("mcp-executions-history")).toBeVisible();

    // Sidebar NO contiene MCPs (R23 directiva firmísima)
    const sidebarMcps = page.locator("aside").getByText("MCPs", {
      exact: true,
    });
    await expect(sidebarMcps).toHaveCount(0);
  });
});
