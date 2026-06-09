"""Motor 3 — DdA Engine Enums."""
from enum import Enum


class Aplicabilidad(str, Enum):
    """Si una medida aplica al sistema segun RD 311/2022 Anexo II."""
    APLICA = "aplica"
    APLICA_CON_REFUERZOS = "aplica_con_refuerzos"
    NO_APLICA = "no_aplica"


class EstadoImplementacion(str, Enum):
    """Estado de implementacion de cada medida segun CCN-STIC 803."""
    NO_VALORADO = "no_valorado"
    NO_IMPLANTADA = "no_implantada"
    PARCIAL = "parcial"
    IMPLANTADA = "implantada"
    NO_APLICA = "no_aplica"


class CategoriaSistema(str, Enum):
    """Categorias ENS segun RD 311/2022 Anexo I."""
    BASICA = "BASICA"
    MEDIA = "MEDIA"
    ALTA = "ALTA"
