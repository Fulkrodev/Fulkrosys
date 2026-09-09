# Golden datasets · m_observability eval harness

**Sub-atom**: 1.E.1.B.3 · FULKRO LLM Ops Platform v2

Cada agente LLM activo tiene una carpeta `<agent_name>/v<version>.json`
con golden examples curados manualmente para regression detection
post-prompt-change o post-model-bump.

## Estructura

```
docs/catalogs/golden_datasets/
├── README.md                                  (este documento)
├── deliverable_text_auditor/                  (capability NEW · pending build Future-1.E.1.dossier-pack-10docs)
│   └── v1.json                                (10 entries Marcos-curated · B.3.C · entry IDs a11-* historical)
├── agent_04_redactor/                         (Future-B.3 · post DeliverableTextAuditor build)
├── agent_06_contratos/                        (Future-B.3)
└── ...
```

## JSON schema canonical

```json
{
  "agent_name": "agent_<id>_<slug>",
  "version": "v1",
  "created_at": "YYYY-MM-DD",
  "curated_by": "<author>",
  "purpose": "1-2 sentence statement of scope · sector mix · severity coverage",
  "schema_version": "1.0",
  "regression_thresholds": {
    "pass_rate_warn_below": 0.8,
    "pass_rate_alert_below": 0.6
  },
  "entries": [
    {
      "id": "<agent_short>-<NNN>",
      "category": "<scenario_label>",
      "input": { /* agent-specific shape */ },
      "expected_output": {
        "verdict": "<canonical_value>",
        "issues_critical": 0,
        "key_phrases_required": ["..."],
        "key_phrases_forbidden": ["..."]
      },
      "rubric": {
        "structure_check": true,
        "ens_coverage_required_pct": 80
      }
    }
  ]
}
```

## Loader pattern

Use `backend/app/motors/m_observability/golden_datasets_loader.py`:

```python
from backend.app.motors.m_observability.golden_datasets_loader import (
    load_golden_dataset,
    list_available_datasets,
)

ds = load_golden_dataset("deliverable_text_auditor", version="v1")
# ds.entries → list[GoldenDatasetEntry]
```

Loader is **singleton cached** (mismo pattern `copilot_personas_loader` ·
OPS-026 DRY sostener).

## Runner CLI

```bash
python -m backend.app.motors.m_observability.eval_runner \
    --agent deliverable_text_auditor \
    --version v1 \
    --skip-llm-if-no-key \
    --report-out /tmp/a11_eval_report.md
```

Returns:
- Markdown report (default)
- Exit code 0 si pass_rate ≥ pass_rate_warn_below
- Exit code 1 si pass_rate < pass_rate_warn_below (warn)
- Exit code 2 si pass_rate < pass_rate_alert_below (alert)

## Curation workflow (B.3.C session-specific)

1. **Marcos input session** · per agente · revisa 5-10 escenarios reales
2. **PR** con nuevas entries en `<agent>/v<version>.json`
3. **CI runs eval** automatic en PR (pytest `@pytest.mark.golden`)
4. **Merge** cuando pass_rate ≥ threshold + manual review approval

## Versionado

- `v1` baseline · referenced indefinidamente
- `v2` cuando schema breaking change (NUEVOS campos required en rubric)
- Histórico preserved · `v1` queryable post-`v2` merge

## Reglas inviolables curation

- Cliente NUNCA aparece nombrado (datos sintéticos · CIFs fake)
- Output schema MUST match agent's Pydantic strict validator
- Anti-hallucination patterns referenced (e.g. nc_origen ∈ input)
- Rubric criteria empíricamente verificables (NO subjective "sounds good")

## Cross-references

- ADR-025 (NO new tables · YAML/JSON catalog canonical FULKRO)
- ADR-031 (ENAC-ready trazabilidad determinista · golden = regression insurance)
- OPS-026 DRY (loader singleton pattern reuse)
- OPS-045 audit-first (B.3.A reveals 7 reuse opportunities sostained)
- LECCIÓN-OPS-049 ARTIFACT honesty (skeleton claims 0 entries · curation B.3.C)
- LECCIÓN-OPS-052 architect briefings empirical verification
