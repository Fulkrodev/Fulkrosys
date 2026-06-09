/**
 * P2 18 · /admin/meetings/[id] · meeting detail.
 *
 * Sesión 3B-2B.3 Cluster C.3.
 * Uses POLISH_TEST_MEETING_ID env var (defaults to placeholder UUID).
 */
import { test } from "../_helpers/polish-test-fixture";
import { runTopLevelAdminProbe } from "../_helpers/spec-template";

const SEED_MEETING_ID =
  process.env.POLISH_TEST_MEETING_ID ??
  "11111111-1111-1111-1111-111111111111";

test.describe("P2 · /admin/meetings/[id]", () => {
  test("12-criteria empirical sweep", async ({ authedPage }, testInfo) => {
    await runTopLevelAdminProbe(authedPage, testInfo, {
      path: `/admin/meetings/${SEED_MEETING_ID}`,
      pageName: "admin-meetings-id",
    });
  });
});
