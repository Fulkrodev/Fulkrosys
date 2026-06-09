/**
 * AUDITOR-PORTAL 10 · annotations panel · 12-criteria empirical sweep.
 *
 * Annotations widget embedded en DdA + Evidence + MAGERIT views Phase C1.3.
 * SCAFFOLD mode · AUDITOR_PORTAL_TOKEN env var required at runtime.
 */
import { test } from "@playwright/test";
import { runAuditorPortalProbe } from "../_helpers/spec-template-auditor-portal";

test.describe("AUDITOR-PORTAL · annotations panel inline (DdA view sample)", () => {
  test("12-criteria empirical sweep", async ({ page }, testInfo) => {
    await runAuditorPortalProbe(page, testInfo, {
      subPath: "dda",
      pageName: "auditor-portal-annotations-panel",
    });
  });
});
