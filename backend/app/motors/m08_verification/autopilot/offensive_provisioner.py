"""Provisión efímera de infra ofensiva on-demand (tier dedicado · doc §2 §15).

Levanta una box cloud temporal con las herramientas ofensivas del tier (cracking
GPU / phishing GoPhish / red team), la usa DENTRO de la autorización firmada del
engagement, y la DESTRUYE garantizado al cerrar (mismo principio de zero standing
access que ``ephemeral_connector``).

mock-by-default: si ``OFFENSIVE_PROVISIONER_ENABLED`` es false o falta
``HETZNER_CLOUD_TOKEN``, ``provision_box`` devuelve una box SIMULADA (no toca red).
Real: Hetzner Cloud API (crea servidor con cloud-init del tier · DELETE al cerrar).

FRONTERA HONESTA (metadato auditable · NO truco de marketing): esta infra ejecuta
testing ofensivo AUTORIZADO y SUPERVISADO, pero NO convierte el resultado en una
prueba de penetración INDEPENDIENTE certificable. ENS ALTA (mp.s.3) exige pentester
cualificado e independiente del implantador; el engagement registra authorized_by +
attestor + independencia, y ese es el ancla que verifica el auditor ENAC. La
plataforma acelera y abarata el engagement; no sustituye la firma cualificada.

WIRELESS sigue siendo FÍSICAMENTE IMPOSIBLE remotamente (antena en modo monitor
on-site): provision_box lo declina explícitamente.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from backend.app.config import get_settings

logger = logging.getLogger(__name__)

HETZNER_API = "https://api.hetzner.cloud/v1"

# Tiers ofensivos provisionables en cloud (wireless excluido · físico on-site).
PROVISIONABLE_TIERS = ("cracking", "phishing", "redteam", "mobile")

# cloud-init mínimo por tier (lo que se instala en la box efímera al arrancar).
_CLOUD_INIT: dict[str, str] = {
    "cracking": (
        "#cloud-config\npackages: [hashcat, hashid, john]\n"
        "runcmd:\n  - mkdir -p /opt/wordlists\n"
        "  - curl -sSL https://github.com/praetorian-inc/Hob0Rules/raw/master/wordlists/rockyou.txt.gz "
        "-o /opt/wordlists/rockyou.txt.gz || true\n"
        "  - gunzip -f /opt/wordlists/rockyou.txt.gz || true\n"
    ),
    "phishing": (
        "#cloud-config\npackages: [docker.io]\n"
        "runcmd:\n  - systemctl enable --now docker\n"
        "  - docker run -d --name gophish -p 3333:3333 -p 8080:80 gophish/gophish || true\n"
    ),
    "redteam": (
        "#cloud-config\npackages: [git, python3-pip, nmap]\n"
        "runcmd:\n  - pip3 install impacket || true\n"
    ),
    "mobile": (
        "#cloud-config\npackages: [openjdk-17-jdk]\n"
        "runcmd:\n  - pip3 install mobsf || true\n"
    ),
}

# Tipo de servidor Hetzner por tier (cracking necesita GPU/CPU potente).
_SERVER_TYPE: dict[str, str] = {
    "cracking": "ccx33",   # dedicated vCPU (no hay GPU en Hetzner Cloud · CPU-bound)
    "phishing": "cx22",
    "redteam": "cx32",
    "mobile": "cx32",
}


@dataclass
class OffensiveBox:
    """Handle de una box ofensiva efímera (zero standing access)."""

    box_id: str
    tier: str
    provider_server_id: Optional[str] = None
    host: Optional[str] = None
    status: str = "provisioning"  # provisioning | ready | destroyed | error | mocked
    mock: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    destroyed_at: Optional[datetime] = None
    error: Optional[str] = None

    def env_overrides(self) -> dict[str, str]:
        """Variables de entorno que las tools del tier necesitan apuntando a la box."""
        if self.tier == "phishing" and self.host:
            return {"GOPHISH_HOST": f"http://{self.host}:3333"}
        return {}


def provisioner_enabled() -> bool:
    s = get_settings()
    try:
        token = s.hetzner_cloud_token.get_secret_value()
    except Exception:
        token = ""
    return bool(getattr(s, "offensive_provisioner_enabled", False)) and bool(token)


async def provision_box(tier: str, *, label: str | None = None) -> OffensiveBox:
    """Provisiona una box ofensiva del tier. mock-by-default (no toca red).

    Wireless se declina (físico on-site). Real: Hetzner Cloud API.
    """
    tier = (tier or "").lower()
    if tier == "wireless":
        return OffensiveBox(
            box_id=str(uuid.uuid4()), tier=tier, status="error", mock=True,
            error="wireless requiere antena física en modo monitor (on-site) · NO provisionable en cloud",
        )
    if tier not in PROVISIONABLE_TIERS:
        return OffensiveBox(
            box_id=str(uuid.uuid4()), tier=tier, status="error", mock=True,
            error=f"tier '{tier}' no provisionable",
        )

    if not provisioner_enabled():
        # mock determinista · no toca red (dev/test · KYC/credenciales pendientes)
        return OffensiveBox(
            box_id=str(uuid.uuid4()), tier=tier, status="mocked", mock=True,
            host=f"mock-{tier}.offensive.local",
        )

    s = get_settings()
    token = s.hetzner_cloud_token.get_secret_value()
    name = f"fk-offensive-{tier}-{uuid.uuid4().hex[:8]}"
    payload: dict[str, Any] = {
        "name": name,
        "server_type": _SERVER_TYPE.get(tier, "cx32"),
        "image": getattr(s, "offensive_box_image", "ubuntu-24.04"),
        "location": getattr(s, "offensive_box_location", "nbg1"),
        "user_data": _CLOUD_INIT.get(tier, "#cloud-config\n"),
        "labels": {"fulkro": "offensive-ephemeral", "tier": tier},
    }
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(f"{HETZNER_API}/servers", json=payload, headers=headers)
    except httpx.RequestError as exc:
        return OffensiveBox(box_id=str(uuid.uuid4()), tier=tier, status="error",
                            mock=False, error=f"provision network error: {exc}"[:200])
    if resp.status_code >= 400:
        return OffensiveBox(box_id=str(uuid.uuid4()), tier=tier, status="error",
                            mock=False, error=f"hetzner http_{resp.status_code}: {resp.text[:300]}")
    data = resp.json().get("server", {})
    host = ((data.get("public_net") or {}).get("ipv4") or {}).get("ip")
    return OffensiveBox(
        box_id=str(uuid.uuid4()), tier=tier, provider_server_id=str(data.get("id")),
        host=host, status="ready", mock=False,
    )


async def teardown_box(box: OffensiveBox) -> None:
    """DESTRUYE la box (zero standing access · garantizado · idempotente).

    Nunca lanza: el teardown se llama en finally y no debe romper el flujo. Un
    fallo de teardown se loggea como CRÍTICO (box huérfana = coste + exposición).
    """
    if box.destroyed_at is not None:
        return
    box.destroyed_at = datetime.now(timezone.utc)
    if box.mock or not box.provider_server_id:
        box.status = "destroyed"
        return
    try:
        s = get_settings()
        token = s.hetzner_cloud_token.get_secret_value()
        headers = {"Authorization": f"Bearer {token}"}
        async with httpx.AsyncClient(timeout=60.0) as client:
            await client.delete(
                f"{HETZNER_API}/servers/{box.provider_server_id}", headers=headers,
            )
        box.status = "destroyed"
    except Exception as exc:  # pragma: no cover — teardown nunca rompe el flujo
        box.status = "error"
        box.error = f"teardown failed: {exc}"[:200]
        logger.critical(
            "OFFENSIVE BOX HUÉRFANA · server %s NO destruida: %s · DESTRUIR A MANO",
            box.provider_server_id, exc,
        )
