# Golden datasets · curation + eval workflow

**Sub-atom**: 1.E.1.B.3 · FULKRO LLM Ops Platform v2 · regression detection
post-prompt-change y post-model-bump per agente LLM activo.

## Purpose

Golden datasets bloquean **regresiones silenciosas** cuando:

- Cambia un system prompt de agente (e.g. añades una nueva sección de guía)
- Sube un modelo (e.g. Sonnet 4.6 → Sonnet 4.7) y output schema drift
- Cambia prompt caching strategy y latencia degrada
- Se introduce un nuevo validator y rompe outputs históricos

Cada agente activo curated tiene 5-10 examples canónicos cubriendo sector
mix (sanidad MEDIA · aapp BASICA · fintech ALTA · otro PYME) + severity
range (verdict `listo_auditar` → `muy_lejos`).

## Storage (Opción A JSON files · canonical FULKRO pattern)

```
docs/catalogs/golden_datasets/
├── README.md
├── agent_11_auditor_virtual/
│   └── v1.json                                # primer dataset · curation B.3.C
├── agent_04_redactor/                         # Future-B.3 demand-driven
├── agent_06_contratos/                        # Future-B.3
└── ...
```

ADR-025 sostained · NO DB table · YAML/JSON catalog pattern (docs/catalogs/*).
Loader cached singleton · OPS-026 DRY.

## JSON schema (`v1.json`)

```json
{
  "agent_name": "agent_11_auditor_virtual",
  "version": "v1",
  "created_at": "YYYY-MM-DD",
  "curated_by": "marcos",
  "purpose": "Sector mix coverage statement",
  "schema_version": "1.0",
  "regression_thresholds": {
    "pass_rate_warn_below": 0.8,
    "pass_rate_alert_below": 0.6
  },
  "entries": [
    {
      "id": "a11-001",
      "category": "ens_dossier_basic_sanidad",
      "input": {
        "ens_category": "MEDIA",
        "sector": "sanidad",
        "m10_audit_result": { "score_conformidad": 72, "nc_mayores": [...] },
        "client_context": { "company_name": "Sintético S.L." }
      },
      "expected_output": {
        "verdict": "listo_con_riesgos",
        "issues_critical": 0,
        "key_phrases_required": ["mp.info.3", "Plan Acción Correctivo"],
        "key_phrases_forbidden": ["[error]", "no aplica", "TODO"]
      },
      "rubric": {
        "structure_check": true,
        "ens_coverage_required_pct": 80
      }
    }
  ]
}
```

## Curation workflow (B.3.C session-specific)

1. **Marcos input session** · por agente · revisa 5-10 escenarios reales
   anonymized (CIFs sintéticos · NO PII)
2. **Schema validation** · `python -m backend.app.motors.m_observability.eval_runner --list`
   debe listar el nuevo dataset
3. **Pre-merge eval** · `pytest -m golden backend/tests/motors/m_observability/`
   debe pasar (loader schema verify)
4. **PR review** · approve manual + merge

## CLI usage

```bash
# Listar todos golden datasets disponibles
python -m backend.app.motors.m_observability.eval_runner --list

# Ejecutar eval skeleton (sin LLM · 0 entries · vacuously OK)
python -m backend.app.motors.m_observability.eval_runner \
    --agent agent_11_auditor_virtual --version v1

# Con report file output
python -m backend.app.motors.m_observability.eval_runner \
    --agent agent_11_auditor_virtual --version v1 \
    --report-out /tmp/a11_eval.md

# JSON format para CI artifact
python -m backend.app.motors.m_observability.eval_runner \
    --agent agent_11_auditor_virtual --version v1 \
    --format json --report-out /tmp/a11_eval.json
```

### Exit codes

| Code | Severity | Trigger | Action |
|------|----------|---------|--------|
| 0 | ✅ ok | pass_rate ≥ `pass_rate_warn_below` | continue |
| 1 | ⚠️ warn | pass_rate < `pass_rate_warn_below` (default 0.8) | admin digest alert |
| 2 | 🛑 alert | pass_rate < `pass_rate_alert_below` (default 0.6) | immediate alert |
| 3 | error | dataset load failed (missing · schema invalid) | fix dataset |

## Pytest harness

```python
import pytest

pytestmark = pytest.mark.golden  # registered en pyproject.toml

def test_my_agent_skeleton_loadable():
    from backend.app.motors.m_observability.golden_datasets_loader import (
        load_golden_dataset,
    )
    ds = load_golden_dataset("agent_XX_name", "v1")
    assert ds.entries  # post-curation
```

Run only golden tests:
```bash
pytest -m golden backend/
```

Skip golden en CI rápido:
```bash
pytest -m "not golden" backend/
```

## Real evaluator wiring (B.3.D phase · post-skeleton)

```python
from backend.app.motors.m_observability.eval_runner import (
    register_evaluator,
    run_eval,
)
from backend.app.agents.agent_11_auditor_virtual import Agent11AuditorVirtual

def a11_evaluator(entry, actual):
    # custom logic per agente (anti-hallucination · sector match · etc)
    if actual.get("veredicto") != entry.expected_output.verdict:
        return False, f"verdict mismatch · expected={entry.expected_output.verdict}"
    return True, "ok"

register_evaluator("agent_11_auditor_virtual", a11_evaluator)

def real_actual_provider(entry):
    agent = Agent11AuditorVirtual(...)
    return agent.run(entry.input)

report = run_eval(
    "agent_11_auditor_virtual", "v1",
    actual_provider=real_actual_provider,
)
```

## Reglas curation inviolables

- **0 PII** · CIFs sintéticos · nombres genéricos
- **Anti-hallucination patterns** referenced en `expected_output`
  (e.g. `nc_origen ∈ input.m10_audit_result.nc_mayores ∪ nc_menores`)
- **Rubric criteria empíricamente verificables** · NO subjective "sounds good"
- **Sector mix obligatorio** (sanidad · aapp · fintech · otro) per dataset
- **Severity range** · al menos 1 entry de cada verdict canonical

## Versionado

- `v1` baseline · referenced indefinidamente
- `v2` cuando schema breaking change (new required field en rubric)
- Histórico preserved · `v1` queryable post-`v2` merge

## Roadmap B.3.C-E sessions siguientes

| Phase | Scope | ETA empírico |
|-------|-------|--------------|
| B.3.A | Audit-first existing infrastructure | ✅ DONE |
| B.3.B | Skeleton storage + loader + runner + CLI + tests | ✅ DONE |
| B.3.C | A11 curation 5-10 entries (Marcos input) | ~1-2h |
| B.3.D | Regression detection wiring (actual_providers · alerts) | ~1.5-2h |
| B.3.E | Admin UI extension (/admin/llm-observability/golden-eval) | ~1.5-2h |

## Cross-references

- ADR-025 (NO new tables · YAML/JSON catalog canonical FULKRO)
- ADR-031 (ENAC-ready trazabilidad determinista · golden = regression insurance)
- OPS-026 DRY (loader singleton pattern reuse)
- OPS-045 audit-first (B.3.A reveals 7 reuse opportunities)
- LECCIÓN-OPS-049 ARTIFACT honesty (skeleton claims 0 entries · curation B.3.C)
- LECCIÓN-OPS-052 architect briefings empirical verification
