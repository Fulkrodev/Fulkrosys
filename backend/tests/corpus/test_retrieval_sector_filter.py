"""Tests retrieval sector_aplicacion filter · sub-lote 1.B.5.2 PASO 5.

Valida que hybrid_search(sector_aplicacion=...) filtra correctamente por
array overlap sobre knowledge_documents.sector_aplicacion. Backward-compat:
sector_aplicacion=None devuelve TODOS los docs (sin filtro).

Requires: DB live con corpus 1.B.5.2 ingerido (incluye UE-DORA solo 'privado'
+ otros docs ['publico','privado']).
"""
from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.corpus.retrieval import hybrid_search


@pytest.mark.asyncio
async def test_sector_none_default_backward_compat(db: AsyncSession):
    """sector_aplicacion=None devuelve resultados sin filtrar (backward compat)."""
    results = await hybrid_search(
        db, "resiliencia operativa digital", top_k=5,
    )
    assert len(results) > 0
    # Sin sector filter · pueden venir docs de cualquier sector


@pytest.mark.asyncio
async def test_sector_privado_includes_dora(db: AsyncSession):
    """DORA (sector_aplicacion=['privado']) debe aparecer en query relevante."""
    results = await hybrid_search(
        db, "DORA resiliencia operativa digital sector financiero",
        top_k=10, sector_aplicacion=["privado"],
    )
    sources = {r.source_code for r in results if r.source_code}
    assert "UE-DORA" in sources, (
        f"UE-DORA no en resultados con sector_aplicacion=['privado']: {sorted(sources)}"
    )


@pytest.mark.asyncio
async def test_sector_solo_publico_excluye_dora(db: AsyncSession):
    """sector_aplicacion=['publico'] debe EXCLUIR UE-DORA (que es solo 'privado').

    Verifica el caso edge donde DORA es el unico doc del corpus marcado solo
    como 'privado' · no debe aparecer si filtramos por 'publico' exclusivo.
    """
    results = await hybrid_search(
        db, "DORA resiliencia operativa digital sector financiero",
        top_k=10, sector_aplicacion=["publico"],
    )
    sources = {r.source_code for r in results if r.source_code}
    assert "UE-DORA" not in sources, (
        f"UE-DORA NO debe aparecer con sector_aplicacion=['publico']: {sorted(sources)}"
    )


@pytest.mark.asyncio
async def test_sector_ambos_incluye_todos(db: AsyncSession):
    """sector_aplicacion=['publico','privado'] debe incluir docs de cualquiera de los dos."""
    results = await hybrid_search(
        db, "auditoria ENS", top_k=10,
        sector_aplicacion=["publico", "privado"],
    )
    assert len(results) > 0
    # Debe incluir CCN-STIC docs (publico,privado)
    sources = {r.source_code for r in results if r.source_code}
    ccn_docs = {s for s in sources if s.startswith("CCN-STIC")}
    assert len(ccn_docs) > 0, f"Esperaba CCN-STIC en results: {sorted(sources)}"
