"""Identity Discovery Service (M22).

Normaliza identidades descubiertas por connectors, evalua reglas de alerta
deterministicas y persiste los resultados (DiscoveredIdentity + PKG + DiscoveryAlert).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.discovery import DiscoveryAlert
from backend.app.models.onboarding import DiscoveredIdentity
from backend.app.motors.m16_onboarding import pkg_service as pkg
from backend.app.motors.m16_onboarding.connectors.base import DiscoveredIdentityDTO


# Reglas de alertas. Cada regla opera sobre DiscoveredIdentity ya persistida.
ALERT_RULES: list[dict] = [
    {
        "codigo": "PRIV_NO_MFA",
        "severidad": "critica",
        "condicion": lambda i: bool(i.es_privilegiada) and i.mfa_activo is False,
        "titulo": "Cuenta privilegiada sin MFA",
        "mensaje_template": (
            "La cuenta privilegiada '{username}' ({directorio}) no tiene MFA activo"
        ),
        "medidas_ens": ["op.acc.5", "op.acc.6"],
    },
    {
        "codigo": "INACTIVE_90D",
        "severidad": "alta",
        "condicion": lambda i: i.dias_inactiva is not None and i.dias_inactiva > 90,
        "titulo": "Cuenta inactiva >90 dias",
        "mensaje_template": (
            "La cuenta '{username}' lleva {dias_inactiva} dias sin actividad"
        ),
        "medidas_ens": ["op.acc.1", "op.acc.4"],
    },
    {
        "codigo": "SHARED_ACCOUNT",
        "severidad": "alta",
        "condicion": lambda i: i.tipo_cuenta == "compartida",
        "titulo": "Cuenta compartida detectada",
        "mensaje_template": "La cuenta '{username}' es compartida entre multiples personas",
        "medidas_ens": ["op.acc.1", "op.acc.5"],
    },
    {
        "codigo": "SERVICE_NO_OWNER",
        "severidad": "media",
        "condicion": lambda i: i.tipo_cuenta == "servicio" and not (i.display_name or "").strip(),
        "titulo": "Cuenta de servicio sin propietario documentado",
        "mensaje_template": (
            "La cuenta de servicio '{username}' no tiene propietario asignado"
        ),
        "medidas_ens": ["op.acc.1", "op.acc.2"],
    },
    {
        "codigo": "NO_MFA_STANDARD",
        "severidad": "media",
        "condicion": lambda i: i.tipo_cuenta == "standard" and i.mfa_activo is False,
        "titulo": "Cuenta estandar sin MFA",
        "mensaje_template": "La cuenta '{username}' no tiene MFA activo",
        "medidas_ens": ["op.acc.5"],
    },
    {
        "codigo": "EXTERNAL_PRIVILEGED",
        "severidad": "critica",
        "condicion": lambda i: i.tipo_cuenta == "externa" and bool(i.es_privilegiada),
        "titulo": "Cuenta externa con privilegios",
        "mensaje_template": (
            "La cuenta externa '{username}' tiene privilegios de administracion"
        ),
        "medidas_ens": ["op.acc.1", "op.acc.4", "op.ext.1"],
    },
    {
        "codigo": "PASSWORD_POLICY_FAIL",
        "severidad": "alta",
        "condicion": lambda i: i.password_policy_compliant is False,
        "titulo": "Incumplimiento de politica de contrasenas",
        "mensaje_template": (
            "La cuenta '{username}' no cumple la politica de contrasenas vigente"
        ),
        "medidas_ens": ["op.acc.5"],
    },
]


def _infer_tipo_cuenta(dto: DiscoveredIdentityDTO) -> str:
    itype = (dto.identity_type or "").lower()
    raw = dto.raw_data or {}
    user_type = str(raw.get("userType") or raw.get("user_type") or "").lower()

    if itype in {"service_account", "service", "sa"}:
        return "servicio"
    if itype in {"shared", "compartida"}:
        return "compartida"
    # "externa" prevalece sobre "privilegiada": una cuenta externa con admin
    # es un caso distinto (EXTERNAL_PRIVILEGED alert) que una cuenta interna.
    if user_type == "guest" or itype in {"guest", "external"}:
        return "externa"
    if dto.is_privileged or itype in {"admin", "privileged"}:
        return "privilegiada"
    if itype == "generic" or raw.get("is_generic") is True:
        return "generica"

    return "standard"


def _compute_dias_inactiva(dto: DiscoveredIdentityDTO) -> Optional[int]:
    raw = dto.raw_data or {}
    last = raw.get("last_sign_in") or raw.get("lastSignIn") or raw.get("last_activity")
    if not last:
        return None
    try:
        if isinstance(last, str):
            ts = datetime.fromisoformat(last.replace("Z", "+00:00"))
        elif isinstance(last, datetime):
            ts = last
        else:
            return None
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        delta = datetime.now(timezone.utc) - ts
        return max(0, delta.days)
    except Exception:
        return None


async def persist_identity_dto(
    session: AsyncSession,
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    provider: str,
    directorio: str,
    dto: DiscoveredIdentityDTO,
) -> DiscoveredIdentity:
    """Persiste un DTO como DiscoveredIdentity + nodo PKG."""
    tipo_cuenta = _infer_tipo_cuenta(dto)
    dias = _compute_dias_inactiva(dto)
    raw = dto.raw_data or {}

    pkg_node = await pkg.add_node(
        session, project_id,
        node_type="identity",
        label=dto.display_name or dto.external_id,
        external_id=f"m22:{provider}:{dto.external_id}",
        properties={
            "tipo_cuenta": tipo_cuenta,
            "es_privilegiada": bool(dto.is_privileged),
            "mfa_enabled": dto.mfa_enabled,
            "directorio": directorio,
            "fuente_conector": provider,
            "source": "m22_discovery",
        },
    )

    identity = DiscoveredIdentity(
        project_id=project_id,
        discovery_run_id=run_id,
        fuente_conector=provider,
        directorio=directorio,
        username=dto.external_id,
        email=dto.email,
        display_name=dto.display_name,
        tipo_cuenta=tipo_cuenta,
        es_privilegiada=bool(dto.is_privileged),
        es_activa=dto.is_active,
        mfa_activo=dto.mfa_enabled,
        dias_inactiva=dias,
        password_policy_compliant=raw.get("password_policy_compliant"),
        grupos=list(raw.get("groups") or []),
        permisos_efectivos=list(raw.get("permissions") or []),
        alertas=[],
        pkg_node_id=pkg_node,
    )
    session.add(identity)
    await session.flush()
    return identity


async def evaluate_alerts_for_identity(
    session: AsyncSession,
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    identity: DiscoveredIdentity,
) -> list[DiscoveryAlert]:
    """Aplica ALERT_RULES a una identidad y persiste alertas resultantes."""
    created: list[DiscoveryAlert] = []
    alerts_summary: list[dict] = []
    for rule in ALERT_RULES:
        try:
            if not rule["condicion"](identity):
                continue
        except Exception:
            continue

        try:
            descripcion = rule["mensaje_template"].format(
                username=identity.username or "(sin-username)",
                directorio=identity.directorio or "(sin-directorio)",
                dias_inactiva=identity.dias_inactiva or 0,
            )
        except Exception:
            descripcion = rule["titulo"]

        alert = DiscoveryAlert(
            project_id=project_id,
            discovery_run_id=run_id,
            modulo="identities",
            severidad=rule["severidad"],
            codigo=rule["codigo"],
            titulo=rule["titulo"],
            descripcion=descripcion,
            entity_type="discovered_identity",
            entity_id=identity.id,
            medidas_ens_afectadas=list(rule["medidas_ens"]),
        )
        session.add(alert)
        created.append(alert)
        alerts_summary.append({
            "severidad": rule["severidad"],
            "codigo": rule["codigo"],
            "titulo": rule["titulo"],
        })

    if alerts_summary:
        existing = list(identity.alertas or [])
        existing.extend(alerts_summary)
        identity.alertas = existing
    await session.flush()
    return created


async def discover_from_connector(
    session: AsyncSession,
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    provider: str,
    directorio: str,
    dtos: list[DiscoveredIdentityDTO],
) -> tuple[list[DiscoveredIdentity], list[DiscoveryAlert]]:
    """Persiste identidades normalizadas y evalua alertas por cada una."""
    identities: list[DiscoveredIdentity] = []
    alerts: list[DiscoveryAlert] = []
    for dto in dtos:
        identity = await persist_identity_dto(
            session, project_id, run_id, provider, directorio, dto
        )
        identities.append(identity)
        alerts.extend(
            await evaluate_alerts_for_identity(session, project_id, run_id, identity)
        )
    return identities, alerts


async def list_identities(
    session: AsyncSession,
    project_id: uuid.UUID,
    es_privilegiada: Optional[bool] = None,
    mfa_activo: Optional[bool] = None,
    tipo_cuenta: Optional[str] = None,
) -> list[DiscoveredIdentity]:
    stmt = select(DiscoveredIdentity).where(
        DiscoveredIdentity.project_id == project_id,
        DiscoveredIdentity.deleted_at.is_(None),
    )
    if es_privilegiada is not None:
        stmt = stmt.where(DiscoveredIdentity.es_privilegiada.is_(es_privilegiada))
    if mfa_activo is not None:
        stmt = stmt.where(DiscoveredIdentity.mfa_activo.is_(mfa_activo))
    if tipo_cuenta:
        stmt = stmt.where(DiscoveredIdentity.tipo_cuenta == tipo_cuenta)
    r = await session.execute(stmt.order_by(DiscoveredIdentity.created_at.desc()))
    return list(r.scalars().all())


async def get_identity(
    session: AsyncSession, identity_id: uuid.UUID
) -> Optional[DiscoveredIdentity]:
    r = await session.execute(
        select(DiscoveredIdentity).where(
            DiscoveredIdentity.id == identity_id,
            DiscoveredIdentity.deleted_at.is_(None),
        )
    )
    return r.scalar_one_or_none()


async def soft_delete_identity(session: AsyncSession, identity_id: uuid.UUID) -> bool:
    identity = await get_identity(session, identity_id)
    if identity is None:
        return False
    identity.deleted_at = datetime.now(timezone.utc)
    await session.flush()
    return True


async def identity_summary(session: AsyncSession, project_id: uuid.UUID) -> dict:
    """Resumen total, por tipo_cuenta, privilegiadas, sin MFA, inactivas."""
    base_where = (
        DiscoveredIdentity.project_id == project_id,
        DiscoveredIdentity.deleted_at.is_(None),
    )
    total = (await session.execute(
        select(func.count(DiscoveredIdentity.id)).where(*base_where)
    )).scalar_one() or 0

    privilegiadas = (await session.execute(
        select(func.count(DiscoveredIdentity.id)).where(
            *base_where, DiscoveredIdentity.es_privilegiada.is_(True)
        )
    )).scalar_one() or 0

    sin_mfa = (await session.execute(
        select(func.count(DiscoveredIdentity.id)).where(
            *base_where, DiscoveredIdentity.mfa_activo.is_(False)
        )
    )).scalar_one() or 0

    inactivas_90 = (await session.execute(
        select(func.count(DiscoveredIdentity.id)).where(
            *base_where, DiscoveredIdentity.dias_inactiva > 90
        )
    )).scalar_one() or 0

    by_tipo: dict[str, int] = {}
    r = await session.execute(
        select(DiscoveredIdentity.tipo_cuenta, func.count(DiscoveredIdentity.id))
        .where(*base_where)
        .group_by(DiscoveredIdentity.tipo_cuenta)
    )
    for t, count in r.all():
        by_tipo[t or "unknown"] = count

    # MFA coverage
    evaluated = (await session.execute(
        select(func.count(DiscoveredIdentity.id)).where(
            *base_where, DiscoveredIdentity.mfa_activo.isnot(None)
        )
    )).scalar_one() or 0
    with_mfa = (await session.execute(
        select(func.count(DiscoveredIdentity.id)).where(
            *base_where, DiscoveredIdentity.mfa_activo.is_(True)
        )
    )).scalar_one() or 0
    mfa_pct = round(100.0 * with_mfa / evaluated, 1) if evaluated else 0.0

    # Alertas por severidad del run mas reciente
    alert_by_sev: dict[str, int] = {}
    r = await session.execute(
        select(DiscoveryAlert.severidad, func.count(DiscoveryAlert.id))
        .where(DiscoveryAlert.project_id == project_id, DiscoveryAlert.modulo == "identities")
        .group_by(DiscoveryAlert.severidad)
    )
    for sev, count in r.all():
        alert_by_sev[sev] = count

    return {
        "total": total,
        "privilegiadas": privilegiadas,
        "sin_mfa": sin_mfa,
        "inactivas_90d": inactivas_90,
        "by_tipo_cuenta": by_tipo,
        "mfa_coverage": {
            "evaluated": evaluated,
            "with_mfa": with_mfa,
            "percentage": mfa_pct,
        },
        "alerts_by_severidad": alert_by_sev,
    }


async def mfa_coverage(session: AsyncSession, project_id: uuid.UUID) -> dict:
    """Cobertura MFA global + por tipo de cuenta."""
    summary = await identity_summary(session, project_id)
    base_where = (
        DiscoveredIdentity.project_id == project_id,
        DiscoveredIdentity.deleted_at.is_(None),
        DiscoveredIdentity.mfa_activo.isnot(None),
    )
    by_tipo: dict[str, dict] = {}
    r = await session.execute(
        select(
            DiscoveredIdentity.tipo_cuenta,
            func.count(DiscoveredIdentity.id),
            func.sum(
                func.cast(DiscoveredIdentity.mfa_activo, sa_types_boolean_int())
            ),
        )
        .where(*base_where)
        .group_by(DiscoveredIdentity.tipo_cuenta)
    )
    for tipo, total, with_mfa in r.all():
        total = total or 0
        with_mfa = int(with_mfa or 0)
        by_tipo[tipo or "unknown"] = {
            "total": total,
            "with_mfa": with_mfa,
            "percentage": round(100.0 * with_mfa / total, 1) if total else 0.0,
        }
    return {
        "overall": summary["mfa_coverage"],
        "by_tipo_cuenta": by_tipo,
    }


def sa_types_boolean_int():
    """Cast boolean -> int para SUM en agregados."""
    from sqlalchemy import Integer
    return Integer
