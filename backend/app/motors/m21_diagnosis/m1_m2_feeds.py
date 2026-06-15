"""M21 Paso 5 — Feeds a M1 (Categorizacion) y M2 (MAGERIT).

M21 genera hints deterministas para no dejar a M1 y M2 vacios tras el
diagnostico. El consultor revisa y ajusta, pero el arranque viene con
datos plausibles.

- ``suggest_category(project_id)`` → categoria ENS preliminar (BASICA/MEDIA/ALTA)
- ``suggest_magerit_assets(project_id)`` → assets base derivados de los
  procesos ya descubiertos por M21
"""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.diagnosis import BusinessProcess, LegalObligation


# ════════════════════════════════════════════════════════════════════
# M1 — sugerencia de categoria ENS
# ════════════════════════════════════════════════════════════════════

def _score_from_processes(processes: list[BusinessProcess]) -> int:
    """Score de impacto 0-10 derivado de criticidad de procesos."""
    if not processes:
        return 0
    weights = {"alta": 10, "media": 5, "baja": 2}
    total = sum(weights.get((p.criticidad or "media").lower(), 5) for p in processes)
    # Normalizar a 0-10: promedio * factor con cap
    avg = total / len(processes)
    return min(10, int(round(avg)))


def _score_from_obligations(obligations: list[LegalObligation]) -> int:
    """Score de sensibilidad normativa 0-10."""
    if not obligations:
        return 0
    # Peso por norma (claves en MAYUSCULAS para casar con la normalizacion).
    weight = {
        "RGPD": 3,      # base
        "NIS2": 6,      # sector critico
        "DORA": 7,      # entidad financiera
        "AI ACT": 5,    # IA alto riesgo
        "LOPDGDD": 4,   # datos sensibles
        "ENI": 4,       # admin publica
    }
    score = 0
    seen: set[str] = set()
    for o in obligations:
        raw = (o.normativa or "").strip().upper()
        # Casar por prefijo conocido (p.ej. "AI ACT ..." o "RGPD (UE) 2016/679")
        # en vez de split()[0], que rompia las normas multi-palabra como "AI Act"
        # (se quedaba en "AI" y caia al peso por defecto 1 en vez de 5).
        key = next((k for k in weight if raw.startswith(k)), raw.split()[0] if raw else "")
        if key in seen:
            continue
        seen.add(key)
        score += weight.get(key, 1)
    return min(10, score)


async def suggest_category(
    db: AsyncSession, project_id: uuid.UUID,
) -> dict[str, Any]:
    """Propone categoria ENS preliminar.

    Regla simple:
    - max(score_procesos, score_obligaciones) ≥ 8 → ALTA
    - ≥ 5 → MEDIA
    - < 5 → BASICA

    Output incluye justificacion y los dos scores para auditar el
    razonamiento (clave para que Marcos valide con el cliente).
    """
    proc_stmt = select(BusinessProcess).where(
        BusinessProcess.project_id == project_id,
        BusinessProcess.deleted_at.is_(None),
    )
    processes = list((await db.execute(proc_stmt)).scalars().all())

    obl_stmt = select(LegalObligation).where(
        LegalObligation.project_id == project_id,
        LegalObligation.deleted_at.is_(None),
    )
    obligations = list((await db.execute(obl_stmt)).scalars().all())

    s_proc = _score_from_processes(processes)
    s_obl = _score_from_obligations(obligations)
    top = max(s_proc, s_obl)
    if top >= 8:
        cat = "ALTA"
    elif top >= 5:
        cat = "MEDIA"
    else:
        cat = "BASICA"

    return {
        "categoria_sugerida": cat,
        "confianza": "alta" if top >= 8 or top < 3 else "media",
        "score_procesos": s_proc,
        "score_obligaciones": s_obl,
        "total_procesos": len(processes),
        "total_obligaciones": len(obligations),
        "justificacion": (
            f"Procesos criticos detectados ({sum(1 for p in processes if (p.criticidad or '').lower() == 'alta')}) "
            f"y {len(obligations)} obligaciones normativas aplicables "
            f"sugieren categoria {cat}."
        ),
    }


# ════════════════════════════════════════════════════════════════════
# M2 — sugerencia de assets MAGERIT
# ════════════════════════════════════════════════════════════════════

# Mapeo procesos → taxonomia MAGERIT
_ASSET_DERIVATIONS = [
    # Cada proceso genera al menos un asset de tipo Servicio (S)
    {"asset_type_code": "S", "source": "process", "prefix": "Servicio: "},
    # Procesos con sistemas → assets SW/HW derivados
]


async def suggest_magerit_assets(
    db: AsyncSession, project_id: uuid.UUID,
) -> list[dict[str, Any]]:
    """Deriva assets base MAGERIT desde procesos de negocio.

    Cada proceso se convierte en:
    - 1 asset Servicio (S) con el nombre del proceso
    - N assets Software/Hardware por cada sistema mencionado
    - 1 asset Informacion (D) por proceso (dato procesado)

    Los valores DICAT iniciales se estiman desde la criticidad del
    proceso y los flags de cross_compliance (datos sensibles → valor
    confidencialidad alto).
    """
    proc_stmt = select(BusinessProcess).where(
        BusinessProcess.project_id == project_id,
        BusinessProcess.deleted_at.is_(None),
    )
    processes = list((await db.execute(proc_stmt)).scalars().all())

    obl_stmt = select(LegalObligation).where(
        LegalObligation.project_id == project_id,
        LegalObligation.deleted_at.is_(None),
    )
    obligations = list((await db.execute(obl_stmt)).scalars().all())
    sensitivos = any(
        ("LOPDGDD" in (o.normativa or "") or "salud" in (o.alcance or "").lower())
        for o in obligations
    )

    suggested: list[dict[str, Any]] = []
    for p in processes:
        crit = (p.criticidad or "media").lower()
        base_vals = {
            "alta": {"D": 7, "I": 6, "C": 6, "A": 6, "T": 5},
            "media": {"D": 5, "I": 5, "C": 4, "A": 4, "T": 4},
            "baja": {"D": 3, "I": 3, "C": 2, "A": 2, "T": 2},
        }[crit]
        if sensitivos:
            base_vals["C"] = max(base_vals["C"], 8)

        # 1) Asset Servicio
        suggested.append({
            "code": f"SRV-{p.nombre[:30]}",
            "name": f"Servicio: {p.nombre}",
            "asset_type_code": "S",
            "owner": p.propietario,
            "value_d": base_vals["D"], "value_i": base_vals["I"],
            "value_c": base_vals["C"], "value_a": base_vals["A"],
            "value_t": base_vals["T"],
            "derived_from_process_id": str(p.id),
        })

        # 2) Assets SW/HW por sistema
        sistemas = (p.sistemas_involucrados or {}).get("sistemas", [])
        for s in sistemas:
            suggested.append({
                "code": f"SW-{s[:30]}",
                "name": f"Sistema software: {s}",
                "asset_type_code": "SW",
                "owner": p.propietario,
                "value_d": base_vals["D"] - 1, "value_i": base_vals["I"] - 1,
                "value_c": base_vals["C"] - 1, "value_a": base_vals["A"] - 1,
                "value_t": base_vals["T"] - 1,
                "derived_from_process_id": str(p.id),
            })

        # 3) Asset Informacion (D)
        suggested.append({
            "code": f"DATA-{p.nombre[:25]}",
            "name": f"Datos procesados por {p.nombre}",
            "asset_type_code": "D",
            "owner": p.propietario,
            "value_d": base_vals["D"], "value_i": base_vals["I"],
            "value_c": max(base_vals["C"], 7) if sensitivos else base_vals["C"],
            "value_a": base_vals["A"],
            "value_t": base_vals["T"],
            "derived_from_process_id": str(p.id),
        })

    # Dedupe por code
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for a in suggested:
        if a["code"] in seen:
            continue
        seen.add(a["code"])
        unique.append(a)
    return unique


__all__ = ["suggest_category", "suggest_magerit_assets"]
