# AUDIT CLUSTER 4 Phase 4A · LLM Coach Mode Upgrade Empirical State

**Sesión**: 3B-2B.8 CLUSTER 4 Phase 4A
**Fecha**: 2026-05-26
**Ejecutor**: Phase 4A.0 OPS-052 audit mandatory
**Status**: ✅ **Audit complete · scope refined coach context injection · NO STOP HARD**

---

## Resumen ejecutivo

Briefing Phase 4A asumió necesidad de coach mode conversational cliente. Empirical reality:

- ✅ **compute_workflow_state Phase 1D pure functional** existing · returns `next_cliente_actions` per phase ENS + categoria aware
- ✅ **top_action_for_role helper** existing · prioritizes per role
- ✅ **Phase 2C nudge_scheduler** existing · proactive nudges via Celery beat (post-action follow-up)
- ✅ **Phase 2E category-aware system prompt injection** existing · LLM tailorea per BASICA/MEDIA/ALTA
- ✅ **agent_14_copiloto.service.answer_question** RAG pipeline existing · /client-portal/copilot/chat endpoint
- ⚠️ **agent_12_coach_cliente** existe pero scope EVALUADOR · NOT coach conversational (evalúa cliente responses · NO autoría coaching)
- ❌ **NO coach mode endpoint** que consume `compute_workflow_state` for current phase context injection
- ❌ **NO "next step recommendation" endpoint** que devuelva top action cliente-friendly explained

**Refined empirical scope**: agent_12 está dedicated a EVALUACIÓN respuestas cliente · scope diferente. Phase 4A aporta NEW coach mode endpoint que extiende agent_14 RAG pipeline con workflow state context injection (consume compute_workflow_state next_cliente_actions · inject en system prompt) + NEW next-step recommendation endpoint reuse top_action_for_role helper.

ETA refined: ~2-3h backend MVP vs briefing 3-5h (-30% to -50% OPS-045 60ª manifestation · audit-first reveals: compute_workflow_state + category injection Phase 2E + nudge scheduler Phase 2C todo ya wired · solo coach mode endpoint + next-step recommendation faltaban).

---

## Phase 4A.0.1 · Existing infrastructure map

### compute_workflow_state (Phase 1D)
`backend/app/motors/m11_copiloto/workflow_state_scanner.py:546`:
- Returns WorkflowState dataclass: current_phase + phase_progress + next_admin_actions + next_cliente_actions + blockers + categoria_objetivo + audit_passed_at
- Pure functional R1 deterministic · JSON-serializable asdict()
- Reuse cross-consumer (m11 copilot hint endpoint + Sesión 3B-2B.9 admin · Sesión 3B-2B.10 simulacro · etc)

### top_action_for_role helper
`workflow_state_scanner.py:607`:
- Returns highest priority ActionHint per role (urgent > normal > low)
- Tiebreaker: insertion-order Python 3.7+

### Phase 2C nudge_scheduler
`m11_copiloto/nudge_scheduler.py`:
- scan_pending_nudges + dispatch · daily Celery beat 09:00 ES
- emit_client_notification type=generic_alert + audit_log coach.nudge.dispatched
- Dedup via source_key `coach_nudge:{source_action}`

### Phase 2E category-aware system prompt injection
`agent_14_copiloto/service.py:_build_system_prompt`:
- PageContext.ens_category injection (BASICA/MEDIA/ALTA)
- _CATEGORY_GUIDANCE dict 3 entries · tailorea LLM responses per categoría

### agent_12_coach_cliente
- Scope: EVALUADOR · evalúa cliente respuestas a coaching questions (~80 deterministic questions de M9 coaching.COACHING_QUESTIONS)
- NOT autoría coaching · output JSON strict scoring L0-L5 + feedback Marcos
- NOT relevant Phase 4A scope · scope diferente

---

## Phase 4A.0.2 · Coach mode endpoint design

### NEW endpoint · POST /client-portal/copilot/coach

Extends `portal_copiloto_chat` con coach context injection:

```python
# 1. Resolve project_id + categoria_objetivo (Phase 2E _resolve_project_meta)
# 2. Compute workflow state (reuse compute_workflow_state Phase 1D)
# 3. Extract next_cliente_actions + current_phase + blockers
# 4. Inject coach context into PageContext (NEW field coach_context)
# 5. _build_system_prompt enriched · coach guidance section
# 6. RAG pipeline answer_question (reuse agent_14)
# 7. audit_log copilot.coach.session.message (Sub-atom 5.A)
```

### NEW endpoint · GET /client-portal/copilot/coach/next-step

Single-shot recommendation cliente-friendly:

```python
# 1. Resolve project_id
# 2. Compute workflow state
# 3. top_action_for_role(state, role="cliente")
# 4. Compose R29 friendly recommendation:
#    "Te toca: {action.cliente_description}"
#    "¿Por qué importa? {action.why_matters}"
#    "Cuando puedas. Sin prisa por tu parte."
# 5. audit_log copilot.coach.next_step.viewed
```

### PageContext extension (Phase 2E)

```python
@dataclass
class PageContext:
    # ... existing fields
    coach_mode: bool = False
    coach_current_phase: Optional[str] = None
    coach_pending_action: Optional[str] = None
```

### System prompt coach enrichment

```python
_COACH_MODE_GUIDANCE_TEMPLATE = """
## Modo coach activo

El cliente está en la fase ENS: **{phase}**. Tareas que le tocan:

{pending_actions_list}

Ajustes obligatorios en tu respuesta:
- Tono coach amigable · primer-principios cliente · NO ENS técnico sin TooltipENS
- Explica cuál es la próxima acción y POR QUÉ importa (impacto compliance)
- "Sin prisa por tu parte" · R29 firmísimo
- Cliente NO genera contenido ENS · solo recibe/aprueba/firma · Marcos owns content
- Si cliente pregunta algo fuera de su fase actual · responde + sugiere su tarea actual amigable
"""
```

---

## Phase 4A.0.3 · audit_log accion canonical

- `cliente.coach.session.started` (cliente abre coach UI)
- `cliente.coach.message.sent` (cliente envía pregunta)
- `cliente.coach.message.answered` (LLM responde post-coach injection)
- `cliente.coach.next_step.viewed` (cliente views top action)

Sub-atom 5.A 3-way OR (project_id + client_id propagated).

---

## Phase 4A.0.4 · Recommended Phase 4A refined scope (~2-3h)

### Phase 4A.1 implementation (~1.5-2h)

**Step 1 · Extend PageContext** (~10 min)
- ADD `coach_mode` + `coach_current_phase` + `coach_pending_action` fields (Optional)
- Backward-compat (default None / False)

**Step 2 · Extend `_build_system_prompt`** (~20-30 min)
- Inject coach guidance section cuando `coach_mode=True`
- Reuse `_CATEGORY_GUIDANCE` (Phase 2E)
- _COACH_MODE_GUIDANCE_TEMPLATE Spanish R29 friendly

**Step 3 · NEW coach endpoint** (~30-45 min)
- `m11_copiloto/portal_api.py` ADD POST `/client-portal/copilot/coach`
- Resolve workflow state · top_action_for_role · inject PageContext
- Reuse `answer_question` (agent_14 RAG pipeline)
- audit_log Sub-atom 5.A

**Step 4 · NEW next-step recommendation endpoint** (~20-30 min)
- ADD GET `/client-portal/copilot/coach/next-step`
- Compute workflow state · top_action_for_role
- Compose R29 friendly response (cliente_description + why_matters + sin prisa)
- audit_log Sub-atom 5.A

### Phase 4A.2 tests (~30-45 min)

**Backend tests (8-10 tests)**:
- PageContext coach_mode field backward-compat
- _build_system_prompt injects coach guidance cuando coach_mode=True
- _build_system_prompt NO coach guidance cuando coach_mode=False (default)
- POST coach endpoint integrates compute_workflow_state empirical
- POST coach endpoint emits audit_log Sub-atom 5.A
- GET next-step returns top action cuando exists
- GET next-step returns "Todo al día" cuando no pending actions
- audit_log cliente.coach.* propagated cross endpoints

---

## ETA refined Phase 4A

- **Briefing nominal**: ~3-5h
- **Empirical refined**: ~2-3h (extend PageContext + system prompt + 2 endpoints + tests)
- **OPS-045 60ª manifestation**: -30% to -50% vs nominal (audit-first reveals all infrastructure components already wired · solo aggregate coach context + 2 endpoints)

---

## Filosofía cliente-mínimo compliance

100% aligned:
- Cliente pregunta · coach guides "qué hacer y por qué" · NO autoría contenido ENS
- "Sin prisa por tu parte" R29 firmísimo enforced
- Cliente NO genera ENS contenido · Marcos owns content authoritative
- audit_log trace · ENAC trazabilidad cumulative

---

## STOP HARD trigger evaluation

**NO STOP HARD necesario**. Briefing intent (LLM coach mode upgrade) ratified · refined a context injection scope + 2 endpoints. agent_12 scope EVALUADOR diferente · NO replazo · agent_14 RAG pipeline extends con coach context (Pattern #16 category-aware extension).

---

## Patterns potencialmente formalizables Phase 4A

- **Coach context injection pattern** (compute_workflow_state → PageContext coach_mode → _build_system_prompt coach guidance section · reuse Pattern #16 mechanism)
- **Single-shot next-step recommendation pattern** (top_action_for_role helper + R29 friendly compose · NO LLM call · deterministic O(1))

---

## Decisión pendiente

⏸️ **Architect approve Phase 4A.1 refined scope**:
- Extend PageContext + _build_system_prompt + 2 endpoints (POST coach + GET next-step)
- 8-10 tests coach awareness + workflow_state integration + audit_log
- ETA refined ~2-3h
- Filosofía cliente-mínimo 100% aligned
