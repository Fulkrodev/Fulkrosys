"""Continuity Assessment (M22-C).

Evalua backups, DRP, SLAs y SPOFs tecnicos. Calcula nivel de madurez L0-L5
con reglas deterministas y genera alertas para gaps criticos (sin DRP en
categoria Media/Alta, backup sin cifrar, sin pruebas restauracion recientes).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.discovery import ContinuityAssessment, DiscoveryAlert
from backend.app.models.onboarding import DiscoveredAsset


MATURITY_RULES: dict[str, str] = {
    "L0": "Sin backups documentados, sin DRP",
    "L1": "Backups parciales, sin DRP formal, sin pruebas",
    "L2": "Backups completos documentados, DRP existe pero no probado",
    "L3": "Backups probados, DRP documentado y probado, RTO/RPO definidos",
    "L4": "Backup offsite + cifrado, DRP probado anualmente, SLAs monitorizados",
    "L5": "Backup automatico verificado, DRP con failover, 0 SPOFs criticos",
}


def _parse_date(value) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        ts = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def _all_backups_encrypted(backups: list[dict]) -> bool:
    if not backups:
        return False
    return all(bool(b.get("cifrado")) for b in backups)


def _any_backup_offsite(backups: list[dict]) -> bool:
    if not backups:
        return False
    return any(
        (b.get("offsite") is True)
        or ("s3" in str(b.get("destino") or "").lower())
        or ("azure" in str(b.get("destino") or "").lower())
        or ("offsite" in str(b.get("destino") or "").lower())
        for b in backups
    )


def _latest_restoration(backups: list[dict]) -> Optional[datetime]:
    dates = [
        _parse_date(b.get("ultima_prueba") or b.get("ultima_prueba_restauracion"))
        for b in backups
    ]
    dates = [d for d in dates if d is not None]
    return max(dates) if dates else None


def _calculate_maturity(
    tiene_drp: Optional[bool], drp_probado: Optional[bool],
    backups: list[dict], tiene_offsite: bool, all_encrypted: bool,
    prueba_exitosa: Optional[bool], spofs: list[dict], rto: Optional[int],
    rpo: Optional[int],
) -> str:
    backups_count = len(backups or [])
    spofs_criticos = sum(
        1 for s in (spofs or [])
        if str(s.get("impacto", "")).lower() in {"alto", "critico", "critica"}
    )

    if (
        backups_count > 0 and all_encrypted and tiene_offsite
        and drp_probado and prueba_exitosa and spofs_criticos == 0
        and (rto is not None) and (rpo is not None)
    ):
        return "L5"
    if (
        tiene_offsite and all_encrypted and drp_probado
        and (rto is not None) and (rpo is not None)
    ):
        return "L4"
    if backups_count > 0 and drp_probado and prueba_exitosa is not None:
        return "L3"
    if backups_count > 0 and tiene_drp:
        return "L2"
    if backups_count > 0 or tiene_drp:
        return "L1"
    return "L0"


async def _detect_spofs(
    session: AsyncSession, project_id: uuid.UUID, backups: list[dict],
) -> list[dict]:
    """Cruza assets criticos con backups: si no hay backup que mencione el
    asset, se registra como SPOF potencial."""
    r = await session.execute(
        select(DiscoveredAsset).where(
            DiscoveredAsset.project_id == project_id,
            DiscoveredAsset.deleted_at.is_(None),
        )
    )
    assets = list(r.scalars().all())
    criticos = [
        a for a in assets
        if a.criticidad_propuesta in {"alta", "muy_alta"}
    ]
    if not criticos:
        return []
    backup_names = [
        str(b.get("sistema") or "").lower() for b in (backups or [])
    ]
    spofs: list[dict] = []
    for a in criticos:
        if not any(a.nombre.lower() in bn for bn in backup_names):
            spofs.append({
                "sistema": a.nombre,
                "descripcion": (
                    f"Asset critico (criticidad {a.criticidad_propuesta}) "
                    f"sin backup asociado en el inventario"
                ),
                "impacto": "alto",
                "mitigacion_propuesta": (
                    f"Incluir '{a.nombre}' en la estrategia de backup formal"
                ),
            })
    return spofs


async def assess(
    session: AsyncSession,
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    continuity_data: Optional[dict] = None,
) -> tuple[ContinuityAssessment, list[DiscoveryAlert]]:
    data = continuity_data or {}
    backups = list(data.get("backups") or [])
    drp = data.get("drp") or {}
    slas = list(data.get("slas") or [])
    spofs_input = list(data.get("spofs") or [])

    all_encrypted = _all_backups_encrypted(backups)
    offsite = _any_backup_offsite(backups)
    ultima_restore = _latest_restoration(backups)
    # prueba_exitosa: si cualquier backup tiene prueba_restauracion_exitosa=True
    prueba_exitosa = None
    if backups:
        vals = [b.get("prueba_exitosa") for b in backups if "prueba_exitosa" in b]
        if vals:
            prueba_exitosa = any(bool(v) for v in vals)

    spofs_auto = await _detect_spofs(session, project_id, backups)
    spofs = spofs_input + spofs_auto

    rto = data.get("rto_global_horas")
    rpo = data.get("rpo_global_horas")

    tiene_drp = drp.get("tiene") if drp else None
    madurez = _calculate_maturity(
        tiene_drp=tiene_drp,
        drp_probado=drp.get("probado") if drp else None,
        backups=backups, tiene_offsite=offsite, all_encrypted=all_encrypted,
        prueba_exitosa=prueba_exitosa, spofs=spofs, rto=rto, rpo=rpo,
    )

    assessment = ContinuityAssessment(
        project_id=project_id,
        discovery_run_id=run_id,
        backups_inventario=backups,
        tiene_backup_offsite=offsite if backups else None,
        tiene_backup_cifrado=all_encrypted if backups else None,
        ultima_prueba_restauracion=ultima_restore,
        prueba_restauracion_exitosa=prueba_exitosa,
        tiene_drp=tiene_drp,
        drp_documentado=drp.get("documentado") if drp else None,
        drp_probado=drp.get("probado") if drp else None,
        drp_ultima_prueba=_parse_date(drp.get("ultima_prueba")) if drp else None,
        slas_proveedores=slas,
        spofs_detectados=spofs,
        rto_global_horas=rto,
        rpo_global_horas=rpo,
        nivel_madurez_continuidad=madurez,
        observaciones=data.get("observaciones"),
    )
    session.add(assessment)
    await session.flush()

    # Alertas
    alerts: list[DiscoveryAlert] = []
    categoria = str(data.get("categoria_ens") or "media").lower()

    if not tiene_drp and categoria in {"media", "alta"}:
        alerts.append(DiscoveryAlert(
            project_id=project_id, discovery_run_id=run_id,
            modulo="continuity", severidad="alta",
            codigo="CONT_NO_DRP",
            titulo=f"Sin DRP en categoria ENS {categoria}",
            descripcion=(
                "La organizacion no tiene DRP documentado y la categoria ENS "
                f"({categoria}) lo requiere (op.cont.1-4)."
            ),
            entity_type="continuity_assessment",
            entity_id=assessment.id,
            medidas_ens_afectadas=["op.cont.1", "op.cont.2"],
        ))

    if backups and not all_encrypted:
        alerts.append(DiscoveryAlert(
            project_id=project_id, discovery_run_id=run_id,
            modulo="continuity", severidad="alta",
            codigo="CONT_BACKUP_SIN_CIFRAR",
            titulo="Backup sin cifrar detectado",
            descripcion=(
                "Uno o mas backups no estan cifrados. mp.info.6 requiere "
                "copias de seguridad protegidas."
            ),
            entity_type="continuity_assessment",
            entity_id=assessment.id,
            medidas_ens_afectadas=["mp.info.6"],
        ))

    # Sin prueba de restauracion > 12 meses (o nunca)
    now = datetime.now(timezone.utc)
    if backups and (
        ultima_restore is None or (now - ultima_restore).days > 365
    ):
        alerts.append(DiscoveryAlert(
            project_id=project_id, discovery_run_id=run_id,
            modulo="continuity", severidad="media",
            codigo="CONT_RESTORE_OBSOLETA",
            titulo="Sin prueba de restauracion reciente (>12 meses)",
            descripcion=(
                "No hay registro de una prueba de restauracion exitosa en "
                "los ultimos 12 meses."
            ),
            entity_type="continuity_assessment",
            entity_id=assessment.id,
            medidas_ens_afectadas=["op.cont.3"],
        ))

    # SPOFs criticos detectados
    critical_spofs = [
        s for s in spofs
        if str(s.get("impacto", "")).lower() in {"alto", "critico", "critica"}
    ]
    if critical_spofs:
        alerts.append(DiscoveryAlert(
            project_id=project_id, discovery_run_id=run_id,
            modulo="continuity", severidad="alta",
            codigo="CONT_SPOF_DETECTED",
            titulo=f"{len(critical_spofs)} SPOFs criticos detectados",
            descripcion=(
                "Assets criticos sin redundancia ni backup: "
                + ", ".join(s.get("sistema", "?") for s in critical_spofs[:5])
            ),
            entity_type="continuity_assessment",
            entity_id=assessment.id,
            medidas_ens_afectadas=["op.cont.2"],
        ))

    for a in alerts:
        session.add(a)
    await session.flush()
    return assessment, alerts


async def get_latest(
    session: AsyncSession, project_id: uuid.UUID,
) -> Optional[ContinuityAssessment]:
    r = await session.execute(
        select(ContinuityAssessment)
        .where(
            ContinuityAssessment.project_id == project_id,
            ContinuityAssessment.deleted_at.is_(None),
        )
        .order_by(ContinuityAssessment.created_at.desc())
        .limit(1)
    )
    return r.scalar_one_or_none()


def to_dict(a: ContinuityAssessment) -> dict:
    return {
        "id": str(a.id),
        "project_id": str(a.project_id),
        "discovery_run_id": str(a.discovery_run_id),
        "backups_inventario": a.backups_inventario or [],
        "tiene_backup_offsite": a.tiene_backup_offsite,
        "tiene_backup_cifrado": a.tiene_backup_cifrado,
        "ultima_prueba_restauracion": (
            a.ultima_prueba_restauracion.isoformat()
            if a.ultima_prueba_restauracion else None
        ),
        "prueba_restauracion_exitosa": a.prueba_restauracion_exitosa,
        "tiene_drp": a.tiene_drp,
        "drp_documentado": a.drp_documentado,
        "drp_probado": a.drp_probado,
        "drp_ultima_prueba": (
            a.drp_ultima_prueba.isoformat() if a.drp_ultima_prueba else None
        ),
        "slas_proveedores": a.slas_proveedores or [],
        "spofs_detectados": a.spofs_detectados or [],
        "rto_global_horas": a.rto_global_horas,
        "rpo_global_horas": a.rpo_global_horas,
        "nivel_madurez_continuidad": a.nivel_madurez_continuidad,
        "observaciones": a.observaciones,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }
