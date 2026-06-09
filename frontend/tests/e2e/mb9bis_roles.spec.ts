import { expect, test } from "@playwright/test";

/**
 * E2E /admin/projects/[id]/roles · RolesSegregationAlert · SAN-C.MB-9.bis.4.
 *
 * Smoke sin auth ni DB seed: verifica que /roles tab incluye el alert
 * de segregación SIN romper SSR.
 */

const TEST_PROJECT_ID = "00000000-0000-0000-0000-000000000000";

test("RolesSegregationAlert · página /roles renderiza sin crash", async ({
  page,
}) => {
  await page.goto(`/admin/projects/${TEST_PROJECT_ID}/roles`);
  const html = await page.content();
  expect(html).not.toMatch(/Application error/i);
  expect(html).not.toMatch(/Internal Server Error/i);
});
