/**
 * P2 03 · /admin/compliance/norma-reports · multi-norma compliance reports.
 */
import { test } from "../_helpers/polish-test-fixture";
import { runTopLevelAdminProbe } from "../_helpers/spec-template";

test.describe("P2 · /admin/compliance/norma-reports", () => {
  test("12-criteria empirical sweep", async ({ authedPage }, testInfo) => {
    await runTopLevelAdminProbe(authedPage, testInfo, {
      path: "/admin/compliance/norma-reports",
      pageName: "admin-compliance-norma-reports",
      contentText: "Norma",
    });
  });
});
