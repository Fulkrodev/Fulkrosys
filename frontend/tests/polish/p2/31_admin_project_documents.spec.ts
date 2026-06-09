/**
 * P2 31 · /admin/projects/[id]/documents · M24 IDMS daily.
 *
 * Sesión 3B-2B.3 Cluster C.6.
 */
import { test } from "../_helpers/polish-test-fixture";
import { runProjectScopedProbe } from "../_helpers/spec-template";

test.describe("P2 · /admin/projects/[id]/documents", () => {
  test("12-criteria empirical sweep", async ({ authedPage }, testInfo) => {
    await runProjectScopedProbe(authedPage, testInfo, {
      subPath: "documents",
      pageName: "admin-project-documents",
    });
  });
});
