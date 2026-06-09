# Ejecutable 8 · Pasada 13 · Copilots + Agents Intelligence

## 1. Inventario funcional · 12 agentes activos

Fuente: `backend/app/agents/registry.py` (AGENT_REGISTRY) + `backend/app/agents/api.py` (`_AGENT_CLASSES`). Empírico: 31 IDs registrados, 12 invocables (status `activo` + 1 `scaffolding_covered_by_engine` A2). Resto deprecated / externalized_to_motor / reservado.

| Agente | Nombre | Status | Modelo (alias) | Temp | Motor | Funcional (clase + endpoint) | Proactividad |
|--------|--------|--------|----------------|------|-------|------------------------------|--------------|
| A2 | Analizador Pliegos | scaffolding_covered_by_engine | sonnet-4.5 | 0.1 | — | SÍ · `/2/analyze-pliego` (stub 24 LOC funcional) | prompt-driven |
| A4 | Redactor E-090 | activo | sonnet-4.6 | 0.2 | m22 | SÍ · `/4/generate-e090-narrative` | prompt-driven |
| A6 | Analista Contratos | activo | sonnet-4.6 | 0.1 | m14 | SÍ · `/6/analyze-contract` | prompt-driven |
| A11 | Auditor Interno Virtual | activo | opus-4.7 | 0.1 | m10 | SÍ · `/11/run-supplementary-audit` | prompt-driven |
| A12 | Coach Cliente Evaluador | activo | sonnet-4.6 | 0.2 | m09 | SÍ · `/12/evaluate-response` + `/12/evaluate-batch` | prompt-driven (NO genera preguntas) |
| A14 | Copiloto Conversacional | activo | sonnet-4.5 | 0.2 | m11 | SÍ · `agent_14_copiloto` RAG (citation_validator) | event/prompt (chat + coach) |
| A17 | Cualificador Comercial | activo | sonnet-4.6 | 0.1 | m13 | SÍ · `/17/qualify-lead` | prompt-driven |
| A18 | Reunión Exploratoria | activo | sonnet-4.6 | 0.1 | m13 | SÍ · `/18/meeting-update` + SSE `/stream` | prompt-driven (panel live K.4) |
| A19 | Redactor Propuestas | activo | opus-4.7 | 0.15 | m13 | SÍ · vía `/{id}/invoke` (16k tokens) | prompt-driven |
| A20 | Negociador Contractual | activo | sonnet-4.6 | 0.15 | m14 | SÍ · vía `/{id}/invoke` | prompt-driven |
| A21 | Detector Discrepancias | activo | **determinista** | 0.0 | m04 | SÍ · DiscrepancyDetectorService SQL (R1 inviolable) | event-driven cross-motor |
| A27 | Clasificador IDMS | activo | haiku-4.5 | 0.1 | m24 | SÍ · `/27/classify-document` + batch | event (upload-triggered) |
| A31 | Enriquecedor DdA | activo | sonnet-4.6 | 0.2 | m03 | SÍ · `/31/enrich-measure` + batch | prompt-driven |

**Copilotos** (separados de los agentes A-id):
| Copiloto | Servicio | Modelo | Temp | Persona | Endpoint principal |
|----------|----------|--------|------|---------|--------------------|
| Admin (m11) | `copilot_admin_service.py` | sonnet-4.6 (`copilot_personas_v1.yaml` admin) | **0.15** | R30 tutor cronológico | `/api/v1/admin/copilot/chat` (`admin_copilot_stub.py`) |
| Cliente | `copilot_cliente_service.py` (`CopilotClienteLLMService`) | sonnet-4.6 (persona cliente) | **0.2** | R29 friendly | `/api/v1/client-portal/copilot/chat` (`client_copilot_stub.py`) |
| Coach/hint cliente | `m11_copiloto/portal_api.py` (RAG `answer_question` A14) | sonnet-4.5 | 0.2 (A14) | R29 coach | `/api/v1/client-portal/copiloto/{coach,chat/stream,hint,quick-actions}` |

Evidencia: `registry.py:84-252`, `api.py:23-50`, `copilot_personas_v1.yaml:41-44` (admin) `:113-116` (cliente).

## 2. LÍMITES

### 2.1 Temperatura ≤0.2 (R3)
Verificado grep `TEMPERATURE`/`temperature=` en `backend/app/agents` + motores LLM.
- TODOS los 12 agentes + 2 personas copiloto: temp ∈ {0.0, 0.1, 0.15, 0.2} → **R3 OK**.
- AgentBase default `TEMPERATURE = 0.15` (`base.py:51`), pasada a router en `base.py:106,190`.
- **2 OUTLIERS R3 en motores (NO agentes)**: `m05_obligations/personalization.py:99` temp=**0.3** (enrich descripción obligación) y `m10_ens_radar/outreach/draft_generator.py:713` temp=**0.3** (borrador outbound). Ambos >0.2 → violación R3. (m04_gap/llm_prioritizer 0.2 OK · m08 guide_generator 0.2 OK · m10 proposal_service 0.2 OK).

### 2.2 Rate limits + token/cost budgets per cliente
`backend/app/agents/copilot_rate_limit.py` (robusto, derived on-query desde `LLMInteractionLog` ADR-025):
- CLIENTE Haiku: 100 msg/día · 30k output tok/día · €6/mes (`CLIENTE_CAPS`).
- ADMIN Sonnet: 500 msg/día · 100k output tok/día · €40/mes (`ADMIN_CAPS`).
- soft-warn ≥80% (warning_message) · hard-fail ≥100% (`CopilotRateLimitExceeded` → HTTP 429).
- cost via `LLMInteractionLog.cost_usd` (`knowledge.py:262` Numeric(10,6)). USD→EUR 1:1 simplificación.
- **GAP de wiring (F-13-01)**: `enforce_rate_limit_or_raise` invocado SOLO en `client_copilot_stub.py:152` + `admin_copilot_stub.py:147`. El router paralelo `m11_copiloto/portal_api.py` (prefix `/client-portal/copiloto`, sirve `/coach`, `/coach/stream`, `/chat/stream`, `/hint`, `/quick-actions` — que el FE `frontend/lib/api/copiloto.ts` SÍ consume: `:67 /copiloto/chat/stream`, `:54 /hint`, `:38 /quick-actions`) NO llama rate limiter. Tráfico cliente real por esa vía evade caps.

### 2.3 LLM PI guard (Pasada 9 · 2 fallos tuning)
`backend/app/security/llm_prompt_injection_guard.py` (8 categorías, determinista regex, pure functional). Test en `backend/tests/security/test_llm_prompt_injection.py`.
- **GAP CRÍTICO (F-13-02)**: `sanitize_user_input` tiene **CERO callers en producción**. grep confirma referencias solo en su propio módulo + `security/__init__.py:4` (docstring) + tests. NO está wired en copilot_cliente_service / copilot_admin_service / agent_14 / portal_api / stubs. Defensa anti-jailbreak presente pero INACTIVA. (Los 2 fallos tuning de Pasada 9 son secundarios: el módulo no protege nada en runtime.)
- R29 boundary check (`check_r29_boundaries`, `copilot_cliente_service.py:69`) SÍ está wired (post-response, fallback stub) — distinto del PI guard pre-LLM.

### 2.4 Cost controls (m_observability)
`m_observability/llm_observability_service.py`: `get_cost_summary` + listing por interacción. **Reporting-only** — NO enforce caps (la única enforcement de coste vive en copilot_rate_limit, ver 2.2/F-13-01). Eval/golden datasets presentes (`eval_runner.py`, `golden_eval_runs_service.py`).

## 3. PROACTIVIDAD

| Mecanismo | Archivo | Trigger | Autónomo vs prompt-driven |
|-----------|---------|---------|---------------------------|
| Nudge scheduler | `m11_copiloto/nudge_scheduler.py` + `coach_tasks.py:33` | **Cron** Celery beat daily 09:15 ES (`m11_copiloto.scan_pending_nudges`) | Autónomo (cron, NO event-driven). Cliente-mínimo: priority cap `urgent→high` (`_PRIORITY_MAP`), cooldown 24h, `_ensure_friendly_body` R29 |
| Coach `/coach` | `portal_api.py:341` | request-driven (cliente pregunta) | prompt-driven · LLM A14 RAG con workflow_state injection |
| Coach `/coach/next-step` | `portal_api.py:430` | request-driven | determinista O(1) NO LLM |
| Hint cliente | `portal_api.py:549` | request-driven | determinista (compute_workflow_state) |
| A21 discrepancias | m04 service | event-driven cross-motor SQL | autónomo determinista |
| A27 IDMS | upload event | event-driven | semi-autónomo (requires_human_review flag) |

**F-08-01 confirmado · root cause exacto (F-13-03)**: `_resolve_coach_context` (`portal_api.py:330-332`) accede `top.cliente_description`, `top.motor`, `top.template_id` sobre el `ActionHint` devuelto por `top_action_for_role`. El dataclass `ActionHint` (`workflow_state_scanner.py:46-55`) NO tiene esos campos — los reales son `description_cliente`, `description_admin`, `motor`, `target_url`. `top.cliente_description` y `top.template_id` → **AttributeError**, capturado por `except Exception` (`:334`) → `/coach` siempre devuelve `(None,None,None,None)` → coach NUNCA surface pending_action ni inyecta guidance al system prompt (degradación silenciosa, no 500). Solo `top.motor` existe; las otras 2 rompen.

## 4. Sub-atom 5.A · copilot.* events emit (audit_log)
Confirmados (grep audit_log/accion en m11):
- `cliente.copilot.asked` / `cliente.copilot.answered` (`portal_api.py:177,197`)
- `copilot.hint.generated` (`api.py:370`, `portal_api.py:557,598` con project_id + client_id 3-way OR)
- `cliente.coach.message.sent` / `cliente.coach.message.answered` (`portal_api.py:389,408`)
- `coach.nudge.dispatched` (`nudge_scheduler.py:313` · INSERT manual con JOIN client_users→clients para client_id)
Todos sostienen Sub-atom 5.A propagation. Emit best-effort (try/except logger.exception).

## 5. Boundaries · sistema solo vs cliente/admin · R2 citas

| Decisión | Quién | Evidencia |
|----------|-------|-----------|
| Detección discrepancias ENS | Sistema (A21 determinista) | R1 inviolable · `registry.py:157` |
| Categorización / dossier / materialidad | Sistema determinista (motores M01/M09/M28) | agentes deprecated por redundancia |
| Scoring respuestas cliente | A12 evaluador (NO genera preguntas) | M9 fuente única preguntas |
| Conversación / explicación ENS | Copiloto LLM (R1 SOLO conversacional, NO normativo) | `copilot_cliente_service.py:12` |
| Clasificación documento ambiguo | A27 propone + `requires_human_review` | admin/cliente confirma |
| Firma / aprobación | Cliente (cliente-mínimo VE/AUTORIZA/FIRMA/RECIBE) | nudge priority cap, NO operations |
| Nudge dispatch | Sistema autónomo (cron, cooldown 24h, NO urgent) | `nudge_scheduler.py:48` |

**R2 citas obligatorias**: copiloto A14 valida grounding vía `citation_validator` (`agent_14_copiloto/service.py:38-41`, `is_not_in_corpus`, `extract_citations`); response expone `citations_found` + `not_in_corpus` + `low_grounding_confidence`. AgentBase `_extract_citations` (`base.py:242`) extrae RD/CCN/STIC/Anexo/Art/medida. R2 enforced a nivel respuesta.

## Conclusión
12 agentes + 2 copilotos funcionales. R3 temp≤0.2 cumplido en agentes/copilotos (2 outliers en motores m05/m10). Rate limiter sólido pero con gap de cobertura (router /copiloto sin enforce). 2 hallazgos críticos para Pasada 16: PI guard dead code (F-13-02) y rate limit no cubre el router que el FE realmente usa para coach/stream/hint (F-13-01). F-08-01 root cause aislado (F-13-03 · AttributeError por nombres de campo ActionHint).