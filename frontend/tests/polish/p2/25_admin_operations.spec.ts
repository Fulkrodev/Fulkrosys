/**
 * P2 25 · /admin/operations · ops dashboard.
 *
 * Sesión 3B-2B.3 Cluster C.4.
 */
import { test } from "../_helpers/polish-test-fixture";
import { runTopLevelAdminProbe } from "../_helpers/spec-template";

test.describe("P2 · /admin/operations", () => {
  test("12-criteria empirical sweep", async ({ authedPage }, testInfo) => {
    await runTopLevelAdminProbe(authedPage, testInfo, {
      path: "/admin/operations",
      pageName: "admin-operations",
    });
  });
});
