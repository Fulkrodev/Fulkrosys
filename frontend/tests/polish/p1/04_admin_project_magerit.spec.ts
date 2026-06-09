/**
 * P1 04 · /admin/projects/[id]/magerit · M02 MAGERIT risk analysis.
 *
 * Extra ENS MEDIA core workflow (added per Marcos Path A + extras directive).
 */
import { test } from "../_helpers/polish-test-fixture";
import { runProjectScopedProbe } from "../_helpers/spec-template";

test.describe("P1 · /admin/projects/[id]/magerit", () => {
  test("12-criteria empirical sweep", async ({ authedPage }, testInfo) => {
    await runProjectScopedProbe(authedPage, testInfo, {
      subPath: "magerit",
      pageName: "admin-project-magerit",
      contentText: "MAGERIT",
    });
  });
});
