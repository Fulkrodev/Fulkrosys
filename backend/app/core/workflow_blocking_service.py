"""Workflow blocking rules service (ADR-036 SAN-D MB-17.5).

Valida si un proyecto puede transicionar a una target_phase mirando
las features flag de catalog declarativo + completion checks per
feature_key vs estado real motors. Endpoint GET /workflow/can-transition
expone resultado UI · POST /transition se difiere a MB-18 (DEC-5
ADR-036 Deferrables).

Completion checks per feature_key:
- ``alta_pentest_cpstic`` · VerificationRun real (DEC-3 ADR-036)
  category='ALTO' AND mode LIKE 'external_%' AND status='completed'.
- ``alta_criptografia_807`` · Evidence.evidence_type_id='criptografia_807'
  (DEC-4 RESOLVED · field real en backend/app/models/documents.py).
- ``media_vuln_scan`` · #16 · VerificationRun status='completed' existe
  (cualquier vuln-scan · fixture en dev, real con USE_MCP_REAL en prod).
- ``media_auditor_enac`` · #17 · ProjectRoleAssignment (M28) role_code
  auditor asignado (contact_id concreto o assigned_at) · autolimpia el
  gate ENAC cuando Marcos asigna el auditor externo al proyecto.
- ``alta_productos_cpstic`` · stub ``# Future:`` · Asset.cpstic_certified
  field schema deferrable a MB-19+ inventory enrichment (DEC-2 ADR-036).

Default unknown feature: completion=False (safe default · cliente nunca
pasa gate hasta wire-up explícito).
"""
from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.core.feature_flags import (
    get_blocking_features_for_phase,
    phase_int_to_enum,
)
from backend.app.models.core import Project
from backend.app.models.documents import Evidence
from backend.app.models.m28_role_assignment import ProjectRoleAssignment
from backend.app.motors.m08_verification.models import VerificationRun


class BlockingIssue(BaseModel):
    feature_key: str
    description: str
    target_phase: int
    fix_url: str


class WorkflowBlockingResult(BaseModel):
    can_transition: bool
    target_phase: int
    target_phase_label: str
    blocking_issues: list[BlockingIssue]


# Routes mapping (ADR-036 Deferrables · sub-routes dedicadas diferidas)
# fix_url apunta a routes existing con query params · WizardWizard
# inline en ConformityWizard MB-17.7 · stub pages no creadas MB-17.
_BLOCKING_DESCRIPTIONS: dict[str, tuple[str, str]] = {
    "media_auditor_enac": (
        "Asignar auditor externo ENAC obligatorio (Media+) antes de Conformidad",
        "/admin/projects/{pid}/roles?role=auditor_externo",
    ),
    "media_vuln_scan": (
        "Análisis de vulnerabilidades obligatorio (Media+) sin completar antes de Conformidad",
        "/admin/projects/{pid}/verification?focus=vuln_scan",
    ),
    "alta_pentest_cpstic": (
        "Pentest CPSTIC obligatorio (Alta) sin completar · CCN-STIC 105/140",
        "/admin/projects/{pid}/verification?focus=pentest_cpstic",
    ),
    "alta_productos_cpstic": (
        "Inventario sin productos certificados CPSTIC (Alta)",
        "/admin/projects/{pid}/verification?focus=cpstic_products",
    ),
    "alta_criptografia_807": (
        "Evidencias criptografía acreditada CCN-STIC 807 sin documentar",
        "/admin/projects/{pid}/evidence?type=criptografia_807",
    ),
}


class WorkflowBlockingService:
    """Verifica si proyecto puede transicionar a target phase."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def check_can_transition(
        self,
        project_id: UUID,
        target_phase: int,
    ) -> WorkflowBlockingResult:
        """Retorna ``can_transition`` + ``blocking_issues`` per feature flag."""
        target_phase_enum = phase_int_to_enum(target_phase)

        stmt = (
            select(Project)
            .where(Project.id == project_id)
            .options(selectinload(Project.client))
        )
        result = await self.db.execute(stmt)
        project = result.scalar_one_or_none()
        if not project:
            return WorkflowBlockingResult(
                can_transition=False,
                target_phase=target_phase,
                target_phase_label=target_phase_enum.value,
                blocking_issues=[
                    BlockingIssue(
                        feature_key="project_not_found",
                        description="Proyecto no existe",
                        target_phase=target_phase,
                        fix_url="",
                    )
                ],
            )

        categoria = project.categoria_objetivo or "BASICA"
        archetype = project.archetype

        required = get_blocking_features_for_phase(
            target_phase=target_phase,
            categoria=categoria,
            archetype=archetype,
        )

        blocking: list[BlockingIssue] = []
        for feature_key in required:
            completed = await self._is_feature_completed(
                project_id=project_id, feature_key=feature_key,
            )
            if not completed:
                description, fix_template = _BLOCKING_DESCRIPTIONS.get(
                    feature_key,
                    (
                        f"Feature {feature_key} sin completar",
                        "/admin/projects/{pid}",
                    ),
                )
                blocking.append(
                    BlockingIssue(
                        feature_key=feature_key,
                        description=description,
                        target_phase=target_phase,
                        fix_url=fix_template.format(pid=project_id),
                    )
                )

        return WorkflowBlockingResult(
            can_transition=len(blocking) == 0,
            target_phase=target_phase,
            target_phase_label=target_phase_enum.value,
            blocking_issues=blocking,
        )

    async def _is_feature_completed(
        self,
        project_id: UUID,
        feature_key: str,
    ) -> bool:
        """Verifica si feature está completed para proyecto."""
        if feature_key == "alta_pentest_cpstic":
            return await self._has_alta_pentest_cpstic(project_id)

        if feature_key == "alta_criptografia_807":
            return await self._has_alta_criptografia_807(project_id)

        if feature_key == "media_vuln_scan":
            return await self._has_media_vuln_scan(project_id)

        if feature_key == "media_auditor_enac":
            return await self._has_media_auditor_enac(project_id)

        if feature_key == "alta_productos_cpstic":
            # Future: Asset.cpstic_certified schema migration deferred
            # to MB-19+ inventory enrichment (DEC-2 ADR-036 Deferrables).
            # Safe default False · UI bloqueante visible.
            return False

        # Unknown feature: safe default False · forces explicit wire-up
        return False

    async def _has_media_vuln_scan(self, project_id: UUID) -> bool:
        """#16 · Vuln-scan Media/Alta ejecutado: existe un VerificationRun
        completado para el proyecto. No se filtra por categoría (evita el
        choque de naming BASICO/BASICA #39) ni por modo: cualquier run
        completado prueba que el análisis corrió (fixture en dev · real con
        USE_MCP_REAL+binarios en prod). El pentest externo (Alta) es superset
        y también satisface este requisito mínimo de vuln-scan."""
        stmt = (
            select(VerificationRun.id)
            .where(VerificationRun.project_id == project_id)
            .where(VerificationRun.status == "completed")
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def _has_media_auditor_enac(self, project_id: UUID) -> bool:
        """#17 · Auditor externo ENAC asignado: existe un ProjectRoleAssignment
        (M28) con role_code de auditor para el proyecto, efectivamente asignado
        (contact_id concreto o assigned_at fijado) y no borrado. Autolimpia el
        gate cuando se asigna el auditor en /admin/projects/{id}/roles · sustituye
        el stub safe-default que bloqueaba siempre."""
        stmt = (
            select(ProjectRoleAssignment.id)
            .where(ProjectRoleAssignment.project_id == project_id)
            .where(
                ProjectRoleAssignment.role_code.in_(
                    ("auditor", "auditor_externo"),
                )
            )
            .where(ProjectRoleAssignment.deleted_at.is_(None))
            .where(
                (ProjectRoleAssignment.contact_id.isnot(None))
                | (ProjectRoleAssignment.assigned_at.isnot(None))
            )
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def _has_alta_pentest_cpstic(self, project_id: UUID) -> bool:
        """Pentest CPSTIC ejecutado: VerificationRun ALTO + external_* + completed."""
        stmt = (
            select(VerificationRun.id)
            .where(VerificationRun.project_id == project_id)
            .where(VerificationRun.category == "ALTO")
            .where(VerificationRun.mode.like("external_%"))
            .where(VerificationRun.status == "completed")
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def _has_alta_criptografia_807(self, project_id: UUID) -> bool:
        """Evidencia criptografía: Evidence.evidence_type_id='criptografia_807'."""
        stmt = (
            select(Evidence.id)
            .where(Evidence.project_id == project_id)
            .where(Evidence.evidence_type_id == "criptografia_807")
            .where(Evidence.vigente.is_(True))
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none() is not None
