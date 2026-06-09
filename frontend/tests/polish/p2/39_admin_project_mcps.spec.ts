/**
 * P2 39 · /admin/projects/[id]/mcps · pentest MCPs (1.D.E).
 *
 * Sesión 3B-2B.3 Cluster C.7.
 */
import { test } from "../_helpers/polish-test-fixture";
import { runProjectScopedProbe } from "../_helpers/spec-template";

test.describe("P2 · /admin/projects/[id]/mcps", () => {
  test("12-criteria empirical sweep", async ({ authedPage }, testInfo) => {
    await runProjectScopedProbe(authedPage, testInfo, {
      subPath: "mcps",
      pageName: "admin-project-mcps",
    });
  });
});
