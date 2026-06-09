"""EPSS — Exploit Prediction Scoring System (doc §3 Capa 3, §8).

EPSS (FIRST.org) estima la probabilidad [0..1] de que un CVE sea explotado
en los próximos 30 días. Complementa a CVSS (severidad técnica) con
probabilidad real → priorización honesta para SLA (doc §8).

Estrategia de carga (fail-closed, evidence-first):
  1. Cache offline JSON (`data/epss_cache.json`) · determinista, sin red,
     usable en dev/CI/tests. Es la fuente por defecto.
  2. Refresh online opcional (`refresh_online`) contra la API FIRST.org ·
     solo si se invoca explícitamente y hay red. Si falla → se conserva la
     cache (NUNCA rompe el pipeline; ausencia de EPSS = None, no bloquea).

En Hetzner (FASE J) un job periódico puede refrescar la cache. En dev la
cache seed cubre los CVE del catálogo ENS mapper para tests deterministas.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_DEFAULT_CACHE = _DATA_DIR / "epss_cache.json"

# API FIRST.org · GET ?cve=CVE-2021-44228,CVE-... → {data:[{cve,epss,percentile}]}
EPSS_API_URL = "https://api.first.org/data/v1/epss"


class EpssClient:
    """Cliente EPSS con cache offline determinista + refresh online opcional."""

    def __init__(self, cache_path: Path | str | None = None) -> None:
        self.cache_path = Path(cache_path) if cache_path else _DEFAULT_CACHE
        self._cache: dict[str, dict[str, Any]] = {}
        self._loaded = False

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        try:
            if self.cache_path.exists():
                raw = json.loads(self.cache_path.read_text(encoding="utf-8"))
                # acepta {cve: {epss,percentile}} o {cve: float}
                for k, v in (raw or {}).items():
                    key = k.strip().upper()
                    if isinstance(v, dict):
                        self._cache[key] = v
                    else:
                        self._cache[key] = {"epss": float(v)}
        except Exception as exc:  # pragma: no cover — fail-closed
            logger.warning("EPSS cache load failed (%s): %s", self.cache_path, exc)
            self._cache = {}

    def get(self, cve_id: str | None) -> float | None:
        """Devuelve el EPSS score [0..1] de un CVE, o None si desconocido."""
        if not cve_id:
            return None
        self._ensure_loaded()
        entry = self._cache.get(str(cve_id).strip().upper())
        if not entry:
            return None
        val = entry.get("epss")
        try:
            return float(val) if val is not None else None
        except (TypeError, ValueError):
            return None

    def get_percentile(self, cve_id: str | None) -> float | None:
        if not cve_id:
            return None
        self._ensure_loaded()
        entry = self._cache.get(str(cve_id).strip().upper())
        if not entry:
            return None
        val = entry.get("percentile")
        try:
            return float(val) if val is not None else None
        except (TypeError, ValueError):
            return None

    async def refresh_online(self, cve_ids: list[str]) -> int:
        """Refresca la cache desde FIRST.org para los CVE dados.

        Fail-closed: si no hay red / httpx / error → conserva cache, devuelve 0.
        Solo persiste si obtuvo datos. Devuelve nº de CVE actualizados.
        Pensado para job periódico en Hetzner (NO se llama en el pipeline online).
        """
        cve_ids = [c.strip().upper() for c in cve_ids if c]
        if not cve_ids:
            return 0
        self._ensure_loaded()
        try:
            import httpx  # noqa: PLC0415
        except Exception:  # pragma: no cover
            logger.warning("EPSS refresh: httpx no disponible · fail-closed")
            return 0
        updated = 0
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                # API admite hasta ~100 CVE por request
                for i in range(0, len(cve_ids), 100):
                    batch = cve_ids[i : i + 100]
                    resp = await client.get(
                        EPSS_API_URL, params={"cve": ",".join(batch)},
                    )
                    resp.raise_for_status()
                    for row in (resp.json().get("data") or []):
                        cve = str(row.get("cve", "")).strip().upper()
                        if not cve:
                            continue
                        self._cache[cve] = {
                            "epss": float(row.get("epss", 0) or 0),
                            "percentile": float(row.get("percentile", 0) or 0),
                            "date": row.get("date"),
                        }
                        updated += 1
        except Exception as exc:  # pragma: no cover — fail-closed
            logger.warning("EPSS refresh online failed: %s", exc)
            return 0
        if updated:
            try:
                self.cache_path.parent.mkdir(parents=True, exist_ok=True)
                self.cache_path.write_text(
                    json.dumps(self._cache, indent=2, sort_keys=True),
                    encoding="utf-8",
                )
            except Exception as exc:  # pragma: no cover
                logger.warning("EPSS cache persist failed: %s", exc)
        return updated


_client: EpssClient | None = None


def get_epss_client() -> EpssClient:
    global _client
    if _client is None:
        _client = EpssClient()
    return _client


def enrich_findings_with_epss(
    findings: list[dict[str, Any]],
    client: EpssClient | None = None,
) -> list[dict[str, Any]]:
    """Asigna `epss_score` a cada finding con cve_id conocido (in-place + return)."""
    cli = client or get_epss_client()
    for f in findings:
        cve = f.get("cve_id") or f.get("cve")
        if isinstance(cve, (list, tuple)):
            cve = cve[0] if cve else None
        score = cli.get(cve)
        if score is not None:
            f["epss_score"] = score
    return findings
