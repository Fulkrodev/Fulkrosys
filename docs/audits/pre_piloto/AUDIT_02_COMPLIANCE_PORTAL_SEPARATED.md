# AUDIT #3 · Compliance propio · ¿portal separado o tab admin?

**Status**: ✅ Audit empírico completo · Bloque 1 Mega-baseline item 2/11
**Date**: 2026-05-24
**Scope item**: pre-piloto #3 · "Compliance propio (FULKRO self-monitoring) · portal separado como ENS Radar"

---

## Verdict empírico

Compliance infrastructure es **massive production-grade** (~5790 LOC backend cumulative · m_compliance + m_compliance_monitor) pero frontend está **embedded como sub-routes admin** (`/admin/compliance/monitor` + `/admin/compliance/norma-reports`) · NO portal separado tipo ENS Radar `/(radar)/`.

**Gap específico**: NO existe `/(compliance)/compliance/` layout standalone pattern · está nested bajo `/(admin)/admin/compliance/`. Decisión arquitectural: ¿promote a portal separado para self-monitoring FULKRO (admin auto-supervisión) OR mantener como tab admin?

**ETA empírico realista refined**: 
- **Opción A (scope-out)**: 0h · mantener nested admin tab · cubre 100% needs cliente piloto MEDIA (admin solo · NO cliente visibility self-monitoring FULKRO)
- **Opción B (portal separado completo)**: ~4-8h refactor routing + layout + nav

---

## Stats baseline

### Backend m_compliance (~2706 LOC · cliente-facing compliance per project)
- `compliance_admin_api.py` 317 LOC · admin endpoints
- `rgpd_services.py` 625 LOC · RGPD logic
- `dpa_template.py` 540 LOC · DPA generation
- `cookies_api.py` 404 LOC · cookies banner mgmt
- `breach_service.py` 218 LOC · breach notification
- `ropa_service.py` 199 LOC · ROPA registro
- `dpa_api.py` 124 LOC
- `rgpd_api.py` 120 LOC
- `ropa_api.py` 131 LOC

### Backend m_compliance_monitor (~3084 LOC · FULKRO self-monitoring)
- `checks.py` 1057 LOC · 17 checks definidos (CHECK_REGISTRY)
- `service.py` 475 LOC · monitor service core
- `public_api.py` 325 LOC · public endpoints
- `norma_reports_service.py` 278 LOC · normative reports
- `api.py` 230 LOC · admin endpoints
- `reports_service.py` 210 LOC · reports
- `norma_reports_api.py` 195 LOC
- Tasks · Celery jobs scheduling
- 75 tests verified existing per memoria

### Frontend `/admin/compliance/`
- `monitor/page.tsx` 494 LOC · dashboard self-monitoring (status cards + 17 checks table + alerts table + reports list · polling 60s)
- `norma-reports/page.tsx` 237 LOC · reports listing + download
- **Total: 731 LOC**
- Nested bajo `/(admin)/admin/compliance/` · NO standalone layout

---

## Gap pattern comparison · ENS Radar vs Compliance

| Aspect | ENS Radar (separado) | Compliance (nested admin) |
|--------|----------------------|---------------------------|
| Layout | `(radar)/layout.tsx` standalone | `(admin)/admin/layout.tsx` shared |
| Route | `/radar/...` top-level | `/admin/compliance/...` nested |
| Auth | `require_ens_radar_owner` (specific) | Standard admin auth |
| UX | Different brand · dedicado | Embedded admin context |
| Sidebar | Own minimal nav | Admin sidebar shared |
| Use case | Marcos comercial · pre-sales | Marcos ops · self-supervision FULKRO platform |

---

## Decisión arquitectural

### Razones para PROMOTE portal separado (Opción B)
- Self-monitoring FULKRO es **operational concern distinct** del cliente work
- Admin sidebar nav puede saturar con cliente-tabs + self-monitoring tabs
- Branding distinct (Marcos vs Marcos@FULKRO ops mode)
- Future-multi-tenant: si hay otros consultores futuros · separation cleaner

### Razones para MAINTAIN nested (Opción A)
- Cliente piloto MEDIA NO accede compliance/monitor (admin-only)
- Marcos single-user actualmente · sidebar 14→10 entries refactor 1.D.F.bis.III tolera 2 más
- Refactor routing + layout + nav links = 4-8h scope creep PRE-PILOTO
- Workaround: añadir destacar visual en sidebar admin distinguir self vs cliente

---

## Recomendación

**Opción A · MAINTAIN nested admin pre-piloto · PROMOTE post-piloto Future-1.E.compliance-portal-separated**.

**Justification**:
- 0 bloqueador cliente piloto MEDIA (admin-only monitoring NO cliente visible)
- ETA economy ~4-8h vs higher-priority items (cloud remediation #9 · backups #7 · BIA #pre-FASE-I)
- Refactor routing + layout es churn pre-piloto (riesgo regresiones cross-componentes)
- Post-piloto promotion natural cuando Marcos confirma frecuencia uso compliance/monitor

**Future-1.E.compliance-portal-separated** capturado:
- ETA empírico ~4-8h
- Scope: refactor `/admin/compliance/*` → `/(compliance-ops)/compliance-ops/*` con layout dedicado · brand distinct · own sidebar minimal nav · nav entry "Compliance Ops" en root admin

---

## Cross-ref

- M_compliance source: `backend/app/motors/m_compliance/`
- M_compliance_monitor source: `backend/app/motors/m_compliance_monitor/`
- Frontend nested: `frontend/app/(admin)/admin/compliance/`
- Pattern reference portal separado: `frontend/app/(radar)/radar/` (ENS Radar)
- CHECK_REGISTRY 17 checks (per memoria · audit checks.py 1057 LOC confirms massive)

---

## Honest notes

1. NO inspección detallada CHECK_REGISTRY 17 checks (audit demand-driven post-decisión)
2. NO inspección routing dependencies si refactor (Layout shared, breadcrumb, navigation imports)
3. Marcos podría preferir Opción B por estética/clarity · NO blocking decision
