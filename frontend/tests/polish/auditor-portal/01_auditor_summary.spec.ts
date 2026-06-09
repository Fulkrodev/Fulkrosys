/**
 * AUDITOR-PORTAL 01 · /auditor-portal/{token}/summary · 12-criteria empirical sweep.
 *
 * Sesión 3B-2B.6 CLUSTER 2 Phase 5.10 · auditor portal core polish scaffold.
 * SCAFFOLD mode · AUDITOR_PORTAL_TOKEN env var required at runtime.
 */
import { test } from "@playwright/test";
import { runAuditorPortalProbe } from "../_helpers/spec-template-auditor-portal";

test.describe("AUDITOR-PORTAL · /auditor-portal/{token}/summary", () => {
  test("12-criteria empirical sweep", async ({ page }, testInfo) => {
    await runAuditorPortalProbe(page, testInfo, {
      subPath: "summary",
      pageName: "auditor-portal-summary",
    });
  });
});
