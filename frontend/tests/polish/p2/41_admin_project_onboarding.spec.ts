/**
 * P2 41 · /admin/projects/[id]/onboarding · cliente onboarding step.
 *
 * Sesión 3B-2B.3 Cluster C.7.
 */
import { test } from "../_helpers/polish-test-fixture";
import { runProjectScopedProbe } from "../_helpers/spec-template";

test.describe("P2 · /admin/projects/[id]/onboarding", () => {
  test("12-criteria empirical sweep", async ({ authedPage }, testInfo) => {
    await runProjectScopedProbe(authedPage, testInfo, {
      subPath: "onboarding",
      pageName: "admin-project-onboarding",
    });
  });
});
