/**
 * P3 14 · /admin/projects/[id]/renewal · renewal cycle.
 *
 * Sesión 3B-2B.3 Cluster D.3.
 */
import { test } from "../_helpers/polish-test-fixture";
import { runProjectScopedProbe } from "../_helpers/spec-template";

test.describe("P3 · /admin/projects/[id]/renewal", () => {
  test("12-criteria empirical sweep", async ({ authedPage }, testInfo) => {
    await runProjectScopedProbe(authedPage, testInfo, {
      subPath: "renewal",
      pageName: "admin-project-renewal",
    });
  });
});
