/**
 * P1 02 · /admin/projects/[id]/risks · M19 risk dashboard.
 */
import { test } from "../_helpers/polish-test-fixture";
import { runProjectScopedProbe } from "../_helpers/spec-template";

test.describe("P1 · /admin/projects/[id]/risks", () => {
  test("12-criteria empirical sweep", async ({ authedPage }, testInfo) => {
    await runProjectScopedProbe(authedPage, testInfo, {
      subPath: "risks",
      pageName: "admin-project-risks",
      contentText: "Riesgos",
    });
  });
});
