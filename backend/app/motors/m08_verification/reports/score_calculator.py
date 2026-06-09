"""M8 v5.1 - Security score (spec §7.3).

Formula:

    score = 100
            - 15 * n_critical_open
            -  8 * n_high_open
            -  3 * n_medium_open
            -  1 * n_low_open

Se calcula solo sobre findings con status='open' (o 'needs_review')
y classification in {confirmed, probable} — needs_review no penaliza.

``min 0``, ``max 100``.

Devuelve un ``Score`` con todos los desgloses para persistir en
``verification_runs.security_score`` y mostrar en el informe.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


PENALTY = {
    "critical": 15,
    "high": 8,
    "medium": 3,
    "low": 1,
    "info": 0,
}


@dataclass(frozen=True)
class Score:
    score: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    info_count: int
    total_penalty: int
    level: str

    def to_dict(self) -> dict:
        return {
            "score": self.score,
            "level": self.level,
            "critical": self.critical_count,
            "high": self.high_count,
            "medium": self.medium_count,
            "low": self.low_count,
            "info": self.info_count,
            "total_penalty": self.total_penalty,
        }


def _score_level(score: int) -> str:
    if score >= 90:
        return "excelente"
    if score >= 75:
        return "aceptable"
    if score >= 50:
        return "mejorable"
    if score >= 25:
        return "critico"
    return "bloqueante"


def _counts_in_scope(findings: Iterable) -> dict[str, int]:
    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
    for f in findings:
        if isinstance(f, dict):
            status = f.get("status") or "open"
            cls = (f.get("zfp_gate5_classification") or f.get("classification") or "confirmed")
            sev = (f.get("severity") or "info").lower()
        else:
            status = getattr(f, "status", "open") or "open"
            cls = (
                getattr(f, "zfp_gate5_classification", None)
                or getattr(f, "classification", None)
                or "confirmed"
            )
            sev = (getattr(f, "severity", "info") or "info").lower()
        if status not in ("open", "needs_review"):
            continue
        if cls not in ("confirmed", "probable"):
            continue
        if sev in counts:
            counts[sev] += 1
    return counts


def calculate_score(findings: Iterable) -> Score:
    """Calcula el score sobre una coleccion de findings."""
    c = _counts_in_scope(findings)
    total_penalty = (
        c["critical"] * PENALTY["critical"]
        + c["high"] * PENALTY["high"]
        + c["medium"] * PENALTY["medium"]
        + c["low"] * PENALTY["low"]
    )
    score = max(0, 100 - total_penalty)
    return Score(
        score=score,
        critical_count=c["critical"],
        high_count=c["high"],
        medium_count=c["medium"],
        low_count=c["low"],
        info_count=c["info"],
        total_penalty=total_penalty,
        level=_score_level(score),
    )


def persist_score_to_run(run, score: Score) -> None:
    """Copia el score a las columnas del VerificationRun."""
    run.security_score = score.score
    run.critical_count = score.critical_count
    run.high_count = score.high_count
    run.medium_count = score.medium_count
    run.low_count = score.low_count
    run.info_count = score.info_count
