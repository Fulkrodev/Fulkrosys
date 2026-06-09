"""Pydantic schemas for auth endpoints."""
from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)


class LoginResponse(BaseModel):
    mfa_ticket: str
    webauthn: dict | None = None  # PublicKey RequestOptions when credentials exist
    totp_available: bool
    webauthn_available: bool


class WebAuthnVerifyRequest(BaseModel):
    mfa_ticket: str
    credential_id: str  # b64url
    client_data_json: str  # b64url
    authenticator_data: str  # b64url
    signature: str  # b64url


class TOTPVerifyRequest(BaseModel):
    mfa_ticket: str
    code: str = Field(min_length=6, max_length=6)


class WebAuthnRegisterBeginRequest(BaseModel):
    device_name: str | None = Field(default=None, max_length=255)


class WebAuthnRegisterBeginResponse(BaseModel):
    registration_ticket: str
    options: dict


class WebAuthnRegisterCompleteRequest(BaseModel):
    registration_ticket: str
    client_data_json: str
    attestation_object: str
    device_name: str | None = Field(default=None, max_length=255)


class MeResponse(BaseModel):
    id: str
    email: EmailStr
    display_name: str | None
    must_change_password: bool
    webauthn_credentials: int
    totp_enabled: bool
    # Role-aware claims (ADR-013 + ADR-015): role identidad de BD,
    # is_owner derivado. Frontend usa estos para AuthGuard / redirect.
    role: str
    is_owner: bool


class LogoutResponse(BaseModel):
    revoked: bool
