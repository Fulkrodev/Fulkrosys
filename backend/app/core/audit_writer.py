"""Writer central de ``audit_log`` (R09 · DRY OPS-026).

Unifica el patrón inline ``INSERT INTO audit_log`` que estaba duplicado en >=7
motores (m07 request_api · m_compliance measure_translation_api ·
m_compliance_monitor api · m17 portal_api · m05 api · m19 cliente_continuidad_api
· m_audit_accompaniment service). Todos repetían exactamente las mismas columnas
y el mismo try/except best-effort.

Garantías que respeta (NO las re-implementa · las hereda de la BD):

- **R6 hash-chain inviolable**: este writer SOLO hace INSERT. El trigger BD
  ``fn_audit_log_hash_chain`` (migración ``d4f8b2a90001``) calcula ``seq``,
  ``hash_prev`` y ``hash_current = sha256(prev || campos)`` BEFORE INSERT, bajo
  ``pg_advisory_xact_lock(hashtext('audit_log_chain'))`` para serializar la
  cadena. Por eso el writer NUNCA setea esas columnas (igual que todos los
  call-sites previos). ``fn_audit_log_immutable`` rechaza UPDATE/DELETE.

- **Sub-atom 5.A · aislamiento 3-way OR**: ``project_id`` + ``client_id`` son
  opcionales. La policy ``audit_log_isolation`` (migración ``audit_log_rls_001``)
  filtra ``project_id = current_project_id() OR client_id = current_client_id()
  OR (project_id IS NULL AND client_id IS NULL)``. Una fila system-level pasa
  AMBOS como ``None`` → cae en la rama NULL+NULL (audit operacional genérico,
  sin PII tenant-bound). Una fila de tenant DEBE pasar ``project_id`` (y
  ``client_id`` si aplica) para quedar aislada.

  IMPORTANTE: la rama NULL+NULL es deliberadamente la ÚNICA exención permisiva.
  El bypass de admin/owner NO va por un ``OR ... IS NULL`` en la policy: va por
  ROL — ``fulkro_app_bypassrls`` y ``fulkro_migrate`` tienen ``BYPASSRLS``,
  mientras que el rol runtime del pool cliente ``fulkro_app`` es
  ``NOSUPERUSER NOBYPASSRLS`` y SÍ queda sujeto a la policy.

EXENCIÓN RLS DOCUMENTADA (veraz · R09.a):
  La tabla ``llm_interaction_log`` (log de coste/observabilidad LLM) está
  EXENTA de RLS DE FORMA DELIBERADA. Confirmado en 3 migraciones
  (``33cef115cdf5`` la excluye como "cross-tenant audit operacional";
  ``sane_mb9_rls_focused_002`` y ``sane_polish_rls_email_log_001`` la difieren
  como "admin-only · 0 portal cliente exposure") y empíricamente en BD
  (relrowsecurity=f · 0 policies). Sólo la lee Marcos (admin · require_owner);
  NO existe endpoint de portal cliente que la alcance, así que no hay vía de
  fuga cross-tenant. Este writer NO toca ``llm_interaction_log``: escribe
  exclusivamente en ``audit_log`` (que SÍ está RLS-protegida).

Transaccionalidad: hace ``db.flush()`` (NO ``commit``) para que el trigger de
hash-chain dispare dentro de la misma transacción del endpoint, respetando el
contrato "get_db no auto-commitea" (el endpoint es quien commitea). El emit es
best-effort: si falla, se loggea pero NO rompe la mutación primaria (el side
effect de auditoría nunca debe tumbar la operación de negocio).
"""
from __future__ import annotations

import json
import logging
import uuid
from typing import Any, Optional, Union

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Mismo orden de columnas que el patrón canónico inline previo. ``id`` lo genera
# ``gen_random_uuid()``; ``seq``/``hash_prev``/``hash_current`` los pone el
# trigger BD (R6). ``timestamp`` = now() (el trigger lo incluye en el payload
# del hash, por eso debe quedar fijo en el INSERT, no recalculado después).
_INSERT_SQL = text(
    "INSERT INTO audit_log "
    "(id, tabla, registro_id, accion, usuario, "
    "project_id, client_id, payload_old, payload_new, timestamp) "
    "VALUES (gen_random_uuid(), :tabla, :rid, :accion, :usuario, "
    "CAST(:pid AS uuid), CAST(:cid AS uuid), "
    "CAST(:payload_old AS jsonb), CAST(:payload_new AS jsonb), now())"
)

_UuidLike = Union[str, uuid.UUID, None]


def _coerce_uuid(value: _UuidLike) -> Optional[str]:
    """Normaliza UUID/str/None → str | None (parámetro CAST(... AS uuid))."""
    if value is None:
        return None
    return str(value)


def _coerce_jsonb(value: Optional[dict[str, Any]]) -> Optional[str]:
    """dict → texto JSON serializable | None (parámetro CAST(... AS jsonb))."""
    if value is None:
        return None
    return json.dumps(value, default=str)


async def emit_audit_log(
    db: AsyncSession,
    *,
    tabla: str,
    registro_id: _UuidLike,
    accion: str,
    project_id: _UuidLike = None,
    client_id: _UuidLike = None,
    payload_old: Optional[dict[str, Any]] = None,
    payload_new: Optional[dict[str, Any]] = None,
    usuario: str = "system",
) -> None:
    """Inserta una fila en ``audit_log`` (writer central · DRY).

    Args:
        db: sesión async (el commit lo hace el endpoint · aquí sólo flush).
        tabla: nombre lógico de la tabla/dominio auditado (ej. 'evidence_requests').
        registro_id: UUID del registro afectado (o sintético para eventos sin
            fila propia, ej. ``str(project_id)``). NOT NULL en el esquema.
        accion: verbo/evento canónico (ej. 'cliente.plan.viewed', 'signature.signed').
        project_id: tenant scoping · ``None`` ⇒ fila system-level (rama NULL+NULL).
        client_id: tenant scoping · idem.
        payload_old / payload_new: diff JSON (UPDATE) o sólo ``payload_new`` (CREATE).
        usuario: actor (truncado a 255 · columna VARCHAR(255)).

    R6: NO setea seq/hash_prev/hash_current (los pone el trigger BD).
    5.A: project_id/client_id ambos None ⇒ visible bajo policy NULL+NULL.
    Best-effort: nunca propaga la excepción (loggea y sigue).
    """
    if registro_id is None:
        # registro_id es NOT NULL · sintetizamos uno para no romper el INSERT.
        registro_id = uuid.uuid4()
    try:
        # SAVEPOINT: si el INSERT/flush del audit falla (constraint, trigger hash,
        # etc.) el rollback se limita al savepoint y NO envenena la transacción
        # principal → la mutación primaria sigue pudiendo commitear (contrato
        # best-effort de verdad). Las filas que SÍ insertan se confirman con el
        # commit del endpoint, preservando la cadena hash R6.
        async with db.begin_nested():
            await db.execute(
                _INSERT_SQL,
                {
                    "tabla": tabla[:100],
                    "rid": str(registro_id),
                    "accion": accion[:60],
                    "usuario": (usuario or "system")[:255],
                    "pid": _coerce_uuid(project_id),
                    "cid": _coerce_uuid(client_id),
                    "payload_old": _coerce_jsonb(payload_old),
                    "payload_new": _coerce_jsonb(payload_new),
                },
            )
            # flush ⇒ dispara fn_audit_log_hash_chain en esta misma transacción.
            await db.flush()
    except Exception:  # pragma: no cover · best-effort · no rompe la mutación
        logger.exception(
            "emit_audit_log fallo (best-effort) · tabla=%s accion=%s rid=%s",
            tabla, accion, registro_id,
        )
