"""Rule catalog · Diagnostic Gap Engine (sub-atom 1.D.X.H v3.12).

DETERMINISTIC R1 INVIOLABLE · NO LLM decide detected/missing.

Estructura: catalog de GapRule dataclasses · cada regla define:
  - ens_measure_code (canónico Anexo II RD 311/2022)
  - applies_to_categories (BASICA/MEDIA/ALTA aplicabilidad)
  - default_severity (alineado gap_severity_rules_v1.yaml + nucleares)
  - gap_type (structural · reinforcement · configuration · documental)
  - detector_fn (callable que recibe lista CloudResource → emite hallazgo)
  - default_title + default_suggested_action + default_explanation_es_template

NUCLEARES (gap_severity_rules_v1.yaml): op.acc.6 · op.exp.1 · op.exp.4 · op.exp.7
op.exp.8 · op.cont.1 · mp.si.2 · mp.per.3 · org.1 · op.pl.1.

Coverage cloud-detectable focused MVP piloto:
  - op.acc.6 MFA usuarios sin · CRITICAL nuclear
  - op.acc.2 privilegios excesivos · HIGH
  - op.exp.1 inventario sistemas detectado · MEDIUM (verde si OK)
  - op.exp.8 logging activado en cloud · HIGH
  - op.exp.8 retención logs ≥12m (#1) · HIGH · + sincronización NTP · MEDIUM
  - mp.si.2 cifrado at-rest storage · CRITICAL nuclear
  - mp.info.6 backup configurado · HIGH
  - mp.s.2 buckets/storage públicos · CRITICAL
  - mp.com.2 separación de redes · MEDIUM
  - mp.eq.1 inventario equipos · MEDIUM (verde si discovery >0)
  - mp.per.4 personal autorizado documentado · MEDIUM
  - mp.com.4 cifrado en tránsito (TLS) · HIGH

T2 demand-driven post-piloto: cobertura completa 73 medidas Anexo II.

R29 cliente-friendly explanations · R30 admin tutor.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from backend.app.motors.m_cloud_connectors.models import (
    CloudGapSeverity,
    CloudGapType,
)


class RuleCategory(str, Enum):
    BASICA = "BASICA"
    MEDIA = "MEDIA"
    ALTA = "ALTA"


@dataclass(frozen=True)
class GapFinding:
    """Hallazgo emitido por una rule · NO persistido todavía (engine decide)."""

    ens_measure_code: str
    severity: str  # CloudGapSeverity value
    gap_type: str  # CloudGapType value
    title: str
    suggested_action: str
    explanation_es_template: str
    """Template con placeholders · LLM enrichment puede personalizarlo.

    Placeholders: {n_users_no_mfa} · {n_buckets_public} · {provider} · etc.
    """
    raw_evidence: dict[str, Any] = field(default_factory=dict)
    estimated_effort_days: int | None = None
    auto_fixable: bool = False
    cliente_can_see: bool = True


@dataclass(frozen=True)
class GapRule:
    """Regla de detección deterministic · pure function sobre CloudResources."""

    rule_id: str
    ens_measure_code: str
    applies_to_categories: tuple[str, ...]
    detector: Callable[[list[Any]], list[GapFinding]]
    """Recibe lista CloudResource ORM · emite list[GapFinding].

    PURE FUNCTION · sin DB · sin LLM · sin side effects.
    """


# ==================================================================
# Detectores (pure functions sobre resources)
# ==================================================================


def _filter_resources(
    resources: list[Any], resource_type_prefix: str,
) -> list[Any]:
    return [r for r in resources if r.resource_type.startswith(resource_type_prefix)]


def detect_users_without_mfa(resources: list[Any]) -> list[GapFinding]:
    """op.acc.6 · CRITICAL nuclear · usuarios sin MFA = NC inmediata ENAC."""
    identities = _filter_resources(resources, "identity.user")
    no_mfa_users = [
        r for r in identities
        if r.attributes.get("mfa_enabled") is False
    ]
    if not no_mfa_users:
        return []
    n = len(no_mfa_users)
    sample = [r.resource_name or r.resource_external_id for r in no_mfa_users[:5]]
    return [
        GapFinding(
            ens_measure_code="op.acc.6",
            severity=CloudGapSeverity.CRITICAL.value,
            gap_type=CloudGapType.STRUCTURAL.value,
            title=f"{n} usuario(s) sin MFA · op.acc.6 nuclear ENS",
            suggested_action=(
                f"Activar MFA en los {n} usuarios sin segundo factor "
                "(prioridad inmediata · es nuclear para certificación ENAC)."
            ),
            explanation_es_template=(
                "Detectamos {n_users_no_mfa} usuarios sin MFA. La medida "
                "op.acc.6 del Anexo II del RD 311/2022 exige doble factor "
                "para todos los usuarios con acceso a información sensible. "
                "Sin MFA, una contraseña filtrada da acceso directo · es uno "
                "de los hallazgos más penalizados en certificación ENAC."
            ),
            raw_evidence={
                "users_no_mfa_count": n,
                "users_no_mfa_sample": sample,
            },
            estimated_effort_days=1,
            auto_fixable=False,
        ),
    ]


def detect_excess_privileged_users(resources: list[Any]) -> list[GapFinding]:
    """op.acc.2 · HIGH · >20% privileged users sobre total = excess."""
    identities = _filter_resources(resources, "identity.user")
    if len(identities) < 5:
        return []
    privileged = [
        r for r in identities
        if r.attributes.get("is_privileged") is True
    ]
    pct = len(privileged) / max(1, len(identities))
    if pct < 0.20:
        return []
    sample = [r.resource_name or r.resource_external_id for r in privileged[:5]]
    return [
        GapFinding(
            ens_measure_code="op.acc.2",
            severity=CloudGapSeverity.HIGH.value,
            gap_type=CloudGapType.CONFIGURATION.value,
            title=(
                f"{len(privileged)} usuarios privilegiados ({pct:.0%}) · "
                "op.acc.2 excede umbral"
            ),
            suggested_action=(
                "Revisar y reducir el número de usuarios con privilegios "
                "administrativos · principio de mínimo privilegio."
            ),
            explanation_es_template=(
                "Detectamos {n_privileged} usuarios con privilegios elevados "
                "sobre {n_total} totales ({pct_privileged:.0%}). La medida "
                "op.acc.2 exige principio de mínimo privilegio. Buena práctica: "
                "<10% de cuentas administrativas en empresas medianas."
            ),
            raw_evidence={
                "n_privileged": len(privileged),
                "n_total": len(identities),
                "pct_privileged": pct,
                "sample": sample,
            },
            estimated_effort_days=3,
            auto_fixable=False,
        ),
    ]


def detect_inventory_coverage(resources: list[Any]) -> list[GapFinding]:
    """op.exp.1 · MEDIUM documental · sin recursos detectados → gap."""
    assets = _filter_resources(resources, "asset.")
    if assets:
        return []  # OK · inventario poblado por cloud discovery
    return [
        GapFinding(
            ens_measure_code="op.exp.1",
            severity=CloudGapSeverity.MEDIUM.value,
            gap_type=CloudGapType.DOCUMENTAL.value,
            title="Sin inventario de activos detectado",
            suggested_action=(
                "Conectar al menos un proveedor cloud o subir inventario "
                "manual para que la plataforma pueda diagnosticar."
            ),
            explanation_es_template=(
                "La medida op.exp.1 exige inventario actualizado de activos. "
                "Aún no hemos detectado activos en ningún proveedor cloud. "
                "Conecta tus sistemas (Microsoft, AWS, Azure...) o sube tu "
                "inventario manual y volvemos a diagnosticar."
            ),
            raw_evidence={"assets_detected": 0},
            estimated_effort_days=1,
            cliente_can_see=True,
        ),
    ]


def detect_unencrypted_storage(resources: list[Any]) -> list[GapFinding]:
    """mp.si.2 · CRITICAL nuclear · storage buckets sin cifrado at-rest."""
    storage = [
        r for r in resources
        if r.resource_type.startswith("asset.")
        and r.resource_type in {"asset.bucket", "asset.storage", "asset.volume"}
    ]
    unencrypted = [
        r for r in storage
        if r.attributes.get("encrypted_at_rest") is False
    ]
    if not unencrypted:
        return []
    n = len(unencrypted)
    sample = [r.resource_name or r.resource_external_id for r in unencrypted[:5]]
    return [
        GapFinding(
            ens_measure_code="mp.si.2",
            severity=CloudGapSeverity.CRITICAL.value,
            gap_type=CloudGapType.STRUCTURAL.value,
            title=f"{n} almacenamientos sin cifrado at-rest · mp.si.2 nuclear",
            suggested_action=(
                f"Activar cifrado en los {n} buckets/storage sin cifrar · "
                "el ENS exige cifrado de datos sensibles en reposo."
            ),
            explanation_es_template=(
                "Detectamos {n_storage_unencrypted} almacenamientos sin "
                "cifrado en reposo. mp.si.2 es nuclear · datos sensibles "
                "sin cifrar = NC mayor inmediato en auditoría ENAC."
            ),
            raw_evidence={
                "storage_unencrypted_count": n,
                "storage_unencrypted_sample": sample,
            },
            estimated_effort_days=2,
        ),
    ]


def detect_public_buckets(resources: list[Any]) -> list[GapFinding]:
    """mp.s.2 · CRITICAL · buckets/storage/SharePoint sites/shared drives públicos = NC mayor.

    Sesión 3B-2B.7 Ejecutable 4 Phase 7.1.1 (2026-05-27): extended para incluir
    asset.sharepoint_site (M365) + asset.shared_drive (GWorkspace) con misma
    detección public_access/is_public.
    """
    storage = [
        r for r in resources
        if r.resource_type in {
            "asset.bucket",
            "asset.storage",
            "asset.sharepoint_site",
            "asset.shared_drive",
        }
    ]
    public = [
        r for r in storage
        if r.attributes.get("public_access") is True
        or r.attributes.get("is_public") is True
    ]
    if not public:
        return []
    n = len(public)
    sample = [r.resource_name or r.resource_external_id for r in public[:5]]
    return [
        GapFinding(
            ens_measure_code="mp.s.2",
            severity=CloudGapSeverity.CRITICAL.value,
            gap_type=CloudGapType.STRUCTURAL.value,
            title=f"{n} recursos accesibles públicamente · mp.s.2",
            suggested_action=(
                f"Revisar inmediatamente los {n} recursos públicos "
                "(buckets · sites · shared drives) · puede haber datos sensibles "
                "expuestos a internet."
            ),
            explanation_es_template=(
                "Detectamos {n_public_buckets} recursos accesibles "
                "públicamente (puede incluir buckets · SharePoint sites · "
                "shared drives Google). Riesgo crítico · revisa hoy mismo si "
                "contienen datos confidenciales. mp.s.2 trata sobre servicios "
                "seguros y compartición controlada."
            ),
            raw_evidence={
                "public_buckets_count": n,
                "public_buckets_sample": sample,
            },
            estimated_effort_days=1,
        ),
    ]


def detect_logging_disabled(resources: list[Any]) -> list[GapFinding]:
    """op.exp.8 · HIGH nuclear · cloud sin logs centralizados."""
    cloud_resources = [r for r in resources if r.resource_type.startswith("asset.")]
    if not cloud_resources:
        return []
    has_logging = any(
        r.attributes.get("logging_enabled") is True
        for r in cloud_resources
    )
    if has_logging:
        return []
    return [
        GapFinding(
            ens_measure_code="op.exp.8",
            severity=CloudGapSeverity.HIGH.value,
            gap_type=CloudGapType.STRUCTURAL.value,
            title="Logging no detectado en cloud · op.exp.8 nuclear",
            suggested_action=(
                "Activar logs en al menos un servicio cloud y centralizar "
                "(CloudTrail, Azure Monitor, etc)."
            ),
            explanation_es_template=(
                "No detectamos logging activado en ningún recurso cloud. "
                "op.exp.8 exige registro de actividad · sin logs no hay "
                "auditoría posible y el ENAC lo marca como NC mayor."
            ),
            raw_evidence={"any_logging_enabled": False},
            estimated_effort_days=2,
        ),
    ]


# op.exp.8 · retención mínima 12 meses · ENS Media/Alta (RD 311/2022 Anexo II)
OP_EXP_8_MIN_RETENTION_DAYS = 365


def detect_log_retention_insufficient(resources: list[Any]) -> list[GapFinding]:
    """op.exp.8 · #1 · HIGH · logging ACTIVO pero retención < 12 meses (o no
    verificada). Complementa detect_logging_disabled: si no hay logging, lo cubre
    aquella regla (no se duplica); aquí el logging sí está activo pero la
    retención no alcanza los 12 meses que exige el ENS Media/Alta. Retención no
    reportada se trata como no verificada → gap (el cliente aporta evidencia)."""
    logging_resources = [
        r for r in resources
        if r.resource_type.startswith("asset.")
        and r.attributes.get("logging_enabled") is True
    ]
    if not logging_resources:
        return []
    max_retention = max(
        (int(r.attributes.get("log_retention_days") or 0) for r in logging_resources),
        default=0,
    )
    if max_retention >= OP_EXP_8_MIN_RETENTION_DAYS:
        return []
    return [
        GapFinding(
            ens_measure_code="op.exp.8",
            severity=CloudGapSeverity.HIGH.value,
            gap_type=CloudGapType.CONFIGURATION.value,
            title="Retención de logs < 12 meses · op.exp.8",
            suggested_action=(
                "Configurar la retención del registro de actividad a 12 meses "
                "mínimo, o aportar evidencia de la política de retención vigente."
            ),
            explanation_es_template=(
                "El registro de actividad está activo, pero no detectamos una "
                f"retención de al menos 12 meses ({OP_EXP_8_MIN_RETENTION_DAYS} "
                "días). op.exp.8 exige conservar los logs ≥12 meses en Media/Alta "
                "· sin ello el ENAC marca no conformidad. Si ya cumples, sube la "
                "evidencia de tu política de retención."
            ),
            raw_evidence={
                "max_retention_days_detected": max_retention,
                "min_required_days": OP_EXP_8_MIN_RETENTION_DAYS,
            },
            estimated_effort_days=1,
        ),
    ]


def detect_ntp_not_synced(resources: list[Any]) -> list[GapFinding]:
    """op.exp.8 · #1 · MEDIUM · sincronización horaria (NTP) no verificada. Los
    registros de actividad necesitan marcas de tiempo fiables (reloj
    sincronizado) para tener valor probatorio ante el ENAC. Si hay cloud
    conectado y ningún recurso confirma sincronización horaria → gap a verificar
    con evidencia. Sin assets cloud no aplica (se cubre documentalmente)."""
    asset_resources = [
        r for r in resources if r.resource_type.startswith("asset.")
    ]
    if not asset_resources:
        return []
    any_time_sync = any(
        r.attributes.get("ntp_enabled") is True
        or r.attributes.get("time_sync_enabled") is True
        or r.attributes.get("ntp_synced") is True
        for r in asset_resources
    )
    if any_time_sync:
        return []
    return [
        GapFinding(
            ens_measure_code="op.exp.8",
            severity=CloudGapSeverity.MEDIUM.value,
            gap_type=CloudGapType.CONFIGURATION.value,
            title="Sincronización horaria (NTP) no verificada · op.exp.8",
            suggested_action=(
                "Verificar que los sistemas sincronizan su reloj contra una "
                "fuente NTP fiable y aportar evidencia (configuración/estado NTP)."
            ),
            explanation_es_template=(
                "No detectamos sincronización horaria (NTP) confirmada en el "
                "cloud. op.exp.8 exige marcas de tiempo fiables en los registros "
                "· sin reloj sincronizado los logs pierden valor probatorio ante "
                "el ENAC. Aporta evidencia de tu configuración NTP para cerrarlo."
            ),
            raw_evidence={"time_sync_confirmed": False},
            estimated_effort_days=1,
        ),
    ]


def detect_no_backup_strategy(resources: list[Any]) -> list[GapFinding]:
    """mp.info.6 · HIGH · sin backup detectado para storage críticos."""
    storage = [
        r for r in resources
        if r.resource_type in {"asset.bucket", "asset.storage", "asset.volume", "asset.database"}
    ]
    if not storage:
        return []
    has_backup = any(
        r.attributes.get("backup_enabled") is True
        for r in storage
    )
    if has_backup:
        return []
    return [
        GapFinding(
            ens_measure_code="mp.info.6",
            severity=CloudGapSeverity.HIGH.value,
            gap_type=CloudGapType.STRUCTURAL.value,
            title="Sin estrategia de backup detectada · mp.info.6",
            suggested_action=(
                "Configurar copias de seguridad automáticas y verificar "
                "restauración mensualmente."
            ),
            explanation_es_template=(
                "No detectamos backups activos en almacenamientos cloud. "
                "mp.info.6 exige copias y procedimiento de restauración · "
                "Marcos te ayuda a diseñar la política."
            ),
            raw_evidence={"backup_strategy_detected": False},
            estimated_effort_days=3,
        ),
    ]


def detect_documental_policy_missing(resources: list[Any]) -> list[GapFinding]:
    """org.1 · MEDIUM documental · siempre emite (cliente sube política)."""
    # Documental rule: no se detecta desde cloud · siempre genera "documental"
    # status para que el cliente entienda que esta medida requiere documento
    # firmado por dirección. Se resolverá cuando suba evidence política.
    return [
        GapFinding(
            ens_measure_code="org.1",
            severity=CloudGapSeverity.MEDIUM.value,
            gap_type=CloudGapType.DOCUMENTAL.value,
            title="Política de seguridad firmada · org.1 nuclear documental",
            suggested_action=(
                "Subir política de seguridad firmada por dirección · "
                "FULKRO incluye plantilla E-100 lista."
            ),
            explanation_es_template=(
                "org.1 exige política de seguridad firmada y comunicada. "
                "Esto no se detecta desde la nube · cuando subas el "
                "documento firmado, este hallazgo desaparece."
            ),
            raw_evidence={"detection_method": "documental_assumed_missing"},
            estimated_effort_days=1,
            cliente_can_see=True,
        ),
    ]


# ==================================================================
# Rule catalog · canónico (orden = priority del informe)
# ==================================================================


RULE_CATALOG: tuple[GapRule, ...] = (
    GapRule(
        rule_id="rule_users_no_mfa",
        ens_measure_code="op.acc.6",
        applies_to_categories=("BASICA", "MEDIA", "ALTA"),
        detector=detect_users_without_mfa,
    ),
    GapRule(
        rule_id="rule_excess_privileged",
        ens_measure_code="op.acc.2",
        applies_to_categories=("MEDIA", "ALTA"),
        detector=detect_excess_privileged_users,
    ),
    GapRule(
        rule_id="rule_inventory_coverage",
        ens_measure_code="op.exp.1",
        applies_to_categories=("BASICA", "MEDIA", "ALTA"),
        detector=detect_inventory_coverage,
    ),
    GapRule(
        rule_id="rule_unencrypted_storage",
        ens_measure_code="mp.si.2",
        # FIX(REV-1): mp.si.2 "Criptografía" aplica a MEDIA/ALTA (no BÁSICA) según
        # Anexo II RD 311/2022. Antes el cifrado at-rest se mapeaba a mp.info.3
        # (= "Firma electrónica" · medida equivocada).
        applies_to_categories=("MEDIA", "ALTA"),
        detector=detect_unencrypted_storage,
    ),
    GapRule(
        rule_id="rule_public_buckets",
        ens_measure_code="mp.s.2",
        applies_to_categories=("BASICA", "MEDIA", "ALTA"),
        detector=detect_public_buckets,
    ),
    GapRule(
        rule_id="rule_logging_disabled",
        ens_measure_code="op.exp.8",
        applies_to_categories=("MEDIA", "ALTA"),
        detector=detect_logging_disabled,
    ),
    GapRule(
        rule_id="rule_log_retention_insufficient",
        ens_measure_code="op.exp.8",
        applies_to_categories=("MEDIA", "ALTA"),
        detector=detect_log_retention_insufficient,
    ),
    GapRule(
        rule_id="rule_ntp_not_synced",
        ens_measure_code="op.exp.8",
        applies_to_categories=("MEDIA", "ALTA"),
        detector=detect_ntp_not_synced,
    ),
    GapRule(
        rule_id="rule_no_backup",
        ens_measure_code="mp.info.6",
        applies_to_categories=("MEDIA", "ALTA"),
        detector=detect_no_backup_strategy,
    ),
    GapRule(
        rule_id="rule_org1_documental",
        ens_measure_code="org.1",
        applies_to_categories=("BASICA", "MEDIA", "ALTA"),
        detector=detect_documental_policy_missing,
    ),
)


def rules_for_category(category: str | None) -> tuple[GapRule, ...]:
    """Filtra reglas aplicables a la categoría ENS (B/M/A · normaliza)."""
    if not category:
        return ()
    cat_upper = category.upper()
    if cat_upper not in {"BASICA", "MEDIA", "ALTA"}:
        return ()
    return tuple(
        r for r in RULE_CATALOG if cat_upper in r.applies_to_categories
    )


def list_supported_measures() -> list[str]:
    """Lista de ens_measure_code soportadas por el engine (para UI / docs)."""
    return sorted({r.ens_measure_code for r in RULE_CATALOG})


# ==================================================================
# Provider agent guidance (Sesión 3B-2B.7 Ejecutable 4 Phase 7.1.1)
# ==================================================================
# Cada provider declara qué ENS measures puede investigar empirical.
# UI cliente onboarding usa este map para explicar "qué te diagnostica
# conectar X provider". NO restrictivo · solo informativo + R30 admin tutor.


CONNECTOR_PROVIDER_ENS_GUIDANCE: dict[str, dict[str, Any]] = {
    "microsoft_365": {
        "display_name": "Microsoft 365 (incluye SharePoint)",
        "measures_detectable": [
            "op.acc.6",   # MFA users (Reports.Read.All)
            "op.acc.2",   # Privileged users (RoleManagement.Read.Directory)
            "op.exp.1",   # Inventory (devices + users + sites)
            "mp.s.2",     # SharePoint sites públicos
            "org.1",      # Política documental (siempre documental)
        ],
        "asset_types_discovered": ["endpoint", "sharepoint_site"],
        "identity_types_discovered": ["user", "group"],
        "scopes_required": [
            "User.Read.All",
            "Group.Read.All",
            "DeviceManagementManagedDevices.Read.All",
            "Sites.Read.All",
            "Reports.Read.All",
            "RoleManagement.Read.Directory",
        ],
        "cliente_friendly_blurb": (
            "Detectamos usuarios sin MFA, administradores con privilegios "
            "excesivos y sitios SharePoint compartidos públicamente."
        ),
    },
    "google_workspace": {
        "display_name": "Google Workspace (incluye Drive)",
        "measures_detectable": [
            "op.acc.6",   # MFA users (isEnrolledIn2Sv)
            "op.acc.2",   # Privileged users (isAdmin)
            "op.exp.1",   # Inventory (devices + users + drives)
            "mp.s.2",     # Shared drives sin restricción dominio
            "org.1",      # Política documental
        ],
        "asset_types_discovered": ["mobile_device", "shared_drive"],
        "identity_types_discovered": ["user", "group"],
        "scopes_required": [
            "admin.directory.user.readonly",
            "admin.directory.group.readonly",
            "admin.directory.device.mobile.readonly",
            "drive.readonly",
        ],
        "cliente_friendly_blurb": (
            "Detectamos usuarios sin verificación en 2 pasos, "
            "administradores con privilegios excesivos y drives compartidos "
            "fuera del dominio."
        ),
    },
    # DEFER providers post-piloto Future-3B-2B-7-EXPANDED:
    # aws · azure · github · gitlab · dropbox_business · cross-provider orchestrator
}


def get_provider_ens_guidance(provider: str) -> dict[str, Any] | None:
    """Retorna agent guidance dict para provider · None si no soportado.

    Usado por:
    - api_cliente.py catalog endpoint (cliente UI explanation)
    - audit reports per-provider section
    - admin tutor R30 onboarding
    """
    return CONNECTOR_PROVIDER_ENS_GUIDANCE.get(provider)
