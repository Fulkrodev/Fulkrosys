/**
 * Constantes de roles compartidas entre middleware y redirect helpers.
 *
 * Single source of truth para evitar drift entre el dispatcher
 * server-side (`middleware.ts`) y los helpers post-login
 * (`redirect.ts`). Ambos archivos deben tratar el mismo rol como
 * "cliente" o "admin".
 *
 * Backend equivalents:
 *   - ADMIN_ROLE: corresponde a `auth_users.role == "owner"`
 *   - CLIENT_PORTAL_SCOPE: corresponde a
 *     `backend/app/motors/m21_portal_cliente/scopes.py::PORTAL_SCOPE`
 *     (= "rw" único · ADR-013 v3 single-user-RW · MB-3 cleanup).
 *
 * Ver ADR-013 v3 (1 user/cliente · 1 rol RW único),
 * ADR-015 (role identidad), ADR-018 (regresión middleware 3.C
 * corregida en BLOQUE 7 MF3.5).
 */

export const ADMIN_ROLE = "owner";

/**
 * Único valor que un cliente portal puede tener en `claims.role`.
 * El backend emite `PORTAL_SCOPE = "rw"` en `extra_claims` al login
 * tras SAN-E v3.MB-3.cleanup.
 */
export const CLIENT_PORTAL_SCOPE = "rw";

export function isAdminRole(role: string | undefined | null): boolean {
  return role === ADMIN_ROLE;
}

export function isClientRole(role: string | undefined | null): boolean {
  return role === CLIENT_PORTAL_SCOPE;
}
