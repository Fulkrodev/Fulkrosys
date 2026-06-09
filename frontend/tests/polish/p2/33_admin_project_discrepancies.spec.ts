/**
 * P2 33 · /admin/projects/[id]/discrepancies · A21 quality control.
 *
 * Sesión 3B-2B.3 Cluster C.6.
 */
import { test } from "../_helpers/polish-test-fixture";
import { runProjectScopedProbe } from "../_helpers/spec-template";

test.describe("P2 · /admin/projects/[id]/discrepancies", () => {
  test("12-criteria empirical sweep", async ({ authedPage }, testInfo) => {
    await runProjectScopedProbe(authedPage, testInfo, {
      subPath: "discrepancies",
      pageName: "admin-project-discrepancies",
    });
  });
});
