/**
 * P2 16 · /admin/meetings · cross-cliente calendar.
 *
 * Sesión 3B-2B.3 Cluster C.3.
 */
import { test } from "../_helpers/polish-test-fixture";
import { runTopLevelAdminProbe } from "../_helpers/spec-template";

test.describe("P2 · /admin/meetings", () => {
  test("12-criteria empirical sweep", async ({ authedPage }, testInfo) => {
    await runTopLevelAdminProbe(authedPage, testInfo, {
      path: "/admin/meetings",
      pageName: "admin-meetings",
    });
  });
});
