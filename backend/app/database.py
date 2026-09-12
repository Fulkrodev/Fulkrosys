"""Database configuration — SQLAlchemy 2.0 async."""
import uuid
from typing import AsyncGenerator

from sqlalchemy import event, text
from sqlalchemy.orm import Session as SyncSession
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from backend.app.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    echo=(not settings.is_production),
    pool_size=20,
    max_overflow=10,
    # Resiliencia del pool (auditoría 2026-06-07 · "no tumbar el sistema"):
    pool_pre_ping=True,   # descarta conexiones muertas (recupera tras corte de PG)
    pool_recycle=1800,    # recicla a los 30 min (evita server-side idle timeout)
    pool_timeout=30,      # falla rápido si el pool está agotado (NO cuelga la app)
)

async_session = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


# ─────────────────────────────────────────────────────────────────────────────
# Q2 · el contexto de inquilino es de la SESION, no de una transaccion
#
# EL FALLO QUE ARREGLA
#     `set_config(..., true)` fija la variable con is_local=true: su alcance es
#     la TRANSACCION en curso. `commit()` la termina, y con ella se borra el
#     GUC. Todo lo que venga despues abre una transaccion NUEVA sin contexto:
#     para las policias RLS ese usuario no es de ningun inquilino y no ve NADA,
#     ni siquiera la fila que acaba de escribir.
#
#     El sintoma tipico es `db.refresh(obj)` justo detras de `db.commit()`: el
#     SELECT del refresh no encuentra la fila, SQLAlchemy levanta
#     "Could not refresh instance", FastAPI responde 500 -- y la operacion YA
#     ESTA GUARDADA. El usuario ve un error, vuelve a darle al boton y duplica.
#     La huella quedo en la base del demo: un proyecto llamado
#     `DUPLICADO-CLAUDE`, creado dos veces por esta via.
#
#     Hay 30 parejas `commit()` -> `refresh()` en backend/app. Quitarlas una a
#     una arregla las de hoy; la trigesimo primera que alguien escriba manyana
#     vuelve a romper, porque nada impide escribirla.
#
# POR QUE NO SE ARREGLA CON is_local=false
#     Porque entonces el GUC vive lo que viva la CONEXION, y las conexiones se
#     reciclan en el pool: la siguiente peticion, de otro cliente, heredaria el
#     contexto del anterior. Eso no es un 500, es una fuga entre inquilinos.
#
# COMO SE ARREGLA
#     Guardando quien es el inquilino EN LA SESION y volviendolo a aplicar al
#     empezar cada transaccion. El GUC sigue siendo transaccional (no se puede
#     filtrar por el pool) y aun asi sobrevive a un commit, porque se vuelve a
#     poner. Es la garantia puesta en el sitio donde no se puede esquivar
#     escribiendo otra consulta.
# ─────────────────────────────────────────────────────────────────────────────

_CLAVE_RLS = "fulkro_rls"


def _aplicar_contexto(connection, datos: dict) -> None:
    """Escribe los GUC del inquilino en la transaccion que acaba de empezar."""
    if datos.get("client_id"):
        connection.execute(
            text("SELECT set_config('app.current_client_id', :cid, true)"),
            {"cid": str(datos["client_id"])},
        )
    if datos.get("project_id"):
        connection.execute(
            text("SELECT set_config('app.current_project_id', :pid, true)"),
            {"pid": str(datos["project_id"])},
        )


@event.listens_for(SyncSession, "after_begin")
def _reaplicar_contexto_rls(session, transaction, connection) -> None:
    datos = session.info.get(_CLAVE_RLS)
    if datos:
        _aplicar_contexto(connection, datos)


async def set_tenant_context(
    session: AsyncSession,
    client_id: uuid.UUID | None = None,
    project_id: uuid.UUID | None = None,
) -> None:
    """Set RLS context variables for the current session.

    Uses set_config() PostgreSQL function instead of SET LOCAL because
    set_config() supports bind parameters with asyncpg, while SET LOCAL
    requires literal values. Functionally equivalent: third parameter
    `true` means is_local=true (scope is the current transaction).

    Reference: https://www.postgresql.org/docs/current/functions-admin.html

    WAVE C3 (tracker §2.2 line 228): las policies RLS leen este GUC con ~3 formas
    equivalentes (``current_project_id()`` canónica vs ``current_setting`` raw vs
    el bypass admin ``current_role_pool='marcos'``). La convención canónica está
    documentada en ``backend/app/auth/tenant_scope`` (no se reescriben las ~244
    referencias existentes · diferido a tarea RLS dedicada post-piloto).
    """
    # Q2 · se RECUERDA en la sesion antes de aplicarlo, para que el listener
    # `after_begin` lo vuelva a poner en cada transaccion posterior (un commit
    # borra los GUC transaccionales y deja ciega a la propia sesion que acaba
    # de escribir). Se acumula: llamar solo con project_id no borra el client_id
    # ya fijado.
    datos = dict(session.info.get(_CLAVE_RLS) or {})
    if client_id:
        datos["client_id"] = str(uuid.UUID(str(client_id)))
    if project_id:
        datos["project_id"] = str(uuid.UUID(str(project_id)))
    session.info[_CLAVE_RLS] = datos

    if client_id:
        await session.execute(
            text("SELECT set_config('app.current_client_id', :cid, true)"),
            {"cid": str(client_id)},
        )
    if project_id:
        await session.execute(
            text("SELECT set_config('app.current_project_id', :pid, true)"),
            {"pid": str(project_id)},
        )


async def clear_tenant_context(session: AsyncSession) -> None:
    """Olvida el inquilino de esta sesion (y deja de reaplicarlo).

    No hace falta en el ciclo normal de peticion --cada peticion trae su propia
    sesion-- pero si cuando una tarea de fondo reutiliza una sesion para varios
    proyectos: ahi el olvido tiene que ser explicito.
    """
    session.info.pop(_CLAVE_RLS, None)
