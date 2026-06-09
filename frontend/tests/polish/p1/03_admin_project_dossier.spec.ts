/**
 * P1 03 · /admin/projects/[id]/dossier · M09 audit-prep dossier ENAC.
 */
import { test } from "../_helpers/polish-test-fixture";
import { runProjectScopedProbe } from "../_helpers/spec-template";

test.describe("P1 · /admin/projects/[id]/dossier", () => {
  test("12-criteria empirical sweep", async ({ authedPage }, testInfo) => {
    await runProjectScopedProbe(authedPage, testInfo, {
      subPath: "dossier",
      pageName: "admin-project-dossier",
      contentText: "Dossier",
    });
  });
});
