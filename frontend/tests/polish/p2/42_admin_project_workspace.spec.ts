/**
 * P2 42 · /admin/projects/[id]/workspace · daily project entry.
 *
 * Sesión 3B-2B.3 Cluster C.7.
 */
import { test } from "../_helpers/polish-test-fixture";
import { runProjectScopedProbe } from "../_helpers/spec-template";

test.describe("P2 · /admin/projects/[id]/workspace", () => {
  test("12-criteria empirical sweep", async ({ authedPage }, testInfo) => {
    await runProjectScopedProbe(authedPage, testInfo, {
      subPath: "workspace",
      pageName: "admin-project-workspace",
    });
  });
});
