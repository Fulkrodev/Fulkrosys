/**
 * P1 11 · /admin/projects/[id]/personalizacion · branding admin.
 */
import { test } from "../_helpers/polish-test-fixture";
import { runProjectScopedProbe } from "../_helpers/spec-template";

test.describe("P1 · /admin/projects/[id]/personalizacion", () => {
  test("12-criteria empirical sweep", async ({ authedPage }, testInfo) => {
    await runProjectScopedProbe(authedPage, testInfo, {
      subPath: "personalizacion",
      pageName: "admin-project-personalizacion",
      contentText: "Personaliza",
    });
  });
});
