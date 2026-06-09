/**
 * AUDITOR-PORTAL 03 · /auditor-portal/{token}/magerit · 12-criteria empirical sweep.
 */
import { test } from "@playwright/test";
import { runAuditorPortalProbe } from "../_helpers/spec-template-auditor-portal";

test.describe("AUDITOR-PORTAL · /auditor-portal/{token}/magerit", () => {
  test("12-criteria empirical sweep", async ({ page }, testInfo) => {
    await runAuditorPortalProbe(page, testInfo, {
      subPath: "magerit",
      pageName: "auditor-portal-magerit",
    });
  });
});
