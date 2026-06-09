"""Cross-portfolio isolation tests · MB-9 atom 9.3 Q5.D.

Verifies that cliente A cannot see cliente B data via RLS enforcement.
These tests use the regular `db` fixture which runs as fulkro_app
(NOSUPERUSER, RLS enforced).
"""
import uuid

import pytest
from sqlalchemy import text

from backend.tests.conftest import _admin_setup


pytestmark = pytest.mark.asyncio


async def _seed_two_clients_with_projects(db):
    """Create cliente A and cliente B each with 1 project + 1 alert_queue row."""
    ids = {}
    async with _admin_setup(db):
        for label in ("A", "B"):
            client_id = uuid.uuid4()
            project_id = uuid.uuid4()
            cif = f"B{uuid.uuid4().hex[:8].upper()}"
            await db.execute(text(
                "INSERT INTO clients (id, nombre, cif, created_at) "
                "VALUES (:id, :n, :cif, now())"
            ), {"id": str(client_id), "n": f"Cli {label}", "cif": cif})
            await db.execute(text(
                "INSERT INTO projects (id, client_id, nombre, fase, created_at) "
                "VALUES (:id, :cid, :n, 'diagnostico', now())"
            ), {
                "id": str(project_id),
                "cid": str(client_id),
                "n": f"Proj {label}",
            })
            ids[label] = (client_id, project_id)
    await db.flush()
    return ids


async def test_alert_queue_isolated_per_project(db):
    """Insert alert_queue rows for both clientes + verify RLS isolates."""
    ids = await _seed_two_clients_with_projects(db)
    cid_a, pid_a = ids["A"]
    cid_b, pid_b = ids["B"]

    async with _admin_setup(db):
        await db.execute(text(
            "INSERT INTO alert_queue "
            "(project_id, category, severity, title, triggered_at) "
            "VALUES (:pid, 'other', 'warning', 'Alert A', now())"
        ), {"pid": str(pid_a)})
        await db.execute(text(
            "INSERT INTO alert_queue "
            "(project_id, category, severity, title, triggered_at) "
            "VALUES (:pid, 'other', 'warning', 'Alert B', now())"
        ), {"pid": str(pid_b)})

    # Set tenant context to cliente A and query · should see only A's row
    await db.execute(
        text("SELECT set_config('app.current_project_id', :v, true)"),
        {"v": str(pid_a)},
    )
    rows_a = (await db.execute(text(
        "SELECT title FROM alert_queue ORDER BY title"
    ))).fetchall()
    titles_a = [r[0] for r in rows_a]
    assert "Alert A" in titles_a
    assert "Alert B" not in titles_a

    # Switch to B
    await db.execute(
        text("SELECT set_config('app.current_project_id', :v, true)"),
        {"v": str(pid_b)},
    )
    rows_b = (await db.execute(text(
        "SELECT title FROM alert_queue ORDER BY title"
    ))).fetchall()
    titles_b = [r[0] for r in rows_b]
    assert "Alert B" in titles_b
    assert "Alert A" not in titles_b


async def test_client_notifications_isolated_per_project(db):
    """Cliente A cannot see cliente B notifications · RLS verified."""
    ids = await _seed_two_clients_with_projects(db)
    cid_a, pid_a = ids["A"]
    cid_b, pid_b = ids["B"]
    user_a = uuid.uuid4()
    user_b = uuid.uuid4()
    async with _admin_setup(db):
        for label, cid, uid in (("A", cid_a, user_a), ("B", cid_b, user_b)):
            await db.execute(text(
                "INSERT INTO client_users "
                "(id, client_id, email, full_name, password_hash, created_at) "
                "VALUES (:id, :cid, :em, 'U', 'x', now())"
            ), {
                "id": str(uid),
                "cid": str(cid),
                "em": f"u+{uid.hex[:6]}@e.com",
            })
        await db.execute(text(
            "INSERT INTO client_notifications "
            "(project_id, client_user_id, type, title, target_url, priority, "
            " emitted_by_motor) "
            "VALUES (:pid, :uid, 'generic_alert', 'Notif A', "
            " '/portal', 'normal', 'm18')"
        ), {"pid": str(pid_a), "uid": str(user_a)})
        await db.execute(text(
            "INSERT INTO client_notifications "
            "(project_id, client_user_id, type, title, target_url, priority, "
            " emitted_by_motor) "
            "VALUES (:pid, :uid, 'generic_alert', 'Notif B', "
            " '/portal', 'normal', 'm18')"
        ), {"pid": str(pid_b), "uid": str(user_b)})

    # Cliente A scope
    await db.execute(
        text("SELECT set_config('app.current_project_id', :v, true)"),
        {"v": str(pid_a)},
    )
    titles_a = [
        r[0] for r in (await db.execute(text(
            "SELECT title FROM client_notifications"
        ))).fetchall()
    ]
    assert "Notif A" in titles_a
    assert "Notif B" not in titles_a

    # Cliente B scope
    await db.execute(
        text("SELECT set_config('app.current_project_id', :v, true)"),
        {"v": str(pid_b)},
    )
    titles_b = [
        r[0] for r in (await db.execute(text(
            "SELECT title FROM client_notifications"
        ))).fetchall()
    ]
    assert "Notif B" in titles_b
    assert "Notif A" not in titles_b


async def test_documents_already_isolated_per_project(db):
    """Sanity · documents already had RLS pre-MB-9 · verify still holds."""
    ids = await _seed_two_clients_with_projects(db)
    _, pid_a = ids["A"]
    _, pid_b = ids["B"]

    async with _admin_setup(db):
        await db.execute(text(
            "INSERT INTO documents (project_id, tipo, nombre, created_at) "
            "VALUES (:pid, 'policy', 'Doc A', now())"
        ), {"pid": str(pid_a)})
        await db.execute(text(
            "INSERT INTO documents (project_id, tipo, nombre, created_at) "
            "VALUES (:pid, 'policy', 'Doc B', now())"
        ), {"pid": str(pid_b)})

    await db.execute(
        text("SELECT set_config('app.current_project_id', :v, true)"),
        {"v": str(pid_a)},
    )
    names_a = [
        r[0] for r in (await db.execute(text(
            "SELECT nombre FROM documents"
        ))).fetchall()
    ]
    assert "Doc A" in names_a
    assert "Doc B" not in names_a


async def test_email_log_tenant_isolation(db):
    """Sprint Polish block 4 Aplus-final · RLS email_log defense-in-depth.

    Verifies:
    - Rows con `client_id = cliente_A` solo visibles bajo contexto cliente A
    - Rows con `client_id = cliente_B` solo visibles bajo contexto cliente B
    - Rows con `client_id = NULL` (system-wide) accesibles desde cualquier contexto
    """
    ids = await _seed_two_clients_with_projects(db)
    cid_a, _ = ids["A"]
    cid_b, _ = ids["B"]

    async with _admin_setup(db):
        await db.execute(text(
            "INSERT INTO email_log "
            "(recipient, subject, backend_used, delivery_status, client_id) "
            "VALUES (:r, :s, 'postmark_api', 'queued', :cid)"
        ), {"r": "a@cli-a.es", "s": "Email A", "cid": str(cid_a)})
        await db.execute(text(
            "INSERT INTO email_log "
            "(recipient, subject, backend_used, delivery_status, client_id) "
            "VALUES (:r, :s, 'postmark_api', 'queued', :cid)"
        ), {"r": "b@cli-b.es", "s": "Email B", "cid": str(cid_b)})
        await db.execute(text(
            "INSERT INTO email_log "
            "(recipient, subject, backend_used, delivery_status, client_id) "
            "VALUES (:r, :s, 'postmark_api', 'queued', NULL)"
        ), {"r": "lead@empresa.es", "s": "Lead system-wide"})

    # Contexto cliente A
    await db.execute(
        text("SELECT set_config('app.current_client_id', :v, true)"),
        {"v": str(cid_a)},
    )
    subjects_a = sorted(
        r[0] for r in (await db.execute(text(
            "SELECT subject FROM email_log "
            "WHERE subject IN ('Email A', 'Email B', 'Lead system-wide')"
        ))).fetchall()
    )
    assert subjects_a == ["Email A", "Lead system-wide"], (
        f"Cliente A debería ver solo su email + system-wide: {subjects_a}"
    )

    # Contexto cliente B
    await db.execute(
        text("SELECT set_config('app.current_client_id', :v, true)"),
        {"v": str(cid_b)},
    )
    subjects_b = sorted(
        r[0] for r in (await db.execute(text(
            "SELECT subject FROM email_log "
            "WHERE subject IN ('Email A', 'Email B', 'Lead system-wide')"
        ))).fetchall()
    )
    assert subjects_b == ["Email B", "Lead system-wide"], (
        f"Cliente B debería ver solo su email + system-wide: {subjects_b}"
    )

    # Sin contexto · admin/cron sin tenant set · email_log NO leak rows con client_id
    await db.execute(
        text("SELECT set_config('app.current_client_id', '', true)"),
    )
    subjects_no_ctx = sorted(
        r[0] for r in (await db.execute(text(
            "SELECT subject FROM email_log "
            "WHERE subject IN ('Email A', 'Email B', 'Lead system-wide')"
        ))).fetchall()
    )
    # USING (client_id IS NULL OR client_id = current_client_id())
    # · sin contexto, current_client_id() retorna NULL · client_id = NULL es FALSE
    # · solo rows con client_id IS NULL pasan el filter
    assert subjects_no_ctx == ["Lead system-wide"], (
        f"Sin contexto solo system-wide debería verse: {subjects_no_ctx}"
    )


# ══════════════════════════════════════════════════════════════════════
# MB-10 Atom 10.2.D · feature_flag_overrides RLS isolation (ADR-037)
# ══════════════════════════════════════════════════════════════════════


async def test_feature_flag_overrides_tenant_isolation(db):
    """Cliente A NO ve overrides de cliente B (project-level y client-level)."""
    ids = await _seed_two_clients_with_projects(db)
    cid_a, pid_a = ids["A"]
    cid_b, pid_b = ids["B"]

    async with _admin_setup(db):
        # Override project-level cliente A
        await db.execute(text(
            "INSERT INTO feature_flag_overrides "
            "(project_id, feature_key, override_value, granted_at) "
            "VALUES (:pid, 'override_proj_A', 'true'::jsonb, now())"
        ), {"pid": str(pid_a)})
        # Override client-level cliente A
        await db.execute(text(
            "INSERT INTO feature_flag_overrides "
            "(client_id, feature_key, override_value, granted_at) "
            "VALUES (:cid, 'override_cli_A', 'true'::jsonb, now())"
        ), {"cid": str(cid_a)})
        # Override project-level cliente B
        await db.execute(text(
            "INSERT INTO feature_flag_overrides "
            "(project_id, feature_key, override_value, granted_at) "
            "VALUES (:pid, 'override_proj_B', 'true'::jsonb, now())"
        ), {"pid": str(pid_b)})
        # Override client-level cliente B
        await db.execute(text(
            "INSERT INTO feature_flag_overrides "
            "(client_id, feature_key, override_value, granted_at) "
            "VALUES (:cid, 'override_cli_B', 'true'::jsonb, now())"
        ), {"cid": str(cid_b)})

    # Tenant context A → solo ve overrides A
    await db.execute(
        text("SELECT set_config('app.current_client_id', :v, true)"),
        {"v": str(cid_a)},
    )
    keys_a = sorted(
        r[0] for r in (await db.execute(text(
            "SELECT feature_key FROM feature_flag_overrides "
            "WHERE feature_key LIKE 'override_%'"
        ))).fetchall()
    )
    assert keys_a == ["override_cli_A", "override_proj_A"], (
        f"Cliente A leak detected: {keys_a}"
    )

    # Tenant context B → solo ve overrides B
    await db.execute(
        text("SELECT set_config('app.current_client_id', :v, true)"),
        {"v": str(cid_b)},
    )
    keys_b = sorted(
        r[0] for r in (await db.execute(text(
            "SELECT feature_key FROM feature_flag_overrides "
            "WHERE feature_key LIKE 'override_%'"
        ))).fetchall()
    )
    assert keys_b == ["override_cli_B", "override_proj_B"], (
        f"Cliente B leak detected: {keys_b}"
    )

    # Admin sin contexto · current_client_id() IS NULL · ve TODO (policy permite)
    await db.execute(
        text("SELECT set_config('app.current_client_id', '', true)"),
    )
    keys_admin = sorted(
        r[0] for r in (await db.execute(text(
            "SELECT feature_key FROM feature_flag_overrides "
            "WHERE feature_key LIKE 'override_%'"
        ))).fetchall()
    )
    assert keys_admin == [
        "override_cli_A", "override_cli_B",
        "override_proj_A", "override_proj_B",
    ], f"Admin sin contexto debería ver todos: {keys_admin}"
