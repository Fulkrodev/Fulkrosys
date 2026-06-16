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

# Tamaño de lote del scan paginado por keyset (overridable en tests).
_BADGE_SCAN_BATCH = 1000


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

    # Buscar project cuyo cert_id derivado coincida. cert_id = uuid5(...) es un
    # hash one-way → NO invertible en SQL, de ahí el scan en Python. Antes el scan
    # usaba 'LIMIT 1000', lo que truncaba SILENCIOSAMENTE: con >1000 proyectos
    # activos, un cert_id válido de un proyecto fuera del top-1000 daba 404 falso.
    # Ahora se pagina por keyset (id) en lotes hasta agotar → sin truncación
    # silenciosa, memoria acotada por lote (early-break al encontrar match).
    matched_project_id: uuid.UUID | None = None
    cursor: str | None = None
    while matched_project_id is None:
        rows = await db.execute(
            sa_text(
                "SELECT id FROM projects "
                "WHERE deleted_at IS NULL "
                "AND (CAST(:cursor AS uuid) IS NULL "
                "     OR id > CAST(:cursor AS uuid)) "
                "ORDER BY id ASC LIMIT :batch"
            ),
            {"cursor": cursor, "batch": _BADGE_SCAN_BATCH},
        )
        batch = rows.fetchall()
        if not batch:
            break
        for (pid,) in batch:
            if derive_cert_id(pid) == cert_id:
                matched_project_id = pid
                break
        cursor = str(batch[-1][0])

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
