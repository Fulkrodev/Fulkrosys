"""m_workflow_engine deliverables service · sub-atom 1.C.D.D.1 v3.8.

Match deliverable_codes per sub-paso → Evidence Vault rows existing.

Pattern:
  - Lookup template via get_template_by_id(template_id) (1.C.D.A loader)
  - For each deliverable_code (E-XXX format · ej "E-040"):
      - Match against evidence.evidence_type_id OR evidence.measure_code
      - If existing + vigente=True → status="available"
      - If existing + vigente=False → status="needs_regen"
      - If NO existe → status="missing" (admin trigger generate vía M06)
  - NO auto-generación · explicit admin action (single source decision)
  - NO new columns · sostener ADR-025 (reuse evidence_type_id / measure_code)

OPS-026 sostener · audit-first reveal:
  - evidence model existing tiene evidence_type_id + measure_code · NO step_template_id
  - DECISION: match via evidence_type_id (catalog ENS deliverable codes)
"""
from __future__ import annotations

import uuid
from pathlib import Path
from typing import Literal

from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m21_portal_cliente.task_templates_loader import (
    get_template_by_id,
)


DeliverableStatus = Literal["available", "needs_regen", "missing"]


class DeliverableState(BaseModel):
    """Estado per deliverable_code · template + evidence match."""

    code: str  # E-XXX
    status: DeliverableStatus
    evidence_id: uuid.UUID | None = None
    fichero_nombre_original: str | None = None
    fichero_mime_type: str | None = None
    fichero_tamano_bytes: int | None = None
    hash_sha256: str | None = None
    fecha_evidencia: str | None = None
    fecha_caducidad: str | None = None
    vigente: bool | None = None


class StepDeliverablesResponse(BaseModel):
    """Lista deliverables per step · admin/cliente."""

    project_id: uuid.UUID
    template_id: str
    template_title: str
    deliverable_codes: list[str]
    deliverables: list[DeliverableState]
    counts: dict[str, int]  # {available, needs_regen, missing}


class DeliverablesServiceError(ValueError):
    """Errores del service deliverables."""


class WorkflowDeliverablesService:
    """Service · matching deliverable_codes → Evidence Vault."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_step_deliverables(
        self, project_id: uuid.UUID, template_id: str,
    ) -> StepDeliverablesResponse:
        """List deliverables per step + match Evidence Vault status."""
        template = get_template_by_id(template_id)
        if template is None:
            raise DeliverablesServiceError(
                f"Template {template_id} not found",
            )

        codes = list(template.deliverable_codes or [])
        states: list[DeliverableState] = []

        for code in codes:
            row = await self.db.execute(
                text(
                    "SELECT id, fichero_nombre_original, fichero_mime_type, "
                    "fichero_tamano_bytes, hash_sha256, "
                    "fecha_evidencia, fecha_caducidad, vigente "
                    "FROM evidence "
                    "WHERE project_id = :pid "
                    "AND deleted_at IS NULL "
                    "AND (evidence_type_id = :code OR measure_code = :code) "
                    "ORDER BY created_at DESC LIMIT 1"
                ),
                {"pid": str(project_id), "code": code},
            )
            hit = row.first()
            if hit is None:
                states.append(DeliverableState(code=code, status="missing"))
                continue
            vigente = bool(hit[7])
            status: DeliverableStatus = "available" if vigente else "needs_regen"
            states.append(
                DeliverableState(
                    code=code,
                    status=status,
                    evidence_id=hit[0],
                    fichero_nombre_original=hit[1],
                    fichero_mime_type=hit[2],
                    fichero_tamano_bytes=hit[3],
                    hash_sha256=hit[4],
                    fecha_evidencia=hit[5].isoformat() if hit[5] else None,
                    fecha_caducidad=hit[6].isoformat() if hit[6] else None,
                    vigente=vigente,
                )
            )

        counts = {
            "available": sum(1 for s in states if s.status == "available"),
            "needs_regen": sum(1 for s in states if s.status == "needs_regen"),
            "missing": sum(1 for s in states if s.status == "missing"),
        }

        return StepDeliverablesResponse(
            project_id=project_id,
            template_id=template_id,
            template_title=template.title,
            deliverable_codes=codes,
            deliverables=states,
            counts=counts,
        )

    async def get_evidence_file_path(
        self, project_id: uuid.UUID, evidence_id: uuid.UUID,
    ) -> tuple[Path, str, str]:
        """Resolve fichero_path + nombre_original + mime_type para download.

        Returns (path · nombre_original · mime_type).
        Raises DeliverablesServiceError si evidence NO existe en project.
        """
        row = await self.db.execute(
            text(
                "SELECT fichero_path, fichero_nombre_original, fichero_mime_type "
                "FROM evidence "
                "WHERE id = :eid AND project_id = :pid "
                "AND deleted_at IS NULL"
            ),
            {"eid": str(evidence_id), "pid": str(project_id)},
        )
        hit = row.first()
        if hit is None:
            raise DeliverablesServiceError(
                f"Evidence {evidence_id} not in project {project_id}",
            )
        fichero_path, nombre, mime = hit[0], hit[1], hit[2]
        if not fichero_path:
            raise DeliverablesServiceError(
                f"Evidence {evidence_id} has no file path",
            )
        path = Path(fichero_path)
        return path, nombre or "deliverable.bin", mime or "application/octet-stream"
