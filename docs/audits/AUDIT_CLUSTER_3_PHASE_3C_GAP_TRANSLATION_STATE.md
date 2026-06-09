# AUDIT CLUSTER 3 Phase 3C · Gap Translation Layer Empirical State

**Sesión**: 3B-2B.8 CLUSTER 3 Phase 3C
**Fecha**: 2026-05-26
**Ejecutor**: Phase 3C.0 OPS-052 micro-audit mandatory
**Status**: ✅ **Audit complete · scope refined canonical translation service · NO STOP HARD**

---

## Resumen ejecutivo

Briefing Phase 3C asumió necesidad de full ENS gap translation layer + cliente actions (assign IT · confirm correction · request help). Empirical reality:

- ✅ **`ens_measures` table existe** con campos: codigo + nombre + descripcion + familia + requisito_base + fuente_oficial + categoria_minima · rica
- ✅ **`cloud_gaps` table tiene `explanation_es`** (LLM enriched cliente-friendly R29/R30) + `suggested_action` (deterministic) + `cliente_can_see` flag + `title`
- ✅ **Cloud remediation workflow state machine** completa (Sesión 3B-2B.4): detected → proposed_to_cliente → approved | rejected → executing → executed | failed + cliente_approval_at tracking
- ✅ **m_compliance_monitor + m_compliance** existing infraestructura compliance cross-norma
- ❌ **NO canonical `translate_measure_to_cliente_friendly()` function** reusable cross-motors (DdA + Evidence + Controls + Cloud gaps · cada uno reinventa)
- ❌ **NO admin/cliente endpoint dual GET technical detail vs friendly version** desde measure_code (consumer drives)
- ❌ **Cliente actions assign-it/confirm-correction/request-help** son scope greenfield (NEW infrastructure · 1 table + 3 endpoints)

**Refined empirical scope**: la translation layer canonical EXISTS via cloud_gaps.explanation_es per-row (LLM enriched) pero NO está formalizada como canonical function consultable per measure_code aggregate. Phase 3C aporta canonical function deterministic con curated overrides + cliente-friendly mapping reusable cross-motors.

**Cliente actions (assign IT/confirm/help)** scope-out Phase 3C → defer to Future-1.E (demand-driven post-piloto) o CLUSTER 6 chronological backbone (cliente UI per phase tasks curated R29).

ETA refined: ~2-3h backend MVP vs briefing 3-6h (-30% to -40% OPS-045 59ª manifestation · audit-first reveals: ens_measures + cloud_gaps explanation_es ya rica · solo canonical function aggregate + 2 endpoints faltaban).

---

## Phase 3C.0.1 · Existing translation infrastructure map

### ens_measures (m_ens core)
```python
class EnsMeasure(FullMixin, Base):
    codigo: Mapped[str]            # 'op.acc.6'
    nombre: Mapped[str]            # 'Autenticación · MFA'
    marco: Mapped[str]
    familia: Mapped[str | None]    # 'op.acc'
    descripcion: Mapped[str | None]
    requisito_base: Mapped[str | None]
    fuente_oficial: Mapped[str | None]
    categoria_minima: Mapped[str | None]  # BASICA/MEDIA/ALTA
    aplica_basica/media/alta: bool
    dimensiones_aplicables: JSONB
```

### cloud_gaps (m_cloud_connectors)
```python
title: str              # "Usuarios admin sin MFA"
explanation_es: str | None  # LLM-enriched primer-principios R29/R30
suggested_action: str       # deterministic action recommend
cliente_can_see: bool       # filter cliente visibility
ens_measure_code: str       # 'op.acc.6'
```

### Existing cliente actions empirical (NO scope Phase 3C MVP)
- Cloud remediation workflow: cliente_approval_at + cliente_approval_user_id (approve/reject existing Sesión 3B-2B.4 Bloque 3+5)
- Evidence request workflow: Phase 3A NEW (cliente upload + mark-na)
- DdA review Pattern A: client_review_status pendiente_revision/revisada_ok/con_pregunta/suggest_change

**Existing cliente actions adequate**. Phase 3C focuses TRANSLATION LAYER canonical · NO new cliente actions.

---

## Phase 3C.0.2 · Translation function design

### Pure functional translation service · m_compliance/measure_translation_service.py

```python
@dataclass(frozen=True)
class MeasureTranslation:
    measure_code: str
    nombre: str                 # Admin name (ej "Autenticación · MFA")
    cliente_friendly_title: str  # R29 Spanish ("Inicio de sesión seguro")
    cliente_friendly_explanation: str  # primer-principios cliente
    admin_technical_detail: str  # Marcos technical detail
    familia: str | None
    categoria_minima: str | None
    fuente_oficial: str | None

async def translate_measure_to_cliente_friendly(
    db: AsyncSession,
    measure_code: str,
) -> Optional[MeasureTranslation]:
    """Canonical translation function · pure functional R1 deterministic.

    1. Lookup ens_measures por codigo
    2. Augment con curated cliente-friendly mapping (TRANSLATION_OVERRIDES)
    3. Fallback: derive cliente-friendly desde ens_measures.descripcion
    4. Returns MeasureTranslation o None si codigo not found

    Filosofía:
    - admin sees technical (ENS codigo · familia · fuente_oficial)
    - cliente sees friendly title + explanation (NO ENS lingo · TooltipENS sugerido)
    - Same source data (ens_measures) · UX dual per audience
    """
```

### TRANSLATION_OVERRIDES curated (initial seed · expand demand-driven)

Common high-frequency measures con cliente-friendly mapping curated Marcos:
- `op.acc.6` (Autenticación · MFA) → "Inicio de sesión seguro (MFA)" + "Tus usuarios admin necesitan un segundo paso al iniciar sesión..."
- `op.acc.5` (Mecanismo de autenticación) → "Cuentas y contraseñas seguras"
- `mp.s.4` (Antivirus · malware) → "Antivirus en equipos y servidores"
- `org.4` (Política de seguridad) → "Reglas internas de seguridad"
- etc (curated initial seed · ~10-20 high-frequency measures)

Fallback para non-curated: ens_measures.nombre + descripcion mostrar al cliente con caveat "Esta medida del marco ENS aplica a tu proyecto."

---

## Phase 3C.0.3 · Endpoints proposed

### Admin endpoint (require_owner)
- `GET /admin/measures/{measure_code}/translation` → MeasureTranslation full (admin_technical_detail + cliente_friendly)

### Cliente endpoint (require_client_user · R29)
- `GET /client-portal/measures/{measure_code}/explain` → cliente-friendly only (NO admin_technical_detail) + TooltipENS hints

---

## Phase 3C.0.4 · audit_log accion canonical

- `cliente.measure.translation.viewed` (cliente views measure friendly explanation)
- Sub-atom 5.A 3-way OR

---

## Phase 3C.0.5 · Recommended Phase 3C refined scope (~2-3h)

### Phase 3C.1 implementation (~1.5-2h)

**Step 1 · Service module + curated overrides** (~45-60 min)
- `backend/app/motors/m_compliance/measure_translation_service.py` NEW
- MeasureTranslation dataclass + translate_measure_to_cliente_friendly()
- TRANSLATION_OVERRIDES dict initial seed (10-15 common measures)
- Pure functional R1 · NO LLM · NO HTTP · NO side-effects · deterministic
- Fallback safe defaults (ens_measures.nombre + caveat)

**Step 2 · Admin API + audit_log** (~30-45 min)
- `backend/app/motors/m_compliance/measure_translation_api.py` 2 routers
- 2 endpoints (admin GET full · cliente GET friendly only)
- audit_log Sub-atom 5.A 3-way OR per cliente endpoint

**Step 3 · Router wiring** (~5-10 min)
- `backend/app/main.py` include 2 routers

### Phase 3C.2 tests (~30-45 min)

**Backend tests (8-10 tests)**:
- translate_measure_to_cliente_friendly returns curated override cuando measure_code en TRANSLATION_OVERRIDES
- translate_measure_to_cliente_friendly fallback desde ens_measures cuando NO override
- Returns None cuando measure_code no existe en ens_measures
- Curated overrides 100% cliente-friendly Spanish (NO admin lingo · NO ENS codigo plain)
- Admin endpoint returns full MeasureTranslation
- Cliente endpoint returns cliente-friendly only (NO admin_technical_detail)
- audit_log Sub-atom 5.A 3-way OR cliente.measure.translation.viewed
- Filosofía cliente-mínimo enforcement (cliente endpoint NO leak admin technical)

### Phase 3C.3 cliente actions scope-out

Cliente actions (assign IT · confirm correction · request help) DEFERRED Future-X:

**Future-1.E.gap-assign-it-owner-cliente** (~3-4h post-piloto demand-driven):
- Cliente designa responsable IT per gap (name + email · NO crea cuenta · solo informativo)
- Admin VE cliente assignment trazabilidad

**Future-1.E.gap-confirm-correction-cliente** (~2-3h post-piloto):
- Cliente confirma IT corrigió gap · admin valida via cloud connector re-scan

**Future-1.E.gap-request-help-cliente** (~2-3h post-piloto):
- Cliente pide ayuda cuando NO sabe qué hacer · admin recibe ClientNotification + chat thread

CLUSTER 6 backbone integrará estas cliente actions via per-phase task curation R29 (architecturally coherent).

---

## ETA refined Phase 3C

- **Briefing nominal**: ~3-6h
- **Empirical refined**: ~2-3h backend (service canonical + 2 endpoints + 8-10 tests)
- **OPS-045 59ª manifestation**: -33% to -50% vs nominal (audit-first reveals ens_measures + cloud_gaps explanation_es ya rica · solo aggregate function canonical reusable cross-motors)

---

## Filosofía cliente-mínimo compliance

100% aligned:
- Cliente VE friendly Spanish title + explanation (R29 firmísimo)
- Admin VE technical detail (ENS codigo · fuente_oficial · familia)
- Same source data ens_measures · UX dual function audience
- cliente.measure.translation.viewed audit_log trace · ENAC trazabilidad
- NO admin lingo cliente leak

---

## STOP HARD trigger evaluation

**NO STOP HARD necesario**. Briefing intent (translation layer ENS measure → cliente-friendly) ratified · refined a canonical function + 2 endpoints scope.

Cliente actions (assign-IT/confirm/help) DEFERRED Future-X · CLUSTER 6 backbone destination architecturally coherent.

---

## Patterns potencialmente formalizables Phase 3C

- **Canonical translation function + curated overrides + fallback safe** (R1 deterministic · TRANSLATION_OVERRIDES dict expandable demand-driven · graceful fallback ens_measures)
- **Same source data + dual UX per audience** (admin technical · cliente friendly · NO duplicate data · single function returns both)

---

## Decisión pendiente

⏸️ **Architect approve Phase 3C.1 refined scope**:
- Canonical translation service + 2 endpoints (1 admin + 1 cliente)
- Cliente actions DEFERRED Future-X CLUSTER 6 backbone
- 8-10 tests translation + audit_log
- ETA refined ~2-3h
