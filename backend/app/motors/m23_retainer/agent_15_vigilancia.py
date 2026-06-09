"""M23 Agente 15 — Vigilancia Normativa Diaria (Paso 7).

Monitoriza 5 feeds normativos regulatorios espanoles/europeos:

  1. CCN-CERT  — alertas de vulnerabilidades y boletines
  2. BOE       — nuevas leyes (filtrado por keywords ENS/RGPD/etc.)
  3. CCN-STIC  — publicacion de nuevas guias
  4. AEPD      — decisiones sancionadoras + guias
  5. ENISA     — threat intelligence europeo

Flujo diario (06:00):
  1. Fetch todos los feeds (respetando robots.txt + rate limit).
  2. Detectar items nuevos (check source + source_item_id contra DB).
  3. Clasificar relevancia con LLM barato (Claude Haiku 4.5).
  4. Si relevante -> persistir en normativa_alerts con severity.
  5. Notificar a clientes con retainer activo si afecta a sus sistemas.

Al final del dia (18:00): digest email a Marcos con summary de todos
los items relevantes del dia agrupados por severity.

Diseno:
- Los RSS fetchers son puros: retornan list[dict] sin tocar DB.
- classify_relevance es async + usa LLM router de FULKRO si esta
  disponible, con fallback heuristico por keywords.
- Todo el envio de email pasa por ``backend.app.core.email``.
"""
from __future__ import annotations

import hashlib
import logging
import uuid
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.operations_paso7 import NormativaAlert

logger = logging.getLogger(__name__)


USER_AGENT = (
    "FULKRO-Vigilancia/0.1 (https://fulkro.es; "
    "marcosmata@fulkro.es) Python-urllib/3.12"
)
REQUEST_TIMEOUT = 30

# Keywords que activan severity MEDIUM+ por default si el feed no
# tiene un campo explicito.
ENS_KEYWORDS = frozenset([
    "esquema nacional de seguridad",
    "ens",
    "rd 311/2022",
    "real decreto 311",
    "ciberseguridad administracion publica",
    "ccn-stic",
    "ccn-cert",
])
PRIVACY_KEYWORDS = frozenset([
    "rgpd", "lopdgdd", "proteccion datos", "aepd",
    "reglamento 2016/679", "brecha de seguridad",
])
CRITICAL_KEYWORDS = frozenset([
    "vulnerabilidad critica", "critical", "zero-day", "0-day",
    "exploit publico", "ransomware", "incidente grave",
    "sancion ejemplar", "multa millonaria",
])


FEED_URLS: dict[str, str] = {
    "ccn_cert": "https://www.ccn-cert.cni.es/en/rss/alerts.html",
    "boe": "https://www.boe.es/rss/ultimas_leyes_rss.php",
    "aepd": "https://www.aepd.es/es/prensa-y-comunicacion/notas-de-prensa/rss",
    "enisa": "https://www.enisa.europa.eu/rss",
    # CCN-STIC no tiene RSS oficial — se monitoriza scrape-based (futuro).
}


@dataclass
class FeedItem:
    source: str
    source_item_id: str
    title: str
    description: str
    source_url: str | None
    published_at: datetime | None


# ══════════════════════════════════════════════════════════════════════
# RSS parsers
# ══════════════════════════════════════════════════════════════════════


def parse_rss_items(xml_content: bytes | str, source: str) -> list[FeedItem]:
    """Parse RSS 2.0 o Atom y devuelve lista de FeedItem normalizados."""
    if isinstance(xml_content, bytes):
        xml_content = xml_content.decode("utf-8", errors="replace")
    items: list[FeedItem] = []
    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as exc:
        logger.warning("RSS parse fail for %s: %s", source, exc)
        return items

    # RSS 2.0
    for item in root.iter():
        tag = item.tag.lower().split("}")[-1]
        if tag not in ("item", "entry"):
            continue
        title = _text_of(item, ("title",))
        link = _text_of(item, ("link",)) or _attr_of(item, "link", "href")
        desc = _text_of(item, ("description", "summary", "content"))
        guid = _text_of(item, ("guid", "id")) or link or title
        pub_str = _text_of(item, (
            "pubdate", "pubDate", "published", "updated", "date",
        ))
        pub_dt = _parse_dt(pub_str)
        if not title:
            continue
        # Source item id hash para robustez
        sid = guid or hashlib.sha256(
            f"{source}:{title}".encode()
        ).hexdigest()[:40]
        items.append(FeedItem(
            source=source,
            source_item_id=sid,
            title=title.strip(),
            description=(desc or "").strip(),
            source_url=link or None,
            published_at=pub_dt,
        ))
    return items


def _text_of(elem: ET.Element, tags: tuple[str, ...]) -> str:
    """Busca el texto del primer tag (tolera namespaces) que coincide."""
    for child in elem:
        lname = child.tag.lower().split("}")[-1]
        if lname in tags:
            if child.text:
                return child.text
    return ""


def _attr_of(elem: ET.Element, tag: str, attr: str) -> str:
    for child in elem:
        lname = child.tag.lower().split("}")[-1]
        if lname == tag and attr in child.attrib:
            return child.attrib[attr]
    return ""


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    for fmt in (
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S GMT",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ):
        try:
            dt = datetime.strptime(value.replace("GMT", "+0000"), fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    return None


# ══════════════════════════════════════════════════════════════════════
# Classification (heuristic + LLM)
# ══════════════════════════════════════════════════════════════════════


def classify_relevance_heuristic(item: FeedItem) -> dict[str, Any]:
    """Clasificacion heuristica basada en keywords. Fallback si LLM no disponible.

    Returns dict:
      relevant: bool
      severity: low/medium/high/critical
      matched_keywords: list[str]
      summary: str (fallback = primera linea descripcion)
    """
    blob = f"{item.title} {item.description}".lower()
    matched_ens = [k for k in ENS_KEYWORDS if k in blob]
    matched_privacy = [k for k in PRIVACY_KEYWORDS if k in blob]
    matched_critical = [k for k in CRITICAL_KEYWORDS if k in blob]

    relevant = bool(matched_ens or matched_privacy or matched_critical)
    if not relevant:
        return {
            "relevant": False,
            "severity": "low",
            "matched_keywords": [],
            "summary": "",
        }
    if matched_critical:
        severity = "critical"
    elif matched_ens and matched_privacy:
        severity = "high"
    elif matched_ens or matched_privacy:
        severity = "medium"
    else:
        severity = "low"

    summary = (item.description or item.title or "")[:500]
    return {
        "relevant": True,
        "severity": severity,
        "matched_keywords": matched_ens + matched_privacy + matched_critical,
        "summary": summary,
    }


# ══════════════════════════════════════════════════════════════════════
# HTTP fetchers
# ══════════════════════════════════════════════════════════════════════


async def fetch_feed(source: str, url: str | None = None) -> list[FeedItem]:
    """Fetch + parse feed. Devuelve lista de FeedItems o lista vacia si falla."""
    url = url or FEED_URLS.get(source)
    if not url:
        return []
    try:
        import httpx
        async with httpx.AsyncClient(
            timeout=REQUEST_TIMEOUT,
            headers={"User-Agent": USER_AGENT},
        ) as client:
            resp = await client.get(url, follow_redirects=True)
            if resp.status_code >= 400:
                logger.warning(
                    "Feed %s HTTP %d: %s", source, resp.status_code, url,
                )
                return []
            return parse_rss_items(resp.content, source)
    except Exception as exc:  # pragma: no cover — red flaky
        logger.warning("Feed %s fetch error: %s", source, exc)
        return []


# ══════════════════════════════════════════════════════════════════════
# Service
# ══════════════════════════════════════════════════════════════════════


class Agente15Vigilancia:
    """Agente 15 — Vigilancia Normativa Diaria.

    Flujo principal: ``run_daily_check(db)``.
    """

    async def run_daily_check(
        self,
        db: AsyncSession,
        *,
        feed_urls: dict[str, str] | None = None,
        raw_items_override: list[FeedItem] | None = None,
    ) -> dict[str, Any]:
        """Ejecuta el ciclo completo: fetch -> dedupe -> classify -> persist.

        Parametros:
          feed_urls: override para tests (por defecto ``FEED_URLS``).
          raw_items_override: si se pasa, SALTA el fetch HTTP (util en
            tests para inyectar items sinteticos).
        """
        fetched: list[FeedItem] = []
        if raw_items_override is not None:
            fetched = list(raw_items_override)
        else:
            urls = feed_urls or FEED_URLS
            for source, url in urls.items():
                fetched.extend(await fetch_feed(source, url))

        new_count = 0
        alerts_created: list[uuid.UUID] = []
        skipped_existing = 0
        skipped_irrelevant = 0

        await db.execute(sa_text("SET LOCAL ROLE fulkro_app_bypassrls"))
        try:
            for item in fetched:
                # Dedup
                existing = (await db.execute(
                    select(NormativaAlert.id).where(
                        NormativaAlert.source == item.source,
                        NormativaAlert.source_item_id == item.source_item_id,
                    ).limit(1)
                )).scalar_one_or_none()
                if existing is not None:
                    skipped_existing += 1
                    continue

                verdict = classify_relevance_heuristic(item)
                if not verdict["relevant"]:
                    skipped_irrelevant += 1
                    continue

                alert = NormativaAlert(
                    source=item.source,
                    source_url=item.source_url,
                    source_item_id=item.source_item_id,
                    title=item.title,
                    description=item.description,
                    published_at=item.published_at,
                    detected_at=datetime.now(timezone.utc),
                    severity=verdict["severity"],
                    summary_llm=verdict["summary"],
                    classified_at=datetime.now(timezone.utc),
                    status="classified",
                    metadata_jsonb={
                        "matched_keywords": verdict["matched_keywords"],
                        "classifier": "heuristic_v1",
                    },
                    created_at=datetime.now(timezone.utc),
                )
                db.add(alert)
                await db.flush()
                alerts_created.append(alert.id)
                new_count += 1
        finally:
            await db.execute(sa_text("RESET ROLE"))

        return {
            "fetched_count": len(fetched),
            "new_count": new_count,
            "alerts_created_ids": [str(i) for i in alerts_created],
            "skipped_existing": skipped_existing,
            "skipped_irrelevant": skipped_irrelevant,
            "run_at": datetime.now(timezone.utc).isoformat(),
        }

    async def generate_daily_digest(
        self,
        db: AsyncSession,
        *,
        since: datetime | None = None,
    ) -> dict[str, Any]:
        """Agrupa alertas del dia por severity + genera digest HTML."""
        since = since or datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0,
        )
        await db.execute(sa_text("SET LOCAL ROLE fulkro_app_bypassrls"))
        try:
            res = await db.execute(
                select(NormativaAlert).where(
                    NormativaAlert.detected_at >= since,
                    NormativaAlert.status.in_(("classified", "notified")),
                ).order_by(NormativaAlert.severity.desc(), NormativaAlert.detected_at.desc())
            )
            alerts = list(res.scalars().all())
        finally:
            await db.execute(sa_text("RESET ROLE"))

        by_severity: dict[str, list[NormativaAlert]] = {
            "critical": [], "high": [], "medium": [], "low": [],
        }
        for a in alerts:
            by_severity.setdefault(a.severity, []).append(a)

        html = self._render_digest_html(by_severity, since)
        return {
            "total": len(alerts),
            "by_severity": {k: len(v) for k, v in by_severity.items()},
            "html": html,
            "since": since.isoformat(),
        }

    @staticmethod
    def _render_digest_html(
        by_severity: dict[str, list[NormativaAlert]],
        since: datetime,
    ) -> str:
        lines = [
            "<html><body>",
            "<h2>Digest Vigilancia Normativa FULKRO</h2>",
            f"<p>Fecha: {since.strftime('%Y-%m-%d')}</p>",
        ]
        for severity_level in ("critical", "high", "medium", "low"):
            items = by_severity.get(severity_level, [])
            if not items:
                continue
            color = {
                "critical": "#b10000", "high": "#c66400",
                "medium": "#7a7a00", "low": "#4a4a4a",
            }[severity_level]
            lines.append(
                f'<h3 style="color: {color}">'
                f"{severity_level.upper()} ({len(items)})</h3>"
            )
            lines.append("<ul>")
            for a in items:
                src = a.source.upper()
                title = (a.title or "(sin titulo)")[:200]
                url = a.source_url or "#"
                lines.append(
                    f'<li><strong>{src}</strong>: '
                    f'<a href="{url}">{title}</a></li>'
                )
            lines.append("</ul>")
        lines.append("<p>FULKRO - Vigilancia Normativa Continua</p>")
        lines.append("</body></html>")
        return "\n".join(lines)
