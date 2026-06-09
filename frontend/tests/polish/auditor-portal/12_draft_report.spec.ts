/**
 * AUDITOR-PORTAL 12 · /draft-report preview + generate · 12-criteria empirical sweep.
 *
 * Phase C4.3 UI · iframe preview + signed PDF download CTA + opinion form.
 */
import { test } from "@playwright/test";
import { runAuditorPortalProbe } from "../_helpers/spec-template-auditor-portal";

test.describe("AUDITOR-PORTAL · /draft-report preview + generate", () => {
  test("12-criteria empirical sweep", async ({ page }, testInfo) => {
    await runAuditorPortalProbe(page, testInfo, {
      subPath: "draft-report",
      pageName: "auditor-portal-draft-report",
    });
  });
});
