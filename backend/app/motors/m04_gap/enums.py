"""Motor 4 -- Gap Analysis Engine -- enumerations.

Centralized enums to avoid magic strings scattered across service/api/tests.
"""
from enum import Enum


class GapSeverity(str, Enum):
    CRITICA = "critica"
    ALTA = "alta"
    MEDIA = "media"
    BAJA = "baja"
    INFORMATIVA = "informativa"


class GapStatus(str, Enum):
    ABIERTO = "abierto"
    EN_CURSO = "en_curso"
    CERRADO = "cerrado"
    DESCARTADO = "descartado"


class ControlState(str, Enum):
    """Maturity levels L0-L5 from CCN-STIC 804."""
    L0_INEXISTENTE = "L0"
    L1_INICIAL = "L1"
    L2_REPETIBLE = "L2"
    L3_DEFINIDO = "L3"
    L4_GESTIONADO = "L4"
    L5_OPTIMIZADO = "L5"


# Mapping severidad -> numeric (matches catalog severidad_scoring)
SEVERITY_SCORING: dict[GapSeverity, int] = {
    GapSeverity.CRITICA: 5,
    GapSeverity.ALTA: 4,
    GapSeverity.MEDIA: 3,
    GapSeverity.BAJA: 2,
    GapSeverity.INFORMATIVA: 1,
}

# Reverse: string -> numeric for catalog values
SEVERITY_SCORING_STR: dict[str, int] = {
    "critica": 5,
    "alta": 4,
    "media": 3,
    "baja": 2,
    "informativa": 1,
}

# Level ordering for gap detection (higher = more mature)
LEVEL_ORDER: dict[str, int] = {
    "L0": 0,
    "L1": 1,
    "L2": 2,
    "L3": 3,
    "L4": 4,
    "L5": 5,
}

# Category -> target level mapping (CCN-STIC 808)
CATEGORY_TARGET_LEVEL: dict[str, str] = {
    "BASICA": "L2",
    "MEDIA": "L3",
    "ALTA": "L4",
}

# #21 Ola 4 (2026-06-04) · mapping conformidad (SoA) → madurez CMM (CCN-STIC 804).
#
# Fuente ÚNICA persistida: dda_entries.estado_implementacion (la SoA · lo que
# declara el estado de cada medida · lo que ENAC mira). Madurez (L0-L5) y
# conformidad (estado) son lentes DISTINTAS (madurez ≠ conformidad · #6):
#  - Frontera L2↔L3 = DOCUMENTACIÓN: declarar 'implantada' en una SoA rigurosa ya
#    exige la justificación documental que distingue L3 (definido) de L2
#    (reproducible pero intuitivo) → 'implantada' arranca en L3 (criterio ENS
#    Marcos · CCN-STIC 804). L2/L5 quedan sin estado origen (correcto · L2 es el
#    umbral que cruzan parcial<L2<implantada; L5 = optimización fuera de la SoA).
#  - Frontera L3↔L4 = EVIDENCIA VIGENTE VERIFICADA: 'implantada' + semáforo de
#    evidencia VERDE → L4 (gestionado/medido). NO se mapea aquí porque requiere
#    el semáforo (#20) · se resuelve en el acople #20→#21 (analyze_project).
#
# None = excluida del CMM/gap (no_aplica).
# Claves = grafías REALES del enum EstadoImplementacion (masculino 'no_valorado';
# el FE envía 'no_valorada' femenino pero el backend lo rechaza 422 → NUNCA se
# persiste · diagnóstico audit Ola 4 · normalización FE diferida al cierre).
ESTADO_IMPL_TO_CMM: dict[str, str | None] = {
    "no_aplica": None,
    "no_valorado": "L0",
    "no_implantada": "L0",
    "parcial": "L1",
    "implantada": "L3",
}

# Etiquetas legibles de los niveles CMM (CCN-STIC 804) para UI / fila SoA.
CMM_LABELS: dict[str, str] = {
    "L0": "Inexistente",
    "L1": "Inicial",
    "L2": "Repetible",
    "L3": "Definido",
    "L4": "Gestionado",
    "L5": "Optimizado",
}
