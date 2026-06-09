# AUDIT #9 · Cloud remediation propuesta (NEW)

**Status**: ✅ Audit empírico completo · Bloque 1 Mega-baseline item 8/11 · **CRÍTICO**
**Date**: 2026-05-24
**Scope item**: pre-piloto #9 (NEW) · "Cloud remediation propuesta · admin propone · cliente aprueba · admin/cliente ejecuta"

---

## Verdict empírico

Infrastructure remediation existing es **SIGNIFICANT pero PARCIAL**:
- ✅ **m_cloud_connectors** (~4903 LOC) production-grade · `DiagnosticGapEngine` deterministic R1 · `CloudGap` model + JSONB `raw_evidence` (ADR-031 ENAC-ready) · gap_rules.py 449 LOC + integrations.py 960 LOC + service.py 554 LOC
- ✅ **m08_verification/remediation** (~838 LOC) · `guide_generator.py` 363 LOC (Haiku) + `retest_runner.py` 347 LOC (quirurgico) + `sla_calculator.py` 100 LOC
- ✅ **15 MCP servers pentest** existing (apisec · cloud · config · cracking · infra · mobile · phishing · recon · redteam · sast · scope_enforcer · shared · vulnscan · webpentest · wireless)
- 🟡 **Approval workflow generic** EXISTE (cliente firma + magic link) pero NO específico para remediations
- 🔴 **Cliente portal page "Remediaciones"** MISSING · NO `/client-portal/remediaciones`
- 🔴 **End-to-end flow** (admin propone → cliente aprueba → ejecuta) NOT wired explícito

**ETA empírico realista refined**:
- **Backend wire-up flow**: ~3-5h (orchestrator service que conecta DiagnosticGapEngine + guide_generator + approval workflow + retest_runner)
- **Frontend cliente UI**: ~3-5h (page + components + audit trail)
- **Total**: ~6-10h (scope-reduce vs ~10-15h nominal pure greenfield)

---

## Stats baseline

### m_cloud_connectors (~4903 LOC production-grade)
- `api.py` 855 LOC · admin endpoints REST
- `integrations.py` 960 LOC · cross-motor wires (M03/M04/M07 K-light)
- `service.py` 554 LOC · core service
- `gap_rules.py` 449 LOC · 8 reglas pure-function detectors (op.acc.6 MFA · op.exp.1 inventario · etc)
- `digest_service.py` 416 LOC · monthly snapshot (1.D.X.VERIFY 2a)
- `models.py` 397 LOC · CloudConnector + CloudResource + CloudGap + CloudSyncJob + CloudDigestSnapshot
- `diagnostic_gap_engine.py` 291 LOC · deterministic R1 DiagnosisReport
- `api_cliente.py` 267 LOC · cliente endpoints
- `schemas.py` 248 LOC · Pydantic
- `tasks.py` 246 LOC · Celery
- `base_connector.py` 129 LOC · BaseConnector abstraction
- 5 OAuth providers existing (M16): M365 · Google · Azure · AWS · GitHub + MANUAL_IMPORT fallback

### m08_verification/remediation (~838 LOC)
- `guide_generator.py` 363 LOC · Haiku LLM generation guías en español (PYME-friendly)
  - JSON schema: resumen_no_tecnico + riesgo_real + pasos[] (titulo · comando · explicacion · verificacion) + tiempo_estimado + requiere_reinicio
  - Fallback deterministic templates (TLS · CVE · web · hardening · AD)
- `retest_runner.py` 347 LOC · retest QUIRURGICO post-"ya lo arreglé"
  - Types: ssl (testssl) · cve (nuclei) · web (zap) · hardening (lynis) · port (nmap)
  - Outputs: fixed | still_present | error | inconclusive
- `sla_calculator.py` 100 LOC · SLA enforcement
- ORM `RemediationRetest` + `VerificationFinding` existing

### MCP servers 15 directories (per Audit #11 needed)
- apisec · cloud · config · cracking · infra · mobile · phishing · recon · redteam · sast · scope_enforcer · shared · vulnscan · webpentest · wireless
- Per memoria: 3 reales validados (Prowler + ScoutSuite + OpenVAS · 88 mappings) + 11 estructurales

---

## End-to-end flow gap analysis

### Step 1 · Admin detecta gap cloud (DONE)
- `DiagnosticGapEngine.run_diagnosis()` ejecutado per project
- Persists `CloudGap` rows con severity + raw_evidence
- Auto-trigger on sync completion + categoría change + manual POST

### Step 2 · Admin genera guía remediation (DONE backend · WIRE missing)
- `guide_generator.py` produce JSON estructurado
- Reads `CloudGap` + Haiku LLM
- Wire missing: cross-motor connection `CloudGap` → `guide_generator` automated

### Step 3 · Admin propone al cliente (PARTIAL)
- Approval workflow generic existe (firma Ed25519 magic link)
- Specific cloud remediation proposal flow NOT wired
- Notification cliente (m18 alerts existing · template missing `cloud_remediation_proposed.yaml`)

### Step 4 · Cliente aprueba (MISSING)
- Cliente portal `/client-portal/remediaciones/` page NOT existing
- Approval flow per-remediation NOT wired
- 1-click approve/reject + firma Ed25519 si critical

### Step 5 · Ejecuta remediation (PARTIAL)
- Manual: cliente ejecuta pasos (guía en español PYME)
- Admin ejecuta if delegated
- Retest: `retest_runner.py` retest quirurgico post-"ya arregló"
- Wire missing: trigger retest auto post-cliente-marks-done

### Step 6 · Verifica fix (DONE backend · WIRE missing)
- `retest_runner` retorna fixed/still_present/error/inconclusive
- Wire missing: cliente notification post-verify + close CloudGap

---

## Recomendación

**Pre-piloto MEDIA scope: ~6-10h cumulative empírico** (vs ~10-15h nominal greenfield):

### Backend wire-up (~3-5h)
1. NEW orchestrator service `cloud_remediation_orchestrator.py` (~150 LOC):
   - Cross-motor wire: `CloudGap` → `guide_generator` → `proposal` → `client_approval` → `retest_runner` → `close_gap`
   - State machine: detected → proposal_generated → proposed_to_client → approved → executing → verified → resolved
2. NEW notification template `cloud_remediation_proposed.yaml` (~30 LOC)
3. NEW endpoint cliente `POST /client-portal/remediations/{id}/approve|reject` (~80 LOC)
4. WIRE admin proposal endpoint con magic link FIRMA_DOCUMENTO purpose extend

### Frontend cliente (~3-5h)
5. NEW page `/client-portal/remediaciones/page.tsx` (~150 LOC)
6. NEW component `RemediationProposalCard` (~180 LOC):
   - Resumen no técnico R29 friendly
   - Riesgo real
   - Pasos guía expandable
   - Approve/reject buttons + firma trigger si critical
   - Status pill (proposed · approved · executing · verified)
7. NEW component `RemediationsList` (~120 LOC) feed activo
8. WIRE sidebar entry (probable scope-reduce per Audit #4 sidebar 14→10 cement OR sub-route /files)

---

## Cross-ref

- m_cloud_connectors source: `backend/app/motors/m_cloud_connectors/`
- m08 remediation: `backend/app/motors/m08_verification/remediation/`
- DiagnosticGapEngine: `backend/app/motors/m_cloud_connectors/diagnostic_gap_engine.py`
- guide_generator Haiku: `backend/app/motors/m08_verification/remediation/guide_generator.py`
- Audit #4 cliente portal gap reference
- Audit #10 admin↔cliente sync (next · directamente dep aquí)
- Audit #11 MCPs 16 servers verification (next · context)
- ADR-031 ENAC-ready trazabilidad CloudGap raw_evidence

---

## Honest notes

1. NO inspección detallada gap_rules.py 8 reglas (audit demand-driven cuando wire)
2. Magic link M12 FIRMA_DOCUMENTO purpose puede extend OR new purpose `REMEDIATION_APPROVAL`
3. Sidebar cliente 14→10 cement (1.D.F.bis.III) tolera 1 entry adicional `Remediaciones` (HIGH priority)
4. Workflow approval cliente Ed25519 magic link · NO new auth infrastructure
5. ETA realistic empírico ~6-10h **assumes** orchestrator coordinator is greenfield (existing motors NO modificar)
