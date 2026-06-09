/**
 * P2 32 · /admin/projects/[id]/changes · M28 change governance.
 *
 * Sesión 3B-2B.3 Cluster C.6.
 */
import { test } from "../_helpers/polish-test-fixture";
import { runProjectScopedProbe } from "../_helpers/spec-template";

test.describe("P2 · /admin/projects/[id]/changes", () => {
  test("12-criteria empirical sweep", async ({ authedPage }, testInfo) => {
    await runProjectScopedProbe(authedPage, testInfo, {
      subPath: "changes",
      pageName: "admin-project-changes",
    });
  });
});
