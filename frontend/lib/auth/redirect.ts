/**
 * Role-based redirect helpers post-login.
 *
 * Tras MFA verify exitoso (LoginForm.completeLogin), el usuario debe ir
 * al portal correspondiente a su role. Adicionalmente, el query param
 * ?next= permite preservar la URL original que el middleware (3.C)
 * incluyó al redirigir a /login, pero solo si está autorizada para
 * el role real del user.
 *
 * Sanitización del next param rechaza:
 *   - Paths externos (https://attacker.com/...) — protección open redirect
 *   - Paths protocol-relative (//attacker.com) — mismo riesgo
 *   - Paths que no empiezan por "/" — relativos no son válidos como destino
 *   - Paths fuera del role autorizado (cliente intentando ?next=/admin/* es
 *     ignorado y va a su default — no exfiltra estructura de paths admin)
 *
 * Ver ADR-013 v3 (1 user/cliente · 1 rol RW único · MB-3 cleanup)
 * + ADR-015 (role identidad) + ADR-018 (auth flow MF3.5).
 *
 * Tests E2E de esta lógica viven en SUB-FASE 3.F (frontend repo solo
 * tiene Playwright, no framework de tests unitarios TS).
 */

import { readLastUsedProjectIdFromStorage } from "@/lib/stores/active-project-store";

import { isAdminRole, isClientRole } from "./roles";

function getAllowedPaths(role: string): string[] {
  if (isAdminRole(role)) return ["/admin"];
  if (isClientRole(role)) return ["/client-portal"];
  return [];
}

/**
 * L3 hybrid post-login redirect (sub-atom 1.E.2 · ADR-054).
 *
 * Admin:
 *   - Si lastUsedProjectId existe en localStorage → /admin/projects/{id}/dashboard
 *   - Else → /admin/projects (selector landing)
 *
 * Cliente: /client-portal/dashboard (R29 unchanged · 1 proyecto/user natively).
 *
 * Server-side / SSR: localStorage NO accessible → admin falls back a
 * /admin/projects selector landing. Client-side LoginForm completion
 * triggers L3 hydrate en próxima navigation.
 */
export function getDefaultPathForRole(role: string): string {
  if (isAdminRole(role)) {
    const lastUsed = readLastUsedProjectIdFromStorage();
    if (lastUsed) {
      return `/admin/projects/${lastUsed}/dashboard`;
    }
    return "/admin/projects";
  }
  if (isClientRole(role)) return "/client-portal/dashboard";
  // Fallback defensivo: roles futuros (partner_senior, pentester_external,
  // introducer) que aún no tienen portal propio. Mandar a /login en lugar
  // de un portal aleatorio.
  return "/login";
}

export function isPathAllowedForRole(path: string, role: string): boolean {
  // Solo paths internos absolutos
  if (!path.startsWith("/")) return false;
  // Rechazar protocol-relative URLs (//attacker.com pasa el primer check)
  if (path.startsWith("//")) return false;

  const allowed = getAllowedPaths(role);
  return allowed.some(
    (prefix) => path === prefix || path.startsWith(`${prefix}/`),
  );
}

export function resolvePostLoginRedirect(
  role: string,
  nextParam: string | null,
): string {
  if (nextParam && isPathAllowedForRole(nextParam, role)) {
    return nextParam;
  }
  return getDefaultPathForRole(role);
}
