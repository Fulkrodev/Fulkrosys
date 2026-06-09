/**
 * Cookie consent API client (atom 9.bis.1 PARTE B).
 *
 * Mirrors `backend/app/motors/m_compliance/cookies_api.py`. Public,
 * unauthenticated for anonymous visitors; authenticated cliente sessions
 * pick the same endpoints (cookie auth is detected server-side).
 */
import { api } from "@/lib/api";

export interface CookieConsentState {
  functional: boolean;
  analytics: boolean;
  marketing: boolean;
  consent_timestamp: string | null;
  consent_renewal_due: string | null;
  authenticated: boolean;
}

export type CookieCategory = "functional" | "analytics" | "marketing";

const ANON_KEY = "fulkro.anonymous_session_id";

/** Read or create the browser-side anonymous session UUID. */
export function getOrCreateAnonymousSessionId(): string {
  if (typeof window === "undefined") return "";
  let id = localStorage.getItem(ANON_KEY);
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem(ANON_KEY, id);
  }
  return id;
}

export async function getConsent(): Promise<CookieConsentState> {
  const sid = getOrCreateAnonymousSessionId();
  const qs = sid ? `?anonymous_session_id=${encodeURIComponent(sid)}` : "";
  return api<CookieConsentState>(`/api/v1/legal/cookies/consent${qs}`);
}

export async function postConsent(
  decisions: { functional: boolean; analytics: boolean; marketing: boolean },
  pageUrl?: string,
): Promise<CookieConsentState> {
  return api<CookieConsentState>("/api/v1/legal/cookies/consent", {
    method: "POST",
    json: {
      ...decisions,
      anonymous_session_id: getOrCreateAnonymousSessionId(),
      page_url: pageUrl ?? (typeof window !== "undefined" ? window.location.pathname : null),
    },
  });
}

export async function revokeConsent(
  category: CookieCategory,
  pageUrl?: string,
): Promise<CookieConsentState> {
  return api<CookieConsentState>("/api/v1/legal/cookies/revoke", {
    method: "POST",
    json: {
      category,
      anonymous_session_id: getOrCreateAnonymousSessionId(),
      page_url: pageUrl ?? (typeof window !== "undefined" ? window.location.pathname : null),
    },
  });
}

/** Local persisted cache for instant banner show/hide decisions (no network). */
const CACHE_KEY = "fulkro.cookie_consent.v1";

export function readCachedConsent(): CookieConsentState | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem(CACHE_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as CookieConsentState;
  } catch {
    return null;
  }
}

export function writeCachedConsent(state: CookieConsentState): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(CACHE_KEY, JSON.stringify(state));
}

export function clearCachedConsent(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(CACHE_KEY);
}
