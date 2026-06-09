import { CSRF_COOKIE } from "./constants";

/**
 * CSRF helper compartido admin + portal cliente.
 *
 * Lee la cookie CSRF (no httpOnly) que el backend setea post-login.
 * Backend usa el mismo nombre (`fulkro_csrf`) para ambos contextos,
 * así que un único helper sirve a los dos wrappers de fetch.
 *
 * SSR-safe: devuelve null cuando `document` no existe (middleware
 * Next.js, server components, etc).
 *
 * Ver ADR-019 (CSRF triple binding).
 */
export function getCsrfToken(): string | null {
  if (typeof document === "undefined") return null;
  const pattern = new RegExp(`(?:^|;\\s*)${CSRF_COOKIE}=([^;]+)`);
  const match = document.cookie.match(pattern);
  return match ? decodeURIComponent(match[1]) : null;
}
