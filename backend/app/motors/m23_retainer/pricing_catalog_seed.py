"""Seeds pricing_catalog segun imagen oficial 2026-04-21.

4 niveles retainer + 3 implantacion + extras (sector regulado,
multi-ubicacion, formacion extra, etc.).

Invocable desde seed_all_fulkro.py o standalone.
"""
from __future__ import annotations

import asyncio
import os
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
os.environ.setdefault("FULKRO_SKIP_WORKFLOW_GATES", "1")

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from backend.app.config import get_settings


EFFECTIVE_FROM = date(2026, 4, 21)


PRICING_ENTRIES = [
    # ── Retainer (4 niveles, segun imagen) ──
    {
        "category": "retainer", "tier_code": "R_MICRO",
        "name": "Retainer Micro (post-Basica)",
        "base_price": 150.00, "billing_unit": "mensual",
        "description": "Post-certificacion Basica. Vigilancia + reporte "
                       "trimestral + comite semestral. SLA best-effort.",
        "extras_jsonb": {
            "sector_regulado": 0,  # no aplica en Basica
            "incident_support_hour": 85.00,
        },
    },
    {
        "category": "retainer", "tier_code": "R_LITE",
        "name": "Retainer Lite (Basica/Media simple)",
        "base_price": 300.00, "billing_unit": "mensual",
        "description": "Micro/pyme <=25 usuarios. Comite semestral + "
                       "auditoria interna anual + vuln mensual. SLA 72h.",
        "extras_jsonb": {
            "sector_regulado": 150.00,
            "multi_ubicacion": 100.00,
            "incident_support_hour": 85.00,
        },
    },
    {
        "category": "retainer", "tier_code": "R_STD",
        "name": "Retainer Standard (Media + CISO externo)",
        "base_price": 700.00, "billing_unit": "mensual",
        "description": "Pyme 26-150 usuarios, categoria MEDIA. Comite "
                       "trimestral + todas anuales + CISO ext + vuln "
                       "semanal. SLA 48h. Base del negocio.",
        "extras_jsonb": {
            "sector_regulado": 250.00,
            "multi_ubicacion": 200.00,
            "formacion_extra_sesion": 180.00,
            "incident_support_hour": 95.00,
        },
    },
    {
        "category": "retainer", "tier_code": "R_PLUS",
        "name": "Retainer Plus (Media complejo / Alta)",
        "base_price": 1200.00, "billing_unit": "mensual",
        "description": "150-500 usuarios, multi-sede/cloud, MEDIA-ALTA. "
                       "Comite mensual + pentest anual + phishing trimestral "
                       "+ vuln semanal. SLA 24h.",
        "extras_jsonb": {
            "sector_regulado": 300.00,
            "multi_ubicacion": 300.00,
            "redteam_anual": 2500.00,
            "formacion_extra_sesion": 200.00,
            "incident_support_hour": 110.00,
        },
    },
    # ── Implantacion (proyecto fijo) ──
    {
        "category": "implantacion", "tier_code": "BASICA",
        "name": "Implantacion ENS Categoria Basica",
        "base_price": 5500.00, "billing_unit": "proyecto_fijo",
        "description": "Proyecto de adecuacion ENS Basica, "
                       "4-6 meses, todo-incluido.",
        "extras_jsonb": {
            "sector_regulado": 1000.00,
            "multi_ubicacion": 750.00,
        },
    },
    {
        "category": "implantacion", "tier_code": "MEDIA",
        "name": "Implantacion ENS Categoria Media",
        "base_price": 9500.00, "billing_unit": "proyecto_fijo",
        "description": "Proyecto de adecuacion ENS Media, "
                       "8-10 meses, todo-incluido.",
        "extras_jsonb": {
            "sector_regulado": 2000.00,
            "multi_ubicacion": 1500.00,
        },
    },
    {
        "category": "implantacion", "tier_code": "ALTA",
        "name": "Implantacion ENS Categoria Alta",
        "base_price": 17500.00, "billing_unit": "proyecto_fijo",
        "description": "Proyecto de adecuacion ENS Alta, "
                       "10-14 meses, todo-incluido con red team.",
        "extras_jsonb": {
            "sector_regulado": 3500.00,
            "multi_ubicacion": 2500.00,
            "redteam_extra": 3000.00,
        },
    },
    # ── Complementarios (eventos puntuales) ──
    {
        "category": "complementario", "tier_code": "AUDIT_RECERT",
        "name": "Re-certificacion bianual (auditoria externa + dossier)",
        "base_price": 2500.00, "billing_unit": "evento",
        "description": "Preparacion re-certificacion a los 2 anios + "
                       "acompañamiento auditoria externa.",
        "extras_jsonb": {},
    },
    {
        "category": "complementario", "tier_code": "INCIDENT_RESPONSE",
        "name": "Respuesta a incidente (fuera de horario)",
        "base_price": 150.00, "billing_unit": "hora",
        "description": "Intervencion urgente incident response. "
                       "Minimo 2h. Factura por tramos 30 min.",
        "extras_jsonb": {"fuera_horario_pct": 1.5},
    },
    {
        "category": "complementario", "tier_code": "FORMACION_EXTRA",
        "name": "Sesion de formacion extra (presencial/remota)",
        "base_price": 450.00, "billing_unit": "evento",
        "description": "Sesion formacion adicional (no incluida en retainer).",
        "extras_jsonb": {},
    },
]


async def seed_pricing_catalog(conn) -> dict:
    """Inserta/actualiza PRICING_ENTRIES en pricing_catalog. Idempotente.

    Accepts AsyncConnection (desde engine.begin()) o AsyncSession
    (desde sessionmaker). Ambos soportan execute(); flush() solo se
    llama si es Session.
    """
    await conn.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    r = await conn.execute(text("SELECT COUNT(*) FROM pricing_catalog"))
    existing = r.scalar() or 0
    if existing >= len(PRICING_ENTRIES):
        return {"inserted": 0, "skipped": existing}

    inserted = 0
    import json as _json
    for entry in PRICING_ENTRIES:
        r = await conn.execute(text("""
            SELECT id FROM pricing_catalog
            WHERE category = :cat AND tier_code = :tc
              AND effective_from = :ef
              AND deleted_at IS NULL
        """), {
            "cat": entry["category"], "tc": entry["tier_code"],
            "ef": EFFECTIVE_FROM,
        })
        if r.scalar_one_or_none():
            continue
        await conn.execute(text("""
            INSERT INTO pricing_catalog
                (id, category, tier_code, name, base_price, currency,
                 billing_unit, extras_jsonb, description, effective_from,
                 version, is_active, created_at)
            VALUES
                (gen_random_uuid(), :cat, :tc, :name, :price, 'EUR',
                 :unit, CAST(:extras AS JSONB), :desc, :ef,
                 '2026-04-21', true, NOW())
        """), {
            "cat": entry["category"], "tc": entry["tier_code"],
            "name": entry["name"], "price": entry["base_price"],
            "unit": entry["billing_unit"],
            "extras": _json.dumps(entry.get("extras_jsonb") or {}),
            "desc": entry.get("description", ""),
            "ef": EFFECTIVE_FROM,
        })
        inserted += 1
    flush = getattr(conn, "flush", None)
    if callable(flush):
        await flush()
    return {"inserted": inserted, "total": len(PRICING_ENTRIES)}


async def _main_standalone() -> int:
    engine = create_async_engine(get_settings().database_url, echo=False)
    async with engine.begin() as conn:
        result = await seed_pricing_catalog(conn)
    print(f"pricing_catalog: {result}")
    await engine.dispose()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(_main_standalone()))
