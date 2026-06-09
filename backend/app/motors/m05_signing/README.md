# Motor 5 · In-portal Signing (SAN-E v3.MB-5.2)

Servicio de firma in-portal que reemplaza el flow magic-link cliente (DEPRECATED MB-4.bis3 per ADR-020). Ed25519 + hash chain audit inmutable + step-up OTP via email para documentos críticos. Cliente firma todos los documentos directamente desde el portal · 0 magic-links cliente para firma.

## Funcionalidades

- **Create signing intent** cliente inicia flow de firma sobre un `SignableType` concreto (11 tipos: DdA, Conformidad, MAGERIT, Pentest, Policies, etc.).
- **Request OTP** 6-dígitos via email · TTL 5 min · BD storage encriptado (`signing_otp_codes`).
- **Verify OTP** máximo 5 intentos · lockout post-exhaustion · update intent state.
- **Sign action** Ed25519 signature + hash chain link (`previous_signature_hash` per project) + audit event.
- **Reject action** cliente rechaza con razón · audit log immutable.
- **Verify chain integrity** admin endpoint · audita que el hash chain del proyecto no esté roto.
- **Get intent detail** + events log (audit trail completo per intent).
- **Hash chain**: `event_hash_sha256 = SHA256(payload + previous_hash + signature)` · garantiza inmutabilidad ordenada.

## Stats empírico

| Métrica | Valor |
|---|:---:|
| LOC | 1.840 |
| Files | 9 |
| Status | production-grade · SAN-E v3.MB-5.2 |
| Tests | `backend/tests/motors/m05_signing/` |
| API prefix | `/api/v1/portal/signing/*` (cliente) · `/api/v1/admin/signing/*` (admin) |
| RBAC | Cliente (cookie session + CSRF triple binding) + Marcos admin chain integrity |

## Key files

- `api.py` · 6 endpoints cliente + 1 admin (chain integrity)
- `service.py` · `SigningService` core (intent · OTP · sign · reject · chain integrity · history)
- `models.py` · `SigningIntent` · `SigningEvent` · `SigningOtpCode` (motor-specific ORM)
- `signable_types.py` · 11 `SignableType` + `REQUIRES_STEP_UP_OTP` frozenset
- `keypair.py` · process-level Ed25519 keypair (pattern reuse `var/keys/`)
- `email_templates.py` · `render_step_up_otp_email` + `mask_email` helpers
- `exceptions.py` · domain errors (IntentNotFoundError · OtpInvalidError · HashChainBrokenError · etc.)
- `schemas.py` · Pydantic in/out (intent create · OTP request/verify · history · chain integrity)

## DB tables

Motor-specific (ORM en `models.py`):

- `signing_intents` · intents de firma per project + signable_type + state
- `signing_events` · audit log inmutable (chain SHA256)
- `signing_otp_codes` · OTPs activos + intentos + lockout state

RLS por `signing_intents` + `signing_events`.

## Cross-motor integration

- **Inbound** (motores que consumen M05_signing):
  - M06 Document Factory (firma docs generados)
  - M19 Risk (firma valoración riesgos)
  - M23 Retainer (firma retainer mensual)
  - M27 Conformity (firma conformidad final cliente)
  - M_meetings (firma actas reuniones)
- **Outbound**: M21_portal_cliente (autenticación ClientUser)
- **LLM agents**: ninguno (motor criptográfico determinístico)

## Limitaciones conocidas

### Email OTP NO enviado automáticamente este atom

El endpoint `request-otp` retorna el código OTP en plano dentro del response para que la UI frontend maneje display/email vía M18 EmailSender. Decisión simplificada para evitar coupling tight con M18 templates.

**Cuándo se implementará** · futura iteración wire-up M18 send con template `signing/step_up_otp.html` (atom 5.2.bis pendiente cement Marcos).

## ADRs referenced

- ADR-020 · IMPLEMENTED FULLY · tablas sessions separadas con cookie común + dual dispatcher (cliente in-portal review reemplaza magic-link)

## Cement OPS

Sibling de M05_obligations (numbering anomaly intencional). Hub criptográfico central: 5 motores upstream firman a través de M05_signing. Hash chain audit es invariante ENAC: cualquier ruptura levanta `HashChainBrokenError` y bloquea operaciones de firma del proyecto hasta investigación.
