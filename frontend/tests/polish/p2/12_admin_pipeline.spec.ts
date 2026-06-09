/**
 * P2 12 · /admin/pipeline · pre-sales pipeline list.
 *
 * Sesión 3B-2B.3 Cluster C.2.
 */
import { test } from "../_helpers/polish-test-fixture";
import { runTopLevelAdminProbe } from "../_helpers/spec-template";

test.describe("P2 · /admin/pipeline", () => {
  test("12-criteria empirical sweep", async ({ authedPage }, testInfo) => {
    await runTopLevelAdminProbe(authedPage, testInfo, {
      path: "/admin/pipeline",
      pageName: "admin-pipeline",
    });
  });
});
