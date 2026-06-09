"""Política copias 3-2-1 · SAN-C MB-11.5.

CCN-STIC + buenas prácticas backup:
- 3 copias mínimas (1 producción + 2 backup)
- 2 medios distintos (disk + tape/cloud)
- 1 copia offsite (otra región/ubicación)

Servicio stateless: evalúa compliance contra payload explícito o lista
de backups con metadata. NO requiere column nueva en backup_jobs;
el caller (UI o tests) provee la lista de backup configs estructurada.

Para integración con M26 BackupJob existente, los callers pueden mapear
backup_jobs → BackupCopy via interpretación heurística de
``location`` (cloud:// → cloud, /mnt/disk/ → disk, etc.) en el endpoint
adapter. Decisión: motor 3-2-1 mantiene contrato puro stateless para
test + reuse + clear semantics.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BackupCopy:
    """Representación copia backup para evaluación 3-2-1."""

    label: str
    media_type: str  # disk | tape | cloud | object_storage
    is_offsite: bool


@dataclass(frozen=True)
class Compliance321Result:
    """Resultado evaluación compliance 3-2-1."""

    compliant: bool
    copies_count: int
    media_types: list[str]
    offsite_count: int
    gaps: list[str]


def evaluate_3_2_1(copies: list[BackupCopy]) -> Compliance321Result:
    """Evalúa compliance regla 3-2-1.

    Args:
        copies: Lista BackupCopy (mínimo 3 para compliance).

    Returns:
        Compliance321Result con flag boolean + métricas + gaps texto.
    """
    copies_count = len(copies)
    media_types = sorted({c.media_type for c in copies})
    offsite_count = sum(1 for c in copies if c.is_offsite)

    gaps: list[str] = []
    if copies_count < 3:
        gaps.append(
            f"Faltan copias: hay {copies_count}, mínimo 3 (1 producción + 2 backup)"
        )
    if len(media_types) < 2:
        gaps.append(
            f"Faltan medios distintos: hay {len(media_types)}, mínimo 2 "
            f"(p.ej. disk + cloud)"
        )
    if offsite_count < 1:
        gaps.append("Falta copia offsite (otra región/ubicación física)")

    compliant = (
        copies_count >= 3
        and len(media_types) >= 2
        and offsite_count >= 1
    )

    return Compliance321Result(
        compliant=compliant,
        copies_count=copies_count,
        media_types=media_types,
        offsite_count=offsite_count,
        gaps=gaps,
    )
