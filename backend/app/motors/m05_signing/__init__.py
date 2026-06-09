"""Motor 05 — In-portal signing service · SAN-E v3.MB-5.2.

Sibling de m05_obligations (pattern m10/m21 parallel motors). Backend-only
in-portal signing replacement para magic_link cliente flow (DEPRECATED
MB-4.bis3 ADR-020 IMPLEMENTED FULLY).

Ed25519 + hash chain audit + step-up OTP per docs críticos. Cliente firma
documentos in-portal · 0 magic links cliente.

Modules:
- models.py · ORM SigningIntent · SigningEvent · SigningOtpCode
- signable_types.py · 11 SignableType + REQUIRES_STEP_UP_OTP frozenset
- keypair.py · process-level Ed25519 (reuse pattern var/keys/)
- service.py · SigningService core (intent · OTP · sign · chain integrity)
- schemas.py · Pydantic in/out
- exceptions.py · domain errors
- api.py · 6 endpoints client + 1 admin chain integrity
"""
