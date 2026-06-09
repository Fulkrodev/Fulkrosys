/**
 * AUDITOR-PORTAL 04 · /auditor-portal/{token}/plan · 12-criteria empirical sweep.
 */
import { test } from "@playwright/test";
import { runAuditorPortalProbe } from "../_helpers/spec-template-auditor-portal";

test.describe("AUDITOR-PORTAL · /auditor-portal/{token}/plan", () => {
  test("12-criteria empirical sweep", async ({ page }, testInfo) => {
    await runAuditorPortalProbe(page, testInfo, {
      subPath: "plan",
      pageName: "auditor-portal-plan",
    });
  });
});
