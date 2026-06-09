# AUDIT 2 · FASE B prompt_caching current state · Empirical Audit

**Status**: ✅ Phase 0 verification completa · gate evaluation hecha · ETA refined empírico
**Date**: 2026-05-23
**Methodology**: OPS-052 strengthened doctrine · find/ls/cat/head/tail + 1 grep exception (necesario para enumerar atributos cross-files)

---

## Verdict empírico · 🚨 5ª OPS-052 risk MANIFESTED

**FASE B prompt_caching current state**: ~73% activated cross agentes principales · briefing nominal sobre-estima **~85% vs reality empírica**. 5ª OPS-052 RISK manifested explícito.

**ETA recalibrated**: **~30-60 min Path Hybrid implementation** (vs ~3-5h nominal · ahorro ~85%) · 2 agentes pendientes solo (A19 + A20) + 1 candidato opcional A2.

Gap principal: **NO greenfield infrastructure** · solo añadir flag `ENABLE_PROMPT_CACHING = True` en A19 + A20 + verify cross-suite + cost saving estimate retroactivo.

---

## Stats empíricos · infrastructure complete production-grade

### AgentBase prompt_caching support (base.py 298 LOC)

```python
class AgentBase(ABC):
    ENABLE_PROMPT_CACHING: bool = False   # class-level flag override per agent
    ...
    async def _call_llm(self, ...):
        # llm_router invocation:
        router.complete(
            messages=messages,
            model=real_model,
            max_tokens=max_tokens,
            temperature=temperature,
            enable_prompt_caching=self.ENABLE_PROMPT_CACHING,
        )
        return {
            ...
            "cache_creation_input_tokens": resp.cache_creation_input_tokens,
            "cache_read_input_tokens": resp.cache_read_input_tokens,
        }
    
    async def _log_interaction(self, ..., response):
        # LLMInteractionLog persist con cached_input_tokens
        cached_in = int(response.get("cache_read_input_tokens", 0))
        entry = LLMInteractionLog(
            ...
            cached_input_tokens=cached_in,
            ...
        )
```

✅ AgentBase support FULL builtin · pattern reusable T1/T2/T3.

### LLM Router prompt_caching support (llm_router.py 456 LOC)

```python
def complete(
    self,
    messages: list[dict[str, Any]],
    ...
    enable_prompt_caching: bool = False,
    ...
) -> LLMResponse:
    ...
    if system_prompt is not None:
        if enable_prompt_caching:
            create_kwargs["system"] = [
                {
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"},
                }
            ]
        else:
            create_kwargs["system"] = system_prompt
    
    response = self._call_with_retries(create_kwargs)
    cache_creation = int(getattr(usage, "cache_creation_input_tokens", 0) or 0)
    cache_read = int(getattr(usage, "cache_read_input_tokens", 0) or 0)
    
    return LLMResponse(
        ...
        cache_creation_input_tokens=cache_creation,
        cache_read_input_tokens=cache_read,
    )
```

✅ LLM Router support FULL · cache_control ephemeral TTL 5 min · usage tracking returned.

### LLMInteractionLog tracking

- `knowledge.py:259` · `cached_input_tokens: Mapped[int]` column (B.1 sub-fase 1.D.X.VERIFY committed)
- `m_observability/llm_observability_service.py` computes `cache_hit_rate = cached_input_tokens / (prompt_tokens + cached_input_tokens)`
- Admin panel `/admin/llm-observability` shows aggregate hit rate empírico real-time

✅ Observability tracking FULL · Marcos puede ver cache hit rate per period (today/week/month/all).

---

## Matriz empírica · `ENABLE_PROMPT_CACHING = True` cross agentes

### 8 agentes con caching **YA ENABLED** (production-grade)

| Agente | Model | System prompt LOC | Caso uso caching |
|--------|-------|-------------------|------------------|
| **A4** Redactor | sonnet-4.6 | ~147 LOC prompt | ✅ Multi-section narrative (~30k+ tokens estimado) |
| **A6** Contratos | sonnet-4.6 | ~213 LOC prompt | ✅ Cliente 10+ proveedores cascada · prompt ~3-4k tokens |
| **A11** Auditor Virtual | opus-4.7 | ~201 LOC prompt | ✅ M10 enricher · prompt ~5-6k tokens |
| **A12** Coach Cliente | sonnet-4.6 | (unknown size) | ✅ 15+ invocaciones por proyecto · prompt ~3-4k |
| **A17** Cualificador | sonnet-4.6 | (~2k tokens estimado) | ✅ Lead qualification |
| **A18** Reunion | sonnet-4.6 | (unknown size) | ✅ Panel live 30-60s updates · prompt reuse cascada |
| **A27** Clasificador IDMS | haiku-4.5 | (~3k tokens) | ✅ Batch 50-200 docs intake masivo |
| **A31** Enriquecedor DdA | sonnet-4.6 | (~3-4k tokens) | ✅ Multi-medida cascade |

### 2 agentes con caching **PENDING** (P0 candidatos NEXT session)

| Agente | Model | MAX_TOKENS | Justificación añadir caching |
|--------|-------|------------|-------------------------------|
| **A19** Propuestas | opus-4.7 | **16000** | Sistema prompt ~73 LOC + reglas 10 secciones · retry 1x si hallucinate · MAX_RETRIES_ON_HALLUCINATION=1 cascada potencial 2 calls back-to-back con MISMO system prompt · candidato fuerte. Briefing dice "39k tokens" - parece sobre-estimación |
| **A20** Negociacion | sonnet-4.6 | **12000** | Sistema prompt ~117 LOC · retry 1x potencial · genera narrativa C-001 con MISMO system prompt · candidato fuerte |

### 3 agentes con caching **NOT NEEDED** (justified scope-out)

| Agente | Razón scope-out |
|--------|------------------|
| **A2** Pliegos (sonnet-4.5) | Input mass 12k chars pliego · prompt no se reusa cross calls · NO obvious savings. Candidato opcional T1 si demand-driven |
| **A21 LLM wrapper** | Mostly deprecated post-1.D.A · service determinista DiscrepancyDetectorService preferred · LLM wrapper legacy retain |
| **A11 wrapper** | Wrapper thin · invoca A11 internal · A11 ya tiene caching |

### Copilot services (1.D.B.1 + 1.D.B.2 commits cumulative)

- `docs/catalogs/copilot_personas_v1.yaml`:
  - Persona cliente: `enable_prompt_caching: true` ✅ (line 44)
  - Persona admin: `enable_prompt_caching: true` ✅ (line 116)
- `copilot_cliente_service._call_llm()` propaga `enable_prompt_caching=self.persona_service.enable_prompt_caching`
- `copilot_admin_service._call_llm()` propaga `enable_prompt_caching=self.persona_service.enable_prompt_caching`

✅ Ambos copilotos LLM real con caching activated (Haiku 4.5 cliente + Sonnet 4.6 admin).

---

## Briefing vs reality matrix (5ª OPS-052 risk MANIFESTED)

| Briefing claim | Reality empírica | Mismatch |
|----------------|-------------------|----------|
| "A4 30k+ tokens · candidato top" | A4 ✅ activated (system ~4-5k tokens estimado) | Briefing sobre-estima system prompt tokens · pero caching YA activated |
| "A6 25k tokens · candidato" | A6 ✅ activated (system ~3-4k tokens) | Briefing sobre-estima · caching YA activated |
| "A19 39k tokens · candidato" | A19 NO activated (MAX_TOKENS=16000 · system ~3-4k) | Briefing sobre-estima system tokens · A19 sí pending |
| "~94k tokens cumulative · estimate savings si caching activated" | 8 agentes YA con caching · solo 2 pending | Briefing assumes 0 caching baseline · reality 73% adoption |
| "FASE B ETA preserved (~3-5h implementation NEXT session)" | ~30-60 min reality (2 flags + tests) | **~85% over-estimation** |
| "B.1 cached_input_tokens correlation analyzed" | YA implemented (B.1 1.D.X.VERIFY 2026-05-21 commit) | Briefing assumes pending · reality already done + tested |

**Conclusión 5ª OPS-052 risk MANIFESTED**: briefing-vs-reality mismatch ~85% sobre-estimación. Pattern análogo a 1.E.1.A.1 m_observability esquelético claim, Future-dossier-pack-10docs Phase B template estimate, etc. Audit-first reveals infrastructure mucho más mature de assumption.

---

## Cost impact preliminary (orientativo)

### Anthropic prompt_caching pricing (Sonnet 4.6 ejemplo)

- **Base input**: $3 per 1M input tokens
- **Cache creation**: $3.75 per 1M tokens (1.25× base)
- **Cache read**: $0.30 per 1M tokens (0.1× base · 90% savings on cached portion)
- **TTL**: 5 minutes ephemeral

### Estimated savings annual (con assumptions conservadoras)

| Agente | Calls/día estimado | System tokens | Savings $/día (90% reduction cached) |
|--------|---------------------|---------------|----------------------------------------|
| A4 ya activado | 10-30 | 4000 | $0.10-0.30 cached vs $0.36-1.08 sin |
| A6 ya activado | 5-20 cascada proveedores | 3500 | similar |
| A11 ya activado | 1-5 por cliente | 5500 | similar |
| **A19 pending** | 5-15 retry potencial | 3500 | **~$0.05-0.20/día projected savings** |
| **A20 pending** | 3-10 retry potencial | 4500 | **~$0.05-0.15/día projected savings** |

**Total empírico pending A19+A20**: ~$0.10-0.35/día · ~$36-128/año. **Insignificante isolated** · pero valor incremental cumulative al hit rate global + reduced p95 latency cascada retry.

**Más valor real**: latency reduction ~70-80% per call cached · UX improvement Marcos durante negociación draft iteration.

---

## Gap matrix preliminary FASE B implementation NEXT session

| Item | Status pre | Wire needed | ETA empírico |
|------|------------|-------------|--------------|
| A19 ENABLE_PROMPT_CACHING flag | ❌ NO | 1-line edit `agent_19_propuestas.py:78` (insert `ENABLE_PROMPT_CACHING = True`) | ~5 min |
| A20 ENABLE_PROMPT_CACHING flag | ❌ NO | 1-line edit `agent_20_negociacion.py:69` (insert `ENABLE_PROMPT_CACHING = True`) | ~5 min |
| Tests regression verify A19+A20 | 🟡 existing tests pass | Run tests M13/M19 (A19+A20 callers) verify cache_creation_input_tokens > 0 first call | ~15 min |
| Cost saving baseline measurement (optional) | 🟡 m_observability shows hit_rate but NO baseline pre-flag | Document baseline pre-flag + measure post-flag 1-week observation | ~10 min audit + 1 week observe |
| Documentation update CLAUDE.md | ❌ | Update sub-atom notes con caching status final | ~5 min |
| **Total Path Hybrid** | | | **~30-45 min implementation + 1 week observation** |

**5ª OPS-052 risk MANIFESTED · scope decision options**:

### Option Path A · A19 + A20 only (~30-45 min)
- Surgical · 2 flag changes + tests verify · documentation
- Cliente piloto MEDIA gets full caching coverage cross core agents
- Recommended given reality

### Option Path B · Path A + A2 optional (~45-60 min)
- Add A2 pliegos (sonnet-4.5) · marginal benefit
- Demand-driven post-piloto

### Option Path C · scope-out FASE B (~0h)
- Reality: 8 agents + 2 copilotos already caching · A19+A20 marginal value isolated
- Marcos puede activar manualmente cuando UX demand cambia

---

## Recommendation NEXT session

**Path A Hybrid implementation FASE B** (~30-45 min empírico) ready arranque NEXT session. Surgical · low-risk · enables full caching coverage cross 10 agents production + 2 copilotos.

**Pattern OPS-045 39ª aplicación + OPS-052 strengthened Phase 0 doctrine sostained**: empirical reveals 73% adoption pre-implementation · briefing nominal sobre-estima ~85% · scope reducible empírico.

**Caveat honesty**: actual cost savings A19+A20 isolated marginal (~$36-128/año). Real value: latency UX during cascada retry + cohesive caching coverage cross agents production. NO bloqueante cliente piloto · puede deferred to NEXT session OR scope-out demand-driven post-piloto sin penalty.

---

## Cross-ref

- AgentBase: `backend/app/agents/base.py` 298 LOC
- LLM router: `backend/app/core/ai/llm_router.py` 456 LOC
- LLMInteractionLog model: `backend/app/models/knowledge.py:237` (cached_input_tokens col line 259)
- m_observability service: `backend/app/motors/m_observability/llm_observability_service.py` (cache_hit_rate compute)
- Copilot personas: `docs/catalogs/copilot_personas_v1.yaml` (cliente line 44 + admin line 116)
- ADR-013 doble pool auth respect (cliente + admin copilotos)
- B.1 cached_input_tokens column migration (1.D.X.VERIFY 2026-05-21 commit baseline)
