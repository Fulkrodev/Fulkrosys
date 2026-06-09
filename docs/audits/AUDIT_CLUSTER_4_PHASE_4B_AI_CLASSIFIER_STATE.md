# AUDIT CLUSTER 4 Phase 4B · AI Auto-Classification Cliente Uploads Empirical State

**Sesión**: 3B-2B.8 CLUSTER 4 Phase 4B
**Fecha**: 2026-05-26
**Ejecutor**: Phase 4B.0 OPS-052 audit mandatory
**Status**: ✅ **Audit complete · scope refined enhanced classifier pure functional · NO STOP HARD**

---

## Resumen ejecutivo

Briefing Phase 4B asumió AI auto-classifier para cliente uploads. Empirical reality:

- ✅ **M24 IDMS keyword classifier** (`idms_service.py:CLASSIFICATION_RULES`) existing · 14 keyword groups → 5 clasificacion types (contrato/registro/informe/politica/procedimiento/evidencia/otro)
- ✅ **Phase 3A evidence_requests model** existing · evidence_id FK ready · cliente upload links via Phase 3A.cliente_upload endpoint
- ✅ **ens_measures table** existing · 100+ measures (Phase 3C TRANSLATION_OVERRIDES base)
- ✅ **agent_14 RAG pipeline** existing · si Future LLM-based classifier needed
- ❌ **NO AI/ML classifier currently** · solo keyword-based heuristic (M24 IDMS)
- ❌ **NO measure_code suggestion** · CLASSIFICATION_RULES NO link a ENS measure_code
- ❌ **NO confidence scoring** · classifier deterministic O(1) binary match
- ❌ **NO cliente confirmation flow** · admin sets clasificacion directamente

**Refined empirical scope**: Phase 4B aporta enhanced classifier pure functional R1 deterministic (keyword + measure_code mapping + confidence + tags extraction) sin LLM (MVP). LLM-based augment DEFERRED Future-X (post-piloto demand-driven · LLM cost concern).

Architectural decision: pure functional approach honors R1 (deterministic > LLM para decisiones normativas · trazabilidad ENAC) + OPS-026 DRY (extends M24 IDMS CLASSIFICATION_RULES + maps a ENS measure_code).

ETA refined: ~2-3h backend MVP vs briefing 2-4h (-0% to -25% OPS-045 61ª · MVP scope tight pure functional).

---

## Phase 4B.0.1 · Existing classifier infrastructure

### M24 IDMS keyword classifier (idms_service.py:49)
```python
CLASSIFICATION_RULES: list[tuple[tuple[str, ...], str, str]] = [
    (("contrato", "propuesta", "nda", "sla"), "00", "contrato"),
    (("acta", "categori"), "02", "registro"),
    (("riesgo", "magerit", "amenaza"), "03", "informe"),
    (("dda", "aplicabilid"), "04", "registro"),
    (("plan_adecuacion", "plan adecuac"), "05", "informe"),
    (("politic",), "06", "politica"),
    (("procedimiento",), "07", "procedimiento"),
    (("registro", "log"), "08", "registro"),
    (("evidencia",), "09", "evidencia"),
    (("continuidad", "drp", "bia"), "10", "informe"),
    (("formacion", "curso", "training"), "11", "registro"),
    (("proveedor", "vendor"), "12", "registro"),
    (("informe", "e-7", "pentest", "auditoria"), "13", "informe"),
]
```

**Gap**: NO mapping a ENS measure_code · solo a folder code + clasificacion semántica.

### Evidence model (documents.py:96)
- tipo + measure_id + control_id + measure_code (M07 extensions)
- evidence_type_id catalog (M07 types: politica/registro/etc)

### Phase 3A evidence_requests
- measure_code field + tipo_documento + control_id
- evidence_id FK linkage (cliente upload links)

---

## Phase 4B.0.2 · Enhanced classifier design

### NEW Pure functional service · m07_evidence/ai_classifier_service.py

```python
@dataclass(frozen=True)
class ClassificationSuggestion:
    filename: str
    suggested_clasificacion: str       # politica/procedimiento/contrato/etc
    suggested_tipo_documento: str       # mirror tipo
    suggested_measure_codes: list[str]  # 1+ ENS codes mapped from filename + content
    suggested_tags: list[str]
    confidence: float                   # 0.0-1.0 (deterministic compute)
    matched_keywords: list[str]
    rule_id: Optional[str]              # which rule triggered

def suggest_classification(
    filename: str,
    content_preview: str | None = None,
    project_categoria: str | None = None,
) -> ClassificationSuggestion:
    """Canonical pure functional classifier · R1 deterministic.

    Approach: enhanced keyword matching + ENS measure_code mapping + tags
    extraction. NO LLM (cost concern + R1 trazabilidad).

    LLM augment DEFERRED Future-1.E.classifier-llm-augment post-piloto
    demand-driven.
    """
```

### NEW classifier rules · KEYWORD_TO_MEASURE_CODE mapping

```python
KEYWORD_TO_MEASURE_CODE: dict[str, list[str]] = {
    "mfa": ["op.acc.6"],
    "autenticacion": ["op.acc.5", "op.acc.6"],
    "antivirus": ["mp.s.4"],
    "backup": ["mp.info.6"],
    "continuidad": ["op.cont.2"],
    "politica": ["org.4"],
    "drp": ["op.cont.2", "op.cont.3"],
    "bia": ["op.cont.2"],
    "log": ["op.mon.1"],
    "monitorizacion": ["op.mon.1"],
    # ... expandable demand-driven
}
```

### Confidence scoring

```python
def compute_confidence(matched_kw_count: int, total_rules_tried: int) -> float:
    # Deterministic: more matches = higher confidence, max 1.0
    if matched_kw_count == 0:
        return 0.0
    if matched_kw_count >= 3:
        return 1.0
    return 0.3 + 0.35 * (matched_kw_count - 1)  # 0.3 · 0.65 · 1.0
```

---

## Phase 4B.0.3 · Endpoints proposed

### Cliente endpoint (require_client_user · ADR-013)
- `POST /client-portal/evidencias/{evidence_id}/suggest-classification`
  → ClassificationSuggestion (cliente sees suggestion)
- `POST /client-portal/evidencias/{evidence_id}/confirm-classification`
  body { clasificacion, tipo, measure_code, tags } → updates Evidence row +
  audit_log cliente.classification.confirmed

### Admin endpoint (require_owner)
- `POST /admin/evidencias/{evidence_id}/validate-classification`
  body { clasificacion_final, ... } → admin authoritative · audit_log
  admin.classification.validated

### Cliente actions filosofía cliente-mínimo
- Cliente VE suggestion auto-classified (server pre-computes)
- Cliente CONFIRMS suggestion (NO opera classification logic · just accepts/rejects)
- Admin VALIDATES final (admin OWNS classification authoritative)
- Sub-atom 5.A audit_log Sub-atom 5.A 3-way OR cross transitions

---

## Phase 4B.0.4 · Recommended Phase 4B refined scope (~2-3h)

### Phase 4B.1 implementation (~1.5-2h)

**Step 1 · Service module** (~45-60 min)
- `backend/app/motors/m07_evidence/ai_classifier_service.py` NEW
- ClassificationSuggestion dataclass + suggest_classification() pure functional
- KEYWORD_TO_MEASURE_CODE dict (initial 15-20 high-frequency)
- compute_confidence deterministic formula
- TAGS_EXTRACTION_RULES (familia · tipo · categoría)
- Reuse M24 IDMS CLASSIFICATION_RULES (OPS-026 DRY)

**Step 2 · API endpoints + audit_log** (~30-45 min)
- `backend/app/motors/m07_evidence/classifier_api.py` 2 routers
- POST suggest-classification + POST confirm-classification (cliente)
- POST validate-classification (admin)
- audit_log Sub-atom 5.A

**Step 3 · Router wiring** (~5-10 min)

### Phase 4B.2 tests (~30-45 min)

**Backend tests (8-10 tests)**:
- suggest_classification matches keyword + maps measure_code
- suggest_classification handles unknown filename (no rules matched · 0.0 confidence)
- compute_confidence deterministic formula
- KEYWORD_TO_MEASURE_CODE measures present in ens_measures (validation seed)
- Cliente confirm endpoint updates Evidence · audit_log emit
- Admin validate endpoint admin authoritative · audit_log emit
- Filosofía cliente-mínimo: cliente confirms · admin OWNS classification

---

## ETA refined Phase 4B

- **Briefing nominal**: ~2-4h
- **Empirical refined**: ~2-3h backend MVP (pure functional service + 3 endpoints + tests)
- **OPS-045 61ª manifestation**: -25% to -33% vs nominal (audit-first reveals M24 IDMS + ens_measures + Phase 3A linkage rica · solo aggregate classifier + measure mapping)

---

## Filosofía cliente-mínimo compliance

100% aligned:
- Cliente VE suggestion server-side · NO opera classifier logic
- Cliente CONFIRMS suggestion (binary accept/reject)
- Admin VALIDATES final authoritative
- audit_log trace · ENAC trazabilidad cumulative
- NO admin lingo cliente leak

---

## STOP HARD trigger evaluation

**NO STOP HARD necesario**. Briefing intent (AI auto-classifier) ratified · refined a pure functional enhanced classifier (R1 deterministic · NO LLM cost). LLM-based augment DEFERRED Future-X demand-driven.

---

## Patterns potencialmente formalizables Phase 4B

- **Enhanced keyword classifier + measure_code mapping** (R1 deterministic · expandable KEYWORD_TO_MEASURE_CODE dict · confidence scoring formula)
- **Cliente confirms admin validates pattern** (server pre-computes · cliente binary accept · admin authoritative · 3-step lifecycle)

---

## Decisión pendiente

⏸️ **Architect approve Phase 4B.1 refined scope**:
- Pure functional classifier + 3 endpoints (cliente suggest/confirm + admin validate)
- 8-10 tests
- ETA refined ~2-3h
- Filosofía cliente-mínimo 100% aligned
- LLM-based augment DEFERRED Future-1.E.classifier-llm-augment
