/**
 * P3 11 · /admin/projects/[id]/financial · per-project financial.
 *
 * Sesión 3B-2B.3 Cluster D.2.
 */
import { test } from "../_helpers/polish-test-fixture";
import { runProjectScopedProbe } from "../_helpers/spec-template";

test.describe("P3 · /admin/projects/[id]/financial", () => {
  test("12-criteria empirical sweep", async ({ authedPage }, testInfo) => {
    await runProjectScopedProbe(authedPage, testInfo, {
      subPath: "financial",
      pageName: "admin-project-financial",
    });
  });
});
