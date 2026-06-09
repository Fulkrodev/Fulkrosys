import { expect, test } from "@playwright/test";

/**
 * E2E /admin/projects/[id]/documents · LegalTemplatesPanel · SAN-C.MB-10.2.
 */

const TEST_PROJECT_ID = "00000000-0000-0000-0000-000000000000";

test("LegalTemplatesPanel · /documents tab no rompe SSR", async ({ page }) => {
  await page.goto(`/admin/projects/${TEST_PROJECT_ID}/documents`);
  const html = await page.content();
  expect(html).not.toMatch(/Application error/i);
  expect(html).not.toMatch(/Internal Server Error/i);
});
