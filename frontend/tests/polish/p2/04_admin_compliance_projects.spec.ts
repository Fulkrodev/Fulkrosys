/**
 * P2 04 · /admin/compliance/projects · cross-project compliance KPI aggregator.
 */
import { test } from "../_helpers/polish-test-fixture";
import { runTopLevelAdminProbe } from "../_helpers/spec-template";

test.describe("P2 · /admin/compliance/projects", () => {
  test("12-criteria empirical sweep", async ({ authedPage }, testInfo) => {
    await runTopLevelAdminProbe(authedPage, testInfo, {
      path: "/admin/compliance/projects",
      pageName: "admin-compliance-projects",
      contentText: "Proyectos",
    });
  });
});
