/**
 * P2 14 · /admin/finance · billing/revenue aggregator.
 *
 * Sesión 3B-2B.3 Cluster C.2.
 */
import { test } from "../_helpers/polish-test-fixture";
import { runTopLevelAdminProbe } from "../_helpers/spec-template";

test.describe("P2 · /admin/finance", () => {
  test("12-criteria empirical sweep", async ({ authedPage }, testInfo) => {
    await runTopLevelAdminProbe(authedPage, testInfo, {
      path: "/admin/finance",
      pageName: "admin-finance",
    });
  });
});
