/**
 * AUDITOR-PORTAL 07 · /auditor-portal/{token}/audit-log · 12-criteria empirical sweep.
 */
import { test } from "@playwright/test";
import { runAuditorPortalProbe } from "../_helpers/spec-template-auditor-portal";

test.describe("AUDITOR-PORTAL · /auditor-portal/{token}/audit-log", () => {
  test("12-criteria empirical sweep", async ({ page }, testInfo) => {
    await runAuditorPortalProbe(page, testInfo, {
      subPath: "audit-log",
      pageName: "auditor-portal-audit-log",
    });
  });
});
