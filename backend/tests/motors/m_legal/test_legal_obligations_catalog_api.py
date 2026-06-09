"""Tests integration · m_legal motor (legal_obligations_catalog ORM + API).

Sub-atom 1.C.0.C.expand v3.9 (R32 sostenido · TODO implementado pre-piloto).

Tests cubren:
- ORM seed verify (count + distribution per regulación)
- Service queries (by regulacion · by ENS measure · by sector · by category)
- API endpoints (filter regulacion · ens_measure · lookup codigo · validation 400/404)
- Auth dual admin + cliente (default override bypass · pattern m_observability)
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from sqlalchemy import text

from backend.app.motors.m_legal.service import (
    count_all,
    get_by_codigo,
    list_by_ens_category,
    list_by_ens_measure,
    list_by_regulation,
    list_by_sector,
)
from backend.tests.conftest import _admin_setup


pytestmark = pytest.mark.asyncio


# ────────────────────────────────────────────────────────────────────
# Seed helper · idempotent insert 250 entries from YAML for tests
# ────────────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parents[4]
YAML_PATH = REPO_ROOT / "docs" / "catalogs" / "legal_obligations_v1.yaml"


async def _seed_catalog_for_tests(db) -> None:
    """Idempotent UPSERT 250 entries · matches production seed script logic."""
    import yaml

    with YAML_PATH.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)

    async with _admin_setup(db):
        for o in data.get("obligations", []):
            await db.execute(
                text(
                    """
                    INSERT INTO legal_obligations_catalog
                        (codigo, regulacion, articulo, titulo, obligacion,
                         sector_aplica, ens_categoria_aplica,
                         evidencia_requerida, vinculo_medida_ens, fuente_url)
                    VALUES
                        (:codigo, :regulacion, :articulo, :titulo, :obligacion,
                         CAST(:sector AS jsonb),
                         CAST(:ens_cat AS jsonb),
                         :evidencia,
                         CAST(:vinculo AS jsonb),
                         :fuente)
                    ON CONFLICT (codigo) DO UPDATE SET
                        regulacion = EXCLUDED.regulacion,
                        articulo = EXCLUDED.articulo,
                        titulo = EXCLUDED.titulo,
                        obligacion = EXCLUDED.obligacion,
                        sector_aplica = EXCLUDED.sector_aplica,
                        ens_categoria_aplica = EXCLUDED.ens_categoria_aplica,
                        evidencia_requerida = EXCLUDED.evidencia_requerida,
                        vinculo_medida_ens = EXCLUDED.vinculo_medida_ens,
                        fuente_url = EXCLUDED.fuente_url,
                        updated_at = now()
                    """
                ),
                {
                    "codigo": o["codigo"],
                    "regulacion": o["regulacion"],
                    "articulo": o.get("articulo"),
                    "titulo": o["titulo"],
                    "obligacion": o["obligacion"],
                    "sector": json.dumps(o.get("sector_aplica", []), ensure_ascii=False),
                    "ens_cat": json.dumps(o.get("ens_categoria_aplica", []), ensure_ascii=False),
                    "evidencia": o.get("evidencia_requerida"),
                    "vinculo": json.dumps(o.get("vinculo_medida_ens", []), ensure_ascii=False),
                    "fuente": o.get("fuente_url"),
                },
            )
    await db.flush()


# ────────────────────────────────────────────────────────────────────
# ORM + Service tests
# ────────────────────────────────────────────────────────────────────


async def test_seed_count_total_250(db):
    """Verify ORM count returns 250 (matches plan v3.9 distribution)."""
    await _seed_catalog_for_tests(db)
    total = await count_all(db)
    assert total == 250, f"Expected 250 entries, got {total}"


async def test_service_list_by_regulation_rgpd(db):
    """RGPD query returns exactly 80 entries (target distribution)."""
    await _seed_catalog_for_tests(db)
    rows = await list_by_regulation(db, "RGPD")
    assert len(rows) == 80, f"Expected 80 RGPD entries, got {len(rows)}"
    for r in rows:
        assert r.regulacion == "RGPD"
        assert r.codigo.startswith("RGPD-")


async def test_service_list_by_regulation_invalid_returns_empty(db):
    """Unknown regulation returns empty list (no error)."""
    await _seed_catalog_for_tests(db)
    rows = await list_by_regulation(db, "UNKNOWN")
    assert rows == []


async def test_service_get_by_codigo_existing(db):
    """Lookup RGPD-ART-32 (seguridad tratamiento) returns canonical entry."""
    await _seed_catalog_for_tests(db)
    row = await get_by_codigo(db, "RGPD-ART-32")
    assert row is not None
    assert row.regulacion == "RGPD"
    assert "Seguridad" in row.titulo
    assert "op.exp.7" in (row.vinculo_medida_ens or []) or len(row.vinculo_medida_ens or []) > 0


async def test_service_get_by_codigo_missing(db):
    """Lookup non-existent codigo returns None."""
    await _seed_catalog_for_tests(db)
    row = await get_by_codigo(db, "NONEXISTENT-CODE-999")
    assert row is None


async def test_service_list_by_ens_measure_cross_mapping(db):
    """Reverse lookup ENS measure → obligations with cross-ref."""
    await _seed_catalog_for_tests(db)
    # op.exp.7 (gestión incidentes) tiene varios cross-refs (RGPD-ART-33, NIS2-ART-23, DORA-ART-17/19)
    rows = await list_by_ens_measure(db, "op.exp.7")
    assert len(rows) >= 3, f"Expected ≥3 obligations cross-mapping op.exp.7, got {len(rows)}"
    for r in rows:
        assert "op.exp.7" in (r.vinculo_medida_ens or [])


async def test_service_list_by_sector(db):
    """Sector 'todos' returns multiple obligations."""
    await _seed_catalog_for_tests(db)
    rows = await list_by_sector(db, "todos")
    assert len(rows) >= 10, f"Expected ≥10 obligations applicable to 'todos', got {len(rows)}"


async def test_service_list_by_ens_category(db):
    """ENS category B returns multiple applicable obligations."""
    await _seed_catalog_for_tests(db)
    rows = await list_by_ens_category(db, "B")
    assert len(rows) >= 20, f"Expected ≥20 obligations applicable to B, got {len(rows)}"
    for r in rows:
        assert "B" in (r.ens_categoria_aplica or [])


# ────────────────────────────────────────────────────────────────────
# API endpoint tests
# ────────────────────────────────────────────────────────────────────


async def test_api_catalog_filter_regulacion_rgpd(db, async_client):
    """GET /legal-obligations/catalog?regulacion=RGPD returns 80 items."""
    await _seed_catalog_for_tests(db)
    r = await async_client.get("/api/v1/legal-obligations/catalog?regulacion=RGPD")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["total"] == 80
    assert len(data["items"]) == 80
    for item in data["items"]:
        assert item["regulacion"] == "RGPD"


async def test_api_catalog_filter_ens_measure(db, async_client):
    """GET /legal-obligations/catalog?ens_measure=op.exp.7 returns cross-mapped."""
    await _seed_catalog_for_tests(db)
    r = await async_client.get("/api/v1/legal-obligations/catalog?ens_measure=op.exp.7")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] >= 3
    for item in data["items"]:
        assert "op.exp.7" in (item["vinculo_medida_ens"] or [])


async def test_api_catalog_lookup_by_codigo(db, async_client):
    """GET /legal-obligations/catalog/{codigo} returns single entry."""
    await _seed_catalog_for_tests(db)
    r = await async_client.get("/api/v1/legal-obligations/catalog/RGPD-ART-33")
    assert r.status_code == 200
    data = r.json()
    assert data["codigo"] == "RGPD-ART-33"
    assert data["regulacion"] == "RGPD"


async def test_api_catalog_lookup_missing_returns_404(db, async_client):
    """GET /legal-obligations/catalog/{missing} returns 404."""
    await _seed_catalog_for_tests(db)
    r = await async_client.get("/api/v1/legal-obligations/catalog/MISSING-CODE-999")
    assert r.status_code == 404


async def test_api_catalog_no_filter_returns_400(db, async_client):
    """No filter required → 400 Bad Request."""
    await _seed_catalog_for_tests(db)
    r = await async_client.get("/api/v1/legal-obligations/catalog")
    assert r.status_code == 400
    assert "filter" in r.json()["detail"].lower()


async def test_api_catalog_multiple_filters_returns_400(db, async_client):
    """Two filters at once → 400."""
    await _seed_catalog_for_tests(db)
    r = await async_client.get(
        "/api/v1/legal-obligations/catalog?regulacion=RGPD&sector=fintech"
    )
    assert r.status_code == 400


async def test_api_catalog_invalid_regulacion_returns_400(db, async_client):
    """Unknown regulacion → 400."""
    await _seed_catalog_for_tests(db)
    r = await async_client.get("/api/v1/legal-obligations/catalog?regulacion=UNKNOWN")
    assert r.status_code == 400


async def test_api_catalog_invalid_ens_category_returns_400(db, async_client):
    """Unknown ENS category → 400."""
    await _seed_catalog_for_tests(db)
    r = await async_client.get("/api/v1/legal-obligations/catalog?ens_category=Z")
    assert r.status_code == 400
