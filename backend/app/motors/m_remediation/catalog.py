"""Catálogo de acciones de remediación · ADR-055.

CÓDIGO determinista (NO BD · NO LLM · R1 inviolable). Cada acción se clasifica
estáticamente por nivel de riesgo. El clasificador de `policy.py` lee de aquí:
NUNCA infiere el tier dinámicamente.

Cada `RemediationActionSpec` declara:
  - tier               : SAFE_AUTO | GUARDED | BLOCKED
  - reversible         : si existe rollback determinista
  - provider           : proveedor cloud (o 'host' para agente on-prem)
  - ens_measures       : medidas Anexo II RD 311/2022 que cierra
  - target_kind        : tipo de recurso sobre el que actúa (verify/snapshot)
  - desired_assertion  : clave del estado que `verify` debe confirmar tras apply
  - blast_radius_max    : nº máx de recursos que puede tocar un job sin confirmación
                          extra (guard · None = sin tope · 1 = unitario)
  - cliente_blurb      : explicación R29 cliente-friendly (sin jerga admin)

El `action_type` es la clave canónica usada por jobs, writers y playbooks.
Añadir una acción nueva = añadir una entrada aquí (single source of truth).
"""
from __future__ import annotations

import enum
from dataclasses import dataclass, field


class RemediationTier(str, enum.Enum):
    """Nivel de riesgo determinista de una acción (ADR-055)."""

    SAFE_AUTO = "safe_auto"
    """Reversible · sin impacto acceso/disponibilidad → se aplica solo."""

    GUARDED = "guarded"
    """Puede afectar acceso → autorización previa + snapshot + auto-rollback."""

    BLOCKED = "blocked"
    """Destructivo/irreversible → nunca auto · solo plan (humano externo)."""


@dataclass(frozen=True)
class RemediationActionSpec:
    """Especificación inmutable de una acción de remediación."""

    action_type: str
    tier: RemediationTier
    reversible: bool
    provider: str  # microsoft_365 · azure · aws · google_workspace · github · host
    title_es: str
    ens_measures: tuple[str, ...]
    target_kind: str
    desired_assertion: str
    cliente_blurb: str
    blast_radius_max: int | None = None
    requires_write_scopes: tuple[str, ...] = field(default_factory=tuple)


# ─────────────────────────────────────────────────────────────────────────
# Catálogo canónico. Clave = action_type.
#
# Criterio de tiering (Marcos · ADR-055):
#   SAFE_AUTO  → activar protección que NO quita acceso a nadie (cifrado, logs,
#                versionado, bloquear-público, forzar-MFA, política-contraseñas,
#                hardening que no corta sesiones vivas).
#   GUARDED    → toca credenciales/políticas que PODRÍAN cortar acceso (rotar
#                clave, desactivar protocolo legacy, endurecer IAM).
#   BLOCKED    → borra/recrea recursos o cambia topología de red (irreversible
#                o de alto blast radius).
# ─────────────────────────────────────────────────────────────────────────

ACTION_CATALOG: dict[str, RemediationActionSpec] = {
    # ── Cloud · almacenamiento ──────────────────────────────────────────
    "enable_bucket_encryption": RemediationActionSpec(
        action_type="enable_bucket_encryption",
        tier=RemediationTier.SAFE_AUTO,
        reversible=True,
        provider="aws",
        title_es="Activar cifrado en reposo del bucket",
        ens_measures=("mp.info.3", "mp.s.8"),
        target_kind="asset.storage_bucket",
        desired_assertion="encryption_enabled",
        cliente_blurb=(
            "Activamos el cifrado de tus archivos en la nube. No cambia nada "
            "para ti · solo los protege si alguien accediera al disco."
        ),
        blast_radius_max=1,
        requires_write_scopes=("s3:PutEncryptionConfiguration",),
    ),
    "block_public_access": RemediationActionSpec(
        action_type="block_public_access",
        tier=RemediationTier.SAFE_AUTO,
        reversible=True,
        provider="aws",
        title_es="Bloquear acceso público del bucket",
        ens_measures=("mp.s.2", "op.acc.4"),
        target_kind="asset.storage_bucket",
        desired_assertion="public_access_blocked",
        cliente_blurb=(
            "Cerramos el acceso público a un almacén que estaba abierto a "
            "internet. Tu equipo sigue accediendo igual."
        ),
        blast_radius_max=1,
        requires_write_scopes=("s3:PutBucketPublicAccessBlock",),
    ),
    "enable_bucket_versioning": RemediationActionSpec(
        action_type="enable_bucket_versioning",
        tier=RemediationTier.SAFE_AUTO,
        reversible=True,
        provider="aws",
        title_es="Activar versionado del bucket",
        ens_measures=("mp.info.6", "op.cont.2"),
        target_kind="asset.storage_bucket",
        desired_assertion="versioning_enabled",
        cliente_blurb=(
            "Activamos el histórico de versiones · si algo se borra o cambia "
            "por error, se puede recuperar."
        ),
        blast_radius_max=1,
        requires_write_scopes=("s3:PutBucketVersioning",),
    ),
    # ── Cloud · auditoría/logs ──────────────────────────────────────────
    "enable_audit_logging": RemediationActionSpec(
        action_type="enable_audit_logging",
        tier=RemediationTier.SAFE_AUTO,
        reversible=True,
        provider="aws",
        title_es="Activar registro de auditoría (trail)",
        ens_measures=("op.exp.8", "op.mon.1"),
        target_kind="account",
        desired_assertion="audit_log_enabled",
        cliente_blurb=(
            "Encendemos el registro de actividad · queda traza de quién hace "
            "qué (lo exige el ENS y ayuda en la certificación)."
        ),
        requires_write_scopes=("cloudtrail:CreateTrail",),
    ),
    # ── Cloud · identidad ───────────────────────────────────────────────
    "enforce_password_policy": RemediationActionSpec(
        action_type="enforce_password_policy",
        tier=RemediationTier.SAFE_AUTO,
        reversible=True,
        provider="aws",
        title_es="Endurecer política de contraseñas",
        ens_measures=("op.acc.5", "op.acc.6"),
        target_kind="account",
        desired_assertion="password_policy_strong",
        cliente_blurb=(
            "Subimos los requisitos de contraseña (longitud, caducidad). No "
            "expulsa a nadie · aplica en el próximo cambio."
        ),
        requires_write_scopes=("iam:UpdateAccountPasswordPolicy",),
    ),
    "require_mfa_conditional_access": RemediationActionSpec(
        action_type="require_mfa_conditional_access",
        tier=RemediationTier.SAFE_AUTO,
        reversible=True,
        provider="microsoft_365",
        title_es="Exigir MFA por acceso condicional",
        ens_measures=("op.acc.6",),
        target_kind="tenant",
        desired_assertion="mfa_required",
        cliente_blurb=(
            "Activamos el segundo factor (MFA) para todos · es la medida que "
            "más puntúa en la certificación. Cada usuario lo registra una vez."
        ),
        # Forzar MFA puede dejar fuera a cuentas de servicio sin segundo factor:
        # SAFE en modo report-only; el modo enforce real se ofrece como GUARDED
        # vía require_mfa_enforce. Aquí dejamos la directiva en report-only.
        requires_write_scopes=("Policy.ReadWrite.ConditionalAccess",),
    ),
    # ── Cloud · GUARDED (autorización previa) ───────────────────────────
    "require_mfa_enforce": RemediationActionSpec(
        action_type="require_mfa_enforce",
        tier=RemediationTier.GUARDED,
        reversible=True,
        provider="microsoft_365",
        title_es="Forzar MFA en modo bloqueo (enforce)",
        ens_measures=("op.acc.6",),
        target_kind="tenant",
        desired_assertion="mfa_enforced",
        cliente_blurb=(
            "Pasamos el MFA a obligatorio de verdad · quien no lo tenga "
            "registrado no podrá entrar hasta configurarlo. Lo coordinamos "
            "contigo antes de aplicarlo."
        ),
        requires_write_scopes=("Policy.ReadWrite.ConditionalAccess",),
    ),
    "rotate_access_key": RemediationActionSpec(
        action_type="rotate_access_key",
        tier=RemediationTier.GUARDED,
        reversible=True,
        provider="aws",
        title_es="Rotar clave de acceso antigua",
        ens_measures=("op.acc.5", "mp.s.8"),
        target_kind="identity.access_key",
        desired_assertion="key_age_ok",
        cliente_blurb=(
            "Cambiamos una clave de acceso caducada por una nueva. Puede "
            "requerir actualizar dónde se use · lo coordinamos antes."
        ),
        blast_radius_max=1,
        requires_write_scopes=("iam:CreateAccessKey", "iam:UpdateAccessKey"),
    ),
    "disable_legacy_protocol": RemediationActionSpec(
        action_type="disable_legacy_protocol",
        tier=RemediationTier.GUARDED,
        reversible=True,
        provider="microsoft_365",
        title_es="Desactivar protocolo de autenticación heredado",
        ens_measures=("op.acc.6", "mp.com.1"),
        target_kind="tenant",
        desired_assertion="legacy_auth_disabled",
        cliente_blurb=(
            "Apagamos métodos de login antiguos e inseguros. Apps muy viejas "
            "podrían necesitar actualizarse · lo revisamos contigo antes."
        ),
        requires_write_scopes=("Policy.ReadWrite.ConditionalAccess",),
    ),
    # ── Cloud · BLOCKED (nunca auto) ────────────────────────────────────
    "delete_public_resource": RemediationActionSpec(
        action_type="delete_public_resource",
        tier=RemediationTier.BLOCKED,
        reversible=False,
        provider="aws",
        title_es="Eliminar recurso expuesto",
        ens_measures=("mp.s.2",),
        target_kind="asset",
        desired_assertion="resource_absent",
        cliente_blurb=(
            "Borrar un recurso es irreversible · esto siempre lo revisa y "
            "ejecuta una persona, nunca de forma automática."
        ),
        blast_radius_max=1,
    ),
    "remove_iam_principal": RemediationActionSpec(
        action_type="remove_iam_principal",
        tier=RemediationTier.BLOCKED,
        reversible=False,
        provider="aws",
        title_es="Eliminar identidad/permiso IAM",
        ens_measures=("op.acc.4",),
        target_kind="identity",
        desired_assertion="principal_absent",
        cliente_blurb=(
            "Quitar usuarios o permisos puede dejar a alguien sin acceso · "
            "esto siempre lo decide y ejecuta una persona."
        ),
        blast_radius_max=1,
    ),
    # ── Host on-prem (agente · Fase 3) ──────────────────────────────────
    "harden_sshd_root_login": RemediationActionSpec(
        action_type="harden_sshd_root_login",
        tier=RemediationTier.SAFE_AUTO,
        reversible=True,
        provider="host",
        title_es="Deshabilitar login root por SSH",
        ens_measures=("op.acc.5", "mp.com.3"),
        target_kind="host.sshd",
        desired_assertion="permit_root_login_no",
        cliente_blurb=(
            "Cerramos el acceso directo del administrador raíz por SSH · se "
            "sigue administrando con cuentas nominales (más seguro y trazable)."
        ),
        blast_radius_max=1,
    ),
    "enable_host_firewall_rule": RemediationActionSpec(
        action_type="enable_host_firewall_rule",
        tier=RemediationTier.SAFE_AUTO,
        reversible=True,
        provider="host",
        title_es="Activar regla de firewall (cerrar puerto expuesto)",
        ens_measures=("mp.com.1", "op.acc.4"),
        target_kind="host.firewall",
        desired_assertion="port_closed",
        cliente_blurb=(
            "Cerramos un puerto que estaba abierto sin necesidad. Los "
            "servicios que usas no se ven afectados."
        ),
        blast_radius_max=1,
    ),
    "apply_package_security_update": RemediationActionSpec(
        action_type="apply_package_security_update",
        tier=RemediationTier.GUARDED,
        reversible=True,
        provider="host",
        title_es="Aplicar actualización de seguridad de paquete",
        ens_measures=("op.exp.4", "op.exp.5"),
        target_kind="host.package",
        desired_assertion="package_patched",
        cliente_blurb=(
            "Instalamos un parche de seguridad. Puede requerir reiniciar un "
            "servicio · lo coordinamos contigo y guardamos copia para revertir."
        ),
        blast_radius_max=1,
    ),
}


def get_action_spec(action_type: str) -> RemediationActionSpec | None:
    """Devuelve la spec de una acción · None si no está catalogada."""
    return ACTION_CATALOG.get(action_type)


def tier_for(action_type: str) -> RemediationTier | None:
    """Tier determinista de una acción · None si no catalogada (fail-closed)."""
    spec = ACTION_CATALOG.get(action_type)
    return spec.tier if spec else None


def actions_for_provider(provider: str) -> list[RemediationActionSpec]:
    """Acciones disponibles para un proveedor dado."""
    return [s for s in ACTION_CATALOG.values() if s.provider == provider]
