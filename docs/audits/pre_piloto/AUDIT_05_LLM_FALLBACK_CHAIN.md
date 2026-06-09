# AUDIT #6 · Fallback LLM provider chain

**Status**: ✅ Audit empírico completo · Bloque 1 Mega-baseline item 5/11
**Date**: 2026-05-24
**Scope item**: pre-piloto #6 · "Fallback LLM provider chain · multi-provider failover"

---

## Verdict empírico

LLM Router production-grade (~456 LOC `backend/app/core/ai/llm_router.py`) con:
- Anthropic SDK oficial (litellm bypassed permanent · documented Sesion 10)
- Public exception hierarchy completa (LLMAuthError · LLMRateLimitError · LLMBackendError · LLMBadRequestError)
- Exponential backoff retries (2s/8s/32s on RateLimitError up to 3 attempts)
- Fallback model env var `ANTHROPIC_FALLBACK_MODEL` (default `claude-opus-4-6`)
- Prompt caching tracking integrated

**Gap específico identificado**: Fallback model **es STILL Anthropic-only** (model-to-model fallback) · NO existe true multi-provider failover (OpenAI · Mistral · Cohere). Si Anthropic API down completo → todos los agents fallarían simultáneamente.

**ETA empírico realista refined**:
- **Opción A · Scope-out** (Anthropic SLA suficiente): 0h · sostener current model-to-model fallback
- **Opción B · Multi-provider abstraction**: ~8-15h (provider router + OpenAI SDK + adapter pattern)
- **Opción C · Failover cache local LLM (Llama Hetzner)**: ~12-20h (ollama deploy + adapter)

---

## Stats baseline

### `backend/app/core/ai/llm_router.py` (456 LOC)
- `LLMResponse` dataclass · content + model + tokens + latency + cache metrics
- `LLMRouter` class:
  - `default_model` env `ANTHROPIC_DEFAULT_MODEL` (Sonnet 4.5)
  - `fallback_model` env `ANTHROPIC_FALLBACK_MODEL` (Opus 4.6)
  - `complete()` sync · `stream_complete()` iterator
  - `_call_with_retries()` exponential backoff 3 attempts
  - Uses `messages.stream()` workaround para non-streaming timeout >4096 tokens
- Exception hierarchy 5 classes
- `_strip_anthropic_prefix()` helper · normaliza model names

### `backend/app/agents/base.py` (297 LOC)
- `AgentBase` abstract class · 14 agents existing extend
- `_MODEL_ALIAS_MAP` · 6 aliases (sonnet-4.5/4.6 · opus-4/4.6/4.7 · haiku-4.5)
- `invoke()` async wraps sync llm_router via executor
- ENABLE_PROMPT_CACHING flag opcional

### Agents using LLM (14 archivos identificados)
- agent_02_pliegos · agent_04_redactor · agent_06_contratos · agent_11_auditor_virtual · agent_12_coach_cliente · agent_14_copiloto · agent_17_cualificador · agent_18_reunion · agent_19_propuestas · agent_20_negociacion · agent_21_discrepancias · (+ otros)

### Anthropic-only architecture
- Provider único: Anthropic SDK direct (NO LiteLLM · NO OpenAI · NO Mistral)
- Fallback model-to-model (Sonnet → Opus si Sonnet falla por capacidad)
- NO alternative provider integration

---

## Gap matrix multi-provider failover

### Scenario · Anthropic API down completo (catastrophic)
- Current: all agents fail simultáneamente · platform LLM-features unavailable
- Workaround: Marcos manual ops · sin copilot · sin A21 discrepancias · sin A11 audit virtual
- Mitigation existing: prompt caching reduce tokens 80% pero NO ayuda si API down

### Scenario · Anthropic rate-limit cliente piloto
- Current: backoff 2s/8s/32s up to 3 attempts · then fail RateLimitError exception
- Workaround: fallback model (Opus) tiene own rate limit · pero distinct quota
- Mitigation existing: dual model (Sonnet + Opus) reduce single-model bottleneck

### Scenario · Specific feature degraded (e.g. caching unavailable)
- Current: PROD code path graceful degrades sin cache (~$5x cost increase)
- Acceptable: cliente piloto MEDIA cost burst tolerable short-term

---

## Recomendación

**Opción A · Scope-out PERMANENT pre-piloto**:
- Anthropic SLA 99.9% típico · downtime catastrophic raro
- Current fallback model-to-model suficiente cliente piloto MEDIA único
- Multi-provider abstraction es OVER-ENGINEERING pre-piloto

**Future-1.E.llm-multi-provider** capturado:
- ETA empírico ~8-15h (OpenAI adapter + provider router refactor)
- Pre-condición: 2+ clientes piloto OR Anthropic incident real detected
- Post-piloto demand-driven (cuando scale justifica complejidad)

**Quick win pre-piloto** (~30 min · opcional):
- Add metric `llm_router_failures_24h` exposed `/admin/llm-observability` (m_observability existing)
- Alert si >5 fails 1h period · Marcos manual escalation

---

## Cross-ref

- LLM Router source: `backend/app/core/ai/llm_router.py`
- AgentBase: `backend/app/agents/base.py`
- m_observability LLM cost tracking (per memoria · 7 tests verified)
- ADR-???? prompt caching (FASE B reference)
- Sesion 10 litellm bypass documented

---

## Honest notes

1. NO inspección incident history real Anthropic downtime · audit assume SLA OK
2. Multi-provider integration es feature significant complexity (auth · prompts compat · cost mapping · token counter parity)
3. ETA 8-15h asumes OpenAI as alt provider · Mistral/Cohere similar effort each
4. Quick win metrics ~30 min opcional pero NO required pre-piloto
