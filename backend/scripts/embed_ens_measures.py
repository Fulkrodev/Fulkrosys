"""S11 · Pre-cálculo de embeddings de las medidas ENS (ens_measures.embedding).

Habilita la Capa 2 (búsqueda semántica) de m08 EnsMapper: mapea un finding de
pentest a la medida ENS más cercana por similitud coseno (pgvector), como puente
entre la Capa 1 (CVE/regla) y la Capa 3 (LLM).

INFRA-GATED: requiere fastembed con el modelo intfloat/multilingual-e5-large
(1024 dims · mismo que el corpus RAG). Idempotente (UPDATE por código). Se ejecuta
una vez tras desplegar / cuando cambie el catálogo de medidas.

Uso (desde la raíz del repo, en el host con fastembed):
    .venv/bin/python -m backend.scripts.embed_ens_measures
"""
from __future__ import annotations

import asyncio

from sqlalchemy import text as sa_text

from backend.app.core.ai.embeddings import get_default_embedding_provider
from backend.app.database import async_session


async def _run() -> int:
    provider = get_default_embedding_provider()
    async with async_session() as db:
        rows = (await db.execute(
            sa_text(
                "SELECT codigo, nombre, COALESCE(descripcion, '') "
                "FROM ens_measures ORDER BY codigo"
            )
        )).all()
        n = 0
        for codigo, nombre, descripcion in rows:
            # Prefijo 'passage:' (e5) para documentos · coherente con el corpus.
            texto = f"passage: {codigo} {nombre}. {descripcion}".strip()
            emb = provider.embed_documents([texto])[0]
            await db.execute(
                sa_text(
                    "UPDATE ens_measures SET embedding = CAST(:e AS vector) "
                    "WHERE codigo = :c"
                ),
                {"e": str(list(emb)), "c": codigo},
            )
            n += 1
        await db.commit()
        return n


def main() -> None:
    count = asyncio.run(_run())
    print(f"embed_ens_measures: {count} medidas ENS embebidas (vector 1024)")


if __name__ == "__main__":
    main()
