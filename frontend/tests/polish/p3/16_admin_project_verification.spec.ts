/**
 * P3 16 · /admin/projects/[id]/verification · post-action verify.
 *
 * Sesión 3B-2B.3 Cluster D.3.
 */
import { test } from "../_helpers/polish-test-fixture";
import { runProjectScopedProbe } from "../_helpers/spec-template";

test.describe("P3 · /admin/projects/[id]/verification", () => {
  test("12-criteria empirical sweep", async ({ authedPage }, testInfo) => {
    await runProjectScopedProbe(authedPage, testInfo, {
      subPath: "verification",
      pageName: "admin-project-verification",
    });
  });
});
