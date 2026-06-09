/**
 * P1 01 · /admin/projects/[id]/archetype · M01 categorization preliminar.
 *
 * Sub-atom Sesión 3B-2B.2 Phase A.2 · substitutes Marcos's listed
 * "categorization" route (doesn't exist · archetype is M01 categorization).
 */
import { test } from "../_helpers/polish-test-fixture";
import { runProjectScopedProbe } from "../_helpers/spec-template";

test.describe("P1 · /admin/projects/[id]/archetype (M01 categorization)", () => {
  test("12-criteria empirical sweep", async ({ authedPage }, testInfo) => {
    await runProjectScopedProbe(authedPage, testInfo, {
      subPath: "archetype",
      pageName: "admin-project-archetype",
      contentText: "Arquetipo",
    });
  });
});
