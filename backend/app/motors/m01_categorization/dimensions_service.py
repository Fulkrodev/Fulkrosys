"""Motor 1 Categorization · Dimensions Service (sub-atom 1.C.D.A.0 v3.8).

Service para gestionar las 19 dimensiones del proyecto.

Source of truth canónico: tabla `projects` (columnas existing + 16 nuevas
añadidas por migration projects_19dims_1c_d_a0_001).

Patterns sostenidos:
  - OPS-043: await db.commit() explícito antes return
  - OPS-008: RLS project-scoped (set_tenant_context cuando aplique)
  - OPS-038: audit cols UUID raw (sin FK · pools auth)
"""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.core import Project

from .dimensions_schemas import (
    ProjectDimensionsRead,
    ProjectDimensionsUpdate,
    compute_dims_captured,
)


class ProjectDimensionsServiceError(ValueError):
    """Errores del service de dimensiones."""


class DimensionsService:
    """Service para gestión 19 dimensiones del proyecto."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_dimensions(
        self, project_id: uuid.UUID,
    ) -> ProjectDimensionsRead:
        """Lee las 19 dimensiones del proyecto.

        Returns ProjectDimensionsRead con indicator dims_captured_count.
        """
        result = await self.db.execute(
            select(Project).where(Project.id == project_id),
        )
        project = result.scalar_one_or_none()
        if project is None:
            raise ProjectDimensionsServiceError(
                f"Project {project_id} not found",
            )

        captured = compute_dims_captured(project)

        return ProjectDimensionsRead(
            categoria_objetivo=project.categoria_objetivo,
            archetype=project.archetype,
            fase=project.fase,
            tamano_empleados=project.tamano_empleados,
            madurez_ens_actual=project.madurez_ens_actual,
            geografia_operacion=project.geografia_operacion,
            procesa_datos_sensibles_rgpd9=project.procesa_datos_sensibles_rgpd9,
            aplica_nis2=project.aplica_nis2,
            aplica_dora=project.aplica_dora,
            aplica_ai_act=project.aplica_ai_act,
            dpo_designado=project.dpo_designado,
            arquitectura_sistemas=project.arquitectura_sistemas,
            multi_tenancy=project.multi_tenancy,
            equipo_ti_tamano=project.equipo_ti_tamano,
            certificaciones_previas=list(project.certificaciones_previas or []),
            urgencia_certificacion=project.urgencia_certificacion,
            presupuesto_disponible=project.presupuesto_disponible,
            compromiso_interno=project.compromiso_interno,
            horas_cliente_semana=project.horas_cliente_semana,
            dims_captured_count=captured,
        )

    async def update_dimensions(
        self,
        project_id: uuid.UUID,
        payload: ProjectDimensionsUpdate,
        updated_by: uuid.UUID,
    ) -> ProjectDimensionsRead:
        """Update parcial de las 19 dimensiones (excluye fase/categoria/archetype).

        OPS-043 sostenido: await db.commit() explícito.
        """
        result = await self.db.execute(
            select(Project).where(Project.id == project_id),
        )
        project = result.scalar_one_or_none()
        if project is None:
            raise ProjectDimensionsServiceError(
                f"Project {project_id} not found",
            )

        # Apply only fields provided (model_dump exclude_unset=True)
        updates = payload.model_dump(exclude_unset=True)
        for field, value in updates.items():
            setattr(project, field, value)

        # updated_by audit column (FullMixin)
        project.updated_by = updated_by

        await self.db.commit()  # OPS-043 sostenido
        await self.db.refresh(project)

        return await self.get_dimensions(project_id)

    async def patch_dimensions_partial(
        self,
        project_id: uuid.UUID,
        partial_dict: dict[str, Any],
        updated_by: uuid.UUID,
    ) -> ProjectDimensionsRead:
        """Helper para callers que necesitan update light (m13 · m_meetings · m16).

        Útil cuando upstream motor captura subset dims y los persiste sin
        ir vía Pydantic full schema. Validation Pydantic vía ProjectDimensionsUpdate.
        """
        validated = ProjectDimensionsUpdate.model_validate(partial_dict)
        return await self.update_dimensions(
            project_id=project_id,
            payload=validated,
            updated_by=updated_by,
        )
