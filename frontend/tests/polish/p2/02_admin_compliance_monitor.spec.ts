/**
 * P2 02 · /admin/compliance/monitor · 19 compliance checks dashboard.
 */
import { test } from "../_helpers/polish-test-fixture";
import { runTopLevelAdminProbe } from "../_helpers/spec-template";

test.describe("P2 · /admin/compliance/monitor", () => {
  test("12-criteria empirical sweep", async ({ authedPage }, testInfo) => {
    await runTopLevelAdminProbe(authedPage, testInfo, {
      path: "/admin/compliance/monitor",
      pageName: "admin-compliance-monitor",
      contentText: "Monitor",
    });
  });
});
