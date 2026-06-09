# AUDIT CLUSTER 3 Phase 3B · Document Approval False-Green Prevention Empirical State

**Sesión**: 3B-2B.8 CLUSTER 3 Phase 3B
**Fecha**: 2026-05-26
**Ejecutor**: Phase 3B.0 OPS-052 micro-audit mandatory
**Status**: ✅ **Audit complete · scope refined compute_control_status canonical · NO STOP HARD**

---

## Resumen ejecutivo

Briefing Phase 3B asumió necesidad de full document approval workflow + anti-false-green logic. Empirical reality:

- ✅ **Document model** (`documents.py:17`) ya tiene `estado` + `approved_by_user_id` + `approved_at` + `client_review_status` (vía ClientReviewMixinA enum: pendiente_revision · revisada_ok · con_pregunta · suggest_change) + `client_signing_intent_id` + `signature_ed25519`
- ✅ **DocumentVersion** ya tiene `firmado_por` + `firmado_at` + `firma_data`
- ✅ **M05 Signing infrastructure complete**: SigningIntent + SigningEvent + SigningOtpCode models + signing_service.py (Ed25519 + OTP step-up + hash chain inviolable)
- ✅ **policy_signoff_service Q1.C híbrida** bulk firma única workflow (m06/policy_signoff_service.py · 437 LOC)
- ✅ **ClientReviewMixinA** pattern usado por DdaEntry · MageritAsset · MageritThreatAssessment · Document
- ✅ **m04_gap dashboard semaforo logic** existing (service.py:572-597) calcula verde/amarillo/rojo
- ❌ **m04_gap semaforo computa SOLO sobre severity + gap_magnitude** · NO consulta document approval/signing state
- ❌ **FALSE-GREEN RISK CONFIRMED**: control puede aparecer "verde" en dashboard aun cuando:
  · Documento aplicable NO aprobado (estado != 'approved')
  · Versión específica NO firmada (no signing_intent linked)
  · audit_log entries incomplete para esa control state
- ❌ **NO canonical compute_control_status() function** existing · no centralized "is this control truly green" guard

**Conclusion**: Approval/signing infrastructure RICA · NO consulted por compute control state · false-green risk CONFIRMED empirical.

**Briefing intent refined**: NEW canonical `compute_control_status()` deterministic function que enforce ALL pre-requisites (documento APROBADO + versión FIRMADA + audit_log completas) ANTES marcar verde. Refactor m04_gap dashboard semaforo a CONSULT esta function.

ETA refined: ~3-4h vs briefing 5-7h (-30% to -40% OPS-045 58ª manifestation · audit-first reveals: approval + signing + reviewMixin infrastructure already wired · solo compute_control_status canonical + refactor semaforo + cliente endpoint friendly).

---

## Phase 3B.0.1 · Existing approval/signing infrastructure map

### Document approval fields (documents.py:17)
```python
class Document(ClientReviewMixinA, FullMixin, Base):
    estado: Mapped[str | None] = mapped_column(String(50))
    # IDMS workflow: draft | review | approved | archived | deprecated
    aprobado_por: Mapped[str | None] = mapped_column(String(255))
    fecha_aprobacion: Mapped[date | None]
    approved_by_user_id: Mapped[uuid.UUID | None]
    approved_at: Mapped[datetime | None]
    expires_at: Mapped[datetime | None]
    signature_ed25519: Mapped[str | None]
    client_signing_intent_id: Mapped[uuid.UUID | None]
    # + ClientReviewMixinA: client_review_status · client_reviewed_at · client_reviewed_by_user_id
```

### M05 Signing models
- **SigningIntent**: project_id + signable_type/signable_ref_id + document_id + document_hash_sha256 + status (pending | signed | expired) + requires_step_up_otp + expires_at + created_by_user_id
- **SigningEvent**: project_id + signing_intent_id + event_type + actor_user_id + actor_type + event_payload + signature_ed25519 + previous_signature_hash + event_hash_sha256 (hash chain inviolable)
- **SigningOtpCode**: OTP step-up para cliente firma

### m04_gap dashboard semaforo (service.py:572-597)
```python
# CURRENT LOGIC · severity + gap_magnitude SOLO
sev_num = SEVERITY_SCORING_STR.get(sev, 1)
gap_mag = LEVEL_ORDER.get(md.get("estado_objetivo", "L2"), 2) - ...
score = sev_num * max(gap_mag, 1)

if score >= 15 or sev == "critica":
    semaforo = "rojo"
elif score >= 6 or sev in ("alta", "media"):
    semaforo = "amarillo"
else:
    semaforo = "verde"  # ← FALSE-GREEN RISK aquí
```

**Gap CRITICAL**: Verde marcado SIN consultar:
- ¿Hay documents aplicables al control?
- ¿Esos documents están approved?
- ¿Cliente revisó (client_review_status='revisada_ok')?
- ¿Versión firmada (signing_intent_id NOT NULL · status='signed')?
- ¿audit_log entries trazables (Sub-atom 5.A propagated)?

---

## Phase 3B.0.2 · compute_control_status canonical function design

### NEW Pure functional service · m04_gap/control_status_service.py

```python
@dataclass(frozen=True)
class ControlStatusResult:
    control_id: uuid.UUID
    measure_code: str | None
    semaforo: Literal["verde", "amarillo", "rojo", "no_aplica"]
    documents_count: int
    documents_approved_count: int
    documents_signed_count: int
    cliente_reviewed_count: int
    missing_reasons: list[str]  # UX explicit: por qué NO verde
    requirements_met: dict[str, bool]  # explicit pre-reqs check

async def compute_control_status(
    db: AsyncSession,
    *,
    project_id: uuid.UUID,
    control_id: uuid.UUID | None = None,
    measure_code: str | None = None,
) -> ControlStatusResult:
    """Canonical deterministic compute · false-green prevention.

    Returns 'verde' SOLO si TODOS pre-requisitos cumplen:
    1. ≥1 documento aplicable existe (vía control_id OR measure_code)
    2. TODOS documents aplicables tienen estado='approved'
    3. TODOS documents aplicables tienen client_review_status='revisada_ok'
       (excepto documents NULL · niveles 3-4 CCN-STIC 805 NO requiere cliente)
    4. TODOS documents que requieren firma cliente (niveles 1-2) tienen
       signing_intent_id linked y signing_intent.status='signed'
    5. NO documents expired (expires_at > NOW())

    Si CUALQUIER falla → semaforo='amarillo' (con missing_reasons explicit)
    o 'rojo' (si severity crítica).
    """
```

### Pre-requisitos canonical · CHECK list deterministic

| Pre-requisito | Source | Check |
|--------------|--------|-------|
| Documento existe | documents WHERE control_id OR measure_code matches | count > 0 |
| Estado approved | documents.estado | == 'approved' AND approved_at IS NOT NULL |
| Cliente revisó (niveles 1-2) | documents.client_review_status | == 'revisada_ok' |
| Versión firmada (si requiere firma) | signing_intents.status WHERE document_id matches | == 'signed' |
| NO expired | documents.expires_at | IS NULL OR > NOW() |

**Filosofía**: pre-req faltante → NO verde · explicit missing_reason cliente-friendly.

---

## Phase 3B.0.3 · Endpoints proposed

### Admin endpoint (require_owner)
- `GET /admin/projects/{project_id}/controls/{control_id}/status` → ControlStatusResult full detail
- `GET /admin/projects/{project_id}/controls/status-summary` → list of all controls + semaforo + missing_reasons (replaces dashboard semaforo logic)

### Cliente endpoint (require_client_user · R29 friendly)
- `GET /client-portal/controls/{control_id}/status` → cliente-friendly version:
  - "Esta medida está al 80% · falta firmar el documento de política de accesos"
  - NO admin lingo · TooltipENS para acrónimos · "Sin prisa por tu parte"

### Refactor m04_gap dashboard
- Replace severity-only semaforo logic con consult `compute_control_status()`
- Backward-compat: legacy semaforo solo dashboard summary · NEW canonical = source of truth

---

## Phase 3B.0.4 · audit_log accion canonical

- `cliente.control.status.viewed` · cliente views control state
- `admin.control.status.recomputed` · admin recalculates status (manual trigger optional)

Sub-atom 5.A 3-way OR (project_id + client_id propagated).

---

## Phase 3B.0.5 · Recommended Phase 3B refined scope (~3-4h)

### Phase 3B.1 implementation (~2-2.5h)

**Step 1 · Service module** (~45-60 min)
- `backend/app/motors/m04_gap/control_status_service.py` NEW
- ControlStatusResult dataclass + compute_control_status() async function
- Pure functional · NO LLM · NO HTTP · NO side-effects · deterministic (R1 sostained)
- Empirical: query documents + signing_intents + ClientReviewMixinA · aggregate

**Step 2 · Admin API + audit_log** (~30-45 min)
- `backend/app/motors/m04_gap/control_status_admin_api.py` 2 endpoints
- audit_log emit per endpoint Sub-atom 5.A

**Step 3 · Cliente API + audit_log R29** (~30-45 min)
- `backend/app/motors/m04_gap/control_status_cliente_api.py` 1 endpoint (cliente-friendly)
- ADR-013 require_client_user
- R29 friendly: missing_reasons traducidos cliente Spanish + TooltipENS

**Step 4 · Router wiring** (~5-10 min)
- `backend/app/main.py` include both routers

### Phase 3B.2 tests (~45-60 min)

**Backend tests (10-12 tests)**:
- compute_control_status returns verde cuando ALL pre-reqs met
- compute_control_status returns amarillo cuando documento NOT approved (missing_reason explicit)
- compute_control_status returns amarillo cuando client_review_status != 'revisada_ok'
- compute_control_status returns amarillo cuando signing_intent NOT signed
- compute_control_status returns amarillo cuando documento expired (expires_at < NOW)
- compute_control_status returns 'no_aplica' cuando NO documents existen
- compute_control_status admin endpoint returns full ControlStatusResult
- compute_control_status cliente endpoint returns R29 friendly version
- Anti-false-green guard: cuando semaforo COULD be verde basado en severity SOLO,
  compute_control_status returns amarillo si pre-reqs missing (regression test
  explicit false-green prevention)
- audit_log entries persistidos Sub-atom 5.A 3-way OR

### Phase 3B.3 Refactor m04_gap dashboard (DEFERRED Future-X)

Refactor dashboard semaforo a consult compute_control_status · architecturally
coherent BUT scope-intensive (impacts existing endpoint contract + tests).

**Future-1.E.gap-dashboard-control-status-integration** (~2-3h post-piloto demand-driven):
- m04_gap dashboard semaforo backward-compat preserved
- NEW canonical path via compute_control_status function · OPTIONAL aggregation
- Refactor consumer dashboards to consult control-status-summary endpoint NEW

---

## ETA refined Phase 3B

- **Briefing nominal**: ~5-7h
- **Empirical refined**: ~3-4h backend (pure functional service + 3 endpoints + tests)
- **OPS-045 58ª manifestation**: -30% to -40% vs nominal (audit-first reveals approval/signing/reviewMixin rica · solo aggregate logic + endpoints needed)

---

## Filosofía cliente-mínimo compliance

100% aligned:
- Cliente VE control state friendly (NO admin orchestration detail)
- Cliente VE missing_reasons amigables (qué falta · NO ENS técnico)
- Cliente NO opera document approval directamente (admin OWNS workflow)
- audit_log trace · ENAC trazabilidad cumulative

**ZERO admin operations leaked cliente** · 100% pre-requisite enforcement pattern.

---

## STOP HARD trigger evaluation

**NO STOP HARD necesario**. Briefing intent (document approval false-green prevention) ratified · refined a compute_control_status canonical + 3 endpoints scope. Approval/signing infrastructure already rica empirical · solo aggregate logic + cliente-friendly translation faltaba.

---

## Patterns potencialmente formalizables Phase 3B

- **Pure functional control status compute** (deterministic R1 · pre-req CHECK list explicit · missing_reasons UX guard)
- **Anti-false-green guard pattern** (severity NOT enough · all pre-requisites enforced before verde)
- **Cliente-friendly missing_reasons translation** (admin sees technical detail · cliente sees friendly Spanish R29 · same source data)

---

## Decisión pendiente

⏸️ **Architect approve Phase 3B.1 refined scope**:
- Pure functional service compute_control_status + 3 endpoints (2 admin + 1 cliente)
- Refactor m04_gap dashboard DEFERRED Future-X (architectural concern · post-piloto)
- 10-12 tests false-green prevention scenarios
- ETA refined ~3-4h
- Filosofía cliente-mínimo 100% aligned
