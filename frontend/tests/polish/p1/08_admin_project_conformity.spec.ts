/**
 * P1 08 · /admin/projects/[id]/conformity · M27 declaración conformidad.
 *
 * Substitutes Marcos's listed "compliance" project-scoped route (doesn't
 * exist at /admin/projects/[id]/compliance · conformity IS project-level
 * compliance per project).
 */
import { test } from "../_helpers/polish-test-fixture";
import { runProjectScopedProbe } from "../_helpers/spec-template";

test.describe("P1 · /admin/projects/[id]/conformity", () => {
  test("12-criteria empirical sweep", async ({ authedPage }, testInfo) => {
    await runProjectScopedProbe(authedPage, testInfo, {
      subPath: "conformity",
      pageName: "admin-project-conformity",
      contentText: "Conformidad",
    });
  });
});
