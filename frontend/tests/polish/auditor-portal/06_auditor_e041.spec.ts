/**
 * AUDITOR-PORTAL 06 · /auditor-portal/{token}/e041 · 12-criteria empirical sweep.
 */
import { test } from "@playwright/test";
import { runAuditorPortalProbe } from "../_helpers/spec-template-auditor-portal";

test.describe("AUDITOR-PORTAL · /auditor-portal/{token}/e041", () => {
  test("12-criteria empirical sweep", async ({ page }, testInfo) => {
    await runAuditorPortalProbe(page, testInfo, {
      subPath: "e041",
      pageName: "auditor-portal-e041",
    });
  });
});
