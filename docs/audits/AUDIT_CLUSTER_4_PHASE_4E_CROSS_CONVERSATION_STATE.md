# AUDIT CLUSTER 4 Phase 4E · Cross-Conversation Continuity Empirical State

**Sesión**: 3B-2B.8 CLUSTER 4 Phase 4E
**Fecha**: 2026-05-26
**Status**: ✅ **Audit complete · scope refined cliente conversation read + auto-persist · NO STOP HARD**

## Empirical findings

- ✅ **CopilotConversation + CopilotMessage models** existing · project_id + client_id (Phase 2.1) + role + content + citations
- ✅ Admin endpoints conversations CRUD existing
- ✅ portal_copiloto_chat (Phase 2E) + portal_copiloto_coach (Phase 4A) functional
- ❌ **portal_copiloto_chat + coach NOT persist messages** to copilot_conversations/messages (stateless · sin continuity)
- ❌ **NO cliente endpoints** acceder conversation history
- ❌ **NO context preservation** cross sessions (each Q&A standalone)

## Refined scope Phase 4E (~2-3h)

1. NEW `m11_copiloto/conversation_service.py` pure functional:
   - `get_or_create_active_conversation(db, project_id, client_user_id, client_id)` (single active conversation per cliente_user+project session)
   - `persist_message(db, conversation_id, role, content, ...metadata)`
   - `get_recent_messages(db, conversation_id, limit=10)` for context preservation
2. NEW cliente endpoints:
   - GET /client-portal/copilot/conversations · own list
   - GET /client-portal/copilot/conversations/{id}/messages
3. Wire portal_copiloto_chat + coach to call persist_message (best-effort)
4. Optional: inject get_recent_messages context into LLM call (multi-turn awareness)
5. audit_log Sub-atom 5.A `cliente.conversation.viewed`

## Pattern formalizable
- Conversation persistence + context preservation per cliente_user + project session
- Best-effort persistence side-effect (primary Q&A NUNCA blocked by persistence fail)
