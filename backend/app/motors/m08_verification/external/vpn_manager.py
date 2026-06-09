"""M8 v5.1 - VPN manager para handoff externo (spec §6.2).

Genera:
- Config OpenVPN (.ovpn) para el pentester externo.
- Credenciales cifradas (NUNCA en plano en BD).

Cifrado:
- Si el pentester aporta su clave publica (PEM), ciframos con RSA-OAEP.
- Si no la aporta, generamos una clave simetrica aleatoria (Fernet/
  AES-256) y la entregamos por canal aparte (out-of-band). En la BD
  queda el ciphertext Fernet; la clave simetrica NO se guarda en la BD.

Este modulo es intencionalmente portable — para el demo y los tests no
depende de un servidor VPN real; la config generada es un template que
el DevOps aplica al servidor corporativo.
"""
from __future__ import annotations

import base64
import os
import secrets
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding as rsa_padding
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey


ROOT = Path(__file__).resolve().parents[5]
VPN_CONFIG_DIR = ROOT / "var" / "verification_vpn"


DEFAULT_OVPN_SERVER = os.environ.get("FULKRO_VPN_SERVER", "vpn.ejemplo.es")
DEFAULT_OVPN_PORT = int(os.environ.get("FULKRO_VPN_PORT", "1194"))
DEFAULT_OVPN_PROTO = os.environ.get("FULKRO_VPN_PROTO", "udp")


OVPN_TEMPLATE = """client
dev tun
proto {proto}
remote {server} {port}
resolv-retry infinite
nobind
persist-key
persist-tun
remote-cert-tls server
auth SHA256
cipher AES-256-GCM
verb 3

# Credenciales — se inyectan en tiempo de conexion desde un fichero
# cifrado aparte, nunca se guardan en plano.
auth-user-pass

# Solo acceso a los segmentos del alcance; todo lo demas se bloquea.
route-nopull
{routes}
"""


@dataclass(frozen=True)
class VpnArtifact:
    config_path: Path
    credentials_ciphertext: bytes
    encryption_method: str          # "rsa_oaep" | "fernet_symmetric"
    symmetric_key_b64: str | None   # solo si el caller eligio fernet

    def to_persistable(self) -> dict:
        return {
            "config_path": str(self.config_path),
            "credentials_ciphertext": base64.b64encode(
                self.credentials_ciphertext,
            ).decode("ascii"),
            "encryption_method": self.encryption_method,
        }


def _generate_credentials() -> tuple[str, str]:
    """Genera un usuario + password aleatorios."""
    user = f"pentester_{secrets.token_hex(4)}"
    password = secrets.token_urlsafe(24)
    return user, password


def _routes_for_scope(scope_targets: list[str]) -> str:
    """Genera las directivas ``route`` para restringir la VPN al alcance."""
    unique_hosts = set()
    for t in scope_targets or []:
        t = t.strip().rstrip("/")
        # Si es host:port, nos quedamos con el host
        host = t.split(":")[0] if ":" in t else t
        if host:
            unique_hosts.add(host)
    if not unique_hosts:
        return "# no se pudieron derivar rutas especificas (scope vacio)"
    return "\n".join(
        f"route {h} 255.255.255.255" for h in sorted(unique_hosts)
    )


def _encrypt_with_public_key(creds: bytes, pubkey_pem: bytes) -> bytes:
    """Cifra con la clave publica RSA del pentester (OAEP + SHA-256)."""
    pubkey = serialization.load_pem_public_key(pubkey_pem)
    if not isinstance(pubkey, RSAPublicKey):
        raise ValueError("La clave publica proporcionada no es RSA")
    return pubkey.encrypt(
        creds,
        rsa_padding.OAEP(
            mgf=rsa_padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )


def _encrypt_with_fernet(creds: bytes) -> tuple[bytes, str]:
    """Cifra con una clave simetrica generada al vuelo.

    Devuelve (ciphertext, b64_key). La clave se entrega al pentester por
    canal aparte (no se persiste en BD).
    """
    key = Fernet.generate_key()
    ct = Fernet(key).encrypt(creds)
    return ct, key.decode("ascii")


def generate_for_handoff(
    handoff_id: uuid.UUID,
    scope_targets: list[str],
    *,
    pentester_public_key_pem: Optional[bytes] = None,
    server: str = DEFAULT_OVPN_SERVER,
    port: int = DEFAULT_OVPN_PORT,
    proto: str = DEFAULT_OVPN_PROTO,
) -> VpnArtifact:
    """Genera el .ovpn + credenciales cifradas para un handoff."""
    VPN_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    config_path = VPN_CONFIG_DIR / f"{handoff_id}.ovpn"
    routes_str = _routes_for_scope(scope_targets)
    config_path.write_text(
        OVPN_TEMPLATE.format(
            server=server, port=port, proto=proto, routes=routes_str,
        ),
        encoding="utf-8",
    )

    user, password = _generate_credentials()
    creds_plain = f"{user}\n{password}\n".encode("utf-8")

    if pentester_public_key_pem:
        ct = _encrypt_with_public_key(creds_plain, pentester_public_key_pem)
        return VpnArtifact(
            config_path=config_path,
            credentials_ciphertext=ct,
            encryption_method="rsa_oaep",
            symmetric_key_b64=None,
        )

    ct, sym_b64 = _encrypt_with_fernet(creds_plain)
    return VpnArtifact(
        config_path=config_path,
        credentials_ciphertext=ct,
        encryption_method="fernet_symmetric",
        symmetric_key_b64=sym_b64,
    )
