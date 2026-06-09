"""Motor 7 -- Router publico Evidence (sin auth router-level).

Contiene endpoints disenados publicos para verificacion criptografica
de firmas Ed25519 sin sesion autenticada.

Refs: H53 fix (10.C audit cross-motor) -- separar paths publicos del
router con dependencies=[require_marcos_or_client] router-level.
"""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from backend.app.motors.m07_evidence.signing import get_public_key_pem


public_router = APIRouter(tags=["Motor 7 - Evidence (public)"])


class PublicKeyResponse(BaseModel):
    algorithm: str = "Ed25519"
    public_key_pem: str


@public_router.get("/evidence/public-key", response_model=PublicKeyResponse)
async def get_public_key():
    """Return the Ed25519 public key used to sign evidence (no auth).

    Endpoint PUBLICO (sin auth) para verificacion firmas Ed25519.
    Disenado para clientes externos que reciben documentos firmados
    y necesitan verificar la firma criptograficamente sin sesion.
    """
    pem = get_public_key_pem()
    return PublicKeyResponse(public_key_pem=pem)
