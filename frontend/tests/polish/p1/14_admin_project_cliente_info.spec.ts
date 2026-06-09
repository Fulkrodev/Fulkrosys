/**
 * P1 14 · /admin/projects/[id]/cliente-info · cliente entity per-project.
 *
 * Sesión 3B-2B.3 Phase X.4a · architectural migration target.
 * NEW project-scoped page absorbing "Datos cliente" tab from former
 * /admin/clients/[id] route (deleted by R23 strict cleanup).
 *
 * P1 priority · cliente entity datos are core admin daily-use per project.
 */
import { test } from "../_helpers/polish-test-fixture";
import { runProjectScopedProbe } from "../_helpers/spec-template";

test.describe("P1 · /admin/projects/[id]/cliente-info", () => {
  test("12-criteria empirical sweep", async ({ authedPage }, testInfo) => {
    await runProjectScopedProbe(authedPage, testInfo, {
      subPath: "cliente-info",
      pageName: "admin-project-cliente-info",
    });
  });
});
