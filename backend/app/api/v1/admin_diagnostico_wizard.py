"""Sub-atom 1.D.F.0.A v3.11 · Diagnóstico ENS unificado wizard 6 steps.

Atomic endpoint que consolida creación de cliente + proyecto + diagnostic
inicial ENS desde un único formulario admin (`/admin/projects/new`).

V3 PRIORIDAD ALTA · directiva Marcos firmísima: "perfecto · sin deuda".

#7.2 · la lógica de provisión se extrajo al SERVICIO COMÚN
``m13_commercial.services.project_provisioning_service.provision_project``
(misma fuente que usa la auto-conversión por firma · #7.4) para que el alta
manual y la conversión NO diverjan. Este módulo conserva los schemas del
wizard + un endpoint wrapper fino que delega en el servicio.

Endpoint atomic · rollback completo si cualquier step falla.
"""
from __future__ import annotations

import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.dependencies import require_owner
from backend.app.database import get_db


router = APIRouter(
    prefix="/api/v1/admin/diagnostico-wizard",
    tags=["1.D.F.0.A · Diagnóstico ENS Wizard"],
    dependencies=[Depends(require_owner)],
)


# ════════════════════════════════════════════════════════════════════
# Pydantic schemas · 6 steps
# ════════════════════════════════════════════════════════════════════


SectorEnsType = Literal[
    "aapp",
    "privado_licita_aapp",
    "privado_proveedor_aapp",
    "otros",
]
TipoOrganizacionType = Literal["pyme", "gran_empresa", "sector_publico", "ong"]
TamanoEmpleadosType = Literal[
    "micro", "pequeno", "mediano", "grande", "enterprise",
]
ArquitecturaType = Literal[
    "on_premise", "hibrido", "cloud_native", "multi_cloud", "hyperscaler",
]
DpoDesignadoType = Literal["interno", "externo", "no_designado"]
EquipoTiTamanoType = Literal[
    "sin_equipo", "1_3", "4_10", "11_30", "gt30",
]
GeografiaType = Literal["spain", "ue", "global", "apac", "latam"]
ImpactLevelType = Literal["BAJO", "MEDIO", "ALTO"]
CategoryType = Literal["BASICA", "MEDIA", "ALTA"]
ActivoTipoType = Literal[
    "datos", "servicios", "infraestructura", "software", "personal",
]


class StepDatosCliente(BaseModel):
    """Step 1 · datos básicos cliente."""

    razon_social: str = Field(..., min_length=1, max_length=255)
    cif: str = Field(..., min_length=1, max_length=20)
    sector_industrial: str | None = Field(None, max_length=100)
    domicilio_fiscal: str | None = Field(None, max_length=255)
    web: str | None = Field(None, max_length=255)
    contacto_email: EmailStr | None = None
    contacto_telefono: str | None = Field(None, max_length=50)
    persona_contacto: str | None = Field(None, max_length=255)


class StepContextoENS(BaseModel):
    """Step 2 · contexto ENS de la organización."""

    sector_ens: SectorEnsType
    tipo_organizacion: TipoOrganizacionType
    tamano_empleados: TamanoEmpleadosType
    sites_oficinas: int = Field(1, ge=1, le=999)
    it_interno: bool = True
    ciso_interno: bool = False
    dpo_designado: DpoDesignadoType = "no_designado"
    equipo_ti_tamano: EquipoTiTamanoType = "1_3"
    geografia_operacion: GeografiaType = "spain"
    arquitectura_sistemas: ArquitecturaType = "cloud_native"


class EnsDimsValoracion(BaseModel):
    """5 dimensiones ENS Anexo I · cada Bajo/Medio/Alto."""

    confidencialidad: ImpactLevelType = "BAJO"
    integridad: ImpactLevelType = "BAJO"
    disponibilidad: ImpactLevelType = "BAJO"
    autenticidad: ImpactLevelType = "BAJO"
    trazabilidad: ImpactLevelType = "BAJO"


class StepCategoriaPreliminar(BaseModel):
    """Step 3 · categoría ENS preliminar + 5 dims Anexo I."""

    categoria_preliminar: CategoryType
    dims_anexo_i: EnsDimsValoracion
    justificacion: str | None = Field(None, max_length=1000)
    # #5 (Sub-bloque E) · suelo de categoría heredado de la AAPP contratante
    # (None = sin herencia). Marcos lo captura desde el pliego/contrato (decisión
    # A). Piso DURO: eleva categoria_objetivo (Variante 2) y lo consume luego
    # compute_for_system. Sibling de papel_aapp.
    categoria_heredada_aapp: CategoryType | None = None


class ActivoCritico(BaseModel):
    """Activo crítico capturado en wizard · seed M02 MAGERIT initial."""

    nombre: str = Field(..., min_length=1, max_length=200)
    tipo: ActivoTipoType
    descripcion: str | None = Field(None, max_length=500)


class StepActivosCriticos(BaseModel):
    """Step 4 · top 5 activos críticos + dependencias cloud."""

    activos: list[ActivoCritico] = Field(default_factory=list, max_length=10)
    dependencias_cloud: list[str] = Field(
        default_factory=list,
        max_length=20,
        description=(
            "Proveedores cloud / ERP / SaaS mencionados (AWS · Azure · "
            "GCP · Salesforce · etc.)"
        ),
    )


class StepFirstUser(BaseModel):
    """Step 5 · primer usuario portal cliente."""

    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=255)
    cargo: str | None = Field(None, max_length=150)
    send_magic_link: bool = True


class CreateProjectDiagnosticoRequest(BaseModel):
    """Payload completo del wizard 6 steps (Step 6 = review · no extra data)."""

    model_config = ConfigDict(extra="forbid")

    step1_datos_cliente: StepDatosCliente
    step2_contexto_ens: StepContextoENS
    step3_categoria: StepCategoriaPreliminar
    step4_activos: StepActivosCriticos
    step5_first_user: StepFirstUser
    # #7.5 · lead origen (hidratación). Si el lead tiene proyecto LIGERO, se
    # promueve ese mismo (decisión 2-A · no duplica · invariante "1 proyecto/lead").
    lead_id: uuid.UUID | None = None


class CreateProjectDiagnosticoResponse(BaseModel):
    """Respuesta atomic post-creation · IDs para redirect frontend."""

    client_id: str
    project_id: str
    magerit_analysis_id: str | None
    initial_system_id: str | None
    initial_information_type_id: str | None
    cockpit_user_id: str | None
    departments_created_count: int
    magic_link_sent: bool
    dims_captured_count: int
    summary: str


# ════════════════════════════════════════════════════════════════════
# Atomic endpoint · wrapper fino sobre el servicio común (#7.2)
# ════════════════════════════════════════════════════════════════════


@router.post(
    "/create-project",
    response_model=CreateProjectDiagnosticoResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_project_with_diagnosis(
    body: CreateProjectDiagnosticoRequest,
    db: AsyncSession = Depends(get_db),
) -> CreateProjectDiagnosticoResponse:
    """Alta atómica cliente+proyecto+diagnóstico inicial (1 transacción).

    #7.2: la lógica de provisión vive en el SERVICIO COMÚN
    ``project_provisioning_service.provision_project`` (misma fuente que la
    auto-conversión por firma · #7.4), para que no diverjan. Este endpoint
    es un wrapper fino: valida el payload y delega.
    """
    from backend.app.motors.m13_commercial.services.project_provisioning_service import (
        provision_project,
    )

    r = await provision_project(
        db,
        s1=body.step1_datos_cliente,
        s2=body.step2_contexto_ens,
        s3=body.step3_categoria,
        s4=body.step4_activos,
        s5=body.step5_first_user,
        lead_id=body.lead_id,
    )
    return CreateProjectDiagnosticoResponse(
        client_id=str(r.client_id),
        project_id=str(r.project_id),
        magerit_analysis_id=str(r.magerit_analysis_id) if r.magerit_analysis_id else None,
        initial_system_id=str(r.initial_system_id),
        initial_information_type_id=str(r.initial_information_type_id),
        cockpit_user_id=str(r.cockpit_user_id) if r.cockpit_user_id else None,
        departments_created_count=r.departments_created_count,
        magic_link_sent=r.magic_link_sent,
        dims_captured_count=r.dims_captured_count,
        summary=r.summary,
    )


# ════════════════════════════════════════════════════════════════════
# #7.5 · Prefill del wizard desde un lead (hidratación)
# ════════════════════════════════════════════════════════════════════


class WizardPrefillResponse(BaseModel):
    """Datos del lead mapeados a campos del wizard para prerellenar el form."""

    lead_id: str
    razon_social: str | None = None
    cif: str | None = None
    sector_industrial: str | None = None
    contacto_email: str | None = None
    contacto_telefono: str | None = None
    categoria_preliminar: str | None = None  # lead.categoria_objetivo_ens
    papel_aapp: str | None = None
    has_lightweight_project: bool = False


@router.get("/prefill", response_model=WizardPrefillResponse)
async def prefill_wizard_from_lead(
    lead_id: uuid.UUID = Query(..., description="Lead origen a hidratar"),
    db: AsyncSession = Depends(get_db),
) -> WizardPrefillResponse:
    """#7.5 · Devuelve los datos del lead mapeados a los campos del wizard.

    El lead no tiene domicilio_fiscal/web/persona_contacto → quedan vacíos
    (Marcos los completa). Si el lead ya tiene un proyecto LIGERO, al crear se
    PROMOVERÁ ese mismo (decisión 2-A · no duplica) · ``has_lightweight_project``
    se lo indica al frontend.
    """
    from backend.app.database import set_tenant_context
    from backend.app.models.commercial import Lead
    from backend.app.models.core import Project
    from backend.app.motors.m13_commercial.services.project_provisioning_service import (
        resolve_lead_client_id,
    )

    lead = await db.get(Lead, lead_id)
    if lead is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lead {lead_id} no encontrado",
        )

    has_lightweight = False
    if lead.convertido_a_proyecto_id is not None:
        # ``projects`` tiene RLS por cliente · sin contexto la RLS oculta el
        # proyecto (deny-all) y has_lightweight saldría siempre False. Fijar el
        # contexto del cliente del lead (clients sin RLS) antes de leerlo.
        light_client_id = await resolve_lead_client_id(db, lead)
        if light_client_id is not None:
            await set_tenant_context(db, client_id=light_client_id)
            proj = await db.get(Project, lead.convertido_a_proyecto_id)
            has_lightweight = (
                proj is not None
                and proj.client_id == light_client_id
                and proj.lifecycle_state == "DRAFT"
                and proj.fase == "pre_venta"
            )

    return WizardPrefillResponse(
        lead_id=str(lead.id),
        razon_social=lead.empresa_nombre,
        cif=lead.empresa_cif,
        sector_industrial=lead.sector,
        contacto_email=lead.contacto_email,
        contacto_telefono=lead.contacto_telefono,
        categoria_preliminar=lead.categoria_objetivo_ens,
        papel_aapp=lead.papel_aapp,
        has_lightweight_project=has_lightweight,
    )
