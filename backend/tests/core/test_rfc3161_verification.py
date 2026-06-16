"""RFC3161 full verification · CMS signature + EKU + validity + X.509 chain.

Uses a REAL freeTSA token captured as a fixture, so the manual CMS verification
path is exercised end-to-end: a valid token verifies, while a tampered token, a
wrong artifact digest, or an untrusted CA are rejected. The real fixture is what
makes the hand-rolled CMS signature check safe to ship (a subtly-wrong
implementation that accepts forged tokens would fail these tests).
"""
from __future__ import annotations

import datetime
from pathlib import Path

from backend.app.core.timestamping.rfc3161 import (
    default_ca_bundle,
    verify_timestamp,
    verify_timestamp_token,
)

_FIX = Path(__file__).resolve().parents[1] / "fixtures" / "tsa"
_TOKEN = (_FIX / "freetsa_token.tsr").read_bytes()
_DIGEST = (_FIX / "freetsa_digest.txt").read_text().strip()
_CA = default_ca_bundle("https://freetsa.org/tsr")


def test_bundled_ca_present():
    assert _CA is not None and b"BEGIN CERTIFICATE" in _CA


def test_imprint_only_still_works():
    assert verify_timestamp(_TOKEN, _DIGEST) is True


def test_full_verify_valid_token_with_chain():
    ok, reason = verify_timestamp_token(_TOKEN, _DIGEST, trusted_ca_pem=_CA)
    assert ok is True, reason


def test_full_verify_valid_token_without_ca_skips_chain():
    ok, reason = verify_timestamp_token(_TOKEN, _DIGEST, trusted_ca_pem=None)
    assert ok is True, reason


def test_wrong_digest_rejected():
    ok, reason = verify_timestamp_token(_TOKEN, "00" * 32, trusted_ca_pem=_CA)
    assert ok is False
    assert "imprint" in reason


def test_tampered_signature_rejected():
    bad = bytearray(_TOKEN)
    bad[-15] ^= 0xFF  # flip a byte inside the trailing TSA signature
    ok, _ = verify_timestamp_token(bytes(bad), _DIGEST, trusted_ca_pem=_CA)
    assert ok is False


def test_untrusted_ca_breaks_chain():
    """A valid but unrelated self-signed cert is not the freeTSA issuer."""
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import NameOID

    key = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "bogus-ca")])
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(1)
        .not_valid_before(datetime.datetime(2020, 1, 1))
        .not_valid_after(datetime.datetime(2035, 1, 1))
        .sign(key, hashes.SHA256())
    )
    bogus_ca = cert.public_bytes(serialization.Encoding.PEM)
    ok, reason = verify_timestamp_token(_TOKEN, _DIGEST, trusted_ca_pem=bogus_ca)
    assert ok is False
    assert "cadena" in reason
