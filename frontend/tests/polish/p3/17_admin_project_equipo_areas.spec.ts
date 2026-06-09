/**
 * P3 17 · /admin/projects/[id]/equipo/areas · departments sub-route.
 *
 * Sesión 3B-2B.3 Cluster D.3.
 */
import { test } from "../_helpers/polish-test-fixture";
import { runProjectScopedProbe } from "../_helpers/spec-template";

test.describe("P3 · /admin/projects/[id]/equipo/areas", () => {
  test("12-criteria empirical sweep", async ({ authedPage }, testInfo) => {
    await runProjectScopedProbe(authedPage, testInfo, {
      subPath: "equipo/areas",
      pageName: "admin-project-equipo-areas",
    });
  });
});
