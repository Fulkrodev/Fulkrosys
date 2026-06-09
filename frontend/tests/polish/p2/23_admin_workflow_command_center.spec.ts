/**
 * P2 23 · /admin/workflow-command-center · WCC cross-cliente.
 *
 * Sesión 3B-2B.3 Cluster C.4.
 */
import { test } from "../_helpers/polish-test-fixture";
import { runTopLevelAdminProbe } from "../_helpers/spec-template";

test.describe("P2 · /admin/workflow-command-center", () => {
  test("12-criteria empirical sweep", async ({ authedPage }, testInfo) => {
    await runTopLevelAdminProbe(authedPage, testInfo, {
      path: "/admin/workflow-command-center",
      pageName: "admin-workflow-command-center",
    });
  });
});
