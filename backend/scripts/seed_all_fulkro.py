"""Seed unificado FULKRO — restaura el estado `baseline` de BD en <3 min.

Uso (idempotente, seguro re-ejecutar):

    source .venv/bin/activate
    PYTHONPATH=. python backend/scripts/seed_all_fulkro.py [--skip-corpus]

Ejecuta en orden:
  A. Pre-checks: extensions, functions, role, alembic head
  B. Catalogos MAGERIT: asset_types, threats, safeguards, ens_mapping
  C. Catalogo ENS medidas (80 v2.2) + refuerzos (20 unicos)
  D. Corpus RAG: RD 311/2022 ingest desde var/corpus/boe/ (si existe)
  E. Clientes ficticios (DataForma + 2 mas)
  F. Catalogo evidencias ENS
  G. AGE knowledge graph

Cada paso reporta PASS/FAIL/SKIP. Salida JSON final con estado.

Opciones:
  --skip-corpus    No re-ingestar RD 311/2022 (si ya esta ingestado se
                   mantiene; si no, se salta con warning)
  --skip-age-kg    No seedear el grafo Apache AGE
  --skip-clients   No sembrar los 3 clientes ficticios (dev/test/CI)
  --optional-ext   Lista separada por comas de extensiones que pueden faltar
                   sin abortar. Solo se admiten `age` y `pgaudit`; equivale a
                   la variable de entorno FULKRO_SEED_OPTIONAL_EXT.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import subprocess
import sys
import time
import yaml
from pathlib import Path
from typing import Any

os.environ.setdefault("FULKRO_SKIP_WORKFLOW_GATES", "1")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from backend.app.config import get_settings

logger = logging.getLogger("seed_all_fulkro")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)


CATALOG_DIR = Path(__file__).resolve().parents[2] / "docs" / "catalogs"
MAGERIT_DIR = Path(__file__).resolve().parents[2] / "docs" / "magerit_catalog"
CORPUS_HTML = Path(__file__).resolve().parents[2] / "var" / "corpus" / "boe" / "RD_311_2022_consolidado.html"


# ════════════════════════════════════════════════════════════════════
# Extensiones PostgreSQL
# ════════════════════════════════════════════════════════════════════
# Las tres del núcleo son innegociables: sin `uuid-ossp`/`pgcrypto` no hay
# UUIDs ni hashes, y sin `vector` no hay columna de embeddings. Si falta
# cualquiera de ellas, el seed aborta como siempre.
REQUIRED_EXT_CORE = {"uuid-ossp", "pgcrypto", "vector"}

# `age` y `pgaudit` siguen siendo OBLIGATORIAS por defecto (producción no se
# degrada: si la imagen las trae y alguien olvidó el CREATE EXTENSION, el seed
# sigue abortando). Sólo se relajan en dos casos, y ambos se reportan:
#   1. Petición explícita: --optional-ext age,pgaudit  ó
#      FULKRO_SEED_OPTIONAL_EXT=age,pgaudit
#   2. La extensión NO existe en el catálogo de la imagen
#      (pg_available_extensions): el binario no está instalado, no hay nada
#      que crear. Es el caso del demo, que corre sobre pgvector/pgvector:pg16
#      (ver docs/adr/ADR-056-postgres-demo-sin-age.md).
# Ninguna otra extensión puede declararse opcional.
RELAXABLE_EXT = {"age", "pgaudit"}


def resolve_optional_ext(cli_value: str | None) -> set[str]:
    """Extensiones que el operador declara prescindibles (CLI + entorno).

    Une `--optional-ext` y FULKRO_SEED_OPTIONAL_EXT, y descarta con aviso
    cualquier nombre que no esté en RELAXABLE_EXT: así un typo (`vecto`) o un
    abuso (`vector`) no puede desactivar en silencio un pre-check del núcleo.
    """
    raw = ",".join(
        v for v in (cli_value, os.environ.get("FULKRO_SEED_OPTIONAL_EXT")) if v
    )
    pedidas = {p.strip().lower() for p in raw.split(",") if p.strip()}
    rechazadas = pedidas - RELAXABLE_EXT
    if rechazadas:
        logger.warning(
            "--optional-ext: ignoradas %s (solo se admiten %s)",
            sorted(rechazadas), sorted(RELAXABLE_EXT),
        )
    return pedidas & RELAXABLE_EXT


# ════════════════════════════════════════════════════════════════════
# Reporte
# ════════════════════════════════════════════════════════════════════

class SeedReport:
    def __init__(self) -> None:
        self.steps: list[dict[str, Any]] = []
        self.t0 = time.monotonic()

    def add(self, name: str, status: str, detail: str = "", **extra: Any) -> None:
        self.steps.append({
            "step": name, "status": status, "detail": detail,
            **extra,
        })
        icon = {"ok": "✓", "skip": "○", "fail": "✗"}.get(status, "?")
        logger.info("%s %s: %s %s", icon, name, status, detail)

    def summary(self) -> dict[str, Any]:
        elapsed = time.monotonic() - self.t0
        ok = sum(1 for s in self.steps if s["status"] == "ok")
        skip = sum(1 for s in self.steps if s["status"] == "skip")
        fail = sum(1 for s in self.steps if s["status"] == "fail")
        return {
            "elapsed_seconds": round(elapsed, 2),
            "total_steps": len(self.steps),
            "ok": ok, "skip": skip, "fail": fail,
            "steps": self.steps,
        }


# ════════════════════════════════════════════════════════════════════
# A. Pre-checks
# ════════════════════════════════════════════════════════════════════

async def pre_checks(
    engine, report: SeedReport, optional_ext: set[str] | None = None,
) -> tuple[bool, set[str]]:
    """Devuelve (todo_ok, extensiones_instaladas).

    La segunda mitad de la tupla la usa `main` para saltarse el grafo AGE
    cuando `age` no está instalada (si no, el paso G fallaría siempre).
    """
    optional_ext = optional_ext or set()
    async with engine.connect() as conn:
        # Extensions
        r = await conn.execute(sa_text(
            "SELECT extname FROM pg_extension ORDER BY extname"
        ))
        extensions = {row[0] for row in r.all()}
        r = await conn.execute(sa_text(
            "SELECT name FROM pg_available_extensions"
        ))
        disponibles = {row[0] for row in r.all()}

        # Relajadas: las que pidió el operador + las que la imagen NO trae.
        no_instalables = {
            e for e in RELAXABLE_EXT
            if e not in extensions and e not in disponibles
        }
        relajadas = (optional_ext | no_instalables) & RELAXABLE_EXT
        required_ext = (REQUIRED_EXT_CORE | RELAXABLE_EXT) - relajadas

        missing = required_ext - extensions
        if missing:
            report.add(
                "pre_check:extensions", "fail",
                f"missing: {missing}. Run psql -f infra/docker/init-extensions.sql",
            )
            return False, extensions

        ausentes = sorted(relajadas - extensions)
        detalle = f"loaded: {sorted(required_ext)}"
        if ausentes:
            detalle += (
                f" · ausentes toleradas: {ausentes}"
                f" (pedidas={sorted(optional_ext)} ·"
                f" no instalables en esta imagen={sorted(no_instalables)})"
            )
        report.add("pre_check:extensions", "ok", detalle)

        # Functions
        r = await conn.execute(sa_text(
            "SELECT proname FROM pg_proc WHERE proname IN "
            "('current_client_id', 'current_project_id')"
        ))
        funcs = {row[0] for row in r.all()}
        if funcs != {"current_client_id", "current_project_id"}:
            report.add(
                "pre_check:functions", "fail",
                "current_client_id/current_project_id no registradas. "
                "Run psql -f infra/docker/init-functions.sql",
            )
            return False, extensions
        report.add("pre_check:functions", "ok", "RLS helpers OK")

        # Role fulkro_app
        r = await conn.execute(sa_text(
            "SELECT rolname FROM pg_roles WHERE rolname = 'fulkro_app'"
        ))
        if r.scalar() is None:
            report.add(
                "pre_check:role", "fail",
                "fulkro_app no existe. Run psql -f infra/docker/init-roles.sql",
            )
            return False, extensions
        report.add("pre_check:role", "ok", "fulkro_app role exists")

        # Alembic head
        try:
            r = await conn.execute(sa_text(
                "SELECT version_num FROM alembic_version"
            ))
            ver = r.scalar()
            report.add("pre_check:alembic", "ok", f"head={ver}")
        except Exception as exc:
            report.add(
                "pre_check:alembic", "fail",
                f"alembic_version no existe. Run: cd backend && alembic upgrade head. {exc}",
            )
            return False, extensions
    return True, extensions


# ════════════════════════════════════════════════════════════════════
# B. Catalogos MAGERIT
# ════════════════════════════════════════════════════════════════════

async def seed_magerit_asset_types(conn, report: SeedReport) -> None:
    data = yaml.safe_load((MAGERIT_DIR / "asset_types.yaml").read_text())
    await conn.execute(sa_text("SET LOCAL ROLE fulkro"))
    r = await conn.execute(sa_text("SELECT COUNT(*) FROM magerit_asset_types"))
    existing = r.scalar() or 0
    if existing >= 60:
        report.add("seed:magerit_asset_types", "skip", f"ya hay {existing} rows")
        return
    n = 0
    for cat in data["asset_categories"]:
        cat_code = cat["code"].strip("[]")
        # Top-level category (usado por M02 importer: HW, SW, COM, S, D, etc.)
        await conn.execute(sa_text("""
            INSERT INTO magerit_asset_types
                (id, code, name, category_code, description,
                 default_dimensions, created_at)
            VALUES (gen_random_uuid(), :c, :n, :cat, :d,
                    CAST(:dims AS JSONB), NOW())
            ON CONFLICT (code) DO NOTHING
        """), {
            "c": cat_code,
            "n": cat.get("name") or cat_code,
            "cat": cat_code,
            "d": cat.get("description", ""),
            "dims": json.dumps(["D", "I", "C", "A", "T"]),
        })
        n += 1
        for t in cat.get("subtypes") or []:
            await conn.execute(sa_text("""
                INSERT INTO magerit_asset_types
                    (id, code, name, category_code, description,
                     default_dimensions, created_at)
                VALUES (gen_random_uuid(), :c, :n, :cat, :d,
                        CAST(:dims AS JSONB), NOW())
                ON CONFLICT (code) DO NOTHING
            """), {
                "c": t["code"].strip("[]"),
                "n": t["name"],
                "cat": cat_code,
                "d": t.get("description", ""),
                "dims": json.dumps(t.get("dimensions") or []),
            })
            n += 1
    r = await conn.execute(sa_text("SELECT COUNT(*) FROM magerit_asset_types"))
    total = r.scalar()
    report.add("seed:magerit_asset_types", "ok", f"{total} rows (processed {n})")


async def seed_magerit_threats(conn, report: SeedReport) -> None:
    data = yaml.safe_load((MAGERIT_DIR / "threats.yaml").read_text())
    await conn.execute(sa_text("SET LOCAL ROLE fulkro"))
    r = await conn.execute(sa_text("SELECT COUNT(*) FROM threats"))
    existing = r.scalar() or 0
    if existing >= 50:
        report.add("seed:threats", "skip", f"ya hay {existing}")
        return
    n = 0
    for grp in data["threat_groups"]:
        for t in grp.get("threats") or []:
            await conn.execute(sa_text("""
                INSERT INTO threats
                    (id, codigo_magerit, nombre, descripcion,
                     dimensiones_afectadas, created_at)
                VALUES (gen_random_uuid(), :c, :n, :d, :dims, NOW())
                ON CONFLICT DO NOTHING
            """), {
                "c": t["code"], "n": t["name"],
                "d": t.get("description", ""),
                "dims": t.get("dimensions") or [],
            })
            n += 1
    r = await conn.execute(sa_text("SELECT COUNT(*) FROM threats"))
    report.add("seed:threats", "ok", f"{r.scalar()} rows (processed {n})")


async def seed_magerit_safeguards(conn, report: SeedReport) -> None:
    data = yaml.safe_load((MAGERIT_DIR / "safeguards.yaml").read_text())
    await conn.execute(sa_text("SET LOCAL ROLE fulkro"))
    r = await conn.execute(sa_text("SELECT COUNT(*) FROM safeguards"))
    existing = r.scalar() or 0
    if existing >= 80:
        report.add("seed:safeguards", "skip", f"ya hay {existing}")
        return
    n = 0
    for fam in data["safeguard_families"]:
        for s in fam.get("safeguards") or []:
            await conn.execute(sa_text("""
                INSERT INTO safeguards
                    (id, codigo, nombre, eficacia, medida_ens_relacionada,
                     created_at)
                VALUES (gen_random_uuid(), :c, :n, :e, :m, NOW())
                ON CONFLICT DO NOTHING
            """), {
                "c": s["code"], "n": s["name"],
                "e": float(s.get("effectiveness", 0.7)),
                "m": s.get("ens_measure"),
            })
            n += 1
    r = await conn.execute(sa_text("SELECT COUNT(*) FROM safeguards"))
    report.add("seed:safeguards", "ok", f"{r.scalar()} rows (processed {n})")


async def seed_magerit_ens_mapping(conn, report: SeedReport) -> None:
    data = yaml.safe_load((MAGERIT_DIR / "ens_mapping.yaml").read_text())
    await conn.execute(sa_text("SET LOCAL ROLE fulkro"))
    r = await conn.execute(sa_text("SELECT COUNT(*) FROM magerit_ens_mapping"))
    existing = r.scalar() or 0
    if existing >= 73:
        report.add("seed:magerit_ens_mapping", "skip", f"ya hay {existing}")
        return
    n = 0
    for m in data["ens_to_magerit"]:
        await conn.execute(sa_text("""
            INSERT INTO magerit_ens_mapping
                (id, ens_measure, ens_measure_name, magerit_safeguards,
                 confidence, notes, created_at)
            VALUES (gen_random_uuid(), :m, :n, CAST(:sg AS JSONB),
                    :c, :nt, NOW())
            ON CONFLICT (ens_measure) DO NOTHING
        """), {
            "m": m["measure"],
            "n": m.get("name", ""),
            "sg": json.dumps(m.get("magerit_safeguards") or []),
            "c": m.get("confidence", "medium"),
            "nt": m.get("notes", ""),
        })
        n += 1
    r = await conn.execute(sa_text("SELECT COUNT(*) FROM magerit_ens_mapping"))
    report.add("seed:magerit_ens_mapping", "ok", f"{r.scalar()} rows (processed {n})")


# ════════════════════════════════════════════════════════════════════
# C. ENS medidas + refuerzos
# ════════════════════════════════════════════════════════════════════

async def seed_ens_measures(conn, report: SeedReport) -> None:
    data = yaml.safe_load((CATALOG_DIR / "ens_measures_catalog_v1.yaml").read_text())
    medidas = data.get("medidas", [])
    # Ejecutable 8 Pasada 16 (a · CÓDIGO seed): cargar SOLO las 73 medidas oficiales Anexo II.
    # El catálogo tiene 79 (73 + 6 rollups de familia/extras no-oficiales). Coherente con
    # load_ens_measures_catalog.py (intersección magerit_ens_mapping = 73). Sin este filtro la
    # DdA generaba total_medidas=79 y rompía las aserciones ==73 (m03_dda). Fuente: catálogo
    # `codigos_validados_contra: magerit_ens_mapping (73)` + skip-list del loader canónico.
    _NON_OFFICIAL = {"mp.com.9", "mp.if.9", "mp.per.9", "mp.s.8", "mp.s.9", "op.exp.11"}
    medidas = [m for m in medidas if m.get("codigo") not in _NON_OFFICIAL]
    await conn.execute(sa_text("SET LOCAL ROLE fulkro"))
    r = await conn.execute(sa_text("SELECT COUNT(*) FROM ens_measures"))
    existing = r.scalar() or 0
    if existing >= 73:
        report.add("seed:ens_measures", "skip", f"ya hay {existing}")
    else:
        n = 0
        for m in medidas:
            await conn.execute(sa_text("""
                INSERT INTO ens_measures
                    (id, codigo, nombre, marco, familia, descripcion,
                     aplica_basica, aplica_media, aplica_alta,
                     categoria_minima, dimensiones_aplicables,
                     version_ens, fuente_oficial, created_at)
                VALUES (gen_random_uuid(), :cod, :nom, :mar, :fam, :desc,
                        :ab, :am, :aa, :cm, CAST(:dims AS JSONB),
                        'v2', :fo, NOW())
                ON CONFLICT DO NOTHING
            """), {
                "cod": m["codigo"], "nom": m["nombre"],
                "mar": m.get("marco", "org"),
                "fam": m.get("familia", "org"),
                "desc": m.get("descripcion", ""),
                "ab": bool(m.get("aplica_basica")),
                "am": bool(m.get("aplica_media")),
                "aa": bool(m.get("aplica_alta")),
                "cm": m.get("categoria_minima", "BASICA"),
                "dims": json.dumps(m.get("dimensiones_aplicables") or []),
                "fo": m.get("fuente_oficial", ""),
            })
            n += 1
        r = await conn.execute(sa_text("SELECT COUNT(*) FROM ens_measures"))
        report.add("seed:ens_measures", "ok", f"{r.scalar()} rows (v2.2, processed {n})")

    # Override autoritativo RD 311/2022 Anexo II (BOE-A-2022-7191) · audit 2026-06-07.
    # El YAML arrastraba numeración/nombres/aplicabilidad del RD 3/2010 (derogado): se
    # forzaron nombre + aplica_* + descripcion (casada por nombre) a la tabla oficial,
    # verificada celda a celda. Idempotente · corre también en la rama skip (corrige BD
    # ya sembrada). Ver backend/app/motors/m03_dda/anexo2_rd311_2022.py + guard test.
    from backend.app.motors.m03_dda.anexo2_rd311_2022 import resolve_entries

    entries = resolve_entries(data["medidas"])  # lista completa para casar descripciones
    overridden = 0
    for codigo, e in entries.items():
        res = await conn.execute(sa_text("""
            UPDATE ens_measures SET nombre = :n, descripcion = :d,
                aplica_basica = :b, aplica_media = :m, aplica_alta = :a,
                fuente_oficial = 'RD 311/2022 Anexo II (BOE-A-2022-7191)',
                version_ens = 'RD 311/2022'
            WHERE codigo = :c
        """), {"c": codigo, "n": e["nombre"], "d": e["descripcion"],
               "b": e["aplica_basica"], "m": e["aplica_media"], "a": e["aplica_alta"]})
        overridden += res.rowcount or 0
    report.add("seed:ens_measures_rd311", "ok", f"{overridden} rows -> RD 311/2022 Anexo II")


async def seed_ens_reinforcements(conn, report: SeedReport) -> None:
    data = yaml.safe_load((CATALOG_DIR / "ens_measures_catalog_v1.yaml").read_text())
    medidas = data.get("medidas", [])
    await conn.execute(sa_text("SET LOCAL ROLE fulkro"))
    r = await conn.execute(sa_text("SELECT COUNT(*) FROM ens_reinforcements"))
    existing = r.scalar() or 0
    if existing >= 18:
        report.add("seed:ens_reinforcements", "skip", f"ya hay {existing}")
        return

    # Mapa codigo → id
    r_ids = await conn.execute(sa_text(
        "SELECT codigo, id FROM ens_measures WHERE deleted_at IS NULL"
    ))
    code_to_id = {row[0]: row[1] for row in r_ids.all()}

    cat_map = {"B": "B", "M": "M", "A": "A"}
    inserted = 0
    for m in medidas:
        mid = code_to_id.get(m["codigo"])
        if mid is None:
            continue
        refuerzos = m.get("refuerzos") or {}
        # Consolidar: para cada (codigo_refuerzo), usar la categoria_minima
        # mas baja en la que aplica (B < M < A).
        priority = {"B": 0, "M": 1, "A": 2}
        by_code: dict[str, str] = {}
        for cat, codes in refuerzos.items():
            if not codes:
                continue
            cat_norm = cat_map.get(cat, cat)
            if cat_norm not in {"B", "M", "A"}:
                continue
            for rcode in codes:
                if rcode not in by_code or priority[cat_norm] < priority[by_code[rcode]]:
                    by_code[rcode] = cat_norm

        for rcode, cat_min in by_code.items():
            await conn.execute(sa_text("""
                INSERT INTO ens_reinforcements
                    (id, measure_id, codigo_refuerzo, descripcion,
                     aplica_categoria_minima, dimension_aplicable, created_at)
                VALUES (gen_random_uuid(), :mid, :rc, :d, :cm, NULL, NOW())
                ON CONFLICT DO NOTHING
            """), {
                "mid": mid, "rc": rcode,
                "d": f"Refuerzo {rcode} de medida {m['codigo']} (categoria minima {cat_min}).",
                "cm": cat_min,
            })
            inserted += 1

    r = await conn.execute(sa_text("SELECT COUNT(*) FROM ens_reinforcements"))
    report.add(
        "seed:ens_reinforcements", "ok",
        f"{r.scalar()} rows (processed {inserted})",
    )


# ════════════════════════════════════════════════════════════════════
# D. Corpus RAG RD 311/2022
# ════════════════════════════════════════════════════════════════════

async def seed_corpus(engine, report: SeedReport, skip: bool) -> None:
    if skip:
        report.add("seed:corpus", "skip", "--skip-corpus")
        return
    if not CORPUS_HTML.exists():
        report.add(
            "seed:corpus", "skip",
            f"{CORPUS_HTML} no existe. Descarga manual requerida "
            "(var/corpus/boe/RD_311_2022_consolidado.html)",
        )
        return

    try:
        from backend.app.corpus.rd311_ingest import ingest_rd311
    except Exception as exc:
        report.add("seed:corpus", "fail", f"import error: {exc}")
        return

    # Comprobar si ya esta ingestado
    async with engine.connect() as conn:
        await conn.execute(sa_text("SET LOCAL ROLE fulkro"))
        r = await conn.execute(sa_text(
            "SELECT COUNT(*) FROM knowledge_chunks"
        ))
        existing = r.scalar() or 0
    if existing >= 100:
        report.add("seed:corpus", "skip", f"ya hay {existing} chunks ingestados")
        return

    t0 = time.monotonic()
    Session = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    try:
        async with Session() as db:
            await db.execute(sa_text("SET LOCAL ROLE fulkro"))
            summary = await ingest_rd311(db, CORPUS_HTML)
            await db.commit()
        elapsed = time.monotonic() - t0
        # Post-check
        async with engine.connect() as conn:
            await conn.execute(sa_text("SET LOCAL ROLE fulkro"))
            r = await conn.execute(sa_text(
                "SELECT COUNT(*) FROM knowledge_documents"
            ))
            n_docs = r.scalar()
            r = await conn.execute(sa_text(
                "SELECT COUNT(*) FROM knowledge_chunks"
            ))
            n_chunks = r.scalar()
        report.add(
            "seed:corpus", "ok",
            f"RD 311/2022 ingested ({elapsed:.1f}s): {n_docs} docs, {n_chunks} chunks",
            **(summary if isinstance(summary, dict) else {}),
        )
    except Exception as exc:
        report.add("seed:corpus", "fail", f"ingest error: {exc}")
        return

    # Embeddings: multilingual-e5-large (dim 1024). Tarda ~60s.
    async with engine.connect() as conn:
        await conn.execute(sa_text("SET LOCAL ROLE fulkro"))
        r = await conn.execute(sa_text(
            "SELECT COUNT(*) FROM knowledge_chunks WHERE embedding IS NOT NULL"
        ))
        embedded = r.scalar() or 0
    if embedded >= 100:
        report.add(
            "seed:corpus_embeddings", "skip",
            f"ya hay {embedded} chunks con embedding",
        )
        return
    try:
        from backend.app.corpus.rd311_embed import embed_rd311_chunks
    except Exception as exc:
        report.add("seed:corpus_embeddings", "fail", f"import: {exc}")
        return
    t0 = time.monotonic()
    try:
        async with Session() as db:
            await db.execute(sa_text("SET LOCAL ROLE fulkro"))
            emb_summary = await embed_rd311_chunks(db)
            await db.commit()
        elapsed = time.monotonic() - t0
        report.add(
            "seed:corpus_embeddings", "ok",
            f"embedded en {elapsed:.1f}s: "
            f"{emb_summary.get('chunks_embedded')} chunks",
        )
    except Exception as exc:
        report.add("seed:corpus_embeddings", "fail", f"embed error: {exc}")


# ════════════════════════════════════════════════════════════════════
# E. Clientes, F. Evidence catalog, G. AGE KG
# ════════════════════════════════════════════════════════════════════

def run_external_script(script_name: str, report: SeedReport) -> None:
    """Ejecuta un script seed externo con PYTHONPATH correcto."""
    script = Path(__file__).parent / script_name
    if not script.exists():
        report.add(f"seed:{script_name}", "fail", f"{script} no existe")
        return
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[2])
    t0 = time.monotonic()
    try:
        result = subprocess.run(
            [sys.executable, str(script)],
            env=env, capture_output=True, text=True, timeout=300,
        )
        elapsed = time.monotonic() - t0
        if result.returncode == 0:
            last_line = (result.stdout.strip().splitlines() or [""])[-1]
            report.add(
                f"seed:{script_name}", "ok",
                f"{elapsed:.1f}s · {last_line[:120]}",
            )
        else:
            report.add(
                f"seed:{script_name}", "fail",
                f"exit={result.returncode} · stderr={result.stderr[:200]}",
            )
    except subprocess.TimeoutExpired:
        report.add(f"seed:{script_name}", "fail", "timeout 300s")


async def seed_fake_clients(
    engine, report: SeedReport, skip: bool = False,
) -> None:
    if skip:
        report.add("seed:seed_fake_clients.py", "skip", "--skip-clients")
        return
    # En PRODUCCIÓN no se siembran clientes ficticios: el sistema arranca
    # vacío y el primer cliente real se da de alta desde el portal (guiado
    # por el copiloto). Los fakes (DataForma + 2) son fixtures dev/test/CI.
    if get_settings().is_production:
        report.add(
            "seed:seed_fake_clients.py", "skip",
            "producción · sin clientes de demostración (alta real desde portal)",
        )
        return
    # Skip si ya hay 3+ clientes seed (evita FK violation al re-ejecutar)
    async with engine.connect() as conn:
        await conn.execute(sa_text("SET LOCAL ROLE fulkro"))
        r = await conn.execute(sa_text(
            "SELECT COUNT(*) FROM clients WHERE lead_source = 'seed'"
        ))
        if (r.scalar() or 0) >= 3:
            report.add(
                "seed:seed_fake_clients.py", "skip",
                "ya hay 3+ clientes con lead_source='seed'",
            )
            return
    run_external_script("seed_fake_clients.py", report)


async def seed_evidence_catalog(engine, report: SeedReport) -> None:
    # Idempotente por naturaleza (INSERT ... ON CONFLICT), pero skip
    # si ya cubre 80 medidas
    async with engine.connect() as conn:
        await conn.execute(sa_text("SET LOCAL ROLE fulkro"))
        r = await conn.execute(sa_text(
            "SELECT COUNT(*) FROM ens_measure_evidencia_types"
        ))
        existing = r.scalar() or 0
    # Siempre lanzamos porque el script actualiza existentes
    run_external_script("seed_ens_evidence_catalog.py", report)


async def seed_iso27001_mapping(engine, report: SeedReport) -> None:
    """M9 · puebla ens_iso27001_mapping (~137 pares ISO27001:2022 → ENS).

    Sin este seed la tabla queda vacía y M21 iso27001_coverage devuelve 0%
    cobertura para CUALQUIER cliente (panel comercial engañoso). Idempotente
    (INSERT ... ON CONFLICT en el script)."""
    run_external_script("seed_ens_iso27001_mapping.py", report)


async def seed_age_kg(
    engine, report: SeedReport, skip: bool = False, age_installed: bool = True,
) -> None:
    if not age_installed:
        # La imagen no trae Apache AGE (caso del demo · ADR-056). El grafo es
        # un extra: 0 migraciones y 0 ficheros de backend/app lo consultan.
        report.add(
            "seed:age_seed_kg.py", "skip",
            "extension `age` no instalada en este PostgreSQL",
        )
        return
    if skip:
        # KG demo (Apache AGE) requiere superuser real para `LOAD 'age'`
        # (fulkro_app/fulkro_migrate no lo son sobre TCP). 0 tests dependen de
        # fulkro_kg → se omite en la BD de test. Ejecutable 8 Pasada 16.
        report.add("seed:age_seed_kg.py", "skip", "--skip-age-kg (LOAD age requiere superuser)")
        return
    # Always run — script is idempotent (CREATE ... IF NOT EXISTS + MERGE)
    run_external_script("age_seed_kg.py", report)


async def seed_pricing(engine, report: SeedReport) -> None:
    """Seed pricing_catalog (M23 Sesion 8 Paso 2)."""
    from backend.app.motors.m23_retainer.pricing_catalog_seed import (
        seed_pricing_catalog,
    )
    async with engine.begin() as conn:
        result = await seed_pricing_catalog(conn)
    inserted = result.get("inserted", 0)
    total = result.get("total") or result.get("skipped", 0)
    status = "ok" if inserted + total > 0 else "skip"
    report.add(
        "seed:pricing_catalog", status,
        f"inserted={inserted} skipped={result.get('skipped', 0)} total={total}",
    )


async def seed_templates(engine, report: SeedReport) -> None:
    """Seed catalogo de plantillas M06 (templates) desde el YAML → BD.

    Cablea ``DocumentFactoryService.load_template_metadata_from_catalog`` (upsert
    idempotente desde docs/catalogs/template_catalog_v1.yaml) al seed canonico.
    Antes solo lo invocaban scripts demo, por lo que la tabla `templates` quedaba
    vacia en fulkro_test (y en cualquier BD fresca) y NO se generaba NINGUN
    documento ENS end-to-end (hallazgo #10 B2). Solo filas: los DOCX base ya
    existen en var/templates_docx/ y el sync los autolinka via docx_path.
    """
    from backend.app.motors.m06_document_factory.service import (
        DocumentFactoryService,
    )

    Session = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as db:
        result = await DocumentFactoryService(db).load_template_metadata_from_catalog()
        await db.commit()
    created = result.get("created", 0)
    updated = result.get("updated", 0)
    total = result.get("total_in_catalog", 0)
    status = "ok" if (created + updated) > 0 else "fail"
    report.add(
        "seed:templates", status,
        f"created={created} updated={updated} total_catalog={total}",
    )


# ════════════════════════════════════════════════════════════════════
# Verificaciones finales
# ════════════════════════════════════════════════════════════════════

async def final_checks(
    engine, report: SeedReport, skip_clients: bool = False,
) -> None:
    async with engine.connect() as conn:
        await conn.execute(sa_text("SET LOCAL ROLE fulkro"))
        checks = [
            # 73 = medidas oficiales RD 311/2022 Anexo II (intersección
            # magerit_ens_mapping). El catálogo trae 79 entries (73 + 6 rollups
            # no-oficiales) pero seed_ens_measures filtra a 73 canónicos.
            # Ejecutable 8 Pasada 16 (antes 80 stale).
            ("ens_measures", 73),
            # 18 = combos (medida × código refuerzo) que rinde el catálogo
            # corregido vs RD 311/2022 Anexo II (Pasada 16 P16.B · antes 20
            # aproximado). Tabla legacy; la canónica nueva es ens_measure_refuerzos.
            ("ens_reinforcements", 18),
            ("magerit_ens_mapping", 73),
            ("threats", 50),
            ("safeguards", 80),
            ("magerit_asset_types", 50),
            # En producción el sistema arranca SIN clientes (alta real desde
            # el portal); en dev/test/CI se siembran 3 fakes (DataForma + 2).
            # Con --skip-clients el mínimo baja a 0: si no, el propio seed se
            # suspendería por no haber sembrado lo que se le pidió no sembrar.
            ("clients", 0 if (get_settings().is_production or skip_clients) else 3),
            ("pricing_catalog", 10),
            # 84 = entradas del catalogo template_catalog_v1.yaml (M06).
            # Sin este seed la fabrica documental no genera nada (#10 B2).
            ("templates", 84),
        ]
        for table, minimum in checks:
            r = await conn.execute(sa_text(f"SELECT COUNT(*) FROM {table}"))
            count = r.scalar() or 0
            status = "ok" if count >= minimum else "fail"
            report.add(
                f"final:{table}", status,
                f"{count} rows (min esperado {minimum})",
            )


# ════════════════════════════════════════════════════════════════════
# Main
# ════════════════════════════════════════════════════════════════════

async def main(
    skip_corpus: bool = False,
    skip_age_kg: bool = False,
    skip_clients: bool = False,
    optional_ext: set[str] | None = None,
) -> int:
    report = SeedReport()
    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=False)

    # Pre-checks
    ok, extensions = await pre_checks(engine, report, optional_ext)
    if not ok:
        print(json.dumps(report.summary(), indent=2, ensure_ascii=False))
        await engine.dispose()
        return 1

    # B + C: catalogos MAGERIT + ENS
    async with engine.begin() as conn:
        await seed_magerit_asset_types(conn, report)
        await seed_magerit_threats(conn, report)
        await seed_magerit_safeguards(conn, report)
        await seed_magerit_ens_mapping(conn, report)
        await seed_ens_measures(conn, report)
        await seed_ens_reinforcements(conn, report)

    # D: corpus
    await seed_corpus(engine, report, skip=skip_corpus)

    # E + F + G via scripts externos
    await seed_fake_clients(engine, report, skip=skip_clients)
    await seed_evidence_catalog(engine, report)
    await seed_iso27001_mapping(engine, report)
    await seed_age_kg(
        engine, report, skip=skip_age_kg, age_installed="age" in extensions,
    )
    await seed_pricing(engine, report)
    await seed_templates(engine, report)

    # Final checks
    await final_checks(engine, report, skip_clients=skip_clients)

    summary = report.summary()
    print(json.dumps(summary, indent=2, ensure_ascii=False, default=str))
    await engine.dispose()
    return 0 if summary["fail"] == 0 else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-corpus", action="store_true",
                        help="No re-ingestar RD 311/2022")
    parser.add_argument("--skip-age-kg", action="store_true",
                        help="No seedear el grafo Apache AGE (requiere superuser LOAD age)")
    # scripts/deploy-hetzner.sh:131 ya pasaba --skip-clients, que NO existía:
    # argparse salía con codigo 2 y el paso de seed del despliegue moría ahi.
    parser.add_argument("--skip-clients", action="store_true",
                        help="No sembrar los 3 clientes ficticios (dev/test/CI)")
    parser.add_argument("--optional-ext", default=None,
                        help=("Extensiones que pueden faltar sin abortar "
                              "(solo age,pgaudit). Tambien por entorno: "
                              "FULKRO_SEED_OPTIONAL_EXT"))
    args = parser.parse_args()
    sys.exit(asyncio.run(main(
        skip_corpus=args.skip_corpus,
        skip_age_kg=args.skip_age_kg,
        skip_clients=args.skip_clients,
        optional_ext=resolve_optional_ext(args.optional_ext),
    )))
