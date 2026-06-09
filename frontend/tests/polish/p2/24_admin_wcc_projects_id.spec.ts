/**
 * P2 24 · /admin/workflow-command-center/projects/[id] · WCC per-project.
 *
 * Sesión 3B-2B.3 Cluster C.4.
 * Uses SEED_PROJECT_ID via env (defaults to Cliente Test 1 project UUID).
 */
import { test } from "../_helpers/polish-test-fixture";
import { runTopLevelAdminProbe } from "../_helpers/spec-template";

const SEED_PROJECT_ID =
  process.env.POLISH_TEST_PROJECT_ID ??
  "11111111-1111-1111-1111-111111111111";

test.describe("P2 · /admin/workflow-command-center/projects/[id]", () => {
  test("12-criteria empirical sweep", async ({ authedPage }, testInfo) => {
    await runTopLevelAdminProbe(authedPage, testInfo, {
      path: `/admin/workflow-command-center/projects/${SEED_PROJECT_ID}`,
      pageName: "admin-wcc-projects-id",
    });
  });
});
