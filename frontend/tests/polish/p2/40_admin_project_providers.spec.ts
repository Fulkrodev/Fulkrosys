/**
 * P2 40 · /admin/projects/[id]/providers · supply chain (1.D.I).
 *
 * Sesión 3B-2B.3 Cluster C.7.
 */
import { test } from "../_helpers/polish-test-fixture";
import { runProjectScopedProbe } from "../_helpers/spec-template";

test.describe("P2 · /admin/projects/[id]/providers", () => {
  test("12-criteria empirical sweep", async ({ authedPage }, testInfo) => {
    await runProjectScopedProbe(authedPage, testInfo, {
      subPath: "providers",
      pageName: "admin-project-providers",
    });
  });
});
