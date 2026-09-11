"""Motor 27 — Conformity Portal cliente in-portal · SAN-E v3.MB-5.6.

ADR-020 v6 Q5.3: cliente revisa declaracion conformidad ENS + readiness
chain firmas previas (DdA + MAGERIT + Pentest + evidencias + politicas) ·
firma con OTP step-up.

Escenario X audit-driven (5.6.A.bis): reutiliza BasicDeclarationRow tier-aware.
- BASICA → declaration_type='initial' (self-declaration final · genera distintivo)
- MEDIA/ALTA → declaration_type='commitment_pre_certification' (pre-auditor ENAC)

Sub-atom 5.6.C endpoints:
- GET  /portal/conformidad/projects/{id}/declaration · cliente VE draft + tier metadata
- GET  /portal/conformidad/projects/{id}/readiness · ConformityReadinessSnapshot
- POST /portal/conformidad/projects/{id}/mark-reviewed · cliente confirm + concerns
- GET  /portal/conformidad/projects/{id}/document-hash · SHA256 pre-firma
- GET  /portal/conformidad/projects/{id}/post-signature · post-firma · distintivo o commitment summary

Auth: ClientUser via cookie + CSRF triple binding.
RLS: basic_declarations enforce project_id · _ensure_project_belongs_to_client.
"""
from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db, set_tenant_context
from backend.app.models.client_portal import ClientUser
from backend.app.models.conformity_lifecycle import BasicDeclarationRow
from backend.app.motors.m21_portal_cliente.api import get_current_client_user
from backend.app.motors.m27_conformity.readiness_service import (
    ConformityReadinessSnapshot,
    compute_readiness,
)


router = APIRouter(
    prefix="/portal/conformidad",
    tags=["Motor 27 - Conformidad cliente in-portal"],
)


# ====================================================================
# Schemas
# ====================================================================


_BASICA_NEXT_STEP = (
    "Tras firmar generaremos automáticamente tu distintivo de conformidad + "
    "cert-id publicables. Marcos te ayudará con la publicación URL evidence "
    "en el Registro CCN si aplica."
)


_COMMITMENT_NEXT_STEP = (
    "Tras firmar Marcos enviará tu dossier al auditor ENAC acreditado. "
    "Plazos típicos: 30-60 días para certificación formal post-auditoría."
)


_BASICA_LABEL = "Declaración de Conformidad ENS final (E-041)"
_COMMITMENT_LABEL = "Compromiso de conformidad pre-auditoría ENAC"

# #2 Ola 7 · explicación R29 (en llano) de QUIÉN firma · muchas PYMEs no saben
# que esta Declaración la firma la Dirección y no el técnico de seguridad.
_BASICA_SIGNER_NOTE = (
    "Esta Declaración la firma la Dirección de tu empresa (no el responsable "
    "técnico de seguridad), porque la Dirección es quien asume la "
    "responsabilidad sobre la seguridad del sistema. Es un requisito del ENS "
    "(CCN-STIC 809). Si en tu empresa la Dirección y quien gestiona la "
    "seguridad son la misma persona, esa persona firma."
)


def _signer_explanation(declaration_type: str) -> str | None:
    """Solo BÁSICA (autodeclaración): la Declaración la firma la Dirección."""
    if declaration_type == "initial":
        return _BASICA_SIGNER_NOTE
    return None


def _workflow_label(declaration_type: str) -> str:
    if declaration_type == "initial":
        return _BASICA_LABEL
    if declaration_type == "commitment_pre_certification":
        return _COMMITMENT_LABEL
    return "Declaración de conformidad"


def _next_step_post_signature(declaration_type: str) -> str:
    if declaration_type == "initial":
        return _BASICA_NEXT_STEP
    if declaration_type == "commitment_pre_certification":
        return _COMMITMENT_NEXT_STEP
    return "Marcos te contactará para coordinar siguientes pasos."


class ConformidadDeclarationClientView(BaseModel):
    """Cliente view BasicDeclarationRow tier-aware."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    declaration_type: str
    tier: str
    workflow_label: str
    next_step_post_signature: str
    # #2 Ola 7 · explica al cliente que firma la Dirección (solo BÁSICA · None en
    # MEDIA/ALTA). R30 inverso: lenguaje llano, sin jerga.
    signer_explanation: str | None = None

    responsible_person_name: str | None
    responsible_person_email: str | None
    status: str
    signed_at: datetime | None
    signed_hash: str | None

    client_reviewed_at: datetime | None
    client_reviewed_by_user_id: uuid.UUID | None
    client_concerns_note: str | None
    client_signing_intent_id: uuid.UUID | None

    readiness_snapshot_jsonb: dict | None
    last_modified_at: datetime | None


class ReadinessItemView(BaseModel):
    label: str
    ready: bool
    detail: str | None = None


class ConformityReadinessView(BaseModel):
    tier: str
    ready_for_conformity_sign: bool
    blockers: list[str]
    captured_at: datetime
    items: list[ReadinessItemView]
    # Raw chain data
    dda_signed_at: datetime | None
    magerit_signed_at: datetime | None
    pentest_signed_at: datetime | None
    evidence_count: int
    policies_signed_count: int


class MarkReviewedRequest(BaseModel):
    concerns_note: str | None = Field(None, max_length=4000)


class ConformidadDocumentHashResponse(BaseModel):
    document_hash_sha256: str
    canonical_length: int
    declaration_id: uuid.UUID
    last_modified_at: datetime | None
    ready_for_signing: bool


class PostSignatureBasicaResponse(BaseModel):
    declaration_type: str  # "initial"
    distintivo_svg_url: str
    cert_id_url: str
    declaration_docx_url: str
    summary: str


class PostSignatureCommitmentResponse(BaseModel):
    declaration_type: str  # "commitment_pre_certification"
    commitment_signed_at: datetime
    next_step_summary: str
    next_step_eta_days_min: int
    next_step_eta_days_max: int
    contacto_marcos_email: str


# ====================================================================
# Helpers
# ====================================================================


async def _ensure_project_belongs_to_client(
    db: AsyncSession,
    project_id: uuid.UUID,
    user: ClientUser,
) -> None:
    row = await db.execute(
        sa_text("SELECT client_id FROM projects WHERE id = :pid"),
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


async def _get_active_declaration(
    db: AsyncSession,
    project_id: uuid.UUID,
) -> BasicDeclarationRow | None:
    """Latest BasicDeclarationRow draft o signed (NO recategorization)."""
    row = await db.execute(
        select(BasicDeclarationRow)
        .where(BasicDeclarationRow.project_id == project_id)
        .where(
            BasicDeclarationRow.declaration_type.in_(
                ("initial", "commitment_pre_certification")
            )
        )
        .order_by(BasicDeclarationRow.created_at.desc())
        .limit(1)
    )
    return row.scalar_one_or_none()


async def _get_project_tier(
    db: AsyncSession, project_id: uuid.UUID,
) -> str:
    from backend.app.motors.m27_conformity.readiness_service import _get_project_tier
    return await _get_project_tier(db, project_id)


def _readiness_to_view(snap: ConformityReadinessSnapshot) -> ConformityReadinessView:
    """Convert snapshot dataclass → API view + itemized checklist."""
    items: list[ReadinessItemView] = [
        ReadinessItemView(
            # No fijar "73 medidas": el nº aplicable depende de la categoría
            # (BÁSICA 52 · MEDIA 68 · ALTA 73). Referenciar el Anexo II sin número.
            label="DdA firmada (Declaración de Aplicabilidad · Anexo II)",
            ready=snap.dda_signed_at is not None,
            detail=(
                f"Firmada {snap.dda_signed_at.isoformat()}"
                if snap.dda_signed_at else None
            ),
        ),
        ReadinessItemView(
            label="MAGERIT validado (inventario activos + análisis riesgos)",
            ready=snap.magerit_signed_at is not None,
            detail=(
                f"Firmada {snap.magerit_signed_at.isoformat()}"
                if snap.magerit_signed_at else None
            ),
        ),
        ReadinessItemView(
            label=f"Evidencias del Anexo II ({snap.evidence_count} cargadas)",
            ready=snap.evidence_count > 0
            and len([b for b in snap.blockers if "Evidencias" in b]) == 0,
            detail=f"{snap.evidence_count} evidencias vigentes",
        ),
    ]
    # FIX(categoría · R29): el pentest solo es obligatorio en ALTA (en MEDIA es
    # opcional y en BÁSICA nunca · readiness_service gate solo ALTA). Antes el item
    # se mostraba SIEMPRE en rojo "Autorización pentest firmada: NO listo" con CTA
    # engañoso para BÁSICA/MEDIA (el cliente creía que le faltaba algo que no
    # necesita). No bloqueaba la firma, pero confundía.
    if snap.tier == "ALTA":
        items.append(
            ReadinessItemView(
                label="Autorización pentest firmada",
                ready=snap.pentest_signed_at is not None,
                detail=(
                    f"Firmada {snap.pentest_signed_at.isoformat()}"
                    if snap.pentest_signed_at else None
                ),
            )
        )
    # Policies item · tier-aware (SAN-E v3.MB-6 atom 1 · Q2.b)
    # BASICA 10 · MEDIA 18 · ALTA 25 · pre-atom-1 era solo ALTA 8.
    from backend.app.motors.m27_conformity.readiness_service import (
        tier_min_policies_count,
    )
    min_policies_tier = tier_min_policies_count(snap.tier)
    if min_policies_tier > 0:
        items.append(
            ReadinessItemView(
                label=f"Políticas firmadas (mínimo {min_policies_tier} {snap.tier})",
                ready=snap.policies_signed_count >= min_policies_tier,
                detail=f"{snap.policies_signed_count}/{min_policies_tier} firmadas",
            )
        )
    return ConformityReadinessView(
        tier=snap.tier,
        ready_for_conformity_sign=snap.ready_for_conformity_sign,
        blockers=snap.blockers,
        captured_at=snap.captured_at,
        items=items,
        dda_signed_at=snap.dda_signed_at,
        magerit_signed_at=snap.magerit_signed_at,
        pentest_signed_at=snap.pentest_signed_at,
        evidence_count=snap.evidence_count,
        policies_signed_count=snap.policies_signed_count,
    )


def _to_declaration_client_view(
    decl: BasicDeclarationRow,
    tier: str,
) -> ConformidadDeclarationClientView:
    """DRY: BasicDeclarationRow ORM → cliente view tier-aware."""
    return ConformidadDeclarationClientView(
        id=decl.id,
        project_id=decl.project_id,
        declaration_type=decl.declaration_type,
        tier=tier,
        workflow_label=_workflow_label(decl.declaration_type),
        next_step_post_signature=_next_step_post_signature(decl.declaration_type),
        signer_explanation=_signer_explanation(decl.declaration_type),
        responsible_person_name=decl.responsible_person_name,
        responsible_person_email=decl.responsible_person_email,
        status=decl.status,
        signed_at=decl.signed_at,
        signed_hash=decl.signed_hash,
        client_reviewed_at=decl.client_reviewed_at,
        client_reviewed_by_user_id=decl.client_reviewed_by_user_id,
        client_concerns_note=decl.client_concerns_note,
        client_signing_intent_id=decl.client_signing_intent_id,
        readiness_snapshot_jsonb=decl.readiness_snapshot_jsonb,
        last_modified_at=decl.created_at,
    )


# ====================================================================
# Service helper · prepare_client_declaration_draft (tier-aware)
# ====================================================================


async def prepare_client_declaration_draft(
    db: AsyncSession,
    project_id: uuid.UUID,
    *,
    responsible_name: str,
    responsible_email: str,
) -> BasicDeclarationRow:
    """Tier-aware draft creation · idempotent reuse existing draft.

    BASICA → declaration_type='initial' (E-041 self-declaration)
    MEDIA/ALTA → declaration_type='commitment_pre_certification' (pre-auditor)
    """
    existing = await _get_active_declaration(db, project_id)
    if existing is not None and existing.signed_at is None:
        return existing

    from backend.app.motors.m27_conformity.readiness_service import _get_project_tier
    tier = await _get_project_tier(db, project_id)

    declaration_type = (
        "initial" if tier == "BASICA" else "commitment_pre_certification"
    )

    decl = BasicDeclarationRow(
        project_id=project_id,
        declaration_type=declaration_type,
        responsible_person_name=responsible_name,
        responsible_person_email=responsible_email,
        status="pending_client_signature",
    )
    db.add(decl)
    await db.flush()
    return decl


# ====================================================================
# Endpoints
# ====================================================================


@router.get(
    "/projects/{project_id}/declaration",
    response_model=ConformidadDeclarationClientView,
)
async def get_conformidad_declaration(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: ClientUser = Depends(get_current_client_user),
) -> ConformidadDeclarationClientView:
    """Cliente VE declaracion conformidad pendiente firma o firmada."""
    await _ensure_project_belongs_to_client(db, project_id, user)
    decl = await _get_active_declaration(db, project_id)
    if decl is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "No hay declaracion conformidad pendiente. "
                "Marcos debe preparar el draft primero."
            ),
        )
    from backend.app.motors.m27_conformity.readiness_service import (
        _get_project_tier as get_tier,
    )
    tier = await get_tier(db, project_id)
    return _to_declaration_client_view(decl, tier)


@router.get(
    "/projects/{project_id}/readiness",
    response_model=ConformityReadinessView,
)
async def get_conformidad_readiness(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: ClientUser = Depends(get_current_client_user),
) -> ConformityReadinessView:
    """Cliente VE readiness checklist (DdA + MAGERIT + Pentest + evidencias + policies)."""
    await _ensure_project_belongs_to_client(db, project_id, user)
    snap = await compute_readiness(db, project_id)
    return _readiness_to_view(snap)


@router.post(
    "/projects/{project_id}/mark-reviewed",
    response_model=ConformidadDeclarationClientView,
)
async def mark_conformidad_reviewed(
    project_id: uuid.UUID,
    body: MarkReviewedRequest,
    db: AsyncSession = Depends(get_db),
    user: ClientUser = Depends(get_current_client_user),
) -> ConformidadDeclarationClientView:
    """Cliente confirma review · optional concerns_note · NO firma aun."""
    await _ensure_project_belongs_to_client(db, project_id, user)
    decl = await _get_active_declaration(db, project_id)
    if decl is None:
        raise HTTPException(
            status_code=404,
            detail="No hay declaracion conformidad pendiente",
        )
    if decl.signed_at is not None:
        raise HTTPException(
            status_code=409,
            detail="Declaracion ya firmada · NO se puede re-marcar revisada",
        )

    decl.client_reviewed_at = datetime.now(UTC)
    decl.client_reviewed_by_user_id = user.id
    if body.concerns_note is not None:
        decl.client_concerns_note = body.concerns_note
    await db.flush()

    # Construir la vista ANTES del commit. El cliente corre con RLS (client_id vía
    # SET LOCAL) y db.commit() RESETEA el GUC is_local → un refresh/lazy-load
    # posterior consulta SIN contexto RLS → 0 filas → InvalidRequestError "Could
    # not refresh instance" (500). Verificación: este 500 bloqueaba el cierre de
    # conformidad (cliente no podía marcar revisado → no podía firmar) en BÁSICA/
    # MEDIA/ALTA. Se lee decl + tier con el contexto RLS aún activo (post-flush).
    from backend.app.motors.m27_conformity.readiness_service import (
        _get_project_tier as get_tier,
    )
    tier = await get_tier(db, project_id)
    view = _to_declaration_client_view(decl, tier)
    await db.commit()
    return view


@router.get(
    "/projects/{project_id}/document-hash",
    response_model=ConformidadDocumentHashResponse,
)
async def get_conformidad_document_hash(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: ClientUser = Depends(get_current_client_user),
) -> ConformidadDocumentHashResponse:
    """SHA256 determinista state declaracion + readiness snapshot pre-firma.

    Hash incluye declaration_type + tier + responsible + signed chain firmas previas
    (DdA + MAGERIT + Pentest signed_at) + cliente review state.

    ready_for_signing gate: declaracion exists + cliente reviewed + readiness ready.
    """
    await _ensure_project_belongs_to_client(db, project_id, user)
    decl = await _get_active_declaration(db, project_id)
    if decl is None:
        raise HTTPException(
            status_code=404,
            detail="No hay declaracion conformidad pendiente",
        )

    snap = await compute_readiness(db, project_id)
    canonical_parts: list[str] = [
        f"project_id:{project_id}",
        f"declaration_id:{decl.id}",
        f"declaration_type:{decl.declaration_type}",
        f"tier:{snap.tier}",
        f"responsible:{decl.responsible_person_name or ''}",
        f"responsible_email:{decl.responsible_person_email or ''}",
        f"dda_signed:{snap.dda_signed_at.isoformat() if snap.dda_signed_at else 'pending'}",
        f"magerit_signed:{snap.magerit_signed_at.isoformat() if snap.magerit_signed_at else 'pending'}",
        f"pentest_signed:{snap.pentest_signed_at.isoformat() if snap.pentest_signed_at else 'pending'}",
        f"evidence_count:{snap.evidence_count}",
        f"policies_count:{snap.policies_signed_count}",
        f"client_reviewed:{decl.client_reviewed_at.isoformat() if decl.client_reviewed_at else 'pending'}",
    ]
    canonical = "\n".join(canonical_parts)
    document_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    ready_for_signing = (
        decl.client_reviewed_at is not None
        and snap.ready_for_conformity_sign
    )

    return ConformidadDocumentHashResponse(
        document_hash_sha256=document_hash,
        canonical_length=len(canonical),
        declaration_id=decl.id,
        last_modified_at=decl.created_at,
        ready_for_signing=ready_for_signing,
    )


@router.get(
    "/projects/{project_id}/post-signature",
)
async def get_conformidad_post_signature(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: ClientUser = Depends(get_current_client_user),
) -> dict[str, Any]:
    """Post-firma · tier-aware response.

    BASICA (declaration_type='initial') → distintivo_svg_url + cert_id_url + .docx
    MEDIA/ALTA (commitment_pre_certification) → commitment summary + next step ETA
    """
    await _ensure_project_belongs_to_client(db, project_id, user)
    decl = await _get_active_declaration(db, project_id)
    if decl is None:
        raise HTTPException(
            status_code=404,
            detail="No hay declaracion conformidad",
        )
    if decl.signed_at is None:
        raise HTTPException(
            status_code=409,
            detail="Declaracion NO firmada · post-signature solo disponible post-firma cliente",
        )

    if decl.declaration_type == "initial":
        # Auditoría 2026-06-07 · las URLs apuntaban a /api/v1/m27/ (prefijo
        # INEXISTENTE) + endpoints admin-only → el cliente NO podía descargar su
        # distintivo. Fix: distintivo desde el badge PÚBLICO (sin auth · embed
        # en sede electrónica) + cert-id/docx desde endpoints CLIENTE nuevos.
        from .distintivo_generator import derive_cert_id

        cert_id = derive_cert_id(project_id)
        return PostSignatureBasicaResponse(
            declaration_type="initial",
            distintivo_svg_url=(
                f"/api/v1/public/conformity/badge/{cert_id}/badge.svg"
            ),
            cert_id_url=(
                f"/api/v1/portal/conformidad/projects/{project_id}/cert-id"
            ),
            declaration_docx_url=(
                f"/api/v1/portal/conformidad/projects/{project_id}/declaration.docx"
            ),
            summary=(
                "Tu organización es conforme ENS BASICA. "
                "Puedes descargar tu distintivo y publicarlo donde quieras."
            ),
        ).model_dump()

    return PostSignatureCommitmentResponse(
        declaration_type="commitment_pre_certification",
        commitment_signed_at=decl.signed_at,
        next_step_summary=(
            "Tu compromiso de conformidad pre-auditoría está firmado. "
            "Marcos te contactará en los próximos 7 días para coordinar "
            "el envío del dossier al auditor ENAC acreditado."
        ),
        next_step_eta_days_min=30,
        next_step_eta_days_max=60,
        contacto_marcos_email="marcosmata@fulkro.es",
    ).model_dump()


@router.get("/projects/{project_id}/cert-id")
async def get_conformidad_cert_id_cliente(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: ClientUser = Depends(get_current_client_user),
) -> dict[str, Any]:
    """Cert-id determinístico + URL pública del distintivo · accesible CLIENTE.

    Auditoría 2026-06-07: el cliente necesita su cert-id pero el endpoint admin
    es require_owner. Reusa derive_cert_id (DRY · OPS-026).
    """
    await _ensure_project_belongs_to_client(db, project_id, user)
    from .distintivo_generator import derive_cert_id

    cert_id = derive_cert_id(project_id)
    return {
        "cert_id": str(cert_id),
        "public_badge_url": (
            f"/api/v1/public/conformity/badge/{cert_id}/badge.svg"
        ),
    }


@router.get("/projects/{project_id}/declaration.docx")
async def get_conformidad_declaration_docx_cliente(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: ClientUser = Depends(get_current_client_user),
):
    """Declaración de Conformidad BÁSICA (E-180 · CCN-STIC 809) DOCX · CLIENTE.

    Auditoría 2026-06-07: el único generate-docx era admin-only (require_owner)
    → el cliente NO podía descargar su declaración firmada. Endpoint cliente que
    reusa el generador (build_distintivo_context + generate_declaration_docx · DRY).
    """
    await _ensure_project_belongs_to_client(db, project_id, user)
    from fastapi.responses import Response

    from .distintivo_generator import (
        DECLARATION_DOCUMENT_KIND,
        build_distintivo_context,
        generate_declaration_docx,
    )

    ctx = await build_distintivo_context(db, project_id)
    bio = generate_declaration_docx(ctx)
    docx_bytes = bio.getvalue()

    # O2 · el gemelo de administracion tambien registra. Si solo registrara
    # aquel, un proyecto donde la declaracion la descarga SOLO el cliente se
    # quedaria sin ella en el expediente. El registro es idempotente por
    # (proyecto, codigo), asi que llamarlo desde los dos no duplica.
    from backend.app.motors.m06_document_factory.registro import (
        registrar_documento_generado,
    )

    fila = await registrar_documento_generado(
        db, project_id=project_id, template_codigo="E-041",
        nombre="E-041 - Declaracion de Conformidad con el ENS",
        docx_bytes=docx_bytes, generated_by="m27.portal_cliente",
        tipo="conformidad",
    )
    await db.commit()

    return Response(
        content=docx_bytes,
        media_type=(
            "application/vnd.openxmlformats-officedocument."
            "wordprocessingml.document"
        ),
        headers={
            "Content-Disposition": (
                f'attachment; filename="declaracion_conformidad_{project_id}.docx"'
            ),
            "X-Cert-Id": str(ctx.cert_id),
            "X-Document-Kind": DECLARATION_DOCUMENT_KIND,
            "X-Fulkro-Document-Id": str(fila.id),
        },
    )
