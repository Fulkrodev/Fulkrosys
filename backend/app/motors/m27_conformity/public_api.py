"""Motor 27 — Public router (sin auth) · SAN-C.MB-9.2.

Endpoints públicos para que los clientes embedan el distintivo de
conformidad ENS en su sede electrónica conforme CCN-STIC 809.

El path está bajo ``/api/v1/public/`` por lo que cae dentro del
``WHITELIST_PREFIX`` de ``backend/app/auth/global_dep.py`` y bypassa la
auth automáticamente.

* GET /api/v1/public/conformity/badge/{cert_id}/badge.svg

Diseño: el ``cert_id`` es uuid5 determinístico desde project_id, por
lo que el badge se cachea agresivamente (``Cache-Control`` 1 hora).
La firma criptográfica de garantía contra manipulación se obtiene a
través de ``/api/v1/auth/verify-signature`` con el contenido SVG +
clave pública FULKRO en ``/api/v1/auth/public-key``.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, Response
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db
from fastapi import Depends


public_router = APIRouter(tags=["Motor 27 - Conformity (public)"])


@public_router.get(
    "/public/conformity/badge/{cert_id}/badge.svg",
    response_class=Response,
)
async def public_badge_svg(
    cert_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Sirve distintivo SVG público (sin auth) embed-able en sede electrónica.

    El ``cert_id`` es uuid5 determinístico desde el project_id. El handler
    busca el proyecto cuyo cert derivado coincida con el id solicitado,
    y devuelve el SVG generado por ``distintivo_generator``.

    Cache-Control 1 hora · clientes pueden refrescar sin sobrecargar el
    backend. Re-emisión del distintivo no cambia la URL (idempotente).
    """
    from backend.app.motors.m27_conformity.distintivo_generator import (
        build_distintivo_context,
        derive_cert_id,
        generate_distintivo_svg,
    )

    # Endpoint PÚBLICO (sin auth · embed en sede electrónica) → no hay contexto
    # de tenant, por lo que RLS sobre `projects` filtraba a 0 filas y el badge
    # daba 404 SIEMPRE (auditoría 2026-06-07). Bypass RLS para el lookup+build:
    # es read-only y el cert_id (uuid5 determinístico) actúa de capability token
    # · el distintivo es público por diseño (CCN-STIC 809). Con la cirugía de rol
    # futura, fulkro → rol BYPASSRLS dedicado (mismo patrón que el resto del repo).
    await db.execute(sa_text("SET LOCAL ROLE fulkro_app_bypassrls"))

    # Buscar project cuyo cert_id derivado coincida (linear scan O(n) sobre
    # projects activos · aceptable para volumen bajo · index futuro vía
    # tabla materialized si la lista crece).
    rows = await db.execute(
        sa_text(
            "SELECT id FROM projects "
            "WHERE deleted_at IS NULL "
            "ORDER BY created_at DESC LIMIT 1000"
        )
    )
    matched_project_id: uuid.UUID | None = None
    for (pid,) in rows.fetchall():
        if derive_cert_id(pid) == cert_id:
            matched_project_id = pid
            break

    if matched_project_id is None:
        raise HTTPException(status_code=404, detail="Cert ID not found")

    ctx = await build_distintivo_context(db, matched_project_id)
    svg = generate_distintivo_svg(ctx)
    return Response(
        content=svg,
        media_type="image/svg+xml",
        headers={
            "Cache-Control": "public, max-age=3600",
            "X-Cert-Id": str(cert_id),
            "X-Issued-Date": ctx.today,
            "X-Expiry-Date": ctx.expiry_date,
        },
    )
