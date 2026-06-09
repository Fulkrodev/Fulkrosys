/**
 * P3 04 · /admin/projects/[id]/awareness · LMS workflow.
 *
 * Sesión 3B-2B.3 Cluster D.1.
 */
import { test } from "../_helpers/polish-test-fixture";
import { runProjectScopedProbe } from "../_helpers/spec-template";

test.describe("P3 · /admin/projects/[id]/awareness", () => {
  test("12-criteria empirical sweep", async ({ authedPage }, testInfo) => {
    await runProjectScopedProbe(authedPage, testInfo, {
      subPath: "awareness",
      pageName: "admin-project-awareness",
    });
  });
});
