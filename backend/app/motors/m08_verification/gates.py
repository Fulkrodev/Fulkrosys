"""5 gates con niveles de verificación (doc §5).

Capa fina sobre el ZFP engine existente (`zfp_engine.py`) que añade la
semántica del doc v2.0 sin reescribir lo vivo:

  Gate 1 Detección · Gate 2 Dedup/correlación · Gate 3 Umbral de confianza ·
  Gate 4 Verificación (pasivo / activo-seguro / explotación) · Gate 5 Triage.

Dos invariantes del doc:
- **Gate 3 nunca descarta**: confidence < θ → va al *anexo técnico* (visibilidad
  degradada), NO se borra. Solo Gate 2 (patrón FP determinista) rechaza.
- **Zero-FP vive en Gate 4**: solo `active_safe`/`exploitation` son verificación
  que sostiene el claim Zero-False-Positive. `passive`/`unverified` van al
  informe con su nivel etiquetado (honest boundaries §0).
"""
from __future__ import annotations

from typing import Any

# Umbral para informe ejecutivo vs anexo técnico (doc §5 Gate 3)
CONFIDENCE_THRESHOLD_REPORT = 0.70

VERIFICATION_UNVERIFIED = "unverified"
VERIFICATION_PASSIVE = "passive"
VERIFICATION_ACTIVE_SAFE = "active_safe"
VERIFICATION_EXPLOITATION = "exploitation"

# Solo estos niveles sostienen el claim Zero-False-Positive (doc §5 Gate 4)
ZERO_FP_LEVELS = frozenset({VERIFICATION_ACTIVE_SAFE, VERIFICATION_EXPLOITATION})

# Visibilidad del hallazgo (doc §5 Gate 3)
VISIBILITY_EXECUTIVE = "executive_report"   # confirmed/probable → informe ejecutivo
VISIBILITY_ANNEX = "technical_annex"        # needs_review → anexo técnico
VISIBILITY_REJECTED = "rejected"            # gate2 FP determinista → solo audit log


def classify_visibility(classification: str | None, confidence: float | None) -> str:
    """Gate 3 · decide visibilidad sin descartar (salvo rechazo determinista).

    `classification` es zfp_gate5_classification (confirmed/probable/needs_review/rejected).
    """
    if classification == "rejected":
        return VISIBILITY_REJECTED
    if classification in ("confirmed", "probable"):
        return VISIBILITY_EXECUTIVE
    # needs_review o confidence < θ → anexo técnico (NUNCA descartado)
    if confidence is not None and confidence >= CONFIDENCE_THRESHOLD_REPORT:
        return VISIBILITY_EXECUTIVE
    return VISIBILITY_ANNEX


def derive_verification_level(
    *,
    gate4_retest: str | None,
    cross_tool_count: int = 0,
    has_known_cve: bool = False,
    exploitation_authorized: bool = False,
    exploited: bool = False,
) -> str:
    """Gate 4 · deriva el nivel de verificación (doc §5).

    - exploitation: prueba intrusiva ejecutada Y autorizada (típicamente Gate 2
      humano / pentester). Sostiene Zero-FP al máximo.
    - active_safe: retest activo no destructivo confirmó (gate4_retest=confirmed).
      Sostiene Zero-FP.
    - passive: corroborado por ≥1 fuente (banner/versión/CVE) sin retest activo.
      NO sostiene Zero-FP (puede ser version-match).
    - unverified: sin corroboración.
    """
    if exploited and exploitation_authorized:
        return VERIFICATION_EXPLOITATION
    if gate4_retest == "confirmed":
        return VERIFICATION_ACTIVE_SAFE
    if cross_tool_count >= 1 or has_known_cve:
        return VERIFICATION_PASSIVE
    return VERIFICATION_UNVERIFIED


def is_zero_fp_verified(verification_level: str | None) -> bool:
    """True solo si el nivel sostiene el claim Zero-False-Positive (doc §5)."""
    return verification_level in ZERO_FP_LEVELS


def verification_level_for_zfp_finding(zf: Any) -> str:
    """Deriva verification_level desde un ZfpFinding (post-pipeline)."""
    return derive_verification_level(
        gate4_retest=getattr(zf, "zfp_gate4_retest", None),
        cross_tool_count=int(getattr(zf, "zfp_gate3_cross_tool", 0) or 0),
        has_known_cve=bool(getattr(zf, "has_known_cve", False)),
        # explotación solo la fija el flujo humano/pentester explícitamente
        exploitation_authorized=bool(getattr(zf, "exploitation_authorized", False)),
        exploited=bool(getattr(zf, "exploited", False)),
    )
