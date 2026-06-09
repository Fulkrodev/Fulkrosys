# ADR-052 · Copilot SSE streaming wire-up · distinct intent vs generic `/agents/{id}/invoke`

**Status**: Accepted · 2026-05-13 (FASE 2 H5 cement post audit-driven CANCEL)
**Cement**: OPS-061 7ª aplicación cumulative · audit-first reveal vaporware-style finding

## Context

Audit O2 / O15 (2026-05-13) detectó:

> "Copilot DevHint 'streaming mock' · POST /api/v1/agents/14/invoke backend pendiente"
> — `O2_FRONTEND_ADMIN_INVENTORY.md` línea 441 / 452 / 470 / 477
> — `O15_CONSOLIDATED_SUMMARY.md` HIGH PRIORITY #10 línea 128 + O2 row línea 53

Pre-audit empirical FASE-2-H5 reveló **wire-up YA implementado 100%** desde S11.A copilot SSE expansion. El audit finding cita un endpoint path (`/agents/14/invoke`) que **NUNCA fue el path real** · el path empírico es `/api/v1/copilot/chat/stream` (M11 motor wrapper dedicated per ADR-049 cement 3 surfaces architectural).

## Empirical findings (audit-driven sostained · OPS-026 45ª aplicación)

### Cadena wire-up SSE Copilot (todos los layers REAL)

| Layer | Path | Status |
|---|---|---|
| Frontend hook | `frontend/hooks/useCopilot.ts` | ✅ REAL · calls `chatWithCopilotStream` (NO mock) |
| Frontend lib | `frontend/lib/api/copilot.ts:176` | ✅ REAL · `fetch("/api/v1/copilot/chat/stream", POST)` + `ReadableStream` parser SSE |
| Backend router | `backend/app/motors/m11_copiloto/api.py:175` | ✅ REGISTERED · `@router.post("/copilot/chat/stream")` · `StreamingResponse` + `media_type="text/event-stream"` |
| Backend service | `backend/app/agents/agent_14_copiloto/service.py` | ✅ 20.454 LOC · `stream_answer_question` AsyncIterator pipeline (detect_filters → hybrid_search → build_messages → LLM stream → validate → log) |
| LLM SDK | `backend/app/core/ai/llm_router.py:31` | ✅ Anthropic SDK direct (`from anthropic import (...)`) · post-H6 cement (NO litellm) |
| Tests | `backend/tests/motors/m11_copiloto/test_copilot_stream.py` | ✅ **2/2 PASSED** · `test_stream_emits_citation_frames_with_mock_llm` validates frame sequence (start → delta → citation → done) |

### SSE events streaming wire-up real

Frontend `useCopilot.ts` consume eventos SSE:
- `delta` (token chunks) → append a assistant message
- `citation` (chunk citations) → push enriched chip
- `done` (final metadata) → finalize confidence/corpus_gap/chunks_used
- `error` → throw + catch UI

Backend `stream_answer_question` (service.py) emite mismos frames con `data: <json>\n\n` SSE format.

### Path discrepancy

| Source | Path claimed | Real path |
|---|---|---|
| Audit O2/O15 finding #5 | `/api/v1/agents/14/invoke` | NUNCA fue el path |
| Frontend DevHint banner (page.tsx:18) | `/api/v1/agents/14/invoke` | STALE · mismo audit influence |
| Frontend `useCopilot.ts` real | `/api/v1/copilot/chat/stream` | ✅ Empirical real path |
| OpenAPI registered | `/api/v1/copilot/chat/stream` | ✅ Confirmed |

Generic `/api/v1/agents/{agent_id}/invoke` endpoint **SÍ existe** (`backend/app/agents/api.py`) pero es dispatcher genérico para otros agentes (11/17/18/etc.). Agent 14 usa M11 motor wrapper dedicado per ADR-049 (3 surfaces architectural intent · admin Sheet + admin fullscreen + cliente Dock) · ese cement architectural justifica NO usar generic dispatcher.

## Decision

**Wire-up SSE Copilot REAL** preservado as-is en `/api/v1/copilot/chat/stream` (M11 motor wrapper).

**NO** crear alias `/agents/14/invoke` (anti-pattern · violaría OPS-027 existing infra reuse + ADR-049 3 surfaces architectural distinct).

**Actions ejecutadas**:
1. Remove DevHint stale del admin Copilot page (`frontend/app/(admin)/admin/copilot/page.tsx`)
2. Audit O2/O15 finding #5 RECLASSIFIED ✅ RESOLVED via audit-driven cancel
3. Cement architectural ADR-049 honored: M11 wrapper dedicated · NO generic dispatcher Agent 14

## Consequences

- `/api/v1/copilot/chat/stream` preserved as-is (wire-up real existing)
- DevHint stale banner removed (no más cliente cement confusion)
- ADR-049 3 surfaces architectural distinct cement reinforced
- NO scope creep redundant endpoint alias (OPS-027 sostained)
- Forward MB-14 polish bloque mayor: Copilot ADMIN guided mode visión Marcos (ADR-050 cement DEFER honored · NO ahora)

## OPS cement

- **OPS-026 audit-first 45ª aplicación** · pre-audit cazó audit O2/O15 #5 vaporware-style finding (path inventado + status incorrecto)
- **OPS-061 7ª aplicación cumulative** · vaporware-detection pattern (8 instancias acumuladas: M32 Capabilities · features panel path · Intelligence cross-motor · backup encryption-as-stub · ADR-037/042/043 self-collisions · copilot/copiloto H2 ADR-049 · firma/firmas-hub H3 ADR-051 · copilot streaming wire-up H5 ADR-052)
- **OPS-027 sostained** · existing infra discovery (M11 wrapper + agent_14 service + llm_router · NO build redundant)
- **OPS-062 sostained** · architectural cement con ADR explicit ≠ silent debt (ADR-049 3 surfaces honored)

## Referencias

- ADR-049 · Copilot Agent 14 · 3 surfaces architectural intent (FASE 2 H2 cement)
- ADR-050 · Copilot ADMIN guided mode visión defer MB-14 polish bloque mayor
- ADR-051 · firma/firmas-hub distinct architectural intent (FASE 2 H3 cement · OPS-061 6ª)
- DECISIONS.md `ADR-049` inline entry (3 surfaces architectural distinct intent)
- `backend/app/motors/m11_copiloto/api.py:175` · streaming endpoint real registrado
- `backend/app/agents/agent_14_copiloto/service.py` · stream_answer_question pipeline
- `frontend/hooks/useCopilot.ts` · real SSE consumer (NO mock)
- `O2_FRONTEND_ADMIN_INVENTORY.md` líneas 441/452/470/477 (RECLASSIFIED ✅ RESOLVED)
- `O15_CONSOLIDATED_SUMMARY.md` HIGH PRIORITY #10 línea 128 + O2 row línea 53 (RECLASSIFIED ✅ RESOLVED)
