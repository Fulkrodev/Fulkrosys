#!/usr/bin/env python3
"""
Launch run productivo m10 ENS Radar · Path B1 cement Sub-atom N.

Robusto para 12-20h:
- nohup process · sobrevive cierre terminal
- Process independiente uvicorn · sobrevive uvicorn restart
- triggered_by/triggered_via preserve audit trail

Uso:
   nohup .venv/bin/python scripts/m10/launch_productivo_subatom_n.py \\
      > /tmp/run_productivo_$(date +%Y%m%d_%H%M).log 2>&1 &
   echo $! > /tmp/run_productivo.pid
"""
import asyncio
import sys
import os

REPO_ROOT = "/home/usuario/fulkro"
sys.path.insert(0, REPO_ROOT)
os.chdir(REPO_ROOT)

from backend.app.motors.m10_ens_radar.orchestrator.pipeline import PipelineV2
from backend.app.motors.m10_ens_radar.config import settings as radar_settings


async def main():
    print("=" * 70)
    print("LAUNCH RUN PRODUCTIVO m10 ENS Radar · Path B1")
    print("=" * 70)
    print(f"cost_limit_usd: {radar_settings.cost_limit_usd}")
    print(f"cost_limit_mode: {radar_settings.cost_limit_mode}")
    print(f"enabled_sources: {radar_settings.enabled_sources}")
    print(f"since_days: 60 (Path B1 cement)")
    print(f"triggered_by: marcosmata@fulkro.es")
    print(f"triggered_via: script_subatom_n")
    print("=" * 70)

    pipeline = PipelineV2(
        since_days=60,
        skip_ingest=False,
        skip_ens=False,
        enable_ccn_scrape=False,
        dry_run=False,
        triggered_by="marcosmata@fulkro.es",
        triggered_via="script_subatom_n",
    )

    print(f"Pipeline initialized · running execute()...")
    print(f"ETA: 12-20h continuous · background")
    print("=" * 70)

    try:
        result = await pipeline.execute()
        print(f"Pipeline DONE · result: {result}")
    except Exception as e:
        print(f"Pipeline ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
