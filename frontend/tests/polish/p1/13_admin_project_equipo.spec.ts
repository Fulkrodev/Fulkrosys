/**
 * P1 13 · /admin/projects/[id]/equipo · team + roles ENS.
 */
import { test } from "../_helpers/polish-test-fixture";
import { runProjectScopedProbe } from "../_helpers/spec-template";

test.describe("P1 · /admin/projects/[id]/equipo", () => {
  test("12-criteria empirical sweep", async ({ authedPage }, testInfo) => {
    await runProjectScopedProbe(authedPage, testInfo, {
      subPath: "equipo",
      pageName: "admin-project-equipo",
      contentText: "Equipo",
    });
  });
});
