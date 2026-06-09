"""Audit log integrity checker · pure functional service.

Sesión 3B-2B.10 Ejecutable 5 Phase 10.1 (2026-05-27).

Wraps existing PostgreSQL function `fn_audit_log_verify_chain` (migration
`d4f8b2a90001_audit_log_hash_chain_trigger.py`) + adds project-scoped variant.

R6 hash chain inviolable preserved:
- audit_log immutability via triggers `tg_audit_log_no_update` + `tg_audit_log_no_delete`
- BEFORE INSERT trigger `tg_audit_log_hash_chain` computes SHA-256 hash chain
- This service does NOT mutate audit_log · read-only verification

Pattern Phase C3 pure functional:
- Accepts db session + project_id (optional · global scan si None)
- NO HTTP coupling · NO ORM coupling
- JSON-serializable return (asdict-friendly)
- Deterministic given same DB state

Reusable consumers:
- SimulacroPreEnacService (Sesión 3B-2B.10 Phase 10.3)
- Future audit drilldown UI (admin Sesión 3B-2B.X)
- Future ENAC handoff portal integrity proof

Note algorithm: SHA-256 hash chain (NO Ed25519 · per audit_log_hash_chain
existing trigger). Ed25519 reside en M05 PDF signing layer (different concern).
"""
from __future__ import annotations

import hashlib
import uuid
from dataclasses import asdict, dataclass
from typing import Optional

from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class IntegrityReport:
    """Audit log hash chain integrity verification report.

    Fields:
        ok: True si all rows verified · False si chain corrupted
        total_rows: count rows verified (filtered si project_id provided)
        first_bad_seq: first row seq where hash mismatch detected · None si ok
        project_id: project scope si filtered · None si global scan
        since_seq: starting seq filter si provided · None si full chain
    """

    ok: bool
    total_rows: int
    first_bad_seq: Optional[int]
    project_id: Optional[str]
    since_seq: Optional[int]

    def to_dict(self) -> dict:
        """JSON-serializable representation."""
        return asdict(self)


async def check_audit_log_integrity(
    db: AsyncSession,
    project_id: Optional[uuid.UUID] = None,
    since_seq: Optional[int] = None,
) -> IntegrityReport:
    """Check audit_log hash chain integrity · pure functional.

    Args:
        db: AsyncSession (read-only · any role works)
        project_id: optional project scope filter · None scans global chain
        since_seq: optional starting seq · None starts from beginning

    Returns:
        IntegrityReport con ok flag + total_rows + first_bad_seq + scope metadata

    Algorithm:
        - Global scan (project_id=None + since_seq=None): delegate to
          `fn_audit_log_verify_chain()` PostgreSQL function existing
        - Filtered scan (project_id and/or since_seq): per-row hash verify ·
          use stored hash_prev (NOT recomputed) · since filtered subset breaks
          chain continuity. Each row verified independently:
            h_current == sha256(stored_hash_prev || tabla || ... || payload_new)
        - Hash payload format (mirror trigger fn_audit_log_hash_chain):
          `COALESCE(prev_hash, '') || '|' || tabla || '|' || registro_id || '|' ||
           accion || '|' || COALESCE(usuario, '') || '|' || timestamp || '|' ||
           COALESCE(payload_old::text, '') || '|' || COALESCE(payload_new::text, '')`
    """
    if project_id is None and since_seq is None:
        row = (await db.execute(sa_text(
            "SELECT total, first_bad_seq, ok FROM fn_audit_log_verify_chain()"
        ))).first()
        if row is None:
            return IntegrityReport(
                ok=True, total_rows=0, first_bad_seq=None,
                project_id=None, since_seq=None,
            )
        return IntegrityReport(
            ok=bool(row[2]),
            total_rows=int(row[0] or 0),
            first_bad_seq=int(row[1]) if row[1] is not None else None,
            project_id=None,
            since_seq=None,
        )

    sql_parts = [
        "SELECT seq, "
        "(COALESCE(hash_prev, '') || '|' || tabla || '|' || registro_id::text || '|' || "
        "accion || '|' || COALESCE(usuario, '') || '|' || timestamp::text || '|' || "
        "COALESCE(payload_old::text, '') || '|' || COALESCE(payload_new::text, '')) AS payload_canonical, "
        "hash_current "
        "FROM audit_log WHERE 1=1"
    ]
    params: dict = {}
    if project_id is not None:
        sql_parts.append("AND project_id = :pid")
        params["pid"] = str(project_id)
    if since_seq is not None:
        sql_parts.append("AND seq >= :sseq")
        params["sseq"] = since_seq
    sql_parts.append("ORDER BY seq")

    rows = (await db.execute(sa_text(" ".join(sql_parts)), params)).all()

    total = 0
    first_bad_seq: Optional[int] = None

    for r in rows:
        total += 1
        seq, payload_canonical, h_current = r
        expected = hashlib.sha256(payload_canonical.encode("utf-8")).hexdigest()
        if h_current != expected:
            first_bad_seq = int(seq)
            return IntegrityReport(
                ok=False,
                total_rows=total,
                first_bad_seq=first_bad_seq,
                project_id=str(project_id) if project_id else None,
                since_seq=since_seq,
            )

    return IntegrityReport(
        ok=True,
        total_rows=total,
        first_bad_seq=None,
        project_id=str(project_id) if project_id else None,
        since_seq=since_seq,
    )


def _jsonb_to_text(payload) -> str:
    """Match PostgreSQL `payload::text` JSON canonical serialization.

    PostgreSQL JSONB::text uses no whitespace + lexicographic key order (sortof).
    Python json.dumps con sort_keys=True + separators sin spaces approximates.
    NOTE: edge cases unicode escape sequences may differ · acceptable per MVP.
    """
    if payload is None:
        return ""
    import json
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))
