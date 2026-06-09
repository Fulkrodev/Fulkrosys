# Motor 29 · Client Messaging

Mensajería bidireccional cliente ↔ Marcos con captura adjuntos, email forward, notifications. Integrado con M30 Contacts (composer admin permite seleccionar contacto destinatario). Plan v4.2 FASE 6.A backend. Arquitectura cement: 2 tablas (`client_messages` + `client_message_attachments`) + RLS `client_isolation` + EmailSender + MinIO bucket `fulkro-client-messages` + Celery digest diario.

## Funcionalidades

- **Mensajería bidireccional** cliente ↔ Marcos · pool RLS (cliente ve solo sus mensajes · admin bypassa via `SET LOCAL ROLE fulkro`).
- **Attachments** MinIO bucket `fulkro-client-messages` + signed URLs TTL 7d + MIME whitelist + 10MB size limit.
- **Email forward** EmailSender consolidado + override `contact.email` si `to_contact_id` presente (composer admin selecciona contacto M30).
- **Notifications inbox** integration M21 `notifications_inbox_api`.
- **Cleanup attachments Celery** TTL expirado + digest diario (`tasks.py`).
- **Auto-log interaction M30** al enviar/responder mensaje a contacto (cross-motor).
- **Full-text search GIN** index sobre mensajes (admin `search_messages`).
- **Mark as read** idempotente per pool.
- **Unread count** badge sidebar.
- **Soft delete** owner only (preserva audit trail).

## Stats empírico

| Métrica | Valor |
|---|:---:|
| LOC | 2.557 |
| Files | 9 |
| Status | production-grade · Sub-fase 6.A backend complete |
| Tests | `backend/tests/motors/m29_client_messaging/` |
| API prefix | admin `/admin/messages/*` + cliente `/client-portal/messages/*` |
| RBAC | Mixed · admin via `require_owner` + cliente via cookie+CSRF |

## Key files

- `api_admin.py` · endpoints admin (composer · inbox · search · responder)
- `api_client.py` · endpoints cliente portal (send · list threads · view thread)
- `service.py` · `ClientMessagingService` core 9 métodos (cliente + admin + común)
- `models.py` · ORM `client_messages` + `client_message_attachments`
- `attachments.py` · MinIO upload + signed URLs + MIME whitelist
- `email_forward.py` · EmailSender wire-up + contact override
- `schemas.py` · Pydantic in/out
- `tasks.py` · Celery jobs (cleanup attachments · digest diario)

⚠️ NO existe `api.py` único · scope split per pool (`api_admin.py` · `api_client.py`).

## DB tables

Motor-specific (ORM en `models.py`):

- `client_messages` · mensajes bidireccionales con `sender_pool` (client | admin) + `to_contact_id` opcional
- `client_message_attachments` · adjuntos MinIO con signed URL TTL 7d

RLS · `client_isolation` policy (cliente solo ve sus mensajes · admin bypassa via `SET LOCAL ROLE fulkro`). Full-text search GIN index.

## Cross-motor integration

- **Inbound**: ninguno directo (motor entrada UI cliente + admin cockpit)
- **Outbound**:
  - M21 Portal Cliente (auth ClientUser + notifications inbox)
  - M30 Client Contacts (auto-log interaction al enviar mensaje a contacto)
- **LLM agents**: ninguno (motor mensajería pura)

## ADRs referenced

- ADR-005 · M29 Client Messaging motor nuevo (cement decisión inicial)

## Cement OPS

Plan v4.2 FASE 6 cement. RLS `client_isolation` es invariante security (cross-tenant leakage = breach). MinIO bucket dedicated + signed URLs TTL 7d es cement (anti hot-link + signed access). Auto-log interaction M30 es invariante cross-motor (timeline cliente preserved).
