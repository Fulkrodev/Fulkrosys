/**
 * P2 27 · /admin/system-health · FULKRO self-monitoring.
 *
 * Sesión 3B-2B.3 Cluster C.5.
 */
import { test } from "../_helpers/polish-test-fixture";
import { runTopLevelAdminProbe } from "../_helpers/spec-template";

test.describe("P2 · /admin/system-health", () => {
  test("12-criteria empirical sweep", async ({ authedPage }, testInfo) => {
    await runTopLevelAdminProbe(authedPage, testInfo, {
      path: "/admin/system-health",
      pageName: "admin-system-health",
    });
  });
});
