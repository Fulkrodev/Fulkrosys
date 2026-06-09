/**
 * Middleware Next.js — protección server-side 3 portales.
 *
 * Ver ADR-013 (separación 3 portales) + ADR-015 (role vs capability)
 * + ADR-018 (regresión 3.C cerrada en BLOQUE 7 MF3.5).
 *
 * Reglas:
 *   /admin/*         → requiere role=owner
 *   /client-portal/* → requiere role=rw (CLIENT_PORTAL_SCOPE · ADR-013 v3)
 *   /                → redirect según role
 *
 * Defensa en profundidad: middleware bloquea server-side ANTES de
 * cargar página. AuthGuard (SUB-FASE 3.D) hace check adicional
 * client-side por UX (loading state, fallback). Backend dependencies
 * (require_owner, require_client_user en
 * backend/app/auth/dependencies.py) son la barrera final en API.
 *
 * JWT verification: usa jose con la PUBLIC KEY Ed25519 compartida con
 * backend (env FULKRO_AUTH_PUBLIC_KEY, server-side only). Cookie name
 * "fulkro_session" httpOnly seteada por backend tras MFA verify.
 *
 * Algoritmo: EdDSA (Ed25519). NO HS256. La clave pública se importa
 * vía jose.importSPKI y se cachea en memoria del proceso para evitar
 * re-parseo en cada request.
 */
import { type CryptoKey, importSPKI, jwtVerify } from "jose";
import { type NextRequest, NextResponse } from "next/server";

import { isAdminRole, isClientRole } from "@/lib/auth/roles";

const SESSION_COOKIE = "fulkro_session";
const PUBLIC_KEY_PEM = process.env.FULKRO_AUTH_PUBLIC_KEY;

if (!PUBLIC_KEY_PEM) {
  // Build/runtime warning. Sin PUBLIC_KEY = todos los requests caerán
  // a unauthenticated (degradación segura: redirect a /login).
  // eslint-disable-next-line no-console
  console.warn(
    "[middleware] FULKRO_AUTH_PUBLIC_KEY no configurada — todos los " +
      "requests autenticados caerán a unauthenticated. Configurar en " +
      "frontend/.env (pareja Ed25519 con backend FULKRO_AUTH_PRIVATE_KEY).",
  );
}

interface SessionClaims {
  sub: string;
  role?: string;
  is_owner?: boolean;
  exp?: number;
}

let _publicKeyCache: CryptoKey | null = null;

async function getPublicKey(): Promise<CryptoKey | null> {
  if (_publicKeyCache) return _publicKeyCache;
  if (!PUBLIC_KEY_PEM) return null;
  try {
    // .env multi-line con quotes dobles preserva newlines reales —
    // pero por robustez, también convertimos \n literales si los
    // hubiera (compat con setups que usen format single-line).
    const pem = PUBLIC_KEY_PEM.replace(/\\n/g, "\n");
    _publicKeyCache = await importSPKI(pem, "EdDSA");
    return _publicKeyCache;
  } catch (err) {
    // eslint-disable-next-line no-console
    console.error("[middleware] Error importando public key:", err);
    return null;
  }
}

async function getClaims(
  request: NextRequest,
): Promise<SessionClaims | null> {
  const token = request.cookies.get(SESSION_COOKIE)?.value;
  if (!token) return null;

  const publicKey = await getPublicKey();
  if (!publicKey) return null;

  try {
    const { payload } = await jwtVerify(token, publicKey, {
      algorithms: ["EdDSA"],
    });
    return payload as unknown as SessionClaims;
  } catch {
    // Token inválido, expirado, o secret no coincide
    return null;
  }
}

function redirectToLogin(
  request: NextRequest,
  loginPath: string = "/login",
): NextResponse {
  const url = request.nextUrl.clone();
  url.pathname = loginPath;
  url.searchParams.set("next", request.nextUrl.pathname);
  return NextResponse.redirect(url);
}

function redirectTo(request: NextRequest, path: string): NextResponse {
  const url = request.nextUrl.clone();
  url.pathname = path;
  url.searchParams.delete("next");
  return NextResponse.redirect(url);
}

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const claims = await getClaims(request);

  // ===== /admin/* — requiere owner =====
  if (pathname.startsWith("/admin")) {
    if (!claims) {
      return redirectToLogin(request, "/login");
    }
    if (!isAdminRole(claims.role)) {
      // Cliente intentando entrar a /admin/* → su portal.
      // Role desconocido → /login (no asumir cliente).
      if (isClientRole(claims.role)) {
        return redirectTo(request, "/client-portal/dashboard");
      }
      return redirectToLogin(request, "/login");
    }
    return NextResponse.next();
  }

  // ===== /client-portal/* — requiere role cliente (8 reales) =====
  if (pathname.startsWith("/client-portal")) {
    // Páginas públicas dentro de client-portal (login, etc.)
    const publicClientPortalPaths = [
      "/client-portal/login",
      "/client-portal/forgot-password",
    ];
    if (
      publicClientPortalPaths.some(
        (p) => pathname === p || pathname.startsWith(`${p}/`),
      )
    ) {
      return NextResponse.next();
    }

    if (!claims) {
      return redirectToLogin(request, "/client-portal/login");
    }
    if (isAdminRole(claims.role)) {
      // Owner intentando portal cliente → su portal admin.
      return redirectTo(request, "/admin/dashboard");
    }
    if (!isClientRole(claims.role)) {
      // Role desconocido (sesión inválida o role retirado) → login.
      return redirectToLogin(request, "/client-portal/login");
    }
    return NextResponse.next();
  }

  // ===== "/" raíz — redirect según role =====
  if (pathname === "/") {
    if (!claims) {
      return redirectTo(request, "/login");
    }
    if (isAdminRole(claims.role)) {
      return redirectTo(request, "/admin/dashboard");
    }
    if (isClientRole(claims.role)) {
      return redirectTo(request, "/client-portal/dashboard");
    }
    // Role desconocido (partner_senior, pentester_external, introducer):
    // redirect neutral a /login. Cuando esos roles tengan portal propio
    // (FASE futura), añadir branches aquí.
    return redirectTo(request, "/login");
  }

  // ===== Resto: público (login, sign, survey, upload, etc.) =====
  return NextResponse.next();
}

export const config = {
  matcher: [
    // Match all request paths except:
    // - _next/static (static files)
    // - _next/image (image optimization)
    // - favicon.ico
    // - api (API routes — Next.js rewrites a backend FastAPI)
    // - cualquier path con extensión (assets públicos en /public/)
    "/((?!_next/static|_next/image|favicon.ico|api/|.*\\..*).*)",
  ],
};
