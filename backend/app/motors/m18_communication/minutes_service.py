"""M18 — Acta de Comite (E-005) — Service.

Orquesta el ciclo de vida completo de un acta:

1. ``create``                  — registro inicial en estado 'draft'
2. ``generate_docx``           — DOCX + hash SHA-256 + Ed25519 + PDF
3. ``send_for_signature``      — N magic links APROBACION_ACTA
4. ``register_signature``      — marca firma + transicion automatica
                                  a 'fully_signed' cuando todos firman
5. ``get_signing_status``      — % firmado, asistentes pendientes
6. ``regenerate_docx_with_signatures`` — re-renderiza el DOCX con el
   bloque de firmas relleno una vez firmado todos los asistentes

El bloqueo de gates externo (categorizacion, DdA) NO aplica aqui:
las actas pueden generarse en cualquier momento del proyecto.
"""
from __future__ import annotations

import hashlib
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.governance import CommitteeMeeting
from backend.app.models.operations import MagicLink
from backend.app.motors.m12_magic_link.purposes import MagicLinkPurpose
from backend.app.motors.m12_magic_link.schemas import MagicLinkGenerateRequest
from backend.app.motors.m12_magic_link.service import MagicLinkService
from backend.app.motors.m12_magic_link.emails.renderer import (
    render_email_for_magic_link,
)
from backend.app.motors.m18_communication.minutes_docx import build_minutes_docx


# Where DOCX/PDF go — vease tambien m06 service para coherencia
_BASE_DIR = Path(__file__).resolve().parents[4] / "var" / "documents_minutes"


VALID_TIPOS = {"kickoff", "seguimiento_trimestral", "cierre", "extraordinario"}
VALID_ESTADOS = {
    "draft", "generated", "sent_for_signature",
    "partially_signed", "fully_signed", "archived",
}


class MinutesError(Exception):
    """Error generico del servicio de actas."""


class MinutesNotFoundError(MinutesError):
    pass


class MinutesStateError(MinutesError):
    pass


class MinutesValidationError(MinutesError):
    pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _next_codigo(db: AsyncSession, project_id: uuid.UUID) -> str:
    """Genera el siguiente codigo E-005-NNN para el proyecto."""
    result = await db.execute(
        select(func.count(CommitteeMeeting.id)).where(
            CommitteeMeeting.project_id == project_id,
            CommitteeMeeting.codigo.isnot(None),
        )
    )
    n = (result.scalar() or 0) + 1
    return f"E-005-{n:03d}"


def _validate_asistentes(asistentes: list[dict]) -> None:
    if not asistentes:
        raise MinutesValidationError("El acta requiere al menos un asistente")
    for i, a in enumerate(asistentes):
        if not a.get("nombre"):
            raise MinutesValidationError(f"Asistente {i}: falta 'nombre'")


def _hash_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _ed25519_sign(data: bytes) -> str | None:
    """Best-effort Ed25519 signing reusing M6 sign_bytes helper.

    Devuelve hex de la firma, o None si la clave no esta disponible.
    """
    try:
        from backend.app.motors.m06_document_factory.signing import (
            sign_bytes, SigningError,
        )
        try:
            return sign_bytes(data).hex()
        except SigningError:
            return None
    except Exception:
        return None


def _convert_to_pdf(docx_path: Path) -> Path | None:
    """Best-effort DOCX → PDF using LibreOffice (M6 helper)."""
    try:
        from backend.app.motors.m06_document_factory.rendering import (
            convert_docx_to_pdf,
        )
        return convert_docx_to_pdf(docx_path, docx_path.parent)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class MinutesService:
    """Servicio de actas de comite (E-005)."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ─── CRUD ───────────────────────────────────────────────────────────

    async def create(
        self,
        project_id: uuid.UUID,
        tipo_comite: str,
        titulo: str,
        fecha: date,
        presidente: str,
        secretario: str,
        asistentes: list[dict],
        orden_del_dia: list[dict] | None = None,
        acuerdos: list[dict] | None = None,
        proximos_pasos: list[dict] | None = None,
        lugar: str | None = None,
        notas_libres: str | None = None,
        interlocutor_contact_id: uuid.UUID | None = None,
    ) -> CommitteeMeeting:
        if tipo_comite not in VALID_TIPOS:
            raise MinutesValidationError(
                f"tipo_comite invalido: '{tipo_comite}'. Validos: {sorted(VALID_TIPOS)}"
            )
        _validate_asistentes(asistentes)
        codigo = await _next_codigo(self.db, project_id)
        meeting = CommitteeMeeting(
            project_id=project_id,
            codigo=codigo,
            tipo_comite=tipo_comite,
            titulo=titulo,
            fecha=fecha,
            lugar=lugar,
            presidente=presidente,
            secretario=secretario,
            asistentes=asistentes,
            orden_del_dia=orden_del_dia or [],
            acuerdos_jsonb=acuerdos or [],
            proximos_pasos=proximos_pasos or [],
            notas_libres=notas_libres,
            firmas=[],
            estado="draft",
        )
        self.db.add(meeting)
        await self.db.flush()

        # Sub-fase 5.5.F integración M30 (plan v4.2 5.5.4.2):
        # auto-log interaction al timeline contacto si presente.
        if interlocutor_contact_id is not None:
            from backend.app.motors.m30_client_contacts.service import (
                ClientContactService, ContactNotFoundError,
            )
            try:
                await ClientContactService(self.db).log_interaction(
                    contact_id=interlocutor_contact_id,
                    interaction_type="meeting",
                    source_motor="a18",
                    source_id=meeting.id,
                    summary=f"{tipo_comite}: {titulo}",
                    details={
                        "fecha": fecha.isoformat(),
                        "codigo": codigo,
                    },
                )
            except ContactNotFoundError:
                # contacto referenciado no existe — silent fail, log_interaction
                # no debe romper creación de acta.
                pass

        return meeting

    async def get(self, minutes_id: uuid.UUID) -> CommitteeMeeting:
        m = await self.db.get(CommitteeMeeting, minutes_id)
        if m is None or m.deleted_at is not None:
            raise MinutesNotFoundError(f"Acta {minutes_id} no encontrada")
        return m

    async def list_by_project(
        self,
        project_id: uuid.UUID,
        estado: str | None = None,
    ) -> list[CommitteeMeeting]:
        stmt = select(CommitteeMeeting).where(
            CommitteeMeeting.project_id == project_id,
            CommitteeMeeting.deleted_at.is_(None),
            CommitteeMeeting.codigo.isnot(None),
        )
        if estado:
            stmt = stmt.where(CommitteeMeeting.estado == estado)
        stmt = stmt.order_by(CommitteeMeeting.fecha.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # ─── DOCX + sign + PDF ──────────────────────────────────────────────

    async def generate_docx(
        self,
        minutes_id: uuid.UUID,
        cliente_razon: str,
        version_actual: str = "1.0",
    ) -> CommitteeMeeting:
        """Renderiza DOCX + hash SHA-256 + Ed25519 + PDF.

        Idempotente para un mismo estado del acta: si ya existe DOCX,
        regenera y sobreescribe. Util para incluir el bloque de firmas
        relleno una vez todos firmen (vease ``regenerate_docx_with_signatures``).
        """
        m = await self.get(minutes_id)

        docx_bytes = build_minutes_docx(
            codigo=m.codigo,
            titulo=m.titulo,
            tipo_comite=m.tipo_comite,
            fecha=m.fecha,
            lugar=m.lugar,
            presidente=m.presidente,
            secretario=m.secretario,
            asistentes=m.asistentes or [],
            orden_del_dia=m.orden_del_dia or [],
            acuerdos=m.acuerdos_jsonb or [],
            proximos_pasos=m.proximos_pasos or [],
            notas_libres=m.notas_libres,
            firmas=m.firmas or [],
            cliente_razon=cliente_razon,
            version_actual=version_actual,
        )

        out_dir = _BASE_DIR / str(m.project_id) / m.codigo
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        docx_out = out_dir / f"{m.codigo}_{ts}.docx"
        docx_out.write_bytes(docx_bytes)

        m.docx_path = str(docx_out)
        m.hash_sha256 = _hash_sha256(docx_bytes)
        m.signature_ed25519 = _ed25519_sign(docx_bytes)
        m.generado_at = datetime.now(timezone.utc)
        if m.estado == "draft":
            m.estado = "generated"

        pdf = _convert_to_pdf(docx_out)
        if pdf:
            m.pdf_path = str(pdf)

        await self.db.flush()
        return m

    async def regenerate_docx_with_signatures(
        self,
        minutes_id: uuid.UUID,
        cliente_razon: str,
    ) -> CommitteeMeeting:
        """Re-renderiza DOCX con el bloque de firmas relleno.

        Llamar solo cuando estado=fully_signed; esto crea el documento
        final inmutable que se conservara como acta firmada.
        """
        m = await self.get(minutes_id)
        if m.estado != "fully_signed":
            raise MinutesStateError(
                f"Solo se regenera con firmas si esta fully_signed. "
                f"Estado actual: {m.estado}"
            )
        return await self.generate_docx(minutes_id, cliente_razon)

    # ─── Magic links + envio ────────────────────────────────────────────

    async def send_for_signature(
        self,
        minutes_id: uuid.UUID,
        cliente_razon: str,
        base_url: str,
    ) -> dict[str, Any]:
        """Genera un magic link APROBACION_ACTA por cada asistente.

        Renderiza el email rico (HTML + texto) listo para envio. El envio
        SMTP real es responsabilidad del caller (devolvemos los emails
        renderizados + magic links).

        Devuelve:
        {
          "minutes_id": uuid,
          "codigo": "E-005-NNN",
          "envios": [
             {"asistente_idx": 0, "email": "...", "magic_link_id": uuid,
              "url": "...", "otp": "123456",
              "subject": "...", "html_b64": "...", "text": "..."},
             ...
          ]
        }
        """
        m = await self.get(minutes_id)
        if m.estado not in {"generated", "draft", "sent_for_signature",
                            "partially_signed"}:
            raise MinutesStateError(
                f"No se puede enviar para firma en estado '{m.estado}'."
            )
        if not m.asistentes:
            raise MinutesStateError("El acta no tiene asistentes")

        ml_service = MagicLinkService(self.db)
        envios: list[dict[str, Any]] = []
        for idx, a in enumerate(m.asistentes):
            email = a.get("email")
            if not email:
                continue
            request = MagicLinkGenerateRequest(
                project_id=m.project_id,
                purpose=MagicLinkPurpose.APROBACION_ACTA,
                recipient_email=email,
                scope={
                    "minutes_id": str(m.id),
                    "asistente_idx": idx,
                    "asistente_nombre": a.get("nombre", ""),
                    "codigo": m.codigo,
                },
            )
            response = await ml_service.generate_magic_link(request, base_url)

            subject, html, text = render_email_for_magic_link(
                purpose=MagicLinkPurpose.APROBACION_ACTA,
                link_url=response.url,
                expires_at=response.expires_at,
                cliente={"razon_social": cliente_razon, "cif": ""},
                proyecto={"nombre": m.titulo or "Proyecto ENS"},
                destinatario={
                    "nombre": a.get("nombre", ""),
                    "cargo": a.get("cargo", ""),
                    "email": email,
                },
                otp=response.otp,
                acta={"codigo": m.codigo},
            )

            import base64 as _b64
            envios.append({
                "asistente_idx": idx,
                "asistente_nombre": a.get("nombre", ""),
                "email": email,
                "magic_link_id": str(response.magic_link_id),
                "url": response.url,
                "otp": response.otp,
                "expires_at": response.expires_at.isoformat(),
                "subject": subject,
                "html_b64": _b64.b64encode(html.encode("utf-8")).decode("ascii"),
                "text": text,
            })

        m.estado = "sent_for_signature"
        m.enviada_at = datetime.now(timezone.utc)
        await self.db.flush()

        return {
            "minutes_id": str(m.id),
            "codigo": m.codigo,
            "total_envios": len(envios),
            "envios": envios,
        }

    # ─── Firmas ─────────────────────────────────────────────────────────

    async def register_signature(
        self,
        minutes_id: uuid.UUID,
        magic_link_id: uuid.UUID,
        ip: str | None = None,
        action_proof: str | None = None,
    ) -> CommitteeMeeting:
        """Registra la firma de un asistente.

        - Verifica que el magic_link_id corresponda a este acta y a un
          asistente valido (via scope).
        - Marca firma con timestamp + ip.
        - Si TODOS los asistentes con email han firmado → estado =
          fully_signed + fully_signed_at + transicion automatica.
        """
        m = await self.get(minutes_id)
        if m.estado not in {"sent_for_signature", "partially_signed"}:
            raise MinutesStateError(
                f"No se aceptan firmas en estado '{m.estado}'. "
                f"Envia primero para firma."
            )

        ml = await self.db.get(MagicLink, magic_link_id)
        if ml is None or ml.deleted_at is not None:
            raise MinutesValidationError("Magic link no encontrado")
        if ml.tipo_operacion != MagicLinkPurpose.APROBACION_ACTA.value:
            raise MinutesValidationError(
                f"Magic link no es APROBACION_ACTA (purpose={ml.tipo_operacion})"
            )
        if ml.project_id != m.project_id:
            raise MinutesValidationError(
                "Magic link pertenece a otro proyecto"
            )
        scope = ml.scope or {}
        if scope.get("minutes_id") != str(m.id):
            raise MinutesValidationError(
                "Magic link no esta vinculado a esta acta"
            )
        idx = scope.get("asistente_idx")
        if not isinstance(idx, int):
            raise MinutesValidationError(
                "Magic link sin asistente_idx en scope"
            )
        if idx < 0 or idx >= len(m.asistentes or []):
            raise MinutesValidationError(
                f"asistente_idx {idx} fuera de rango"
            )

        # Idempotente: si el asistente ya firmo, no duplicamos
        firmas = list(m.firmas or [])
        already = next(
            (f for f in firmas if f.get("asistente_idx") == idx),
            None,
        )
        if already is None:
            firmas.append({
                "asistente_idx": idx,
                "asistente_nombre": (
                    m.asistentes[idx].get("nombre", "")
                    if idx < len(m.asistentes) else ""
                ),
                "magic_link_id": str(magic_link_id),
                "firmado_at": datetime.now(timezone.utc).isoformat(),
                "ip": ip,
                "action_proof": action_proof,
            })
        m.firmas = firmas

        # Calculo de estado
        emails_required = sum(
            1 for a in (m.asistentes or []) if a.get("email")
        )
        firmas_validas = len(firmas)
        if firmas_validas >= emails_required and emails_required > 0:
            m.estado = "fully_signed"
            m.fully_signed_at = datetime.now(timezone.utc)
        else:
            m.estado = "partially_signed"

        await self.db.flush()
        return m

    async def get_signing_status(
        self, minutes_id: uuid.UUID,
    ) -> dict[str, Any]:
        m = await self.get(minutes_id)
        asistentes_email = [
            a for a in (m.asistentes or []) if a.get("email")
        ]
        firmas = m.firmas or []
        firmados_idx = {f.get("asistente_idx") for f in firmas}
        pendientes = [
            {
                "asistente_idx": i,
                "nombre": a.get("nombre", ""),
                "email": a.get("email", ""),
            }
            for i, a in enumerate(m.asistentes or [])
            if a.get("email") and i not in firmados_idx
        ]
        total_required = len(asistentes_email)
        firmas_validas = sum(
            1 for f in firmas
            if f.get("asistente_idx") is not None
            and f.get("asistente_idx") < len(m.asistentes or [])
            and (m.asistentes or [])[f["asistente_idx"]].get("email")
        )
        pct = (
            round(100.0 * firmas_validas / total_required, 1)
            if total_required else 0.0
        )
        return {
            "minutes_id": str(m.id),
            "codigo": m.codigo,
            "estado": m.estado,
            "total_asistentes_con_email": total_required,
            "firmas_recibidas": firmas_validas,
            "porcentaje_firmado": pct,
            "pendientes": pendientes,
            "fully_signed_at": (
                m.fully_signed_at.isoformat() if m.fully_signed_at else None
            ),
        }


# ---------------------------------------------------------------------------
# Local helpers
# ---------------------------------------------------------------------------

def _subject_for_acta(codigo: str, cliente_razon: str) -> str:
    return f"Aprobacion del acta {codigo} — {cliente_razon}"


def _format_date_short(d) -> str:
    if d is None:
        return ""
    if isinstance(d, str):
        try:
            d = date.fromisoformat(d[:10])
        except Exception:
            return d
    if isinstance(d, datetime):
        d = d.date()
    return d.strftime("%d/%m/%Y")
