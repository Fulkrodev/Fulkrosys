/**
 * Helper E2E Playwright · seed conformidad ENS ready data tier-aware.
 *
 * SAN-E v3.MB-5.6.E · drop-in pattern atom 5.3.D + 5.4.D + 5.5.D.
 * Requires seedDdaAltaProject invocado primero (reusa test project + cliente).
 *
 * Tier-aware seed:
 * - BASICA (default) · 25 evidencias + chain firmas · declaration_type=initial
 * - MEDIA · 50 evidencias + chain firmas · declaration_type=commitment_pre_certification
 * - ALTA · 73 evidencias + 8 politicas firmadas + chain · declaration_type=commitment_pre_certification
 */
import type { APIRequestContext } from "@playwright/test";

const BACKEND_BASE =
  process.env.PLAYWRIGHT_BACKEND_URL ?? "http://localhost:8000";


export type ConformidadTier = "BASICA" | "MEDIA" | "ALTA";


export interface ConformidadReadySeedResult {
  project_id: string;
  client_id: string;
  declaration_id: string;
  tier: ConformidadTier;
  chain_signed: Record<string, string>;
  evidence_count: number;
  policies_signed_count: number;
  note: string;
}


/**
 * Tarea C · `key` opcional → CLIENT DEDICADO aislado (mismo `key` que el
 * seedDdaAltaProject del spec) para que R27 LIMIT 1 resuelva el proyecto del
 * tier correcto sin race cross-spec. Omitir `key` = legacy compartido.
 */
export async function seedConformidadReady(
  request: APIRequestContext,
  tier: ConformidadTier = "BASICA",
  key?: string,
): Promise<ConformidadReadySeedResult> {
  const keyQs = key ? `&key=${encodeURIComponent(key)}` : "";
  const res = await request.post(
    `${BACKEND_BASE}/api/v1/_dev/seed-conformidad-ready?tier=${tier}${keyQs}`,
  );
  if (!res.ok()) {
    throw new Error(
      `_dev/seed-conformidad-ready devolvio ${res.status()}. Backend running?`,
    );
  }
  return (await res.json()) as ConformidadReadySeedResult;
}
