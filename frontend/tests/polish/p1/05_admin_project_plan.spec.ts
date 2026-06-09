/**
 * P1 05 · /admin/projects/[id]/plan · M04 plan adecuación ENS.
 *
 * Extra ENS MEDIA core workflow (added per Marcos Path A + extras directive).
 */
import { test } from "../_helpers/polish-test-fixture";
import { runProjectScopedProbe } from "../_helpers/spec-template";

test.describe("P1 · /admin/projects/[id]/plan", () => {
  test("12-criteria empirical sweep", async ({ authedPage }, testInfo) => {
    await runProjectScopedProbe(authedPage, testInfo, {
      subPath: "plan",
      pageName: "admin-project-plan",
      contentText: "Plan",
    });
  });
});
