# AUDIT CLUSTER 2 Phase 2E · Copiloto Q&A Cliente Adaptación per Categoría Empirical State

**Sesión**: 3B-2B.8 CLUSTER 2 Path B Phase 2E
**Fecha**: 2026-05-26
**Ejecutor**: Phase 2E.0 OPS-052 micro-audit mandatory
**Status**: ✅ **Audit complete · scope refined inject categoria_objetivo PageContext · NO STOP HARD**

---

## Resumen ejecutivo

Briefing Phase 2E asumió necesidad de adapt LLM model selection per categoría (BÁSICA Haiku · MEDIA Sonnet · ALTA Opus). Empirical reality:

- ✅ **Copiloto Q&A infrastructure complete** · `/api/v1/client-portal/copilot/chat` + `/chat/stream` SSE
- ✅ **`answer_question` pipeline functional** (agent_14_copiloto/service.py:286) · detect_filters → hybrid_search → LLM → validate → log
- ✅ **DEFAULT_MODEL = claude-sonnet-4-5-20250929** · DEFAULT_TEMPERATURE = 0.1 (R3 ≤ 0.2 sostained)
- ✅ **Quick actions per-page context** (_PORTAL_QUICK_ACTIONS dict · 6 contexts: default · magerit · dda · conformidad · evidencias · incidents)
- ✅ **System prompt explicit BASICA/MEDIA/ALTA differentiation logic** (prompts.py:27-41 instructions)
- ✅ **PageContext dataclass** existing (url + client_id + project_phase + active_motor)
- ❌ **PageContext lacks `ens_category` field** · NO categoria_objetivo passed to LLM
- ❌ **NO category-specific guidance injection** in `_build_system_prompt` (page_context aware but NO category-aware)
- ❌ **NO audit_log emit cliente.copilot.asked / cliente.copilot.answered** (LLMInteractionLog persists answer · NO audit_log Sub-atom 5.A trace)

**Conclusion**: Existing answer_question pipeline LLM-driven category awareness via SYSTEM_PROMPT (BASICA/MEDIA/ALTA must-respond-per-category instruction) ALREADY explicit. Gap empirical: inject PROJECT'S categoria_objetivo so LLM tailors advice contextual to cliente's specific category (NOT model switching).

Briefing assumption "LLM model per categoría" replaced empirical "category-aware system prompt + PageContext.ens_category injection" · scope refined ~1.5-2h vs briefing 2-3h nominal (-25% to -50% OPS-045 55ª · DRY reuse system prompt builder).

---

## Phase 2E.0.1 · Existing Q&A pipeline empirical

### Endpoint surface cliente

| Endpoint | File | Purpose |
|----------|------|---------|
| `POST /api/v1/client-portal/copilot/chat` | m11_copiloto/portal_api.py:88 | Single-shot Q&A |
| `POST /api/v1/client-portal/copilot/chat/stream` | portal_api.py:121 | SSE streaming responses |
| `GET /api/v1/client-portal/copilot/quick-actions` | portal_api.py:203 | Pre-defined prompts per page context |
| `GET /api/v1/client-portal/copilot/workflow-hint` | portal_api.py:228 | Phase 1D Phase 2C nudges (existing) |

### Service-level pipeline (agent_14_copiloto/service.py)

```
detect_filters(question) → measure_codes_mentioned + source_codes
  → hybrid_search(query, top_k=5, filters) → HybridResult[]
  → _build_user_message(question, chunks) + _enrich_user_message_with_m30
  → _build_system_prompt(page_context, corpus_gap)
  → router.complete(messages, model=DEFAULT_MODEL, temperature=0.1)
  → extract_citations + assess_grounding
  → LLMInteractionLog persist
  → CopilotResponse(answer, citations, model_used, latency_ms, ...)
```

### PageContext current schema (agent_14_copiloto/types.py)

```python
@dataclass
class PageContext:
    url: Optional[str] = None
    client_id: Optional[str] = None       # M30 contacts integration
    project_phase: Optional[str] = None
    active_motor: Optional[str] = None
    # MISSING: ens_category (categoria_objetivo project)
```

### SYSTEM_PROMPT categoría-aware logic ALREADY existing

`backend/app/agents/agent_14_copiloto/prompts.py:27-41`:
> "Cuando una medida o control es obligatorio o aplica a una categoría del ENS, debes responder EXPLÍCITAMENTE por cada una de las tres categorías (BASICA, MEDIA, ALTA)..."
> "Nunca respondas solo 'no' o solo para una categoría cuando la pregunta..."

**Gap**: Sistema prompt aplica multi-categoría logic GENÉRICO · NO sabe la categoría DEL CLIENTE específico para tailoring (BÁSICA simpler advice vs ALTA detailed advice).

---

## Phase 2E.0.2 · Cliente-mínimo R29/R30 compliance evaluation

Filosofía cliente-mínimo guard per briefing intent:
- Cliente preguntas FUNCIONALES ("¿qué firmo?" · "¿qué evidencia subo?" · "¿qué pasa si no?")
- Copiloto adapta respuesta per categoría:
  - **BÁSICA**: explicaciones simplificadas · "Para tu categoría Básica solo necesitas..."
  - **MEDIA**: depth estándar · audit-ready language · "Para tu categoría Media (requiere auditoría ENAC)..."
  - **ALTA**: detailed · SOC/DR mentions · "Para tu categoría Alta (vigilancia 24/7 SOC requerida)..."
- R29 firmísimo: NO admin lingo · NO ENS técnico sin TooltipENS · "Sin prisa por tu parte"
- R30 inverso: cliente NO ve admin orchestration · solo qué LE TOCA

✅ 100% aligned · NO violations.

---

## Phase 2E.0.3 · audit_log emit current state

Search `cliente.copilot.asked` empirical: **NO ENCONTRADO** audit_log accion.

Existing trace:
- `LLMInteractionLog` (project_id + feature='copilot_chat' + prompt_hash + response_preview + tokens + latency_ms + status)
- NO Sub-atom 5.A audit_log trace (project_id + client_id propagated explicit)

**Gap**: Cliente copilot interactions NO audit_log Sub-atom 5.A trail · ENAC trazabilidad incomplete.

---

## Phase 2E.0.4 · Recommended Phase 2E refined scope (~1.5-2h)

### Phase 2E.1 implementation (~1-1.5h)

**Step 1 · types.py**: ADD `ens_category` field to PageContext (~5 min)
- Optional[str] · valores BASICA / MEDIA / ALTA / None
- Backward-compat (Optional preserves existing callers)

**Step 2 · service.py `_build_system_prompt`**: Inject category-specific guidance (~15-20 min)
- Detect page_context.ens_category
- Append section "## Categoría del proyecto cliente" con guidance per categoría
- BASICA: "Cliente categoría BÁSICA · explicaciones simplificadas..."
- MEDIA: "Cliente categoría MEDIA · audit-ready · menciona auditoría ENAC obligatoria..."
- ALTA: "Cliente categoría ALTA · enfatiza SOC 24/7 · DR drills..."

**Step 3 · portal_api.py `portal_copiloto_chat` + `_stream`**: Resolve project.categoria_objetivo (~20-30 min)
- Lookup project.categoria_objetivo desde project_id resolved
- Inject en PageContext.ens_category antes de query
- Best-effort: si lookup fails · fallback PageContext sin ens_category (NO bloquea Q&A)

**Step 4 · audit_log emit Sub-atom 5.A** (~15-20 min)
- audit_log `cliente.copilot.asked` post-receive question (project_id + client_id propagated)
- audit_log `cliente.copilot.answered` post-LLM response (latency_ms + model_used + citations_count metadata)
- Raw SQL INSERT pattern (existing m_cloud_connectors/digest_service.py · m21/notification_service.py)

### Phase 2E.2 tests (~30-45 min)

**Backend tests (4-5 tests)**:
- Test PageContext.ens_category field works (backward-compat None default)
- Test `_build_system_prompt` injects BASICA guidance when ens_category=BASICA
- Test `_build_system_prompt` injects MEDIA guidance when ens_category=MEDIA
- Test `_build_system_prompt` injects ALTA guidance when ens_category=ALTA
- Test portal_copiloto_chat endpoint resolves project.categoria_objetivo + passes to PageContext
- Test audit_log cliente.copilot.asked + cliente.copilot.answered persisted Sub-atom 5.A 3-way OR

---

## ETA refined Phase 2E

- **Briefing nominal**: ~2-3h
- **Empirical refined**: ~1.5-2h (PageContext extend + system prompt enrichment + audit_log emit · NO model switching · NO greenfield)
- **OPS-045 55ª manifestation**: -25% to -50% vs nominal (audit-first reveals SYSTEM_PROMPT BASICA/MEDIA/ALTA logic already · PageContext extend is small additive)

---

## Filosofía cliente-mínimo compliance

Category injection cliente-mínimo aligned:
- Cliente pregunta · copilot responde con context DE SU categoría (NO categorías genéricas)
- NO admin orchestration leaked
- NO ENS técnico sin TooltipENS
- R29 firmísimo: tone friendly · "Sin prisa por tu parte"
- R30 inverso: cliente NO ve internal LLM routing decisions

**ZERO admin operations cliente-facing**.

---

## STOP HARD trigger evaluation

**NO STOP HARD necesario**. Briefing intent (copilot Q&A categoría-aware) ratified · refined a system prompt enrichment scope (vs model switching greenfield assumption).

**Briefing assumption "LLM model per categoría" replaced empirical "system prompt category-aware injection"**:
- Model switching adds operational cost (Opus expensive) sin tailoring benefit measurable
- LLM router already capable model switching · NOT scoped Phase 2E necessary
- System prompt category injection achieves intent empirical (cliente sees tailored advice)
- Future-1.E.copilot-model-per-category (~2-3h post-piloto demand-driven · LLM cost optimization decision)

---

## Patterns potencialmente formalizables Phase 2E

- **Category-aware system prompt injection** (PageContext extends with project category · LLM tailors per categoría sin model switching · DRY existing pipeline)
- **Sub-atom 5.A audit_log LLM interaction tracing** (cliente.copilot.asked + cliente.copilot.answered · project_id + client_id propagated · forward-compat ENAC trazabilidad)

---

## Decisión pendiente

⏸️ **Architect approve Phase 2E.1 refined scope**:
- ADD `ens_category` to PageContext (backward-compat)
- INJECT category guidance in `_build_system_prompt`
- RESOLVE project.categoria_objetivo en portal_copiloto_chat backend + pass PageContext
- ADD audit_log emit Sub-atom 5.A 3-way OR
- 4-5 backend tests + audit_log coverage
- ETA refined ~1.5-2h
