/**
 * P3 13 · /admin/projects/[id]/roles · ENS roles assignment.
 *
 * Sesión 3B-2B.3 Cluster D.3.
 */
import { test } from "../_helpers/polish-test-fixture";
import { runProjectScopedProbe } from "../_helpers/spec-template";

test.describe("P3 · /admin/projects/[id]/roles", () => {
  test("12-criteria empirical sweep", async ({ authedPage }, testInfo) => {
    await runProjectScopedProbe(authedPage, testInfo, {
      subPath: "roles",
      pageName: "admin-project-roles",
    });
  });
});
