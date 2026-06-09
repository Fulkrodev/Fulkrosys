"""WebAuthn helpers on top of python-fido2 (2.x).

Wraps ``Fido2Server`` with serializable state so the begin/complete
challenge can travel inside a signed MFA / registration ticket (JWT)
without server-side session storage.
"""
from __future__ import annotations

import base64
import dataclasses
import struct
from dataclasses import dataclass
from enum import Enum

from fido2.server import Fido2Server
from fido2.webauthn import (
    AttestationConveyancePreference,
    AttestedCredentialData,
    AuthenticatorAssertionResponse,
    AuthenticatorAttestationResponse,
    CollectedClientData,
    PublicKeyCredentialRpEntity,
    PublicKeyCredentialUserEntity,
    UserVerificationRequirement,
)

from backend.app.config import get_settings


_settings = get_settings()


def _rp() -> PublicKeyCredentialRpEntity:
    return PublicKeyCredentialRpEntity(
        id=_settings.webauthn_rp_id, name=_settings.webauthn_rp_name
    )


def _server() -> Fido2Server:
    return Fido2Server(_rp(), attestation=AttestationConveyancePreference.NONE)


@dataclass
class StoredCredential:
    credential_id: bytes
    public_key: bytes
    sign_count: int

    def to_attested(self) -> AttestedCredentialData:
        aaguid = b"\x00" * 16
        header = aaguid + struct.pack(">H", len(self.credential_id)) + self.credential_id
        return AttestedCredentialData(header + self.public_key)


def b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def b64url_decode(data: str) -> bytes:
    padding = 4 - (len(data) % 4)
    if padding != 4:
        data = data + ("=" * padding)
    return base64.urlsafe_b64decode(data.encode("ascii"))


def _to_json_safe(obj):
    """Recursively serialize dataclasses / enums / bytes to JSON-safe dict."""
    if isinstance(obj, bytes):
        return b64url_encode(obj)
    if isinstance(obj, Enum):
        return obj.value
    if dataclasses.is_dataclass(obj):
        return {
            f.name: _to_json_safe(getattr(obj, f.name))
            for f in dataclasses.fields(obj)
            if getattr(obj, f.name) is not None
        }
    if isinstance(obj, dict):
        return {k: _to_json_safe(v) for k, v in obj.items() if v is not None}
    if isinstance(obj, (list, tuple)):
        return [_to_json_safe(x) for x in obj]
    return obj


def serialize_state(state: dict) -> dict:
    """Make Fido2Server state JSON-safe for embedding in a JWT."""
    out = dict(state)
    uv = out.get("user_verification")
    if isinstance(uv, Enum):
        out["user_verification"] = uv.value
    return out


def deserialize_state(state: dict) -> dict:
    """Reverse of ``serialize_state`` — rebuild enum values."""
    out = dict(state)
    uv = out.get("user_verification")
    if isinstance(uv, str):
        out["user_verification"] = UserVerificationRequirement(uv)
    return out


def begin_registration(
    *,
    user_id: bytes,
    user_name: str,
    display_name: str,
    existing: list[StoredCredential],
) -> tuple[dict, dict]:
    """Return ``(publicKey options JSON, state dict)``."""
    server = _server()
    creds = [c.to_attested() for c in existing]
    user = PublicKeyCredentialUserEntity(
        id=user_id, name=user_name, display_name=display_name
    )
    options, state = server.register_begin(
        user=user,
        credentials=creds,
        user_verification=UserVerificationRequirement.PREFERRED,
    )
    return _to_json_safe(options), serialize_state(state)


def complete_registration(
    state: dict,
    client_data_json: bytes,
    attestation_object: bytes,
) -> AttestedCredentialData:
    server = _server()
    response = AuthenticatorAttestationResponse(
        client_data=CollectedClientData(client_data_json),
        attestation_object=attestation_object,
    )
    auth_data = server.register_complete(deserialize_state(state), response=response)
    return auth_data.credential_data


def begin_authentication(
    existing: list[StoredCredential],
) -> tuple[dict, dict]:
    server = _server()
    creds = [c.to_attested() for c in existing]
    options, state = server.authenticate_begin(
        credentials=creds,
        user_verification=UserVerificationRequirement.PREFERRED,
    )
    return _to_json_safe(options), serialize_state(state)


def complete_authentication(
    state: dict,
    existing: list[StoredCredential],
    credential_id: bytes,
    client_data_json: bytes,
    authenticator_data: bytes,
    signature: bytes,
) -> StoredCredential:
    """Verify the assertion; return the matching stored credential."""
    server = _server()
    creds = [c.to_attested() for c in existing]
    response = AuthenticatorAssertionResponse(
        client_data=CollectedClientData(client_data_json),
        authenticator_data=authenticator_data,
        signature=signature,
    )
    matched = server.authenticate_complete(
        state=deserialize_state(state),
        credentials=creds,
        credential_id=credential_id,
        response=response,
    )
    for c in existing:
        if c.credential_id == matched.credential_id:
            return c
    raise ValueError(
        "credential match not found after successful assertion verification"
    )
