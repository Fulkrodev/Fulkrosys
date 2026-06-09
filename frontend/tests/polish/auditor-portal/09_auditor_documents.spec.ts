/**
 * AUDITOR-PORTAL 09 · /auditor-portal/{token}/documents · 12-criteria empirical sweep.
 */
import { test } from "@playwright/test";
import { runAuditorPortalProbe } from "../_helpers/spec-template-auditor-portal";

test.describe("AUDITOR-PORTAL · /auditor-portal/{token}/documents", () => {
  test("12-criteria empirical sweep", async ({ page }, testInfo) => {
    await runAuditorPortalProbe(page, testInfo, {
      subPath: "documents",
      pageName: "auditor-portal-documents",
    });
  });
});
