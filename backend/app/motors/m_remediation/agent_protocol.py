"""Protocolo cripto del agente on-prem · m_remediation (ADR-055 Fase 3).

NÚCLEO DE SEGURIDAD compartido entre el servidor (control-plane) y el agente
(binario en la infra del cliente). Pure functions · sin DB · sin I/O · testeable.

Garantías de "blindaje" (defensa en profundidad):

  1. **Comandos firmados Ed25519 por el servidor**: el agente SOLO ejecuta un
     comando si la firma del servidor valida con la clave pública que fijó (pin)
     en el enrollment. Un comando forjado/manipulado → rechazado.

  2. **Allowlist de playbooks horneada en el agente**: aunque la firma valide, el
     agente SOLO ejecuta playbooks de su allowlist (dato ≠ instrucción · espejo de
     la doctrina anti-injection M8). NUNCA shell arbitrario · NUNCA eval.

  3. **Serialización canónica**: el payload se firma sobre JSON canónico
     (sort_keys + separadores fijos) → mismo bytes en servidor y agente, sin
     ambigüedad de orden de claves.

  4. **Reports firmados por el agente**: el resultado lo firma el agente con SU
     clave; el servidor verifica con la pública del agente (integridad del report).

NO contiene la clave privada: las claves se pasan como bytes a las funciones.
"""
from __future__ import annotations

import json
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)


# Allowlist canónica de playbooks que un agente puede ejecutar (ADR-055).
# DEBE coincidir con las acciones provider='host' del catálogo. El agente la
# tiene horneada; el servidor la usa para validar antes de encolar.
PLAYBOOK_ALLOWLIST: frozenset[str] = frozenset(
    {
        "harden_sshd_root_login",
        "enable_host_firewall_rule",
        "apply_package_security_update",
    }
)


class CommandValidationError(Exception):
    """El comando NO es ejecutable (firma inválida o playbook no permitido)."""


def canonical_bytes(payload: dict[str, Any]) -> bytes:
    """Serialización canónica determinista del payload (para firmar/verificar)."""
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")


# ── claves ────────────────────────────────────────────────────────────────


def generate_keypair() -> tuple[bytes, bytes]:
    """Genera (private_raw_32, public_raw_32) Ed25519."""
    sk = Ed25519PrivateKey.generate()
    priv = sk.private_bytes_raw()
    pub = sk.public_key().public_bytes_raw()
    return priv, pub


def public_from_private(private_raw: bytes) -> bytes:
    sk = Ed25519PrivateKey.from_private_bytes(private_raw)
    return sk.public_key().public_bytes_raw()


# ── firma / verificación ────────────────────────────────────────────────────


def sign_payload(private_raw: bytes, payload: dict[str, Any]) -> str:
    """Firma el payload canónico · devuelve firma hex."""
    sk = Ed25519PrivateKey.from_private_bytes(private_raw)
    return sk.sign(canonical_bytes(payload)).hex()


def verify_payload(
    public_raw: bytes, payload: dict[str, Any], signature_hex: str,
) -> bool:
    """Verifica la firma del payload canónico. NUNCA lanza · devuelve bool."""
    try:
        pk = Ed25519PublicKey.from_public_bytes(public_raw)
        pk.verify(bytes.fromhex(signature_hex), canonical_bytes(payload))
        return True
    except (InvalidSignature, ValueError, TypeError):
        return False


# ── validación de comando (el guard que ejecuta el AGENTE) ──────────────────


def validate_command(
    *,
    server_public_raw: bytes,
    command_payload: dict[str, Any],
    signature_hex: str,
    allowlist: frozenset[str] = PLAYBOOK_ALLOWLIST,
) -> None:
    """Valida un comando ANTES de ejecutarlo. Lanza CommandValidationError si NO.

    Orden de comprobaciones (fail-closed):
      1. playbook_id presente y en la allowlist (anti-injection · dato≠instrucción)
      2. firma del servidor válida sobre el payload canónico

    Si CUALQUIERA falla → el agente NO ejecuta nada.
    """
    playbook_id = command_payload.get("playbook_id")
    if not playbook_id or playbook_id not in allowlist:
        raise CommandValidationError(
            f"Playbook no permitido o ausente: {playbook_id!r} "
            f"(allowlist={sorted(allowlist)})",
        )
    if not verify_payload(server_public_raw, command_payload, signature_hex):
        raise CommandValidationError(
            "Firma del servidor inválida · comando rechazado (posible manipulación).",
        )
