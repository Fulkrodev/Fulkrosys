"""Motor 14 - Contracts Pydantic schemas.

Define ScanWindow canónico consumido por Contract.scan_window y por
M08 verification scope_deriver para wiring contractual de la ventana
de escaneo nocturno (TODO-M8-G3 cerrado).
"""
from __future__ import annotations

import re
from datetime import date
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, Field, field_validator


WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
HHMM_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")

WeekdayLiteral = Literal["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


class ScanWindow(BaseModel):
    """Maintenance/scan window configuration per contract.

    Format canónico SAN-B.MB-3.bis.3 (cierre TODO-M8-G3).
    Cross-midnight: horario_inicio > horario_fin → window cruza medianoche
    (ej. 22:00-06:00 = de 22h a las 6h del día siguiente).
    """

    horario_inicio: str = Field(
        ..., description="HH:MM 24h format (00:00-23:59)",
    )
    horario_fin: str = Field(
        ..., description="HH:MM 24h format · si > inicio cruza medianoche",
    )
    tz: str = Field(
        default="Europe/Madrid",
        description="IANA timezone name",
    )
    dias_ok: list[WeekdayLiteral] = Field(
        default_factory=lambda: list(WEEKDAYS),
        description="Días de la semana en que se permite scan",
    )
    dias_bloqueados: list[WeekdayLiteral] = Field(
        default_factory=list,
        description="Días explícitamente excluidos (overrides dias_ok)",
    )
    fechas_bloqueadas: list[str] = Field(
        default_factory=list,
        description="Fechas ISO YYYY-MM-DD bloqueadas (festivos cliente)",
    )

    @field_validator("horario_inicio", "horario_fin")
    @classmethod
    def _validate_hhmm(cls, v: str) -> str:
        if not HHMM_RE.match(v):
            raise ValueError(
                f"horario debe formato HH:MM 24h (00:00-23:59), recibido: {v!r}"
            )
        return v

    @field_validator("tz")
    @classmethod
    def _validate_tz(cls, v: str) -> str:
        try:
            ZoneInfo(v)
        except ZoneInfoNotFoundError:
            raise ValueError(f"tz IANA no reconocido: {v!r}")
        return v

    @field_validator("fechas_bloqueadas")
    @classmethod
    def _validate_fechas(cls, v: list[str]) -> list[str]:
        for f in v:
            try:
                date.fromisoformat(f)
            except (ValueError, TypeError):
                raise ValueError(
                    f"fecha ISO YYYY-MM-DD inválida: {f!r}"
                )
        return v


# Default fallback usado por scope_deriver cuando no hay Contract.scan_window
DEFAULT_SCAN_WINDOW: dict = ScanWindow(
    horario_inicio="22:00",
    horario_fin="06:00",
).model_dump()
