/**
 * AUDITOR-PORTAL 11 · /audit/dda-evidence-gaps heatmap · 12-criteria empirical sweep.
 *
 * Phase C3.3 heatmap UI · 73 medidas + drawer drill-down + clarification embed.
 */
import { test } from "@playwright/test";
import { runAuditorPortalProbe } from "../_helpers/spec-template-auditor-portal";

test.describe("AUDITOR-PORTAL · /audit/dda-evidence-gaps heatmap", () => {
  test("12-criteria empirical sweep", async ({ page }, testInfo) => {
    await runAuditorPortalProbe(page, testInfo, {
      subPath: "audit/dda-evidence-gaps",
      pageName: "auditor-portal-dda-evidence-gaps",
    });
  });
});
