"""Smoke A24 cross_compliance · 3 perfiles cliente sintetico · sub-lote 1.B.6.1 v3.

Ejecuta detect_obligations + build_summary contra 3 ComplianceContext
representativos sin tocar DB (puro · ms-level fast).

Tabla output 8 columnas por norma + TOTAL + tiempo:
  perfil | RGPD | LOPDGDD | NIS2 | DORA | PSD2 | AI Act | ISO 27001 | ENI | TOTAL | t(ms)

Perfiles (alineados con tests E2E):
  P1 · fintech_alto_trigger    · CTX-A · RGPD+NIS2+DORA+PSD2+ISO27001
  P2 · proveedor_tic_ai        · CTX-B · RGPD+NIS2+AI Act+ISO27001  · NO DORA/PSD2
  P3 · pyme_basica_rgpd        · CTX-C · RGPD+ISO27001              · solo RGPD sectorial

Usage:
    PYTHONPATH=. .venv/bin/python backend/scripts/smoke/smoke_a24_obligations.py
"""
from __future__ import annotations

import time
from collections import Counter
from typing import NamedTuple

from backend.app.motors.m21_diagnosis.cross_compliance_service import (
    ComplianceContext,
    build_summary,
    detect_obligations,
)


# Normativas que pueden generar las 7 funciones (orden tabla).
NORMA_COLUMNS = ["RGPD", "LOPDGDD", "NIS2", "DORA", "PSD2", "AI Act", "ISO 27001", "ENI"]


class Profile(NamedTuple):
    name: str
    ctx: ComplianceContext


PROFILES: list[Profile] = [
    Profile(
        name="fintech_alto_trigger",
        ctx=ComplianceContext(
            sector="fintech",
            empleados=50,
            maneja_datos_personales=True,
            es_sector_importante_nis2=True,
            es_entidad_financiera_ue=True,
            procesa_pagos=True,
        ),
    ),
    Profile(
        name="proveedor_tic_ai",
        ctx=ComplianceContext(
            sector="proveedor-tic",
            empleados=300,
            maneja_datos_personales=True,
            es_sector_esencial_nis2=True,
            tiene_sistemas_ia_alto_riesgo=True,
        ),
    ),
    Profile(
        name="pyme_basica_rgpd",
        ctx=ComplianceContext(
            sector="general",
            empleados=300,
            maneja_datos_personales=True,
        ),
    ),
]


def _fmt_row(name: str, counts: dict[str, int], total: int, ms: float) -> str:
    cols = [f"{counts.get(n, 0):>4}" for n in NORMA_COLUMNS]
    return (
        f"{name:<25} | {' | '.join(cols)} | {total:>5} | {ms:>6.2f}"
    )


def _header() -> tuple[str, str]:
    cols = [f"{n:>4}" if len(n) <= 4 else f"{n:>{len(n)}}" for n in NORMA_COLUMNS]
    head = f"{'perfil':<25} | {' | '.join(cols)} | {'TOTAL':>5} | {'t(ms)':>6}"
    sep = "-" * len(head)
    return head, sep


def main() -> int:
    head, sep = _header()
    print(f"\n{head}")
    print(sep)

    summary_rows: list[dict] = []

    for p in PROFILES:
        t0 = time.monotonic()
        obs = detect_obligations(p.ctx)
        summary = build_summary(p.ctx, obs)  # ejercita helper agregador
        ms = (time.monotonic() - t0) * 1000

        counts = Counter(o.norma for o in obs)
        total = len(obs)
        print(_fmt_row(p.name, counts, total, ms))
        summary_rows.append({
            "perfil": p.name,
            "counts": dict(counts),
            "total": total,
            "ms": round(ms, 2),
            "recomendacion": summary["recomendacion"],
        })

    print(sep)
    print(f"\n=== SMOKE A24 · {len(PROFILES)} perfiles procesados ===")
    print("  hardcoded A24 max global: 15 rows (5 RGPD + 3 NIS2 + 3 DORA + 1 cada PSD2/AI/ISO/ENI)")
    print("  zero side effects · sin DB · puro detect + build_summary")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
