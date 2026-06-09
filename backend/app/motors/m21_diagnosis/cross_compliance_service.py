"""M21 Paso 5 — Cross compliance (Agente 24).

Deteccion automatica de obligaciones legales/normativas aplicables al
proyecto segun:
- sector (privado sanidad, fintech, servicios, industria, educacion,
  administracion publica)
- tamano (empleados)
- datos sensibles manejados (salud, biometricos, financieros, menores)
- tipo de servicio (critico, esencial, importante, servicio pago,
  IA alto riesgo)

Genera filas en ``legal_obligations`` con trazabilidad:
- obligacion
- norma_origen (art. especifico)
- autoridad competente
- accion requerida
- deadline (None si open-ended)
- estado inicial = 'identificada'
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.diagnosis import LegalObligation


# ════════════════════════════════════════════════════════════════════
# Input de detecc ion
# ════════════════════════════════════════════════════════════════════

@dataclass
class ComplianceContext:
    sector: str                       # sanidad_privada, fintech, servicios_profesionales, industria, educacion_privada, administracion_publica, ...
    empleados: int = 50
    maneja_datos_personales: bool = True
    maneja_datos_sensibles: bool = False   # Art. 9 RGPD (salud, biometricos, religion...)
    maneja_datos_menores: bool = False
    es_sector_esencial_nis2: bool = False  # sanidad, energia, agua, transporte, banca, salud publica...
    es_sector_importante_nis2: bool = False
    es_entidad_financiera_ue: bool = False
    procesa_pagos: bool = False
    tiene_sistemas_ia_alto_riesgo: bool = False
    es_administracion_publica: bool = False


@dataclass
class Obligation:
    obligacion: str
    norma: str
    articulo: str
    autoridad: str
    accion_requerida: str
    deadline: str | None = None                # ISO date o descripcion
    condicion: str = ""
    measure_codes: list[str] = field(default_factory=list)


# ════════════════════════════════════════════════════════════════════
# Reglas por norma
# ════════════════════════════════════════════════════════════════════

def _rgpd_obligations(ctx: ComplianceContext) -> list[Obligation]:
    """RGPD + LOPDGDD aplica SIEMPRE si hay datos personales."""
    if not ctx.maneja_datos_personales:
        return []
    obs = [
        Obligation(
            obligacion="Registro de actividades de tratamiento",
            norma="RGPD", articulo="Art. 30 RGPD",
            autoridad="AEPD",
            accion_requerida=(
                "Mantener registro actualizado con finalidades, categorias "
                "de datos, tiempos de conservacion, transferencias."
            ),
            measure_codes=["mp.info.1", "op.exp.4"],
        ),
        Obligation(
            obligacion="Notificacion de brechas en 72h",
            norma="RGPD", articulo="Art. 33 RGPD",
            autoridad="AEPD",
            accion_requerida=(
                "Notificar a la AEPD en un plazo maximo de 72h desde el "
                "conocimiento, con alcance, medidas y contacto DPO."
            ),
            deadline="ongoing",
            measure_codes=["op.exp.7"],
        ),
    ]
    if ctx.empleados >= 250 or ctx.maneja_datos_sensibles:
        obs.append(Obligation(
            obligacion="Designar Delegado de Proteccion de Datos (DPO)",
            norma="RGPD", articulo="Art. 37 RGPD + LOPDGDD Art. 34",
            autoridad="AEPD",
            accion_requerida=(
                "Designar y comunicar a la AEPD un DPO independiente. "
                "Condicion: >=250 empleados o tratamiento sensible."
            ),
            condicion=f"empleados={ctx.empleados} o sensibles={ctx.maneja_datos_sensibles}",
            measure_codes=["org.1"],
        ))
    if ctx.maneja_datos_sensibles or ctx.tiene_sistemas_ia_alto_riesgo:
        obs.append(Obligation(
            obligacion="Evaluacion de Impacto en Proteccion de Datos (EIPD)",
            norma="RGPD", articulo="Art. 35 RGPD",
            autoridad="AEPD",
            accion_requerida=(
                "Realizar EIPD previa al tratamiento cuando suponga riesgo "
                "alto para derechos y libertades."
            ),
            condicion="datos sensibles o IA de alto riesgo",
            measure_codes=["op.pl.1", "mp.info.1"],
        ))
    if ctx.maneja_datos_menores:
        obs.append(Obligation(
            obligacion="Consentimiento parental para menores <14",
            norma="LOPDGDD", articulo="Art. 7 LOPDGDD",
            autoridad="AEPD",
            accion_requerida=(
                "Recabar consentimiento de titulares de patria potestad en "
                "tratamientos de datos de menores de 14 anos."
            ),
            measure_codes=["mp.info.2"],
        ))
    return obs


def _nis2_obligations(ctx: ComplianceContext) -> list[Obligation]:
    """NIS2 aplica a entidades esenciales e importantes."""
    if not (ctx.es_sector_esencial_nis2 or ctx.es_sector_importante_nis2):
        return []
    tier = "esencial" if ctx.es_sector_esencial_nis2 else "importante"
    return [
        Obligation(
            obligacion=f"Registro como entidad {tier} NIS2",
            norma="NIS2",
            articulo="Art. 3 Directiva (UE) 2022/2555",
            autoridad="INCIBE / CCN-CERT",
            accion_requerida=(
                f"Darse de alta como entidad {tier} y aportar punto de contacto"
                " unico."
            ),
            deadline="2025-10-17",
            measure_codes=["org.1", "op.exp.4"],
        ),
        Obligation(
            obligacion="Notificacion de incidentes significativos en 24h",
            norma="NIS2", articulo="Art. 23",
            autoridad="INCIBE-CERT",
            accion_requerida=(
                "Notificar al CSIRT nacional incidentes significativos "
                "(24h alerta temprana + 72h informe + 1 mes informe final)."
            ),
            measure_codes=["op.exp.7"],
        ),
        Obligation(
            obligacion="Formacion y responsabilidad de direccion",
            norma="NIS2", articulo="Art. 20",
            autoridad="INCIBE",
            accion_requerida=(
                "Organo de direccion aprueba y supervisa medidas de "
                "ciberseguridad; recibe formacion especifica."
            ),
            measure_codes=["mp.per.1"],
        ),
    ]


def _dora_obligations(ctx: ComplianceContext) -> list[Obligation]:
    """DORA aplica a entidades financieras UE desde 17/01/2025."""
    if not ctx.es_entidad_financiera_ue:
        return []
    return [
        Obligation(
            obligacion="Registro de incidentes ICT y notificacion DORA",
            norma="DORA",
            articulo="Art. 19 Reg. (UE) 2022/2554",
            autoridad="Banco de Espana / CNMV",
            accion_requerida=(
                "Clasificar, documentar y notificar a autoridad competente "
                "incidentes ICT graves segun plazos DORA."
            ),
            deadline="2025-01-17",
            measure_codes=["op.exp.7"],
        ),
        Obligation(
            obligacion="Pruebas de resiliencia operativa digital",
            norma="DORA", articulo="Art. 24-27",
            autoridad="Banco de Espana",
            accion_requerida=(
                "Programa de pruebas: escaneos, pentests, amenazas (TLPT) "
                "con ciclos determinados por tipo de entidad."
            ),
            measure_codes=["op.exp.5", "mp.com.2"],
        ),
        Obligation(
            obligacion="Registro de proveedores TIC criticos",
            norma="DORA", articulo="Art. 28",
            autoridad="Banco de Espana",
            accion_requerida=(
                "Mantener registro de terceros TIC, due diligence, contratos "
                "con clausulas especificas DORA, salida planificada."
            ),
            measure_codes=["op.ext.1", "op.ext.4"],
        ),
    ]


def _psd2_obligations(ctx: ComplianceContext) -> list[Obligation]:
    if not ctx.procesa_pagos:
        return []
    return [
        Obligation(
            obligacion="Autenticacion Reforzada (SCA)",
            norma="PSD2",
            articulo="Art. 97 Directiva (UE) 2015/2366 + RTS SCA",
            autoridad="Banco de Espana",
            accion_requerida=(
                "Aplicar SCA (dos factores independientes) en pagos "
                "remotos, con excepciones reguladas."
            ),
            measure_codes=["op.acc.5"],
        ),
    ]


def _ai_act_obligations(ctx: ComplianceContext) -> list[Obligation]:
    if not ctx.tiene_sistemas_ia_alto_riesgo:
        return []
    return [
        Obligation(
            obligacion="Conformidad AI Act para sistemas de alto riesgo",
            norma="AI Act",
            articulo="Art. 9-15 Reg. (UE) 2024/1689",
            autoridad="AESIA (Espana)",
            accion_requerida=(
                "Sistema de gestion de riesgos, datos de entrenamiento, "
                "registro, transparencia, supervision humana, robustez "
                "y ciberseguridad. Declaracion UE + marcado CE."
            ),
            deadline="2027-08-02",
            measure_codes=["op.pl.1", "mp.sw.1"],
        ),
    ]


def _iso27001_opportunity(ctx: ComplianceContext) -> list[Obligation]:
    """ISO 27001: no obligatoria; se reporta como oportunidad."""
    return [
        Obligation(
            obligacion="Certificacion ISO 27001:2022 (cross-compliance)",
            norma="ISO 27001",
            articulo="Anexo A / ISO/IEC 27002:2022",
            autoridad="Entidad certificadora acreditada ENAC",
            accion_requerida=(
                "Palanca de esfuerzo compartido con ENS: ~70% de controles "
                "ISO 27002 mapean a medidas del Anexo II del ENS."
            ),
            condicion="voluntaria pero recomendada",
            measure_codes=[],
        ),
    ]


def _eni_obligations(ctx: ComplianceContext) -> list[Obligation]:
    """Esquema Nacional de Interoperabilidad (ENI) para admin publica."""
    if not ctx.es_administracion_publica:
        return []
    return [
        Obligation(
            obligacion="Conformidad con Esquema Nacional de Interoperabilidad",
            norma="ENI",
            articulo="RD 4/2010 + Guias CCN-STIC 808",
            autoridad="Ministerio para la Transformacion Digital",
            accion_requerida=(
                "Politica de interoperabilidad publicada, uso de estandares"
                " abiertos, aplicacion ENI en todos los sistemas e "
                "intercambios."
            ),
            measure_codes=["op.ext.1", "mp.com.4"],
        ),
    ]


ALL_RULES = [
    _rgpd_obligations,
    _nis2_obligations,
    _dora_obligations,
    _psd2_obligations,
    _ai_act_obligations,
    _eni_obligations,
]


# ════════════════════════════════════════════════════════════════════
# Heuristica desde sector → ComplianceContext
# ════════════════════════════════════════════════════════════════════

_SECTORS_SENSIBLES = {"sanidad_privada", "sanidad", "educacion_privada"}
_SECTORS_ESENCIAL_NIS2 = {
    "sanidad_privada", "energia", "agua", "transporte", "banca_finanzas",
    "administracion_publica",
}
_SECTORS_IMPORTANTE_NIS2 = {
    "fintech", "quimica", "alimentacion", "manufactura", "postal",
    "residuos", "proveedor_digital",
}
_SECTORS_FINANCIEROS_UE = {"fintech", "banca_finanzas"}


def context_from_hints(
    sector: str,
    empleados: int = 50,
    datos_sensibles: bool | None = None,
    datos_menores: bool | None = None,
    procesa_pagos: bool | None = None,
    sistemas_ia_alto_riesgo: bool = False,
    es_administracion_publica: bool | None = None,
) -> ComplianceContext:
    """Construye un ComplianceContext a partir de hints de sector + datos."""
    s = sector.lower()
    datos_sensibles = bool(
        datos_sensibles if datos_sensibles is not None else s in _SECTORS_SENSIBLES,
    )
    datos_menores = bool(
        datos_menores if datos_menores is not None else s == "educacion_privada",
    )
    procesa_pagos = bool(
        procesa_pagos if procesa_pagos is not None else s in _SECTORS_FINANCIEROS_UE,
    )
    es_admin = bool(
        es_administracion_publica if es_administracion_publica is not None
        else s == "administracion_publica",
    )
    return ComplianceContext(
        sector=s,
        empleados=empleados,
        maneja_datos_personales=True,
        maneja_datos_sensibles=datos_sensibles,
        maneja_datos_menores=datos_menores,
        es_sector_esencial_nis2=(s in _SECTORS_ESENCIAL_NIS2),
        es_sector_importante_nis2=(s in _SECTORS_IMPORTANTE_NIS2),
        es_entidad_financiera_ue=(s in _SECTORS_FINANCIEROS_UE),
        procesa_pagos=procesa_pagos,
        tiene_sistemas_ia_alto_riesgo=sistemas_ia_alto_riesgo,
        es_administracion_publica=es_admin,
    )


# ════════════════════════════════════════════════════════════════════
# API publica
# ════════════════════════════════════════════════════════════════════

def detect_obligations(ctx: ComplianceContext) -> list[Obligation]:
    """Ejecuta todas las reglas sobre el contexto y devuelve obligaciones."""
    found: list[Obligation] = []
    for rule in ALL_RULES:
        found.extend(rule(ctx))
    # ISO 27001 se sugiere siempre como oportunidad cross-compliance
    found.extend(_iso27001_opportunity(ctx))
    return found


async def persist_obligations(
    db: AsyncSession, project_id: uuid.UUID, ctx: ComplianceContext,
    *, skip_existing: bool = True,
) -> list[LegalObligation]:
    """Detecta y persiste obligaciones en ``legal_obligations``."""
    obs = detect_obligations(ctx)
    existing_keys: set[str] = set()
    if skip_existing:
        stmt = select(LegalObligation.normativa, LegalObligation.articulo).where(
            LegalObligation.project_id == project_id,
            LegalObligation.deleted_at.is_(None),
        )
        existing_keys = {
            f"{r[0]}|{r[1]}" for r in (await db.execute(stmt)).all()
        }
    created: list[LegalObligation] = []
    for o in obs:
        key = f"{o.norma}|{o.articulo}"
        if key in existing_keys:
            continue
        row = LegalObligation(
            project_id=project_id,
            normativa=o.norma,
            articulo=o.articulo,
            alcance=o.obligacion,
            impacto_ens=o.accion_requerida,
            estado="identificada",
            notas=(
                f"Autoridad: {o.autoridad}. "
                f"{('Condicion: ' + o.condicion) if o.condicion else ''} "
                f"{('Deadline: ' + o.deadline) if o.deadline else ''}"
            ).strip(),
            measure_codes_relacionadas={
                "codes": o.measure_codes,
                "autoridad": o.autoridad,
                "deadline": o.deadline,
            },
        )
        db.add(row)
        created.append(row)
    await db.flush()
    return created


def build_summary(ctx: ComplianceContext, obligations: list[Obligation]) -> dict[str, Any]:
    """Resumen agregado para el informe E-090."""
    by_norma: dict[str, list[dict[str, Any]]] = {}
    for o in obligations:
        by_norma.setdefault(o.norma, []).append({
            "obligacion": o.obligacion,
            "articulo": o.articulo,
            "autoridad": o.autoridad,
            "accion_requerida": o.accion_requerida,
            "deadline": o.deadline,
            "medidas_ens": o.measure_codes,
        })
    return {
        "sector": ctx.sector,
        "empleados": ctx.empleados,
        "total_obligaciones": len(obligations),
        "por_norma": by_norma,
        "recomendacion": (
            "multi_compliance" if len(by_norma) >= 3
            else "estandar_ens_rgpd"
        ),
        "flags": {
            "dpo_obligatorio": any(
                o.obligacion.startswith("Designar Delegado") for o in obligations
            ),
            "eipd_requerida": any(
                "EIPD" in o.obligacion for o in obligations
            ),
            "nis2_aplicable": any(o.norma == "NIS2" for o in obligations),
            "dora_aplicable": any(o.norma == "DORA" for o in obligations),
            "ai_act_aplicable": any(o.norma == "AI Act" for o in obligations),
            "eni_aplicable": any(o.norma == "ENI" for o in obligations),
        },
    }


__all__ = [
    "ALL_RULES",
    "ComplianceContext",
    "Obligation",
    "build_summary",
    "context_from_hints",
    "detect_obligations",
    "persist_obligations",
]
