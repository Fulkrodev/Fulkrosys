/**
 * P2 17 · /admin/meetings/new · create meeting form.
 *
 * Sesión 3B-2B.3 Cluster C.3.
 */
import { test } from "../_helpers/polish-test-fixture";
import { runTopLevelAdminProbe } from "../_helpers/spec-template";

test.describe("P2 · /admin/meetings/new", () => {
  test("12-criteria empirical sweep", async ({ authedPage }, testInfo) => {
    await runTopLevelAdminProbe(authedPage, testInfo, {
      path: "/admin/meetings/new",
      pageName: "admin-meetings-new",
    });
  });
});
