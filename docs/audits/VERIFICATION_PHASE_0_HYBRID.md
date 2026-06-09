# Phase 0 · Empirical State Verification · Future-1.E.1.dossier-pack-10docs Path Hybrid

**Status**: ✅ ALL GATES GREEN · proceed Phase C-hybrid

**Date**: 2026-05-23

**Methodology**: OPS-052 strengthened doctrine · architect runs empirical filesystem inspection ANTES briefing-generation propagation. 7-step verification per pattern.

---

## Step 1 · Motor structure empírico

```
backend/app/motors/m27_conformity/      (directory · production-grade)
backend/app/motors/m09_audit_prep/      (directory · production-grade)
backend/app/motors/m06_document_factory/ (directory · production-grade)
```

## Step 2 · LOC baseline empírico

| Motor | Total LOC | Key file LOC |
|-------|-----------|--------------|
| **m27_conformity** | **6525** | conformity_service_paso5.py: 783 · api.py: 1025 · api_paso5.py: 539 · service.py: 301 |
| **m09_audit_prep** | **3485** | checklist_service.py: 954 · dossier_generator.py: 565 · internal_auditor.py: 463 · api.py: 453 · matriz_99.py: 406 |
| **m06_document_factory** | **507** (service only) | service.py: 507 |

## Step 3 · M27 ↔ M9 cross-reference state

```bash
grep -l "m27\|conformity" backend/app/motors/m09_audit_prep/*.py  → 0 matches
grep -l "m09\|audit_prep" backend/app/motors/m27_conformity/*.py  → 1 match (renewal_scheduler only)
```

**Verdict**: **GREENFIELD wire** · M9 dossier_generator does NOT currently invoke M27 declaration generation.

## Step 4 · DocumentFactoryService (M6) wire pattern

`DocumentFactoryService.generate_document(project_id, template_codigo, context, generate_pdf, sign, generated_by, enforce_gates)` is the canonical entry point.

Returns dict with: `docx_path`, `pdf_path`, `rendered_hash`, `signature_ed25519`, Document record persisted.

## Step 5 · E701 template status

```
backend/app/motors/m06_document_factory/templates/deliverables/E701_auditoria_interna_pre_externa.md
backend/app/motors/m06_document_factory/templates/deliverables/E701_auditoria_interna_pre_externa.py
```

Template variables required (per .md inspection):
- `cliente.razon_social`
- `proyecto.codigo_documento_base`, `proyecto.version_actual`, `proyecto.sistema_principal`, `proyecto.alcance`, `proyecto.categoria_ens`
- `responsables.consultor.nombre`, `responsables.consultor.cargo`
- `responsables.responsable_seguridad.nombre`, `responsables.responsable_seguridad.cargo`
- `cliente.organo_aprobador_politicas`
- `auditoria.fecha_inicio`, `auditoria.fecha_fin`, `auditoria.auditor_jefe`, `auditoria.equipo_auditor`, `auditoria.e700_ref`, `auditoria.externa_fecha`
- `cierre_ncs` (iterable), `nuevas_ncs` (iterable), `documentos_revisados` (iterable), `puntos_riesgo` (iterable)
- `resumen.ncs_iniciales`, `resumen.ncs_cerradas`, `resumen.ncs_pendientes`, `resumen.ncs_nuevas`

`build_e701_context` in `internal_auditor.py:427` builds context but **does NOT populate** `auditoria`, `cierre_ncs`, `nuevas_ncs`, `documentos_revisados`, `puntos_riesgo`, `resumen`. **Gap identified for Phase E polish**.

## Step 6 · Declaration templates E-041..E-044

```
✅ E041_declaracion_conformidad_ens.md + .py        (template registered)
✅ E042_comunicacion_cambio_material_sistema.md + .py
✅ E043_renovacion_periodica_conformidad.md + .py
❌ E044                                              (NO template found · scope-out from Hybrid)
```

E-044 was originally cited in M27 `DECLARATION_DOCUMENTS` (service.py:92) but NO template exists. Honesty note · scope-out from Hybrid: M27 declaration flow targets E-041 only via `process_basic_declaration` · E-042/E-043 are change/renewal-driven workflows (separate triggers).

## Step 7 · Tests + Frontend exposure

### Backend tests existing
- `backend/tests/motors/m09_audit_prep/test_m09_dossier.py` (520 LOC) · existing dossier test suite
- `backend/tests/motors/m27_conformity/test_m27_paso5_conformity.py` (616 LOC) · existing M27 tests covering `process_basic_declaration`

### Frontend exposure
- M9 dossier UI: existing per CLAUDE.md (DossierPreview + PlanGantt production)
- M27 admin UI: existing per Phase B audit

## Step 8 · M9 dossier `DELIVERABLE_TO_FOLDER` gap

Current mapping (`backend/app/motors/m09_audit_prep/dossier_generator.py:67`):

```python
DELIVERABLE_TO_FOLDER: dict[str, str] = {
    "E-001": "06_NORMATIVA",
    "E-002": "06_NORMATIVA",
    "E-003": "07_PROCEDIMIENTOS",
    "E-005": "01_GOBIERNO",
    "E-012": "02_CATEGORIZACION",
    "E-040": "04_DECLARACION_APLICABILIDAD",
    "E-050": "03_ANALISIS_RIESGOS",
    "E-400": "10_PLAN_CONTINUIDAD",
    "E-500": "10_PLAN_CONTINUIDAD",
    "E-702": "13_INFORMES_TECNICOS",
    "E-703": "13_INFORMES_TECNICOS",
    "E-704": "13_INFORMES_TECNICOS",
    "E-705": "13_INFORMES_TECNICOS",
    "E-706": "13_INFORMES_TECNICOS",
}
```

**Missing**: E-041 · E-042 · E-043 · E-701 · they fallback to wrong folder ("08_REGISTROS_OPERATIVOS"). Phase C fix adds these mappings.

---

## Gate evaluation (briefing rules)

| Rule | Result |
|------|--------|
| M27 ya wired a M9 (>80% integration) → STOP HARD | ❌ 0% wire · greenfield ✅ proceed |
| M27 100% greenfield wire | ✅ proceed Phase C |
| M27 partial wire | n/a |
| E701 template missing | ✅ template EXISTS · proceed Phase E |

**Verdict**: ✅ ALL gates green · proceed Phase C-hybrid auto-arranque.

---

## Phase C-hybrid implementation approach (decided post-Phase 0)

1. **Extend `DELIVERABLE_TO_FOLDER`** add E-041 + E-042 + E-043 + E-701 mappings:
   - E-041 → "01_GOBIERNO" (Declaración corporate-level)
   - E-042 → "13_INFORMES_TECNICOS" (Comunicación cambio material)
   - E-043 → "01_GOBIERNO" (Renovación periódica)
   - E-701 → "13_INFORMES_TECNICOS" (Auditoría interna pre-externa)

2. **New collector** `_collect_conformity_declarations(db, project_id)` in `dossier_generator.py` queries M27 `BasicDeclarationRow` + `ConformitySubmissionRow` · returns list of declaration metadata.

3. **New helper service method** in M9 `dossier_generator.py`:
   ```python
   async def generate_declaracion_conformidad_via_m27(
       db: AsyncSession, project_id: UUID,
       responsible_person_name: str, responsible_person_email: str,
       published_url: str | None = None,
   ) -> dict[str, Any]
   ```
   Invokes M27 `process_basic_declaration` + returns declaration metadata.

4. **Wire into `generate_dossier`**: include declarations in ZIP under `01_GOBIERNO/declaracion_conformidad/`.

5. **Tests**: 3-5 new tests in `test_m09_dossier.py`:
   - `test_deliverable_e041_classified_to_gobierno`
   - `test_collect_conformity_declarations_empty`
   - `test_collect_conformity_declarations_with_declaration`
   - `test_dossier_includes_declaration_artifacts`
   - `test_generate_declaracion_conformidad_via_m27_basica`

6. **Frontend**: NO new components · DossierPreview will display existing artifacts list (declarations now included).

ADR-025 sostained · 0 new tables · 0 new templates · orchestration only.
OPS-045 audit-first reuse M27 production-grade existing.
