#!/usr/bin/env python3
"""Arranque del demo: crea el operador, lo enrola en TOTP y siembra datos visibles.

Qué resuelve
────────────
1. El operador. Los seeds del repo dejan un administrador con el correo escrito
   a mano (``marcosmata@fulkro.es``) y sin segundo factor, así que nadie puede
   entrar por la UI: ``POST /api/v1/auth/login`` NO devuelve cookie de sesión,
   sólo un ``mfa_ticket``; la cookie la ponen ``/auth/totp/verify`` y
   ``/auth/webauthn/verify``. Este script crea (o realinea) el operador desde
   FULKRO_DEMO_OWNER_EMAIL / FULKRO_DEMO_OWNER_PASSWORD, le enrola TOTP y
   imprime el secreto en base32 y un código válido en ese instante.

   Se enrola TOTP a propósito, en lugar de añadir una bandera que desactive el
   MFA: así no se toca ni una línea del código de autenticación y no queda
   ningún interruptor que pueda escaparse a producción.

2. Los datos. ``seed_all_fulkro.py`` deja catálogos y 3 clientes, pero cero
   DdA, cero MAGERIT de proyecto, cero evidencias y cero plan: las pantallas de
   proyecto salen con estructura y sin contenido. Aquí se invoca el poblador que
   ya existe (``POST /api/v1/_dev/seed-full-implantation``) llamando a la
   función directamente, sin HTTP: el script corre en la fase de provisión,
   cuando el backend todavía no escucha.

Uso
───
    DATABASE_URL=postgresql+asyncpg://fulkro_migrate:...@postgres:5432/fulkro \
    PYTHONPATH=. python3 backend/scripts/demo_bootstrap.py

Vale cualquiera de los tres roles del despliegue (``fulkro_app``,
``fulkro_migrate`` o el superusuario ``fulkro``): el script asume
``fulkro_app_bypassrls`` donde necesita saltarse las políticas RLS, y los tres
son miembros de ese rol. `make demo` lo ejecuta dentro del contenedor
``backend``, o sea con ``fulkro_app``; comprobado ahí.

Es idempotente: ejecutarlo dos veces no duplica nada y NO regenera el secreto
TOTP ya enrolado (el autenticador que el operador escaneó sigue valiendo).

Variables de entorno
────────────────────
    FULKRO_DEMO_OWNER_EMAIL     (por defecto demo@fulkro.es)
    FULKRO_DEMO_OWNER_PASSWORD  (por defecto fulkro-demo-2026)
    FULKRO_DEMO_URL             (por defecto http://localhost:3000)
    FULKRO_DEMO_API_URL         sólo para el texto que se imprime
                                (por defecto http://localhost:18000)
    FULKRO_DEMO_TIER            BASICA | MEDIA | ALTA (por defecto MEDIA)
    FULKRO_DEMO_CORPUS_FIXTURE  ruta del volcado del corpus (ver más abajo)
    DATABASE_URL                URL asyncpg; si falta se usa la de config.py

El corpus
─────────
``ens_measure_refuerzos`` y ``ens_measure_dimensiones`` NO las puebla el seed:
llegan en ``backend/tests/fixtures/corpus_seed.sql.gz`` junto con 1.031 chunks
de conocimiento que YA traen su vector de 1024 dimensiones (o sea que cargarlo
no necesita servicio de embeddings ni red). El demo lo carga si encuentra el
fichero y hay un ``psql`` a mano. Si no lo encuentra, sigue adelante y lo avisa:
el demo se ve igual, pero la DdA no muestra refuerzos y el copiloto no tiene
corpus que citar. OJO: ``.dockerignore`` excluye ``backend/tests/``, así que
dentro del contenedor el fichero sólo existe si el compose lo monta.
"""
from __future__ import annotations

import asyncio
import gzip
import json
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
# Mismo interruptor que usa seed_all_fulkro.py: la siembra no debe tropezar con
# las puertas del motor de workflow (el proyecto se crea ya "en curso").
os.environ.setdefault("FULKRO_SKIP_WORKFLOW_GATES", "1")

from sqlalchemy import text as sa_text  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession, async_sessionmaker, create_async_engine,
)

from backend.app.auth.crypto import hash_password  # noqa: E402
from backend.app.config import get_settings  # noqa: E402
from backend.scripts.bootstrap_marcos_totp import (  # noqa: E402
    current_code, enroll_totp,
)


# ── Contrato del demo (defaults documentados · no cambiar sin avisar) ────────
# OJO con el dominio: NO puede ser .local, .localhost, .test, .invalid ni
# .example-reservado. `email-validator` (el que usa pydantic EmailStr) rechaza los
# dominios de uso especial, asi que POST /auth/login devolvia 422 y el operador del
# demo no podia entrar. Medido: "demo@fulkro.local" -> «The part after the @-sign is
# a special-use or reserved name». Por eso el default usa el dominio real del proyecto.
DEMO_OWNER_EMAIL = os.environ.get("FULKRO_DEMO_OWNER_EMAIL", "demo@fulkro.es")
DEMO_OWNER_PASSWORD = os.environ.get(
    "FULKRO_DEMO_OWNER_PASSWORD", "fulkro-demo-2026"
)
DEMO_URL = os.environ.get("FULKRO_DEMO_URL", "http://localhost:3000").rstrip("/")
DEMO_TIER = os.environ.get("FULKRO_DEMO_TIER", "MEDIA").upper()

# ── Identidad presentable del proyecto del demo (D3) ────────────────────────
# El endpoint `_dev/seed-full-implantation` crea el proyecto con los nombres del
# arnes de pruebas ("Test E2E Client" / "Proyecto ENS Test E2E"), que estan bien
# para Playwright y muy mal para ensenarselos a nadie. Peor: las diez capturas
# de landing/assets/capturas/marketing/ —las que usa USAGE.md— se tomaron con
# `scripts/capturas_landing.py`, que renombra ese mismo proyecto a NovaEdge. Sin
# esto, el recorrido guiado ensena capturas de una empresa y la pantalla dice
# otra cosa.
#
# Se renombra POR ID (el que devuelve el propio seed), no por nombre, para no
# tocar ningun otro cliente. Es idempotente y no altera CIF, ids ni datos.
# El nombre del proyecto se importa de `backend/app/dev/router.py` a proposito:
# ese modulo tiene que reconocerlo para no crear un proyecto nuevo en cada
# arranque, asi que la constante vive alli y aqui se consume. Una sola fuente.
from backend.app.dev.router import (  # noqa: E402
    _DEMO_PROJECT_NOMBRE as DEMO_PROYECTO_NOMBRE,
)

DEMO_CLIENTE_NOMBRE = "NovaEdge S.L."
DEMO_USUARIO_PORTAL_NOMBRE = "Laura Giménez"
CORPUS_FIXTURE = Path(
    os.environ.get(
        "FULKRO_DEMO_CORPUS_FIXTURE",
        str(REPO_ROOT / "backend" / "tests" / "fixtures" / "corpus_seed.sql.gz"),
    )
)

# Tablas que el fixture del corpus repone (mismo conjunto que el paso 7/7 de
# scripts/build_test_db.sh). El orden va de hijas a madres: así el borrado
# previo no viola ninguna clave ajena.
CORPUS_TABLES = (
    "knowledge_measure_mappings",
    "ens_measure_refuerzos",
    "ens_measure_dimensiones",
    "knowledge_chunks",
    "knowledge_documents",
    "knowledge_sources",
)

# ── Cuántas filas deja el demo ───────────────────────────────────────────────
# Cifras MEDIDAS el 2026-09-10 sobre una base creada desde cero (268 migraciones
# + seed_all_fulkro --skip-corpus + este script, tier=MEDIA). Se publican como
# MÍNIMOS, con margen a la baja donde el dato depende del tier o del catálogo,
# para que scripts/demo_smoke.sh tenga un criterio que no sea vacuamente cierto
# (GET /api/v1/health no toca la base: pasa con el esquema vacío).
MINIMOS_GLOBALES: dict[str, int] = {
    "ens_measures": 73,            # medido 73 · Anexo II RD 311/2022
    "ens_reinforcements": 18,      # medido 18 · tabla legacy
    "magerit_ens_mapping": 73,     # medido 73
    "threats": 50,                 # medido 57
    "safeguards": 80,              # medido 98
    "magerit_asset_types": 50,     # medido 67
    "ens_measure_evidencia_types": 90,   # medido 98
    "ens_iso27001_mapping": 70,    # medido 76
    "pricing_catalog": 10,         # medido 11
    "templates": 84,               # medido 123
    "clients": 3,                  # medido 3 del seed + 1 del poblador
    "projects": 3,
    "client_users": 1,
    "auth_users": 1,
}
# Sólo se comprueban si el fixture del corpus se ha cargado (son suyas).
MINIMOS_CORPUS: dict[str, int] = {
    "knowledge_chunks": 1000,      # medido 1031 en el fixture
    "ens_measure_refuerzos": 50,
    "ens_measure_dimensiones": 50,
}
# Del proyecto que siembra el poblador (tier MEDIA).
MINIMOS_PROYECTO: dict[str, int] = {
    "dda_entries": 68,             # medido 73 filas · 68 aplicables en MEDIA
    "evidence": 60,                # medido 204 (3 por medida aplicable)
    "magerit_assets": 1,           # medido 8
    "project_plans": 1,            # medido 1
    "wbs_tasks": 1,                # medido 35
    "conformity_routes": 1,        # medido 1 (estado REGISTERED)
    "documents": 1,                # medido 21
    "categorizations": 1,
    "dda_project_signatures": 1,
}

# SQL de recuento por tabla del proyecto (unas llegan por join).
SQL_PROYECTO: dict[str, str] = {
    "dda_entries":
        "SELECT count(*) FROM dda_entries WHERE project_id=:p AND deleted_at IS NULL",
    "evidence":
        "SELECT count(*) FROM evidence WHERE project_id=:p AND deleted_at IS NULL",
    "magerit_assets":
        "SELECT count(*) FROM magerit_assets a JOIN magerit_analysis an "
        "ON a.analysis_id = an.id WHERE an.project_id=:p",
    "project_plans":
        "SELECT count(*) FROM project_plans WHERE project_id=:p AND deleted_at IS NULL",
    "wbs_tasks":
        "SELECT count(*) FROM wbs_tasks WHERE project_id=:p AND deleted_at IS NULL",
    "conformity_routes":
        "SELECT count(*) FROM conformity_routes WHERE project_id=:p",
    "documents":
        "SELECT count(*) FROM documents WHERE project_id=:p AND deleted_at IS NULL",
    "categorizations":
        "SELECT count(*) FROM categorizations c JOIN systems s ON c.system_id = s.id "
        "WHERE s.project_id=:p",
    "dda_project_signatures":
        "SELECT count(*) FROM dda_project_signatures WHERE project_id=:p",
}


def _print(msg: str = "") -> None:
    print(msg, flush=True)


# ════════════════════════════════════════════════════════════════════
# URLs de base de datos
# ════════════════════════════════════════════════════════════════════

def resolve_async_url() -> str:
    """URL asyncpg del demo. Acepta que le pasen una URL síncrona y la adapta."""
    url = (
        os.environ.get("DATABASE_MIGRATE_URL_ASYNC")
        or os.environ.get("DATABASE_URL")
        or get_settings().database_url
    )
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


def to_libpq_url(async_url: str) -> str:
    """La misma URL en el formato que entiende ``psql``."""
    return async_url.replace("+asyncpg", "").replace("+psycopg2", "")


# ════════════════════════════════════════════════════════════════════
# Paso 1 · corpus (refuerzos + dimensiones + chunks ya vectorizados)
# ════════════════════════════════════════════════════════════════════

async def elevar(session: AsyncSession) -> None:
    """Asume `fulkro_app_bypassrls` para saltarse las políticas RLS.

    Sin esto, los recuentos hechos con el rol de la aplicación devuelven 0 en
    todas las tablas con RLS (projects, dda_entries, evidence…) porque no hay
    contexto de inquilino: el demo parecería vacío estando lleno (medido).
    Los tres roles posibles —app, migrate y el superusuario— pueden asumirlo;
    si alguno no pudiera, se sigue con el rol actual.
    """
    try:
        await session.execute(sa_text("SET LOCAL ROLE fulkro_app_bypassrls"))
    except Exception:  # noqa: BLE001
        await session.rollback()


async def _tabla_tiene_filas(session: AsyncSession, tabla: str, minimo: int) -> bool:
    try:
        n = (await session.execute(sa_text(f"SELECT count(*) FROM {tabla}"))).scalar()
    except Exception:  # noqa: BLE001 — tabla ausente en un esquema viejo
        await session.rollback()
        return False
    return int(n or 0) >= minimo


async def cargar_corpus(session: AsyncSession, libpq_url: str) -> str:
    """Carga el volcado del corpus. Devuelve una línea de estado legible."""
    await elevar(session)
    ya = await _tabla_tiene_filas(session, "ens_measure_refuerzos", 1) and \
        await _tabla_tiene_filas(session, "knowledge_chunks", 1000)
    if ya:
        return "ya cargado (no se toca)"
    if not CORPUS_FIXTURE.exists():
        return (
            f"OMITIDO · no existe {CORPUS_FIXTURE} · la DdA saldrá sin refuerzos "
            "y el copiloto sin corpus (.dockerignore excluye backend/tests/: "
            "el compose tiene que montarlo)"
        )
    psql = shutil.which("psql")
    if psql is None:
        return f"OMITIDO · no hay psql en el PATH para cargar {CORPUS_FIXTURE.name}"

    # Mismo espíritu que el paso 7/7 de scripts/build_test_db.sh, con dos
    # diferencias deliberadas, porque `make demo` ejecuta este script DENTRO
    # del contenedor `backend`, o sea con el rol de la aplicación:
    #   · `SET ROLE fulkro_app_bypassrls` en vez de `fulkro`: los tres roles
    #     (app, migrate y el superusuario) pueden asumirlo, y salta las
    #     políticas RLS sin necesitar superusuario.
    #   · DELETE en vez de TRUNCATE: ese rol tiene DELETE pero no TRUNCATE.
    #     El orden va de hijas a madres para no violar claves ajenas.
    # `session_replication_role = replica` desactiva los disparadores durante
    # la carga (init-roles.sql concede ese parámetro al rol bypass).
    borrados = "".join(f"DELETE FROM {t};\n" for t in CORPUS_TABLES)
    cabecera = (
        "SET ROLE fulkro_app_bypassrls;\n"
        "SET session_replication_role = replica;\n"
        + borrados
    )
    with gzip.open(CORPUS_FIXTURE, "rt", encoding="utf-8") as fh:
        cuerpo = fh.read()
    # CERRAR la transacción propia ANTES de llamar a psql: los SELECT de
    # comprobación de arriba dejan una transacción abierta que retiene un
    # candado de lectura sobre ens_measure_refuerzos, y el borrado del volcado
    # se queda esperándolo para siempre (medido con la versión que usaba
    # TRUNCATE: psql en `Lock`, esta sesión en `idle in transaction`).
    await session.rollback()
    # Sin ON_ERROR_STOP a propósito: si alguna de las sentencias de cabecera
    # no le está permitida al rol conectado, el volcado entra igual. La verdad
    # la dice el recuento de después, no el código de salida de psql.
    proc = subprocess.run(
        [psql, "-q", "-o", os.devnull, libpq_url],
        input=cabecera + cuerpo, text=True,
        capture_output=True, timeout=600,
    )
    await session.rollback()  # la conexión de psql es otra: refrescar la vista
    await elevar(session)
    filas: dict[str, int] = {}
    for t in ("knowledge_chunks", "ens_measure_refuerzos", "ens_measure_dimensiones"):
        filas[t] = (
            await session.execute(sa_text(f"SELECT count(*) FROM {t}"))
        ).scalar()
    if not int(filas["ens_measure_refuerzos"] or 0):
        err = (proc.stderr or "").strip().splitlines()[-1:] or ["sin stderr"]
        return f"FALLÓ · {err[0]}"
    return " · ".join(f"{k}={v}" for k, v in filas.items())


# ════════════════════════════════════════════════════════════════════
# Paso 2 · operador (auth_users) + TOTP
# ════════════════════════════════════════════════════════════════════

async def crear_operador(session: AsyncSession) -> uuid.UUID:
    """Alta o realineación del operador del demo. Idempotente por correo.

    ``role='owner'`` es lo que exige ``require_owner``; ``must_change_password``
    se deja en false para que el demo no arranque pidiendo cambiar la clave que
    acaba de imprimir, y se limpian el bloqueo y los intentos fallidos por si
    alguien probó a entrar a ciegas.
    """
    fila = (await session.execute(sa_text("""
        INSERT INTO auth_users (
            id, email, password_hash, display_name, role, is_active,
            must_change_password, failed_login_attempts, created_at
        )
        VALUES (
            gen_random_uuid(), :email, :hash, :nombre, 'owner', true,
            false, 0, now()
        )
        ON CONFLICT (email) DO UPDATE SET
            password_hash = EXCLUDED.password_hash,
            display_name  = EXCLUDED.display_name,
            role          = 'owner',
            is_active     = true,
            must_change_password = false,
            failed_login_attempts = 0,
            locked_until  = NULL,
            deleted_at    = NULL,
            updated_at    = now()
        RETURNING id
    """), {
        "email": DEMO_OWNER_EMAIL,
        "hash": hash_password(DEMO_OWNER_PASSWORD),
        "nombre": "Operador del demo",
    })).first()
    await session.commit()
    return fila.id


# ════════════════════════════════════════════════════════════════════
# Paso 3 · datos del proyecto (poblador ya existente)
# ════════════════════════════════════════════════════════════════════

async def sembrar_implantacion(session: AsyncSession) -> dict:
    """Llama a ``/api/v1/_dev/seed-full-implantation`` sin pasar por HTTP.

    El endpoint es una función asíncrona normal cuyo único servicio inyectado es
    la sesión de base de datos, así que se la pasamos y nos ahorramos levantar
    el backend en la fase de provisión. Es idempotente: si la DdA ya tiene 70+
    entradas no la regenera.
    """
    from backend.app.dev.router import seed_full_implantation

    respuesta = await seed_full_implantation(tier=DEMO_TIER, key=None, db=session)
    return json.loads(respuesta.model_dump_json())


# ── Evidencias firmadas de verdad (D3) ─────────────────────────────────────
# El seed masivo (`_dev/seed-full-implantation`) crea 204 filas en `evidence`
# SIN fichero, SIN nombre y SIN firma: los contadores salen llenos ("204/204")
# y la tabla entera dice «(sin nombre) · Pendiente firma · Sin firma». Medido:
#
#   SELECT count(*), count(fichero_nombre_original), count(firma_ed25519)
#   FROM evidence WHERE project_id='<demo>';
#   -->  204 | 0 | 0
#
# Para que el recorrido de USAGE.md pueda ensenar UNA evidencia firmada de
# verdad, aqui se ingieren unas pocas por el MISMO camino que usa la aplicacion
# (`ingest_evidence`): valida el tipo, calcula SHA-256, firma con Ed25519 y
# guarda el fichero. No se tocan las otras 204: siguen siendo relleno, y
# USAGE.md lo dice con esas palabras.
_PDF_MINIMO = (
    b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 595 842]>>endobj\n"
    b"trailer<</Root 1 0 R>>\n%%EOF\n"
)
_PNG_MINIMO = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
    "1f15c4890000000a49444154789c6360000002000100ffff0300000600"
    "05570c0d0a0000000049454e44ae426082"
)

#: (tipo de evidencia, medida ENS, nombre del fichero, contenido, mime)
_EVIDENCIAS_DEL_DEMO: tuple[tuple[str, str, str, bytes, str], ...] = (
    ("EVT-politica_firmada-001", "org.1",
     "politica-seguridad-novaedge-v1.pdf", _PDF_MINIMO, "application/pdf"),
    ("EVT-acta_comite-001", "org.2",
     "acta-comite-seguridad-2026-03.pdf", _PDF_MINIMO, "application/pdf"),
    ("EVT-captura_idp_mfa-001", "op.acc.5",
     "mfa-obligatorio-entra-id.png", _PNG_MINIMO, "image/png"),
    ("EVT-export_inventario-001", "mp.info.1",
     "inventario-activos-2026Q1.csv",
     b"activo;tipo;responsable;criticidad\n"
     b"Sede electronica;servicio;TI;alta\n"
     b"Base de datos de expedientes;informacion;TI;alta\n",
     "text/csv"),
    ("EVT-prueba_restauracion-001", "op.cont.1",
     "prueba-restauracion-backup-2026-02.pdf", _PDF_MINIMO, "application/pdf"),
)


async def sembrar_evidencias_firmadas(
    session: AsyncSession, project_id: str
) -> int:
    """Ingiere unas pocas evidencias REALES, firmadas Ed25519. Idempotente."""
    from backend.app.motors.m07_evidence.ingestion_service import ingest_evidence
    from backend.app.motors.m07_evidence.ingestion_types import (
        IngestionError,
        IngestionRequest,
    )

    await elevar(session)
    ya = {
        fila[0]
        for fila in (await session.execute(sa_text(
            "SELECT fichero_nombre_original FROM evidence "
            "WHERE project_id = :p AND fichero_nombre_original IS NOT NULL"
        ), {"p": project_id})).fetchall()
    }
    creadas = 0
    for tipo, medida, nombre, contenido, mime in _EVIDENCIAS_DEL_DEMO:
        if nombre in ya:
            continue
        try:
            await ingest_evidence(session, IngestionRequest(
                project_id=uuid.UUID(project_id),
                evidence_type_id=tipo,
                measure_code=medida,
                file_bytes=contenido,
                file_name=nombre,
                mime_type=mime,
            ))
            creadas += 1
        except IngestionError as exc:
            _print(f"    aviso: no se pudo ingerir {nombre}: {exc}")
    await session.commit()
    return creadas


async def poner_nombres_presentables(
    session: AsyncSession, client_id: uuid.UUID, project_id: str
) -> None:
    """Renombra el cliente y el proyecto del demo a la identidad de las capturas.

    Ver la nota de DEMO_CLIENTE_NOMBRE. Sin esto, USAGE.md ensena capturas de
    "NovaEdge S.L." y la aplicacion dice "Test E2E Client".
    """
    await elevar(session)
    await session.execute(
        sa_text("UPDATE clients SET nombre = :n, updated_at = now() WHERE id = :cid"),
        {"n": DEMO_CLIENTE_NOMBRE, "cid": str(client_id)},
    )
    await session.execute(
        sa_text("UPDATE projects SET nombre = :n, updated_at = now() WHERE id = :pid"),
        {"n": DEMO_PROYECTO_NOMBRE, "pid": str(project_id)},
    )
    await session.execute(
        sa_text(
            "UPDATE client_users SET full_name = :n, updated_at = now() "
            "WHERE client_id = :cid AND full_name LIKE 'Test E2E%'"
        ),
        {"n": DEMO_USUARIO_PORTAL_NOMBRE, "cid": str(client_id)},
    )
    await session.commit()


async def crear_usuario_portal(
    session: AsyncSession, client_id: uuid.UUID
) -> str | None:
    """Usuario del portal de cliente con las credenciales del demo.

    El portal de cliente va por correo + contraseña (``/api/v1/client-auth/login``)
    y ningún seed crea usuarios de portal, así que el poblador deja el suyo con
    un correo de pruebas. Aquí se AÑADE uno con el dominio del operador
    (demo@fulkro.es → cliente@fulkro.es) y su misma contraseña, sin tocar
    el de pruebas para no romper los ficheros de Playwright que lo usan.
    """
    dominio = DEMO_OWNER_EMAIL.split("@")[-1] if "@" in DEMO_OWNER_EMAIL else "fulkro.es"
    email = f"cliente@{dominio}"
    await elevar(session)
    await session.execute(sa_text("""
        INSERT INTO client_users (
            id, client_id, email, password_hash, full_name,
            must_change_password, created_by_marcos, created_at
        )
        VALUES (gen_random_uuid(), :cid, :email, :hash, 'Cliente del demo',
                false, true, now())
        ON CONFLICT (client_id, email) DO UPDATE SET
            password_hash = EXCLUDED.password_hash,
            must_change_password = false,
            failed_attempts = 0,
            locked_until = NULL,
            deactivated_at = NULL,
            deleted_at = NULL,
            updated_at = now()
    """), {
        "cid": str(client_id),
        "email": email,
        "hash": hash_password(DEMO_OWNER_PASSWORD),
    })
    await session.commit()
    return email


# ════════════════════════════════════════════════════════════════════
# Paso 4 · enlace del portal de auditor
# ════════════════════════════════════════════════════════════════════

async def enlace_auditor(session: AsyncSession, project_id: str) -> dict | None:
    from backend.app.dev.router import auditor_portal_token

    respuesta = await auditor_portal_token(project_id=project_id, db=session)
    return json.loads(respuesta.model_dump_json())


# ════════════════════════════════════════════════════════════════════
# Paso 5 · recuento
# ════════════════════════════════════════════════════════════════════

async def contar(
    session: AsyncSession, project_id: str | None, con_corpus: bool,
) -> tuple[list[tuple[str, str, int, int]], bool]:
    """Devuelve [(ámbito, tabla, filas, mínimo)] y si todos llegan al mínimo."""
    filas: list[tuple[str, str, int, int]] = []
    todo_ok = True
    await elevar(session)

    esperado = dict(MINIMOS_GLOBALES)
    if con_corpus:
        esperado.update(MINIMOS_CORPUS)
    for tabla, minimo in esperado.items():
        try:
            n = int((await session.execute(
                sa_text(f"SELECT count(*) FROM {tabla}")
            )).scalar() or 0)
        except Exception:  # noqa: BLE001
            await session.rollback()
            await elevar(session)
            n = -1
        filas.append(("global", tabla, n, minimo))
        todo_ok &= n >= minimo

    if project_id:
        for tabla, minimo in MINIMOS_PROYECTO.items():
            try:
                n = int((await session.execute(
                    sa_text(SQL_PROYECTO[tabla]), {"p": project_id}
                )).scalar() or 0)
            except Exception:  # noqa: BLE001
                await session.rollback()
                await elevar(session)
                n = -1
            filas.append(("proyecto", tabla, n, minimo))
            todo_ok &= n >= minimo
    return filas, todo_ok


# ════════════════════════════════════════════════════════════════════
# Main
# ════════════════════════════════════════════════════════════════════

async def main() -> int:
    async_url = resolve_async_url()
    engine = create_async_engine(async_url, echo=False)
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    resumen: dict[str, object] = {
        "url": DEMO_URL, "tier": DEMO_TIER, "operador": DEMO_OWNER_EMAIL,
    }
    try:
        # ── 1/5 corpus ──
        async with Session() as session:
            estado_corpus = await cargar_corpus(session, to_libpq_url(async_url))
        con_corpus = not estado_corpus.startswith(("OMITIDO", "FALLÓ"))
        _print(f"==> [1/5] corpus: {estado_corpus}")

        # ── 2/5 operador + TOTP ──
        async with Session() as session:
            await crear_operador(session)
            secreto, uri = await enroll_totp(
                session, DEMO_OWNER_EMAIL, reuse_existing=True
            )
            await session.commit()
        _print(f"==> [2/5] operador {DEMO_OWNER_EMAIL} listo · TOTP enrolado")

        # ── 3/5 datos del proyecto ──
        async with Session() as session:
            implantacion = await sembrar_implantacion(session)
        project_id = str(implantacion.get("project_id") or "")
        client_id = implantacion.get("client_id")
        errores = implantacion.get("extras_errors") or []
        _print(
            f"==> [3/5] implantación {DEMO_TIER}: proyecto {project_id} · "
            f"DdA aplicables={implantacion.get('dda_aplicables')} · "
            f"evidencias={implantacion.get('evidence_count')} · "
            f"MAGERIT={implantacion.get('magerit_assets')} · "
            f"ruta={implantacion.get('conformity_route_state')}"
        )
        for err in errores:
            _print(f"    aviso: {err}")

        async with Session() as session:
            await poner_nombres_presentables(
                session, uuid.UUID(str(client_id)), project_id
            )
        _print(
            f"    renombrado a «{DEMO_CLIENTE_NOMBRE}» / "
            f"«{DEMO_PROYECTO_NOMBRE}» (coincide con las capturas de USAGE.md)"
        )

        async with Session() as session:
            nuevas = await sembrar_evidencias_firmadas(session, project_id)
        _print(
            f"    evidencias firmadas de verdad (Ed25519, con fichero): "
            f"{nuevas} nuevas de {len(_EVIDENCIAS_DEL_DEMO)}"
        )

        async with Session() as session:
            email_portal = await crear_usuario_portal(
                session, uuid.UUID(str(client_id))
            )

        # ── 4/5 auditor ──
        auditor = None
        try:
            async with Session() as session:
                auditor = await enlace_auditor(session, project_id)
        except Exception as exc:  # noqa: BLE001
            _print(f"==> [4/5] portal de auditor: FALLÓ · {exc}")
        else:
            _print("==> [4/5] portal de auditor: enlace generado")

        # ── 5/5 recuento ──
        async with Session() as session:
            filas, todo_ok = await contar(session, project_id, con_corpus)
        _print("==> [5/5] filas sembradas")
        _print(f"    {'ámbito':9} {'tabla':30} {'filas':>7} {'mínimo':>7}")
        for ambito, tabla, n, minimo in filas:
            marca = " " if n >= minimo else "  <-- POR DEBAJO"
            valor = "ERROR" if n < 0 else str(n)
            _print(f"    {ambito:9} {tabla:30} {valor:>7} {minimo:>7}{marca}")

        resumen.update({
            "corpus": estado_corpus,
            "project_id": project_id,
            "client_id": client_id,
            "extras_errors": errores,
            "conteos": {f"{a}:{t}": n for a, t, n, _ in filas},
            "minimos_ok": todo_ok,
        })

        # ── bloque final para el operador ──
        _print()
        _print("═" * 72)
        _print("  DEMO DE FULKRO · LISTO")
        _print("═" * 72)
        _print(f"  Aplicación   {DEMO_URL}")
        _print(f"  API / docs   {os.environ.get('FULKRO_DEMO_API_URL', 'http://localhost:18000')}/docs")
        _print()
        _print("  ── Administración (Marcos) ──────────────────────────────")
        _print(f"  Entrar en    {DEMO_URL}/login")
        _print(f"  Correo       {DEMO_OWNER_EMAIL}")
        _print(f"  Contraseña   {DEMO_OWNER_PASSWORD}")
        _print(f"  Código TOTP  {current_code(secreto)}   (cambia cada 30 s)")
        _print(f"  Secreto TOTP {secreto}")
        _print(f"  URI del QR   {uri}")
        _print("  El login pide contraseña y, después, el código de 6 dígitos.")
        _print()
        _print("  ── Portal de cliente ────────────────────────────────────")
        _print(f"  Entrar en    {DEMO_URL}/client-portal/login")
        if email_portal:
            _print(f"  Correo       {email_portal}")
            _print(f"  Contraseña   {DEMO_OWNER_PASSWORD}")
        try:
            from backend.app.dev.router import (
                _TEST_USER_EMAIL, _TEST_USER_PASSWORD,
            )
            _print(f"  (alternativo {_TEST_USER_EMAIL} / {_TEST_USER_PASSWORD})")
        except Exception:  # noqa: BLE001
            pass
        _print()
        _print("  ── Portal de auditor (enlace de un solo uso) ────────────")
        if auditor:
            _print(f"  Entrar en    {DEMO_URL}{auditor['portal_path']}")
            _print(f"  Código OTP   {auditor.get('otp')}")
        else:
            _print("  No se pudo generar el enlace (ver el aviso de arriba).")
        _print("═" * 72)
        _print()
        _print("RESUMEN_JSON " + json.dumps(resumen, ensure_ascii=False, default=str))

        if not todo_ok:
            _print(
                "ERROR: alguna tabla está por debajo del mínimo · el demo "
                "arrancaría con pantallas vacías."
            )
            return 1
        return 0
    finally:
        await engine.dispose()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
