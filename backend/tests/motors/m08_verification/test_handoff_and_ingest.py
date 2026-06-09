"""Tests para external handoff + findings ingester (Checkpoint 3)."""
from __future__ import annotations


import pytest

from backend.app.motors.m08_verification.external.findings_ingester import (
    parse_structured_payload,
    REQUIRED_FIELDS_STRUCTURED,
)
from backend.app.motors.m08_verification.external.vpn_manager import (
    _encrypt_with_fernet,
    _routes_for_scope,
    generate_for_handoff,
)


# ═══════════════════════════════════════════════════════════════════
# Structured findings parser
# ═══════════════════════════════════════════════════════════════════

class TestStructuredParser:
    def _valid_finding(self, **overrides):
        base = {
            "title": "OpenSSH CVE-2024-6387",
            "severity": "critical",
            "affected_host": "srv.example.es",
            "description": "regreSSHion RCE",
        }
        base.update(overrides)
        return base

    def test_parses_list_directly(self):
        out = parse_structured_payload([self._valid_finding()])
        assert len(out) == 1
        assert out[0]["title"] == "OpenSSH CVE-2024-6387"

    def test_parses_dict_with_findings_key(self):
        out = parse_structured_payload({"findings": [self._valid_finding()]})
        assert len(out) == 1

    def test_rejects_missing_required(self):
        with pytest.raises(ValueError) as e:
            parse_structured_payload([{"title": "only title"}])
        assert "faltan" in str(e.value).lower()

    def test_rejects_non_list(self):
        with pytest.raises(ValueError):
            parse_structured_payload("not a list")

    def test_normalizes_severity_to_lowercase(self):
        out = parse_structured_payload([
            self._valid_finding(severity="CRITICAL"),
        ])
        assert out[0]["severity"] == "critical"

    def test_preserves_optional_fields(self):
        out = parse_structured_payload([
            self._valid_finding(
                cve_id="CVE-2024-6387",
                affected_port=22,
                cvss_score=9.8,
                remediation_summary="apt upgrade openssh",
            ),
        ])
        assert out[0]["cve_id"] == "CVE-2024-6387"
        assert out[0]["affected_port"] == 22
        assert out[0]["cvss_score"] == 9.8
        assert out[0]["remediation_summary"] == "apt upgrade openssh"

    def test_required_fields_catalog(self):
        assert REQUIRED_FIELDS_STRUCTURED == {
            "title", "severity", "affected_host", "description",
        }


# ═══════════════════════════════════════════════════════════════════
# VPN manager
# ═══════════════════════════════════════════════════════════════════

class TestVpnManager:
    def test_routes_derived_from_scope(self):
        routes = _routes_for_scope(["srv1.example.es:443", "srv2.example.es"])
        assert "srv1.example.es 255.255.255.255" in routes
        assert "srv2.example.es 255.255.255.255" in routes

    def test_routes_empty_when_scope_empty(self):
        routes = _routes_for_scope([])
        assert "no se pudieron derivar" in routes

    def test_fernet_symmetric_roundtrip(self):
        from cryptography.fernet import Fernet
        ct, key_b64 = _encrypt_with_fernet(b"hello world")
        assert Fernet(key_b64.encode()).decrypt(ct) == b"hello world"

    def test_generate_for_handoff_symmetric(self, tmp_path, monkeypatch):
        import uuid as _uuid
        from backend.app.motors.m08_verification.external import vpn_manager as vpn_mod
        monkeypatch.setattr(vpn_mod, "VPN_CONFIG_DIR", tmp_path)
        artifact = generate_for_handoff(
            _uuid.uuid4(),
            ["srv.example.es:443", "app.example.es"],
        )
        assert artifact.config_path.exists()
        assert artifact.encryption_method == "fernet_symmetric"
        assert artifact.symmetric_key_b64
        content = artifact.config_path.read_text()
        assert "srv.example.es" in content
        assert "AES-256-GCM" in content

    def test_generate_for_handoff_with_rsa(self, tmp_path, monkeypatch):
        import uuid as _uuid
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from backend.app.motors.m08_verification.external import vpn_manager as vpn_mod
        monkeypatch.setattr(vpn_mod, "VPN_CONFIG_DIR", tmp_path)
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        pub_pem = key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        artifact = generate_for_handoff(
            _uuid.uuid4(), ["srv.example.es"],
            pentester_public_key_pem=pub_pem,
        )
        assert artifact.encryption_method == "rsa_oaep"
        assert artifact.symmetric_key_b64 is None
