# AUDIT Ejecutable 7.6 Phase 7.6.0 · Fulkro Identity Propagation State Empirical

**Fecha**: 2026-05-27
**Sesión**: Ejecutable 7.6 · Fulkro Identity & Contact Propagation cross-system insert pre-Ejecutable 8 EXPANDED
**Status**: Phase 7.6.0 audit COMPLETO · 90% greenfield · proceed Phase 7.6.1

## Empirical findings cross-system

### Identity strings empirical occurrences (Fulkro phone/email/web)

9 backend files con identity strings · NO frontend matches · 0 email templates con full identity:

| File | Status | Action |
|------|--------|--------|
| `backend/scripts/generate_propuesta_pdf.py` lines 67-72 | ✅ Hardcoded `BRAND_WEB` + `BRAND_EMAIL` + `BRAND_PHONE` + `BRAND_AUTHOR` | REFACTOR import constants module |
| `backend/tests/scripts/test_generate_propuesta_pdf.py` | ✅ Test asserts identity strings | Preserve · validates constants |
| `backend/app/motors/m10_ens_radar/outreach/draft_generator.py` | ✅ Outreach drafts mention Fulkro | REFACTOR import constants |
| `backend/app/motors/m23_retainer/agent_15_vigilancia.py` | ✅ Agent retainer mention | Audit context · likely REFACTOR |
| `backend/app/motors/m23_retainer/ccn_stic_scraper.py` | ✅ Reference scraper | Audit context |
| `backend/app/motors/m25_lifecycle/lifecycle_paso4.py` | ✅ Lifecycle mention | Audit context |
| `backend/app/motors/m25_lifecycle/backup_builder.py` + `tasks.py` | ✅ Mention | Audit context |
| `backend/scripts/download_ccn_corpus.py` | ✅ Mention | Audit context |

### Frontend identity propagation

- 0 frontend files match `637 165 328` OR `marcosmata@fulkro` OR `www.fulkro` (verified Grep)
- `frontend/lib/branding/` EXISTS but covers **CLIENT branding** (per-cliente colors/logo · NOT Fulkro consultora identity)
- 0 Footer component existing en `frontend/components/layout/` (verified ls)
- Layout structure: `app/layout.tsx` + admin/cliente/auditor sub-layouts · footer integration TBD

### Email templates m20 notifications

13 templates yaml en `backend/app/notifications/templates/`:
- `acta_signed.yaml` · `audit_due.yaml` · `chat_admin_reply.yaml` · `client_inactivity_admin.yaml` · `evidence_expiring.yaml` · `evidence_quarantined_admin.yaml` · `incident_resolved_cliente.yaml` · `milestone_billed.yaml` · `payment_received.yaml` · `phase_changed.yaml` · `retainer_quarterly_signed.yaml` · `signoff_completed.yaml` · `task_assigned.yaml`

Sample inspection `audit_due.yaml`:
```yaml
html_body_es: |
  ...
  <p>Un saludo,<br>Marcos · FULKRO</p>
```

**Gap**: NO phone/web/email/tagline en signature · only "Marcos · FULKRO".

### Copilots system prompts

`backend/app/agents/prompts/agent_14_copiloto.py` PROMPT:
- ROL: "Asistir a Marcos en cualquier pregunta sobre ENS..."
- NO Fulkro identity context (phone/web/email)
- Agent CANNOT empirically answer "¿cómo contactaros?" sin Fulkro identity primary context

`agent_31_enriquecedor_dda.py` similar pattern · no identity wiring.

### PDF generators existing

- `backend/scripts/generate_propuesta_pdf.py` · ✅ already con identity hardcoded (V3.4 final)
- `backend/app/motors/m09_audit_prep/draft_report_generator.py` · ❓ NO identity check (verify)
- `backend/app/motors/m09_audit_prep/simulacro_pre_enac_service.py` · uses `generate_draft_audit_report` (cascade · same generator)

## Propagation gap empirical summary

- **10% existing**: propuesta_pdf hardcoded V3.4 (1 file out of 4 primary outputs)
- **90% greenfield**:
  - 0 frontend constants
  - 0 frontend Footer
  - 13 email templates sin full signature
  - 2+ copilots system prompts sin identity
  - 7 backend files scattered identity references sin module

## Phase 7.6.1 scope refined

- NEW `backend/app/config/__init__.py` + `backend/app/config/fulkro_identity.py` (5 constants)
- NEW `frontend/lib/fulkro-identity.ts` (FULKRO_IDENTITY const object)
- These are PURE constants modules · NO DB · NO runtime · NO migration · zero risk

## Phase 7.6.2 propagation scope refined

Priority order per audit:
1. **NEW Frontend Footer** component `frontend/components/layout/FulkroFooter.tsx` · embedded root layouts
2. **REFACTOR propuesta_pdf** import constants (sostained existing hardcoded · DRY)
3. **UPDATE 13 email templates** add full identity signature (phone/web/email + tagline)
4. **UPDATE Frontend** existing pages footer mention donde apropiado
5. **CCN-STIC-809 sede artifacts** declaración conformidad mention Fulkro consultora

## Phase 7.6.3 copilots wiring scope refined

- ADD primary context section a `agent_14_copiloto.py` PROMPT (3-4 lines Fulkro identity)
- Cliente copilot (m21 si existing similar) · same wiring

Note: Ejecutable 8 Pasada 18-19 expandirá knowledge base copilots con SYSTEM_KNOWLEDGE_BASE.md · Phase 7.6.3 es preview wiring · architect briefing sostained.

## OPS-045 projection

- Nominal scope: ~30-45 min cumulative Phase 7.6.1-7.6.4
- Empirical projection: ~25-35 min (-15% modest dado scope clean greenfield · no scope reductions disponibles)
- 55ª aplicación cumulative · scope alignment matches nominal projection

## Doctrinas honored cumulative

- OPS-026 DRY (single source of truth backend + frontend constants modules)
- OPS-045 audit-first 55ª aplicación (-15% empirical projection scope clean)
- OPS-049 honest path (90% greenfield documented transparent · empirical findings precise)
- Fulkro "shown not sold" doctrine (cliente VE info Fulkro consultora trust building · Outcome-as-a-Service framing)
- R23 + R30 admin tutor sostained (copilots primary context · NO hallucination)
- Pattern P-CL2-4 ENRICH outputs existing (Footer embedded layouts · NO new routes)
