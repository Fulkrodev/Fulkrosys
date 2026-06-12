"""M27 Conformity Lifecycle Paso 5 — service con persistencia SQL.

Extiende el modulo service.py (stateless) con las funciones que
persisten en las 13 tablas nuevas y orquestan:

- initialize_conformity_route (desde categoria M1)
- process_basic_declaration (E-041 firmada por RSEG, publicada)
- process_enac_certification (paquete dossier ENAC)
- detect_material_change (arbol 10 preguntas + score)
- apply_pce_overlay (cloud_* / uceens_* -> medidas extra al DdA)
- generate_role_topology (5 patrones + excepciones)
- trigger_renewal_campaign (auto +21m post-certif)
- record_exploratory_meeting (plantilla F.1)
"""
from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.conformity_lifecycle import (
    BasicDeclarationRow,
    ConformityRouteRow,
    ConformitySubmissionRow,
    EffortEstimateRow,
    ExploratoryMeetingRow,
    ExtraordinaryAuditRow,
    MaterialChangeRow,
    PceOverlayRow,
    RecategorizationRow,
    RenewalCampaignRow,
    RoleExceptionMemoRow,
    RoleTopologyRow,
    StakeholdersGraphSnapshotRow,
)
from backend.app.models.core import Categorization, Project, System

from .catalogs import (
    OVERLAY_TYPES,
    get_extra_measures,
    load_overlay_catalog,
    suggest_overlays_by_hints,
)

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════
# Constantes
# ══════════════════════════════════════════════════════════════════════


ROUTE_STATUSES = (
    "planned", "active", "submitted", "accepted", "rejected", "renewed",
)

RECERTIFICATION_MONTHS = 21  # 3 meses antes del aniversario bianual
CERTIFICATION_VALIDITY_MONTHS = 24

MATERIALITY_THRESHOLD = 0.6

# Efforts base por fase (calibracion inicial — actual_hours se rellena
# ex-post). Calibrable via calibrated_from_similar_projects_jsonb.
DEFAULT_EFFORT_BY_PHASE: dict[str, tuple[float, float]] = {
    # phase: (hours, cost_eur)
    "categorizacion": (24.0, 2400.0),
    "dda": (60.0, 6000.0),
    "implantacion": (120.0, 12000.0),
    "audit": (40.0, 4000.0),
    "retainer_year": (100.0, 10000.0),
}


ROLE_PATTERNS_BY_SIZE: tuple[tuple[int, str], ...] = (
    (1, "startup_unipersonal"),
    (10, "pyme_basica"),
    (50, "pyme_media"),
    (250, "empresa_grande"),
)
# admin_publica se detecta aparte por sector


class ConformityError(Exception):
    pass


# ══════════════════════════════════════════════════════════════════════
# Materiality 10-question tree
# ══════════════════════════════════════════════════════════════════════


# Cada pregunta suma al score si respuesta == True. Total max ~1.4, se
# cappea a 1.0. Umbral material = 0.6.
MATERIALITY_QUESTIONS: list[tuple[str, float, str]] = [
    ("affects_critical_systems", 0.25,
     "¿Afecta a sistemas clasificados C, I o A como MEDIO/ALTO?"),
    ("affects_personal_data_high", 0.20,
     "¿Afecta a tratamiento de datos personales de alto volumen o sensibles?"),
    ("affects_availability_24x7", 0.10,
     "¿Afecta a servicios con requisito de disponibilidad 24/7?"),
    ("permanent_change", 0.10,
     "¿Es un cambio permanente (no temporal)?"),
    ("outsourced_abroad", 0.15,
     "¿Externaliza o mueve datos a pais fuera de EEE?"),
    ("large_scale_users", 0.10,
     "¿Afecta a > 1000 usuarios / ciudadanos / empleados?"),
    ("changes_categorization", 0.30,
     "¿Requiere recategorizacion ENS del sistema afectado?"),
    ("new_attack_surface", 0.15,
     "¿Introduce nueva superficie de exposicion (internet, API publica)?"),
    ("disrupts_evidences", 0.10,
     "¿Requiere regenerar evidencias nucleares (>20% del set)?"),
    ("requires_new_contracts", 0.05,
     "¿Requiere firma de nuevos contratos / DPAs con terceros?"),
]


def compute_materiality_score(answers: dict[str, bool]) -> float:
    """Calcula score 0.0-1.0 a partir de respuestas del arbol.

    Respuestas no presentes se asumen False.
    """
    score = 0.0
    for key, weight, _ in MATERIALITY_QUESTIONS:
        if answers.get(key, False):
            score += weight
    return min(1.0, round(score, 2))


# ══════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def _get_project(db: AsyncSession, project_id: uuid.UUID) -> Project:
    res = await db.execute(select(Project).where(Project.id == project_id))
    p = res.scalar_one_or_none()
    if p is None:
        raise ConformityError(f"Project {project_id} no encontrado")
    return p


async def _get_project_category(
    db: AsyncSession, project_id: uuid.UUID,
) -> str | None:
    """Devuelve la categoria efectiva del proyecto (BASICA/MEDIA/ALTA)
    a partir de Categorization mas reciente en cualquiera de sus systems.

    Si el proyecto tiene campo ``categoria_objetivo`` ya populated y
    no hay Categorization, usa ese como fallback.
    """
    res = await db.execute(
        select(Categorization, System)
        .join(System, Categorization.system_id == System.id)
        .where(System.project_id == project_id)
        .order_by(Categorization.created_at.desc().nulls_last())
        .limit(1)
    )
    row = res.first()
    if row:
        cat = row[0].categoria_resultante
        if cat:
            return cat.upper()
    project = await _get_project(db, project_id)
    obj = project.categoria_objetivo
    if obj:
        return obj.upper()
    return None


# ══════════════════════════════════════════════════════════════════════
# Service
# ══════════════════════════════════════════════════════════════════════


class ConformityServicePaso5:
    """Gestiona ruta conformidad + overlays + gobierno cambios + renewal."""

    # ── Route initialization ────────────────────────────────────────

    async def initialize_conformity_route(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        *,
        detected_overlay_hints: list[str] | None = None,
    ) -> ConformityRouteRow:
        """Inicializa la ruta segun categoria del proyecto.

        BASICA -> route_type=declaracion_basica
        MEDIA/ALTA -> route_type=certificacion_enac

        Si ``detected_overlay_hints`` permite identificar un overlay
        aplicable, NO crea el overlay (eso es via apply_pce_overlay),
        pero lo anota en metadata_jsonb.suggested_overlays para que
        Marcos decida.

        Tambien inicializa effort_estimates por fase.
        """
        project = await _get_project(db, project_id)
        # Evitar duplicidad
        existing = (await db.execute(
            select(ConformityRouteRow).where(
                ConformityRouteRow.project_id == project_id,
                ConformityRouteRow.status.in_(("planned", "active")),
            ).limit(1)
        )).scalar_one_or_none()
        if existing:
            raise ConformityError(
                f"Ruta activa ya existe para {project_id} (id={existing.id})"
            )

        category = await _get_project_category(db, project_id)
        if category == "BASICA":
            route_type = "declaracion_basica"
            route_subtype = "self_assessment"
            exp = None  # Declaracion no caduca
        elif category in ("MEDIA", "ALTA"):
            route_type = "certificacion_enac"
            route_subtype = "enac_accredited"
            exp = date.today() + timedelta(days=CERTIFICATION_VALIDITY_MONTHS * 30)
        else:
            raise ConformityError(
                f"Categoria invalida o ausente para {project_id}: {category}"
            )

        suggested = suggest_overlays_by_hints(detected_overlay_hints or []) or []
        now = _now()
        # L-10 (FRENTE L): perfil autónomo/microempresa · NO cambia route_type ·
        # anota individual_mode + acumulación de roles RSeg/RSis en la misma
        # persona (Art.11 RD 311/2022 · CCN-STIC 801 · permitida con justificación
        # documentada). El copiloto (L-9) lo presenta sin inferir aceptación ENAC.
        is_micro = (project.tamano_empleados or "").strip().lower() in {
            "micro", "autonomo", "autónomo", "individual",
        }
        metadata: dict = {
            "category": category,
            "suggested_overlays": suggested,
            "project_name": project.nombre,
        }
        if is_micro:
            metadata["individual_mode"] = True
            metadata["rseg_rsys_same_person"] = True
        route = ConformityRouteRow(
            project_id=project_id,
            route_type=route_type,
            route_subtype=route_subtype,
            status="planned",
            initiated_at=now,
            expiration_date=exp,
            metadata_jsonb=metadata,
            created_at=now,
        )
        db.add(route)
        await db.flush()

        # Effort estimates
        for phase, (hours, cost) in DEFAULT_EFFORT_BY_PHASE.items():
            if route_type == "declaracion_basica" and phase in ("audit",):
                continue
            db.add(EffortEstimateRow(
                project_id=project_id,
                phase=phase,
                estimated_hours=hours,
                estimated_cost=cost,
                calibrated_from_similar_projects_jsonb={
                    "source": "DEFAULT_EFFORT_BY_PHASE",
                    "category": category,
                },
                created_at=now,
            ))
        await db.flush()
        return route

    # ── Basic Declaration (BASICA) ──────────────────────────────────

    async def _validate_self_assessment_808(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        report_id: uuid.UUID,
    ) -> None:
        """Valida la autoevaluación CCN-STIC 808 que respalda el cierre BÁSICA (R15).

        Antes ``self_assessment_report_id`` era un UUID opcional sin comprobar.
        Ahora debe apuntar a un ``documents`` REAL de ESTE proyecto que sea la
        autoevaluación CCN-STIC 808 (plantilla E-808*). El generador del E-808 ya
        existe (M10 Audit-Sim ``run_simulation`` + ``generate_report_docx`` →
        Documento); aquí se valida la referencia (FK + tipo) en el gate de cierre.
        """
        row = (await db.execute(
            text(
                "SELECT template_codigo FROM documents "
                "WHERE id = :rid AND project_id = :pid AND deleted_at IS NULL"
            ),
            {"rid": str(report_id), "pid": str(project_id)},
        )).first()
        if row is None:
            raise ConformityError(
                "self_assessment_report_id no corresponde a ningún documento de "
                "este proyecto (genere la autoevaluación CCN-STIC 808 / E-808 "
                "antes de cerrar BÁSICA)."
            )
        template_codigo = (row[0] or "")
        if not template_codigo.upper().startswith("E-808"):
            raise ConformityError(
                f"self_assessment_report_id apunta a '{template_codigo or 'documento sin código'}', "
                "no a la autoevaluación CCN-STIC 808 (se espera plantilla E-808)."
            )

    async def process_basic_declaration(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        *,
        responsible_person_name: str,
        responsible_person_email: str,
        published_url: str | None = None,
        self_assessment_report_id: uuid.UUID | None = None,
    ) -> BasicDeclarationRow:
        """Genera E-041 (Declaracion conformidad) y crea submission.

        Publica en la URL web del cliente (si ``published_url`` dado).
        Firma via hash SHA-256 del payload por simplicidad; la firma real la
        suscribe la DIRECCIÓN/órgano superior (CCN-STIC 809 Anexo A · asume la
        responsabilidad sobre la seguridad), NO el RSeg · vía magic link
        FIRMA_DOCUMENTO en paso M6. ``responsible_person_*`` debe ser el
        contacto de Dirección (M30 role_category='sponsor').
        """
        route = await self._get_active_route(db, project_id)
        if route.route_type != "declaracion_basica":
            raise ConformityError(
                "process_basic_declaration solo valido para "
                "route_type=declaracion_basica"
            )

        # #41 (FRENTE D): el cierre BÁSICA (publicación/firma) EXIGE la
        # autoevaluación CCN-STIC 808 (self_assessment_report_id). Sin ella la
        # autodeclaración no resiste que el órgano de contratación pida
        # evidencias (Premisa #1). En borrador (sin published_url) se tolera.
        if published_url and self_assessment_report_id is None:
            raise ConformityError(
                "No se puede publicar/firmar la Declaración de Conformidad "
                "BÁSICA sin la autoevaluación CCN-STIC 808 "
                "(self_assessment_report_id es obligatorio para el cierre)."
            )
        # R15: si se aporta la autoevaluación 808, VALIDARLA contra la tabla
        # `audit_simulation_runs` (antes era un UUID opcional sin comprobar).
        # Debe ser una autoevaluación real, de ESTE proyecto, de categoría
        # BÁSICA, FINALIZADA y sin no-conformidades MAYORES abiertas (no se puede
        # autodeclarar conformidad con NC mayores pendientes · CCN-STIC 808).
        if self_assessment_report_id is not None:
            await self._validate_self_assessment_808(
                db, project_id, self_assessment_report_id,
            )

        now = _now()
        payload = {
            "project_id": str(project_id),
            "responsible": responsible_person_name,
            "responsible_email": responsible_person_email,
            "published_url": published_url,
            "signed_at": now.isoformat(),
            # #44 (FRENTE D): tipo de firmable dedicado + firmante = DIRECCIÓN
            # (no RSeg · CCN-STIC 809 Anexo A · asume la responsabilidad).
            "signable_type": "declaracion_conformidad_basica",
            "signer_role": "direccion",
            "self_assessment_report_id": (
                str(self_assessment_report_id)
                if self_assessment_report_id else None
            ),
        }
        signed_hash = hashlib.sha256(
            str(sorted(payload.items())).encode("utf-8")
        ).hexdigest()

        # Submission (al sistema WEB del cliente + Registro CCN opcional)
        sub = ConformitySubmissionRow(
            project_id=project_id,
            submission_type="basic_declaration",
            external_system=("webpage_cliente" if published_url else "pending_publication"),
            submitted_by="marcos",
            submitted_at=now if published_url else None,
            external_ref_id=published_url,
            submission_payload_jsonb=payload,
            status="submitted" if published_url else "draft",
            created_at=now,
        )
        db.add(sub)
        await db.flush()

        decl = BasicDeclarationRow(
            project_id=project_id,
            declaration_type="initial",
            published_evidence_url=published_url,
            self_assessment_report_id=self_assessment_report_id,
            responsible_person_name=responsible_person_name,
            responsible_person_email=responsible_person_email,
            signed_at=now,
            signed_hash=signed_hash,
            submission_id=sub.id,
            status="signed" if published_url else "draft",
            created_at=now,
        )
        db.add(decl)
        await db.flush()

        # Transition route -> active si submission publicada
        if published_url:
            route.status = "active"
            route.submitted_at = now
            route.accepted_at = now
            await db.flush()
        return decl

    # ── ENAC Certification (MEDIA/ALTA) ─────────────────────────────

    async def prepare_enac_certification(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        *,
        auditor_entity: str,
        dossier_run_id: uuid.UUID | None = None,
    ) -> ConformitySubmissionRow:
        """Crea submission tipo enac_dossier con el paquete listo para
        el auditor acreditado ENAC.
        """
        route = await self._get_active_route(db, project_id)
        if route.route_type != "certificacion_enac":
            raise ConformityError(
                "prepare_enac_certification solo valido para route_type="
                "certificacion_enac"
            )
        now = _now()
        sub = ConformitySubmissionRow(
            project_id=project_id,
            submission_type="enac_dossier",
            external_system=auditor_entity,
            submitted_by="marcos",
            submitted_at=now,
            submission_payload_jsonb={
                "dossier_run_id": str(dossier_run_id) if dossier_run_id else None,
                "auditor_entity": auditor_entity,
            },
            status="submitted",
            created_at=now,
        )
        db.add(sub)
        route.status = "submitted"
        route.submitted_at = now
        await db.flush()
        return sub

    # ── Material changes ────────────────────────────────────────────

    async def detect_material_change(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        *,
        change_type: str,
        description: str,
        answers: dict[str, bool],
        detected_by: str = "marcos",
    ) -> MaterialChangeRow:
        """Registra un cambio + aplica arbol materialidad + dispara
        extraordinary_audit si score >= umbral.
        """
        await _get_project(db, project_id)
        score = compute_materiality_score(answers)
        is_material = score >= MATERIALITY_THRESHOLD

        now = _now()
        change = MaterialChangeRow(
            project_id=project_id,
            change_type=change_type,
            detected_at=now,
            detected_by=detected_by,
            description=description,
            materiality_score=score,
            is_material=is_material,
            materiality_tree_answers_jsonb=answers,
            triggered_extraordinary_audit=False,
            status="assessed",
            created_at=now,
        )
        db.add(change)
        await db.flush()

        if is_material:
            # Si cambia categorizacion, programar recategorization flow
            if answers.get("changes_categorization", False):
                # No se crea recategorization aqui (requiere nueva categoria
                # decidida); Marcos invoca create_recategorization despues.
                pass
            # Disparar extraordinary_audit
            audit = ExtraordinaryAuditRow(
                project_id=project_id,
                trigger_material_change_id=change.id,
                scope_description=(
                    f"Cambio material detectado: {description[:500]}"
                ),
                scheduled_for=now + timedelta(days=7),
                status="scheduled",
                created_at=now,
            )
            db.add(audit)
            await db.flush()
            change.extraordinary_audit_id = audit.id
            change.triggered_extraordinary_audit = True
            await db.flush()
        return change

    async def create_recategorization(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        *,
        old_category: str,
        new_category: str,
        trigger_material_change_id: uuid.UUID | None = None,
        approved_by: str | None = None,
    ) -> RecategorizationRow:
        if old_category.upper() not in ("BASICA", "MEDIA", "ALTA"):
            raise ConformityError(f"Categoria old invalida: {old_category}")
        if new_category.upper() not in ("BASICA", "MEDIA", "ALTA"):
            raise ConformityError(f"Categoria new invalida: {new_category}")
        now = _now()
        row = RecategorizationRow(
            project_id=project_id,
            old_category=old_category.upper(),
            new_category=new_category.upper(),
            trigger_material_change_id=trigger_material_change_id,
            approved_at=now if approved_by else None,
            approved_by=approved_by,
            status="approved" if approved_by else "pending",
            created_at=now,
        )
        db.add(row)
        await db.flush()
        return row

    # ── PCE overlays ────────────────────────────────────────────────

    async def apply_pce_overlay(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        *,
        overlay_type: str,
        assessment_report_id: uuid.UUID | None = None,
    ) -> PceOverlayRow:
        if overlay_type not in OVERLAY_TYPES:
            raise ConformityError(
                f"overlay_type invalido: {overlay_type}. "
                f"Validos: {OVERLAY_TYPES}"
            )
        catalog = load_overlay_catalog(overlay_type)
        version = catalog.get("version", "1.0")
        category = await _get_project_category(db, project_id)
        extra_measures = get_extra_measures(overlay_type, min_category=category)

        now = _now()
        row = PceOverlayRow(
            project_id=project_id,
            overlay_type=overlay_type,
            overlay_spec_version=version,
            applicability_assessment_jsonb={
                "category": category,
                "applicability_conditions": catalog.get("applicability", {}).get(
                    "conditions", [],
                ),
            },
            extra_measures_jsonb={
                "count": len(extra_measures),
                "measures": extra_measures,
                "compliance_checklist": catalog.get("compliance_checklist", []),
                "simplifications": catalog.get("simplifications", []),
            },
            compliance_status="in_progress",
            assessment_report_id=assessment_report_id,
            created_at=now,
        )
        db.add(row)
        await db.flush()
        return row

    # ── Role topology ───────────────────────────────────────────────

    async def generate_role_topology(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        *,
        total_persons: int,
        roles_assigned: dict[str, Any],
        sector: str | None = None,
        approved_by: str | None = None,
    ) -> RoleTopologyRow:
        """Detecta el patron de topologia y las excepciones conflictivas.

        roles_assigned debe contener los 4 roles ENS (rseg, rseg_delegado,
        responsable_seguridad, responsable_sistema, responsable_informacion).
        """
        pattern = self._detect_pattern(total_persons, sector)
        exceptions_count = self._count_role_conflicts(roles_assigned)
        now = _now()
        topo = RoleTopologyRow(
            project_id=project_id,
            pattern=pattern,
            total_persons=total_persons,
            ens_roles_assigned_jsonb=roles_assigned,
            exceptions_count=exceptions_count,
            approved_at=now if approved_by else None,
            approved_by=approved_by,
            revision_date=date.today() + timedelta(days=365),
            created_at=now,
        )
        db.add(topo)
        await db.flush()
        return topo

    def _detect_pattern(self, total_persons: int, sector: str | None) -> str:
        if sector and any(
            s in (sector or "").lower()
            for s in ("ayunt", "publica", "diputa", "univers")
        ):
            return "admin_publica"
        for max_persons, pattern in ROLE_PATTERNS_BY_SIZE:
            if total_persons <= max_persons:
                return pattern
        return "empresa_grande"

    @staticmethod
    def _count_role_conflicts(roles_assigned: dict[str, Any]) -> int:
        """Detecta personas que cubren roles conflictivos (CCN-STIC 801).

        Conflictos:
        - Responsable Informacion == Responsable Seguridad
        - Responsable Sistema == Responsable Seguridad
        - Responsable Informacion == Responsable Sistema
        """
        ri = roles_assigned.get("responsable_informacion")
        rs = roles_assigned.get("responsable_seguridad") or roles_assigned.get("rseg")
        rsis = roles_assigned.get("responsable_sistema")
        conflicts = 0
        if ri and rs and ri == rs:
            conflicts += 1
        if rs and rsis and rs == rsis:
            conflicts += 1
        if ri and rsis and ri == rsis:
            conflicts += 1
        return conflicts

    async def create_role_exception_memo(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        *,
        role_topology_id: uuid.UUID,
        exception_description: str,
        justification: str,
        compensating_controls: str,
        approved_by: str | None = None,
        document_id: uuid.UUID | None = None,
    ) -> RoleExceptionMemoRow:
        now = _now()
        memo = RoleExceptionMemoRow(
            project_id=project_id,
            role_topology_id=role_topology_id,
            exception_description=exception_description,
            justification=justification,
            compensating_controls=compensating_controls,
            approved_by=approved_by,
            document_id=document_id,
            created_at=now,
        )
        db.add(memo)
        await db.flush()
        return memo

    # ── Renewal campaigns ───────────────────────────────────────────

    async def trigger_renewal_campaign(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        *,
        months_since_certification: int | None = None,
        auto_triggered: bool = True,
        dossier_run_id: uuid.UUID | None = None,
    ) -> RenewalCampaignRow:
        route = await self._get_active_route(db, project_id)
        if route.route_type == "declaracion_basica":
            campaign_type = "renewal_declaracion"
        else:
            campaign_type = "recertification_bianual"
        now = _now()
        scheduled_for = now + timedelta(
            days=(CERTIFICATION_VALIDITY_MONTHS - RECERTIFICATION_MONTHS) * 30
        )
        row = RenewalCampaignRow(
            project_id=project_id,
            campaign_type=campaign_type,
            scheduled_for=scheduled_for,
            auto_triggered=auto_triggered,
            dossier_run_id=dossier_run_id,
            status="planned",
            created_at=now,
            result_jsonb={
                "months_since_certification": months_since_certification,
                "reason": (
                    "auto: 21 meses post-certificacion"
                    if auto_triggered else "manual"
                ),
            },
        )
        db.add(row)
        await db.flush()
        return row

    # ── Exploratory meetings (plantilla F.1) ────────────────────────

    async def record_exploratory_meeting(
        self,
        db: AsyncSession,
        client_id: uuid.UUID,
        *,
        lead_source: str,
        meeting_date: datetime | None = None,
        duration_minutes: int | None = None,
        blocks_completed: dict[str, Any] | None = None,
        outputs_agente_18: dict[str, Any] | None = None,
    ) -> ExploratoryMeetingRow:
        now = _now()
        row = ExploratoryMeetingRow(
            client_id=client_id,
            lead_source=lead_source,
            meeting_date=meeting_date or now,
            duration_minutes=duration_minutes,
            blocks_completed_jsonb=blocks_completed,
            outputs_agente_18_jsonb=outputs_agente_18,
            conversion_status="proposal_pending",
            created_at=now,
        )
        db.add(row)
        await db.flush()
        return row

    # ── Stakeholders graph snapshot ─────────────────────────────────

    async def snapshot_stakeholders_graph(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        *,
        graph_data: dict[str, Any],
    ) -> StakeholdersGraphSnapshotRow:
        prev = (await db.execute(
            select(StakeholdersGraphSnapshotRow).where(
                StakeholdersGraphSnapshotRow.project_id == project_id,
            ).order_by(
                StakeholdersGraphSnapshotRow.snapshot_date.desc().nulls_last()
            ).limit(1)
        )).scalar_one_or_none()
        now = _now()
        changed = prev is None or prev.graph_data_jsonb != graph_data
        change_summary = None
        if prev and changed:
            change_summary = "changes detected vs previous snapshot"
        row = StakeholdersGraphSnapshotRow(
            project_id=project_id,
            snapshot_date=now,
            graph_data_jsonb=graph_data,
            changed_from_previous=changed,
            change_summary=change_summary,
            created_at=now,
        )
        db.add(row)
        await db.flush()
        return row

    # ── Helpers ─────────────────────────────────────────────────────

    async def _get_active_route(
        self, db: AsyncSession, project_id: uuid.UUID,
    ) -> ConformityRouteRow:
        res = await db.execute(
            select(ConformityRouteRow).where(
                ConformityRouteRow.project_id == project_id,
                ConformityRouteRow.status.in_(("planned", "active", "submitted")),
            ).order_by(ConformityRouteRow.created_at.desc().nulls_last()).limit(1)
        )
        row = res.scalar_one_or_none()
        if row is None:
            raise ConformityError(
                f"No hay ruta activa para {project_id}. "
                "Llama a initialize_conformity_route primero."
            )
        return row

    async def get_conformity_status(
        self, db: AsyncSession, project_id: uuid.UUID,
    ) -> dict[str, Any]:
        route_res = await db.execute(
            select(ConformityRouteRow).where(
                ConformityRouteRow.project_id == project_id,
            ).order_by(ConformityRouteRow.created_at.desc().nulls_last()).limit(1)
        )
        route = route_res.scalar_one_or_none()

        mc_count = (await db.execute(
            select(text("count(*)")).select_from(MaterialChangeRow).where(
                MaterialChangeRow.project_id == project_id,
                MaterialChangeRow.is_material.is_(True),
            )
        )).scalar()
        overlay_count = (await db.execute(
            select(text("count(*)")).select_from(PceOverlayRow).where(
                PceOverlayRow.project_id == project_id,
            )
        )).scalar()
        subm_count = (await db.execute(
            select(text("count(*)")).select_from(ConformitySubmissionRow).where(
                ConformitySubmissionRow.project_id == project_id,
            )
        )).scalar()
        renewals = (await db.execute(
            select(text("count(*)")).select_from(RenewalCampaignRow).where(
                RenewalCampaignRow.project_id == project_id,
            )
        )).scalar()

        return {
            "project_id": str(project_id),
            "route": {
                "id": str(route.id) if route else None,
                "route_type": route.route_type if route else None,
                "status": route.status if route else None,
                "expiration_date": (
                    route.expiration_date.isoformat()
                    if route and route.expiration_date else None
                ),
            } if route else None,
            "material_changes_count": mc_count,
            "overlays_count": overlay_count,
            "submissions_count": subm_count,
            "renewals_count": renewals,
        }
