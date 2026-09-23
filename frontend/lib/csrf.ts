import { CSRF_COOKIE, CSRF_HEADER } from "./constants";

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

/**
 * Cabecera CSRF para un `fetch` directo que ESCRIBE (POST/PUT/PATCH/DELETE).
 *
 * El backend exige `X-CSRF-Token` == cookie `fulkro_csrf` en toda peticion que
 * no sea GET/HEAD/OPTIONS (auth/csrf.py). Los envoltorios `api`/`clientApi` ya
 * la ponen; un `fetch` directo NO, y sin ella el backend responde 403. Asi
 * estuvieron rotos el copiloto de cliente, el logout y el borrador de informe.
 */
export function csrfHeaders(): Record<string, string> {
  const token = getCsrfToken();
  return token ? { [CSRF_HEADER]: token } : {};
}
