"""Audit cross-project search endpoint (FASE 9.B / MB-4.D.2).

Búsqueda lexical (ILIKE) cross-motor para auditor externo · agrupa
findings (M04 gaps + M08 verification) + evidence (M07) + documents
(M06/M24 IDMS) en un único listado normalizado.

Pre-requisito: caller authenticated + scope auditor (UI bound a vista
audit). Backend no fuerza scope porque admin route pero podría reforzarse
con dependency `require_owner` futura.
"""
from __future__ import annotations

import uuid as _uuid
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import require_owner
from backend.app.database import get_db


# SEGURIDAD (auditoría 2026-06-07): este router ejecuta SET LOCAL ROLE fulkro_app_bypassrls
# (bypass RLS cross-tenant) y agrega findings/evidence/documents de TODOS los
# proyectos. Era alcanzable por el pool cliente → fuga cross-tenant. Cerrado el
# TODO histórico: gate admin-only obligatorio (ADR-013 require_owner).
router = APIRouter(
    tags=["Audit Search (FASE 9.B)"],
    dependencies=[Depends(require_owner)],
)


SEARCH_TYPE_LABELS = {
    "finding_gap": "Finding (gap)",
    "finding_verification": "Finding (verificación)",
    "evidence": "Evidencia",
    "document": "Documento",
}


class AuditSearchHit(BaseModel):
    type: str  # finding_gap | finding_verification | evidence | document
    id: str
    project_id: str
    title: str
    snippet: str | None = None
    severity: str | None = None
    estado: str | None = None
    measure_code: str | None = None
    created_at: str | None = None


class AuditSearchResponse(BaseModel):
    query: str
    types_filter: list[str]
    total: int
    hits: list[AuditSearchHit]


_VALID_TYPES = {"finding_gap", "finding_verification", "evidence", "document"}


def _parse_iso_dt(value: str | None) -> Optional[datetime]:
    """Parsea una fecha/hora ISO a ``datetime`` o ``None``.

    asyncpg infiere el tipo del bind por el ``CAST(... AS timestamptz)`` y exige
    un ``datetime`` real (no acepta str → DataError). Convertimos aquí en vez de
    delegar el cast a Postgres sobre un texto. Degradación honesta: si la cadena
    no es parseable, se trata como ausente (``None``) en lugar de provocar 500.
    """
    if not value:
        return None
    raw = value.strip()
    if not raw:
        return None
    try:
        # fromisoformat acepta 'YYYY-MM-DD' y 'YYYY-MM-DDTHH:MM:SS[+TZ]'.
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def _parse_uuid(value: str | None) -> Optional[str]:
    """Valida que ``value`` sea un UUID y lo normaliza, o devuelve ``None``.

    El bind se inyecta vía ``CAST(:project_id AS uuid)`` → asyncpg infiere el
    tipo y exige un UUID válido (un texto como ``'sdl-demo'`` provoca DataError
    → 500). A diferencia de los endpoints project-scoped (path param tipado UUID
    por FastAPI → 422 automático), aquí ``project_id`` es un query param string.
    Degradación honesta: un valor no-UUID se trata como filtro ausente (búsqueda
    cross-project sin acotar) en lugar de reventar con 500. Devolvemos str para
    mantener el bind como texto (el CAST en SQL hace la conversión final).
    """
    if not value:
        return None
    raw = value.strip()
    if not raw:
        return None
    try:
        return str(_uuid.UUID(raw))
    except (ValueError, AttributeError, TypeError):
        return None


@router.get(
    "/audit/search",
    response_model=AuditSearchResponse,
)
async def audit_search(
    q: str = Query("", description="Texto a buscar (ILIKE en campos relevantes)"),
    types: list[str] | None = Query(
        None,
        description="Filtro tipos · subset de finding_gap|finding_verification|evidence|document",
    ),
    project_id: str | None = Query(None, description="Filtra a un proyecto"),
    date_from: str | None = Query(None, description="ISO date inclusive"),
    date_to: str | None = Query(None, description="ISO date inclusive"),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> AuditSearchResponse:
    """Cross-project search · UNION normalizada de findings + evidence + docs."""
    types_filter: list[str] = []
    if types:
        types_filter = [t for t in types if t in _VALID_TYPES]
    if not types_filter:
        types_filter = list(_VALID_TYPES)

    # Admin role bypass para search cross-tenant (auditor externo solo accede
    # via magic link separado · este endpoint asume sesión Marcos).
    await db.execute(sa_text("SET LOCAL ROLE fulkro_app_bypassrls"))

    q_pattern = f"%{q.strip()}%" if q and q.strip() else None
    params: dict[str, Any] = {
        "limit": limit,
        "q": q_pattern,
        # asyncpg infiere uuid por el CAST → un project_id no-UUID daría DataError
        # (500). Validamos aquí: garbage → None (filtro ausente, NO 500).
        "project_id": _parse_uuid(project_id),
        # asyncpg infiere timestamptz por el CAST → exige datetime real, no str.
        "date_from": _parse_iso_dt(date_from),
        "date_to": _parse_iso_dt(date_to),
    }

    union_parts: list[str] = []

    if "finding_gap" in types_filter:
        union_parts.append(
            """
            SELECT 'finding_gap' AS type, id::text AS id, project_id::text,
                   COALESCE(SUBSTRING(descripcion, 1, 80), 'Finding') AS title,
                   SUBSTRING(descripcion, 1, 280) AS snippet,
                   severidad AS severity,
                   estado AS estado,
                   medida_afectada AS measure_code,
                   created_at
            FROM findings
            WHERE deleted_at IS NULL
              AND ('finding_gap' = ANY(:types))
              AND (CAST(:project_id AS uuid) IS NULL OR project_id = CAST(:project_id AS uuid))
              AND (CAST(:q AS text) IS NULL OR descripcion ILIKE CAST(:q AS text) OR medida_afectada ILIKE CAST(:q AS text))
              AND (CAST(:date_from AS timestamptz) IS NULL OR created_at >= CAST(:date_from AS timestamptz))
              AND (CAST(:date_to AS timestamptz) IS NULL OR created_at <= CAST(:date_to AS timestamptz))
            """,
        )

    if "finding_verification" in types_filter:
        union_parts.append(
            """
            SELECT 'finding_verification' AS type, id::text AS id, project_id::text,
                   COALESCE(SUBSTRING(title, 1, 80), 'Verification finding') AS title,
                   SUBSTRING(description, 1, 280) AS snippet,
                   severity AS severity,
                   status AS estado,
                   ens_primary_measure AS measure_code,
                   created_at
            FROM verification_findings
            WHERE deleted_at IS NULL
              AND ('finding_verification' = ANY(:types))
              AND (CAST(:project_id AS uuid) IS NULL OR project_id = CAST(:project_id AS uuid))
              AND (CAST(:q AS text) IS NULL OR title ILIKE CAST(:q AS text) OR description ILIKE CAST(:q AS text))
              AND (CAST(:date_from AS timestamptz) IS NULL OR created_at >= CAST(:date_from AS timestamptz))
              AND (CAST(:date_to AS timestamptz) IS NULL OR created_at <= CAST(:date_to AS timestamptz))
            """,
        )

    if "evidence" in types_filter:
        union_parts.append(
            """
            SELECT 'evidence' AS type, id::text AS id, project_id::text,
                   COALESCE(nombre_tipo, fichero_nombre_original, 'Evidence') AS title,
                   measure_code AS snippet,
                   NULL::text AS severity,
                   CASE WHEN vigente THEN 'vigente' ELSE 'caducada' END AS estado,
                   measure_code,
                   created_at
            FROM evidence
            WHERE deleted_at IS NULL
              AND ('evidence' = ANY(:types))
              AND (CAST(:project_id AS uuid) IS NULL OR project_id = CAST(:project_id AS uuid))
              AND (CAST(:q AS text) IS NULL OR nombre_tipo ILIKE CAST(:q AS text) OR fichero_nombre_original ILIKE CAST(:q AS text)
                   OR measure_code ILIKE CAST(:q AS text))
              AND (CAST(:date_from AS timestamptz) IS NULL OR created_at >= CAST(:date_from AS timestamptz))
              AND (CAST(:date_to AS timestamptz) IS NULL OR created_at <= CAST(:date_to AS timestamptz))
            """,
        )

    if "document" in types_filter:
        union_parts.append(
            """
            SELECT 'document' AS type, id::text AS id, project_id::text,
                   COALESCE(nombre, template_codigo, 'Documento') AS title,
                   COALESCE(clasificacion, tipo) AS snippet,
                   NULL::text AS severity,
                   estado AS estado,
                   template_codigo AS measure_code,
                   created_at
            FROM documents
            WHERE deleted_at IS NULL
              AND ('document' = ANY(:types))
              AND (CAST(:project_id AS uuid) IS NULL OR project_id = CAST(:project_id AS uuid))
              AND (CAST(:q AS text) IS NULL OR nombre ILIKE CAST(:q AS text) OR template_codigo ILIKE CAST(:q AS text)
                   OR full_text_content ILIKE CAST(:q AS text))
              AND (CAST(:date_from AS timestamptz) IS NULL OR created_at >= CAST(:date_from AS timestamptz))
              AND (CAST(:date_to AS timestamptz) IS NULL OR created_at <= CAST(:date_to AS timestamptz))
            """,
        )

    if not union_parts:
        return AuditSearchResponse(
            query=q, types_filter=types_filter, total=0, hits=[],
        )

    union_sql = "\nUNION ALL\n".join(f"({part})" for part in union_parts)
    full_sql = f"""
        WITH all_hits AS (
{union_sql}
        )
        SELECT * FROM all_hits
        ORDER BY created_at DESC NULLS LAST
        LIMIT :limit
    """

    params["types"] = types_filter
    rows = (await db.execute(sa_text(full_sql), params)).mappings().all()

    hits: list[AuditSearchHit] = []
    for row in rows:
        created_at = row["created_at"]
        if isinstance(created_at, datetime):
            created_at_iso = created_at.isoformat()
        else:
            created_at_iso = str(created_at) if created_at else None
        hits.append(AuditSearchHit(
            type=row["type"],
            id=row["id"],
            project_id=row["project_id"],
            title=row["title"] or "(sin título)",
            snippet=row["snippet"],
            severity=row["severity"],
            estado=row["estado"],
            measure_code=row["measure_code"],
            created_at=created_at_iso,
        ))

    return AuditSearchResponse(
        query=q, types_filter=types_filter, total=len(hits), hits=hits,
    )
