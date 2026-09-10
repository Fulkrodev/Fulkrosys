"""Recuperacion sobre el corpus normativo: ranking vectorial (pgvector).

HUBO UNA FUSION AQUI, Y SE QUITO EL 2026-09-11 PORQUE SE MIDIO
--------------------------------------------------------------
Hasta esa fecha este modulo fusionaba dos ramas con Reciprocal Rank Fusion:
un ranking lexico de PostgreSQL y el coseno de pgvector. Ya no. La fusion no
se ha quitado por gusto arquitectonico sino porque perdia, y consta el numero:

  Sobre 49 consultas de cumplimiento etiquetadas a mano (docs/EVAL_RECUPERACION.md,
  `make eval-recuperacion`), con la rama lexica YA ARREGLADA:

    rama         hit@5    recall@5    MRR
    vectorial    0,959      0,824    0,752
    fusion RRF   0,857      0,667    0,627

  Los tres contrastes pareados vectorial - fusion excluyen el cero
  (hit@5 +0,102 [+0,020, +0,204] · recall@5 +0,157 [+0,065, +0,255] ·
  MRR +0,125 [+0,013, +0,246]). Y el dato que cierra la puerta: la rama lexica
  aporto 0 de 96 fragmentos relevantes que el vector no trajera ya en su top-30,
  y hubo 0 consultas rescatadas solo por ella. No es que pesara poco: es que no
  aportaba nada y desplazaba.

  Se barrio ademas el peso de la rama lexica en la fusion, w en [0, 1] de 0,1 en
  0,1. La curva es monotona decreciente y su maximo esta en w = 0, que ES no
  fusionar. Ninguno de los 30 contrastes contra w = 0 excluye el cero.

ALCANCE DE ESA EVIDENCIA, DICHO ANTES DE QUE ALGUIEN LO PREGUNTE
  1.031 fragmentos, cinco normas, un solo modelo de embeddings (e5-large), 49
  consultas etiquetadas por quien conoce el corpus. Con un corpus mucho mayor,
  con vocabulario mas raro (codigos, referencias exactas) o con otro modelo, una
  rama lexica puede volver a ganarse el sitio. Por eso el arnes de evaluacion
  SIGUE midiendo las cinco ramas: `make eval-recuperacion` vuelve a responder la
  pregunta cuando el corpus cambie. Lo que no se sostiene es mantener en el
  camino caliente una rama que hoy esta medida y no aporta.

Y NO ERA BM25, aunque el codigo lo llamara asi hasta 2026-09-11. Postgres no
implementa BM25: `ts_rank_cd` puntua la densidad de coincidencias DENTRO del
documento y no sabe nada de la IDF (la rareza del termino en el corpus entero)
ni normaliza contra la longitud MEDIA del corpus. Son justo las dos mitades de
BM25. El nombre hacia esperar de esa rama un comportamiento que no tenia.

Lo consume el Motor 11 Copiloto y cualquier agente que necesite RAG anclado.

Refs:
- Robertson & Zaragoza (2009) "The Probabilistic Relevance Framework: BM25 and
  Beyond" — para el contraste de arriba
- Wang et al. (2024) "Text Embeddings by Weakly-Supervised Contrastive
  Pre-training" (e5) — de donde salen los prefijos query:/passage:
- ENS_PLATFORM_MASTER_SPEC_v2.1 sec 4.5
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from time import perf_counter as _perf_counter
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.ai.embeddings import get_default_embedding_provider
from backend.app.motors.m_observability.metricas import (
    observar_recuperacion as _observar_recuperacion,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DEFAULT_VECTOR_TOP = 30
DEFAULT_FINAL_TOP = 5

# e5 se entreno con prefijos asimetricos y los espera: la consulta lleva
# 'query: ' y el documento 'passage: '. Comprobado contra la base (F5 del bloque
# F): los 1.031 embeddings guardados llevan 'passage: ', unanime en la muestra.
E5_QUERY_PREFIX = "query: "


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------
@dataclass
class CorpusResult:
    """Un fragmento recuperado, con su procedencia.

    Se llamaba `HybridResult` y traia dos campos mas, `bm25_rank` y `rrf_score`.
    Los tres nombres prometian una fusion que ya no existe y una funcion de
    puntuacion que Postgres nunca implemento. Ver el docstring del modulo.
    """

    chunk_id: str
    content: str
    measure_code: Optional[str]
    document_title: str
    source_code: Optional[str]
    heading_path: Optional[str]
    article_ref: Optional[str]
    vector_rank: int  # 1-indexado dentro de esta busqueda
    # Similitud coseno DE ESTE fragmento con la consulta (0..1, e5 + L2).
    score: float
    # Similitud coseno del MEJOR fragmento de la busqueda. Es la misma cifra en
    # todos los resultados de una consulta: senal global «cuanto se acerca el
    # corpus a esta pregunta». La consume el repliegue corpus_gap de A14
    # (umbral 0,45). Coincide con `score` del primer resultado por construccion;
    # se conserva como campo propio porque hay consumidores que leen
    # `results[0].confidence` sin mirar el orden.
    confidence: float = 0.0



# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _l2_normalize(vec: list[float]) -> list[float]:
    n = math.sqrt(sum(x * x for x in vec))
    return [x / n for x in vec] if n > 0 else vec


def _filtros(
    only_with_measure_code: bool,
    source_codes: Optional[list[str]],
    measure_codes: Optional[list[str]],
    sector_aplicacion: Optional[list[str]],
    params: dict,
) -> list[str]:
    """Clausulas WHERE comunes. Muta `params` con los valores que necesita."""
    where = ["c.embedding IS NOT NULL"]
    if measure_codes:
        where.append("LOWER(c.measure_code) = ANY(:measure_codes)")
        params["measure_codes"] = [m.lower() for m in measure_codes]
    elif only_with_measure_code:
        where.append("c.measure_code IS NOT NULL")
    if source_codes:
        where.append("s.code = ANY(:source_codes)")
        params["source_codes"] = source_codes
    if sector_aplicacion:
        # Solapamiento de arrays: cierto si coincide algun elemento.
        where.append("d.sector_aplicacion && CAST(:sector_aplicacion AS TEXT[])")
        params["sector_aplicacion"] = sector_aplicacion
    return where


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def corpus_search(
    session: AsyncSession,
    query: str,
    top_k: int = DEFAULT_FINAL_TOP,
    vector_top: int = DEFAULT_VECTOR_TOP,
    only_with_measure_code: bool = False,
    source_codes: Optional[list[str]] = None,
    measure_codes: Optional[list[str]] = None,
    sector_aplicacion: Optional[list[str]] = None,
) -> list[CorpusResult]:
    """Busqueda vectorial sobre el corpus normativo.

    Args:
        session: AsyncSession conectada a la base del corpus.
        query: pregunta en lenguaje natural, en espanol.
        top_k: numero de resultados finales (5 por defecto).
        vector_top: candidatos que pide a pgvector antes de recortar a top_k.
            Sigue existiendo aunque ya no haya fusion porque los filtros de
            abajo se aplican en SQL y el recorte final se hace en Python.
        only_with_measure_code: limita a fragmentos de medidas ENS.
        source_codes: limita a fuentes concretas del corpus.
        measure_codes: limita a medidas ENS concretas (p. ej. ["op.acc.6"]).
            Esta es la via para una busqueda por codigo exacto; no depende de
            que ningun ranking lexico acierte con el codigo.
        sector_aplicacion: limita a documentos con al menos uno de esos sectores
            (solapamiento de arrays de PostgreSQL). Ejemplo: ["privado"] excluye
            los etiquetados solo ["publico"]. None = sin filtro.
            Sub-lote 1.B.5.2 · ADR-CORPUS-001 Decision 7 · AMEND-012.

    Returns:
        Lista de CorpusResult ordenada por similitud coseno descendente.
    """
    # Cada etapa se cronometra por separado (BLOQUE G). Se mide POR ETAPA y no
    # solo el total porque el total no dice donde esta el problema. Medido en el
    # bloque F: el embebido de la consulta es el 80 % del tiempo (p50 32,8 ms de
    # 41,2 ms totales); Postgres son 3 ms. Optimizar SQL aqui seria trabajar
    # sobre el 7 % del reloj.
    _t = _perf_counter()
    provider = get_default_embedding_provider()
    query_emb = _l2_normalize(provider.embed_query(E5_QUERY_PREFIX + query))
    _observar_recuperacion("embebido", _perf_counter() - _t)

    params: dict = {"qemb": str(query_emb), "k": vector_top}
    where = _filtros(only_with_measure_code, source_codes, measure_codes,
                     sector_aplicacion, params)

    _t = _perf_counter()
    sql = (
        "SELECT c.id::text, c.content, c.measure_code, c.heading_path, "
        "c.article_ref, d.title AS doc_title, s.code AS source_code, "
        "1 - (c.embedding <=> CAST(:qemb AS vector)) AS cos_sim "
        "FROM knowledge_chunks c "
        "JOIN knowledge_documents d ON d.id = c.document_id "
        "LEFT JOIN knowledge_sources s ON s.id = d.source_id "
        f"WHERE {' AND '.join(where)} "
        "ORDER BY c.embedding <=> CAST(:qemb AS vector) LIMIT :k"
    )
    rows = list(await session.execute(text(sql), params))
    _observar_recuperacion("vectorial", _perf_counter() - _t)

    top_cos = float(rows[0][7]) if rows else 0.0
    return [
        CorpusResult(
            chunk_id=row[0],
            content=row[1] or "",
            measure_code=row[2],
            document_title=row[5] or "",
            source_code=row[6],
            heading_path=row[3],
            article_ref=row[4],
            vector_rank=idx + 1,
            score=float(row[7]),
            confidence=top_cos,
        )
        for idx, row in enumerate(rows[:top_k])
    ]
