import { expect, test } from "@playwright/test";

/**
 * E2E /admin/projects/[id]/documents · RectoresGeneratorPanel · SAN-C.MB-9.bis.3.
 *
 * Smoke sin auth ni DB seed: verifica que /documents tab incluye el
 * panel rectores SIN romper SSR.
 */

const TEST_PROJECT_ID = "00000000-0000-0000-0000-000000000000";

test("RectoresGeneratorPanel · página /documents renderiza sin crash", async ({
  page,
}) => {
  await page.goto(`/admin/projects/${TEST_PROJECT_ID}/documents`);
  const html = await page.content();
  expect(html).not.toMatch(/Application error/i);
  expect(html).not.toMatch(/Internal Server Error/i);
});
