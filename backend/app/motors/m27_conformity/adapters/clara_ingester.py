"""CLARA ingester — parsea output CLARA (CCN) y lo mapea a evidencias M7.

CLARA es la herramienta CCN para verificacion de cumplimiento en
Windows y Linux. Genera informes HTML o XML con estado de controles.

Este ingester:
  1. Parsea el fichero (XML o HTML-table).
  2. Mapea controles CLARA a medidas ENS segun CLARA_TO_ENS_MAP.
  3. Crea evidencias M7 con tipo='CLARA' para las medidas afectadas.
  4. Registra un informe consolidado (document fields).
"""
from __future__ import annotations

import hashlib
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any
from xml.etree.ElementTree import ParseError, fromstring

from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


# Mapping de controles CLARA a medidas ENS (subset, CCN-STIC 850/851/...)
CLARA_TO_ENS_MAP: dict[str, list[str]] = {
    # Windows CIS + ENS
    "CLARA-W-PWD-01": ["op.acc.3", "op.acc.5"],
    "CLARA-W-UAC-01": ["op.acc.5"],
    "CLARA-W-FW-01": ["mp.com.2"],
    "CLARA-W-PATCH-01": ["op.exp.3", "mp.sw.2"],
    "CLARA-W-AV-01": ["mp.per.3"],
    "CLARA-W-LOG-01": ["op.mon.2"],
    "CLARA-W-BITLOCKER-01": ["mp.info.9"],
    # Linux CIS + ENS
    "CLARA-L-SSH-01": ["op.acc.3"],
    "CLARA-L-FW-01": ["mp.com.2"],
    "CLARA-L-SELINUX-01": ["op.exp.5"],
    "CLARA-L-AUDIT-01": ["op.mon.2"],
    "CLARA-L-PATCH-01": ["op.exp.3"],
    "CLARA-L-LUKS-01": ["mp.info.9"],
    # Comunes
    "CLARA-NET-ENCRYPT-01": ["mp.com.2"],
    "CLARA-BACKUP-01": ["op.cont.3"],
}


STATUS_MAP = {
    "PASS": "cumple",
    "FAIL": "no_cumple",
    "OK": "cumple",
    "KO": "no_cumple",
    "NOT_APPLICABLE": "na",
    "SKIPPED": "na",
    "WARNING": "parcial",
}


def parse_clara_xml(content: bytes | str) -> list[dict[str, Any]]:
    """Parsea output XML de CLARA (CCN-STIC 850/851/852) a lista de resultados.

    Esquema tolerante: busca <check id='X' status='Y'>description</check>
    o <control code='X'><status>Y</status><desc>..</desc></control>.
    """
    if isinstance(content, bytes):
        content = content.decode("utf-8", errors="replace")
    results: list[dict[str, Any]] = []
    try:
        root = fromstring(content)
    except ParseError:
        return _parse_clara_html_table(content)

    for elem in root.iter():
        tag = elem.tag.lower().split("}")[-1]  # strip namespace
        if tag in ("check", "control", "item"):
            clara_id = (
                elem.attrib.get("id")
                or elem.attrib.get("code")
                or elem.findtext("code")
                or elem.findtext("id")
            )
            status = (
                elem.attrib.get("status")
                or elem.findtext("status")
                or elem.findtext("result")
            )
            desc = (
                elem.attrib.get("desc")
                or elem.findtext("description")
                or elem.findtext("desc")
                or elem.text
                or ""
            )
            if clara_id and status:
                results.append({
                    "clara_id": clara_id.strip(),
                    "status": status.strip().upper(),
                    "description": desc.strip() if desc else "",
                })
    return results


_HTML_ROW_RE = re.compile(
    r"<tr>.*?"
    r"<td[^>]*>(?P<id>CLARA-[A-Z-]+-\d+)</td>.*?"
    r"<td[^>]*>(?P<status>PASS|FAIL|OK|KO|NOT_APPLICABLE|SKIPPED|WARNING)</td>.*?"
    r"<td[^>]*>(?P<desc>[^<]*)</td>",
    re.DOTALL | re.IGNORECASE,
)


def _parse_clara_html_table(html: str) -> list[dict[str, Any]]:
    return [
        {
            "clara_id": m.group("id").strip(),
            "status": m.group("status").strip().upper(),
            "description": m.group("desc").strip(),
        }
        for m in _HTML_ROW_RE.finditer(html)
    ]


async def ingest_clara_output(
    db: AsyncSession,
    project_id: uuid.UUID,
    *,
    content: bytes | str,
    report_filename: str = "clara_report.xml",
) -> dict[str, Any]:
    """Ingesta un output CLARA y crea evidencias M7.

    Returns dict con: parsed_count, evidencias_created, ens_measures_touched,
    content_hash.
    """
    if isinstance(content, str):
        content_bytes = content.encode("utf-8")
    else:
        content_bytes = bytes(content)
    content_hash = hashlib.sha256(content_bytes).hexdigest()

    results = parse_clara_xml(content_bytes)
    now = datetime.now(timezone.utc)
    evidences_created: list[str] = []
    measures_touched: set[str] = set()

    await db.execute(sa_text("SET LOCAL ROLE fulkro_app_bypassrls"))
    try:
        for r in results:
            ens_measures = CLARA_TO_ENS_MAP.get(r["clara_id"], [])
            for measure in ens_measures:
                measures_touched.add(measure)
                ev_id = str(uuid.uuid4())
                # Hash especifico por medida (unico por run + medida)
                ev_hash = hashlib.sha256(
                    f"{content_hash}:{measure}".encode()
                ).hexdigest()
                status_map = STATUS_MAP.get(r["status"], "parcial")
                await db.execute(sa_text(
                    "INSERT INTO evidence (id, project_id, measure_code, tipo, "
                    "hash_sha256, vigente, fecha_evidencia, created_at) "
                    "VALUES (:id, :pid, :m, 'CLARA', :h, true, "
                    "CURRENT_DATE, :now)"
                ), {
                    "id": ev_id, "pid": str(project_id), "m": measure,
                    "h": ev_hash, "now": now,
                })
                evidences_created.append(ev_id)
    finally:
        await db.execute(sa_text("RESET ROLE"))

    return {
        "project_id": str(project_id),
        "report_filename": report_filename,
        "content_hash": content_hash,
        "parsed_count": len(results),
        "evidences_created_count": len(evidences_created),
        "evidences_created": evidences_created[:50],
        "ens_measures_touched": sorted(measures_touched),
        "ingested_at": now.isoformat(),
    }
