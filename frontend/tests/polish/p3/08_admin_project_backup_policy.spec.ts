/**
 * P3 08 · /admin/projects/[id]/backup-policy · M26 backup.
 *
 * Sesión 3B-2B.3 Cluster D.2.
 */
import { test } from "../_helpers/polish-test-fixture";
import { runProjectScopedProbe } from "../_helpers/spec-template";

test.describe("P3 · /admin/projects/[id]/backup-policy", () => {
  test("12-criteria empirical sweep", async ({ authedPage }, testInfo) => {
    await runProjectScopedProbe(authedPage, testInfo, {
      subPath: "backup-policy",
      pageName: "admin-project-backup-policy",
    });
  });
});
