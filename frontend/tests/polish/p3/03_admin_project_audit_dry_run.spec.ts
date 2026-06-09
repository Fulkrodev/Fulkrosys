/**
 * P3 03 · /admin/projects/[id]/audit-dry-run · ENS audit dry-run (A11).
 *
 * Sesión 3B-2B.3 Cluster D.1.
 */
import { test } from "../_helpers/polish-test-fixture";
import { runProjectScopedProbe } from "../_helpers/spec-template";

test.describe("P3 · /admin/projects/[id]/audit-dry-run", () => {
  test("12-criteria empirical sweep", async ({ authedPage }, testInfo) => {
    await runProjectScopedProbe(authedPage, testInfo, {
      subPath: "audit-dry-run",
      pageName: "admin-project-audit-dry-run",
    });
  });
});
