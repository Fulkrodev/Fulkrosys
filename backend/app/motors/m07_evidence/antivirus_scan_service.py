"""Antivirus scan service · SAN-E v3.MB-6 atom 6 · Gap A27 ENS op.exp.6.

Async ClamAV scan workflow para uploads cliente (Q4 B scope):
  evidence row created → scan_status='scanning' (server default)
    → Celery scan_evidence_file_task picks up
    → clamd InstreamScan via TCP 3310 (Q1 A docker-compose sidecar)
    → branch:
       * clean → scan_status='clean'
       * INFECTED → scan_status='quarantined' (Q2 B quarantine pattern):
                    + move file a var/quarantine/{project_id}/{evidence_id}{ext}
                    + alert_queue category='antivirus_infected'
       * error/timeout → scan_status='error' + alert_queue 'antivirus_scan_error'

Admin actions (Q2 B false-positive recoverable):
- admin_release_quarantined(evidence_id, admin_user_id)
  -> move file BACK to original path + scan_status='clean'
- admin_permanent_delete_quarantined(evidence_id, admin_user_id)
  -> delete file + soft-delete evidence row

Q7 NO MixinA aqui · scan_status es tecnico antivirus (NO review decisional).
"""
from __future__ import annotations

import logging
import os
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════
# Constants
# ════════════════════════════════════════════════════════════════════

SCAN_STATUS_VALUES = (
    "clean", "scanning", "infected", "error", "quarantined",
)

# clamd network defaults (override via env in production).
DEFAULT_CLAMD_HOST = os.environ.get("CLAMD_HOST", "localhost")
DEFAULT_CLAMD_PORT = int(os.environ.get("CLAMD_PORT", "3310"))
DEFAULT_CLAMD_TIMEOUT = float(os.environ.get("CLAMD_TIMEOUT_SECONDS", "25"))

# Storage roots
_REPO_ROOT = Path(__file__).resolve().parents[4]
_EVIDENCES_DIR = _REPO_ROOT / "var" / "evidences"
_QUARANTINE_DIR = _REPO_ROOT / "var" / "quarantine"

# FIX P2-7: retención WORM (Object Lock COMPLIANCE) de la evidencia LIMPIA ·
# inmutable para ENAC (Art. 24 ENS · R6). Env-configurable: prod 7 años (2555d),
# dev puede bajarlo. La evidencia se archiva al bucket WORM SOLO tras pasar el
# antivirus (clean) → nunca se escribe malware en el almacén inmutable. La
# durabilidad (sobrevivir reinicios) ya la garantiza el volumen vardata (P0-1);
# el WORM añade la inmutabilidad de almacenamiento.
_WORM_RETENTION_DAYS = int(os.environ.get("FULKRO_WORM_RETENTION_DAYS", "2555"))


async def _archive_clean_evidence_to_worm(
    file_bytes: bytes, project_id, evidence_id, fichero_path: str,
) -> str | None:
    """Archiva la evidencia LIMPIA al bucket WORM inmutable. Best-effort.

    Devuelve la URI ``minio://...`` del objeto WORM, o ``None`` si MinIO/WORM no
    está disponible (dev). NO bloquea el flujo de escaneo.
    """
    try:
        from backend.app.core.storage.minio_client import (
            BUCKET_EVIDENCE_WORM,
            put_object,
        )
        ext = Path(fichero_path).suffix if fichero_path else ""
        key = f"{project_id}/{evidence_id}{ext}"
        res = put_object(
            BUCKET_EVIDENCE_WORM, key, file_bytes,
            worm_retention_days=_WORM_RETENTION_DAYS,
        )
        return f"minio://{res.bucket}/{res.key}"
    except Exception as exc:
        logger.warning(
            "WORM archival evidencia %s falló (best-effort): %s",
            evidence_id, exc,
        )
        return None


# ════════════════════════════════════════════════════════════════════
# Exceptions
# ════════════════════════════════════════════════════════════════════


class AntivirusScanError(Exception):
    """Base error antivirus scan service."""


class EvidenceNotFoundError(AntivirusScanError):
    """Evidence row no existe o deleted."""


class ClamdConnectionError(AntivirusScanError):
    """clamd daemon no accesible (down/timeout)."""


class InvalidQuarantineActionError(AntivirusScanError):
    """Acción admin invalida (estado no quarantined)."""


# ════════════════════════════════════════════════════════════════════
# Scan result dataclass-like
# ════════════════════════════════════════════════════════════════════


class ScanResult:
    """Result of a single clamd scan."""

    def __init__(
        self,
        status: Literal["clean", "infected", "error"],
        virus_name: str | None = None,
        engine_version: str | None = None,
        signature_db_version: str | None = None,
        duration_ms: int = 0,
        error_msg: str | None = None,
    ) -> None:
        self.status = status
        self.virus_name = virus_name
        self.engine_version = engine_version
        self.signature_db_version = signature_db_version
        self.duration_ms = duration_ms
        self.error_msg = error_msg

    def to_jsonb(self) -> dict:
        return {
            "status": self.status,
            "virus_name": self.virus_name,
            "engine_version": self.engine_version,
            "signature_db_version": self.signature_db_version,
            "duration_ms": self.duration_ms,
            "error_msg": self.error_msg,
        }


# ════════════════════════════════════════════════════════════════════
# clamd client + scan primitives
# ════════════════════════════════════════════════════════════════════


def get_clamd_client(
    host: str = DEFAULT_CLAMD_HOST,
    port: int = DEFAULT_CLAMD_PORT,
    timeout: float = DEFAULT_CLAMD_TIMEOUT,
):
    """Returns clamd.ClamdNetworkSocket · TCP 3310 internal.

    Lazy import para que el módulo sea importable aunque clamd library NO
    esté instalado (tests + dev sin clamd usan mocks).
    """
    import clamd
    return clamd.ClamdNetworkSocket(host=host, port=port, timeout=timeout)


def scan_bytes(
    file_bytes: bytes,
    clamd_client=None,
) -> ScanResult:
    """Scan in-memory bytes via clamd INSTREAM · returns ScanResult.

    Raises ClamdConnectionError si clamd unreachable.
    """
    import io
    started_ms = time.perf_counter()
    client = clamd_client or get_clamd_client()

    engine_version = None
    try:
        # clamd.version() returns "ClamAV 1.X.Y/<sig_db_version>/<date>"
        version_full = client.version()
        engine_version = version_full.split("/")[0].strip() if version_full else None
    except Exception:
        # version probe optional · NO bloquear scan
        pass

    try:
        result = client.instream(io.BytesIO(file_bytes))
    except Exception as exc:
        raise ClamdConnectionError(
            f"clamd connection failed (host={DEFAULT_CLAMD_HOST}:{DEFAULT_CLAMD_PORT}): {exc}"
        ) from exc

    duration_ms = int((time.perf_counter() - started_ms) * 1000)

    # clamd instream returns {"stream": (verdict, signature_or_None)}
    verdict_tuple = result.get("stream", (None, None))
    verdict = verdict_tuple[0] if verdict_tuple else None
    signature = verdict_tuple[1] if verdict_tuple else None

    if verdict == "OK":
        return ScanResult(
            status="clean",
            engine_version=engine_version,
            duration_ms=duration_ms,
        )
    if verdict == "FOUND":
        return ScanResult(
            status="infected",
            virus_name=signature,
            engine_version=engine_version,
            duration_ms=duration_ms,
        )
    return ScanResult(
        status="error",
        engine_version=engine_version,
        duration_ms=duration_ms,
        error_msg=f"Unknown verdict from clamd: {verdict!r}",
    )


# ════════════════════════════════════════════════════════════════════
# Evidence scan orchestration
# ════════════════════════════════════════════════════════════════════


async def _fetch_evidence_row(
    db: AsyncSession, evidence_id: uuid.UUID,
) -> dict:
    row = await db.execute(
        text(
            "SELECT id, project_id, fichero_path, scan_status, deleted_at "
            "FROM evidence WHERE id = :eid"
        ),
        {"eid": str(evidence_id)},
    )
    hit = row.first()
    if hit is None:
        raise EvidenceNotFoundError(f"Evidence {evidence_id} no encontrada")
    if hit[4] is not None:
        raise EvidenceNotFoundError(f"Evidence {evidence_id} deleted")
    return {
        "id": hit[0],
        "project_id": hit[1],
        "fichero_path": hit[2],
        "scan_status": hit[3],
    }


def _abs_path(relative_path: str | None) -> Path | None:
    if not relative_path:
        return None
    p = Path(relative_path)
    if p.is_absolute():
        return p
    return _REPO_ROOT / relative_path


async def mark_scan_started(
    db: AsyncSession, evidence_id: uuid.UUID,
) -> None:
    """Pre-scan: mark scan_status='scanning' + scan_started_at."""
    await db.execute(
        text(
            "UPDATE evidence "
            "SET scan_status = 'scanning', scan_started_at = :ts "
            "WHERE id = :eid"
        ),
        {"eid": str(evidence_id), "ts": datetime.now(UTC)},
    )
    await db.flush()


async def mark_scan_clean(
    db: AsyncSession, evidence_id: uuid.UUID, result: ScanResult,
    worm_uri: str | None = None,
) -> None:
    payload = result.to_jsonb()
    if worm_uri:
        payload["worm_uri"] = worm_uri  # FIX P2-7: copia inmutable WORM
    await db.execute(
        text(
            "UPDATE evidence SET "
            "scan_status = 'clean', "
            "scan_completed_at = :ts, "
            "scan_engine_version = :ver, "
            "scan_result_jsonb = CAST(:res AS jsonb) "
            "WHERE id = :eid"
        ),
        {
            "eid": str(evidence_id),
            "ts": datetime.now(UTC),
            "ver": result.engine_version,
            "res": _jsonify(payload),
        },
    )
    await db.flush()


async def mark_scan_quarantined(
    db: AsyncSession,
    evidence_id: uuid.UUID,
    project_id: uuid.UUID,
    fichero_path: str,
    result: ScanResult,
) -> str:
    """Move file → quarantine dir + scan_status='quarantined' + alert_queue.

    Returns new quarantine relative path.
    """
    src_abs = _abs_path(fichero_path)
    if src_abs is None or not src_abs.exists():
        # File desaparecido: marcar error en vez de quarantined.
        await _mark_status_error(
            db, evidence_id, result, "Source file vanished pre-quarantine",
        )
        return ""

    quarantine_dir = _QUARANTINE_DIR / str(project_id)
    quarantine_dir.mkdir(parents=True, exist_ok=True)
    dest = quarantine_dir / src_abs.name
    src_abs.rename(dest)

    quarantine_relative = (
        f"var/quarantine/{project_id}/{dest.name}"
    )

    # Update evidence row · keep fichero_path apuntando a quarantine.
    await db.execute(
        text(
            "UPDATE evidence SET "
            "scan_status = 'quarantined', "
            "scan_completed_at = :ts, "
            "scan_engine_version = :ver, "
            "scan_result_jsonb = CAST(:res AS jsonb), "
            "fichero_path = :path, "
            "vigente = FALSE "
            "WHERE id = :eid"
        ),
        {
            "eid": str(evidence_id),
            "ts": datetime.now(UTC),
            "ver": result.engine_version,
            "res": _jsonify(result.to_jsonb()),
            "path": quarantine_relative,
        },
    )
    await _emit_alert(
        db, project_id, evidence_id,
        category="antivirus_infected",
        virus_name=result.virus_name,
    )
    await db.flush()

    # MB-6 atom 8 · admin notify post-quarantine (Orchestrator email)
    try:
        from backend.app.notifications.post_signoff_hooks import (
            post_event_evidence_quarantined,
        )
        await post_event_evidence_quarantined(
            db,
            evidence_id=evidence_id,
            project_id=project_id,
            filename=src_abs.name,
            virus_name=result.virus_name,
            scanned_at=datetime.now(UTC),
        )
    except Exception:
        pass  # silent fail

    return quarantine_relative


async def mark_scan_error(
    db: AsyncSession,
    evidence_id: uuid.UUID,
    project_id: uuid.UUID,
    error_msg: str,
) -> None:
    result = ScanResult(status="error", error_msg=error_msg)
    await _mark_status_error(db, evidence_id, result, error_msg)
    await _emit_alert(
        db, project_id, evidence_id,
        category="antivirus_scan_error",
        virus_name=None,
        error_msg=error_msg,
    )
    await db.flush()


async def _mark_status_error(
    db: AsyncSession,
    evidence_id: uuid.UUID,
    result: ScanResult,
    error_msg: str,
) -> None:
    await db.execute(
        text(
            "UPDATE evidence SET "
            "scan_status = 'error', "
            "scan_completed_at = :ts, "
            "scan_engine_version = :ver, "
            "scan_result_jsonb = CAST(:res AS jsonb) "
            "WHERE id = :eid"
        ),
        {
            "eid": str(evidence_id),
            "ts": datetime.now(UTC),
            "ver": result.engine_version,
            "res": _jsonify({**result.to_jsonb(), "error_msg": error_msg}),
        },
    )


async def _emit_alert(
    db: AsyncSession,
    project_id: uuid.UUID,
    evidence_id: uuid.UUID,
    category: str,
    virus_name: str | None = None,
    error_msg: str | None = None,
) -> None:
    """Insert alert_queue row · admin notification."""
    severity = "critical" if category == "antivirus_infected" else "warning"
    if category == "antivirus_infected":
        title = f"Archivo infectado en cuarentena (virus: {virus_name or 'unknown'})"
    else:
        title = "Error escaneo antivirus"
    metadata = {
        "evidence_id": str(evidence_id),
        "virus_name": virus_name,
        "error_msg": error_msg,
    }
    await db.execute(
        text(
            "INSERT INTO alert_queue (id, project_id, severity, category, "
            "title, description, triggered_by, triggered_at, metadata_jsonb) "
            "VALUES (:id, :pid, :sev, :cat, :title, :desc, "
            "'m07_antivirus_scan_service', now(), CAST(:meta AS jsonb))"
        ),
        {
            "id": str(uuid.uuid4()),
            "pid": str(project_id),
            "sev": severity,
            "cat": category,
            "title": title,
            "desc": error_msg or virus_name or "",
            "meta": _jsonify(metadata),
        },
    )


async def scan_evidence(
    db: AsyncSession,
    evidence_id: uuid.UUID,
    *,
    clamd_client=None,
) -> str:
    """Full scan workflow async · returns terminal scan_status.

    Pre-condition: evidence row exists + has fichero_path.
    Side effects: file may be moved to quarantine · alert_queue may receive row.
    """
    row = await _fetch_evidence_row(db, evidence_id)
    project_id = row["project_id"]
    fichero_path = row["fichero_path"]

    await mark_scan_started(db, evidence_id)

    src_abs = _abs_path(fichero_path)
    if src_abs is None or not src_abs.exists():
        await mark_scan_error(
            db, evidence_id, project_id,
            f"Source file not found: {fichero_path}",
        )
        return "error"

    try:
        file_bytes = src_abs.read_bytes()
    except OSError as exc:
        await mark_scan_error(
            db, evidence_id, project_id, f"Read failed: {exc}",
        )
        return "error"

    try:
        result = scan_bytes(file_bytes, clamd_client=clamd_client)
    except ClamdConnectionError as exc:
        await mark_scan_error(
            db, evidence_id, project_id, str(exc),
        )
        return "error"

    if result.status == "clean":
        # FIX P2-7: archivar la evidencia LIMPIA al bucket WORM inmutable
        # (best-effort · no bloquea · solo tras pasar el antivirus → NUNCA
        # malware en WORM). La durabilidad ya la da el volumen vardata (P0-1).
        worm_uri = await _archive_clean_evidence_to_worm(
            file_bytes, project_id, evidence_id, fichero_path,
        )
        await mark_scan_clean(db, evidence_id, result, worm_uri=worm_uri)
        return "clean"
    if result.status == "infected":
        await mark_scan_quarantined(
            db, evidence_id, project_id, fichero_path, result,
        )
        return "quarantined"
    # status == 'error'
    await mark_scan_error(
        db, evidence_id, project_id,
        result.error_msg or "Unknown clamd error",
    )
    return "error"


# ════════════════════════════════════════════════════════════════════
# Admin quarantine workflow (Q2 B false-positive recoverable)
# ════════════════════════════════════════════════════════════════════


async def admin_release_quarantined(
    db: AsyncSession,
    evidence_id: uuid.UUID,
    admin_user_id: uuid.UUID,
) -> None:
    """Move file BACK from quarantine → original path + scan_status='clean'.

    Justified false-positive · admin manual override · audit log entry.
    """
    # FIX(RLS): op admin cross-cliente sobre evidence (RLS FORCE) · sin bypass el
    # UPDATE afectaba 0 filas (no-op silencioso) en prod.
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    row = await db.execute(
        text(
            "SELECT id, project_id, fichero_path, scan_status, "
            "fichero_nombre_original, scan_result_jsonb "
            "FROM evidence WHERE id = :eid AND deleted_at IS NULL"
        ),
        {"eid": str(evidence_id)},
    )
    hit = row.first()
    if hit is None:
        raise EvidenceNotFoundError(f"Evidence {evidence_id} no encontrada")
    if hit[3] != "quarantined":
        raise InvalidQuarantineActionError(
            f"Evidence status='{hit[3]}' · esperado 'quarantined' para release"
        )

    project_id = hit[1]
    current_quarantine_path = hit[2]
    quarantine_abs = _abs_path(current_quarantine_path)
    if quarantine_abs is None or not quarantine_abs.exists():
        raise InvalidQuarantineActionError(
            f"Quarantine file not found: {current_quarantine_path}"
        )

    # Restore destination · var/evidences/<project_id>/<filename>
    restore_dir = _EVIDENCES_DIR / str(project_id)
    restore_dir.mkdir(parents=True, exist_ok=True)
    restore_abs = restore_dir / quarantine_abs.name
    quarantine_abs.rename(restore_abs)
    restore_relative = f"var/evidences/{project_id}/{restore_abs.name}"

    # Merge release info en scan_result_jsonb existing.
    await db.execute(
        text(
            "UPDATE evidence SET "
            "scan_status = 'clean', "
            "fichero_path = :path, "
            "vigente = TRUE, "
            "scan_result_jsonb = COALESCE(scan_result_jsonb, '{}'::jsonb) || "
            "CAST(:override AS jsonb) "
            "WHERE id = :eid"
        ),
        {
            "eid": str(evidence_id),
            "path": restore_relative,
            "override": _jsonify({
                "admin_override": "released_from_quarantine",
                "admin_user_id": str(admin_user_id),
                "override_at": datetime.now(UTC).isoformat(),
            }),
        },
    )
    await db.flush()


async def admin_permanent_delete_quarantined(
    db: AsyncSession,
    evidence_id: uuid.UUID,
    admin_user_id: uuid.UUID,
) -> None:
    """Delete quarantined file from disk + soft-delete evidence row."""
    # FIX(RLS): op admin cross-cliente sobre evidence (RLS FORCE) · sin bypass el
    # SELECT/UPDATE no veía la fila en prod (no-op silencioso).
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    row = await db.execute(
        text(
            "SELECT project_id, fichero_path, scan_status "
            "FROM evidence WHERE id = :eid AND deleted_at IS NULL"
        ),
        {"eid": str(evidence_id)},
    )
    hit = row.first()
    if hit is None:
        raise EvidenceNotFoundError(f"Evidence {evidence_id} no encontrada")
    if hit[2] != "quarantined":
        raise InvalidQuarantineActionError(
            f"Evidence status='{hit[2]}' · esperado 'quarantined' para permanent-delete"
        )

    quarantine_abs = _abs_path(hit[1])
    if quarantine_abs and quarantine_abs.exists():
        try:
            quarantine_abs.unlink()
        except OSError:
            pass  # Best-effort · soft-delete row procede de todos modos

    await db.execute(
        text(
            "UPDATE evidence SET "
            "deleted_at = now(), "
            "vigente = FALSE, "
            "scan_result_jsonb = COALESCE(scan_result_jsonb, '{}'::jsonb) || "
            "CAST(:override AS jsonb) "
            "WHERE id = :eid"
        ),
        {
            "eid": str(evidence_id),
            "override": _jsonify({
                "admin_override": "permanent_delete_from_quarantine",
                "admin_user_id": str(admin_user_id),
                "override_at": datetime.now(UTC).isoformat(),
            }),
        },
    )
    await db.flush()


async def list_quarantined(
    db: AsyncSession,
    project_id: uuid.UUID | None = None,
) -> list[dict]:
    """List quarantined evidences · optional project_id filter."""
    # FIX(RLS): cola de cuarentena admin cross-cliente · evidence tiene RLS FORCE
    # y la ruta admin (require_owner) NO fija tenant context → vacío en prod.
    # Elevar a fulkro_app_bypassrls (como m07_evidence/request_api.py:199).
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    sql = (
        "SELECT id, project_id, fichero_nombre_original, "
        "scan_completed_at, scan_result_jsonb "
        "FROM evidence "
        "WHERE scan_status = 'quarantined' AND deleted_at IS NULL"
    )
    params: dict = {}
    if project_id is not None:
        sql += " AND project_id = :pid"
        params["pid"] = str(project_id)
    sql += " ORDER BY scan_completed_at DESC NULLS LAST"

    row = await db.execute(text(sql), params)
    out: list[dict] = []
    for r in row:
        out.append({
            "id": r[0],
            "project_id": r[1],
            "fichero_nombre_original": r[2],
            "scan_completed_at": r[3],
            "scan_result_jsonb": r[4],
        })
    return out


# ════════════════════════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════════════════════════


def _jsonify(d: dict) -> str:
    import json
    return json.dumps(d, default=str)


# EICAR universal test signature (CCN-STIC + Cisco-Talos golden test).
# https://www.eicar.org/?page_id=3950 · NO real virus · detection guarantee.
EICAR_TEST_STRING = (
    "X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
)
