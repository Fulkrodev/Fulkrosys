/**
 * API client wrapper · Magic Links.
 *
 * Cubre los 5 endpoints del backend M12:
 *   GET    /api/v1/magic-links                  · admin list filtered
 *   POST   /api/v1/magic-links/generate         · admin generate
 *   GET    /api/v1/magic-links/by-token/{token} · público status
 *   POST   /api/v1/magic-links/consume          · público consume
 *   POST   /api/v1/magic-links/{id}/revoke      · admin revoke
 *
 * Usa el fetch wrapper compartido (`api`) de @/lib/api con CSRF + cookies.
 */
import { api } from "@/lib/api";
import type {
  ConsumeMagicLinkRequest,
  ConsumeMagicLinkResponse,
  GenerateAndSendMagicLinkResponse,
  GenerateMagicLinkRequest,
  MagicLinkBackendPurpose,
  MagicLinkRecord,
  MagicLinkStatus,
} from "@/lib/magic-link-types";

const BASE = "/api/v1/magic-links";

export interface ListMagicLinksParams {
  project_id?: string;
  purpose?: MagicLinkBackendPurpose;
  active_only?: boolean;
  limit?: number;
}

function toQuery(params: ListMagicLinksParams): string {
  const sp = new URLSearchParams();
  if (params.project_id) sp.set("project_id", params.project_id);
  if (params.purpose) sp.set("purpose", params.purpose);
  if (params.active_only !== undefined) {
    sp.set("active_only", String(params.active_only));
  }
  if (params.limit !== undefined) sp.set("limit", String(params.limit));
  const qs = sp.toString();
  return qs ? `?${qs}` : "";
}

export const magicLinksApi = {
  list: (params: ListMagicLinksParams = {}) =>
    api<MagicLinkRecord[]>(`${BASE}${toQuery(params)}`),

  generate: (req: GenerateMagicLinkRequest) =>
    api<MagicLinkRecord>(`${BASE}/generate`, { json: req }),

  /** #11 · admin · genera + envía el enlace por email en un paso (manual). */
  generateAndSend: (req: GenerateMagicLinkRequest) =>
    api<GenerateAndSendMagicLinkResponse>(`${BASE}/generate-and-send`, {
      json: req,
    }),

  /** Público · sin auth · resuelve token → contexto del magic link. */
  getByToken: (token: string) =>
    api<MagicLinkStatus>(`${BASE}/by-token/${encodeURIComponent(token)}`),

  /** Público · sin auth · consume el link (presenta OTP si requerido). */
  consume: (req: ConsumeMagicLinkRequest) =>
    api<ConsumeMagicLinkResponse>(`${BASE}/consume`, { json: req }),

  revoke: (id: string) =>
    api<void>(`${BASE}/${id}/revoke`, { method: "POST" }),
};
