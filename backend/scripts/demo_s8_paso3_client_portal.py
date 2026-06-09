"""V-CHECK Sesion 8 Paso 3 — Demo Portal Cliente sobre DataForma.

Flujo:
1. Marcos crea 3 usuarios cliente (RSEG, Director TI, CEO)
2. Cada uno cambia su temp password y opcionalmente habilita TOTP
3. Cada uno logina y accede a dashboard adaptativo por rol
4. Intentos de login fallidos -> locked_until aplicado
5. Marcos reset password desde cockpit
6. Logout revoca sesion
"""
from __future__ import annotations

import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("FULKRO_SKIP_WORKFLOW_GATES", "1")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pyotp
from sqlalchemy import select, text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from backend.app.auth.crypto import decode_token
from backend.app.config import get_settings
from backend.app.database import set_tenant_context
from backend.app.models.client_portal import ClientUser
from backend.app.motors.m21_portal_cliente import auth_service
from backend.app.motors.m21_portal_cliente.auth_service import (
    AuthError, effective_scopes,
)


RESULTS: list[tuple[str, bool, str]] = []


def report(label: str, ok: bool, detail: str = "") -> None:
    mark = "\033[32mPASS\033[0m" if ok else "\033[31mFAIL\033[0m"
    print(f"[{mark}] {label}")
    if detail:
        print(f"       {detail}")
    RESULTS.append((label, ok, detail))


async def _get_dataforma(engine) -> uuid.UUID:
    async with engine.begin() as conn:
        await conn.execute(sa_text("SET LOCAL ROLE fulkro"))
        r = await conn.execute(sa_text(
            "SELECT id FROM clients WHERE nombre ILIKE '%DataForma%' LIMIT 1"
        ))
        row = r.first()
        if not row:
            raise RuntimeError("DataForma no existe")
        return row[0]


async def _cleanup_users(engine, client_id: uuid.UUID) -> None:
    """Elimina users demo previos para re-ejecutar idempotente."""
    async with engine.begin() as conn:
        await conn.execute(sa_text("SET LOCAL ROLE fulkro"))
        await conn.execute(sa_text("""
            DELETE FROM client_user_audit
            WHERE client_user_id IN (
                SELECT id FROM client_users WHERE client_id = :cid
            )
        """), {"cid": str(client_id)})
        await conn.execute(sa_text("""
            DELETE FROM client_sessions
            WHERE client_user_id IN (
                SELECT id FROM client_users WHERE client_id = :cid
            )
        """), {"cid": str(client_id)})
        await conn.execute(sa_text(
            "DELETE FROM client_users WHERE client_id = :cid"
        ), {"cid": str(client_id)})


async def main() -> int:
    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=False)
    Session = sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False,
    )

    client_id = await _get_dataforma(engine)
    print("\n" + "=" * 70)
    print("V-CHECK SESION 8 PASO 3 — Portal Cliente DataForma")
    print("=" * 70)
    print(f"client_id={client_id}\n")

    await _cleanup_users(engine, client_id)

    # ────────────────────────────────────────────────────────────
    # 1) Marcos crea 3 usuarios
    # ────────────────────────────────────────────────────────────
    created_users: dict[str, dict] = {}
    users_to_create = [
        ("jfernandez@dataforma.es", "Jorge Fernandez Rodriguez", "rseg"),
        ("lvazquez@dataforma.es", "Laura Vazquez Torres", "director_ti"),
        ("mperez@dataforma.es", "Maria Perez Nunez", "direccion"),
    ]
    async with Session() as db:
        await db.execute(sa_text("SET LOCAL ROLE fulkro"))
        for email, nombre, role in users_to_create:
            user, temp = await auth_service.create_user(
                db, client_id=client_id,
                email=email, full_name=nombre, role=role,
            )
            created_users[email] = {
                "id": user.id, "role": role, "full_name": nombre,
                "temp_password": temp,
            }
        await db.commit()
    report(
        "1) Marcos crea 3 usuarios cliente (RSEG + director_ti + direccion)",
        len(created_users) == 3,
        " · ".join(f"{u['full_name']} ({u['role']})" for u in created_users.values()),
    )

    # ────────────────────────────────────────────────────────────
    # 2) Jorge (RSEG) entra, cambia password, habilita TOTP
    # ────────────────────────────────────────────────────────────
    jorge_info = created_users["jfernandez@dataforma.es"]
    async with Session() as db:
        await db.execute(sa_text("SET LOCAL ROLE fulkro"))
        user, token, exp = await auth_service.login(
            db, "jfernandez@dataforma.es", jorge_info["temp_password"],
        )
        # Cambio password
        await auth_service.change_password(
            db, user.id,
            jorge_info["temp_password"],
            "NuevaContrasena2026!",
        )
        # TOTP setup
        totp_setup = await auth_service.setup_totp(db, user.id)
        code = pyotp.TOTP(totp_setup["secret"]).now()
        await auth_service.verify_totp_setup(db, user.id, code)
        await db.commit()
        jorge_totp_secret = totp_setup["secret"]
    report(
        "2) Jorge (RSEG) login + change password + enable TOTP",
        user.totp_enabled,
        f"TOTP URI: {totp_setup['otpauth_uri'][:60]}...",
    )

    # ────────────────────────────────────────────────────────────
    # 3) Jorge login con TOTP -> dashboard RSEG con scopes full
    # ────────────────────────────────────────────────────────────
    async with Session() as db:
        await db.execute(sa_text("SET LOCAL ROLE fulkro"))
        totp_code = pyotp.TOTP(jorge_totp_secret).now()
        user, token, _ = await auth_service.login(
            db, "jfernandez@dataforma.es", "NuevaContrasena2026!",
            totp_code=totp_code,
        )
        jorge_scopes = effective_scopes(user)
        await db.commit()
    report(
        "3) Jorge login con TOTP -> scopes RSEG",
        "sign_documents" in jorge_scopes and "view_retainer_full" in jorge_scopes,
        f"scopes: {', '.join(jorge_scopes[:5])}...",
    )

    # ────────────────────────────────────────────────────────────
    # 4) Laura (director_ti) login -> scopes tecnicos
    # ────────────────────────────────────────────────────────────
    laura_info = created_users["lvazquez@dataforma.es"]
    async with Session() as db:
        await db.execute(sa_text("SET LOCAL ROLE fulkro"))
        user, token, _ = await auth_service.login(
            db, "lvazquez@dataforma.es", laura_info["temp_password"],
        )
        laura_scopes = effective_scopes(user)
        await db.commit()
    report(
        "4) Laura (director_ti) login -> scopes tecnicos",
        "view_documents_technical" in laura_scopes,
        f"scopes: {', '.join(laura_scopes)}",
    )

    # ────────────────────────────────────────────────────────────
    # 5) Maria (direccion) login -> scopes ejecutivos + retainer summary
    # ────────────────────────────────────────────────────────────
    maria_info = created_users["mperez@dataforma.es"]
    async with Session() as db:
        await db.execute(sa_text("SET LOCAL ROLE fulkro"))
        user, token, _ = await auth_service.login(
            db, "mperez@dataforma.es", maria_info["temp_password"],
        )
        maria_scopes = effective_scopes(user)
        await db.commit()
    report(
        "5) Maria (direccion) login -> scopes ejecutivos",
        "view_executive_reports" in maria_scopes
        and "view_invoices" in maria_scopes
        and "view_documents_technical" not in maria_scopes,
        f"scopes: {', '.join(maria_scopes)}",
    )

    # ────────────────────────────────────────────────────────────
    # 6) 5 intentos fallidos Maria -> locked
    # ────────────────────────────────────────────────────────────
    async with Session() as db:
        await db.execute(sa_text("SET LOCAL ROLE fulkro"))
        for _ in range(5):
            try:
                await auth_service.login(
                    db, "mperez@dataforma.es", "wrong_password",
                )
            except AuthError:
                pass
        await db.commit()
    async with Session() as db:
        await db.execute(sa_text("SET LOCAL ROLE fulkro"))
        user = (await db.execute(
            select(ClientUser).where(
                ClientUser.email == "mperez@dataforma.es"
            )
        )).scalar_one()
    report(
        "6) 5 intentos fallidos -> Maria locked_until aplicado",
        user.locked_until is not None,
        f"locked_until={user.locked_until}",
    )

    # ────────────────────────────────────────────────────────────
    # 7) Marcos reset password Maria desde cockpit
    # ────────────────────────────────────────────────────────────
    async with Session() as db:
        await db.execute(sa_text("SET LOCAL ROLE fulkro"))
        new_temp = await auth_service.reset_password_by_marcos(
            db, maria_info["id"],
        )
        # Locked_until deberia haberse liberado
        u = await db.get(ClientUser, maria_info["id"])
        await db.commit()
    report(
        "7) Marcos reset password Maria (unlocks + nueva temp)",
        u.locked_until is None and u.failed_attempts == 0,
        f"nueva_temp (primeros 4 chars)={new_temp[:4]}**** "
        f"· must_change_password={u.must_change_password}",
    )

    # ────────────────────────────────────────────────────────────
    # 8) Maria login con nueva temp + logout revoca sesion
    # ────────────────────────────────────────────────────────────
    async with Session() as db:
        await db.execute(sa_text("SET LOCAL ROLE fulkro"))
        user, token, _ = await auth_service.login(
            db, "mperez@dataforma.es", new_temp,
        )
        jti = decode_token(token)["jti"]
        revoked = await auth_service.logout(db, jti)
        await db.commit()
    report(
        "8) Maria login post-reset + logout revoca sesion",
        revoked is True,
        f"jti={jti[:8]}... revoked_at set",
    )

    # ────────────────────────────────────────────────────────────
    # 9) Verify session revocada falla
    # ────────────────────────────────────────────────────────────
    async with Session() as db:
        await db.execute(sa_text("SET LOCAL ROLE fulkro"))
        rejected = False
        try:
            await auth_service.verify_session(db, token)
        except AuthError:
            rejected = True
    report(
        "9) Token de sesion revocada rechazado",
        rejected,
        "verify_session raises AuthError tras logout",
    )

    # ────────────────────────────────────────────────────────────
    # 10) Audit log: cuenta acciones registradas
    # ────────────────────────────────────────────────────────────
    async with Session() as db:
        await db.execute(sa_text("SET LOCAL ROLE fulkro"))
        r = await db.execute(sa_text("""
            SELECT action, COUNT(*) FROM client_user_audit
            WHERE client_id = :cid
            GROUP BY action ORDER BY action
        """), {"cid": str(client_id)})
        audit_counts = {row[0]: row[1] for row in r.all()}
    ok = (
        audit_counts.get("user_created", 0) >= 3
        and audit_counts.get("login_success", 0) >= 3
        and audit_counts.get("password_reset_by_marcos", 0) >= 1
        and audit_counts.get("session_revoked", 0) >= 1
    )
    report(
        "10) Audit log registra todas las acciones criticas",
        ok,
        f"audit: {audit_counts}",
    )

    # ────────────────────────────────────────────────────────────
    # Resumen
    # ────────────────────────────────────────────────────────────
    pass_count = sum(1 for _, ok, _ in RESULTS if ok)
    total = len(RESULTS)
    print("\n" + "=" * 70)
    print(f"RESUMEN S8 PASO 3 · {pass_count}/{total} escenarios PASS")
    print("=" * 70)
    print(f"  Usuarios creados en DataForma: {len(created_users)}")
    for email, info in created_users.items():
        print(f"    · {info['full_name']} ({info['role']}) · {email}")
    print(f"  Acciones auditadas: {sum(audit_counts.values())}")
    print(f"  Jorge scopes ({len(jorge_scopes)}): {jorge_scopes[:3]}...")
    print(f"  Laura scopes ({len(laura_scopes)}): {laura_scopes[:3]}...")
    print(f"  Maria scopes ({len(maria_scopes)}): {maria_scopes[:3]}...")
    if pass_count != total:
        print("\n  FAILS:")
        for lbl, ok, det in RESULTS:
            if not ok:
                print(f"    · {lbl}: {det}")
    print("=" * 70)

    await engine.dispose()
    return 0 if pass_count == total else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
