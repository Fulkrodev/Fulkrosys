/**
 * Helper E2E Playwright · seed DdA ALTA project para tests cliente firma.
 *
 * SAN-E v3.MB-5.3.D · idempotent · safe to call multiple times.
 *
 * Usage:
 *
 *     import { seedDdaAltaProject } from "./_helpers/dda-seed";
 *
 *     test.beforeEach(async ({ request }) => {
 *       const seed = await seedDdaAltaProject(request);
 *       // seed.project_id · seed.user_email · seed.user_password
 *     });
 *
 * Backend endpoint requerido (env-gated NO production):
 *   POST /api/v1/_dev/seed-dda-alta-project
 */
import type { APIRequestContext } from "@playwright/test";

const BACKEND_BASE =
  process.env.PLAYWRIGHT_BACKEND_URL ?? "http://localhost:8000";


export interface DdaAltaSeedResult {
  project_id: string;
  client_id: string;
  user_email: string;
  user_password: string;
  categoria_objetivo: string;
  dda_entries_count: number;
  pre_set_status: string;
  note: string;
}


/**
 * Tarea C · `key` opcional → CLIENT DEDICADO aislado (1 client + 1 project)
 * para que las specs conformidad/firma no compartan el único proyecto del
 * client global (race cross-spec → R27 LIMIT 1 resuelve el tier equivocado).
 * Omitir `key` = comportamiento legacy (client compartido `B00000000`).
 */
export async function seedDdaAltaProject(
  request: APIRequestContext,
  key?: string,
): Promise<DdaAltaSeedResult> {
  const qs = key ? `?key=${encodeURIComponent(key)}` : "";
  const res = await request.post(
    `${BACKEND_BASE}/api/v1/_dev/seed-dda-alta-project${qs}`,
  );
  if (!res.ok()) {
    throw new Error(
      `_dev/seed-dda-alta-project devolvio ${res.status()}. Backend running?`,
    );
  }
  return (await res.json()) as DdaAltaSeedResult;
}
