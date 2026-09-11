"""Exige que quien ejecuta un acto sea el titular del rol ENS que lo tiene asignado.

POR QUE EXISTE
    RD 311/2022 art. 11.1: "En los sistemas de informacion se diferenciara el
    responsable de la informacion, el responsable del servicio, el responsable
    de la seguridad y el responsable del sistema." El 11.3 remite a la politica
    de seguridad para las atribuciones de cada uno.

    Si el sistema deja aprobar un acto a nombre de cualquiera, esa
    diferenciacion no existe en la practica: queda como un campo de texto.

    Caso concreto que lo motiva: `POST /dda/projects/{id}/freeze` recibia
    `aprobado_por: str = Query(..., description="Nombre del RSEG que aprueba")`
    y no comprobaba nada. La DdA quedaba congelada a nombre de quien se
    escribiera, aunque no fuera el Responsable de la Seguridad del proyecto o
    no existiera como contacto.

ALCANCE, DICHO CON PRECISION
    Esto NO es autenticacion. El endpoint ya esta tras `require_owner` (router
    Marcos-only, ADR-013). Lo que anyade es que el NOMBRE que se atribuye el
    acto corresponda al contacto que tiene ese rol ENS asignado en el proyecto.
    Es trazabilidad ENAC: que la firma apunte a quien la norma hace responsable.
"""
from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m30_client_contacts.ens_required import (
    ENS_ROLE_LABELS,
    EnsRequiredRole,
)


def _normaliza(nombre: str) -> str:
    """Compara nombres sin castigar espacios ni mayusculas."""
    return " ".join((nombre or "").split()).casefold()


async def titular_del_rol(
    db: AsyncSession,
    project_id: uuid.UUID,
    rol: EnsRequiredRole,
) -> str | None:
    """Nombre del contacto activo con ese rol ENS en el proyecto, o None."""
    fila = (await db.execute(sa_sql := sa_text(
        "SELECT c.full_name FROM client_contacts c "
        "JOIN projects p ON p.client_id = c.client_id "
        "WHERE p.id = :pid AND c.role_ens_required = :rol "
        "  AND c.is_active IS TRUE AND c.deleted_at IS NULL "
        "ORDER BY c.created_at LIMIT 1"
    ), {"pid": str(project_id), "rol": rol})).first()
    del sa_sql
    return fila[0] if fila else None


async def require_ens_role(
    db: AsyncSession,
    project_id: uuid.UUID,
    rol: EnsRequiredRole,
    nombre_declarado: str,
) -> str:
    """Comprueba que `nombre_declarado` es el titular de `rol` en el proyecto.

    Returns:
        El nombre canonico del titular (el que consta en el contacto), para que
        el acto se registre con la grafia buena y no con la que se tecleo.

    Raises:
        HTTPException 403 si no hay titular asignado o si el nombre no coincide.
    """
    etiqueta = ENS_ROLE_LABELS[rol]
    titular = await titular_del_rol(db, project_id, rol)

    if titular is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"No hay {etiqueta} ({rol}) asignado en este proyecto. "
                "El RD 311/2022 (art. 11) exige responsabilidades diferenciadas: "
                "sin titular nombrado no se puede atribuir este acto a nadie. "
                "Asigna el rol en Contactos del cliente y vuelve a intentarlo."
            ),
        )

    if _normaliza(titular) != _normaliza(nombre_declarado):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"'{nombre_declarado}' no es el {etiqueta} ({rol}) de este "
                f"proyecto. Este acto solo puede aprobarlo quien tiene ese rol "
                f"asignado (RD 311/2022 art. 11)."
            ),
        )

    return titular


async def require_ens_role_asignado(
    db: AsyncSession,
    project_id: uuid.UUID,
    rol: EnsRequiredRole,
) -> str:
    """Resuelve el titular del rol y falla con 403 si no hay ninguno.

    Variante para actos que NO reciben el nombre del aprobador: en vez de
    validar una cadena que alguien teclea, el backend RESUELVE quien es y
    atribuye el acto. Es preferible al campo de texto siempre que se pueda:
    no hay grafia que equivocar ni contrato de API que cambiar, y es imposible
    atribuir el acto a quien no tiene el rol.

    Lo usa `POST /magerit/analysis/{id}/freeze` (aprobar el analisis de
    riesgos), que hasta el bloque N no atribuia el acto a nadie.
    """
    etiqueta = ENS_ROLE_LABELS[rol]
    titular = await titular_del_rol(db, project_id, rol)
    if titular is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"No hay {etiqueta} ({rol}) asignado en este proyecto. "
                "El RD 311/2022 exige responsabilidades diferenciadas (art. 11) "
                "y que la auditoria pueda constatar la aprobacion del analisis "
                "de riesgos (Anexo III punto 1.d): sin titular nombrado no se "
                "puede atribuir este acto a nadie. Asigna el rol en Contactos "
                "del cliente y vuelve a intentarlo."
            ),
        )
    return titular
