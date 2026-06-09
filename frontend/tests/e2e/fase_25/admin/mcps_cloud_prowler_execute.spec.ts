/**
 * E2E · Test 3 fase_25 · admin · cloud/prowler execute con enum
 * compliance_check (CIS/NIST/ISO/ENS).
 */
import { expect, test } from "@playwright/test";

import { loginAsMarcos } from "../../_helpers/auth-real";
import {
  PROJECT_EE_ID,
  mockMcpCatalog,
  mockMcpExecuteAndGet,
  mockMcpExecutionsHistoryEmpty,
} from "../_fixtures";

test.describe("fase_25 admin · cloud/prowler execute", () => {
  test("cambio family tab cloud · prowler form aws_account required + enum compliance_check", async ({
    context,
    page,
  }) => {
    await loginAsMarcos(context);
    await mockMcpCatalog(page);
    await mockMcpExecutionsHistoryEmpty(page);
    await mockMcpExecuteAndGet(page, "cloud", "prowler_scan");

    await page.goto(`/admin/projects/${PROJECT_EE_ID}/mcps`);

    // Switch to cloud tab
    await page.getByTestId("mcp-family-tab-cloud").click();

    // Prowler card visible
    await expect(
      page.getByTestId("mcp-tool-card-prowler_scan"),
    ).toBeVisible();

    // Launch
    await page.getByTestId("mcp-tool-launch-prowler_scan").click();
    await expect(
      page.getByTestId("mcp-tool-form-prowler_scan"),
    ).toBeVisible();

    // Fields: aws_account + compliance_check enum
    await expect(page.getByTestId("param-aws_account")).toBeVisible();
    await expect(page.getByTestId("param-compliance_check")).toBeVisible();

    // Fill aws_account
    await page.locator("#mcp-param-aws_account").fill("123456789012");

    // Submit
    await page.getByTestId("mcp-tool-form-submit").click();

    // Active execution panel aparece
    await expect(
      page.getByTestId("mcp-active-execution-panel"),
    ).toBeVisible();
  });
});
