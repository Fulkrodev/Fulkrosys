"""Database configuration — SQLAlchemy 2.0 async."""
import uuid
from typing import AsyncGenerator

from sqlalchemy import text
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
