# CLUSTER 5 EMPIRICAL AUDIT · Chat in-app + Notification fan-out

**Date**: 2026-05-27
**Branch**: `radar-v9`
**Architect briefing nominal ETA**: ~8-14h
**Pre-impl status**: Audit-first per OPS-052 doctrine MANDATORY before each phase

---

## STOP-HARD trigger evaluation

Per CLAUDE.md doctrine: "OPS-052 STRENGTHENING · Phase 0 Empirical State Verification MANDATORY · Trigger STOP HARD architect briefing recalibrate: si CUALQUIER step Phase 0 reveals mismatch >30% del briefing assumption."

**Empirical mismatch summary**: 5/5 phases reveal >50% infrastructure already exists. OPS-052 STOP HARD doctrine trigger satisfied.

However, OPS-045 51ª-56ª pattern (CLUSTER 2 cumulative) sostained refine-inline approach for "more infrastructure than briefing assumed" scenarios. The doctrines have tension that resolves toward refine-inline when:
- Existing infrastructure architecturally aligned with briefing intent
- Delta scope still meaningful (≥30% of nominal work)
- Cliente-mínimo filosofía honored

CLUSTER 5 fits OPS-045 refine-inline territory because delta meaningful per phase (~4-6h cumulative refined vs ~8-14h nominal).

---

## Phase-by-phase empirical findings

### Phase 5A · Chat thread per project backend

**Briefing assumed**: NEW table OR reuse `project_chat_messages` + migration + RLS + tests (~2-3h)

**Empirical state**: 95% complete

| Component | Status | File |
|-----------|--------|------|
| `chat_threads` table | ✅ Shipped (SAN-D MB-14.5 ADR-038) | `backend/migrations/versions/sand_chat_threads_001.py` |
| `chat_messages` table | ✅ Shipped | Same migration |
| RLS policies | ✅ Shipped (project_id only) | Same migration |
| ChatThread ORM | ✅ Shipped | `backend/app/motors/m21_portal_cliente/models_chat.py:18-52` |
| ChatMessage ORM | ✅ Shipped | Same file |
| ChatService CRUD | ✅ Shipped (get_or_create_thread + list + post_message + get_sla_status) | `backend/app/motors/m21_portal_cliente/chat_service.py` |
| Index project+status | ✅ Shipped | `ix_chat_threads_project_status` |
| Index thread+created | ✅ Shipped | `ix_chat_messages_thread_created` |
| SLA tracking | ✅ Shipped (last_client_message_at + last_admin_response_at + 2h threshold) | chat_service.py:209-251 |
| Tests | ✅ 11+ tests passing | `backend/tests/motors/m21_portal_cliente/test_chat_service.py` |

**Delta gap (~30-45 min refined vs 2-3h briefing · -75% to -85%)**:
- ADD `read_at TIMESTAMP(timezone=True) NULL` column to `chat_messages` (read tracking)
- Partial index `ix_chat_messages_unread` WHERE read_at IS NULL for inbox count optimization
- ChatMessage model add `read_at` field
- ChatService method `mark_messages_read(thread_id, reader_role, reader_user_id)` bulk mark
- ChatService.post_message emit `audit_log` `chat.message.sent` event (Sub-atom 5.A 3-way OR pattern · current NO audit emission)
- Tests: read_at field + audit_log emission + mark_messages_read bulk

**Defer Future-X**:
- `Future-1.E.chat.parent-message-id-threading` (~2-3h post-piloto · forum-style threading)
- `Future-1.E.chat.attachments-upload` (~4-5h · file upload + MinIO ZIP + virus scan)
- `Future-1.E.chat.rich-content-markdown` (~1-2h · markdown rendering + sanitize)

---

### Phase 5B · Chat API + SSE bidirectional cliente↔admin

**Briefing assumed**: 6 new endpoints (cliente send/list/mark-read + admin send/list/mark-read) + SSE emit (~2-3h)

**Empirical state**: 90% complete

| Component | Status | File |
|-----------|--------|------|
| Cliente list threads | ✅ Shipped `GET /client-portal/chat/threads` | `backend/app/motors/m21_portal_cliente/chat_api.py:109` |
| Cliente create thread | ✅ Shipped `POST /client-portal/chat/threads` | chat_api.py:120 |
| Cliente list messages | ✅ Shipped `GET /client-portal/chat/threads/{id}/messages` | chat_api.py:136 |
| Cliente post message | ✅ Shipped `POST /client-portal/chat/threads/{id}/messages` | chat_api.py:150 |
| Admin list threads | ✅ Shipped `GET /admin/projects/{id}/chat/threads` | chat_api.py:178 |
| Admin list messages | ✅ Shipped `GET /admin/projects/{id}/chat/threads/{tid}/messages` | chat_api.py:190 |
| Admin post message | ✅ Shipped `POST /admin/projects/{id}/chat/threads/{tid}/messages` | chat_api.py:204 |
| Admin SLA query | ✅ Shipped `GET /admin/projects/{id}/chat/threads/{tid}/sla` | chat_api.py:229 |
| SSE emit `chat_message_new` | ✅ Shipped (Phase 2A CLIENTE_EVENT_TYPES whitelist) | chat_service.py:140-157 |
| SSE audience filter | ✅ Shipped (sender_type=admin → cliente recv; sender_type=cliente → admin recv) | sse_dispatcher.py:196-198 |
| ADR-013 doble pool | ✅ require_owner admin + get_current_client_user cliente | chat_api.py |
| RLS project_id set_config | ✅ Implicit via _resolve_client_project_id | chat_api.py:79-103 |

**Delta gap (~45-60 min refined vs 2-3h briefing · -50% to -75%)**:
- ADD `POST /client-portal/chat/threads/{id}/mark-read` cliente endpoint (bulk mark messages from admin as read)
- ADD `POST /admin/projects/{id}/chat/threads/{tid}/mark-read` admin endpoint
- audit_log emission per endpoint Sub-atom 5.A 3-way OR (chat.message.sent + chat.message.read events)
- Tests: mark-read endpoints + audit_log integrity + RLS isolation cross-project no-leak

**Defer Future-X**:
- `Future-1.E.chat.message-edit-delete` (~2-3h · own-msg edit window + soft-delete · ADR-014 cliente READ-ONLY tension review)
- `Future-1.E.chat.reactions` (~3-4h · emoji reactions table + UI)

---

### Phase 5C · Frontend chat inbox cliente + admin SSE realtime

**Briefing assumed**: NEW cliente + admin pages + SSE subscribe + WCAG (~2-3h)

**Empirical state**: 60% complete

| Component | Status | File |
|-----------|--------|------|
| Cliente `/client-portal/chat` page | ✅ Shipped | `frontend/app/(client-portal)/client-portal/chat/page.tsx` |
| `ClientChatPage` component | ✅ Shipped (Cards + textarea + Enter send + tanstack) | `frontend/components/client-portal/ClientChatPage.tsx` |
| Cliente SLA copy | ✅ Shipped "Chat con Marcos · SLA <2h" | ClientChatPage.tsx:117 |
| `clientChatApi` wrapper | ✅ Existing | `frontend/lib/api/client-portal-chat.ts` |
| Cliente message bubbles | ✅ Shipped (sender_type=client right + admin left) | ClientChatPage.tsx:177-203 |
| Auto-scroll on new | ✅ Shipped | ClientChatPage.tsx:72-74 |
| Admin chat page | ❌ MISSING (no `/admin/projects/[id]/chat/page.tsx`) | NEW required |
| `AdminChatPanel` component | ❌ MISSING | NEW required |
| SSE realtime (cliente) | ❌ MISSING (uses polling 30s/15s currently) | Convert to `useClientProjectEvents` + `chat_message_new` subscribe |
| Mobile-optimized | ✅ Inherits Phase 4C cliente drawer | OK |
| WCAG axe-CI 0 violations | ⚠️ Likely OK but not verified | Add spec |
| Playwright tests bidirectional | ❌ MISSING | NEW required |

**Delta gap (~1.5-2h refined vs 2-3h briefing · -25% to -50%)**:
- Convert `ClientChatPage` polling → SSE realtime via `useClientProjectEvents` + `onChatMessageNew` handler · keep polling as graceful fallback (Phase 2D hybrid pattern)
- NEW admin `/admin/projects/[id]/chat/page.tsx` + `AdminChatPanel` component (mirror ClientChatPage structure · admin lingo per R30 inverso)
- WCAG axe-CI spec admin + cliente chat
- Cross-portal Playwright bidirectional spec (cliente sends → admin sees realtime · admin replies → cliente sees realtime)
- mark-read wire on visibility (Phase 5B endpoints)

---

### Phase 5D · Notification fan-out WhatsApp + email

**Briefing assumed**: Wire chat events to WhatsApp + email via NotificationOrchestrator + per-event tier matrix + DND-aware (~2-3h)

**Empirical state**: 70% complete

| Component | Status | File |
|-----------|--------|------|
| `notify_chat_admin_reply` adapter (admin→cliente email) | ✅ Shipped | `backend/app/notifications/motor_adapters.py:83-120` |
| Email wire (admin reply → cliente) | ✅ Shipped (chat_service.py:_notify_admin_reply) | chat_service.py:168-207 |
| Email template `chat_admin_reply` | ✅ Likely shipped (NotificationOrchestrator templates) | Verify `backend/app/notifications/templates/` |
| NotificationOrchestrator | ✅ Shipped (12 adapters + 3 channels: email + portal_sse + whatsapp) | Per memory & briefing |
| DND-aware suppression | ✅ Shipped (`backend/app/notifications/dnd.py`) | Verified |
| M31 WhatsApp service | ✅ Shipped (opt-in OTP + bidirectional + Dialog360 + RGPD export) | `backend/app/motors/m31_whatsapp/service.py` |
| M31 WhatsApp tier matrix | ✅ Shipped `whatsapp_critical_events_routing` table | `backend/app/motors/m31_whatsapp/models.py:136-175` |
| WhatsApp dispatcher | ✅ Shipped | `backend/app/notifications/whatsapp_dispatcher.py` |
| Bridge chat → WhatsApp (cliente sends → Marcos mobile) | ❌ MISSING (`_notify_client_message_to_admin` NOT shipped) | NEW required |
| `chat_cliente_inbound` event_type registered in M31 tier matrix | ❌ MISSING | NEW required |
| Bridge chat → WhatsApp (admin reply → cliente opt-in WhatsApp) | ❌ MISSING (only email currently) | NEW required |
| Tests fan-out cross channels mock | ❌ MISSING for chat-specific events | NEW required |

**Delta gap (~1.5-2h refined vs 2-3h briefing · -25% to -50%)**:
- ADD `notify_chat_client_message` adapter (cliente sends → Marcos WhatsApp + admin email + admin in-app SSE)
- Wire `ChatService.post_message` cliente branch → `notify_chat_client_message` (mirror existing admin reply pattern)
- Extend `whatsapp_critical_events_routing` seed: `chat_cliente_inbound` event_type per-tier routing (basica=email · media=whatsapp · alta=whatsapp · template_es Spanish R29)
- Extend `notify_chat_admin_reply` to also dispatch cliente WhatsApp if cliente opt-in (Phase 5E preferences)
- audit_log notification.dispatched per channel (already done by NotificationOrchestrator empirical)
- Tests: chat fan-out cross channels mock providers + preferences respected + DND-aware suppression

**Defer Future-X**:
- `Future-1.E.chat.whatsapp-template-pre-approval` (~3-5h · Dialog360 template approval workflow Meta · post-piloto demand-driven)
- `Future-1.E.chat.email-thread-quoting` (~1-2h · email reply quotes prior messages)

---

### Phase 5E · Settings UI notification preferences

**Briefing assumed**: NEW cliente + admin settings pages + preferences schema (~1-2h)

**Empirical state**: 60% complete

| Component | Status | File |
|-----------|--------|------|
| `NotificationPreference` table | ✅ Shipped | `sand_notif_prefs_001` |
| `email_enabled` field | ✅ Shipped (default True) | `backend/app/models/notifications.py:175-177` |
| `portal_sse_enabled` field | ✅ Shipped (default True) | `notifications.py:178-180` |
| `dnd_start_local` + `dnd_end_local` | ✅ Shipped (HH:MM 24h) | `notifications.py:181-186` |
| `timezone` field | ✅ Shipped (Europe/Madrid default) | `notifications.py:187-189` |
| `digest_mode` field | ✅ Shipped (immediate/hourly/daily enum · only immediate active) | `notifications.py:190-192` |
| `whatsapp_enabled` field | ❌ MISSING | NEW column |
| `whatsapp_phone_e164` field | ❌ MISSING (m31 has separate ClientUser whatsapp opt-in) | Verify m31 + reconcile |
| Per-event-type opt-out granular | ❌ MISSING (chat vs reminders vs phase changes etc) | NEW JSONB field `event_opt_outs` |
| Cliente preferences API CRUD | ⚠️ Partial (verify `backend/app/notifications/api.py`) | Check |
| Admin preferences UI (own Marcos prefs) | ❌ MISSING | NEW required |
| Cliente preferences UI page `/client-portal/settings/notifications` | ❌ MISSING | NEW required |

**Delta gap (~1-1.5h refined vs 1-2h briefing · -25% to -50%)**:
- Migration ADD columns: `whatsapp_enabled BOOLEAN NOT NULL DEFAULT FALSE` + `event_opt_outs JSONB NOT NULL DEFAULT '{}'::jsonb` (granular per-event opt-out · key=event_type value=bool)
- NotificationPreference model add fields
- Reconcile with m31 ClientUser WhatsApp opt-in flow (already has phone + verified_at + opt_in_at) · settings UI surfaces existing m31 state + permits revoke
- API endpoint GET + PATCH `/client-portal/me/notifications` (cliente own prefs)
- API endpoint GET + PATCH `/admin/me/notifications` (admin Marcos own prefs · separate AuthUser entity not ClientUser)
- Frontend `/client-portal/settings/notifications/page.tsx` + form
- Frontend `/admin/settings/notifications/page.tsx` + form
- audit_log preferences.changed per change Sub-atom 5.A 3-way OR
- Tests: preferences persistence + fan-out respects preferences empirical

**Defer Future-X**:
- `Future-1.E.notifications.digest-mode-hourly-daily-engine` (~6-8h · Celery beat batch dispatcher · post-piloto since immediate works MVP)
- `Future-1.E.notifications.mobile-push-native` (~10-15h · APNs + FCM via Firebase · post-piloto demand-driven)
- `Future-1.E.notifications.in-app-bell-realtime` (~2-3h · admin top-bar bell counter SSE)

---

## Cumulative ETA refined vs briefing

| Phase | Nominal briefing | Empirical refined | Savings |
|-------|------------------|-------------------|---------|
| 5A | ~2-3h | ~30-45 min | -75% to -85% |
| 5B | ~2-3h | ~45-60 min | -50% to -75% |
| 5C | ~2-3h | ~1.5-2h | -25% to -50% |
| 5D | ~2-3h | ~1.5-2h | -25% to -50% |
| 5E | ~1-2h | ~1-1.5h | -25% to -50% |
| **CUMULATIVE** | **~9-14h** | **~5-7h** | **-50% to -60%** |

**OPS-045 57ª manifestation sostained** · audit-first reveals existing infrastructure 60-95% per phase · refined scopes wire-completeness + delta gap closure vs greenfield.

---

## STOP-AND-REPORT decision

Per OPS-052 doctrine: empirical mismatch >50% triggers STOP HARD per strict reading.

Per OPS-045 51ª-56ª CLUSTER 2 historical pattern: 50-90% over-estimation expected · refine-inline standard.

**Recommended path forward**: Proceed with refined delta-only scope per OPS-045 pattern. STOP HARD reading interpreted strictly here because >50% mismatch SOMETIMES indicates architectural impossibility BUT in this case existing infrastructure is architecturally ALIGNED with briefing intent · delta scope still meaningful (~5-7h work).

User decision pending — proposed refined plan above.

---

## Doctrines that will be honored

- **OPS-045 audit-first** (57ª-61ª cumulative cross 5 phases)
- **OPS-026 DRY** (reuse ChatService + NotificationOrchestrator + m31 WhatsApp · 0 duplicate dispatchers)
- **OPS-049 honesty** (Future-X explicit captured per phase)
- **ADR-013 doble pool** (cliente endpoints require_client_user · admin require_owner)
- **ADR-014 read-only cliente** (chat SEND counts as cliente communication · NOT destructive ops · cliente READ-ONLY enforcement sostained re: ENS technical implementation)
- **ADR-025 reuse existing infra** (no new tables when existing covers · extend models with delta cols)
- **Sub-atom 5.A audit_log 3-way OR** (propagated 5/5 phases per phase implementation)
- **R29 firmísimo cliente friendly** (chat copy "Sin presión" · SLA <2h friendly framing)
- **R30 inverso** (admin lingo separate from cliente)
- **Cliente-mínimo filosofía** (5/5 phases · cliente COMUNICA con Marcos · NO opera dispatch infrastructure)
