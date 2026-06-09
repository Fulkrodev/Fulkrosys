"""Endpoints REST Motor 22 — Technical Discovery."""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db, set_tenant_context
from backend.app.models.discovery import (
    DiscoveredConfiguration,
    DiscoveredDataStore,
    VulnerabilityFinding,
)
from backend.app.models.onboarding import DiscoveredAsset, DiscoveredIdentity
from backend.app.auth.dependencies import require_owner

from fastapi.responses import FileResponse

from . import (
    alerts_service,
    asset_discovery,
    config_discovery,
    continuity_service,
    data_discovery,
    dataflow_service,
    identity_discovery,
    log_assessment,
    orchestrator,
    report_generator,
    vuln_discovery,
)


router = APIRouter(
    prefix="/discovery", tags=["Motor 22 - Technical Discovery"],
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


# ============ Schemas ============

class CreateRunBody(BaseModel):
    modules: list[str] = Field(..., min_length=1)
    connector_sources: dict = Field(default_factory=dict)
    triggered_by: str = Field("manual", max_length=50)
    execute: bool = Field(True, description="Si true, ejecuta el run inmediatamente")


# ============ Discovery Runs ============

@router.post("/projects/{project_id}/runs")
async def create_run_endpoint(
    project_id: uuid.UUID,
    body: CreateRunBody,
    session: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, session)
    try:
        run = await orchestrator.create_run(
            session, project_id,
            modules=body.modules,
            connector_sources=body.connector_sources,
            triggered_by=body.triggered_by,
        )
    except orchestrator.OrchestratorError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        )
    if body.execute:
        try:
            run = await orchestrator.execute_run(session, run.id)
        except orchestrator.OrchestratorError as exc:
            raise HTTPException(
                status_code=http_status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
            )
    await session.commit()
    return orchestrator.run_to_dict(run)


@router.get("/projects/{project_id}/runs")
async def list_runs_endpoint(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, session)
    runs = await orchestrator.list_runs(session, project_id)
    return [orchestrator.run_to_dict(r) for r in runs]


@router.get("/projects/{project_id}/runs/{run_id}")
async def get_run_endpoint(
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, session)
    run = await orchestrator.get_run(session, run_id)
    if run is None or run.project_id != project_id:
        raise HTTPException(status_code=404, detail="DiscoveryRun no encontrado")
    return orchestrator.run_to_dict(run)


@router.post("/projects/{project_id}/runs/{run_id}/cancel")
async def cancel_run_endpoint(
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, session)
    try:
        run = await orchestrator.cancel_run(session, run_id)
    except orchestrator.OrchestratorError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        )
    await session.commit()
    return orchestrator.run_to_dict(run)


@router.delete("/projects/{project_id}/runs/{run_id}")
async def delete_run_endpoint(
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, session)
    ok = await orchestrator.soft_delete_run(session, run_id)
    if not ok:
        raise HTTPException(status_code=404, detail="DiscoveryRun no encontrado")
    await session.commit()
    return {"deleted": True, "run_id": str(run_id)}


# ============ Assets ============

def _asset_to_dict(a: DiscoveredAsset) -> dict:
    return {
        "id": str(a.id),
        "project_id": str(a.project_id),
        "discovery_run_id": str(a.discovery_run_id) if a.discovery_run_id else None,
        "fuente_conector": a.fuente_conector,
        "tipo_magerit": a.tipo_magerit,
        "nombre": a.nombre,
        "identificador": a.identificador,
        "descripcion": a.descripcion,
        "criticidad_propuesta": a.criticidad_propuesta,
        "propietario_inferido": a.propietario_inferido,
        "ubicacion": a.ubicacion,
        "metadata_extra": a.metadata_extra or {},
        "pkg_node_id": str(a.pkg_node_id) if a.pkg_node_id else None,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }


@router.get("/projects/{project_id}/assets")
async def list_assets_endpoint(
    project_id: uuid.UUID,
    tipo_magerit: Optional[str] = Query(None),
    criticidad: Optional[str] = Query(None),
    fuente: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, session)
    assets = await asset_discovery.list_assets(
        session, project_id, tipo_magerit=tipo_magerit,
        criticidad=criticidad, fuente=fuente,
    )
    return [_asset_to_dict(a) for a in assets]


@router.get("/projects/{project_id}/assets/summary")
async def assets_summary_endpoint(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, session)
    return await asset_discovery.assets_summary(session, project_id)


@router.get("/projects/{project_id}/assets/{asset_id}")
async def get_asset_endpoint(
    project_id: uuid.UUID,
    asset_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, session)
    asset = await asset_discovery.get_asset(session, asset_id)
    if asset is None or asset.project_id != project_id:
        raise HTTPException(status_code=404, detail="Asset no encontrado")
    return _asset_to_dict(asset)


@router.delete("/projects/{project_id}/assets/{asset_id}")
async def delete_asset_endpoint(
    project_id: uuid.UUID,
    asset_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, session)
    ok = await asset_discovery.soft_delete_asset(session, asset_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Asset no encontrado")
    await session.commit()
    return {"deleted": True, "asset_id": str(asset_id)}


# ============ Identities ============

def _identity_to_dict(i: DiscoveredIdentity) -> dict:
    return {
        "id": str(i.id),
        "project_id": str(i.project_id),
        "discovery_run_id": str(i.discovery_run_id) if i.discovery_run_id else None,
        "fuente_conector": i.fuente_conector,
        "directorio": i.directorio,
        "username": i.username,
        "email": i.email,
        "display_name": i.display_name,
        "tipo_cuenta": i.tipo_cuenta,
        "es_privilegiada": i.es_privilegiada,
        "es_activa": i.es_activa,
        "mfa_activo": i.mfa_activo,
        "dias_inactiva": i.dias_inactiva,
        "password_policy_compliant": i.password_policy_compliant,
        "grupos": i.grupos or [],
        "permisos_efectivos": i.permisos_efectivos or [],
        "alertas": i.alertas or [],
        "pkg_node_id": str(i.pkg_node_id) if i.pkg_node_id else None,
        "created_at": i.created_at.isoformat() if i.created_at else None,
    }


@router.get("/projects/{project_id}/identities")
async def list_identities_endpoint(
    project_id: uuid.UUID,
    es_privilegiada: Optional[bool] = Query(None),
    mfa_activo: Optional[bool] = Query(None),
    tipo_cuenta: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, session)
    items = await identity_discovery.list_identities(
        session, project_id,
        es_privilegiada=es_privilegiada, mfa_activo=mfa_activo, tipo_cuenta=tipo_cuenta,
    )
    return [_identity_to_dict(i) for i in items]


@router.get("/projects/{project_id}/identities/summary")
async def identity_summary_endpoint(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, session)
    return await identity_discovery.identity_summary(session, project_id)


@router.get("/projects/{project_id}/identities/{identity_id}")
async def get_identity_endpoint(
    project_id: uuid.UUID,
    identity_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, session)
    identity = await identity_discovery.get_identity(session, identity_id)
    if identity is None or identity.project_id != project_id:
        raise HTTPException(status_code=404, detail="Identity no encontrada")
    return _identity_to_dict(identity)


@router.delete("/projects/{project_id}/identities/{identity_id}")
async def delete_identity_endpoint(
    project_id: uuid.UUID,
    identity_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, session)
    ok = await identity_discovery.soft_delete_identity(session, identity_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Identity no encontrada")
    await session.commit()
    return {"deleted": True, "identity_id": str(identity_id)}


# ============ Alerts ============

@router.get("/projects/{project_id}/alerts")
async def list_alerts_endpoint(
    project_id: uuid.UUID,
    severidad: Optional[str] = Query(None),
    modulo: Optional[str] = Query(None),
    run_id: Optional[uuid.UUID] = Query(None),
    session: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, session)
    alerts = await alerts_service.list_alerts(
        session, project_id, severidad=severidad, modulo=modulo, discovery_run_id=run_id,
    )
    return [alerts_service.alert_to_dict(a) for a in alerts]


@router.get("/projects/{project_id}/alerts/summary")
async def alerts_summary_endpoint(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, session)
    return await alerts_service.alerts_summary(session, project_id)


# ============ Configurations (M22-B) ============

def _config_to_dict(c: DiscoveredConfiguration) -> dict:
    return {
        "id": str(c.id),
        "project_id": str(c.project_id),
        "discovery_run_id": str(c.discovery_run_id),
        "fuente_conector": c.fuente_conector,
        "sistema": c.sistema,
        "control_id": c.control_id,
        "control_description": c.control_description,
        "estado": c.estado,
        "valor_actual": c.valor_actual,
        "valor_esperado": c.valor_esperado,
        "gap_severidad": c.gap_severidad,
        "herramienta_deteccion": c.herramienta_deteccion,
        "medidas_ens_afectadas": c.medidas_ens_afectadas or [],
        "raw_output": c.raw_output or {},
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }


@router.get("/projects/{project_id}/configurations")
async def list_configurations_endpoint(
    project_id: uuid.UUID,
    gap_severidad: Optional[str] = Query(None),
    fuente: Optional[str] = Query(None),
    estado: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, session)
    items = await config_discovery.list_configurations(
        session, project_id,
        gap_severidad=gap_severidad, fuente=fuente, estado=estado,
    )
    return [_config_to_dict(c) for c in items]


@router.get("/projects/{project_id}/configurations/summary")
async def configurations_summary_endpoint(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, session)
    return await config_discovery.configurations_summary(session, project_id)


@router.get("/projects/{project_id}/configurations/{config_id}")
async def get_configuration_endpoint(
    project_id: uuid.UUID,
    config_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, session)
    cfg = await config_discovery.get_configuration(session, config_id)
    if cfg is None or cfg.project_id != project_id:
        raise HTTPException(status_code=404, detail="Configuracion no encontrada")
    return _config_to_dict(cfg)


# ============ Vulnerabilities (M22-B) ============

def _vuln_to_dict(v: VulnerabilityFinding) -> dict:
    return {
        "id": str(v.id),
        "project_id": str(v.project_id),
        "discovery_run_id": str(v.discovery_run_id),
        "fuente": v.fuente,
        "titulo": v.titulo,
        "descripcion": v.descripcion,
        "cve_id": v.cve_id,
        "cvss_score": v.cvss_score,
        "cvss_vector": v.cvss_vector,
        "cvss_severity": v.cvss_severity,
        "asset_afectado": v.asset_afectado,
        "asset_id": str(v.asset_id) if v.asset_id else None,
        "es_explotable": v.es_explotable,
        "exploit_disponible": v.exploit_disponible,
        "remediacion_sugerida": v.remediacion_sugerida,
        "medidas_ens_afectadas": v.medidas_ens_afectadas or [],
        "mitre_tactics": v.mitre_tactics or [],
        "estado": v.estado,
        "created_at": v.created_at.isoformat() if v.created_at else None,
    }


class VulnImportBody(BaseModel):
    run_id: uuid.UUID
    source: str = Field(..., min_length=2, max_length=50)
    # source: "openvas", "nuclei", "trivy", "generic"
    findings: list[dict] = Field(default_factory=list)


class VulnUpdateBody(BaseModel):
    estado: str = Field(..., min_length=2, max_length=20)


@router.get("/projects/{project_id}/vulnerabilities")
async def list_vulnerabilities_endpoint(
    project_id: uuid.UUID,
    cvss_severity: Optional[str] = Query(None),
    fuente: Optional[str] = Query(None),
    estado: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, session)
    items = await vuln_discovery.list_vulnerabilities(
        session, project_id,
        cvss_severity=cvss_severity, fuente=fuente, estado=estado,
    )
    return [_vuln_to_dict(v) for v in items]


@router.get("/projects/{project_id}/vulnerabilities/summary")
async def vulnerabilities_summary_endpoint(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, session)
    return await vuln_discovery.vulnerabilities_summary(session, project_id)


@router.get("/projects/{project_id}/vulnerabilities/{finding_id}")
async def get_vulnerability_endpoint(
    project_id: uuid.UUID,
    finding_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, session)
    vf = await vuln_discovery.get_vulnerability(session, finding_id)
    if vf is None or vf.project_id != project_id:
        raise HTTPException(status_code=404, detail="Finding no encontrado")
    return _vuln_to_dict(vf)


@router.patch("/projects/{project_id}/vulnerabilities/{finding_id}")
async def update_vulnerability_endpoint(
    project_id: uuid.UUID,
    finding_id: uuid.UUID,
    body: VulnUpdateBody,
    session: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, session)
    try:
        vf = await vuln_discovery.update_finding_status(session, finding_id, body.estado)
    except vuln_discovery.VulnImportError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        )
    if vf is None:
        raise HTTPException(status_code=404, detail="Finding no encontrado")
    await session.commit()
    return _vuln_to_dict(vf)


@router.post("/projects/{project_id}/vulnerabilities/import")
async def import_vulnerabilities_endpoint(
    project_id: uuid.UUID,
    body: VulnImportBody,
    session: AsyncSession = Depends(get_db),
):
    """Importa findings desde scanner externo (openvas/nuclei/trivy/generic)."""
    await _set_project_rls(project_id, session)
    # Validar que el run existe y pertenece al proyecto
    run = await orchestrator.get_run(session, body.run_id)
    if run is None or run.project_id != project_id:
        raise HTTPException(status_code=404, detail="DiscoveryRun no encontrado")
    src = body.source.strip().lower()
    if src == "openvas":
        findings, alerts = await vuln_discovery.import_openvas_results(
            session, project_id, body.run_id, body.findings,
        )
    elif src == "nuclei":
        findings, alerts = await vuln_discovery.import_nuclei_results(
            session, project_id, body.run_id, body.findings,
        )
    elif src == "trivy":
        # Trivy envia el JSON entero en findings[0] si sigue el formato estandar
        trivy_json = body.findings[0] if body.findings else {}
        findings, alerts = await vuln_discovery.import_trivy_results(
            session, project_id, body.run_id, trivy_json,
        )
    else:
        findings, alerts = await vuln_discovery.import_generic(
            session, project_id, body.run_id, body.findings, src,
        )
    await session.commit()
    return {
        "imported": len(findings),
        "alerts_generated": len(alerts),
        "source": src,
    }


# ============ Data Stores (M22-B) ============

def _datastore_to_dict(d: DiscoveredDataStore) -> dict:
    return {
        "id": str(d.id),
        "project_id": str(d.project_id),
        "discovery_run_id": str(d.discovery_run_id),
        "fuente_conector": d.fuente_conector,
        "tipo": d.tipo,
        "nombre": d.nombre,
        "ubicacion": d.ubicacion,
        "volumen_estimado_gb": d.volumen_estimado_gb,
        "clasificacion_inicial": d.clasificacion_inicial,
        "patrones_detectados": d.patrones_detectados or [],
        "tiene_datos_personales": d.tiene_datos_personales,
        "tiene_datos_salud": d.tiene_datos_salud,
        "tiene_datos_financieros": d.tiene_datos_financieros,
        "cifrado_en_reposo": d.cifrado_en_reposo,
        "cifrado_en_transito": d.cifrado_en_transito,
        "control_acceso": d.control_acceso,
        "tiene_backup": d.tiene_backup,
        "metadata_extra": d.metadata_extra or {},
        "pkg_node_id": str(d.pkg_node_id) if d.pkg_node_id else None,
        "created_at": d.created_at.isoformat() if d.created_at else None,
    }


@router.get("/projects/{project_id}/data-stores")
async def list_data_stores_endpoint(
    project_id: uuid.UUID,
    clasificacion: Optional[str] = Query(None),
    tiene_datos_personales: Optional[bool] = Query(None),
    session: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, session)
    items = await data_discovery.list_data_stores(
        session, project_id,
        clasificacion=clasificacion, tiene_datos_personales=tiene_datos_personales,
    )
    return [_datastore_to_dict(d) for d in items]


@router.get("/projects/{project_id}/data-stores/summary")
async def data_stores_summary_endpoint(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, session)
    return await data_discovery.data_summary(session, project_id)


@router.get("/projects/{project_id}/data-stores/{store_id}")
async def get_data_store_endpoint(
    project_id: uuid.UUID,
    store_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, session)
    store = await data_discovery.get_data_store(session, store_id)
    if store is None or store.project_id != project_id:
        raise HTTPException(status_code=404, detail="Data store no encontrado")
    return _datastore_to_dict(store)


@router.delete("/projects/{project_id}/data-stores/{store_id}")
async def delete_data_store_endpoint(
    project_id: uuid.UUID,
    store_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, session)
    ok = await data_discovery.soft_delete_data_store(session, store_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Data store no encontrado")
    await session.commit()
    return {"deleted": True, "store_id": str(store_id)}


# ============ Logging Assessment (M22-C) ============

class LoggingBody(BaseModel):
    run_id: uuid.UUID
    logging_data: dict = Field(default_factory=dict)


@router.get("/projects/{project_id}/logging")
async def get_logging_endpoint(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, session)
    ass = await log_assessment.get_latest(session, project_id)
    if ass is None:
        raise HTTPException(status_code=404, detail="Sin logging assessment")
    return log_assessment.to_dict(ass)


@router.post("/projects/{project_id}/logging")
async def create_logging_endpoint(
    project_id: uuid.UUID,
    body: LoggingBody,
    session: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, session)
    run = await orchestrator.get_run(session, body.run_id)
    if run is None or run.project_id != project_id:
        raise HTTPException(status_code=404, detail="DiscoveryRun no encontrado")
    assessment, alerts = await log_assessment.assess(
        session, project_id, body.run_id, body.logging_data,
    )
    await session.commit()
    return {
        **log_assessment.to_dict(assessment),
        "alerts_generated": len(alerts),
    }


# ============ Data Flow Diagrams (M22-C) ============

@router.get("/projects/{project_id}/dataflows")
async def list_dataflows_endpoint(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, session)
    dfds = await dataflow_service.list_dfds(session, project_id)
    return [dataflow_service.to_dict(d) for d in dfds]


@router.get("/projects/{project_id}/dataflows/{dfd_id}")
async def get_dataflow_endpoint(
    project_id: uuid.UUID,
    dfd_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, session)
    dfd = await dataflow_service.get_dfd(session, dfd_id)
    if dfd is None or dfd.project_id != project_id:
        raise HTTPException(status_code=404, detail="DFD no encontrado")
    return dataflow_service.to_dict(dfd)


class GenerateDataflowBody(BaseModel):
    run_id: uuid.UUID


@router.post("/projects/{project_id}/dataflows/generate")
async def generate_dataflows_endpoint(
    project_id: uuid.UUID,
    body: GenerateDataflowBody,
    session: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, session)
    run = await orchestrator.get_run(session, body.run_id)
    if run is None or run.project_id != project_id:
        raise HTTPException(status_code=404, detail="DiscoveryRun no encontrado")
    dfds = await dataflow_service.generate_all_dfds(session, project_id, body.run_id)
    await session.commit()
    return {
        "generated": len(dfds),
        "dfds": [dataflow_service.to_dict(d) for d in dfds],
    }


# ============ Continuity Assessment (M22-C) ============

class ContinuityBody(BaseModel):
    run_id: uuid.UUID
    continuity_data: dict = Field(default_factory=dict)


@router.get("/projects/{project_id}/continuity")
async def get_continuity_endpoint(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, session)
    ass = await continuity_service.get_latest(session, project_id)
    if ass is None:
        raise HTTPException(status_code=404, detail="Sin continuity assessment")
    return continuity_service.to_dict(ass)


@router.post("/projects/{project_id}/continuity")
async def create_continuity_endpoint(
    project_id: uuid.UUID,
    body: ContinuityBody,
    session: AsyncSession = Depends(get_db),
):
    await _set_project_rls(project_id, session)
    run = await orchestrator.get_run(session, body.run_id)
    if run is None or run.project_id != project_id:
        raise HTTPException(status_code=404, detail="DiscoveryRun no encontrado")
    assessment, alerts = await continuity_service.assess(
        session, project_id, body.run_id, body.continuity_data,
    )
    await session.commit()
    return {
        **continuity_service.to_dict(assessment),
        "alerts_generated": len(alerts),
    }


# ============ Technical Report (M22-C) ============

@router.get("/projects/{project_id}/report")
async def get_report_endpoint(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    """Informe tecnico consolidado en JSON."""
    await _set_project_rls(project_id, session)
    return await report_generator.generate(session, project_id)


@router.get("/projects/{project_id}/report/docx")
async def download_report_docx_endpoint(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    """Descarga el DOCX del informe tecnico."""
    await _set_project_rls(project_id, session)
    path = await report_generator.generate_docx(session, project_id)
    if path is None:
        raise HTTPException(
            status_code=501, detail="docxtpl no disponible en este entorno",
        )
    return FileResponse(
        str(path),
        media_type=(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ),
        filename=f"informe_tecnico_m22_{project_id}.docx",
    )


@router.get("/projects/{project_id}/summary")
async def discovery_summary_endpoint(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    """Resumen consolidado de todos los modulos (stats + madurez)."""
    await _set_project_rls(project_id, session)
    report = await report_generator.generate(session, project_id)
    return {
        "meta": report["meta"],
        "resumen_ejecutivo": report["resumen_ejecutivo"],
        "alerts_top": report["alerts"].get("top", []),
        "recomendaciones": report["recomendaciones"],
    }
