"""M30 · Department service (sub-atom 1.C.F.2).

CRUD project-scoped + suggestions ENS-aware per category (BASICA/MEDIA/ALTA).

Suggestions arquitectura:
- BASICA: 1 área (TI) · perfil consultor autónomo simple
- MEDIA: 2 áreas (TI · COMPLIANCE) · perfil mid + RGPD
- ALTA: 4 áreas (TI · COMPLIANCE · LEGAL · RRHH) · perfil enterprise

Admin puede customizar/skip suggestions desde page · service NO inserta
automaticamente · solo expone catalogo + ``bulk_create_departments``
explícito.

R23 sostener · TODO project-scoped. R28 materializa adaptación per category
(NO hard-coded · admin decide aceptar/customizar).
"""
from __future__ import annotations

import uuid
from collections import defaultdict
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m30_client_contacts.department_models import Department
from backend.app.motors.m30_client_contacts.department_schemas import (
    DepartmentCreate,
    DepartmentSuggestion,
    DepartmentUpdate,
)
from backend.app.motors.m30_client_contacts.models import ClientContact


class DepartmentError(Exception):
    """Error genérico department service (incluye duplicate code)."""


class DepartmentNotFoundError(DepartmentError):
    """Departamento no encontrado por id en este proyecto."""


class DuplicateDepartmentCodeError(DepartmentError):
    """UNIQUE(project_id, code) violado."""


class ContactNotInProjectError(DepartmentError):
    """Contact no pertenece al project del department (cross-project rejected)."""


DEPARTMENT_SUGGESTIONS_PER_CATEGORY: dict[str, list[DepartmentSuggestion]] = {
    "BASICA": [
        DepartmentSuggestion(
            code="TI",
            name="Tecnologías de la Información",
            description=(
                "Operación, mantenimiento y soporte sistemas TI · "
                "interlocutor primario implantación ENS Básica."
            ),
        ),
    ],
    "MEDIA": [
        DepartmentSuggestion(
            code="TI",
            name="Tecnologías de la Información",
            description=(
                "Operación y administración sistemas TI · RSIS y "
                "Administrador de Seguridad típicamente aquí."
            ),
        ),
        DepartmentSuggestion(
            code="COMPLIANCE",
            name="Compliance + RGPD",
            description=(
                "Cumplimiento normativo · DPO · gestión riesgos · "
                "RSEG suele recaer aquí (separación funcional 801)."
            ),
        ),
    ],
    "ALTA": [
        DepartmentSuggestion(
            code="TI",
            name="Tecnologías de la Información",
            description=(
                "Operación, administración y desarrollo sistemas TI · "
                "RSIS + Administrador de Seguridad."
            ),
        ),
        DepartmentSuggestion(
            code="COMPLIANCE",
            name="Compliance + RGPD",
            description=(
                "Cumplimiento normativo, DPO, riesgos · RSEG + POC + "
                "Miembro Comité Seguridad típicamente aquí."
            ),
        ),
        DepartmentSuggestion(
            code="LEGAL",
            name="Legal",
            description=(
                "Asesoría jurídica, contratos, requisitos regulatorios · "
                "interlocutor para LOPDGDD, NIS2, DORA, AI Act."
            ),
        ),
        DepartmentSuggestion(
            code="RRHH",
            name="Recursos Humanos",
            description=(
                "Personal, formación, segregación funcional · gestión "
                "altas/bajas usuarios sistema."
            ),
        ),
    ],
}


def suggest_departments_for_category(
    category: str | None,
) -> list[DepartmentSuggestion]:
    """Sugerencias per categoría ENS · BASICA/MEDIA/ALTA · ``[]`` si None."""
    if category is None:
        return []
    return list(DEPARTMENT_SUGGESTIONS_PER_CATEGORY.get(category.upper(), []))


class DepartmentService:
    """CRUD project-scoped Department · admin-only (require_owner en API)."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_for_project(
        self, project_id: uuid.UUID,
    ) -> list[Department]:
        stmt = (
            select(Department)
            .where(Department.project_id == project_id)
            .order_by(Department.code.asc())
        )
        return list((await self.db.execute(stmt)).scalars())

    async def get_by_id(
        self, project_id: uuid.UUID, department_id: uuid.UUID,
    ) -> Department:
        dept = (await self.db.execute(
            select(Department).where(
                Department.id == department_id,
                Department.project_id == project_id,
            )
        )).scalar_one_or_none()
        if dept is None:
            raise DepartmentNotFoundError(
                f"Department {department_id} no encontrado en project {project_id}"
            )
        return dept

    async def create(
        self,
        project_id: uuid.UUID,
        payload: DepartmentCreate,
    ) -> Department:
        dept = Department(
            project_id=project_id,
            code=payload.code.strip().upper(),
            name=payload.name.strip(),
            description=payload.description,
        )
        self.db.add(dept)
        try:
            await self.db.flush()
        except IntegrityError as exc:
            await self.db.rollback()
            raise DuplicateDepartmentCodeError(
                f"Ya existe departamento con code={payload.code!r} en este proyecto"
            ) from exc
        return dept

    async def update(
        self,
        project_id: uuid.UUID,
        department_id: uuid.UUID,
        payload: DepartmentUpdate,
    ) -> Department:
        dept = await self.get_by_id(project_id, department_id)
        data = payload.model_dump(exclude_unset=True)
        for k, v in data.items():
            setattr(dept, k, v)
        await self.db.flush()
        return dept

    async def delete(
        self, project_id: uuid.UUID, department_id: uuid.UUID,
    ) -> None:
        dept = await self.get_by_id(project_id, department_id)
        await self.db.delete(dept)
        await self.db.flush()

    async def assign_contact(
        self,
        project_id: uuid.UUID,
        contact_id: uuid.UUID,
        department_id: uuid.UUID | None,
    ) -> ClientContact:
        """Assigna contact a department (o None para des-asignar).

        Validaciones cross-project:
          - contact.project_id == project_id (o contact.project_id None
            permitido y se promueve a project_id)
          - department.project_id == project_id (si department_id no None)

        Raises:
          - DepartmentNotFoundError si department_id no en project
          - ContactNotInProjectError si contact no pertenece al project
        """
        contact = await self._get_contact_in_project(project_id, contact_id)

        if department_id is not None:
            await self.get_by_id(project_id, department_id)
            contact.department_id = department_id
        else:
            contact.department_id = None
        await self.db.flush()
        return contact

    async def bulk_assign_contacts(
        self,
        project_id: uuid.UUID,
        department_id: uuid.UUID,
        contact_ids: Sequence[uuid.UUID],
    ) -> list[ClientContact]:
        """Asigna múltiples contacts al mismo department · valida todos."""
        await self.get_by_id(project_id, department_id)
        updated: list[ClientContact] = []
        for cid in contact_ids:
            contact = await self._get_contact_in_project(project_id, cid)
            contact.department_id = department_id
            updated.append(contact)
        await self.db.flush()
        return updated

    async def list_contacts_for_department(
        self,
        project_id: uuid.UUID,
        department_id: uuid.UUID,
    ) -> list[ClientContact]:
        """Empleados asignados a un department · ordered por full_name."""
        await self.get_by_id(project_id, department_id)
        stmt = (
            select(ClientContact)
            .where(
                ClientContact.department_id == department_id,
                ClientContact.deleted_at.is_(None),
            )
            .order_by(ClientContact.full_name.asc())
        )
        return list((await self.db.execute(stmt)).scalars())

    async def report_per_area(
        self, project_id: uuid.UUID,
    ) -> dict:
        """Counts empleados per department + breakdown role_category + unassigned.

        Returns:
            {
              "project_id": str,
              "departments": [
                {
                  "department_id": str, "code": str, "name": str,
                  "total_contacts": int,
                  "by_role_category": {"rseg": 2, "tecnico": 5, ...}
                }, ...
              ],
              "unassigned": {
                "total_contacts": int,
                "by_role_category": {...}
              },
              "total_employees": int  # has_portal_access=false
            }
        """
        depts = await self.list_for_project(project_id)
        dept_map = {d.id: d for d in depts}

        contacts_stmt = (
            select(ClientContact)
            .where(
                ClientContact.project_id == project_id,
                ClientContact.deleted_at.is_(None),
                ClientContact.has_portal_access.is_(False),
            )
        )
        contacts = list((await self.db.execute(contacts_stmt)).scalars())

        per_dept: dict[uuid.UUID, dict] = {
            d.id: {
                "department_id": str(d.id),
                "code": d.code,
                "name": d.name,
                "total_contacts": 0,
                "by_role_category": defaultdict(int),
            }
            for d in depts
        }
        unassigned = {
            "total_contacts": 0,
            "by_role_category": defaultdict(int),
        }

        for c in contacts:
            if c.department_id and c.department_id in dept_map:
                bucket = per_dept[c.department_id]
            else:
                bucket = unassigned
            bucket["total_contacts"] += 1
            bucket["by_role_category"][c.role_category] += 1

        # Convert defaultdict to plain dict for JSON serialization.
        for bucket in (*per_dept.values(), unassigned):
            bucket["by_role_category"] = dict(bucket["by_role_category"])

        return {
            "project_id": str(project_id),
            "departments": list(per_dept.values()),
            "unassigned": unassigned,
            "total_employees": len(contacts),
        }

    async def _get_contact_in_project(
        self, project_id: uuid.UUID, contact_id: uuid.UUID,
    ) -> ClientContact:
        contact = (await self.db.execute(
            select(ClientContact).where(
                ClientContact.id == contact_id,
                ClientContact.deleted_at.is_(None),
            )
        )).scalar_one_or_none()
        if contact is None:
            raise ContactNotInProjectError(
                f"Contact {contact_id} no encontrado"
            )
        # contact.project_id puede ser None (legacy client-scoped) OR
        # debe coincidir con project_id. Para departments scope, exigimos
        # match exacto.
        if contact.project_id != project_id:
            raise ContactNotInProjectError(
                f"Contact {contact_id} no pertenece al project {project_id}"
            )
        return contact

    async def bulk_create(
        self,
        project_id: uuid.UUID,
        items: Sequence[DepartmentCreate],
    ) -> list[Department]:
        """Crea N departments en una transacción · skipea duplicados existentes.

        Ideal para flujo "aceptar sugerencias B/M/A" desde admin: si el
        admin re-clica el banner, los códigos ya creados se omiten en
        lugar de fallar.
        """
        existing = {
            d.code: d for d in await self.list_for_project(project_id)
        }
        created: list[Department] = []
        for item in items:
            code = item.code.strip().upper()
            if code in existing:
                continue
            dept = Department(
                project_id=project_id,
                code=code,
                name=item.name.strip(),
                description=item.description,
            )
            self.db.add(dept)
            created.append(dept)
        await self.db.flush()
        return created
