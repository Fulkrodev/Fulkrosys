/**
 * E2E · Test 4 fase_25 · admin · phishing/gophish simulacro con risk
 * level high badge + dual required params (campaign_name + target_users).
 */
import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "../../_helpers/auth-real";
import {
  PROJECT_EE_ID,
  mockMcpCatalog,
  mockMcpExecuteAndGet,
  mockMcpExecutionsHistoryEmpty,
} from "../_fixtures";

test.describe("fase_25 admin · phishing/gophish simulacro", () => {
  test("phishing tab · gophish risk=high badge + dual required params", async ({
    context,
    page,
  }) => {
    await loginAsMarcos(context);
    await mockMcpCatalog(page);
    await mockMcpExecutionsHistoryEmpty(page);
    await mockMcpExecuteAndGet(page, "phishing", "gophish_campaign");

    await page.goto(`/admin/projects/${PROJECT_EE_ID}/mcps`);

    // Switch to phishing tab
    await page.getByTestId("mcp-family-tab-phishing").click();

    // GoPhish card visible
    await expect(
      page.getByTestId("mcp-tool-card-gophish_campaign"),
    ).toBeVisible();

    // Launch form
    await page.getByTestId("mcp-tool-launch-gophish_campaign").click();
    await expect(
      page.getByTestId("mcp-tool-form-gophish_campaign"),
    ).toBeVisible();

    // Required fields
    await expect(page.getByTestId("param-campaign_name")).toBeVisible();
    await expect(page.getByTestId("param-target_users")).toBeVisible();

    // Submit disabled sin required
    const submit = page.getByTestId("mcp-tool-form-submit");
    await expect(submit).toBeDisabled();

    // Fill ambos required
    await page
      .locator("#mcp-param-campaign_name")
      .fill("Q2 2026 awareness");
    await page
      .locator("#mcp-param-target_users")
      .fill("u1@empresa.es,u2@empresa.es");

    await expect(submit).toBeEnabled();
    await submit.click();

    await expect(
      page.getByTestId("mcp-active-execution-panel"),
    ).toBeVisible();
  });
});
