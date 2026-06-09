# Motor 31 · WhatsApp Business

Integración WhatsApp Business via Dialog360 BSP (Business Solution Provider · sub-procesador cement). Mensajería bidireccional cliente ↔ Marcos vía WhatsApp · opt-in OTP flow · SSE inbound stream tiempo real · RGPD art. 15 export ready · routing critical events (incidents · alerts crítico). MB-8 atom 8.1.

## Funcionalidades

- **Opt-in flow hybrid (Q3.D)**:
  1. Marcos admin invita cliente via UI · service stores OTP + sends WA template
  2. Cliente introduce phone E.164 en `/portal` · receives OTP via WA
  3. Cliente introduce OTP en `/portal` · `verify_otp` sets `verified_at` + `opt_in_at`
- **Bidireccional (Q4.C)**:
  - `send_outbound` · Marcos envía · stored as `direction='outbound'`
  - `handle_inbound` · webhook receives · stored as `direction='inbound'`
- **Dialog360 BSP client** (`dialog_360_client.py`) HTTP wrapper Dialog360 API.
- **SSE endpoint** (`sse_endpoint.py`) Server-Sent Events stream cliente real-time inbound messages.
- **RGPD art. 15 export (Q6.D)**: `export_rgpd_art15` returns all thread + messages JSON per `client_user`.
- **Critical events routing** (`whatsapp_critical_events_routing` table) routing reglas para escalation crítica.
- **Templates WhatsApp** (Dialog360 approved templates · opt-in + OTP + notifications).

## Stats empírico

| Métrica | Valor |
|---|:---:|
| LOC | 1.323 |
| Files | 6 |
| Status | production-grade · MB-8 atom 8.1 |
| Tests | `backend/tests/motors/m31_whatsapp/` (si existe) |
| API prefix | admin `/admin/whatsapp/*` + cliente `/client-portal/whatsapp/*` + webhook público |
| RBAC | Mixed · admin via `require_owner` + cliente via `get_current_client_user` + webhook público |

## Key files

- `api.py` · admin router + cliente portal router + webhook
- `service.py` · `WhatsAppService` core (opt-in · OTP · send · handle inbound · RGPD export)
- `dialog_360_client.py` · `get_default_client` wrapper Dialog360 API
- `models.py` · ORM `whatsapp_threads` + `whatsapp_messages` + `whatsapp_critical_events_routing`
- `sse_endpoint.py` · SSE stream inbound

## DB tables

Motor-specific (ORM en `models.py`):

- `whatsapp_threads` · threads bidireccionales per client_user
- `whatsapp_messages` · mensajes outbound + inbound con direction
- `whatsapp_critical_events_routing` · reglas routing escalation crítica

RLS por `whatsapp_*` tables · cliente solo ve sus threads.

## Cross-motor integration

- **Inbound**: ninguno directo (motor entrada cliente UI + webhook BSP)
- **Outbound**: M21 Portal Cliente (auth ClientUser)
- **LLM agents**: ninguno directo

## Limitaciones conocidas

### Dialog360 sub-procesador BSP cement

Dialog360 GmbH (Alemania) es sub-procesador cement registrado (DPA + SCC). Cambio de BSP requiere DPA review + cliente notification. Templates WhatsApp requieren approval Dialog360 (24-72h SLA typical).

### Opt-in flow obligatorio RGPD + WhatsApp policy

Cliente NUNCA recibe WA sin opt-in OTP verified previo. RGPD consent cement + WhatsApp Business policy estricta (anti-spam · sanción cuenta BSP).

## ADRs referenced

- ADR-038 · referenced en código motor

## Cement OPS

MB-8 atom 8.1 cement. Opt-in OTP flow es invariante RGPD + WhatsApp policy. Dialog360 como sub-procesador cement institutional (registrado MEMORY.md + sub-procesadores list). RGPD art. 15 export ready cement (cliente puede pedir todos sus datos).
