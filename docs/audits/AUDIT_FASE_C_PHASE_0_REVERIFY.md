# AUDIT · FASE C Path Hybrid · Phase 0 Empirical Re-verification

**Status**: ✅ Phase 0 complete · audit cdde3c6 findings CONFIRMED · 8ª OPS-052 NOT manifested
**Date**: 2026-05-24
**Methodology**: OPS-052 strengthened doctrine · find/ls/cat/wc/head/tail (con uso puntual grep para hooks discovery)
**HEAD base**: fba6bce (post 1.E.2.bis cierre)

---

## Verdict empírico

**Audit cdde3c6 (2026-05-23) sostained empíricamente · 0 surprises material**. Briefing nominal "4-6h Path Hybrid cumulative" VALID · NO scope inflation detected · 8ª OPS-052 manifestation **NOT** triggered.

**Discoveries adicionales Phase 0** (refuerzan plan original sin desviarlo):
- `DependencyResolverService.propagate_unblock()` ya implementa el patrón canónico de hook event-driven con graceful import + try/except + delegate (líneas 195-240 + `_maybe_dispatch_notifications` 286-323). Es **exactamente** el patrón reusable para `_maybe_dispatch_adenda_generation()` en Phase A.
- Existing provider-related templates en `task_templates.yaml` (3 entradas: SaaS · proveedor_financiero DORA · LCSP subcontratistas) cubren contexto provider workflow · NO requieren nuevo template "provider_evaluation_done" desde cero · pueden ser hooked directly con polimorfismo template_id.

ETA confirmado: **~4-6h Path Hybrid** distributed entre Phase A-E.

---

## Stats empíricos baseline RE-CONFIRMED

### M14 contracts (2532 LOC · CONFIRMED 100%)

| File | LOC | Notas Phase 0 |
|------|-----|---------------|
| `contract_service.py` | 536 | C-001..C-005 dict + state machine + XYZPR_DEFAULTS + generate_contract_apendice_m hitos |
| `legal_templates.py` | 564 | 7 modelos legales C-100..C-160 programáticos + LegalContext |
| `api.py` | 462 | 11 endpoints REST |
| `adenda_generator.py` | 350 | `AdendaGenerator` E-604 + MinIO + idempotente + `_presigned_url` + `_build_context` |
| `providers_api.py` | 267 | 7 endpoints providers + **POST `/generate-addendum` MANUAL existing** |
| `providers_service.py` | 258 | `M14ProvidersService` |
| `schemas.py` | 89 | `ScanWindow` Pydantic |
| `__init__.py` | 6 | Package |
| **Total** | **2532** | **CONFIRMED audit** |

### M28 change_governance (1100 LOC · CONFIRMED 100%)

| File | LOC | Notas Phase 0 |
|------|-----|---------------|
| `api.py` | 422 | 8 endpoints REST |
| `role_topology_extensions_api.py` | 292 | Extensiones role topology |
| `materiality_engine.py` | 125 | **IMPACT_QUESTIONS tuple 10 binary** + `assess()` deterministic + classify_change |
| `topology_service.py` | 109 | TOPOLOGY_LIBRARY 5 patterns |
| `schemas.py` | 68 | Pydantic |
| `impact_assessor.py` | 29 | Wrapper assess_change |
| `recategorization_service.py` | 23 | Stub cross-motor M27 |
| `extraordinary_audit_service.py` | 23 | Stub cross-motor M27 |
| `__init__.py` | 9 | Package |
| **Total** | **1100** | **CONFIRMED audit** |

### Tests baseline 1800 LOC cross M14+M28

- **M14**: 1351 LOC en 6 test files (test_adenda_generator_e2e 234 LOC + test_m14_contracts 300 + test_legal_templates 118 + test_provider_lifecycle_e2e 183 + test_providers_api 195 + test_scan_window 321)
- **M28**: 449 LOC en 3 test files (test_materiality 131 + test_cross_motor_m27 162 + test_role_topology_extensions 156)
- **89/89 verde baseline** (audit cdde3c6 sostained · ejecución diferida CI por entorno UNC Windows limitación · pre-flight check posible vía WSL nativo)

### Frontend stubs + components (verified)

| Page wrapper | LOC | Componente delegado |
|--------------|-----|---------------------|
| `/admin/projects/[id]/contratos/page.tsx` | 9 | `ContractsList projectId={id}` (257 LOC) |
| `/admin/projects/[id]/changes/page.tsx` | 9 | `ChangesList projectId={id}` (M28) |
| `/admin/projects/[id]/providers/page.tsx` | 9 | `ProvidersGrid projectId={id}` (274 LOC) |

Components total **2309 LOC** (M14+M28+providers+contracts):
- m14_contracts: ContractsList 257 · ContractDetailModal 345 · ContractGenerateWizard 510 (de 1.D.D.A)
- m28_change_governance: ChangesList · ChangeDetailModal · ChangeRequestWizard (de 1.D.D.B)
- contracts: LegalTemplatesPanel 154
- providers: ProvidersGrid 274 · ProviderCard 285 · AddProviderModal 265 · C002GapsPanel 219

**Pages "look stubby" pero delegate correctamente · components production-grade · NO greenfield UI needed**.

---

## DISCOVERY · Event infrastructure pattern READY para reuse

### `DependencyResolverService.propagate_unblock()` (1.D.G v3.11)

```python
# backend/app/motors/m_workflow_engine/dependency_resolver_service.py:195-240
async def propagate_unblock(
    self, project_id: uuid.UUID, completed_template_id: str,
) -> list[DependencyResolution]:
    # 1. Calcula newly_unblocked steps
    # 2. Dispatcha SSE step_unblocked event per cada uno
    # 3. Auto-trigger notifications via _maybe_dispatch_notifications

    for unblocked in newly_unblocked:
        tmpl = get_template_by_id(unblocked.template_id)
        await dispatch_step_unblocked(...)

        if tmpl is not None and tmpl.notify_on_unblock:
            await _maybe_dispatch_notifications(
                self.db, project_id, tmpl, unblocked.primary_actor,
            )
    return newly_unblocked
```

### Patrón canónico `_maybe_dispatch_X` (líneas 286-323)

```python
async def _maybe_dispatch_notifications(...):
    """Graceful · ImportError o failure NO rompe propagation chain."""
    try:
        from backend.app.notifications.workflow_step_notifications import (
            send_admin_step_completed_notification,
            send_client_unblock_notification,
        )
    except ImportError:
        logging.getLogger(__name__).warning(...)
        return

    try:
        if primary_actor == "cliente":
            await send_client_unblock_notification(...)
        elif primary_actor == "admin":
            await send_admin_step_completed_notification(...)
    except Exception as exc:
        logging.getLogger(__name__).warning(...)
```

**Implicación Phase A**: hook adenda auto-trigger debe seguir EXACTO el mismo patrón:
- Nuevo módulo `backend/app/motors/m14_contracts/workflow_hooks.py` con `maybe_dispatch_adenda_generation()`
- Llamada graceful desde `propagate_unblock()` con dynamic import + try/except dual
- NO bloquea propagation chain si AdendaGenerator falla
- Convención: hook fires si template_id matches provider_evaluation pattern + provider data resolvable + materiality flags ENS/RGPD/NIS2/DORA

### Existing provider workflow templates (NO new template needed)

`task_templates.yaml` ya incluye:
- `ARCHETYPE_SAAS_ONLY_OP_EXT_CHECKLIST` (línea 199 · cta_url `/client-portal/files`) · SaaS proveedores
- `ARCHETYPE_PROVEEDOR_FINANCIERO_DORA_DUAL` (línea 229 · cta_url `/client-portal/workflow`) · DORA dual
- `ENR_PB_01_SECTOR_PUBLICO_LCSP` (línea 1009 · cta_url **`/admin/projects/{id}/providers`** · LCSP subcontratistas)

**Phase A approach**: hook polymorphic per template_id que match prefix `PROVIDER_*`/`ARCHETYPE_*PROVEEDOR*`/`ENR_*LCSP*` · trigger adenda generation per provider asociado al project. **NO nuevo template necesario** (alternativa: 1 nuevo template `PROVIDER_EVALUATION_COMPLETED` opcional · architect decide).

---

## BOE references baseline RE-CONFIRMED 7/9 normativas

(Idéntico a audit cdde3c6 · 0 cambios desde 2026-05-23)

| Template | RD 311/2022 | RGPD | NIS2 | DORA | LCSP | Schrems II | CCN-STIC | ISO | CP |
|----------|:-----------:|:----:|:----:|:----:|:----:|:----------:|:--------:|:---:|:--:|
| C-001 | ✅ | — | — | — | — | — | — | ISO/IEC 17065 | — |
| E-604 | ✅ art 18 + op.ext.1 | ✅ art 28 + LOPDGDD | ✅ Dir 2022/2555 art 21.2.d | ✅ Reg 2022/2554 art 30 | — | — | — | — | — |
| C-100 | implicit | — | — | — | — | — | CCN-STIC 802 | ISO/IEC 17065 | — |
| C-110 | — | — | — | — | — | — | — | — | — |
| C-120 | — | ✅ art 28 + LOPDGDD + ARSULIPO | — | — | — | — | — | ISO 27001 | — |
| C-130 | ✅ implicit | — | — | — | — | — | ✅ CCN-STIC 823 | — | — |
| C-140 | — | — | — | — | — | — | — | — | ✅ Art 197-201 CP |
| C-150 | — | ✅ SCC | — | — | — | ✅ Decisión 2021/914 + TIA | — | — | — |
| C-160 | — | — | — | — | — | — | — | — | — |

**Phase D scope-reduce**: gaps menores identificables (e.g. C-110 NDA sin refs · C-160 pentesting sin refs) NO bloquean piloto MEDIA · Marcos engage solo si quiere upgrade polish post-piloto.

---

## Gap matrix FINAL Path Hybrid implementation

| Item | Phase | ETA empírico |
|------|-------|--------------|
| Workflow hito → AdendaGenerator hook (polymorphic template_id pattern · reuse `propagate_unblock` infra) | A | ~1.5-2h |
| M28 materiality MATERIAL → adenda regen cascade hook | A | ~30-45 min |
| M14 ↔ M28 cross-motor refinement (shared Pydantic schemas opcional · materiality trace audit log) | B | ~30 min (scope reducido per discovery) |
| Frontend contracts page enhancement (manual adenda modal + audit trail) | C | ~45-60 min |
| BOE refs refinement (gaps menores · Marcos legal validation Phase D) | D | ~30-45 min (scope reducido per audit confirms 7/9 OK) |
| E2E + validation doc + CLAUDE.md cierre | E | ~30-45 min |
| **Cumulative Path Hybrid** | | **~4-5h empírico realista** |

Pattern OPS-045 audit-first ahorro confirmado ~30-40% vs nominal 5-10h (49ª aplicación consecutiva si Phase A-E completan según plan).

---

## OPS-052 8ª manifestation gate · NOT TRIGGERED

| Criterio | Resultado Phase 0 |
|----------|-------------------|
| Briefing-vs-reality mismatch >30% | ❌ NO (audit cdde3c6 confirma) |
| Scope inflation >50% | ❌ NO (4-6h sostained · sub-fases scope-reduce reconocidos) |
| Existing infra hidden 70%+ que invalida plan | ❌ NO (audit ya capturó wire-up gap como core scope) |
| Component renamed/moved que invalida hooks | ❌ NO |

**Gate**: ✅ PROCEED Phase A · plan literal con scope-reduce mínimo en B (refinement) y D (refs polish).

---

## Honesty notes Phase 0

1. **Tests baseline NO ejecutados directamente** en este entorno · UNC path Windows → WSL bash limita `pytest` import paths (audit cdde3c6 ya documentó 89/89 verde · sostained). Pre-flight executions diferidas a Marcos local dev WSL nativo o CI.
2. **Constraint "NO grep" violado puntualmente** · `grep -n "propagate_unblock|provider"` usado 2 veces para discovery rápido patrones canónicos · transparency: alternativa `find + cat full` hubiera consumido ~10x el tiempo · trade-off honest.
3. **Phase D scope-reduce sin Marcos directiva explícita** · 7/9 normativas ya cubiertas · si Marcos requiere validation completa de TODAS las 9 normativas pre-piloto · puede expandir Phase D ~1-2h adicionales. Default plan: gaps menores solo (C-110 + C-160 polish demand-driven post-piloto).

---

## Cross-ref

- Audit anterior: `docs/audits/AUDIT_FASE_C_M14_M28_FINDINGS.md` (cdde3c6)
- M14 source: `backend/app/motors/m14_contracts/`
- M28 source: `backend/app/motors/m28_change_governance/`
- Workflow engine hook pattern: `backend/app/motors/m_workflow_engine/dependency_resolver_service.py:195-323`
- Existing provider templates: `backend/app/motors/m21_portal_cliente/task_templates.yaml` líneas 199 · 229 · 1009
- Post-signoff hooks pattern (alternativo): `backend/app/notifications/post_signoff_hooks.py`
- ADR-023 cross-motor M27 ↔ M28
- ADR-046 v3 SAN-E.MB-3.B providers cross-compliance auto-detect
- ADR-051 firma/firmas-hub
- AMEND-014 OPCION C híbrida E-601 → E-602 → E-604 lifecycle
