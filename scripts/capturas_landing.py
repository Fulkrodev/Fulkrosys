#!/usr/bin/env python3
"""Capturas reales del producto para la landing de fulkro.es.

Orquesta de punta a punta:
  1. Siembra un PROYECTO DEMO ficticio sobre el proyecto de test compartido del
     entorno dev (cliente NovaEdge S.L., usuaria Laura, nivel MEDIA) usando los
     endpoints `_dev/*` (create-test-client, seed-full-implantation MEDIA,
     seed-pentest-auth-data) — datos verosímiles pero 100% inventados.
  2. Renombra el cliente/proyecto/usuaria a la identidad de demo (NovaEdge /
     Laura) para que las capturas no muestren nombres de test ni jerga.
  3. Mintea un magic-link AUDITOR_PORTAL_ENAC para el portal auditor (solo
     lectura).
  4. Lanza Playwright (tests/capturas/landing-capturas.spec.ts) que captura el
     portal cliente y el portal auditor en desktop 1440 + móvil 390, tema claro,
     sin barras de scroll.
  5. Convierte cada PNG a WebP optimizado (Pillow).
  6. Restaura los nombres originales del proyecto de test (deja el entorno como
     estaba para el resto de la suite E2E).

RGPD: cero datos reales. Todo proviene de los seeds de test.

Uso:
    cd "$(git rev-parse --show-toplevel)"
    .venv/bin/python scripts/capturas_landing.py
Requiere el backend dev (:8000) y el frontend dev (:3000) en marcha y
APP_ENV != production.
"""
from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
# Permite `import backend.app...` al ejecutar el script directamente (sys.path[0]
# es scripts/, no la raíz del repo).
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
BACKEND = os.environ.get("CAPTURAS_BACKEND", "http://localhost:8000")
FRONTEND_PORT = os.environ.get("CAPTURAS_FRONTEND_PORT", "3000")
OUT_DIR = REPO / "landing" / "assets" / "capturas"
CONFIG_PATH = REPO / "frontend" / "tests" / "capturas" / ".capturas-config.json"

# Identidad de la demo (ficticia · RGPD-safe)
DEMO_CLIENT = "NovaEdge S.L."
DEMO_PROJECT = "Sede electrónica de NovaEdge"
DEMO_USER = "Laura Giménez"

# Originales del proyecto de test compartido (para restaurar al terminar)
ORIG_CLIENT = "Test E2E Client"
ORIG_PROJECT = "Proyecto ENS Test E2E"
ORIG_USER = "Test E2E Client User"
TEST_CIF = "B00000000"
TEST_EMAIL = "test-client-e2e@example.com"

# Modo: captures (default) | video | all | video-fast | marketing | marketing-fast
#  · video-fast / marketing-fast: reutilizan la config ya sembrada (NO re-siembran)
#    · sólo aplican el renombrado demo + capturan + restauran. Para iterar rápido.
#  · marketing: 9 capturas LIMPIAS del carrusel (3 admin + 3 cliente + 3 auditor)
#    vía tests/capturas/marketing-captures.mjs → landing/assets/capturas/marketing/.
MODE = sys.argv[1] if len(sys.argv) > 1 else "captures"
VIDEO_MODES = ("video", "video-fast")
MARKETING_MODES = ("marketing", "marketing-fast")
FAST_MODES = ("video-fast", "marketing-fast")
VIDEO_DIR = REPO / "landing" / "assets" / "video"
FRAMES_DIR = REPO / "out" / "video_frames"


def _post(path: str, timeout: int = 420) -> dict:
    url = f"{BACKEND}{path}"
    req = urllib.request.Request(url, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode()
        return json.loads(body) if body.strip() else {}


def _check_up() -> None:
    try:
        urllib.request.urlopen(f"{BACKEND}/api/v1/_dev/seed-info", timeout=8)
    except urllib.error.URLError as exc:
        sys.exit(
            f"✗ Backend no responde en {BACKEND} ({exc}). "
            "Arranca el backend dev (APP_ENV != production) antes de capturar."
        )


def seed() -> dict:
    print("→ create-test-client")
    tc = _post("/api/v1/_dev/create-test-client", timeout=60)
    pid = tc["project_id"]
    print(f"  project_id={pid}")

    print("→ seed-full-implantation?tier=MEDIA (pesado · puede tardar 1-2 min)")
    try:
        _post("/api/v1/_dev/seed-full-implantation?tier=MEDIA", timeout=900)
        print("  implantación MEDIA sembrada")
    except Exception as exc:  # noqa: BLE001
        print(f"  ⚠ seed-full-implantation falló ({exc}); se continúa con datos base")

    print("→ seed-pentest-auth-data")
    try:
        _post("/api/v1/_dev/seed-pentest-auth-data", timeout=180)
    except Exception as exc:  # noqa: BLE001
        print(f"  (pentest-auth seed opcional falló: {exc})")

    print("→ auditor-portal-token")
    at = _post(f"/api/v1/_dev/auditor-portal-token?project_id={pid}", timeout=60)

    return {
        "clientEmail": tc["email"],
        "clientPassword": tc["password"],
        "projectId": pid,
        "auditorToken": at["token"],
        "auditorOtp": at.get("otp"),
        "outDir": str(OUT_DIR),
    }


async def _db_run(fn):
    """Ejecuta `fn(db)` reusando la config del engine de la app (rol fulkro_app
    + bypass RLS, igual que los endpoints _dev). Engine efímero con NullPool
    para no chocar con el event loop entre llamadas asyncio.run."""
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from sqlalchemy.pool import NullPool

    from backend.app.database import engine as app_engine

    eng = create_async_engine(app_engine.url, poolclass=NullPool)
    try:
        maker = async_sessionmaker(eng, expire_on_commit=False)
        async with maker() as db:
            await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
            res = await fn(db)
            await db.commit()
            return res
    finally:
        await eng.dispose()


async def _snapshot(db):
    """Captura el estado original (cliente + TODOS sus proyectos con su
    deleted_at + 'riqueza' de datos + la usuaria) para restaurarlo tras la
    captura. `rich_id` = el proyecto con más datos (DdA + evidencias): es el que
    queremos que rendericen los portales."""
    from sqlalchemy import text

    cli = (await db.execute(text("SELECT id, nombre FROM clients WHERE cif=:c"), {"c": TEST_CIF})).first()
    if cli is None:
        return None
    projs = (
        await db.execute(
            text(
                "SELECT p.id, p.nombre, p.deleted_at,"
                " (SELECT count(*) FROM dda_entries d WHERE d.project_id=p.id)"
                " + (SELECT count(*) FROM evidence e WHERE e.project_id=p.id) AS score"
                " FROM projects p WHERE p.client_id=:cid"
            ),
            {"cid": cli[0]},
        )
    ).all()
    usr = (await db.execute(text("SELECT full_name FROM client_users WHERE email=:e"), {"e": TEST_EMAIL})).first()
    plist = [
        {"id": str(p[0]), "nombre": p[1], "deleted_at": p[2], "score": int(p[3] or 0)}
        for p in projs
    ]
    rich = max(plist, key=lambda x: x["score"])["id"] if plist else None
    return {"client": cli[1], "projects": plist, "user": usr[0] if usr else None, "rich_id": rich}


def _make_apply_demo(snap):
    """Renombra cliente + usuaria + TODOS los proyectos a la identidad de demo y
    SOFT-DELETE los proyectos vacíos, para que el resolver del portal cliente
    (R27 · un proyecto por cliente) caiga sobre el proyecto rico."""

    async def _apply(db):
        from sqlalchemy import text

        await db.execute(text("UPDATE clients SET nombre=:n WHERE cif=:c"), {"n": DEMO_CLIENT, "c": TEST_CIF})
        for p in snap["projects"]:
            await db.execute(
                text("UPDATE projects SET nombre=:n WHERE id=:pid"),
                {"n": DEMO_PROJECT, "pid": p["id"]},
            )
            if p["id"] != snap["rich_id"]:
                await db.execute(
                    text("UPDATE projects SET deleted_at=now() WHERE id=:pid"), {"pid": p["id"]}
                )
        await db.execute(text("UPDATE client_users SET full_name=:n WHERE email=:e"), {"n": DEMO_USER, "e": TEST_EMAIL})

    return _apply


def _make_restore(snap):
    async def _restore(db):
        from sqlalchemy import text

        await db.execute(text("UPDATE clients SET nombre=:n WHERE cif=:c"), {"n": snap["client"], "c": TEST_CIF})
        for p in snap["projects"]:
            await db.execute(
                text("UPDATE projects SET nombre=:n, deleted_at=:d WHERE id=:pid"),
                {"n": p["nombre"], "d": p["deleted_at"], "pid": p["id"]},
            )
        if snap["user"] is not None:
            await db.execute(
                text("UPDATE client_users SET full_name=:n WHERE email=:e"), {"n": snap["user"], "e": TEST_EMAIL}
            )

    return _restore


def _make_snapshot_state(pid):
    async def _snap(db):
        from sqlalchemy import text
        row = (await db.execute(text("SELECT fase, certified_at FROM projects WHERE id=:p"), {"p": pid})).first()
        acc = (await db.execute(text("SELECT count(*) FROM audit_accompaniment_state WHERE project_id=:p"), {"p": pid})).scalar()
        return {"fase": row[0] if row else None, "certified_at": row[1] if row else None, "acc_exists": int(acc or 0) > 0}
    return _snap


# Firmas que faltan para 6/6 (MEDIA · pentest se re-etiqueta a verificación en el
# saneo) + RSEG/CISO demo. Todo marcado para borrado en el restore.
_MISSING_SIGNATURES = [
    ("pentest_authorization", "a1c4e7"),
    ("conformidad_ens", "c2f5a8"),
    ("dpc_anual", "d3b6c9"),
]
_DEMO_CONTACTS = [
    ("rseg", "Responsable de Seguridad (RSEG)", "Beatriz Alonso Méndez", "rseg@novaedge.es"),
    ("ciso", "CISO", "David Romero Gil", "ciso@novaedge.es"),
]
# Mejoras propuestas demo (cloud_gaps · vista cliente /remediaciones · seguridad.html).
# gap_type, severity, ens_measure, title, explanation_es, suggested_action, approval_status
_MARKETING_GAPS = [
    ("configuration", "high", "op.acc.6",
     "Activar la verificación en dos pasos en 2 cuentas",
     "Vimos 2 cuentas de tu correo que entran solo con contraseña, sin segundo paso. Es lo que más frena los accesos no autorizados.",
     "Activamos la verificación en dos pasos en esas cuentas. No cambia tu día a día.",
     "proposed_to_cliente"),
    ("configuration", "medium", "mp.com.1",
     "Cerrar un acceso de administración abierto a internet",
     "Un panel de administración está accesible desde cualquier punto de internet. Conviene limitarlo a tu red.",
     "Restringimos ese acceso solo a tu red de confianza.",
     "proposed_to_cliente"),
    ("configuration", "low", "mp.com.2",
     "Renovar un certificado que caduca pronto",
     "Uno de tus certificados caduca en unas semanas. Si caduca, los navegadores avisarían de «sitio no seguro».",
     "Lo renovamos con antelación, sin cortar el servicio.",
     "proposed_to_cliente"),
    ("configuration", "medium", "mp.si.2",
     "Cifrado activado en el almacenamiento de tu nube",
     "Tus archivos en la nube ya se guardan cifrados.",
     "Activamos el cifrado en reposo del almacenamiento.",
     "executed"),
]


def _make_apply_state(pid):
    """Alinea el demo a estado certificado/casi-cerrado para las capturas de
    marketing: fase=retainer_cierre (paso 10/10) + acompañamiento certificate_issued
    + certified_at coherente con la aprobación + las 3 firmas que faltan (6/6) +
    RSEG/CISO. Coherente con lifecycle_state=CERTIFIED que ya leen admin/auditor."""
    async def _apply(db):
        import uuid as _uuid
        from sqlalchemy import text
        await db.execute(text("UPDATE projects SET fase='retainer_cierre', certified_at='2026-06-13' WHERE id=:p"), {"p": pid})
        # acompañamiento
        exists = (await db.execute(text("SELECT count(*) FROM audit_accompaniment_state WHERE project_id=:p"), {"p": pid})).scalar()
        if not int(exists or 0):
            await db.execute(text(
                "INSERT INTO audit_accompaniment_state (id, project_id, current_state, category_branch,"
                " last_advanced_at, accompaniment_metadata, created_at, updated_at)"
                " VALUES (gen_random_uuid(), :p, 'certificate_issued', 'MEDIO_ALTO', now(), '{}'::jsonb, now(), now())"
            ), {"p": pid})
        else:
            await db.execute(text("UPDATE audit_accompaniment_state SET current_state='certificate_issued', category_branch='MEDIO_ALTO' WHERE project_id=:p"), {"p": pid})
        # firmas faltantes → 6/6 (mirror de la firma dda existente · events sin encadenar)
        creator = (await db.execute(text("SELECT created_by_user_id FROM signing_intents WHERE project_id=:p AND signable_type='dda' LIMIT 1"), {"p": pid})).scalar()
        for stype, hexp in _MISSING_SIGNATURES:
            already = (await db.execute(text("SELECT count(*) FROM signing_intents WHERE project_id=:p AND signable_type=:t AND status='signed'"), {"p": pid, "t": stype})).scalar()
            if int(already or 0):
                continue
            iid, eid = str(_uuid.uuid4()), str(_uuid.uuid4())
            await db.execute(text(
                "INSERT INTO signing_intents (id, project_id, signable_type, document_hash_sha256, intent_payload, status,"
                " requires_step_up_otp, expires_at, created_by_user_id, created_at, updated_at)"
                " VALUES (:i, :p, :t, repeat('0',64), '{\"marketing_seed\": true}'::jsonb, 'signed', true, now()+interval '1 day', :u, now(), now())"
            ), {"i": iid, "p": pid, "t": stype, "u": creator})
            await db.execute(text(
                "INSERT INTO signing_events (id, project_id, signing_intent_id, event_type, actor_type, event_hash_sha256, previous_signature_hash, created_at)"
                " VALUES (:e, :p, :i, 'signature_generated', 'client_user', :h, NULL, now())"
            ), {"e": eid, "p": pid, "i": iid, "h": (hexp + "0" * 64)[:64]})
        # RSEG/CISO demo
        cid = (await db.execute(text("SELECT client_id FROM projects WHERE id=:p"), {"p": pid})).scalar()
        for cat, title, name, email in _DEMO_CONTACTS:
            ex = (await db.execute(text("SELECT count(*) FROM client_contacts WHERE project_id=:p AND role_category=:c AND deleted_at IS NULL"), {"p": pid, "c": cat})).scalar()
            if int(ex or 0):
                continue
            await db.execute(text(
                "INSERT INTO client_contacts (id, created_at, client_id, full_name, email, role_title, role_category,"
                " is_primary, is_signatory, has_portal_access, timezone, is_active, project_id, notes_marcos)"
                " VALUES (gen_random_uuid(), now(), :cid, :n, :e, :rt, :rc, false, true, false, 'Europe/Madrid', true, :p, '__marketing_seed__')"
            ), {"cid": cid, "n": name, "e": email, "rt": title, "rc": cat, "p": pid})
        # Mejoras propuestas demo (cloud_gaps · vista cliente /remediaciones)
        await db.execute(text("DELETE FROM cloud_gaps WHERE project_id=:p AND raw_evidence->>'marketing_seed'='true'"), {"p": pid})
        for gt, sv, m, ti, ex, sa, st in _MARKETING_GAPS:
            await db.execute(text(
                "INSERT INTO cloud_gaps (id, project_id, gap_type, severity, ens_measure_code, title, explanation_es,"
                " suggested_action, approval_status, cliente_can_see, proposed_to_cliente_at, resolved_at, raw_evidence,"
                " detected_at, created_at, updated_at)"
                " VALUES (gen_random_uuid(), :p, :gt, :sv, :m, :ti, :ex, :sa, :st, true, now(),"
                " CASE WHEN :is_exec THEN now() ELSE NULL END, '{\"marketing_seed\": true}'::jsonb, now(), now(), now())"
            ), {"p": pid, "gt": gt, "sv": sv, "m": m, "ti": ti, "ex": ex, "sa": sa, "st": st, "is_exec": (st == "executed")})
    return _apply


def _make_restore_state(pid, state):
    async def _restore(db):
        from sqlalchemy import text
        await db.execute(text("UPDATE projects SET fase=:f, certified_at=:c WHERE id=:p"), {"f": state["fase"], "c": state["certified_at"], "p": pid})
        if not state["acc_exists"]:
            await db.execute(text("DELETE FROM audit_accompaniment_state WHERE project_id=:p"), {"p": pid})
        await db.execute(text("DELETE FROM signing_events WHERE signing_intent_id IN (SELECT id FROM signing_intents WHERE project_id=:p AND intent_payload->>'marketing_seed'='true')"), {"p": pid})
        await db.execute(text("DELETE FROM signing_intents WHERE project_id=:p AND intent_payload->>'marketing_seed'='true'"), {"p": pid})
        await db.execute(text("DELETE FROM client_contacts WHERE project_id=:p AND notes_marcos='__marketing_seed__'"), {"p": pid})
        await db.execute(text("DELETE FROM cloud_gaps WHERE project_id=:p AND raw_evidence->>'marketing_seed'='true'"), {"p": pid})
    return _restore


def run_playwright() -> None:
    binary = REPO / "frontend" / "node_modules" / ".bin" / "playwright"
    cmd = [str(binary), "test", "--config=playwright.capturas.config.ts"]
    env = dict(os.environ)
    env["PLAYWRIGHT_PORT"] = FRONTEND_PORT
    print(f"→ Playwright: {' '.join(cmd)}")
    res = subprocess.run(cmd, cwd=str(REPO / "frontend"), env=env)
    if res.returncode != 0:
        print(f"  ⚠ Playwright código {res.returncode} (capturas parciales posibles)")


def to_webp() -> None:
    from PIL import Image

    pngs = sorted(OUT_DIR.glob("*.png"))
    print(f"→ Convirtiendo {len(pngs)} PNG → WebP")
    for png in pngs:
        with Image.open(png) as img:
            img.convert("RGB").save(
                png.with_suffix(".webp"), "WEBP", quality=82, method=6
            )


def run_video() -> None:
    """Graba el vídeo walkthrough (node · Playwright recordVideo → WebM + frames)."""
    env = dict(os.environ)
    env["PLAYWRIGHT_PORT"] = FRONTEND_PORT
    print("→ grabando vídeo walkthrough admin↔cliente (node)…")
    res = subprocess.run(
        ["node", "tests/capturas/video-walkthrough.mjs"],
        cwd=str(REPO / "frontend"),
        env=env,
    )
    if res.returncode != 0:
        print(f"  ⚠ vídeo node código {res.returncode}")


def run_marketing() -> None:
    """Genera las 9 capturas de marketing (node · Playwright stills)."""
    env = dict(os.environ)
    env["PLAYWRIGHT_PORT"] = FRONTEND_PORT
    print("→ generando 9 capturas de marketing (admin + cliente + auditor)…")
    res = subprocess.run(
        ["node", "tests/capturas/marketing-captures.mjs"],
        cwd=str(REPO / "frontend"),
        env=env,
    )
    if res.returncode != 0:
        print(f"  ⚠ marketing node código {res.returncode}")


def convert_video() -> None:
    """WebM → MP4 (H.264 faststart) + poster, con ffmpeg-static si está; si no,
    deja WebM + poster PNG de un frame."""
    VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    webm = VIDEO_DIR / "walkthrough.webm"
    if not webm.exists():
        print("  ⚠ no se generó walkthrough.webm")
        return
    poster_src = FRAMES_DIR / "01-admin-a.png"
    ff = REPO / "frontend" / "node_modules" / "ffmpeg-static" / "ffmpeg"
    ffbin = str(ff) if ff.exists() else shutil.which("ffmpeg")
    if not ffbin:
        print("  (sin ffmpeg · WebM + poster PNG)")
        if poster_src.exists():
            shutil.copyfile(poster_src, VIDEO_DIR / "walkthrough-poster.png")
        return
    mp4 = VIDEO_DIR / "walkthrough.mp4"
    poster = VIDEO_DIR / "walkthrough-poster.jpg"
    subprocess.run(
        [ffbin, "-y", "-i", str(webm), "-c:v", "libx264", "-preset", "slow",
         "-crf", "20", "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-an",
         "-loglevel", "error", str(mp4)],
        check=False,
    )
    if poster_src.exists():
        subprocess.run(
            [ffbin, "-y", "-i", str(poster_src), "-q:v", "3", "-loglevel", "error", str(poster)],
            check=False,
        )
    def _kb(p: Path) -> str:
        return f"{p.stat().st_size // 1024} KB" if p.exists() else "—"
    print(f"  ✅ vídeo: webm {_kb(webm)} · mp4 {_kb(mp4)} · poster {_kb(poster)}")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    _check_up()

    if MODE in FAST_MODES:
        if not CONFIG_PATH.exists():
            sys.exit(f"✗ {MODE} requiere una config previa. Corre `captures`/`video`/`marketing` una vez primero.")
        cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        print(f"→ ({MODE}) reutilizando config sembrada (proyecto {str(cfg['projectId'])[:8]})")
    else:
        cfg = seed()
        print("→ snapshot proyectos + identificar el proyecto con datos (rich)")
        snap0 = asyncio.run(_db_run(_snapshot))
        if snap0 and snap0["rich_id"] and snap0["rich_id"] != cfg["projectId"]:
            # el token de auditor debe apuntar al proyecto con datos
            at = _post(f"/api/v1/_dev/auditor-portal-token?project_id={snap0['rich_id']}", timeout=60)
            cfg["projectId"] = snap0["rich_id"]
            cfg["auditorToken"] = at["token"]
            cfg["auditorOtp"] = at.get("otp")
        CONFIG_PATH.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
        rid = (snap0 or {}).get("rich_id") or cfg["projectId"]
        print(f"→ config escrita (proyecto rico {str(rid)[:8]})")

    print("→ snapshot + renombrando demo a «%s» / «%s»" % (DEMO_CLIENT, DEMO_USER))
    # Snapshots (solo lectura) ANTES del try; los apply van DENTRO del try para que
    # cualquier fallo dispare SIEMPRE el restore del finally (no dejar BD sucia).
    snap = asyncio.run(_db_run(_snapshot))
    state = None
    if MODE in MARKETING_MODES:
        state = asyncio.run(_db_run(_make_snapshot_state(cfg["projectId"])))
    try:
        if snap:
            asyncio.run(_db_run(_make_apply_demo(snap)))
        if MODE in MARKETING_MODES:
            asyncio.run(_db_run(_make_apply_state(cfg["projectId"])))
            print(f"→ (marketing) estado alineado a certificado/casi-cerrado (fase orig={state['fase']})")
        if MODE in ("captures", "all"):
            run_playwright()
        if MODE in VIDEO_MODES or MODE == "all":
            run_video()
        if MODE in MARKETING_MODES:
            run_marketing()
    finally:
        print("→ restaurando nombres y estado original de los proyectos de test")
        if snap:
            asyncio.run(_db_run(_make_restore(snap)))
        if state is not None:
            asyncio.run(_db_run(_make_restore_state(cfg["projectId"], state)))

    if MODE in ("captures", "all"):
        to_webp()
        pngs = sorted(OUT_DIR.glob("*.png"))
        webps = sorted(OUT_DIR.glob("*.webp"))
        print(f"\n✅ {len(pngs)} PNG + {len(webps)} WebP en {OUT_DIR}")
    if MODE in VIDEO_MODES or MODE == "all":
        convert_video()
        print(f"✅ vídeo en {VIDEO_DIR}")


if __name__ == "__main__":
    main()
