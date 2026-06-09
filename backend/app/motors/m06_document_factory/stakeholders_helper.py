"""Stakeholders ENS auto-populate helper · SAN-E v3.MB-5.0.bis.

Helpers consumibles por templates M6 Document Factory para inyectar los
stakeholders ENS_REQUIRED (sponsor + 5 RD 311/2022 art. 11) en el context
Jinja2/render_docx pre-generación.

Uso desde caller (típicamente API endpoint o agente generador):

    from backend.app.motors.m06_document_factory.stakeholders_helper import (
        validate_ens_required_roles_assigned,
        get_stakeholders_context,
    )

    # 1. Validate antes de generar
    validation = await validate_ens_required_roles_assigned(
        db, project_id, document_type="E-040"
    )
    if not validation.valid:
        raise StakeholdersIncompleteError(blockers=validation.blockers)

    # 2. Inject context
    stakeholders_ctx = await get_stakeholders_context(db, project_id)
    context.update(stakeholders_ctx)

    # 3. Generate normal
    await DocumentFactoryService(db).generate_document(
        project_id, template_codigo="E-040", context=context, ...
    )
"""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m30_client_contacts.ens_required import (
    DOCUMENTS_REQUIRE_ENS_ROLES,
    ENS_REQUIRED_ROLES,
    ENS_ROLE_LABELS,
)
from backend.app.motors.m30_client_contacts.service import ClientContactService


@dataclass(slots=True)
class ValidationResult:
    valid: bool
    blockers: list[str]
    recoverable: bool  # True si Marcos puede asignar y reintentar


class StakeholdersIncompleteError(Exception):
    """Raised cuando ENS_REQUIRED stakeholders incomplete pre-firma doc ENS."""

    def __init__(
        self,
        message: str,
        *,
        blockers: list[str] | None = None,
        recoverable: bool = True,
    ) -> None:
        super().__init__(message)
        self.blockers = blockers or []
        self.recoverable = recoverable


async def validate_ens_required_roles_assigned(
    db: AsyncSession,
    project_id: UUID,
    document_type: str,
) -> ValidationResult:
    """Verify M30 contacts ENS_REQUIRED fully assigned antes generate/sign doc ENS.

    Si ``document_type`` no esta en ``DOCUMENTS_REQUIRE_ENS_ROLES``, devuelve
    ``valid=True`` sin verificar (doc no requiere stakeholders nombrados).

    Args:
        db: AsyncSession con tenant_context aplicado.
        project_id: UUID del proyecto.
        document_type: codigo template (E-002, E-012, E-040, etc).

    Returns:
        ``ValidationResult`` · ``recoverable=True`` siempre que falten roles
        (Marcos puede asignar y reintentar generacion).
    """
    if document_type not in DOCUMENTS_REQUIRE_ENS_ROLES:
        return ValidationResult(valid=True, blockers=[], recoverable=False)

    service = ClientContactService(db)
    status = await service.get_ens_required_roles_status(project_id)

    if status["all_assigned"]:
        return ValidationResult(valid=True, blockers=[], recoverable=False)

    blockers = [
        f"Asigna {ENS_ROLE_LABELS[role]} antes generar {document_type}"
        for role in status["missing"]
    ]
    return ValidationResult(
        valid=False,
        blockers=blockers,
        recoverable=True,
    )


async def get_stakeholders_context(
    db: AsyncSession,
    project_id: UUID,
) -> dict:
    """Returns dict para inyectar en context Jinja2 templates ENS docs.

    Estructura:

    ``{
        'stakeholders': {
            'sponsor': {
                'label': 'Sponsor / Patrocinador',
                'contact': { contact_id, full_name, email, ... } | None,
                'full_name': str (o '[PENDIENTE ASIGNAR]' si vacio),
                'email': str (o ''),
                'role_title': str (o ''),
            },
            ...6 roles
        },
        'all_assigned': bool,
        'missing_roles': list[str],
    }``
    """
    service = ClientContactService(db)
    status = await service.get_ens_required_roles_status(project_id)

    stakeholders: dict[str, dict] = {}
    for role in ENS_REQUIRED_ROLES:
        contact = status["roles"].get(role)
        stakeholders[role] = {
            "label": ENS_ROLE_LABELS[role],
            "contact": contact,
            "full_name": (
                contact["full_name"] if contact else "[PENDIENTE ASIGNAR]"
            ),
            "email": contact["email"] if contact else "",
            "role_title": contact["role_title"] if contact else "",
        }

    return {
        "stakeholders": stakeholders,
        "all_assigned": status["all_assigned"],
        "missing_roles": status["missing"],
    }
