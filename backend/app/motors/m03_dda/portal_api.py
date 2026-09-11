"""Motor 3 — DdA · cliente in-portal API · SAN-E v3.MB-5.3.

ADR-020 v5: cliente revisa las 73 medidas DdA Anexo II in-portal · marca
su decisión per medida (revisada_ok · con_pregunta · suggest_change) ·
firma DdA final via M05 signing service.

Endpoints (cliente-facing · auth ClientUser via cookie + CSRF triple binding):

- GET /portal/dda/projects/{project_id} → summary
- GET /portal/dda/projects/{project_id}/measures → list with review status
- GET /portal/dda/projects/{project_id}/document-hash → SHA256 deterministic
  state actual · pre-firma SigningIntent (atom 5.3.C)
- GET /portal/dda/entries/{entry_id} → single entry detail
- POST /portal/dda/entries/{entry_id}/review → cliente review action

Q5.3: cliente NO edita aplicabilidad/justificación (admin owns) · solo
review (acepta · pregunta · sugiere). Justificación admin queda visible
read-only · cliente puede dejar nota o pregunta.

RLS: dda_entries enforce ``project_id = current_project_id()`` policy
forced. _ensure_project_belongs_to_client() sets tenant context.
"""
from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import case, func, select, text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db, set_tenant_context
from backend.app.models.client_portal import ClientUser
from backend.app.models.ens import DdaEntry, EnsMeasure
from backend.app.motors.m03_dda.anexo2_rd311_2022 import (
    ANEXO_II_RD311,
    EJE_Y_DIMENSIONES,
)
from backend.app.motors.m21_portal_cliente.api import get_current_client_user
from backend.app.motors.m21_portal_cliente.ownership import ensure_owned_via_project


router = APIRouter(
    prefix="/portal/dda",
    tags=["Motor 3 - DdA cliente in-portal"],
)


# ====================================================================
# Schemas
# ====================================================================


class DdaSummaryResponse(BaseModel):
    project_id: uuid.UUID
    categoria_objetivo: str | None
    total_measures: int
    reviewed_count: int
    pending_review_count: int
    questions_count: int
    suggestions_count: int
    completion_percentage: int
    is_frozen: bool
    frozen_at: datetime | None
    last_signed_at: datetime | None
    ready_for_final_sign: bool


class EvidenceSummary(BaseModel):
    """Resumen evidence cliente · linkable from measure."""

    id: uuid.UUID
    nombre_tipo: str | None
    fichero_nombre_original: str | None
    fichero_mime_type: str | None
    fecha_evidencia: datetime | None
    vigente: bool


class DdaEntryClientView(BaseModel):
    """Vista cliente DdA entry · audit ENAC compliance pre-firma.

    Cliente VE TODO contexto: descripcion + requisito_base + ccn_stic_reference
    + categoria_minima + tier_required_for + dimensiones_aplicables +
    aplicabilidad admin + justificacion admin + evidencias linked.

    Q5.3: cliente NO edita aplicabilidad/justificacion (admin owns).
    Solo review actions (revisada_ok · con_pregunta · suggest_change).
    """

    model_config = ConfigDict(from_attributes=True)

    # Identificacion
    id: uuid.UUID
    measure_codigo: str
    measure_nombre: str
    measure_familia: str | None
    measure_subfamilia: str | None
    measure_descripcion: str | None

    # ENS context educational (atom 5.3.E)
    requisito_base: str | None
    ccn_stic_reference: str | None  # fuente_oficial column
    categoria_minima: str | None  # BASICA · MEDIA · ALTA
    tier_required_for: list[str]  # ['BASICA','MEDIA','ALTA'] computed
    dimensiones_aplicables: list[str] | None  # DICAT subset
    # N1 · de donde sale la exigencia. "categoria" = por la categoria del
    # sistema; "dimension" = por el nivel de las dimensiones que se listan.
    # El Anexo II distingue las dos cosas y hasta ahora la DdA no.
    eje_aplicabilidad: str | None  # "categoria" | "dimension"
    # Nivel MINIMO de cada dimension que hace exigible la medida, segun la
    # tabla del Anexo II. Ej. op.cont.1 -> {"D": "MEDIO"} (en BAJO es n.a.).
    nivel_exigido_por_dimension: dict[str, str] | None

    # Estado admin (cliente VE · NO edit)
    aplicabilidad: str | None
    justificacion_no_aplica: str | None
    estado_implementacion: str | None
    observaciones: str | None
    aprobado_por: str | None
    fecha_aprobacion: datetime | None

    # Evidencias linked (atom 5.3.E)
    evidence_count: int
    evidence_list: list[EvidenceSummary]

    # Cliente review state (atom 5.3.A)
    client_review_status: str | None
    client_review_note: str | None
    client_reviewed_at: datetime | None


class DdaDocumentHashResponse(BaseModel):
    """Document hash determinista para SigningIntent · atom 5.3.C."""

    project_id: uuid.UUID
    document_hash_sha256: str
    canonical_length: int
    measures_count: int
    last_modified_at: datetime | None
    ready_for_signing: bool


class ReviewActionRequest(BaseModel):
    action: str = Field(
        ..., description="revisada_ok | con_pregunta | suggest_change",
    )
    note: str | None = Field(
        None, max_length=2000,
        description="Texto cliente · obligatorio si con_pregunta o suggest_change",
    )


VALID_REVIEW_ACTIONS = {
    "revisada_ok",
    "con_pregunta",
    "suggest_change",
}


# ====================================================================
# Helpers
# ====================================================================


async def _ensure_project_belongs_to_client(
    db: AsyncSession,
    project_id: uuid.UUID,
    user: ClientUser,
) -> str | None:
    """Verify project_id pertenece al client_id del user · sets tenant context.

    Returns ``categoria_objetivo`` del project (string · BASICA/MEDIA/ALTA o NULL).
    """
    row = await db.execute(
        sa_text(
            "SELECT client_id, categoria_objetivo FROM projects "
            "WHERE id = :pid"
        ),
        {"pid": str(project_id)},
    )
    hit = row.first()
    if hit is None:
        raise HTTPException(status_code=404, detail="Project no existe")
    if hit[0] != user.client_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Project no pertenece al cliente del usuario",
        )
    await set_tenant_context(
        db, client_id=user.client_id, project_id=project_id,
    )
    return hit[1]  # categoria_objetivo


async def _get_entry_with_project(
    db: AsyncSession,
    entry_id: uuid.UUID,
) -> tuple[DdaEntry, uuid.UUID]:
    """Fetch entry · returns (entry, project_id)."""
    entry = await db.get(DdaEntry, entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="No encontrado")
    return entry, entry.project_id


def _compute_tier_required_for(measure: EnsMeasure) -> list[str]:
    """Compute tier list desde aplica_basica/media/alta booleans."""
    out: list[str] = []
    if getattr(measure, "aplica_basica", False):
        out.append("BASICA")
    if getattr(measure, "aplica_media", False):
        out.append("MEDIA")
    if getattr(measure, "aplica_alta", False):
        out.append("ALTA")
    return out


async def _evidences_for_measure(
    db: AsyncSession,
    project_id: uuid.UUID,
    measure_codigo: str,
) -> list[EvidenceSummary]:
    """Lista evidencias linked a una medida (M07) · vigentes · sin deleted."""
    rows = await db.execute(
        sa_text(
            "SELECT id, nombre_tipo, fichero_nombre_original, "
            "fichero_mime_type, fecha_evidencia, vigente "
            "FROM evidence "
            "WHERE project_id = :pid AND measure_code = :mc "
            "AND deleted_at IS NULL "
            "ORDER BY fecha_evidencia DESC NULLS LAST, created_at DESC"
        ),
        {"pid": str(project_id), "mc": measure_codigo},
    )
    out: list[EvidenceSummary] = []
    for row in rows.all():
        out.append(EvidenceSummary(
            id=row[0],
            nombre_tipo=row[1],
            fichero_nombre_original=row[2],
            fichero_mime_type=row[3],
            fecha_evidencia=row[4],
            vigente=bool(row[5]),
        ))
    return out


_NIVELES_ANEXO_II = ("BAJO", "MEDIO", "ALTO")


def _nivel_exigido_por_dimension(codigo: str) -> dict[str, str] | None:
    """Nivel MINIMO de cada dimension al que el Anexo II ya exige la medida.

    Recorre las tres columnas de la tabla (BAJO/MEDIO/ALTO) y devuelve, por cada
    dimension de la medida, la primera que no es "n.a.". Ej.: op.cont.1 [D] es
    n.a. en BAJO y aplica en MEDIO, asi que devuelve {"D": "MEDIO"}.
    """
    eje, iniciales = EJE_Y_DIMENSIONES.get(codigo, (None, ""))
    if eje != "dimension" or not iniciales:
        return None
    entrada = ANEXO_II_RD311.get(codigo)
    if not entrada:
        return None
    _nombre, *celdas = entrada
    minimo = next((n for n, aplica in zip(_NIVELES_ANEXO_II, celdas) if aplica), None)
    if minimo is None:
        return None
    return {inicial: minimo for inicial in iniciales}


async def _to_client_view(
    db: AsyncSession,
    entry: DdaEntry,
    measure: EnsMeasure,
    *,
    project_id: uuid.UUID,
) -> DdaEntryClientView:
    """Serialize DdaEntry + EnsMeasure to richer client view (atom 5.3.E)."""
    evidences = await _evidences_for_measure(
        db, project_id, measure.codigo,
    )
    # N1 · el eje y las dimensiones salen del catalogo del Anexo II contrastado
    # contra el PDF del BOE (N0), NO de `ens_measures.dimensiones_aplicables`,
    # que estaba mal en 4 de las 12 medidas que se contrastaron a mano.
    #
    # Tampoco se lee `ens_measure_dimensiones`: esa tabla resuelve "Todas" como
    # las cinco dimensiones, asi que a una medida exigida POR CATEGORIA (org.1,
    # por ejemplo) le atribuye D+I+C+A+T. Cierto como dato, enganyoso en la DdA:
    # haria leer como "exigida por cinco dimensiones" algo que la norma exige
    # por la categoria del sistema. El catalogo si distingue las dos cosas.
    eje, iniciales = EJE_Y_DIMENSIONES.get(measure.codigo, (None, ""))
    dim_list = list(iniciales) if iniciales else None
    nivel_exigido = _nivel_exigido_por_dimension(measure.codigo) if eje == "dimension" else None

    fecha_aprob = entry.fecha_aprobacion
    if fecha_aprob is not None and not isinstance(fecha_aprob, datetime):
        fecha_aprob = datetime.combine(fecha_aprob, datetime.min.time(), tzinfo=UTC)

    # subfamily heuristic · split by '.' (codes like op.acc.1 → op.acc)
    parts = measure.codigo.split(".") if measure.codigo else []
    subfamilia = ".".join(parts[:2]) if len(parts) >= 2 else (measure.familia or None)

    return DdaEntryClientView(
        id=entry.id,
        measure_codigo=measure.codigo,
        measure_nombre=measure.nombre,
        measure_familia=measure.familia,
        measure_subfamilia=subfamilia,
        measure_descripcion=measure.descripcion,
        requisito_base=measure.requisito_base,
        ccn_stic_reference=measure.fuente_oficial,
        categoria_minima=measure.categoria_minima,
        tier_required_for=_compute_tier_required_for(measure),
        dimensiones_aplicables=dim_list,
        eje_aplicabilidad=eje,
        nivel_exigido_por_dimension=nivel_exigido,
        aplicabilidad=entry.aplicabilidad,
        justificacion_no_aplica=entry.justificacion_no_aplica,
        estado_implementacion=entry.estado_implementacion,
        observaciones=entry.observaciones,
        aprobado_por=entry.aprobado_por,
        fecha_aprobacion=fecha_aprob,
        evidence_count=len(evidences),
        evidence_list=evidences,
        client_review_status=entry.client_review_status,
        client_review_note=entry.client_review_note,
        client_reviewed_at=entry.client_reviewed_at,
    )


# ====================================================================
# Endpoints
# ====================================================================


@router.get("/projects/{project_id}", response_model=DdaSummaryResponse)
async def get_dda_summary(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: ClientUser = Depends(get_current_client_user),
) -> DdaSummaryResponse:
    """Summary DdA del project · cliente dashboard."""
    categoria = await _ensure_project_belongs_to_client(db, project_id, user)

    counts_stmt = select(
        func.count(DdaEntry.id).label("total"),
        func.count(case((DdaEntry.client_review_status == "revisada_ok", 1))).label(
            "reviewed"
        ),
        func.count(
            case((DdaEntry.client_review_status == "con_pregunta", 1))
        ).label("questions"),
        func.count(
            case((DdaEntry.client_review_status == "suggest_change", 1))
        ).label("suggestions"),
    ).where(DdaEntry.project_id == project_id)
    counts_row = (await db.execute(counts_stmt)).one()
    total, reviewed, questions, suggestions = counts_row

    pending = total - reviewed - questions - suggestions
    completion = int((reviewed * 100) / total) if total > 0 else 0

    # Frozen state · señal REAL = aprobación admin (aprobado_por en entries · m03
    # freeze_dda). La tabla dda_project_signatures quedó SIN escritor (dead code)
    # → is_frozen era siempre False. En el modelo cliente v3.11 ("indispensable-
    # cliente-only") el cliente NO revisa medida-por-medida; el gate de firma
    # depende de que Marcos haya CONGELADO/aprobado la DdA, no de
    # client_review_status (UI que ya no existe). Ver audit DdA.
    frozen_row = await db.execute(
        sa_text(
            "SELECT COUNT(*) FILTER (WHERE aprobado_por IS NOT NULL) AS frozen_n, "
            "MAX(fecha_aprobacion)::timestamptz AS frozen_at "
            "FROM dda_entries "
            "WHERE project_id = :pid AND deleted_at IS NULL"
        ),
        {"pid": str(project_id)},
    )
    frozen_stat = frozen_row.first()
    is_frozen = bool(frozen_stat and frozen_stat[0] and frozen_stat[0] > 0)
    frozen_at_val = frozen_stat[1] if frozen_stat else None

    # Last signed via signing_events (signing_intent_id from a signed dda intent)
    last_signed_row = await db.execute(
        sa_text(
            "SELECT MAX(se.created_at) FROM signing_events se "
            "JOIN signing_intents si ON si.id = se.signing_intent_id "
            "WHERE si.project_id = :pid AND si.signable_type = 'dda' "
            "AND se.event_type = 'signature_generated'"
        ),
        {"pid": str(project_id)},
    )
    last_signed = last_signed_row.scalar_one_or_none()

    return DdaSummaryResponse(
        project_id=project_id,
        categoria_objetivo=categoria,
        total_measures=total,
        reviewed_count=reviewed,
        pending_review_count=pending,
        questions_count=questions,
        suggestions_count=suggestions,
        completion_percentage=completion,
        is_frozen=is_frozen,
        frozen_at=frozen_at_val,
        last_signed_at=last_signed,
        # Gate firma cliente: DdA congelada por Marcos + aún sin firmar.
        ready_for_final_sign=(is_frozen and total > 0 and last_signed is None),
    )


@router.get(
    "/projects/{project_id}/measures",
    response_model=list[DdaEntryClientView],
)
async def list_dda_entries(
    project_id: uuid.UUID,
    family: str | None = Query(
        None, description="Filtra por familia · org · op · mp",
    ),
    review_status: str | None = Query(
        None,
        description=(
            "Filtra por client_review_status · pendiente_revision · "
            "revisada_ok · con_pregunta · suggest_change"
        ),
    ),
    db: AsyncSession = Depends(get_db),
    user: ClientUser = Depends(get_current_client_user),
) -> list[DdaEntryClientView]:
    """Lista DdA entries del project con info medida + review status cliente."""
    await _ensure_project_belongs_to_client(db, project_id, user)

    stmt = (
        select(DdaEntry, EnsMeasure)
        .join(EnsMeasure, EnsMeasure.id == DdaEntry.measure_id)
        .where(DdaEntry.project_id == project_id)
        .where(DdaEntry.deleted_at.is_(None))
    )
    if family:
        stmt = stmt.where(EnsMeasure.familia == family)
    if review_status:
        if review_status == "pendiente_revision":
            stmt = stmt.where(DdaEntry.client_review_status.is_(None))
        else:
            stmt = stmt.where(DdaEntry.client_review_status == review_status)

    stmt = stmt.order_by(EnsMeasure.codigo)
    rows = (await db.execute(stmt)).all()

    return [
        await _to_client_view(db, entry, measure, project_id=project_id)
        for entry, measure in rows
    ]


@router.get(
    "/projects/{project_id}/document-hash",
    response_model=DdaDocumentHashResponse,
)
async def get_dda_document_hash(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: ClientUser = Depends(get_current_client_user),
) -> DdaDocumentHashResponse:
    """SHA256 deterministic state DdA · usado pre-firma SigningIntent.

    Hash incluye:
    - project_id + categoria_objetivo
    - count medidas
    - per medida (sorted by codigo): codigo · aplicabilidad ·
      client_review_status · client_review_note_len · justificacion_len
    - sorted client_reviewed_at timestamps

    Cualquier modificación de medida o review cambia el hash · obliga
    NEW SigningIntent (intent previo expira o se reject).
    """
    categoria = await _ensure_project_belongs_to_client(db, project_id, user)

    stmt = (
        select(DdaEntry, EnsMeasure)
        .join(EnsMeasure, EnsMeasure.id == DdaEntry.measure_id)
        .where(DdaEntry.project_id == project_id)
        .where(DdaEntry.deleted_at.is_(None))
        .order_by(EnsMeasure.codigo)
    )
    rows = (await db.execute(stmt)).all()

    canonical_parts: list[str] = [
        f"project_id:{project_id}",
        f"categoria:{categoria or ''}",
        f"measures_count:{len(rows)}",
    ]
    last_modified: datetime | None = None
    # Gate firma v3.11: la DdA está lista para firmar cuando Marcos la congeló
    # (aprobado_por), NO cuando el cliente revisó cada medida (modelo viejo).
    any_frozen = False
    for entry, measure in rows:
        review = entry.client_review_status or "pending"
        note_len = len(entry.client_review_note or "")
        justif_len = len(entry.justificacion_no_aplica or "")
        canonical_parts.append(
            f"{measure.codigo}|aplica={entry.aplicabilidad or ''}|"
            f"review={review}|notelen={note_len}|justiflen={justif_len}"
        )
        ts_candidates = [t for t in (entry.updated_at, entry.client_reviewed_at) if t]
        if ts_candidates:
            entry_max = max(ts_candidates)
            if last_modified is None or entry_max > last_modified:
                last_modified = entry_max
        if entry.aprobado_por is not None:
            any_frozen = True

    canonical = "\n".join(canonical_parts)
    document_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    return DdaDocumentHashResponse(
        project_id=project_id,
        document_hash_sha256=document_hash,
        canonical_length=len(canonical),
        measures_count=len(rows),
        last_modified_at=last_modified,
        ready_for_signing=(any_frozen and len(rows) > 0),
    )


@router.get("/entries/{entry_id}", response_model=DdaEntryClientView)
async def get_dda_entry_detail(
    entry_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: ClientUser = Depends(get_current_client_user),
) -> DdaEntryClientView:
    """Detalle de una DdA entry · cliente drawer view."""
    entry, project_id = await _get_entry_with_project(db, entry_id)
    await ensure_owned_via_project(db, project_id, user)
    measure = await db.get(EnsMeasure, entry.measure_id)
    if measure is None:
        raise HTTPException(status_code=500, detail="Measure huerfano")

    return await _to_client_view(db, entry, measure, project_id=project_id)


@router.post(
    "/entries/{entry_id}/review",
    response_model=DdaEntryClientView,
)
async def review_dda_entry(
    entry_id: uuid.UUID,
    body: ReviewActionRequest,
    db: AsyncSession = Depends(get_db),
    user: ClientUser = Depends(get_current_client_user),
) -> DdaEntryClientView:
    """Cliente review action · acepta · pregunta · sugiere cambio."""
    if body.action not in VALID_REVIEW_ACTIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"action invalid · uno de {sorted(VALID_REVIEW_ACTIONS)}"
            ),
        )
    if body.action in {"con_pregunta", "suggest_change"} and not (body.note or "").strip():
        raise HTTPException(
            status_code=400,
            detail=(
                f"action='{body.action}' requiere note no vacia"
            ),
        )

    entry, project_id = await _get_entry_with_project(db, entry_id)
    await ensure_owned_via_project(db, project_id, user)

    entry.client_review_status = body.action
    entry.client_review_note = body.note
    entry.client_reviewed_at = datetime.now(UTC)
    entry.client_reviewed_by_user_id = user.id
    await db.flush()
    # HIGH #5 · que la duda/sugerencia del cliente LLEGUE a admin: la traza en
    # audit_log (visible en feeds admin + recent-activity · 3-way OR Sub-atom 5.A).
    # Antes el review solo mutaba la fila → Marcos nunca se enteraba.
    if body.action in {"con_pregunta", "suggest_change"}:
        import json as _json
        await db.execute(sa_text(
            "INSERT INTO audit_log (id, tabla, registro_id, accion, usuario, "
            "project_id, client_id, payload_new, timestamp) VALUES "
            "(gen_random_uuid(), 'dda_entries', :rid, 'dda.review.flagged', :usr, "
            ":pid, :cid, CAST(:payload AS jsonb), now())"
        ), {
            "rid": str(entry.id), "usr": f"cliente:{user.id}"[:255],
            "pid": str(project_id), "cid": str(user.client_id),
            "payload": _json.dumps({
                "action": body.action,
                "note": (body.note or "")[:2000],
                "measure_id": str(entry.measure_id),
            }),
        })
    await db.commit()

    measure = await db.get(EnsMeasure, entry.measure_id)
    return await _to_client_view(db, entry, measure, project_id=project_id)
