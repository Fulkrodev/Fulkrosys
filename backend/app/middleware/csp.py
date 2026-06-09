"""Content-Security-Policy middleware (SAN-B.MB-7.3 · ADR-033).

Aplica CSP + headers complementarios de hardening (X-Frame-Options
DENY, X-Content-Type-Options nosniff, Referrer-Policy strict-origin)
a todas las responses HTTP.

Directivas CSP justificadas:
- ``default-src 'self'`` · todo el contenido por defecto desde mismo origen
- ``script-src 'self' 'unsafe-inline' 'unsafe-eval'`` · Next.js requiere
  unsafe-inline para hidration scripts y unsafe-eval para HMR dev
- ``style-src 'self' 'unsafe-inline'`` · Tailwind + shadcn inyectan styles
  inline runtime
- ``img-src 'self' data: blob:`` · MinIO signed URLs vienen como blob
- ``connect-src 'self' https://api.anthropic.com`` · A14 Copilot streaming
- ``frame-ancestors 'none'`` · anti-clickjacking (equivale X-Frame-Options DENY)
- ``form-action 'self'`` · forms solo a mismo origen
- ``object-src 'none'`` · sin Flash/Java applets
- ``base-uri 'self'`` · prevenir <base> hijacking

Referencias:
- https://content-security-policy.com/
- ADR-033 (docs/spec/DECISIONS.md) · justificaciones detalladas.
"""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


CSP_DIRECTIVES: dict[str, list[str]] = {
    "default-src": ["'self'"],
    "script-src": ["'self'", "'unsafe-inline'", "'unsafe-eval'"],
    "style-src": ["'self'", "'unsafe-inline'"],
    "img-src": ["'self'", "data:", "blob:"],
    "font-src": ["'self'", "data:"],
    "connect-src": ["'self'", "https://api.anthropic.com"],
    "frame-ancestors": ["'none'"],
    "form-action": ["'self'"],
    "base-uri": ["'self'"],
    "object-src": ["'none'"],
}


def _format_csp(directives: dict[str, list[str]]) -> str:
    return "; ".join(
        f"{name} {' '.join(sources)}" for name, sources in directives.items()
    )


_CSP_HEADER_VALUE = _format_csp(CSP_DIRECTIVES)


class CSPMiddleware(BaseHTTPMiddleware):
    """Inserta CSP + hardening headers en todas las responses."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers.setdefault("Content-Security-Policy", _CSP_HEADER_VALUE)
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault(
            "Referrer-Policy", "strict-origin-when-cross-origin",
        )
        # HSTS + Permissions-Policy (auditoría seguridad 2026-06-07). HSTS sobre
        # HTTP lo ignora el navegador (inocuo en dev); en prod (TLS) fuerza HTTPS
        # 2 años + preload. Permissions-Policy bloquea APIs sensibles del browser.
        response.headers.setdefault(
            "Strict-Transport-Security",
            "max-age=63072000; includeSubDomains; preload",
        )
        response.headers.setdefault(
            "Permissions-Policy",
            "geolocation=(), microphone=(), camera=(), payment=()",
        )
        return response
