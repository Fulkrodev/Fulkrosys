/**
 * AUDITOR-PORTAL 05 · /auditor-portal/{token}/evidence · 12-criteria empirical sweep.
 */
import { test } from "@playwright/test";
import { runAuditorPortalProbe } from "../_helpers/spec-template-auditor-portal";

test.describe("AUDITOR-PORTAL · /auditor-portal/{token}/evidence", () => {
  test("12-criteria empirical sweep", async ({ page }, testInfo) => {
    await runAuditorPortalProbe(page, testInfo, {
      subPath: "evidence",
      pageName: "auditor-portal-evidence",
    });
  });
});
