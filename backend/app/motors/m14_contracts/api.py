"""Motor 14 - Contracts API."""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db, set_tenant_context
from backend.app.auth.dependencies import require_owner

from .contract_service import (
    ContractError,
    ContractService,
)
from .schemas import ScanWindow


router = APIRouter(
    prefix="/contracts", tags=["Motor 14 - Contracts"],
    # TODO-RBAC-PER-ENDPOINT-001 Cat A: Marcos-only.
    dependencies=[Depends(require_owner)],
)


async def _set_project_rls(project_id: uuid.UUID, db: AsyncSession):
    client_id = (await db.execute(
        text("SELECT get_project_owner(:pid)"), {"pid": str(project_id)}
    )).scalar()
    if not client_id:
        raise HTTPException(status_code=404, detail="Project not found")
    await set_tenant_context(db, client_id=client_id, project_id=project_id)


class RetractContractBody(BaseModel):
    motivo: str = Field("recategorizacion", min_length=2, max_length=100)


@router.post("/{contract_id}/retract")
async def retract_contract(
    contract_id: uuid.UUID,
    body: RetractContractBody,
    db: AsyncSession = Depends(get_db),
):
    """#5 cabo N2.5 · retira/anula un contrato EN VUELO (sin firma del cliente)
    revocando su magic-link, para poder elevar la categoría con seguridad. NO
    actúa sobre contratos firmados por el cliente (devuelve 409)."""
    pid = (await db.execute(
        text(
            "SELECT project_id FROM contracts "
            "WHERE id = :cid AND deleted_at IS NULL"
        ),
        {"cid": str(contract_id)},
    )).scalar()
    if not pid:
        raise HTTPException(status_code=404, detail="Contrato no encontrado")
    await _set_project_rls(pid, db)
    try:
        c = await ContractService().retract_in_flight_contract(
            db, contract_id, body.motivo,
        )
    except ContractError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    await db.commit()
    return {"contract_id": str(c.id), "estado": c.estado, "motivo": body.motivo}


# ------------------- Schemas -------------------

class GenerateContractBody(BaseModel):
    proposal_id: uuid.UUID
    plantilla_id: str = Field(..., min_length=5, max_length=20)
    cliente_firmante_nombre: str = Field(..., min_length=2, max_length=255)
    cliente_firmante_cargo: str = Field(..., min_length=2, max_length=255)
    parametros_xyzpr: Optional[dict] = None
    clausula_recursos: Optional[dict] = None
    vigencia_meses: int = Field(12, ge=1, le=120)


class SendClientSignatureBody(BaseModel):
    recipient_email: EmailStr
    base_url: str = Field("https://app.fulkro.es", min_length=10, max_length=255)


# §3.3: RegisterClientSignatureBody eliminado (schema muerto · el endpoint
# register-client-signature se quitó en #43 · flujo real = m13 ContractSigningFlow).


class AddCommitmentBody(BaseModel):
    tipo: str = Field(..., min_length=2, max_length=100)
    descripcion: Optional[str] = None
    parametro: Optional[str] = Field(None, max_length=100)
    valor_esperado: Optional[str] = Field(None, max_length=255)


class GenerateLLMContractBody(BaseModel):
    proposal_id: uuid.UUID
    cliente_firmante_nombre: str = Field(..., min_length=2, max_length=255)
    cliente_firmante_cargo: str = Field(..., min_length=2, max_length=255)
    sector: Optional[str] = Field(None, max_length=64)
    cif_override: Optional[str] = Field(None, max_length=20)
    razon_social_override: Optional[str] = Field(None, max_length=255)
    tipo_organizacion: Optional[str] = Field(None, max_length=255)
    vigencia_meses: int = Field(12, ge=1, le=120)
    clausula_recursos: Optional[dict] = None
    use_llm: bool = True


# ------------------- Endpoints -------------------

@router.get("/templates")
async def list_templates():
    return {"templates": ContractService.list_templates()}


class ContractClientPrefill(BaseModel):
    """#9 · datos del cliente del proyecto para pre-rellenar el wizard."""
    razon_social: str | None = None
    cif: str | None = None
    domicilio_fiscal: str | None = None
    persona_contacto: str | None = None


@router.get(
    "/projects/{project_id}/contracts/client-prefill",
    response_model=ContractClientPrefill,
)
async def contract_client_prefill(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ContractClientPrefill:
    """#9 · datos del cliente del proyecto para pre-rellenar el wizard de
    contrato (firmante editable). El default del firmante es ``persona_contacto``;
    el wizard recuerda confirmar que tiene poder de firma (decisión D2)."""
    await _set_project_rls(project_id, db)
    row = (await db.execute(text(
        "SELECT c.nombre, c.cif, c.domicilio_fiscal, c.persona_contacto "
        "FROM projects p JOIN clients c ON c.id = p.client_id "
        "WHERE p.id = :pid"
    ), {"pid": str(project_id)})).first()
    if row is None:
        return ContractClientPrefill()
    return ContractClientPrefill(
        razon_social=row[0], cif=row[1],
        domicilio_fiscal=row[2], persona_contacto=row[3],
    )


@router.post(
    "/projects/{project_id}/contracts/generate",
    status_code=status.HTTP_201_CREATED,
)
async def generate_contract(
    project_id: uuid.UUID,
    body: GenerateContractBody,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    try:
        c = await ContractService().generate_contract(
            db,
            proposal_id=body.proposal_id,
            project_id=project_id,
            plantilla_id=body.plantilla_id,
            cliente_firmante_nombre=body.cliente_firmante_nombre,
            cliente_firmante_cargo=body.cliente_firmante_cargo,
            parametros=body.parametros_xyzpr,
            clausula_recursos=body.clausula_recursos,
            vigencia_meses=body.vigencia_meses,
        )
    except ContractError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await db.commit()
    return _serialize(c)


@router.post(
    "/projects/{project_id}/contracts/generate-llm",
    status_code=status.HTTP_201_CREATED,
)
async def generate_contract_llm(
    project_id: uuid.UUID,
    body: GenerateLLMContractBody,
    db: AsyncSession = Depends(get_db),
):
    """Genera C-001 con clausulas LLM (Agente 20 Sonnet 4.6) opt-in.

    Espera una ``proposal_id`` ya creada. Si ``use_llm=true`` invoca al
    Agente 20 para producir clausulas narrativas validadas contra
    PricingCalculator. Caida a fallback determinista si el LLM alucina
    tras los reintentos.
    """
    await _set_project_rls(project_id, db)
    cliente_dict = {
        "cif": body.cif_override,
        "razon_social": body.razon_social_override,
        "tipo_organizacion": body.tipo_organizacion,
        "sector": body.sector,
    }
    narrative_mode = "llm" if body.use_llm else "deterministic"
    try:
        contract = await ContractService().generate_contract_apendice_m(
            db,
            proposal_id=body.proposal_id,
            project_id=project_id,
            cliente=cliente_dict,
            cliente_firmante_nombre=body.cliente_firmante_nombre,
            cliente_firmante_cargo=body.cliente_firmante_cargo,
            vigencia_meses=body.vigencia_meses,
            clausula_recursos=body.clausula_recursos,
            narrative_mode=narrative_mode,
        )
    except ContractError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=400, detail=f"Error generando contrato: {exc}"
        )
    await db.commit()
    return {
        "contract": _serialize(contract),
        "narrative_mode": narrative_mode,
        "agent_20_result": (contract.parametros_xyzpr or {}).get("llm_clauses"),
    }


@router.get("/projects/{project_id}/contracts")
async def list_contracts(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    rows = await ContractService().list_contracts(db, project_id=project_id)
    return {"contracts": [_serialize(r) for r in rows]}


@router.get("/projects/{project_id}/contracts/{contract_id}")
async def get_contract(
    project_id: uuid.UUID,
    contract_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    c = await ContractService().get_contract(db, contract_id)
    if not c:
        raise HTTPException(status_code=404, detail="Contract not found")
    return _serialize(c)


@router.post("/projects/{project_id}/contracts/{contract_id}/sign-marcos")
async def sign_marcos(
    project_id: uuid.UUID,
    contract_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    try:
        c = await ContractService().sign_marcos(db, contract_id)
    except ContractError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await db.commit()
    return _serialize(c)


@router.post("/projects/{project_id}/contracts/{contract_id}/send-client")
async def send_to_client(
    project_id: uuid.UUID,
    contract_id: uuid.UUID,
    body: SendClientSignatureBody,
    owner=Depends(require_owner),
    db: AsyncSession = Depends(get_db),
):
    """#43 · REDIRIGIDO al flujo autoritativo m13 ``ContractSigningFlow`` (magic
    -link FIRMA_CONTRATO + OTP/geo + freeze documento_sha256 + SigningIntent
    canvas Ed25519 + IDMS). La UI no cambia (mismo route/respuesta · equivalencia
    #7.2). Sustituye el antiguo ``send_for_client_signature`` (FIRMA_DOCUMENTO ·
    timestamp · sin conversión) que era el path vivo PERO incompleto."""
    await _set_project_rls(project_id, db)
    from backend.app.motors.m13_commercial.services.contract_signing_flow import (
        ContractNotFoundError,
        ContractSigningFlow,
        ContractSigningFlowError,
    )

    svc = ContractService()
    c = await svc.get_contract(db, contract_id)
    if c is None:
        raise HTTPException(status_code=404, detail="Contract no encontrado")
    recipient_name = c.cliente_firmante_nombre or str(body.recipient_email)
    try:
        link = await ContractSigningFlow(db).send_for_signing(
            contract_id=contract_id,
            recipient_email=str(body.recipient_email),
            recipient_name=recipient_name,
            created_by_user_id=owner.id,
            base_url=body.base_url,
        )
    except (ContractSigningFlowError, ContractNotFoundError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await db.commit()
    # Tras el commit se pierde el contexto RLS (`set_tenant_context` usa
    # SET LOCAL · transaction-scoped) → re-leer el contrato sin re-establecerlo
    # devuelve None bajo RLS y revienta al serializar (AttributeError NoneType).
    # Defecto detectado en la simulación MEDIO E2E (envío de contrato al cliente).
    await _set_project_rls(project_id, db)
    c = await svc.get_contract(db, contract_id)
    return {"contract": _serialize(c), "magic_link": link}


# #43 · endpoint `register-client-signature` ELIMINADO. Era el callback del
# antiguo flujo magic-link FIRMA_DOCUMENTO + timestamp (sin canvas, sin
# conversión #7). La UI NO lo llamaba (verificado · solo `send-client` y
# `sign-marcos`). El flujo autoritativo es ahora el público magic-link
# FIRMA_CONTRATO + canvas Ed25519 (`ContractSigningFlow.confirm_signing` ·
# router `contract_signing_public_api`). El método de servicio homónimo se
# conserva (no referenciado por endpoints · deprecado).


@router.get("/projects/{project_id}/contracts/{contract_id}/commitments")
async def list_commitments(
    project_id: uuid.UUID,
    contract_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    rows = await ContractService().list_commitments(db, contract_id)
    return {"commitments": [_serialize_commitment(r) for r in rows]}


@router.post(
    "/projects/{project_id}/contracts/{contract_id}/commitments",
    status_code=status.HTTP_201_CREATED,
)
async def add_commitment(
    project_id: uuid.UUID,
    contract_id: uuid.UUID,
    body: AddCommitmentBody,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    try:
        commitment = await ContractService().add_commitment(
            db, contract_id,
            tipo=body.tipo,
            descripcion=body.descripcion,
            parametro=body.parametro,
            valor_esperado=body.valor_esperado,
        )
    except ContractError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await db.commit()
    return _serialize_commitment(commitment)


@router.post("/projects/{project_id}/contracts/{contract_id}/check-commitments")
async def check_commitments(
    project_id: uuid.UUID,
    contract_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    await db.commit()
    return {"results": await ContractService().check_commitments(db, contract_id)}


@router.put("/projects/{project_id}/contracts/{contract_id}/scan-window")
async def set_scan_window(
    project_id: uuid.UUID,
    contract_id: uuid.UUID,
    body: Optional[ScanWindow] = None,
    db: AsyncSession = Depends(get_db),
):
    """Establece (o limpia con body=null) la ventana de scan del contrato.

    Consumido por M08 verification scope_deriver para wiring contractual
    de ventana nocturna · cierra TODO-M8-G3.
    """
    await _set_project_rls(project_id, db)
    try:
        c = await ContractService().set_scan_window(
            db, contract_id, body.model_dump() if body else None,
        )
    except ContractError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    await db.commit()
    return _serialize(c)


@router.get("/projects/{project_id}/contracts/{contract_id}/docx")
async def download_docx(
    project_id: uuid.UUID,
    contract_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, db)
    svc = ContractService()
    contract = await svc.get_contract(db, contract_id)
    if contract is None:
        raise HTTPException(status_code=404, detail="Contract no encontrado")
    try:
        if contract.plantilla_id == "C-001":
            # #42 · contrato comercial → DOCX canónico REDACTADO (8 cláusulas +
            # hitos + alcance + emisor/cliente + complemento Agent 20), NO el
            # volcado de parámetros. Mismo contrato HTTP (binario DOCX adjunto).
            from .legal_templates import render_canonical_contract_docx
            content = await render_canonical_contract_docx(db, contract)
        else:
            # C-002..C-005 (adenda/retainer/NDA/SLA): render legacy preservado
            # (fuera del alcance de #42 · sin romper su contrato HTTP).
            content = await svc.generate_docx(db, contract_id)
    except ContractError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": f'attachment; filename="contrato_{contract_id}.docx"'
        },
    )


# ------------------- Helpers -------------------

def _serialize(c):
    return {
        "id": str(c.id),
        "lead_id": str(c.lead_id) if c.lead_id else None,
        "proposal_id": str(c.proposal_id) if c.proposal_id else None,
        "project_id": str(c.project_id) if c.project_id else None,
        "tipo": c.tipo,
        "plantilla_id": c.plantilla_id,
        "cliente_firmante_nombre": c.cliente_firmante_nombre,
        "cliente_firmante_cargo": c.cliente_firmante_cargo,
        "clausula_recursos": c.clausula_recursos,
        "parametros_xyzpr": c.parametros_xyzpr,
        "hash_sha256": c.hash_sha256,
        "firmado_marcos_at": c.firmado_marcos_at.isoformat() if c.firmado_marcos_at else None,
        "firmado_cliente_at": c.firmado_cliente_at.isoformat() if c.firmado_cliente_at else None,
        "firmado_cliente_link_id": str(c.firmado_cliente_link_id) if c.firmado_cliente_link_id else None,
        "vigente_desde": c.vigente_desde.isoformat() if c.vigente_desde else None,
        "vigente_hasta": c.vigente_hasta.isoformat() if c.vigente_hasta else None,
        "estado": c.estado,
        "adendas": c.adendas,
        "scan_window": c.scan_window,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }


def _serialize_commitment(com):
    return {
        "id": str(com.id),
        "contract_id": str(com.contract_id),
        "project_id": str(com.project_id) if com.project_id else None,
        "tipo": com.tipo,
        "descripcion": com.descripcion,
        "parametro": com.parametro,
        "valor_esperado": com.valor_esperado,
        "valor_actual": com.valor_actual,
        "cumplido": com.cumplido,
        "ultima_verificacion_at": com.ultima_verificacion_at.isoformat() if com.ultima_verificacion_at else None,
    }


# ================================================================
# 7 modelos legales DOCX (SAN-C.MB-10.2)
# ================================================================


@router.get("/legal-templates")
async def list_legal_templates_endpoint():
    """Catálogo canónico 7 modelos legales DOCX disponibles.

    Refs: SAN-C.MB-10.2
    """
    from .legal_templates import list_legal_templates

    return [
        {
            "code": t.code,
            "slug": t.slug,
            "title": t.title,
            "description": t.description,
            "requires_provider": t.requires_provider,
            "ccn_stic": t.ccn_stic,
        }
        for t in list_legal_templates()
    ]


class GenerateLegalDocxBody(BaseModel):
    provider_name: Optional[str] = None
    provider_cif: Optional[str] = None
    provider_role: Optional[str] = None


@router.post("/projects/{project_id}/legal-templates/{template_slug}/generate")
async def generate_legal_template_endpoint(
    project_id: uuid.UUID,
    template_slug: str,
    body: GenerateLegalDocxBody = GenerateLegalDocxBody(),
    db: AsyncSession = Depends(get_db),
):
    """Genera modelo legal DOCX con datos cliente + proyecto + RSEG/DPO.

    ``provider_name`` opcional · obligatorio si ``requires_provider`` en
    el catálogo (cláusulas terceros · DPA · pentesting back-to-back).

    Refs: SAN-C.MB-10.2
    """
    from .legal_templates import (
        build_legal_context,
        generate_legal_docx,
        get_legal_template,
    )

    await _set_project_rls(project_id, db)

    try:
        info = get_legal_template(template_slug)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    if info.requires_provider and not body.provider_name:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Plantilla {info.code} requiere 'provider_name' "
                f"(cláusulas con tercero)."
            ),
        )

    ctx = await build_legal_context(
        db,
        project_id,
        provider_name=body.provider_name,
        provider_cif=body.provider_cif,
    )
    if body.provider_role is not None:
        ctx.provider_role = body.provider_role

    bio = generate_legal_docx(template_slug, ctx)
    return Response(
        content=bio.getvalue(),
        media_type=(
            "application/vnd.openxmlformats-officedocument."
            "wordprocessingml.document"
        ),
        headers={
            "Content-Disposition": (
                f'attachment; filename="{template_slug}_{project_id}.docx"'
            ),
            "X-Template-Code": info.code,
        },
    )
