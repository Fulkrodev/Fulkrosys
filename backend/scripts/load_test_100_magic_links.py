"""Load test 100 magic links concurrentes — Sesion 8 Paso 8.1.

Mide escalabilidad del pipeline magic link + firma Ed25519 + consumo.
Ejecuta in-process (sin uvicorn real) para estabilidad + facil CI.

Metricas reportadas:
- Total wall-clock time
- min/p50/p95/p99/max latency per link
- Throughput (links/sec)
- Error rate
- Memoria pico (tracemalloc)

Target aceptable primer cliente:
- 100 links en <60s (>= 1.6 links/sec)
- p95 <2.5s
- 0 errores

Uso:
    python backend/scripts/load_test_100_magic_links.py [--count 100]
"""
from __future__ import annotations

import argparse
import asyncio
import os
import statistics
import sys
import time
import tracemalloc
import uuid
from pathlib import Path
from typing import Any

os.environ.setdefault("FULKRO_SKIP_WORKFLOW_GATES", "1")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine


async def _seed_project(conn) -> tuple[str, str]:
    """Crea client + project para asociar magic links a algo real."""
    await conn.execute(sa_text("SET LOCAL ROLE fulkro"))
    cid = uuid.uuid4()
    pid = uuid.uuid4()
    cif = f"B{uuid.uuid4().hex[:8].upper()}"
    await conn.execute(sa_text(
        "INSERT INTO clients (id, nombre, cif, created_at) "
        "VALUES (:id, 'LoadTest', :cif, now())"
    ), {"id": str(cid), "cif": cif})
    await conn.execute(sa_text(
        "INSERT INTO projects (id, client_id, nombre, created_at) "
        "VALUES (:id, :cid, 'LoadTest', now())"
    ), {"id": str(pid), "cid": str(cid)})
    return str(cid), str(pid)


async def _generate_and_consume_one(
    engine, client_id: uuid.UUID, project_id: uuid.UUID,
) -> dict[str, Any]:
    """Genera 1 magic link, lo firma, lo consume, verifica. Mide tiempo."""
    from backend.app.database import set_tenant_context
    from backend.app.motors.m12_magic_link.purposes import MagicLinkPurpose
    from backend.app.motors.m12_magic_link.schemas import (
        MagicLinkGenerateRequest, MagicLinkConsumeRequest,
    )
    from backend.app.motors.m12_magic_link.service import MagicLinkService

    start = time.perf_counter()
    ok = True
    err = None
    try:
        async with engine.connect() as conn:
            trans = await conn.begin()
            session = AsyncSession(bind=conn, expire_on_commit=False)
            try:
                await set_tenant_context(
                    session, client_id=client_id, project_id=project_id,
                )
                svc = MagicLinkService(session)
                gen_req = MagicLinkGenerateRequest(
                    project_id=project_id,
                    purpose=MagicLinkPurpose.OFERTA_RETAINER,
                    recipient_email=f"load-{uuid.uuid4().hex[:6]}@test.es",
                )
                resp = await svc.generate_magic_link(
                    gen_req, base_url="http://load-test",
                )
                consume_req = MagicLinkConsumeRequest(
                    token=resp.token, otp=resp.otp,
                )
                _ = await svc.consume_magic_link(consume_req)
                await trans.commit()
            except Exception:
                await trans.rollback()
                raise
            finally:
                await session.close()
    except Exception as exc:
        ok = False
        err = f"{type(exc).__name__}: {str(exc)[:200]}"

    elapsed = time.perf_counter() - start
    return {"ok": ok, "elapsed": elapsed, "error": err}


async def main(count: int = 100) -> int:
    from backend.app.config import get_settings
    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=False)

    print("=" * 70)
    print(f"LOAD TEST 100 MAGIC LINKS — count={count}")
    print("=" * 70)

    tracemalloc.start()

    # Seed un project comun
    async with engine.begin() as conn:
        cid, pid = await _seed_project(conn)
    client_uuid = uuid.UUID(cid)
    project_uuid = uuid.UUID(pid)

    t0 = time.perf_counter()
    results = await asyncio.gather(*[
        _generate_and_consume_one(engine, client_uuid, project_uuid)
        for _ in range(count)
    ])
    total_elapsed = time.perf_counter() - t0

    current_mem, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    latencies = [r["elapsed"] for r in results]
    errors = [r for r in results if not r["ok"]]

    p50 = statistics.median(latencies)
    p95 = sorted(latencies)[int(0.95 * (len(latencies) - 1))]
    p99 = sorted(latencies)[int(0.99 * (len(latencies) - 1))]

    print(f"\nTotal elapsed: {total_elapsed:.2f}s")
    print(f"Throughput:   {count / total_elapsed:.2f} links/sec")
    print(f"Errors:       {len(errors)}/{count}")
    print(f"Latency min:  {min(latencies):.3f}s")
    print(f"Latency p50:  {p50:.3f}s")
    print(f"Latency p95:  {p95:.3f}s")
    print(f"Latency p99:  {p99:.3f}s")
    print(f"Latency max:  {max(latencies):.3f}s")
    print(f"Memory peak:  {peak_mem / 1024 / 1024:.1f} MB")

    # Cleanup
    async with engine.begin() as conn:
        await conn.execute(sa_text("SET LOCAL ROLE fulkro"))
        await conn.execute(sa_text(
            "DELETE FROM client_interactions WHERE magic_link_id IN "
            "(SELECT id FROM magic_links WHERE project_id = :pid)"
        ), {"pid": pid})
        await conn.execute(sa_text(
            "DELETE FROM magic_links WHERE project_id = :pid"
        ), {"pid": pid})
        await conn.execute(sa_text(
            "DELETE FROM projects WHERE id = :pid"
        ), {"pid": pid})
        await conn.execute(sa_text(
            "DELETE FROM clients WHERE id = :cid"
        ), {"cid": cid})

    await engine.dispose()

    print("\n" + "=" * 70)
    if len(errors) == 0 and total_elapsed < 60 and p95 < 2.5:
        print("LOAD TEST 100 MAGIC LINKS: ✅ PASS (target aceptable cumplido)")
        return 0
    print("LOAD TEST 100 MAGIC LINKS: ⚠️  FALLA target aceptable")
    print(f"  - errors: {len(errors)} (target 0)")
    print(f"  - total time: {total_elapsed:.2f}s (target <60s)")
    print(f"  - p95: {p95:.3f}s (target <2.5s)")
    return 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=100)
    args = ap.parse_args()
    sys.exit(asyncio.run(main(count=args.count)))
