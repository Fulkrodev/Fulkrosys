/**
 * P1 09 · /admin/projects/[id]/evidence · M07 evidence vault.
 *
 * Extra ENS MEDIA core workflow (added per Marcos Path A + extras directive).
 */
import { test } from "../_helpers/polish-test-fixture";
import { runProjectScopedProbe } from "../_helpers/spec-template";

test.describe("P1 · /admin/projects/[id]/evidence", () => {
  test("12-criteria empirical sweep", async ({ authedPage }, testInfo) => {
    await runProjectScopedProbe(authedPage, testInfo, {
      subPath: "evidence",
      pageName: "admin-project-evidence",
      contentText: "Evidencias",
    });
  });
});
