"""Tests del núcleo cripto del agente · m_remediation (ADR-055 Fase 3).

El guard de seguridad más importante: el agente SOLO ejecuta comandos que (1) están
en su allowlist de playbooks y (2) llevan firma válida del servidor. Cualquier
manipulación o playbook desconocido → rechazo (fail-closed).
"""
from __future__ import annotations

import pytest

from backend.app.motors.m_remediation.agent_protocol import (
    PLAYBOOK_ALLOWLIST,
    CommandValidationError,
    canonical_bytes,
    generate_keypair,
    public_from_private,
    sign_payload,
    validate_command,
    verify_payload,
)


def test_canonical_bytes_deterministic_order() -> None:
    a = canonical_bytes({"b": 1, "a": 2})
    b = canonical_bytes({"a": 2, "b": 1})
    assert a == b  # orden de claves no afecta (sort_keys)


def test_sign_and_verify_roundtrip() -> None:
    priv, pub = generate_keypair()
    payload = {"playbook_id": "harden_sshd_root_login", "x": 1}
    sig = sign_payload(priv, payload)
    assert verify_payload(pub, payload, sig) is True


def test_verify_fails_on_tamper() -> None:
    priv, pub = generate_keypair()
    payload = {"playbook_id": "harden_sshd_root_login", "x": 1}
    sig = sign_payload(priv, payload)
    tampered = {"playbook_id": "harden_sshd_root_login", "x": 2}
    assert verify_payload(pub, tampered, sig) is False


def test_verify_fails_wrong_key() -> None:
    priv1, _ = generate_keypair()
    _, pub2 = generate_keypair()
    payload = {"playbook_id": "enable_host_firewall_rule"}
    sig = sign_payload(priv1, payload)
    assert verify_payload(pub2, payload, sig) is False


def test_public_from_private_matches() -> None:
    priv, pub = generate_keypair()
    assert public_from_private(priv) == pub


def test_validate_command_accepts_valid() -> None:
    priv, pub = generate_keypair()
    payload = {"playbook_id": "harden_sshd_root_login", "command_id": "c1"}
    sig = sign_payload(priv, payload)
    # No lanza.
    validate_command(
        server_public_raw=pub, command_payload=payload, signature_hex=sig,
    )


def test_validate_command_rejects_unknown_playbook() -> None:
    priv, pub = generate_keypair()
    payload = {"playbook_id": "rm_rf_slash", "command_id": "c1"}
    sig = sign_payload(priv, payload)
    with pytest.raises(CommandValidationError):
        validate_command(
            server_public_raw=pub, command_payload=payload, signature_hex=sig,
        )


def test_validate_command_rejects_tampered_signature() -> None:
    priv, pub = generate_keypair()
    payload = {"playbook_id": "harden_sshd_root_login", "command_id": "c1"}
    sig = sign_payload(priv, payload)
    payload["command_id"] = "c2"  # manipular tras firmar
    with pytest.raises(CommandValidationError):
        validate_command(
            server_public_raw=pub, command_payload=payload, signature_hex=sig,
        )


def test_validate_command_rejects_missing_playbook() -> None:
    priv, pub = generate_keypair()
    payload = {"command_id": "c1"}
    sig = sign_payload(priv, payload)
    with pytest.raises(CommandValidationError):
        validate_command(
            server_public_raw=pub, command_payload=payload, signature_hex=sig,
        )


def test_allowlist_matches_host_catalog() -> None:
    # La allowlist del agente debe coincidir con las acciones host del catálogo.
    from backend.app.motors.m_remediation.catalog import actions_for_provider

    host_actions = {a.action_type for a in actions_for_provider("host")}
    assert host_actions == set(PLAYBOOK_ALLOWLIST)
