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
    """sector_aplicacion=['publico','privado'] debe incluir docs de AMBOS cubos.

    El invariante es que pedir los dos sectores no colapse en uno solo: los
    resultados tienen que mezclar un documento marcado exclusivamente
    ``{privado}`` con otro marcado ``{publico,privado}``. Antes se comprobaba
    exigiendo un documento CCN-STIC en el top-10; se comprueba igual de bien
    con UE-DORA (privado) frente a RD 311/2022, NIS2, RGPD o eIDAS
    (publico+privado), y ademas sin depender de material de terceros que ya
    no se versiona. La consulta es "notificacion de incidentes" porque cubre
    los dos cubos de forma estable.
    """
    results = await hybrid_search(
        db, "notificacion de incidentes", top_k=10,
        sector_aplicacion=["publico", "privado"],
    )
    assert len(results) > 0
    sources = {r.source_code for r in results if r.source_code}

    # Cubo exclusivo de 'privado'.
    assert "UE-DORA" in sources, (
        f"Esperaba un documento solo-privado (UE-DORA) en results: {sorted(sources)}"
    )
    # Cubo compartido 'publico'+'privado'.
    compartidos = sources & {"RD_311_2022", "UE-NIS2", "UE-RGPD", "UE-EIDAS"}
    assert compartidos, (
        f"Esperaba al menos un documento publico+privado en results: {sorted(sources)}"
    )
