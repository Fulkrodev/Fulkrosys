"""Motor 6 -- Document Factory -- enumerations.

Centralized enums to avoid magic strings scattered across service/api/tests.
"""
from enum import Enum


class TemplateCategoria(str, Enum):
    POLITICA = "politica"
    PROCEDIMIENTO = "procedimiento"
    COMERCIAL = "comercial"
    ENTREGABLE = "entregable"
    APENDICE_F = "apendice_f"
    INSTRUCCION_TECNICA = "instruccion_tecnica"
    REGISTRO = "registro"


class DocumentEstado(str, Enum):
    GENERADO = "generado"
    FIRMADO = "firmado"
    ENTREGADO = "entregado"
    OBSOLETO = "obsoleto"


class AplicaDesde(str, Enum):
    BASICA = "basica"
    MEDIA = "media"
    ALTA = "alta"
