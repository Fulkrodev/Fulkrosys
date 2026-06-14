"""Alembic environment configuration for FULKRO."""
import os
import sys
from pathlib import Path
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool, engine_from_config

# Ensure the backend package is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1].parent))

# Carga .env del repo root para que DATABASE_MIGRATE_URL (y demás) estén
# disponibles cuando se invoca alembic directo desde una shell que no las
# exportó (verificación adversarial FRENTE K: env.py leía DATABASE_MIGRATE_URL
# SIN cargar .env → caía al sqlalchemy.url stale de alembic.ini → auth fail).
try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[1].parent / ".env")
except Exception:  # pragma: no cover — dotenv ausente = comportamiento previo
    pass

# Import all models so Alembic can detect them
import backend.app.models  # noqa: F401
from backend.app.models.base import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Use DATABASE_MIGRATE_URL if set (allows alembic to use a privileged user
# while the application uses a NOSUPERUSER role for RLS enforcement).
# Falls back to the sqlalchemy.url in alembic.ini for backwards compatibility.
migrate_url = os.environ.get("DATABASE_MIGRATE_URL")
if migrate_url:
    # Convert async URL to sync if needed (alembic uses sync driver)
    sync_url = migrate_url.replace("postgresql+asyncpg://", "postgresql://")
    config.set_main_option("sqlalchemy.url", sync_url)

target_metadata = Base.metadata


# FTS GIN expression-based indexes: declarados solo en migrations
# (op.execute "CREATE INDEX ... USING gin (to_tsvector(...))") porque
# SQLAlchemy/alembic no comparan expressions complejas confiablemente.
# Se excluyen del autogenerate compare para evitar drift fantasma.
_AUTOGEN_EXCLUDE_INDEXES = frozenset({
    "ix_client_contacts_notes_fts",      # M30 client_contacts.notes_marcos
    "ix_client_messages_body_fts",       # M29 client_messages.body_markdown
    "ix_exploratory_meetings_notes_fts", # exploratory_meetings.notes_markdown
})

# SAN-E v3.MB-7.0 drift cleanup · tables creadas SOLO via migration SQL raw
# (NO tienen ORM SQLAlchemy declaration). alembic check las consideraba
# "removed table" porque no estan en Base.metadata. Se excluyen del compare
# hasta que se cree ORM declaration (atom MB-7.0.bis si Marcos prioriza).
_AUTOGEN_EXCLUDE_TABLES = frozenset({
    "audit_schedules",          # SAN-C MB-X · NO ORM model
    "ens_iso27001_mapping",     # seeded data table · NO ORM model
    # Ejecutable 8 Pasada 16 (DB-DRIFT-01): tablas catálogo/raw creadas SOLO por migración
    # o seed, sin ORM declaration (decisión pragmática Marcos · exclusión documentada en vez
    # de declarar 16 ORM models). `alembic check` corre limpio salvo estas exclusiones.
    "assets",                   # MAGERIT catálogo libro2 · seed
    "safeguards",               # MAGERIT salvaguardas catálogo · seed
    "threats",                  # MAGERIT amenazas catálogo · seed
    "asset_dependencies",       # MAGERIT grafo dependencias · seed
    "asset_threats",            # MAGERIT asset-threat join · seed
    "risk_treatments",          # MAGERIT tratamientos · raw
    "applied_safeguards",       # ENS salvaguardas aplicadas · seed/raw
    "ens_reinforcements",       # ENS refuerzos Rn · seed (seed_ens_measure_refuerzos)
    "legal_obligations_catalog",# m_legal catálogo obligaciones · seed
    "lucia_submissions",        # m18/m27 LUCIA federation · raw-SQL (migración 726e561c0cc6)
    "lucia_credentials",        # m27 LUCIA credenciales · raw-SQL
    "client_dashboard_state",   # m21 estado dashboard cliente · raw
    "client_workspaces",        # m20 workspaces · raw
    "global_search_queries",    # búsqueda global · raw/telemetría
    "pricing_config",           # P4-1 fuente única precios · raw-SQL (core/pricing/repository.py) · NO ORM
})


# (ENS Radar retirado del producto · ya no hay tablas radar que excluir.)
_EXCLUDED_TABLES = _AUTOGEN_EXCLUDE_TABLES


def _include_object(object_, name, type_, reflected, compare_to):
    if type_ == "index" and name in _AUTOGEN_EXCLUDE_INDEXES:
        return False
    if type_ == "table" and name in _EXCLUDED_TABLES:
        return False
    # Also skip indexes/constraints on excluded tables
    if hasattr(object_, "table") and object_.table is not None:
        table_name = getattr(object_.table, "name", None)
        if table_name in _EXCLUDED_TABLES:
            return False
    # Ejecutable 8 Pasada 16: skip FK constraints (reflejadas desde la BD) cuyo target es
    # una tabla excluida (p.ej. incidents.fk -> lucia_submissions). El FK existe en BD pero
    # su tabla destino no tiene ORM model, así que no debe reportarse como drift.
    if type_ == "foreign_key_constraint":
        referred = getattr(object_, "referred_table", None)
        referred_name = getattr(referred, "name", None)
        if referred_name in _EXCLUDED_TABLES:
            return False
    return True


def _process_revision_directives(context, revision, directives):
    """Filtra el RUIDO de autogenerate que alembic NO refleja fiablemente, para
    que `alembic check` quede VERDE y FIABLE — capta drift real de tablas/columnas/
    tipos, ignora el ruido conocido (Opción 1 Marcos · rigor pragmático):

      - Índices (create/drop): parciales (WHERE), de expresión/orden (DESC, funcs)
        y regulares · se gestionan por migración EXPLÍCITA (op.create_index), no por
        autogenerate · alembic no compara fiablemente sus predicados/expresiones.
      - Alteraciones SOLO-de-comentario: la BD lleva comentarios doc (canonical
        namespaces, FK lógicos) que el ORM no declara · cosmético, cero esquema.
    """
    from alembic.operations import ops as _ops

    def _strip(container) -> None:
        kept = []
        for op in list(getattr(container, "ops", [])):
            if isinstance(op, (_ops.CreateIndexOp, _ops.DropIndexOp)):
                continue
            if isinstance(op, _ops.AlterColumnOp) and (
                op.modify_type is None
                and op.modify_nullable is None
                and op.modify_server_default is False
            ):
                continue  # comment-only
            if isinstance(op, _ops.ModifyTableOps):
                _strip(op)
                if not op.ops:
                    continue
            kept.append(op)
        container.ops = kept

    for d in directives:
        for _attr in ("upgrade_ops", "downgrade_ops"):
            _container = getattr(d, _attr, None)
            if _container is not None:
                _strip(_container)


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=_include_object,
        process_revision_directives=_process_revision_directives,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=_include_object,
            process_revision_directives=_process_revision_directives,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
