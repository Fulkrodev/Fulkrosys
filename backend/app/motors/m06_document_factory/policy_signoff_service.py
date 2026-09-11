"""Motor 6 · Policy signoff service · SAN-E v3.MB-6 atom 1.

CCN-STIC 805 cliente review + firma bulk única workflow (Q1.C híbrida).

Tier-aware mapping (Q2.b):
  - BASICA · 10 policies core (PSI + 9 normativas críticas)
  - MEDIA  · 18 policies (BASICA + 8 extended)
  - ALTA   · 25 policies (todas Niveles 1+2 documentation_levels)

Servicio responsable de:
  - Resolver expected_policy_codes per project tier
  - Listar documents existentes vs expected (gaps detection)
  - Persistir cliente review per policy (revisada_ok / con_pregunta / suggest_change)
  - Calcular bulk_document_hash deterministic (input firma bulk M05)
  - Marcar todos documents signed via signing_intent_id post-firma bulk

Pattern atom 5.3.A consolidated 6ª aplicación.
"""
from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import and_, select, text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.documents import Document


# ════════════════════════════════════════════════════════════════════
# Tier-aware policy mapping CCN-STIC 805 niveles 1+2
# ════════════════════════════════════════════════════════════════════

# BASICA · 10 policies core (PSI + 9 normativas críticas mp.per + mp.info + op.acc)
POLICIES_BASICA: tuple[str, ...] = (
    "E-100",  # PSI · órgano superior
    "E-101",  # control de acceso · op.acc
    "E-102",  # contraseñas y autenticación · op.acc.5
    "E-103",  # uso aceptable recursos · mp.per.4
    "E-104",  # clasificación info · mp.info.2
    "E-105",  # tratamiento datos personales RGPD · mp.info
    "E-106",  # copias de seguridad · mp.info.6
    "E-108",  # gestión de incidentes · op.exp.7
    "E-117",  # gestión privilegios y PAM · op.acc.3
    "E-126",  # borrado seguro y destrucción · mp.si.5
)

# MEDIA · 18 policies (BASICA + 8 extended)
POLICIES_MEDIA: tuple[str, ...] = POLICIES_BASICA + (
    "E-107",  # cifrado y gestión claves · mp.com.3
    "E-109",  # continuidad del servicio · op.cont.1
    "E-110",  # teletrabajo y movilidad · mp.eq.3
    "E-111",  # uso servicios cloud · op.ext.4
    "E-114",  # desarrollo seguro SSDLC · mp.sw.1
    "E-115",  # gestión vulnerabilidades · op.exp.5
    "E-116",  # gestión de cambios · op.exp.4
    "E-119",  # respuesta brechas datos personales · mp.info
)

# ALTA · 25 policies (MEDIA + 7 más · cobertura completa CCN-STIC 805 niveles 1+2)
POLICIES_ALTA: tuple[str, ...] = POLICIES_MEDIA + (
    "E-112",  # seguridad relaciones proveedores · op.ext.1
    "E-113",  # adquisición tecnología · mp.sw.1
    "E-118",  # BYOD · mp.eq.3
    "E-121",  # redes y comunicaciones · mp.com.1
    "E-123",  # seguridad física · mp.if
    "E-124",  # seguridad del personal · mp.per.1
    "E-125",  # mesa limpia y pantalla limpia · mp.per.3
)


TIER_POLICY_MAPPING: dict[str, tuple[str, ...]] = {
    "BASICA": POLICIES_BASICA,
    "MEDIA": POLICIES_MEDIA,
    "ALTA": POLICIES_ALTA,
}


VALID_REVIEW_STATUS: frozenset[str] = frozenset({
    "pendiente_revision",
    "revisada_ok",
    "con_pregunta",
    "suggest_change",
})


CLIENT_FACING_REVIEW_STATUS: frozenset[str] = frozenset({
    "revisada_ok",
    "con_pregunta",
    "suggest_change",
})


# ════════════════════════════════════════════════════════════════════
# Exceptions
# ════════════════════════════════════════════════════════════════════


class PolicyServiceError(Exception):
    """Base error policy signoff service."""


class ProjectNotFoundError(PolicyServiceError):
    """Project no existe o sin categoría_objetivo."""


class InvalidTierError(PolicyServiceError):
    """Tier inválido · esperado BASICA/MEDIA/ALTA."""


class InvalidReviewActionError(PolicyServiceError):
    """Action review inválido · esperado revisada_ok/con_pregunta/suggest_change."""


class PolicyDocumentNotFoundError(PolicyServiceError):
    """Document policy no existe."""


# ════════════════════════════════════════════════════════════════════
# Data transfer objects
# ════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class PolicyReviewSummary:
    """Resumen tier + counters para portal cliente header."""

    project_id: uuid.UUID
    tier: str
    expected_count: int
    generated_count: int
    pending_review_count: int
    revisada_ok_count: int
    with_questions_count: int
    suggest_change_count: int
    ready_for_bulk_sign: bool
    bulk_signing_intent_id: uuid.UUID | None
    bulk_signed: bool


@dataclass(frozen=True)
class PolicyClientView:
    """Vista cliente single policy document."""

    document_id: uuid.UUID | None  # None si no generado yet
    template_codigo: str
    nombre: str | None
    level: int  # 1=PSI, 2=Normativa
    family: str  # identidad / continuidad / operacion / gobernanza / fundamental
    docx_path: str | None
    estado: str | None
    client_review_status: str | None
    client_review_note: str | None
    client_reviewed_at: datetime | None
    client_signing_intent_id: uuid.UUID | None


# Family mapping CCN-STIC 805 niveles 1+2 · agrupación accordion frontend (Q2 UX)
_POLICY_FAMILY: dict[str, str] = {
    "E-100": "fundamental",       # PSI
    "E-101": "identidad",         # control de acceso
    "E-102": "identidad",         # contraseñas
    "E-103": "personal",          # uso aceptable
    "E-104": "informacion",       # clasificación
    "E-105": "informacion",       # RGPD
    "E-106": "continuidad",       # copias seguridad
    "E-107": "criptografia",      # cifrado
    "E-108": "operacion",         # incidentes
    "E-109": "continuidad",       # continuidad servicio
    "E-110": "movilidad",         # teletrabajo
    "E-111": "operacion",         # cloud
    "E-112": "proveedores",       # relaciones proveedores
    "E-113": "operacion",         # adquisición
    "E-114": "desarrollo",        # SSDLC
    "E-115": "operacion",         # vulnerabilidades
    "E-116": "operacion",         # gestión cambios
    "E-117": "identidad",         # privilegios PAM
    "E-118": "movilidad",         # BYOD
    "E-119": "informacion",       # brechas datos
    "E-121": "redes",             # redes comunicaciones
    "E-123": "fisica",            # seguridad física
    "E-124": "personal",          # seguridad personal
    "E-125": "personal",          # mesa limpia
    "E-126": "informacion",       # borrado seguro
}


# ════════════════════════════════════════════════════════════════════
# Service
# ════════════════════════════════════════════════════════════════════


class PolicySignoffService:
    """Service cliente policy review + bulk signoff workflow."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ----------------------------------------------------------------
    # Tier resolution
    # ----------------------------------------------------------------

    async def get_expected_policy_codes(
        self, project_id: uuid.UUID,
    ) -> tuple[str, tuple[str, ...]]:
        """Resolve tier project + return (tier, codes_expected)."""
        row = await self.db.execute(
            sa_text(
                "SELECT categoria_objetivo FROM projects WHERE id = :pid"
            ),
            {"pid": str(project_id)},
        )
        hit = row.first()
        if hit is None:
            raise ProjectNotFoundError(f"Project {project_id} no existe")
        tier = (hit[0] or "").upper()
        if tier not in TIER_POLICY_MAPPING:
            raise InvalidTierError(
                f"Tier '{tier}' inválido para project {project_id} · "
                f"esperado BASICA/MEDIA/ALTA"
            )
        return tier, TIER_POLICY_MAPPING[tier]

    # ----------------------------------------------------------------
    # List documents per project (expected vs existing)
    # ----------------------------------------------------------------

    async def list_policies_for_client(
        self, project_id: uuid.UUID,
    ) -> list[PolicyClientView]:
        """List policy docs project ordenadas por template_codigo + family."""
        tier, expected = await self.get_expected_policy_codes(project_id)

        stmt = (
            select(Document)
            .where(
                and_(
                    Document.project_id == project_id,
                    Document.template_codigo.in_(expected),
                )
            )
        )
        docs_by_code: dict[str, Document] = {}
        for doc in (await self.db.execute(stmt)).scalars().all():
            if doc.template_codigo is not None:
                docs_by_code[doc.template_codigo] = doc

        result: list[PolicyClientView] = []
        for code in expected:
            doc = docs_by_code.get(code)
            level = 1 if code == "E-100" else 2
            family = _POLICY_FAMILY.get(code, "otros")
            if doc is None:
                result.append(PolicyClientView(
                    document_id=None,
                    template_codigo=code,
                    nombre=None,
                    level=level,
                    family=family,
                    docx_path=None,
                    estado=None,
                    client_review_status=None,
                    client_review_note=None,
                    client_reviewed_at=None,
                    client_signing_intent_id=None,
                ))
            else:
                result.append(PolicyClientView(
                    document_id=doc.id,
                    template_codigo=code,
                    nombre=doc.nombre,
                    level=level,
                    family=family,
                    docx_path=doc.docx_path,
                    estado=doc.estado,
                    client_review_status=doc.client_review_status,
                    client_review_note=doc.client_review_note,
                    client_reviewed_at=doc.client_reviewed_at,
                    client_signing_intent_id=doc.client_signing_intent_id,
                ))
        return result

    # ----------------------------------------------------------------
    # Summary
    # ----------------------------------------------------------------

    async def get_summary(self, project_id: uuid.UUID) -> PolicyReviewSummary:
        """Counters tier + readiness gate."""
        tier, expected = await self.get_expected_policy_codes(project_id)
        items = await self.list_policies_for_client(project_id)

        generated = sum(1 for i in items if i.document_id is not None)
        pending = sum(
            1 for i in items
            if i.document_id is not None
            and (i.client_review_status is None
                 or i.client_review_status == "pendiente_revision")
        )
        revisada_ok = sum(
            1 for i in items if i.client_review_status == "revisada_ok"
        )
        with_q = sum(
            1 for i in items if i.client_review_status == "con_pregunta"
        )
        sugg = sum(
            1 for i in items if i.client_review_status == "suggest_change"
        )

        ready_for_bulk = (
            generated == len(expected)
            and revisada_ok == len(expected)
        )

        bulk_intent_id: uuid.UUID | None = None
        bulk_signed = False
        signed_intent_ids = {
            i.client_signing_intent_id for i in items
            if i.client_signing_intent_id is not None
        }
        if len(signed_intent_ids) == 1:
            bulk_intent_id = next(iter(signed_intent_ids))
            bulk_signed = all(
                i.client_signing_intent_id == bulk_intent_id
                for i in items
                if i.document_id is not None
            )

        return PolicyReviewSummary(
            project_id=project_id,
            tier=tier,
            expected_count=len(expected),
            generated_count=generated,
            pending_review_count=pending,
            revisada_ok_count=revisada_ok,
            with_questions_count=with_q,
            suggest_change_count=sugg,
            ready_for_bulk_sign=ready_for_bulk,
            bulk_signing_intent_id=bulk_intent_id,
            bulk_signed=bulk_signed,
        )

    # ----------------------------------------------------------------
    # Review action (individual policy)
    # ----------------------------------------------------------------

    async def review_policy(
        self,
        document_id: uuid.UUID,
        action: str,
        note: str | None,
        user_id: uuid.UUID,
    ) -> Document:
        """Cliente review action per policy · audit log."""
        if action not in CLIENT_FACING_REVIEW_STATUS:
            raise InvalidReviewActionError(
                f"action '{action}' inválido · esperado "
                f"{sorted(CLIENT_FACING_REVIEW_STATUS)}"
            )
        if action in {"con_pregunta", "suggest_change"} and not (note or "").strip():
            raise InvalidReviewActionError(
                f"action '{action}' requiere note no vacía"
            )

        doc = await self.db.get(Document, document_id)
        if doc is None:
            raise PolicyDocumentNotFoundError(
                f"Document {document_id} no existe"
            )

        doc.client_review_status = action
        doc.client_review_note = (note or "").strip() or None
        doc.client_reviewed_at = datetime.now(UTC)
        doc.client_reviewed_by_user_id = user_id
        await self.db.flush()
        return doc

    # ----------------------------------------------------------------
    # Bulk signoff prepare · canonical hash
    # ----------------------------------------------------------------

    async def compute_bulk_document_hash(
        self, project_id: uuid.UUID,
    ) -> tuple[str, int]:
        """SHA256 deterministic hash bulk policies state · input firma M05."""
        tier, expected = await self.get_expected_policy_codes(project_id)
        items = await self.list_policies_for_client(project_id)

        canonical_parts: list[str] = [
            f"project_id:{project_id}",
            f"tier:{tier}",
            f"expected_count:{len(expected)}",
        ]
        items_by_code = {i.template_codigo: i for i in items}
        for code in expected:
            item = items_by_code[code]
            review = item.client_review_status or "pendiente"
            note_len = len(item.client_review_note or "")
            doc_present = "1" if item.document_id else "0"
            canonical_parts.append(
                f"{code}|doc={doc_present}|review={review}|notelen={note_len}"
            )

        canonical = "\n".join(canonical_parts)
        document_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        return document_hash, len(canonical)

    # ----------------------------------------------------------------
    # Bulk signoff finalize · mark all documents signed
    # ----------------------------------------------------------------

    async def mark_bulk_signed(
        self,
        project_id: uuid.UUID,
        signing_intent_id: uuid.UUID,
    ) -> int:
        """Link all expected policy docs to signing_intent post-firma bulk."""
        tier, expected = await self.get_expected_policy_codes(project_id)
        stmt = (
            select(Document)
            .where(
                and_(
                    Document.project_id == project_id,
                    Document.template_codigo.in_(expected),
                )
            )
        )
        docs = (await self.db.execute(stmt)).scalars().all()
        for doc in docs:
            doc.client_signing_intent_id = signing_intent_id
        await self.db.flush()
        return len(docs)
