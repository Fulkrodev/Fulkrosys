/**
 * P3 20 · /admin/magerit-analyses/[id]/import · MAGERIT import flow.
 *
 * Sesión 3B-2B.3 Cluster D.4.
 * Uses POLISH_TEST_MAGERIT_ID env var (defaults to placeholder UUID).
 */
import { test } from "../_helpers/polish-test-fixture";
import { runTopLevelAdminProbe } from "../_helpers/spec-template";

const SEED_MAGERIT_ID =
  process.env.POLISH_TEST_MAGERIT_ID ??
  "11111111-1111-1111-1111-111111111111";

test.describe("P3 · /admin/magerit-analyses/[id]/import", () => {
  test("12-criteria empirical sweep", async ({ authedPage }, testInfo) => {
    await runTopLevelAdminProbe(authedPage, testInfo, {
      path: `/admin/magerit-analyses/${SEED_MAGERIT_ID}/import`,
      pageName: "admin-magerit-analyses-id-import",
    });
  });
});
