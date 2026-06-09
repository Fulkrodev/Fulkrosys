/**
 * P2 13 · /admin/pipeline/leads/[id] · lead drill-down.
 *
 * Sesión 3B-2B.3 Cluster C.2.
 * Uses POLISH_TEST_LEAD_ID env var (defaults to placeholder UUID · template
 * handles 404 / redirect gracefully via passCount floor).
 */
import { test } from "../_helpers/polish-test-fixture";
import { runTopLevelAdminProbe } from "../_helpers/spec-template";

const SEED_LEAD_ID =
  process.env.POLISH_TEST_LEAD_ID ??
  "11111111-1111-1111-1111-111111111111";

test.describe("P2 · /admin/pipeline/leads/[id]", () => {
  test("12-criteria empirical sweep", async ({ authedPage }, testInfo) => {
    await runTopLevelAdminProbe(authedPage, testInfo, {
      path: `/admin/pipeline/leads/${SEED_LEAD_ID}`,
      pageName: "admin-pipeline-leads-id",
    });
  });
});
