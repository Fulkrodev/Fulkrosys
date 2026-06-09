"""V-CHECK Sesion 8 Paso 4 — Demo Lifecycle cierre honesto sin retainer.

Flujo completo sobre cliente sintetico "Bufete Legal Test SL":

a) Marcos crea cliente + proyecto + certificacion
b) Marcos dispara offer_retainer -> magic link TTL 30d
c) Cliente rechaza -> start_grace_period 240 dias
d) Verificar project.lifecycle_state = ENDED_CHURN
e) Cliente sigue con acceso read-only (scopes del portal)
f) Fast-forward dia 150 -> warning_sent a Marcos
g) Fast-forward dia 180 -> reconsideration_sent al cliente
h) Fast-forward dia 210 -> backup ZIP firmado + magic link TTL 60d
i) Verificar ZIP contiene: facturas + documentos + audit_log + manifest
j) Fast-forward dia 240 -> data_deleted (soft project, hard personal)
k) Verificar retencion: audit_log + archived_backups + eventos
l) Reactivar dia 270 (dentro ventana 60d) -> nuevo project ACTIVE
m) Intentar reactivar tras expiracion -> rechazo

Al final imprime tabla de resultados y codigo de salida 0/1.
"""
from __future__ import annotations

import asyncio
import os
import sys
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

os.environ.setdefault("FULKRO_SKIP_WORKFLOW_GATES", "1")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import select, text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from backend.app.config import get_settings
from backend.app.database import set_tenant_context
from backend.app.models.core import Project
from backend.app.models.lifecycle import (
    ProjectArchivedBackup,
)
from backend.app.motors.m25_lifecycle.backup_builder import (
    verify_backup_signature,
)
from backend.app.motors.m25_lifecycle.lifecycle_paso4 import (
    LifecyclePaso4Service,
    process_grace_period_checkpoints,
)


RESULTS: list[tuple[str, bool, str]] = []


def report(label: str, ok: bool, detail: str = "") -> None:
    mark = "\033[32mPASS\033[0m" if ok else "\033[31mFAIL\033[0m"
    print(f"[{mark}] {label}")
    if detail:
        print(f"       {detail}")
    RESULTS.append((label, ok, detail))


# ══════════════════════════════════════════════════════════════════════
# Setup / cleanup idempotente
# ══════════════════════════════════════════════════════════════════════

DEMO_CLIENT_CIF = "B88888888"
DEMO_CLIENT_NAME = "Bufete Legal Test SL (M25 demo)"


async def _exec_ok(conn, sql: str, **params):
    """Ejecuta DELETE aislado en un SAVEPOINT para tolerar FK de tablas
    aun no creadas / inexistentes entre re-runs de migraciones."""
    sp = await conn.begin_nested()
    try:
        await conn.execute(sa_text(sql), params)
        await sp.commit()
    except Exception:
        await sp.rollback()


async def _cleanup(engine) -> None:
    async with engine.begin() as conn:
        await conn.execute(sa_text("SET LOCAL ROLE fulkro"))
        r = await conn.execute(sa_text(
            "SELECT id FROM clients WHERE cif = :cif"
        ), {"cif": DEMO_CLIENT_CIF})
        row = r.first()
        if not row:
            return
        cid = str(row[0])
        # Tablas child-first (project-scoped o referencias a magic_links)
        await _exec_ok(conn,
            "DELETE FROM client_interactions WHERE magic_link_id IN "
            "(SELECT id FROM magic_links WHERE project_id IN "
            "(SELECT id FROM projects WHERE client_id = :cid))",
            cid=cid)
        await _exec_ok(conn,
            "DELETE FROM magic_links WHERE project_id IN "
            "(SELECT id FROM projects WHERE client_id = :cid)", cid=cid)
        await _exec_ok(conn,
            "DELETE FROM project_lifecycle_events WHERE client_id = :cid",
            cid=cid)
        await _exec_ok(conn,
            "DELETE FROM project_archived_backups WHERE client_id = :cid",
            cid=cid)
        await _exec_ok(conn,
            "DELETE FROM invoices WHERE client_id = :cid", cid=cid)
        for tbl in (
            "findings", "evidence", "documents",
            "project_lifecycle_states", "audit_preparation_runs",
            "project_exports", "controls", "dda_entries",
            "onboarding_sessions", "project_plans", "status_reports",
            "nominations", "training_records", "project_risks",
            "collaborative_workspaces", "committee_meetings", "changes",
            "magerit_analyses", "pentest_runs", "categorizations",
            "verification_runs", "discovery_runs",
            "systems", "information_types", "services", "obligations",
        ):
            await _exec_ok(conn,
                f"DELETE FROM {tbl} WHERE project_id IN "
                "(SELECT id FROM projects WHERE client_id = :cid)",
                cid=cid)
        await _exec_ok(conn,
            "DELETE FROM retainer_contracts WHERE client_id = :cid",
            cid=cid)
        await _exec_ok(conn,
            "DELETE FROM projects WHERE client_id = :cid", cid=cid)
        await _exec_ok(conn,
            "DELETE FROM clients WHERE id = :cid", cid=cid)


async def _create_client_and_project(engine) -> tuple[uuid.UUID, uuid.UUID]:
    async with engine.begin() as conn:
        await conn.execute(sa_text("SET LOCAL ROLE fulkro"))
        cid = uuid.uuid4()
        pid = uuid.uuid4()
        await conn.execute(sa_text(
            "INSERT INTO clients (id, nombre, cif, contacto_email, "
            "created_at) VALUES (:id, :nm, :cif, 'rseg@bufete-test.es', now())"
        ), {"id": str(cid), "nm": DEMO_CLIENT_NAME, "cif": DEMO_CLIENT_CIF})
        await conn.execute(sa_text(
            "INSERT INTO projects (id, client_id, nombre, estado, "
            "lifecycle_state, created_at) "
            "VALUES (:id, :cid, 'ENS Base — Bufete Legal', 'active', "
            "'ACTIVE', now())"
        ), {"id": str(pid), "cid": str(cid)})
        # Datos demo (facturas, evidencias, documentos)
        await conn.execute(sa_text(
            "INSERT INTO invoices (id, client_id, project_id, "
            "numero_correlativo, tipo, concepto, total, fecha_emision, "
            "estado_pago, created_at) "
            "VALUES (gen_random_uuid(), :cid, :pid, '2026-001', 'hito', "
            "'Hito 1 categorizacion', 1500, CURRENT_DATE - 200, "
            "'pagado', now() - interval '200 days')"
        ), {"cid": str(cid), "pid": str(pid)})
        await conn.execute(sa_text(
            "INSERT INTO invoices (id, client_id, project_id, "
            "numero_correlativo, tipo, concepto, total, fecha_emision, "
            "estado_pago, created_at) "
            "VALUES (gen_random_uuid(), :cid, :pid, '2026-002', 'hito', "
            "'Hito 2 certificacion', 2500, CURRENT_DATE - 30, "
            "'pagado', now() - interval '30 days')"
        ), {"cid": str(cid), "pid": str(pid)})
        await conn.execute(sa_text(
            "INSERT INTO documents (id, project_id, tipo, nombre, "
            "full_text_content, content_hash, storage_path, created_at) "
            "VALUES (gen_random_uuid(), :pid, 'politica', "
            "'D-001 Politica de Seguridad', "
            "'Texto personal de la politica...', "
            "'aa'||substring(md5(random()::text), 1, 62), "
            "'minio://docs/d001.pdf', now())"
        ), {"pid": str(pid)})
        return cid, pid


async def _run_with_session(engine, fn):
    async with engine.connect() as conn:
        trans = await conn.begin()
        session = AsyncSession(bind=conn, expire_on_commit=False)
        try:
            result = await fn(session)
            await trans.commit()
            return result
        except Exception:
            await trans.rollback()
            raise
        finally:
            await session.close()


# ══════════════════════════════════════════════════════════════════════
# Pasos del demo
# ══════════════════════════════════════════════════════════════════════


async def step_a_setup(engine) -> dict:
    await _cleanup(engine)
    cid, pid = await _create_client_and_project(engine)
    report(
        "a) Cliente + Proyecto creados",
        True, f"client_id={cid} project_id={pid}",
    )
    return {"cid": cid, "pid": pid}


async def step_b_certification(engine, ctx):
    async def _work(db):
        await set_tenant_context(db, client_id=ctx["cid"], project_id=ctx["pid"])
        svc = LifecyclePaso4Service()
        event = await svc.mark_certified(db, ctx["pid"])
        project = (await db.execute(
            select(Project).where(Project.id == ctx["pid"]),
        )).scalar_one()
        assert project.certified_at == date.today()
        assert project.lifecycle_state == "CERTIFIED"
        return event.id
    ev_id = await _run_with_session(engine, _work)
    report("b) Certificacion marcada", True, f"event_id={ev_id}")


async def step_c_offer_retainer_declined(engine, ctx):
    async def _work(db):
        await set_tenant_context(db, client_id=ctx["cid"], project_id=ctx["pid"])
        svc = LifecyclePaso4Service()
        offer = await svc.offer_retainer(
            db, ctx["pid"], recipient_email="rseg@bufete-test.es",
        )
        # Cliente rechaza
        result = await svc.handle_retainer_decision(
            db, ctx["pid"], decision="decline",
        )
        return offer, result
    offer, result = await _run_with_session(engine, _work)
    report(
        "c) Oferta retainer enviada + decision=decline",
        True,
        f"magic_link_id={offer['magic_link_id']} "
        f"grace_event_id={result['grace_period_event_id']}",
    )


async def step_d_grace_state(engine, ctx):
    async def _work(db):
        await set_tenant_context(db, client_id=ctx["cid"], project_id=ctx["pid"])
        project = (await db.execute(
            select(Project).where(Project.id == ctx["pid"]),
        )).scalar_one()
        return project
    project = await _run_with_session(engine, _work)
    ok = (
        project.lifecycle_state == "ENDED_CHURN"
        and project.grace_period_started_at is not None
        and project.grace_period_ends_at is not None
    )
    duration = (
        (project.grace_period_ends_at - project.grace_period_started_at).days
        if project.grace_period_started_at and project.grace_period_ends_at
        else None
    )
    report(
        "d) Grace period iniciado (ENDED_CHURN + 240d)",
        ok and duration and abs(duration - 240) <= 1,
        f"state={project.lifecycle_state} duration_days={duration}",
    )


async def step_e_readonly_access(engine, ctx):
    """En grace el cliente aun tiene acceso via scopes del portal (M21)."""
    async def _work(db):
        await set_tenant_context(db, client_id=ctx["cid"], project_id=ctx["pid"])
        # Un RSEG con role 'lectura_solo' tiene estos scopes
        from backend.app.motors.m21_portal_cliente.scopes import (
            scopes_for_role,
        )
        scopes = scopes_for_role("lectura_solo")
        return scopes
    scopes = await _run_with_session(engine, _work)
    ok = "view_project_summary" in scopes
    report(
        "e) Cliente conserva acceso read-only en grace period",
        ok, f"scopes={scopes}",
    )


async def _fast_forward_grace_start(engine, pid: uuid.UUID, days_ago: int):
    """Re-establece grace_period_started_at para simular dias transcurridos."""
    async with engine.begin() as conn:
        await conn.execute(sa_text("SET LOCAL ROLE fulkro"))
        new_start = datetime.now(timezone.utc) - timedelta(days=days_ago)
        new_end = new_start + timedelta(days=240)
        await conn.execute(sa_text(
            "UPDATE projects SET grace_period_started_at = :s, "
            "grace_period_ends_at = :e "
            "WHERE id = :pid"
        ), {"s": new_start, "e": new_end, "pid": str(pid)})


async def step_f_day_150(engine, ctx):
    await _fast_forward_grace_start(engine, ctx["pid"], 155)

    async def _work(db):
        return await process_grace_period_checkpoints(db)
    result = await _run_with_session(engine, _work)
    ok = str(ctx["pid"]) in result["warning_marcos_sent"]
    report(
        "f) Dia 150+ -> warning_sent a Marcos",
        ok,
        f"warnings_sent={result['warning_marcos_sent']}",
    )


async def step_g_day_180(engine, ctx):
    await _fast_forward_grace_start(engine, ctx["pid"], 185)

    async def _work(db):
        return await process_grace_period_checkpoints(db)
    result = await _run_with_session(engine, _work)
    ok = str(ctx["pid"]) in result["reconsideration_client_sent"]
    report(
        "g) Dia 180+ -> reconsideration_sent al cliente",
        ok,
        f"reconsideration_sent={result['reconsideration_client_sent']}",
    )


async def step_h_day_210_backup(engine, ctx):
    await _fast_forward_grace_start(engine, ctx["pid"], 215)

    async def _work(db):
        return await process_grace_period_checkpoints(db)
    result = await _run_with_session(engine, _work)
    ok = str(ctx["pid"]) in result["backup_generated"]
    report(
        "h) Dia 210+ -> backup ZIP generado + magic link",
        ok,
        f"backups_generated={result['backup_generated']}",
    )


async def step_i_verify_backup(engine, ctx):
    async def _work(db):
        await db.execute(sa_text("SET LOCAL ROLE fulkro"))
        try:
            res = await db.execute(
                select(ProjectArchivedBackup).where(
                    ProjectArchivedBackup.project_id == ctx["pid"],
                ).limit(1)
            )
            return res.scalar_one()
        finally:
            await db.execute(sa_text("RESET ROLE"))
    backup = await _run_with_session(engine, _work)
    ctx["backup_id"] = backup.id

    # verificar manifest directamente
    verifiable = verify_backup_signature(backup.manifest_jsonb)
    counts = backup.manifest_jsonb.get("counts", {})
    ok = (
        verifiable
        and counts.get("invoices", 0) >= 2
        and counts.get("documents", 0) >= 1
        and backup.sha256_hash
        and backup.ed25519_signature
    )
    report(
        "i) Backup verificable Ed25519 + contiene facturas+documentos",
        ok,
        f"sha256={backup.sha256_hash[:16]}... "
        f"facturas={counts.get('invoices')} "
        f"documentos={counts.get('documents')} "
        f"verif={verifiable}",
    )


async def step_j_day_240_delete(engine, ctx):
    await _fast_forward_grace_start(engine, ctx["pid"], 245)

    async def _work(db):
        # Primer run: vuelve a generar backup idempotente? No, backup_generated
        # ya existe, solo dispara data_deleted
        return await process_grace_period_checkpoints(db)
    result = await _run_with_session(engine, _work)
    ok = str(ctx["pid"]) in result["data_deleted"]
    report(
        "j) Dia 240+ -> data_deleted ejecutado",
        ok, f"deleted={result['data_deleted']}",
    )


async def step_k_verify_soft_hard_delete(engine, ctx):
    async def _work(db):
        await db.execute(sa_text("SET LOCAL ROLE fulkro"))
        try:
            proj = (await db.execute(
                select(Project).where(Project.id == ctx["pid"]),
            )).scalar_one()
            invoice_count = (await db.execute(sa_text(
                "SELECT count(*) FROM invoices WHERE client_id = :cid"
            ), {"cid": str(ctx["cid"])})).scalar()
            doc_row = (await db.execute(sa_text(
                "SELECT full_text_content FROM documents "
                "WHERE project_id = :pid LIMIT 1"
            ), {"pid": str(ctx["pid"])})).first()
            backup_exists = (await db.execute(sa_text(
                "SELECT count(*) FROM project_archived_backups "
                "WHERE client_id = :cid AND deleted_at IS NULL"
            ), {"cid": str(ctx["cid"])})).scalar()
            events_count = (await db.execute(sa_text(
                "SELECT count(*) FROM project_lifecycle_events "
                "WHERE client_id = :cid"
            ), {"cid": str(ctx["cid"])})).scalar()
            return {
                "lifecycle": proj.lifecycle_state,
                "deleted_at": proj.deleted_at,
                "invoices_retained": invoice_count,
                "doc_content_wiped": doc_row.full_text_content is None,
                "backup_retained": backup_exists,
                "events_retained": events_count,
            }
        finally:
            await db.execute(sa_text("RESET ROLE"))
    info = await _run_with_session(engine, _work)
    ok = (
        info["lifecycle"] == "PURGED"
        and info["deleted_at"] is not None
        and info["invoices_retained"] >= 2
        and info["doc_content_wiped"]
        and info["backup_retained"] >= 1
        and info["events_retained"] >= 6
    )
    report(
        "k) Soft delete proyecto + Hard delete GDPR + retencion audit",
        ok,
        f"state={info['lifecycle']} doc_wiped={info['doc_content_wiped']} "
        f"facturas_retenidas={info['invoices_retained']} "
        f"backups_retenidos={info['backup_retained']} "
        f"eventos={info['events_retained']}",
    )


async def step_l_reactivate_day_270(engine, ctx):
    """Simula reactivacion dia 270 — DENTRO de los 60d del backup."""
    async def _work(db):
        svc = LifecyclePaso4Service()
        result = await svc.reactivate_project(
            db, archived_backup_id=ctx["backup_id"],
            new_project_name="ENS Base — Bufete Legal (reactivado)",
        )
        return result
    result = await _run_with_session(engine, _work)
    ctx["new_project_id"] = uuid.UUID(result["new_project_id"])
    report(
        "l) Reactivacion dia 270 (dentro ventana 60d) -> OK",
        True,
        f"new_project_id={result['new_project_id']} "
        f"event_id={result['event_id']}",
    )


async def step_m_reactivate_after_expiry(engine, ctx):
    """Simula backup expirado + intento rechazado."""
    # Forzar expires_at en el pasado
    async with engine.begin() as conn:
        await conn.execute(sa_text("SET LOCAL ROLE fulkro"))
        await conn.execute(sa_text(
            "UPDATE project_archived_backups "
            "SET expires_at = now() - interval '1 day' "
            "WHERE id = :bid"
        ), {"bid": str(ctx["backup_id"])})

    async def _work(db):
        svc = LifecyclePaso4Service()
        try:
            await svc.reactivate_project(
                db, archived_backup_id=ctx["backup_id"],
            )
            return None
        except Exception as exc:
            return str(exc)
    err = await _run_with_session(engine, _work)
    ok = err is not None and ("expiro" in err or "eliminado" in err)
    report(
        "m) Reactivacion fuera de ventana 60d -> RECHAZADA",
        ok, f"error={err}",
    )


# ══════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════


async def main() -> int:
    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=False)

    print("\n" + "=" * 70)
    print("V-CHECK SESION 8 PASO 4 — M25 Lifecycle cierre honesto")
    print("=" * 70)

    try:
        ctx = await step_a_setup(engine)
        await step_b_certification(engine, ctx)
        await step_c_offer_retainer_declined(engine, ctx)
        await step_d_grace_state(engine, ctx)
        await step_e_readonly_access(engine, ctx)
        await step_f_day_150(engine, ctx)
        await step_g_day_180(engine, ctx)
        await step_h_day_210_backup(engine, ctx)
        await step_i_verify_backup(engine, ctx)
        await step_j_day_240_delete(engine, ctx)
        await step_k_verify_soft_hard_delete(engine, ctx)
        await step_l_reactivate_day_270(engine, ctx)
        await step_m_reactivate_after_expiry(engine, ctx)
    finally:
        await engine.dispose()

    # Resumen
    total = len(RESULTS)
    passed = sum(1 for _, ok, _ in RESULTS if ok)
    failed = total - passed

    print("\n" + "=" * 70)
    print(f"RESUMEN: {passed}/{total} PASS, {failed} FAIL")
    print("=" * 70)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
