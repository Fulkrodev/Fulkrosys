"""Enums del Motor 16 Adaptive Onboarding.

Sectores y roles tomados exactamente del spec v2.1 sec 5.1 Motor 16.
"""
from __future__ import annotations

from enum import Enum


class Sector(str, Enum):
    """10 sectores soportados (spec v2.1 sec 3.2.1)."""
    SERVICIOS_PROFESIONALES = "servicios_profesionales"
    FINTECH = "fintech"
    SANIDAD_PRIVADA = "sanidad_privada"
    INDUSTRIA = "industria"
    SAAS_TECH = "saas_tech"
    RETAIL_ECOMMERCE = "retail_ecommerce"
    ENERGIA = "energia"
    LOGISTICA = "logistica"
    EDUCACION_PRIVADA = "educacion_privada"
    GENERICO = "generico"
    # Batch B diagnóstico previo (additive): sector sintético para la plantilla
    # del cuestionario que el LEAD responde account-less ANTES de ser cliente.
    # NO es un sector real de onboarding in-portal · se filtra del catálogo admin
    # (api.get_catalog) para no aparecer en el dropdown de creación de sesión.
    PRECLIENTE = "precliente"
    # L-2 (FRENTE L) · perfil autónomo/microempresa (unipersonal · acumulación
    # de roles Art.11 RD 311/2022) · ortogonal a la categoría ENS · soporta los
    # 3 niveles · onboarding ligero (el sponsor cubre todos los roles).
    INDIVIDUAL = "individual"


class Role(str, Enum):
    """7 roles soportados (spec v2.1 sec 3.2.1)."""
    SPONSOR = "sponsor"
    TI_CTO = "ti_cto"
    LEGAL_DPO = "legal_dpo"
    RRHH = "rrhh"
    OPERACIONES = "operaciones"
    COMPRAS = "compras"
    USUARIO_FINAL = "usuario_final"


class SessionState(str, Enum):
    """Estados de una onboarding_session."""
    CREATED = "created"
    SENT = "sent"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class QuestionType(str, Enum):
    """Tipos de pregunta soportados."""
    SINGLE_SELECT = "single_select"
    MULTI_SELECT = "multi_select"
    TEXT = "text"
    LONG_TEXT = "long_text"
    NUMBER = "number"
    DATE = "date"
    BOOLEAN = "boolean"
    EMAIL = "email"
    URL = "url"
