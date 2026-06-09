"""Body-size limit middleware · anti-DoS OOM (auditoría seguridad 2026-06-07).

Rechaza con 413 cualquier request cuyo `Content-Length` supere el tope global
ANTES de leer el cuerpo en memoria. Defensa de borde complementaria a los caps
per-endpoint (m07/m21/IDMS) y al `request_body { max_size }` de Caddy en prod.

Tope configurable vía `FULKRO_MAX_REQUEST_BODY_MB` (default 100 MB · holgado para
evidencias/documentos legítimos, pero acota OOM por subidas concurrentes grandes).
"""
from __future__ import annotations

import os

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


def _max_bytes() -> int:
    try:
        mb = int(os.environ.get("FULKRO_MAX_REQUEST_BODY_MB", "100"))
    except (ValueError, TypeError):
        mb = 100
    return max(1, mb) * 1024 * 1024


_MAX_BODY_BYTES = _max_bytes()


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    """413 si Content-Length excede el tope global (pre-lectura)."""

    async def dispatch(self, request: Request, call_next) -> Response:
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                if int(content_length) > _MAX_BODY_BYTES:
                    return JSONResponse(
                        status_code=413,
                        content={
                            "detail": (
                                "Request body demasiado grande · supera el "
                                "límite del servidor."
                            )
                        },
                    )
            except (ValueError, TypeError):
                # Content-Length malformado · dejar pasar (el endpoint valida).
                pass
        return await call_next(request)
