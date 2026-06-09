# ADR-047 · Intelligence Cross-Motor · Distributed Pattern (NO new motor)

> Rename history: originally created as ADR-042 (MB-10 Atom 10.5 · 2026-05-13) ·
> renamed to ADR-047 post-audit (B1.2 · OPS-063 cement) to resolve collision
> con existing inline ADR-042 (Magic-link policy híbrida final · SAN-D MB-19.B)
> en `docs/spec/DECISIONS.md`.

## Status: ACCEPTED 2026-05-13

## Context

Pre-audit Atom 10.5 (MB-10) reveló (OPS-026 audit-first 30ª aplicación):

1. **No spec literal "Intelligence cross-motor"** en master plan empirical (`docs/master_plan/fulkro_26_motores_v1.md` = M01-M26 + extensions M27-M31)
2. **Source única "Intelligence cross-motor"** = cumulative memorial sprint Block 6 closure umbrella term Claude.ai sin spec literal backing (`progress/SPRINT_POLISH_BLOCK6_REDIS_AUDIT_PIVOT_2026_05_12.md:99`)
3. **OPS-050 cement 10ª vez validated**: MEMORY drift sistemático cumulative esta sesión (10 instances detected empirical)
4. **Cross-motor intelligence ALREADY DISTRIBUTED PRODUCTION-GRADE**:
   - **22 agents** existing (agent_02 pliegos · agent_04 redactor · agent_06 contratos · agent_11 auditor virtual · agent_12 coach · agent_14 copiloto · agent_17 cualificador · agent_18 reunion · agent_19 propuestas · agent_20 negociacion · agent_21 discrepancias · agent_27 clasificador · agent_31 enriquecedor_dda · etc)
   - **Agent 21** literal "Servicio determinista cross-motor (NO LLM · SQL detectors magerit_vs_dda + dda_vs_evidence)"
   - **ChurnPredictor** "NO ML black-box · 6 reglas if/then auditables ENAC compliance"
   - **8+ admin dashboards** cross-motor signals visualized:
     - `/admin/dashboard` Marcos cockpit (KpiRow + MyDay + Alerts + Activity)
     - `/admin/operations` OperationsConsole M25/M26/M27
     - `/admin/llm-observability` cost+anomalies+top consumers
     - `/admin/compliance/monitor` 19 checks (post Atom 10.1)
     - `/admin/copilot` Agent 14
     - `/admin/retainers` ChurnPredictor scores
     - `/admin/finance` billing health
     - `/admin/pipeline` cross-motor opportunities
   - **LLM router** `core/ai/llm_router.py` wrapping Anthropic SDK (claude-sonnet-4-5 + claude-opus-4-6 fallback · retry backoff)
   - **Cross-motor services**: `motors/m21_diagnosis/dashboard_service.py` ProjectDashboardService MB-13.1 · `api/v1/operations.py` admin · `api/v1/projects.py` 6 KPIs
   - **m_compliance_monitor** 19 checks production-ready post Atom 10.1
   - **Data sources structured**: A21Discrepancy + A21ScanRun + RetainerHealthSignal + ChurnSignals + llm_interaction_log + monitor_results + risk_score

## Decision

**NO new motor `m_intelligence/` construido**.

Intelligence cross-motor functionality ALREADY DISTRIBUTED across:

- 22 specialized agents (each with cross-motor domain logic)
- 8+ admin dashboards (signals visualization production-grade)
- Cross-motor services (`dashboard_service` · `operations` · `projects` KPIs)
- LLM router infrastructure (production-ready Anthropic SDK wrapper)
- Anti-hallucination boundary CEMENTED (deterministic detectors + LLM narrative-only)

Building monolithic `m_intelligence/` motor would introduce:

- Architectural duplication of 22 distributed agents
- 8+ dashboard concept overlap risk
- Maintenance burden 2 paralelos sistemas
- Spec-perfect FAIL (vaporware concept without literal backing)

## Anti-pattern detection · "0 deuda perfecto" cement preserved

Cement Marcos literal "0 deuda técnica · sin deuda al máximo · todo perfecto" requires distinguish empirical:

- **DEFER architectural with ADR explícito** = NO deuda (honest closure documented)
- **BUILD redundant duplication existing infrastructure** = deuda introduced (anti-pattern)

This ADR honors "perfecto" cement via architectural decision EXPLICIT (NOT silent defer) + audit-driven empirical evidence distributed pattern.

## Future revisit trigger

If specific functional gap emerges concrete (e.g. "I cannot see X cross-motor insight anywhere in current 8+ dashboards"), revisit with:

1. Specific gap identified empirical (NOT umbrella term)
2. Reuse existing infrastructure (extension OR new agent OR dashboard extension)
3. ADR cement scope decision (analog ADR-046 + ADR-047 pattern · renamed post-audit B1.2)

## Q5.3 cement applied forward

If future revisit builds insights surface:

- **Admin-only access** (no cliente "AI told us about you" labels)
- Q5.3 cement INVISIBLE cliente pattern sostained (same as roles ENS + capabilities)
- Pattern consistent with ADR-046 cement (renamed post-audit B1.2 · was ADR-037 MB-10)

## Consequences

### Positive

- "0 deuda perfecto" cement honored via explicit architectural decision
- ~6-10h effort saved (audit-driven empirical decision)
- 22 agents + 8+ dashboards production-grade infrastructure preserved
- NO architectural duplication risk
- Forward path documented if specific gap emerges
- Spec-perfect aligned (NO vaporware build)

### Negative

- Cumulative memorial term "Intelligence cross-motor" Block 6 closure formally retired (replaced with "distributed pattern across 22 agents + dashboards")
- Future docs should reference specific agent/dashboard, NOT "Intelligence cross-motor" umbrella term

## OPS cement cumulative validated

- OPS-026 audit-first sostained 30ª aplicación · catch vaporware preventive
- OPS-027 existing infra discovery · reuse vs reinvent
- OPS-050 cement 10ª vez · MEMORY drift sistemático detected
- OPS-058 product-perfect + spec-perfect aligned (this decision)
- OPS-061 NEW cement 3ª vez · vaporware path/component detection cumulative pattern
- OPS-062 NEW cement · "0 deuda perfecto" honors DEFER architectural with ADR explicit

## References

- `docs/master_plan/fulkro_26_motores_v1.md` (empirical · 26 motores M01-M26 + extensions)
- ADR-046 capability vs feature_flag (cement pattern reference · renamed post-audit B1.2 · was ADR-037 MB-10)
- ADR-036 SAN-D MB-17 `core/feature_flags/` infrastructure
- `backend/app/agents/` (22 agents distributed)
- `backend/app/motors/m21_diagnosis/dashboard_service.py`
- `backend/app/core/ai/llm_router.py`
- `progress/SPRINT_POLISH_BLOCK6_REDIS_AUDIT_PIVOT_2026_05_12.md` (umbrella term source)
