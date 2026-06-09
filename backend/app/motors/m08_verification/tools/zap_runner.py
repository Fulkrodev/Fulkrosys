"""M8 v5.1 — OWASP ZAP runner.

ZAP corre en el container ``fulkro-scanner`` (vease docker-compose).
La app FastAPI se comunica con el por API HTTP en ``http://fulkro-scanner:8090``
(o ``http://localhost:8090`` desde el host).

Pipeline:
1. ``spider <target>`` (descubre URLs)
2. ``passive scan`` (pasivo, rapido)
3. ``active scan`` opcional para Media (mas intrusivo)
4. ``alerts`` recoge findings

Sin necesidad de zaproxy Python client: usamos httpx directo.
"""
from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone
from typing import Any

try:
    import httpx
    HAS_HTTPX = True
except ImportError:  # pragma: no cover
    HAS_HTTPX = False

from .base import (
    FindingCandidate,
    RunnerResult,
    RunnerInvocationError,
    RunnerNotInstalled,
    excerpt,
    hash_output,
    normalize_severity,
)


DEFAULT_ZAP_BASE_URL = os.getenv("FULKRO_ZAP_URL", "http://localhost:8090")
DEFAULT_ZAP_TIMEOUT = 60 * 60  # 60 min


class ZapRunner:
    TOOL = "zap"
    DEFAULT_TIMEOUT_SECONDS = DEFAULT_ZAP_TIMEOUT

    @classmethod
    def is_available(cls) -> bool:
        """ZAP esta disponible si el container responde a /JSON/core/view/version/."""
        if not HAS_HTTPX:
            return False
        try:
            with httpx.Client(timeout=3.0) as client:
                r = client.get(f"{DEFAULT_ZAP_BASE_URL}/JSON/core/view/version/")
                return r.status_code == 200
        except Exception:
            return False

    @classmethod
    def ensure_available(cls) -> None:
        if not cls.is_available():
            raise RunnerNotInstalled(
                f"ZAP no responde en {DEFAULT_ZAP_BASE_URL}. Arrancar con "
                f"`docker compose --profile scanner up -d fulkro-scanner` "
                f"y esperar a healthy."
            )

    @classmethod
    async def run(
        cls,
        targets: list[str],
        *,
        timeout_seconds: int | None = None,
        active_scan: bool = False,   # True = Media; False = Basica (solo passive)
        max_spider_minutes: int = 5,
    ) -> RunnerResult:
        cls.ensure_available()
        started = datetime.now(timezone.utc)
        all_alerts: list[dict[str, Any]] = []
        timeout_total = timeout_seconds or cls.DEFAULT_TIMEOUT_SECONDS

        async with httpx.AsyncClient(
            base_url=DEFAULT_ZAP_BASE_URL, timeout=30.0,
        ) as client:
            for target in targets:
                try:
                    # 1. Spider
                    r_spider = await client.get(
                        "/JSON/spider/action/scan/",
                        params={"url": target, "maxChildren": "100"},
                    )
                    spider_id = (r_spider.json() or {}).get("scan")
                    if spider_id:
                        await cls._wait_for_spider(client, spider_id, max_spider_minutes)

                    # 2. Passive scan ya corrio en paralelo durante spider.
                    # Esperamos a que cola quede vacia.
                    await cls._wait_for_passive_scan(client, max_minutes=2)

                    # 3. Active scan (opcional para Media)
                    if active_scan:
                        r_active = await client.get(
                            "/JSON/ascan/action/scan/",
                            params={"url": target, "recurse": "true"},
                        )
                        active_id = (r_active.json() or {}).get("scan")
                        if active_id:
                            await cls._wait_for_active_scan(client, active_id, max_minutes=20)

                    # 4. Recoger alerts
                    r_alerts = await client.get(
                        "/JSON/core/view/alerts/",
                        params={"baseurl": target, "start": "0", "count": "5000"},
                    )
                    alerts = (r_alerts.json() or {}).get("alerts", [])
                    all_alerts.extend(alerts)
                except httpx.HTTPError as exc:
                    raise RunnerInvocationError(
                        f"ZAP error para target {target}: {exc}"
                    ) from exc

        raw = b""
        try:
            import json as _json
            raw = _json.dumps({"alerts": all_alerts}).encode("utf-8")
        except Exception:
            pass

        findings = cls.parse_alerts(all_alerts)
        return RunnerResult(
            tool=cls.TOOL,
            targets=targets,
            started_at=started,
            finished_at=datetime.now(timezone.utc),
            return_code=0,
            raw_output=raw,
            raw_output_hash=hash_output(raw),
            raw_output_path=None,
            findings=findings,
        )

    @classmethod
    def parse_output(cls, raw: bytes) -> list[FindingCandidate]:
        """Parsea el JSON envuelto que persistimos en raw_output."""
        if not raw:
            return []
        import json as _json
        try:
            data = _json.loads(raw.decode("utf-8", errors="replace"))
        except _json.JSONDecodeError:
            return []
        return cls.parse_alerts(data.get("alerts", []))

    @classmethod
    def parse_alerts(cls, alerts: list[dict[str, Any]]) -> list[FindingCandidate]:
        findings: list[FindingCandidate] = []
        for alert in alerts:
            risk = (alert.get("risk") or "Informational").lower()
            sev = {
                "informational": "info", "low": "low",
                "medium": "medium", "high": "high",
            }.get(risk, "info")
            url = alert.get("url", "")
            from urllib.parse import urlparse
            host = ""
            port = None
            try:
                parsed = urlparse(url)
                host = parsed.hostname or ""
                port = parsed.port or (443 if parsed.scheme == "https" else 80)
            except Exception:
                pass
            findings.append({
                "title": alert.get("name", "ZAP alert"),
                "description": alert.get("description", "")[:1000],
                "severity": normalize_severity(sev),
                "cve_id": None,
                "cvss_score": None,
                "cvss_vector": None,
                "cwe_id": str(alert.get("cweid")) if alert.get("cweid") else None,
                "affected_host": host or url,
                "affected_port": port,
                "affected_service": "http",
                "affected_service_version": None,
                "affected_url": url,
                "affected_os": None,
                "raw_output_excerpt": excerpt(alert.get("evidence", "") or alert.get("description", "")),
                "tool": "zap",
                "tool_metadata": {
                    "alert_id": alert.get("id"),
                    "plugin_id": alert.get("pluginId"),
                    "confidence": alert.get("confidence"),
                    "solution": alert.get("solution"),
                    "param": alert.get("param"),
                },
            })
        return findings

    # ───────── helpers internos ─────────

    @staticmethod
    async def _wait_for_spider(client, scan_id: str, max_minutes: int) -> None:
        deadline = max_minutes * 60
        elapsed = 0
        while elapsed < deadline:
            r = await client.get(
                "/JSON/spider/view/status/", params={"scanId": scan_id},
            )
            status = int((r.json() or {}).get("status", "0"))
            if status >= 100:
                return
            await asyncio.sleep(2)
            elapsed += 2

    @staticmethod
    async def _wait_for_passive_scan(client, max_minutes: int) -> None:
        deadline = max_minutes * 60
        elapsed = 0
        while elapsed < deadline:
            r = await client.get("/JSON/pscan/view/recordsToScan/")
            queue = int((r.json() or {}).get("recordsToScan", "0"))
            if queue == 0:
                return
            await asyncio.sleep(2)
            elapsed += 2

    @staticmethod
    async def _wait_for_active_scan(client, scan_id: str, max_minutes: int) -> None:
        deadline = max_minutes * 60
        elapsed = 0
        while elapsed < deadline:
            r = await client.get(
                "/JSON/ascan/view/status/", params={"scanId": scan_id},
            )
            status = int((r.json() or {}).get("status", "0"))
            if status >= 100:
                return
            await asyncio.sleep(5)
            elapsed += 5
