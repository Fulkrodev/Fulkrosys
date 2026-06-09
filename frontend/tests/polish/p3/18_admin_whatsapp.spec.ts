/**
 * P3 18 · /admin/whatsapp · whatsapp ops.
 *
 * Sesión 3B-2B.3 Cluster D.4.
 */
import { test } from "../_helpers/polish-test-fixture";
import { runTopLevelAdminProbe } from "../_helpers/spec-template";

test.describe("P3 · /admin/whatsapp", () => {
  test("12-criteria empirical sweep", async ({ authedPage }, testInfo) => {
    await runTopLevelAdminProbe(authedPage, testInfo, {
      path: "/admin/whatsapp",
      pageName: "admin-whatsapp",
    });
  });
});
