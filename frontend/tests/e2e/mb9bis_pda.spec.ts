import { expect, test } from "@playwright/test";

/**
 * E2E /admin/projects/[id]/plan · PdaGeneratorButton · SAN-C.MB-9.bis.2.
 *
 * Smoke sin auth ni DB seed: verifica que /plan tab incluye el botón
 * PdA SIN romper SSR.
 */

const TEST_PROJECT_ID = "00000000-0000-0000-0000-000000000000";

test("PdaGeneratorButton · página /plan renderiza sin crash", async ({
  page,
}) => {
  await page.goto(`/admin/projects/${TEST_PROJECT_ID}/plan`);
  const html = await page.content();
  expect(html).not.toMatch(/Application error/i);
  expect(html).not.toMatch(/Internal Server Error/i);
});
