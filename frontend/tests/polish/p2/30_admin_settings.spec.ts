/**
 * P2 30 · /admin/settings · admin settings.
 *
 * Sesión 3B-2B.3 Cluster C.5.
 */
import { test } from "../_helpers/polish-test-fixture";
import { runTopLevelAdminProbe } from "../_helpers/spec-template";

test.describe("P2 · /admin/settings", () => {
  test("12-criteria empirical sweep", async ({ authedPage }, testInfo) => {
    await runTopLevelAdminProbe(authedPage, testInfo, {
      path: "/admin/settings",
      pageName: "admin-settings",
    });
  });
});
