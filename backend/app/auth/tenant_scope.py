"""Tenant-scope central helper (R07 · DRY).

Reúne el patrón duplicado en 11+ ficheros (``_ensure_project_belongs_to_client``
/ ``_verify_project_belongs_to_client``): valida que el cliente es dueño del
proyecto Y fija el contexto RLS de la transacción, en un único sitio.

Contexto de seguridad: con las políticas RLS fail-CLOSED (R06/R08), un endpoint
del pool cliente que olvide fijar el contexto YA no fuga datos de otro tenant
(la policy devuelve 0 filas). Centralizar este patrón evita ese fallo silencioso
(endpoint que de repente "no ve nada") y reduce el riesgo de regresión en
endpoints nuevos: una sola llamada hace la autorización + el contexto correctos.

Uso típico en un endpoint del pool cliente::

    @client_router.post("/algo")
    async def crear_algo(
        body: AlgoRequest,
        db: AsyncSession = Depends(get_db),
        user: ClientUser = Depends(get_current_client_user),
    ):
        await ensure_client_project_scope(db, body.project_id, user.client_id)
        ...  # a partir de aquí las queries quedan aisladas al proyecto

Convenciones RLS canónicas (WAVE C3 · tracker §2.2 line 228 · SOLO documentación)
----------------------------------------------------------------------------------
En las políticas RLS de las migraciones coexisten ~3 formas de leer el contexto
de tenant. Todas son SEMÁNTICAMENTE EQUIVALENTES y aíslan correctamente; la
fragmentación es histórica, no un fallo de seguridad. Para migraciones NUEVAS
úsese la forma canónica (1):

  (1) CANÓNICA · ``project_id = current_project_id()``
      donde ``current_project_id()`` ≡
      ``SELECT NULLIF(current_setting('app.current_project_id', true), '')::uuid``
      (función SQL · cast UUID · unset/empty → NULL → 0 filas fail-closed).

  (2) EQUIVALENTE (legado · NO reescribir) · ``project_id::text =
      current_setting('app.current_project_id', true)`` — misma semántica vía
      comparación de texto en lugar del cast UUID.

  (3) BYPASS ADMIN LEGÍTIMO (distinto propósito · MANTENER) ·
      ``current_setting('app.current_role_pool', true) = 'marcos'`` — habilita
      el acceso cross-tenant del pool admin/Marcos en policies concretas. NO es
      una convención de aislamiento cliente: es un permiso explícito de admin.

El GUC de contexto (``app.current_project_id`` / ``app.current_client_id``) lo
fija ``database.set_tenant_context`` (vía ``set_config(..., is_local=true)``);
``app.current_role_pool`` lo fijan los routers admin (p.ej. retainer/api.py,
notifications/api.py). NO se reescriben las ~244 referencias existentes (riesgo
alto, valor bajo): la unificación queda diferida a una tarea RLS dedicada
post-piloto.
"""
from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import set_tenant_context


async def ensure_client_project_scope(
    db: AsyncSession,
    project_id: uuid.UUID,
    client_id: uuid.UUID,
) -> uuid.UUID:
    """Valida ownership (project ∈ client) y fija el contexto RLS. Devuelve client_id.

    Args:
        db: sesión async del pool cliente (rol ``fulkro_app``, NOBYPASSRLS).
        project_id: proyecto sobre el que va a operar el endpoint.
        client_id: cliente autenticado (``user.client_id``).

    Returns:
        El ``client_id`` validado (por conveniencia del caller).

    Raises:
        HTTPException 404: el proyecto no existe.
        HTTPException 403: el proyecto no pertenece al cliente autenticado.

    Efecto: tras validar, fija ``app.current_client_id`` + ``app.current_project_id``
    (transaction-local) para que las políticas RLS fail-closed aíslen por proyecto
    el resto de la transacción.
    """
    row = await db.execute(
        text("SELECT client_id FROM projects WHERE id = :pid"),
        {"pid": str(project_id)},
    )
    hit = row.first()
    if hit is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project no existe",
        )
    if hit[0] != client_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Project no pertenece al cliente del usuario",
        )
    await set_tenant_context(db, client_id=client_id, project_id=project_id)
    return client_id
