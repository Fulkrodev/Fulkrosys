/**
 * P1 12 · /admin/projects/[id]/retainer · M23 retainer per-project.
 */
import { test } from "../_helpers/polish-test-fixture";
import { runProjectScopedProbe } from "../_helpers/spec-template";

test.describe("P1 · /admin/projects/[id]/retainer", () => {
  test("12-criteria empirical sweep", async ({ authedPage }, testInfo) => {
    await runProjectScopedProbe(authedPage, testInfo, {
      subPath: "retainer",
      pageName: "admin-project-retainer",
      contentText: "Retainer",
    });
  });
});
