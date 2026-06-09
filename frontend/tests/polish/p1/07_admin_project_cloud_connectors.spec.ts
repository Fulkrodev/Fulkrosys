/**
 * P1 07 · /admin/projects/[id]/cloud-connectors · M_cloud_connectors.
 */
import { test } from "../_helpers/polish-test-fixture";
import { runProjectScopedProbe } from "../_helpers/spec-template";

test.describe("P1 · /admin/projects/[id]/cloud-connectors", () => {
  test("12-criteria empirical sweep", async ({ authedPage }, testInfo) => {
    await runProjectScopedProbe(authedPage, testInfo, {
      subPath: "cloud-connectors",
      pageName: "admin-project-cloud-connectors",
      contentText: "Conexiones",
    });
  });
});
