"""Corpus audit — read-only inspection of knowledge_* tables."""
import sys
sys.path.insert(0, '/home/usuario/fulkro')
import asyncio
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(dotenv_path=Path('/home/usuario/fulkro/.env'))
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import os


async def audit():
    url = os.getenv('DATABASE_URL')
    engine = create_async_engine(url)
    async with engine.connect() as conn:
        print('=== KNOWLEDGE_SOURCES ===')
        r = await conn.execute(text('SELECT COUNT(*) FROM knowledge_sources'))
        print(f'Total sources: {r.scalar()}')
        r = await conn.execute(text(
            'SELECT code, title, publisher, version, language '
            'FROM knowledge_sources ORDER BY code'
        ))
        for row in r:
            print(f'  - [{row[0]}] {row[1][:80]} | pub={row[2]} | ver={row[3]} | lang={row[4]}')

        print()
        print('=== KNOWLEDGE_DOCUMENTS ===')
        r = await conn.execute(text('SELECT COUNT(*) FROM knowledge_documents'))
        print(f'Total documents: {r.scalar()}')
        r = await conn.execute(text(
            'SELECT titulo, fuente, id, source_id '
            'FROM knowledge_documents ORDER BY titulo LIMIT 30'
        ))
        for row in r:
            src = str(row[3])[:8] if row[3] else 'NULL'
            print(f'  - {row[0][:70]} | fuente={row[1]} | id={str(row[2])[:8]} | src={src}')

        print()
        print('=== KNOWLEDGE_CHUNKS totales ===')
        r = await conn.execute(text('SELECT COUNT(*) FROM knowledge_chunks'))
        print(f'Total chunks: {r.scalar()}')
        r = await conn.execute(text(
            'SELECT COUNT(*) FROM knowledge_chunks WHERE content IS NOT NULL'
        ))
        print(f'With content NOT NULL: {r.scalar()}')
        r = await conn.execute(text(
            'SELECT COUNT(*) FROM knowledge_chunks WHERE embedding IS NOT NULL'
        ))
        print(f'With embedding NOT NULL: {r.scalar()}')
        r = await conn.execute(text(
            'SELECT COUNT(*) FROM knowledge_chunks WHERE measure_code IS NOT NULL'
        ))
        print(f'With measure_code NOT NULL: {r.scalar()}')
        r = await conn.execute(text(
            'SELECT COUNT(DISTINCT measure_code) FROM knowledge_chunks WHERE measure_code IS NOT NULL'
        ))
        print(f'Unique measure_codes: {r.scalar()}')

        print()
        print('=== CHUNKS por document ===')
        r = await conn.execute(text(
            'SELECT d.titulo, COUNT(c.id) AS chunks, '
            'COUNT(c.embedding) AS with_emb, '
            'COUNT(c.measure_code) AS with_mc '
            'FROM knowledge_documents d LEFT JOIN knowledge_chunks c ON c.document_id = d.id '
            'GROUP BY d.id, d.titulo ORDER BY chunks DESC LIMIT 20'
        ))
        for row in r:
            print(f'  {row[0][:65]:<65} ch={row[1]:5d} emb={row[2]:5d} mc={row[3]:4d}')

        print()
        print('=== Sample chunks del doc con titulo ~311 ===')
        r = await conn.execute(text(
            "SELECT chunk_index, measure_code, article_ref, "
            "substring(content, 1, 80) AS preview "
            "FROM knowledge_chunks c "
            "JOIN knowledge_documents d ON d.id = c.document_id "
            "WHERE d.titulo ILIKE '%%311%%' "
            "ORDER BY chunk_index LIMIT 10"
        ))
        rows = list(r)
        if not rows:
            print('  (no hay chunks con titulo ~311)')
        else:
            for row in rows:
                print(f'  [{row[0]}] mc={row[1]} ar={row[2]} | {row[3]}...')

        print()
        print('=== Schema: columnas knowledge_chunks ===')
        r = await conn.execute(text(
            "SELECT column_name, data_type, is_generated "
            "FROM information_schema.columns "
            "WHERE table_name = 'knowledge_chunks' "
            "ORDER BY ordinal_position"
        ))
        for row in r:
            gen = ' [GENERATED]' if row[2] == 'ALWAYS' else ''
            print(f'  {row[0]:25s} {row[1]:20s}{gen}')

        print()
        print('=== Alembic head ===')
        r = await conn.execute(text('SELECT version_num FROM alembic_version'))
        print(f'  {r.scalar()}')

    await engine.dispose()


if __name__ == '__main__':
    asyncio.run(audit())
