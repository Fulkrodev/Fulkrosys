"""Motor 1 Categorization · 19 dimensiones adaptación (sub-atom 1.C.D.A.0 v3.8).

Schemas Pydantic para capturar las 19 dimensiones del proyecto que drive
la adaptación del workflow enriched (sub-atom 1.C.D.A YAML 150-300 sub-pasos).

3 dims existing (categoria_objetivo · archetype · fase) + 16 nuevas
(Anexo L plan v3.8). Captura distribuida natural:
  - m13_commercial proposal_service: dims comerciales pre-venta
  - m_meetings actions: dims básicas reunión exploratoria
  - m16_onboarding: 10 dims técnicas/legales cliente onboarding
  - admin page /admin/projects/[id]/dimensiones/: source of truth
    consolidado · Marcos puede editar cualquier dim cualquier momento.

OPS-029 caso 9 formalizada: realidad empírica "3 existing + 16 nuevas"
(spec v3.7 decía "4 + 15" · empleados/tamano_empleados no estaba en projects).
"""
from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


# === ENUMS as Literal types · matching CHECK constraints migration ===

TamanoEmpleadosType = Literal[
    "micro", "pequeno", "mediano", "grande", "enterprise",
]
MadurezEnsType = Literal["L0", "L1", "L2", "L3", "L4", "L5"]
GeografiaType = Literal["spain", "ue", "global", "apac", "latam"]
AplicaNis2Type = Literal["no", "esencial", "importante"]
AplicaDoraType = Literal[
    "no", "entidad_financiera", "proveedor_ict_critico",
]
AplicaAiActType = Literal[
    "no", "alto_riesgo", "gpai", "limitado",
]
DpoDesignadoType = Literal["interno", "externo", "no_designado"]
ArquitecturaType = Literal[
    "on_premise", "hibrido", "cloud_native", "multi_cloud", "hyperscaler",
]
MultiTenancyType = Literal["single", "multi_tenant", "marketplace"]
EquipoTiTamanoType = Literal[
    "sin_equipo", "1_3", "4_10", "11_30", "gt30",
]
UrgenciaType = Literal["no_urge", "6m", "3m", "1m", "urgent_30d"]
PresupuestoType = Literal["minimo", "estandar", "generoso", "premium"]
CompromisoType = Literal["proactivo", "reactivo", "reluctante"]
HorasSemanaType = Literal["lt5h", "5_15h", "15_40h", "full_time"]

CertificacionPreviaType = Literal[
    "ISO27001", "SOC2", "PCI-DSS", "ENS-expirado", "HIPAA", "GDPR-cert", "ninguna",
]


# === SCHEMAS ===


class ProjectDimensionsRead(BaseModel):
    """Lectura de las 19 dimensiones de un proyecto."""

    # 3 dims existing
    categoria_objetivo: str | None = Field(
        None, description="ENS categoría (BASICA/MEDIA/ALTA)",
    )
    archetype: str | None = Field(None, description="Arquetipo sectorial")
    fase: str = Field(..., description="Fase lifecycle (derived)")

    # 16 dims nuevas
    tamano_empleados: TamanoEmpleadosType = "pequeno"
    madurez_ens_actual: MadurezEnsType = "L0"
    geografia_operacion: GeografiaType = "spain"
    procesa_datos_sensibles_rgpd9: bool = False
    aplica_nis2: AplicaNis2Type = "no"
    aplica_dora: AplicaDoraType = "no"
    aplica_ai_act: AplicaAiActType = "no"
    dpo_designado: DpoDesignadoType = "no_designado"
    arquitectura_sistemas: ArquitecturaType = "cloud_native"
    multi_tenancy: MultiTenancyType = "single"
    equipo_ti_tamano: EquipoTiTamanoType = "1_3"
    certificaciones_previas: list[str] = Field(default_factory=list)
    urgencia_certificacion: UrgenciaType = "6m"
    presupuesto_disponible: PresupuestoType = "estandar"
    compromiso_interno: CompromisoType = "reactivo"
    horas_cliente_semana: HorasSemanaType = "5_15h"

    # Indicator helper · % completado (3 base + 16 nuevas non-default)
    dims_captured_count: int = Field(
        0,
        description="Cuántas dims se han capturado (non-default values)",
    )
    dims_total: int = Field(19, description="Total dims target")

    model_config = ConfigDict(from_attributes=True)


class ProjectDimensionsUpdate(BaseModel):
    """Update parcial de dimensiones (Marcos admin o cliente vía onboarding)."""

    # NOTE: categoria_objetivo · archetype · fase no se editan aquí
    # (gestionados por m01_categorization · m_meetings · workflow respectivamente)
    tamano_empleados: TamanoEmpleadosType | None = None
    madurez_ens_actual: MadurezEnsType | None = None
    geografia_operacion: GeografiaType | None = None
    procesa_datos_sensibles_rgpd9: bool | None = None
    aplica_nis2: AplicaNis2Type | None = None
    aplica_dora: AplicaDoraType | None = None
    aplica_ai_act: AplicaAiActType | None = None
    dpo_designado: DpoDesignadoType | None = None
    arquitectura_sistemas: ArquitecturaType | None = None
    multi_tenancy: MultiTenancyType | None = None
    equipo_ti_tamano: EquipoTiTamanoType | None = None
    certificaciones_previas: list[str] | None = None
    urgencia_certificacion: UrgenciaType | None = None
    presupuesto_disponible: PresupuestoType | None = None
    compromiso_interno: CompromisoType | None = None
    horas_cliente_semana: HorasSemanaType | None = None

    model_config = ConfigDict(extra="forbid")


# === Helpers ===

def compute_dims_captured(project) -> int:
    """Cuenta dimensiones capturadas (non-default values).

    Las dims existing (categoria_objetivo, archetype) cuentan si están
    setteadas. fase siempre cuenta (NOT NULL existing).
    """
    count = 1  # fase siempre cuenta
    if project.categoria_objetivo:
        count += 1
    if project.archetype:
        count += 1

    # 16 dims nuevas · check non-default
    if project.tamano_empleados != "pequeno":
        count += 1
    if project.madurez_ens_actual != "L0":
        count += 1
    if project.geografia_operacion != "spain":
        count += 1
    if project.procesa_datos_sensibles_rgpd9:
        count += 1
    if project.aplica_nis2 != "no":
        count += 1
    if project.aplica_dora != "no":
        count += 1
    if project.aplica_ai_act != "no":
        count += 1
    if project.dpo_designado != "no_designado":
        count += 1
    if project.arquitectura_sistemas != "cloud_native":
        count += 1
    if project.multi_tenancy != "single":
        count += 1
    if project.equipo_ti_tamano != "1_3":
        count += 1
    if project.certificaciones_previas:
        count += 1
    if project.urgencia_certificacion != "6m":
        count += 1
    if project.presupuesto_disponible != "estandar":
        count += 1
    if project.compromiso_interno != "reactivo":
        count += 1
    if project.horas_cliente_semana != "5_15h":
        count += 1

    return count
