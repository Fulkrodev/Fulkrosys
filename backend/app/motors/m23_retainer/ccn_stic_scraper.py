"""CCN-STIC scraper · MB-7.bis atom 7.bis.2.

A15 Vigilancia Normativa extension: CCN-STIC index scraping
respecting robots.txt + rate limit + User-Agent identifiable.

Source: https://www.ccn-cert.cni.es/series-ccn-stic.html

Strategy:
1. Fetch index HTML once (cached per ETag/Last-Modified)
2. Parse anchor list of guides (heuristic: <a href=".../series-ccn-stic-XXX">)
3. For each guide URL, fetch HEAD to detect last-modified
4. Compare against existing normativa_alerts (source="ccn_stic")
5. Persist new/updated guides as normativa_alerts records

Falls back to scraping-disabled mode if robots.txt forbids /series-ccn-stic.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
from urllib import robotparser

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.operations_paso7 import NormativaAlert


logger = logging.getLogger(__name__)


SOURCE = "ccn_stic"
INDEX_URL = "https://www.ccn-cert.cni.es/series-ccn-stic.html"
USER_AGENT = (
    "FULKRO-Vigilancia/0.1 (https://fulkro.es; "
    "marcosmata@fulkro.es) Python-urllib/3.12"
)
REQUEST_TIMEOUT = 30
RATE_LIMIT_SECONDS = 2.0


# Anchor href regex · matches guide links like /series-ccn-stic/800-esquema-nacional...
_GUIDE_HREF_RE = re.compile(
    r'href=["\']([^"\']*series-ccn-stic[/-][^"\']*)["\']',
    re.IGNORECASE,
)


@dataclass
class ScrapedGuide:
    """Single CCN-STIC guide entry detected during scrape."""

    url: str
    source_item_id: str  # stable identifier (last path segment + hash)
    title: str
    last_modified: Optional[datetime]


def _http_get(url: str) -> tuple[Optional[bytes], dict[str, str]]:
    """Fetch URL · returns (body_bytes, headers_dict) or (None, {}) on failure."""
    req = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,*/*"},
    )
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            body = resp.read()
            headers = {k.lower(): v for k, v in resp.headers.items()}
            return body, headers
    except Exception as exc:  # noqa: BLE001
        logger.warning("CCN-STIC fetch %s failed: %s", url, exc)
        return None, {}


def _default_robots_allows() -> bool:
    """Comprueba robots.txt de ccn-cert.cni.es para INDEX_URL (S7 fix · antes
    prometido en docstring pero no implementado). Fail-open ante error de red
    (mismo criterio tolerante que _http_get)."""
    rp = robotparser.RobotFileParser()
    rp.set_url("https://www.ccn-cert.cni.es/robots.txt")
    try:
        rp.read()
    except Exception as exc:  # noqa: BLE001
        logger.warning("CCN-STIC robots.txt no accesible (%s) · fail-open", exc)
        return True
    return rp.can_fetch(USER_AGENT, INDEX_URL)


def _http_head(url: str) -> dict[str, str]:
    """HEAD request to inspect Last-Modified without downloading body."""
    req = urllib.request.Request(
        url, method="HEAD", headers={"User-Agent": USER_AGENT},
    )
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            return {k.lower(): v for k, v in resp.headers.items()}
    except Exception as exc:  # noqa: BLE001
        logger.warning("CCN-STIC HEAD %s failed: %s", url, exc)
        return {}


def _parse_last_modified(value: Optional[str]) -> Optional[datetime]:
    """Parse HTTP Last-Modified header (RFC 7231 IMF-fixdate)."""
    if not value:
        return None
    try:
        from email.utils import parsedate_to_datetime

        dt = parsedate_to_datetime(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:  # noqa: BLE001
        return None


def _normalize_url(href: str) -> str:
    """Resolve a relative href against the index URL."""
    return urllib.parse.urljoin(INDEX_URL, href)


def _stable_item_id(url: str) -> str:
    """Build a stable identifier from a guide URL · last segment + sha1[:8]."""
    path = urllib.parse.urlparse(url).path
    segment = path.rstrip("/").rsplit("/", 1)[-1] or "index"
    # sha1 NO criptográfico: solo un id estable corto desde la URL (no seguridad).
    digest = hashlib.sha1(url.encode("utf-8"), usedforsecurity=False).hexdigest()[:8]
    return f"{segment}-{digest}"


def _extract_title_from_url(url: str) -> str:
    """Heuristic title from URL path · last segment with dashes→spaces."""
    path = urllib.parse.urlparse(url).path
    segment = path.rstrip("/").rsplit("/", 1)[-1] or "(sin título)"
    return segment.replace("-", " ").replace("_", " ").strip()[:200] or "(sin título)"


def parse_index_html(html: bytes) -> list[ScrapedGuide]:
    """Parse the index HTML and return scraped guide entries.

    Pure function · no network · safe to unit-test.
    """
    text = html.decode("utf-8", errors="ignore")
    seen: set[str] = set()
    guides: list[ScrapedGuide] = []
    for match in _GUIDE_HREF_RE.finditer(text):
        href = match.group(1).strip()
        url = _normalize_url(href)
        if url in seen:
            continue
        seen.add(url)
        guides.append(ScrapedGuide(
            url=url,
            source_item_id=_stable_item_id(url),
            title=_extract_title_from_url(url),
            last_modified=None,
        ))
    return guides


async def _existing_item_ids(db: AsyncSession) -> set[str]:
    rows = (await db.execute(
        select(NormativaAlert.source_item_id).where(
            NormativaAlert.source == SOURCE,
        )
    )).scalars().all()
    return {r for r in rows if r}


def _severity_for_title(title: str) -> str:
    """Heuristic severity per title keywords."""
    t = title.lower()
    if any(k in t for k in ("urgente", "critic", "emergenc", "zero-day", "rce")):
        return "critical"
    if any(k in t for k in ("alta", "high", "actualizaci")):
        return "high"
    if any(k in t for k in ("media", "moderada")):
        return "medium"
    return "low"


async def scrape_and_persist(
    db: AsyncSession,
    *,
    fetch_html=None,
    head_url=None,
    robots_allows=None,
    rate_limit: float = RATE_LIMIT_SECONDS,
) -> dict:
    """Run a full CCN-STIC scrape cycle.

    Args:
        db: async SQLAlchemy session
        fetch_html: optional injected fetcher for tests · returns (bytes, headers)
        head_url: optional injected HEAD fetcher for tests · returns headers dict
        rate_limit: seconds to sleep between HEAD requests (politeness)

    Returns summary dict ``{indexed, new, skipped, errors}``.
    """
    fetcher = fetch_html or (lambda u: _http_get(u))
    head_fetch = head_url or (lambda u: _http_head(u))

    # S7 fix · robots.txt: solo en modo real (fetcher por defecto · prod via
    # Celery). En tests con fetcher inyectado se omite (no hay red). El check
    # bloqueante (urllib.robotparser) corre en executor para no bloquear el loop.
    if fetch_html is None or robots_allows is not None:
        robots_check = robots_allows or _default_robots_allows
        allowed = await asyncio.get_running_loop().run_in_executor(None, robots_check)
        if not allowed:
            logger.warning(
                "CCN-STIC robots.txt prohíbe %s · scraping omitido", INDEX_URL,
            )
            return {
                "indexed": 0, "new": 0, "skipped": 0, "errors": 0,
                "robots_blocked": True,
            }

    body, _headers = fetcher(INDEX_URL)
    if not body:
        return {"indexed": 0, "new": 0, "skipped": 0, "errors": 1}

    guides = parse_index_html(body)
    existing = await _existing_item_ids(db)

    new_count = 0
    skipped = 0
    for guide in guides:
        if guide.source_item_id in existing:
            skipped += 1
            continue
        head_headers = head_fetch(guide.url)
        last_mod = _parse_last_modified(head_headers.get("last-modified"))
        if rate_limit:
            await asyncio.sleep(rate_limit)

        alert = NormativaAlert(
            source=SOURCE,
            source_url=guide.url,
            source_item_id=guide.source_item_id,
            title=guide.title,
            description=None,
            published_at=last_mod,
            severity=_severity_for_title(guide.title),
            status="detected",
        )
        db.add(alert)
        new_count += 1

    await db.flush()
    return {
        "indexed": len(guides),
        "new": new_count,
        "skipped": skipped,
        "errors": 0,
    }
