/**
 * Helper E2E Playwright · seed MAGERIT ALTA data para tests cliente firma.
 *
 * SAN-E v3.MB-5.4.D · drop-in pattern atom 5.3.D dda-seed.
 * Requires seedDdaAltaProject invocado primero (reusa test project + cliente).
 *
 * Usage:
 *
 *     import { seedDdaAltaProject } from "./_helpers/dda-seed";
 *     import { seedMageritAltaData } from "./_helpers/magerit-seed";
 *
 *     test.beforeEach(async ({ request }) => {
 *       await seedDdaAltaProject(request);  // crea client + project
 *       const magerit = await seedMageritAltaData(request);  // 8 assets + 12 risks
 *     });
 */
import type { APIRequestContext } from "@playwright/test";

const BACKEND_BASE =
  process.env.PLAYWRIGHT_BACKEND_URL ?? "http://localhost:8000";


export interface MageritAltaSeedResult {
  project_id: string;
  client_id: string;
  analysis_id: string;
  assets_count: number;
  risks_count: number;
  note: string;
}


export async function seedMageritAltaData(
  request: APIRequestContext,
): Promise<MageritAltaSeedResult> {
  const res = await request.post(
    `${BACKEND_BASE}/api/v1/_dev/seed-magerit-alta-data`,
  );
  if (!res.ok()) {
    throw new Error(
      `_dev/seed-magerit-alta-data devolvio ${res.status()}. Backend running?`,
    );
  }
  return (await res.json()) as MageritAltaSeedResult;
}
