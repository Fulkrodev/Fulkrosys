# Motor 12 · Magic Link Engine

Generación, consumo y revocación criptográfica de magic links: JWT firmados Ed25519 (EdDSA) + OTP 6-dígitos + rate limiting + geo-restriction (prepared). Permite a clientes ejecutar operaciones específicas (firmar docs, subir evidence, autorizar pentests, etc.) sin necesidad de cuentas. **Hub crítico inbound**: 9 motores upstream lo consumen.

## Funcionalidades

- **JWT Ed25519** generation con TTL configurable + token NEVER stored in DB (solo `token_hash` SHA-256).
- **OTP 6-digit TOTP** vía canal separado cuando purpose requiere step-up (OTP hash stored, never plaintext).
- **Rate limiting**: 3 OTP failures → link permanently invalidated.
- **Geo-restriction prepared** · `allowed_countries` JSONB (NOT enforced yet · forward).
- **Audit trail** every action → `client_interactions` table (append-only).
- **9 purpose types** (`purposes.py` · MagicLinkPurpose enum): FIRMA_DOCUMENTO · UPLOAD_EVIDENCE · AUTORIZAR_PENTEST · ONBOARDING · etc.
- **Policy enforcer** (`policy_enforcer.py`) per-purpose policy (TTL · IP restrictions · attempts max).
- **Migration log** (`models_migration_log.py`) tracking de migration history magic-link policy ADR-042.
- **Email templates** (`emails/` subdir) per-purpose template renderers.
- **Generic 403 response** en `/consume` (evitar information leakage al atacante).
- **Endpoints públicos**: `/consume` solo valida por token (sin tenant context); status público vía `MagicLinkPublicStatus`.

## Stats empírico

| Métrica | Valor |
|---|:---:|
| LOC | 2.949 |
| Files | 9 (+1 subdir `emails/`) |
| Status | production-grade · spec v2.1 |
| Tests | `backend/tests/motors/m12_magic_link/` |
| API prefix | `/api/v1/magic-links/*` |
| RBAC | Admin (`require_owner`) generate/revoke/status + público `/consume` (token-only) |

## Key files

- `api.py` · endpoints HTTP (generate · consume · revoke · status · list)
- `service.py` · `MagicLinkService` core (JWT gen + token_hash + OTP + rate limiting)
- `purposes.py` · 9 `MagicLinkPurpose` enum types
- `policy_enforcer.py` · per-purpose policy rules
- `models_migration_log.py` · ORM `magic_link_migration_log`
- `schemas.py` · Pydantic in/out
- `emails/` · subdir email templates per purpose

## DB tables

Motor-specific:
- `magic_link_migration_log` (ORM en `models_migration_log.py`) · tracking ADR-042 policy migration

Y modelos compartidos `MagicLink` (`backend/app/models/magic_links.py`) + `ClientInteraction` (audit trail · append-only).

RLS por `magic_links` + `client_interactions`.

## Cross-motor integration

- **Inbound** (motores que consume M12 magic-link · **9 motores hub más grande FULKRO**):
  - M01 Categorization (firma E.012)
  - M02 MAGERIT
  - M03 DdA (firma E.040)
  - M08 Verification (autorización pentest cliente)
  - M14 Contracts (firma contratos)
  - M16 Onboarding (interlocutor magic-link sin cuenta)
  - M18 Communication (notificaciones cliente vía link)
  - M19 Risk (incidents reporting cliente)
  - M25 Lifecycle (renewal links)
- **Outbound**: M30 Client Contacts (data interlocutor)
- **LLM agents**: ninguno (motor criptográfico determinístico)

## Limitaciones conocidas

### Geo-restriction prepared but NOT enforced

`allowed_countries` JSONB existe en schema y se persiste, pero el enforcement runtime NO está activo. Decisión: feature preparada para activación post-cliente con compliance requirement geo-specific.

## ADRs referenced

- ADR-011 · Magic Links auditoría + ampliación + email destinatario configurable
- ADR-013 · separación arquitectónica de portales
- ADR-020 · tablas sessions separadas con cookie común + dual dispatcher
- ADR-041 · referenced en código
- ADR-042 · magic-link policy híbrida final (SAN-D MB-19.B) — driver de `migration_log`

## Cement OPS

Hub inbound más grande FULKRO (9 motores upstream). Token NEVER stored in DB es invariante criptográfico ENS. Generic 403 en `/consume` es invariante security (anti information leakage). Spec v2.1 cement.
