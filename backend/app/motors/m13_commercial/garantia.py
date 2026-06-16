"""Resolución robusta de la garantía comercial de una propuesta (WAVE C1).

Histórico (§4.4/370): la garantía se guardaba SÓLO como una línea de texto libre
dentro de ``proposals.notas_marcos`` ("...\\n\\nGarantia: <texto>") y los
consumidores (m14 contratos, A20 negociación) la re-parseaban con
``split("Garantia:")``. Eso acopla el contrato a un marcador editable que un
admin podía borrar, rompiendo silenciosamente la propagación al contrato C-001.

Fuente preferente ahora: la clave ESTRUCTURADA ``importe_desglose["garantia"]``
(JSONB · sin migración). El split() del texto libre se mantiene SÓLO como
fallback legacy para propuestas creadas antes de este cambio.
"""
from __future__ import annotations

from typing import Any, Mapping, Optional

_MARKER = "Garantia:"


def extract_garantia(
    importe_desglose: Optional[Mapping[str, Any]],
    notas_marcos: Optional[str],
) -> str:
    """Devuelve el texto de la garantía de forma robusta.

    Orden de resolución:
      1) ``importe_desglose["garantia"]`` (fuente estructurada · preferente).
      2) Fallback legacy: la cola tras el marcador ``Garantia:`` en
         ``notas_marcos`` (filas antiguas anteriores a la columna estructurada).
      3) Cadena vacía si no hay ninguna de las dos.
    """
    desglose = importe_desglose or {}
    structured = desglose.get("garantia")
    if isinstance(structured, str) and structured.strip():
        return structured.strip()

    notas = notas_marcos or ""
    if _MARKER in notas:
        return notas.split(_MARKER, 1)[1].strip()

    return ""
