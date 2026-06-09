/**
 * P1 06 · /admin/projects/[id]/contratos · M14 contracts + M28 changes.
 */
import { test } from "../_helpers/polish-test-fixture";
import { runProjectScopedProbe } from "../_helpers/spec-template";

test.describe("P1 · /admin/projects/[id]/contratos", () => {
  test("12-criteria empirical sweep", async ({ authedPage }, testInfo) => {
    await runProjectScopedProbe(authedPage, testInfo, {
      subPath: "contratos",
      pageName: "admin-project-contratos",
      contentText: "Contratos",
    });
  });
});
