"""SAN-D MB-19.11 · Migration data script: magic-links soft-deprecated
→ client_tasks portal records (ADR-042).

Convierte magic-links activos no consumidos con purpose ∈ {ONBOARDING_INICIAL,
APORTE_EVIDENCIA} en ClientTask records portal cliente workspace.

Uso:

    python -m backend.scripts.migrate_magic_links_to_tasks
    python -m backend.scripts.migrate_magic_links_to_tasks --dry-run

Idempotente:
- UNIQUE (magic_link_id) en magic_link_migration_log evita duplicados.
- Re-run safe (skip rows ya procesadas).

Strategy per magic-link:
1. Si magic_link_migration_log row existe (magic_link_id) · skip.
2. Si magic_link.consumed/expired/revoked · skip + log "kept_one_shot".
3. Find ClientUser asociado al project (primer ClientUser activated).
4. Si NO ClientUser yet (lead phase · convertido_a_proyecto pre-onboarding) ·
   log "pending_review" (manual cuando cliente onboarding completed).
5. Si ClientUser existe · create ClientTask:
   - template_id: `{template_prefix}_{ml_id_short}` (UNIQUE preserved)
   - phase: project.fase actual o YAML default
   - title/description/cta_*: YAML mapping
   - metadata_jsonb: {migrated_from_magic_link, original_purpose, migrated_at}
6. Revoke magic_link (revocado=True · revoke_reason="migrated_to_portal_task").
7. Insert magic_link_migration_log row con action="converted_to_task".

Stats output dict · Marcos ejecuta manual + revisa output.

Refs:
- ADR-042 · MagicLinkPolicyEnforcer DEPRECATED_SOFT_PURPOSES
- backend/app/motors/m12_magic_link/migration_mappings.yaml
- backend/app/motors/m21_portal_cliente/models_tasks.py:ClientTask
- backend/app/motors/m12_magic_link/models_migration_log.py:MagicLinkMigrationLog
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from backend.app.config import get_settings
from backend.app.models.client_portal import ClientUser
from backend.app.models.core import Project
from backend.app.models.operations import MagicLink
from backend.app.motors.m12_magic_link.models_migration_log import (
    MagicLinkMigrationLog,
)
from backend.app.motors.m12_magic_link.policy_enforcer import (
    DEPRECATED_SOFT_PURPOSES,
)
from backend.app.motors.m12_magic_link.purposes import MagicLinkPurpose
from backend.app.motors.m21_portal_cliente.models_tasks import ClientTask


logger = logging.getLogger(__name__)


_MAPPINGS_PATH = (
    Path(__file__).resolve().parents[1]
    / "app" / "motors" / "m12_magic_link" / "migration_mappings.yaml"
)


def load_migration_mappings() -> dict[str, dict[str, Any]]:
    """Carga YAML mappings purpose → ClientTask template config."""
    with open(_MAPPINGS_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data or {}


# ──────────────────────────────────────────────────────────────────
# Core async migration logic (testeable)
# ──────────────────────────────────────────────────────────────────


async def run_migration(
    db: AsyncSession,
    *,
    dry_run: bool = False,
    batch_limit: int = 200,
) -> dict[str, Any]:
    """Ejecuta migration idempotente · invocable desde CLI o tests.

    Args:
        db: AsyncSession activa.
        dry_run: si True · log decisions sin escribir BD (preview).
        batch_limit: max magic-links por run.

    Returns:
        Stats dict:
          {
            "converted_count": int,
            "pending_review_count": int,
            "kept_one_shot_count": int,
            "revoked_obsolete_count": int,
            "skipped_already_processed": int,
            "errors": int,
            "dry_run": bool,
            "started_at": str ISO,
            "finished_at": str ISO,
          }
    """
    started_at = datetime.now(timezone.utc)
    stats: dict[str, Any] = {
        "converted_count": 0,
        "pending_review_count": 0,
        "kept_one_shot_count": 0,
        "revoked_obsolete_count": 0,
        "skipped_already_processed": 0,
        "errors": 0,
        "dry_run": dry_run,
        "started_at": started_at.isoformat(),
        "finished_at": None,
    }

    mappings = load_migration_mappings()
    deprecated_values = {p.value for p in DEPRECATED_SOFT_PURPOSES}

    # SET LOCAL ROLE para bypass RLS (admin script · conecta como fulkro_app)
    # fulkro_app_bypassrls = NOSUPERUSER+BYPASSRLS (auditoría 2026-06-07 · NO superuser)
    from sqlalchemy import text as _text
    await db.execute(_text("SET LOCAL ROLE fulkro_app_bypassrls"))

    # Pull MagicLinks deprecated soft no consumidos · activos
    stmt = (
        select(MagicLink)
        .where(MagicLink.tipo_operacion.in_(deprecated_values))
        .where(MagicLink.deleted_at.is_(None))
        .where(MagicLink.revocado.is_(False))
        .where(MagicLink.expira_at > datetime.now(timezone.utc))
        .order_by(MagicLink.created_at.asc())
        .limit(batch_limit)
    )
    candidates = list((await db.scalars(stmt)).all())

    for ml in candidates:
        try:
            await _process_one(
                db, ml, mappings, stats, dry_run=dry_run,
            )
        except Exception as exc:
            logger.exception(
                "migrate_magic_links_to_tasks · ML %s falló · %s",
                ml.id, exc,
            )
            stats["errors"] += 1

    if not dry_run:
        await db.commit()

    stats["finished_at"] = datetime.now(timezone.utc).isoformat()
    logger.info(
        "migrate_magic_links_to_tasks completed · %s",
        stats,
    )
    return stats


async def _process_one(
    db: AsyncSession,
    ml: MagicLink,
    mappings: dict[str, dict[str, Any]],
    stats: dict[str, Any],
    *,
    dry_run: bool,
) -> None:
    """Procesa un magic-link · update stats · escribe BD si NO dry_run."""
    # Idempotencia · check log row existing
    existing_log = (await db.scalars(
        select(MagicLinkMigrationLog).where(
            MagicLinkMigrationLog.magic_link_id == ml.id,
        ).limit(1),
    )).first()
    if existing_log:
        stats["skipped_already_processed"] += 1
        return

    # Map purpose key (uppercase YAML keys)
    purpose_key = MagicLinkPurpose(ml.tipo_operacion).name
    mapping = mappings.get(purpose_key)
    if not mapping:
        # Purpose deprecated en ADR-042 pero sin YAML mapping · marcar revoked_obsolete
        stats["revoked_obsolete_count"] += 1
        if not dry_run:
            ml.revocado = True
            ml.revoked_at = datetime.now(timezone.utc)
            db.add(MagicLinkMigrationLog(
                id=uuid.uuid4(),
                magic_link_id=ml.id,
                original_purpose=ml.tipo_operacion,
                migration_action="revoked_obsolete",
                target_task_id=None,
                notes="No YAML mapping · revoked obsolete",
                processed_at=datetime.now(timezone.utc),
            ))
        return

    # Find ClientUser asociado al project
    client_user_stmt = (
        select(ClientUser)
        .join(Project, Project.client_id == ClientUser.client_id)
        .where(Project.id == ml.project_id)
        .where(ClientUser.deactivated_at.is_(None))
        .where(ClientUser.deleted_at.is_(None))
        .order_by(ClientUser.created_at.asc())
        .limit(1)
    )
    client_user = (await db.scalars(client_user_stmt)).first()

    if not client_user:
        # Lead phase · no client_user yet · log pending_review
        stats["pending_review_count"] += 1
        if not dry_run:
            db.add(MagicLinkMigrationLog(
                id=uuid.uuid4(),
                magic_link_id=ml.id,
                original_purpose=ml.tipo_operacion,
                migration_action="pending_review",
                target_task_id=None,
                notes=(
                    f"No ClientUser asociado al project {ml.project_id} · "
                    f"esperando onboarding cliente completed para migration "
                    f"manual"
                ),
                processed_at=datetime.now(timezone.utc),
            ))
        return

    # Resolver Project · phase actual (fallback YAML default)
    project = await db.get(Project, ml.project_id)
    if project is None:
        stats["errors"] += 1
        return

    target_phase = project.fase or mapping.get("phase", "onboarding")

    # Construir template_id UNIQUE per magic_link
    ml_short = str(ml.id)[:8]
    template_id = f"{mapping['template_prefix']}_{ml_short}"

    # Construir cta_url con project_id
    cta_url = (
        mapping.get("cta_url_template", "/client-portal/")
        .replace("{project_id}", str(ml.project_id))
    )

    # Metadata combine YAML extras + migration tracking
    metadata_extras = dict(mapping.get("metadata_extras", {}))
    metadata_extras.update({
        "migrated_from_magic_link": str(ml.id),
        "original_purpose": ml.tipo_operacion,
        "migrated_at": datetime.now(timezone.utc).isoformat(),
        "magic_link_recipient_email": ml.recipient_email,
    })

    if dry_run:
        stats["converted_count"] += 1
        return

    # Create ClientTask
    task = ClientTask(
        project_id=ml.project_id,
        client_user_id=client_user.id,
        template_id=template_id,
        phase=target_phase,
        title=mapping["title"],
        description=mapping.get("description"),
        cta_label=mapping.get("cta_label"),
        cta_url=cta_url,
        expected_evidence_type=mapping.get("expected_evidence_type"),
        expected_evidence_count=mapping.get("expected_evidence_count", 0),
        priority=mapping.get("priority", 0),
        status="pending",
        metadata_jsonb=metadata_extras,
    )
    db.add(task)
    await db.flush()

    # Revoke magic_link
    ml.revocado = True
    ml.revoked_at = datetime.now(timezone.utc)

    # Audit log row
    db.add(MagicLinkMigrationLog(
        id=uuid.uuid4(),
        magic_link_id=ml.id,
        original_purpose=ml.tipo_operacion,
        migration_action="converted_to_task",
        target_task_id=task.id,
        notes=(
            f"Migrated to portal task · template_id={template_id} · "
            f"phase={target_phase}"
        ),
        processed_at=datetime.now(timezone.utc),
    ))

    stats["converted_count"] += 1


# ──────────────────────────────────────────────────────────────────
# CLI entry point
# ──────────────────────────────────────────────────────────────────


async def _main(args: argparse.Namespace) -> dict[str, Any]:
    """Main CLI · wrapper crea engine + sesión propia."""
    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=False)
    try:
        async with engine.connect() as conn:
            trans = await conn.begin()
            try:
                async with AsyncSession(
                    bind=conn, expire_on_commit=False,
                ) as db:
                    stats = await run_migration(
                        db,
                        dry_run=args.dry_run,
                        batch_limit=args.batch_limit,
                    )
                    if args.dry_run:
                        await trans.rollback()
                    else:
                        await trans.commit()
            except Exception:
                await trans.rollback()
                raise
    finally:
        await engine.dispose()
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "SAN-D MB-19.11 migrate magic-links soft-deprecated → "
            "client_tasks portal (ADR-042)"
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview decisions sin escribir BD",
    )
    parser.add_argument(
        "--batch-limit",
        type=int,
        default=200,
        help="Max magic-links per run (default 200)",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    stats = asyncio.run(_main(args))
    print(stats)


if __name__ == "__main__":
    main()
