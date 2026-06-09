/**
 * P3 12 · /admin/projects/[id]/transparency · governance compliance.
 *
 * Sesión 3B-2B.3 Cluster D.2.
 */
import { test } from "../_helpers/polish-test-fixture";
import { runProjectScopedProbe } from "../_helpers/spec-template";

test.describe("P3 · /admin/projects/[id]/transparency", () => {
  test("12-criteria empirical sweep", async ({ authedPage }, testInfo) => {
    await runProjectScopedProbe(authedPage, testInfo, {
      subPath: "transparency",
      pageName: "admin-project-transparency",
    });
  });
});
