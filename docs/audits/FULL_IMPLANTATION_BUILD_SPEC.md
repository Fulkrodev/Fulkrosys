# FULL IMPLANTATION BUILD SPEC · ENS RD 311/2022 (BÁSICA 52 / MEDIA 68 / ALTA 73)

> Fuente única de verdad de medidas: `backend/app/motors/m03_dda/anexo2_rd311_2022.py` (verificado contra BOE‑A‑2022‑7191 el 2026‑06‑07).
> Totales invariantes: `TOTAL_MEDIDAS=73`, `APLICA_BASICA=52`, `APLICA_MEDIA=68`, `APLICA_ALTA=73`.
> La DdA siempre materializa **73 filas** (`DdaEntry`), una por medida; lo que varía es `aplicabilidad` (`aplica*` vs `no_aplica`).

Objetivo: dejar en la **DEV DB** tres triplete cliente+proyecto dedicados (uno por tier) con una implantación ENS **completa, firmada y correcta**, de modo que el **admin UI**, el **portal cliente** y el **portal auditor** rendericen datos REALES, los entregables (E‑codes) sean correctos, y `mark-audit-passed` devuelva 200 con cascada a CERTIFIED.

Claves dedicadas (de `_DEDICATED_KEYS` en `backend/app/dev/router.py:166`):

| Tier   | `key` (seed)            | CIF dedicado | Proyecto aislado |
|--------|-------------------------|--------------|------------------|
| BÁSICA | `conformidad-basica`    | `B0000011`   | proyecto BÁSICA  |
| MEDIA  | `conformidad-media`     | `B0000012`   | proyecto MEDIA   |
| ALTA   | `conformidad-alta`      | `B0000013`   | proyecto ALTA    |

> Nota de aislamiento: cada `key` mapea a su propio Client+Project (R27 LIMIT 1 resuelve por tier). Esto evita que los seeds pisen el client compartido legacy `B00000000`.

---

## 1 · Lever `seed-full-implantation`

Pseudocódigo ordenado por tier. Dos vías equivalentes:

- **Vía RÁPIDA (recomendada para E2E)**: encadenar endpoints `/_dev/*` idempotentes (cubren steps 1‑11 con un puñado de POSTs).
- **Vía SERVICIO (control fino / verificación de entregables)**: llamar a los servicios directamente.

`tier` ∈ {`BASICA`,`MEDIA`,`ALTA`}; `key` ∈ {`conformidad-basica`,`conformidad-media`,`conformidad-alta`}.
`DEV_KEY` = el secreto de `_require_non_production` (header/query según el endpoint).

### 1.A · Vía RÁPIDA (POSTs `/_dev/*`)

```text
# STEP 1+2+3  → crea client+project+system aislado, categoriza, genera DdA (73 entries),
#               preselecciona aplicabilidad por tier y deja la cadena de firma reseteada
POST /_dev/seed-dda-alta-project?key={key}          # idempotente: reusa si DdA ya >=70 filas
#   internamente: setup_test_project(db) + DdaService.generate_dda(pid, CategoriaSistema.{TIER})
#   + UPDATE dda_entries SET estado_implementacion='implantada', aprobado_por, fecha_aprobacion
#     WHERE aplicabilidad <> 'no_aplica'  (FREEZE DdA)

# STEP 4  MAGERIT (obligatorio MEDIA/ALTA; recomendado siempre porque el blocker de readiness
#         exige magerit_validation en TODOS los tiers — ver §2)
POST /_dev/seed-magerit-alta-data?key={key}         # 8+ assets, 8+ threats, 12+ assessments; snapshot_frozen_at

# STEP 5  Pentest (solo si ALTA — readiness solo bloquea ALTA; MEDIA opcional; BÁSICA skip)
if tier == 'ALTA':
    POST /_dev/seed-pentest-auth-data?key={key}     # VerificationRun + authorization_signed_at=NOW(); reset pentest signing chain

# STEP 6..11  Evidencias + políticas + cadena de firma (dda/magerit[/pentest]) +
#             BasicDeclaration draft tier-aware + route init. TODO en un POST:
POST /_dev/seed-conformidad-ready?tier={tier}&key={key}
#   - Evidence: BASICA 25 / MEDIA 50 / ALTA 73
#   - SigningEvent(signature_generated) por signable_type: dda, magerit_validation [, pentest_authorization si ALTA]
#   - Políticas firmadas (bulk policy_approval) hasta el mínimo del tier (10/18/25)
#   - BasicDeclarationRow draft: BASICA initial | MEDIA/ALTA commitment_pre_certification
#   - project.categoria_objetivo = tier
```

> Tras estos 3‑4 POSTs, `compute_readiness(db, pid).ready_for_conformity_sign == True` para el tier.

### 1.B · Vía SERVICIO (steps 1‑12 explícitos)

```python
# ── Imports canónicos ──────────────────────────────────────────────────────
from backend.app.dev.router import setup_test_project          # crea client+project+system+5 contactos
from backend.app.motors.m01_categorization.service import CategorizationService
from backend.app.motors.m03_dda.service import DdaService
from backend.app.motors.m03_dda.enums import CategoriaSistema   # BASICA|MEDIA|ALTA
from backend.app.motors.m02_magerit.service import MageritAnalysisService
from backend.app.motors.m08_verification.models import VerificationRun
from backend.app.models.documents import Evidence, Document
from backend.app.motors.m05_signing.models import SigningIntent, SigningEvent
from backend.app.motors.m27_conformity.conformity_service_paso5 import ConformityServicePaso5
from backend.app.motors.m27_conformity.readiness_service import (
    compute_readiness, _TIER_MIN_EVIDENCE, _TIER_MIN_POLICIES,
)
from backend.app.motors.m27_conformity.distintivo_persistence import (
    attach_distintivo_on_registered, attach_external_certificate,
)
from backend.app.motors.m06_document_factory.service import DocumentFactoryService
from backend.app.motors.m06_document_factory.informe_final_generator import build_informe_final_context
from backend.app.motors.m06_document_factory.rectores_generator import (
    build_rectores_context, generate_manual_sgsi_docx, generate_plan_director_docx,
)
from backend.app.motors.m06_document_factory.continuity_generator import (
    build_bia_context, build_continuity_context, build_drp_context,
)
from backend.app.motors.m19_risk.bia_service import create_bia_entry
from backend.app.models.conformity_lifecycle import ConformityRouteRow, BasicDeclarationRow

TIER = "<BASICA|MEDIA|ALTA>"
CAT  = CategoriaSistema[TIER]
RSEG = "Beatriz Seguridad López"

# Tenancy (RLS) — los seeds usan SET LOCAL ROLE fulkro_app_bypassrls (token/admin-scoped).
await db.execute(sa_text("SET LOCAL ROLE fulkro_app_bypassrls"))

# STEP 1 · CLIENTE + PROYECTO + SISTEMA (+ 1 service finalista + 1 information_type + 1 site + 5 contactos)
client_id, project_id, system_id = await setup_test_project(db)
# UPDATE projects SET categoria_objetivo=TIER, fecha_kickoff=..., fecha_objetivo_certificacion=...

# STEP 2 · CATEGORIZACIÓN (DICAT) + ACTA
dicat = await CategorizationService(db).compute_for_system(system_id)      # → BÁSICA|MEDIA|ALTA
# INSERT categorizations(system_id, categoria_resultante=TIER, aprobado_por=RSEG, fecha_acta=today)

# STEP 3 · DdA (73 entries) + APPLICABILITY + FREEZE
await DdaService(db).generate_dda(project_id, CAT, responsable=RSEG, enforce_gates=False)
#   carga 73 EnsMeasure; por medida: aplica → DdaEntry(aplicabilidad='aplica', estado='no_valorado')
#                                     no aplica → DdaEntry(aplicabilidad='no_aplica', justificación template)
#                                     ALTA → marca refuerzos (ens_measure_refuerzos / CCN-STIC 804)
# FREEZE:
# UPDATE dda_entries SET estado_implementacion='implantada', aprobado_por=RSEG, fecha_aprobacion=today
#   WHERE project_id=project_id AND aplicabilidad <> 'no_aplica'
#   → aplicables: BÁSICA 52 · MEDIA 68 · ALTA 73

# STEP 4 · MAGERIT  (MEDIA/ALTA obligatorio; recomendable en BÁSICA por el blocker de readiness)
analysis = await MageritAnalysisService(db).create(project_id, status='completed',
                                                    snapshot_frozen_at=now)
#   seed >=8 MageritAsset (asset_type_code D/S/SW/HW/L/P/COM + value_d/i/c/a/t)
#   seed >=8 MageritThreat + >=12 MageritThreatAssessment (probability + degradation_*)
#   calcular MageritRiskCalculation (intrínseco vs residual) + MageritTreatmentPlan

# STEP 5 · PENTEST (ALTA obligatorio · MEDIA opcional · BÁSICA skip)
if TIER == "ALTA":
    db.add(VerificationRun(project_id=project_id, category='ALTO',
        scope_jsonb=..., tools_config=..., scheduled_start=..., ventana_fin=...,
        ventana_timezone='Europe/Madrid', ventana_business_hours_only=True,
        contacto_ir_..., rules_of_engagement=..., responsibility_disclosure=...,
        data_handling_policy=..., authorization_signed_at=now, client_reviewed_at=None))

# STEP 6 · ENTREGABLES NUCLEARES
svc = DocumentFactoryService(db)
e040_ctx = await build_informe_final_context(db, project_id)     # raises InformeFinalEmptyError si 0 aplicables
await svc.generate_document(project_id=project_id, template_codigo='E-040',
                            context=e040_ctx, generate_pdf=False, sign=True, generated_by='sim')
rect = await build_rectores_context(db, project_id)
manual_sgsi = generate_manual_sgsi_docx(rect)        # E-160
plan_director = generate_plan_director_docx(rect)    # E-170
if TIER == "ALTA":                                   # continuidad op.cont.* (E-400/401/403)
    for svc_name, rto, rpo, impact in [("Tramitación electrónica", 4, 1, 50000), ("Sede", 24, 8, 10000)]:
        await create_bia_entry(db, project_id, svc_name, rto_hours=rto, rpo_hours=rpo, daily_impact_eur=impact)
    await svc.generate_document(project_id=project_id, template_codigo='E-400', context=await build_bia_context(db, project_id), ...)
    await svc.generate_document(project_id=project_id, template_codigo='E-401', context=await build_continuity_context(db, project_id), ...)
    await svc.generate_document(project_id=project_id, template_codigo='E-403', context=await build_drp_context(db, project_id), ...)

# STEP 7 · EVIDENCIAS (BÁSICA 25 · MEDIA 50 · ALTA 73) linkadas a medidas
min_ev = _TIER_MIN_EVIDENCE[TIER]
for i in range(min_ev):
    db.add(Evidence(project_id=project_id, measure_code=<codigo medida aplicable>,
                    tipo='document', vigente=True, scan_status='clean',
                    hash_sha256=..., fichero_nombre_original=..., fichero_mime_type=...,
                    fichero_path=<existe en disco>, deleted_at=None))
#   medidas críticas (op.acc.*, mp.s.*, mp.com.*) → 3+ evidencias cada una

# STEP 8 · POLÍTICAS + FIRMA BULK (BÁSICA 10 · MEDIA 18 · ALTA 25)
min_pol = _TIER_MIN_POLICIES[TIER]
bulk = SigningIntent(project_id=project_id, signable_type='policy_approval', status='signed', ...)
db.add(bulk); await db.flush()
for j in range(min_pol):
    db.add(Document(project_id=project_id, tipo='politica', clasificacion='evidencia',
                    template_codigo=<E-100.. según tier>, client_signing_intent_id=bulk.id))

# STEP 9 · CADENA DE FIRMA (dda → magerit_validation [→ pentest_authorization])  ── ver §2
# DELETE FROM signing_events WHERE project_id=pid; DELETE FROM signing_intents WHERE project_id=pid;
signables = ['dda', 'magerit_validation'] + (['pentest_authorization'] if TIER == 'ALTA' else [])
for st in signables:
    si = SigningIntent(project_id=project_id, signable_type=st, document_hash_sha256=..., status='signed', ...)
    db.add(si); await db.flush()
    db.add(SigningEvent(project_id=project_id, signing_intent_id=si.id,
                        event_type='signature_generated', actor_type='client_user'))

# STEP 10 · READINESS PRE-FIRMA
snapshot = await compute_readiness(db, project_id)
assert snapshot.ready_for_conformity_sign, snapshot.blockers   # iterar blockers hasta vacío

# STEP 11 · CONFORMITY ROUTE INIT + CONFORMANT
await ConformityServicePaso5().initialize_conformity_route(db, project_id, detected_overlay_hints=None)
#   BÁSICA → route_type='declaracion_basica' (sin expiración)
#   MEDIA/ALTA → route_type='certificacion_enac' (expiration_date = now + 24 meses)
# Transición a CONFORMANT (tras auditoría interna OK, sin NC abiertas):
db.add(ConformityRouteRow(project_id=project_id,
        route_type=('declaracion_basica' if TIER=='BASICA' else 'certificacion_enac'),
        status='CONFORMANT')); await db.flush()

# STEP 12 · DISTINTIVO E-049 + REGISTERED  (+ cert externo MEDIA/ALTA)
dist = await attach_distintivo_on_registered(db, project_id, generated_by='sim')
#   genera Document E-049 (clasificacion='conformidad'), build_distintivo_context, DOCX, persiste MinIO,
#   transiciona route CONFORMANT→REGISTERED (idempotente: 2ª llamada NO crea doc nuevo)
if TIER in ("MEDIA", "ALTA"):
    await attach_external_certificate(db, project_id, filename="cert_enac.pdf",
                                      content=<pdf bytes>, content_type="application/pdf")
#   FULKRO NUNCA emite el certificado: solo PERSISTE el PDF oficial de la entidad acreditada (E-049-EXT)

await db.commit()   # endpoints POST/PATCH/DELETE deben commitear explícito (get_db no auto-commitea)
```

> Resumen 12 steps: (1) client+project+system+contactos, (2) categorización DICAT+acta, (3) DdA 73 entries + freeze, (4) MAGERIT analysis+assets+threats+risks, (5) pentest auth (ALTA), (6) entregables nucleares E‑040/E‑160/E‑170 (+E‑400/401/403 ALTA), (7) evidencias 25/50/73 linkadas, (8) políticas + firma bulk 10/18/25, (9) cadena firma dda/magerit[/pentest], (10) readiness pre‑firma, (11) route init + CONFORMANT, (12) distintivo E‑049 + REGISTERED (+ cert externo MEDIA/ALTA).

---

## 2 · Gates de auditoría (`mark-audit-passed`)

Endpoint: `POST /api/v1/projects/{id}/audit/mark-passed` · `Depends(require_owner)` (admin/Marcos) · `backend/app/motors/m25_lifecycle/api_paso4.py:185`, servicio `lifecycle_paso4.py:197` (`LifecyclePaso4Service.mark_audit_passed`).

**Solo 2 gates lo hacen devolver 200/201** (verificado en código, líneas 227‑238):

1. `result ∈ {passed, observed, correction_required, failed}` (línea 227). Otro valor → `LifecyclePaso4Error` → HTTP 400.
2. `project.audit_passed_at IS NULL` (idempotencia, línea 234). Ya marcado → HTTP 400 `"Proyecto ya tiene audit result registrado..."`.

**NO hay gate sobre**: estado de la ruta de conformidad, firma/freeze de DdA, E‑808, `lifecycle_state` actual, asignación de auditor ENAC, ni recuento de evidencias. `mark_audit_passed` **trata BÁSICA/MEDIA/ALTA idénticamente** (solo mira `result` + idempotencia). La diferenciación por tier vive en M27 (ruta + readiness), no aquí.

**Constraints DB que sí aplican**:
- `projects_audit_result_check`: `audit_result IS NULL OR IN ('passed','observed','correction_required','failed')` (`audit_passed_columns_001.py:60`).
- `project_lifecycle_events.event_type` incluye `'audit_marked'` (`audit_marked_event_type_001.py`); `_log_event` valida contra `ALLOWED_EVENT_TYPES` antes del INSERT.

**Cascada (no bloqueante; los fallos solo se loggean en la respuesta)**:
- Si `result=='passed'` AND `cascade_certify=True` AND `project.certified_at IS NULL` → `mark_certified()` → `lifecycle_state='CERTIFIED'`, `certified_at=today`. Respuesta incluye `certified_event_id`. Ya certificado → `certified_skipped_reason` (no fatal).
- Si además `cascade_retainer_offer=True` AND (certify ok OR ya certificado) → `offer_retainer()` con email del último `ClientUser` (`SELECT ... FROM client_users WHERE client_id=? ORDER BY created_at DESC LIMIT 1`). Sin ClientUser → `retainer_offer_skipped_reason` (cert completa igual). Con éxito → `retainer_offer_notification_id` + `retainer_offer_url='/client-portal/retainer'`.

**Body recomendado para "auditoría pasada" (cualquier tier)**:
```json
{ "result": "passed", "audit_report_ref": "E-702-AUD-001",
  "cascade_certify": true, "cascade_retainer_offer": true }
```
- BÁSICA: igual (autodeclaración; `audit_report_ref` puede ser tu referencia interna de autoevaluación). No exige E‑808 para marcar (solo lo exige M27 para PUBLICAR la declaración básica).
- MEDIA/ALTA: `audit_report_ref` = nº de certificado/acta ENAC (formato `E-702-*`).

**Precondición de estado para `cascade_retainer_offer` real**: que exista ≥1 `ClientUser` para `project.client_id` (los seeds `/_dev/*` lo crean). Si no, el retainer se salta con gracia.

**Estado persistido tras 200**: `projects.audit_passed_at`, `audit_passed_by`, `audit_result`, `audit_report_ref`, `lifecycle_state=CERTIFIED` (si cascada), + eventos `audit_marked` (y `certified` con `triggered_by='audit_marked'`) en `project_lifecycle_events`.

> Para un re‑run E2E: usar `POST /_dev/reset-test-cycle?project_id=...` (`router.py:1707`) que limpia tablas de ciclo por proyecto, dejando `audit_passed_at` NULL otra vez.

---

## 3 · Datos que el auditor necesita (per‑view seed)

Portal auditor: 11 rutas `/(portal)/auditor-portal/[token]/*`, magic‑link `AUDITOR_PORTAL_ENAC` (M12). Token‑peek vía `SET LOCAL ROLE fulkro_app_bypassrls` (alcance acotado por `project_id` del token). Cada vista emite `audit_log` vía `emit_auditor_event()`.

Crear el token: `POST /_dev/auditor-portal-token` (MEDIA/ALTA) → `magic_links(tipo_operacion='auditor_portal_enac', project_id, recipient_email, expira_at, max_usos=1)`.

| Vista (`GET /public/auditor-portal/{token}/…`) | Tablas leídas | Seed mínimo para render REAL |
|---|---|---|
| `summary` | COUNT de `dda_entries`, `evidence`, `magerit_analysis`, `verification_runs` | ≥1 fila en cada una (NULL‑safe → 0) |
| `dda` | `dda_entries` JOIN `ens_measures` | 73 `ens_measures` precargadas + `DdaEntry` por medida con `aplicabilidad`; estado SIGNED via `dda_project_signatures` |
| `magerit` | `magerit_analysis` (último), `magerit_assets`, `magerit_threat_assessment` | `magerit_analysis` con `snapshot_frozen_at` NOT NULL + ≥1 asset (DICAT) + ≥1 assessment |
| `plan` | `project_plans` (último por `version`), `wbs_tasks` | `project_plans` (categoria, fechas, `estado='approved'`, `aprobado_at`) + ≥1 `wbs_tasks` (con `deliverable_e_code`, `is_critical_path`) |
| `evidence` | `evidence` agrupado por `measure_code` | ≥1 evidencia por medida aplicable con `measure_code`, `scan_status='clean'`, `hash_sha256`, `vigente=true` |
| `e041` | `basic_declarations` | ≥1 fila: BÁSICA `declaration_type='initial'` (+`published_evidence_url`); MEDIA/ALTA `commitment_pre_certification`; con `signed_at`+`signed_hash` (Ed25519) |
| `audit-log` | `audit_log` por `project_id` ORDER BY seq DESC | auto‑poblado por acceso al portal (`emit_auditor_event`); siempre ≥ metadata `auditor_portal.view` |
| `pentest` | `verification_runs` agregado | MEDIA/ALTA: 1 run `status='completed'`, `completed_at`, conteos severidad, `security_score`; BÁSICA: vacío con gracia |
| `documents` | `audit_preparation_runs` (últimos 5) | 1 run con `categoria`, `dossier_generated_at` NOT NULL, `estado IN ('pending','ready','completed')` + `signed_zip_endpoint` |
| `audit/dda-evidence-gaps` | `compute_dda_evidence_gaps(db, pid)` puro | mismo seed que `dda`+`evidence`; clasifica covered/partial/missing/not_applicable (min 1/medida, `scan_status='clean'`, `vigente`, no stale >365d) |
| `audit/draft-report` (POST) | sintetiza todas las vistas → PDF firmado Ed25519 | requiere que las vistas previas tengan contenido (no seed extra) |
| download `dossier.zip` | `audit_preparation_runs` + `dossier_generator.generate_dossier(..., sign_manifest=True)` | run con `dossier_generated_at` (o fuerza generación); ZIP = 10 docs canónicos |
| download `evidence/{id}/download` | `evidence` by id | `fichero_path` existe en disco, `scan_status NOT IN ('infected','quarantined')` |
| download `audit-log.csv` | stream `audit_log` por `project_id` | ≥1 fila (auto‑generada por acceso) |

> Atajo de seeding global: `seed-dda-alta-project` + `seed-magerit-alta-data` + (`seed-pentest-auth-data` ALTA) + `seed-conformidad-ready` cubren summary/dda/magerit/evidence/e041/pentest. Para `plan` y `documents` hay que asegurar `project_plans`+`wbs_tasks` y un `audit_preparation_runs` con `dossier_generated_at` (generar dossier una vez).

---

## 4 · Checklist de entregables (E‑code → generador → checks)

| E‑code | Motor / generador | Checks de corrección obligatorios |
|---|---|---|
| **E‑040** Informe Final (SoA) | M06 `informe_final_generator.build_informe_final_context()` (líneas 130‑199) | 16 familias canónicas presentes en `context['informe']['cumplimiento']` (org, op.pl, op.acc, op.exp, op.ext, op.nub, op.cont, op.mon, mp.if, mp.per, mp.eq, mp.com, mp.si, mp.sw, mp.info, mp.s) · `cumplimiento_global = implantadas/aplicables` coincide con DB · nombre cliente en texto · sin `{{`/`{%` · `Declaración de Aplicabilidad`/`Anexo II` presente · `InformeFinalEmptyError` si 0 aplicables |
| **E‑041** Declaración Conformidad | M27 `conformity_service_paso5` + template `E041_declaracion_conformidad_ens.py` | route CONFORMANT→REGISTERED · BÁSICA texto `autodeclaración`/`autoevaluación`; MEDIA/ALTA `entidad acreditada` · firma RSEG (`signature_hash`+`signature_value` NOT NULL) · fecha ISO · sin `{{` |
| **E‑160** Manual SGSI | M06 `rectores_generator.generate_manual_sgsi_docx()` | DOCX OOXML válido (zip `PK`) · `Manual del SGSI`+`Roles`+`CCN-STIC 801`/`805`+`4 niveles` · RSEG + roles_table poblados · Sponsor/Comité names |
| **E‑170** Plan Director | M06 `rectores_generator.generate_plan_director_docx()` | DOCX válido · `Plan Director`+`trianual`+`CCN-STIC 815`/KPIs · strategic_lines + capex/opex no‑placeholder |
| **E‑400** BIA | M06 `continuity_generator.build_bia_context()` (ALTA) | nº procesos == `bia_analyses.count()` · RTO/RPO render correcto · criticidad por umbral (`CRÍTICO` si RTO≤4h) · matriz impacto 6 ventanas · sin `{{` |
| **E‑401** Estrategias Continuidad | M06 `build_continuity_context()` (ALTA) | `len(estrategias)==len(procesos)` · `_estrategia_from_rto` determinista (`Redundancia activa` si RTO≤4) · `ubicaciones_alternas`+`proveedores_criticos` presentes · sin `{{` |
| **E‑403** DRP | M06 `build_drp_context()` (ALTA) | `sistemas_críticos` == procesos BIA · `ubicaciones.primario`/`secundario` (sede_fisica / region_cloud) · `_mecanismo_from_rto` (`Failover automático` si RTO≤4) · sin `{{` |
| **E‑049** Distintivo CCN‑STIC 809 | M27 `distintivo_generator.build_distintivo_context()` + `generate_declaration_docx()` | `cert_id = uuid5(NAMESPACE_OID, str(project_id))` determinista · BÁSICA `autoevaluación CCN-STIC 809`; MEDIA/ALTA `no sustituye`+`entidad certificación acreditada` · RSEG (role_category='responsable_seguridad') + Sponsor names reales · stats DdA (aplicables/refuerzos/conformes/pct) == DB · `Document.clasificacion='conformidad'` adjunto a `ConformityRouteRow.distintivo_document_id` |
| **E‑049‑EXT** Cert externo | M27 `distintivo_persistence.attach_external_certificate()` | SOLO MEDIA/ALTA (BÁSICA → `DistintivoIssueError`) · exige route_type='certificacion_enac' + REGISTERED + `application/pdf` · `Document.template_codigo='E-049-EXT'`, `external_cert_document_id` enlazado |
| **E‑321** Informe Auditoría externa | M09 dossier / `m_live_records` LiveRecord | keys non‑null: `codigo_auditoria_ext`, `entidad_acreditada`, fechas ISO, `categoria_ens_evaluada`, `alcance`, `resultado` |
| **E‑322** No Conformidades | M09 dossier / `m_live_records` LiveRecord | keys non‑null: `codigo_hallazgo`, `auditoria_codigo`, `severidad∈{mayor,menor}`, `medida_ens_afectada` (existe en `ens_measures`, p.ej. `op.exp.8`), `accion_correctiva`, `responsable`, `fecha_compromiso` ISO; `nc_promotion.promote_audit_ncs(db,pid)` → `findings_promoted>0` |

**Checks transversales** (aplicables a todos):
- **Anti‑Jinja**: regex `r"{{|{%|%}|}}"` NO matchea en texto renderizado. Si matchea → falta key en el `build_*_context()`.
- **Firma Ed25519**: cada `Document` firmado tiene `signature_hash` (SHA‑256 del DOCX) y `signature_value` (Ed25519 hex) NOT NULL; `Ed25519PublicKey.verify(sig, bytes)` → True. Clave en env `FULKRO_M06_SIGNING_PRIVATE_KEY`.
- **DdA freeze**: TODOS los `dda_entries` con `aprobado_por` NOT NULL + `fecha_aprobacion` NOT NULL; aplicables con `estado_implementacion='implantada'`.
- **Dossier**: `DELIVERABLE_TO_FOLDER` mapea E‑040→04_DECLARACION_APLICABILIDAD, E‑160/170→06_NORMATIVA, E‑400/401/403→10_PLAN_CONTINUIDAD, E‑049/E‑049‑EXT→01_GOBIERNO; canónicos (E‑040/E‑041/E‑049) nunca se truncan por tamaño; tope total BÁSICA 200MB / MEDIA 500MB / ALTA 1024MB; ZIP válido (`zipfile.testzip() is None`).

---

## 5 · Ruta `/client-portal/retainer` (P0 — falta el frontend)

El backend ya emite la notificación `retainer_offer` con `target_url='/client-portal/retainer'` (`lifecycle_paso4.py:337` `offer_retainer` y `:658` `send_reconsideration_to_client`), pero **la ruta no existe**. La API de decisión sí existe y funciona.

**Backend** (1 endpoint nuevo + reuso):
- NUEVO `GET /api/v1/portal/retainer-offer/{projectId}` en `backend/app/motors/m21_portal_cliente/api.py`: valida auth cliente + RLS; verifica `lifecycle_state=CERTIFIED`; devuelve `{ project_id, project_name, certified_at, recommended_tiers, available_pricing[] }`; 404 si no CERTIFIED. Pricing desde catálogo M23 (`GET /api/v1/retainer/paso2/pricing-catalog`) o `RETAINER_TIERS` canónico (R_MICRO 150 / R_LITE 300 / R_STD 700 / R_PLUS 1.200 / R_CRITICAL 3.000 € — pricing canónico FULKRO, NO los valores genéricos del area map).
- REUSO `POST /api/v1/projects/{projectId}/lifecycle/decision` (`api_paso4.py:339`, `handle_retainer_decision` `lifecycle_paso4.py:404`): body `{ decision: 'accept'|'decline'|'thinking', tier?, precio_mensual }`. accept → crea retainer M23 + `lifecycle_state=RETAINER`; decline/thinking → `retainer_declined` event + grace period (240d) → `ENDED_CHURN`.

**Frontend** (archivos a crear):
1. `frontend/lib/api/retainer-offer.ts` — `getRetainerOffer(projectId)` (GET) + `submitRetainerDecision(projectId, body)` (POST) usando wrapper `clientApi<T>` (`frontend/lib/client-portal-api.ts:34`). Tipos `RetainerOfferData`, `RetainerDecisionBody`, `DecisionResponse`.
2. `frontend/app/(client-portal)/client-portal/retainer/page.tsx` — server wrapper que renderiza `<RetainerOfferPage/>`.
3. `frontend/components/client-portal/retainer-offer/RetainerOfferPage.tsx` — header (nombre proyecto + fecha cert, tono R29 friendly), grid de tier cards (BÁSICO=R_MICRO/R_LITE, MEDIO=R_STD, ALTO=R_PLUS/R_CRITICAL), modal de decisión.
4. `frontend/components/client-portal/retainer-offer/TierCard.tsx` — label comercial + `precio_mensual` + SLA + badge recomendado + botón.
5. `frontend/components/client-portal/retainer-offer/DecisionModal.tsx` — radio (accept/decline/thinking) + selector de tier (solo si accept) + texto del grace period 240d.
6. `frontend/hooks/useRetainerOffer.ts` — `useRetainerOffer(projectId)` (fetch) + `useRetainerDecision()` (mutación optimista + toast).
7. (opcional) actualizar nav/breadcrumbs en `frontend/app/(client-portal)/layout.tsx`.

> Insight clave: `/client-portal/retainer` (oferta inicial post‑cert, pre‑activación) es DISTINTO de `/client-portal/retainer-checkin` (revisión trimestral durante retainer activo). Flujo puro in‑portal por sesión‑cookie (NO magic‑link). `performed_by='cliente'`. Requiere `lifecycle_state=CERTIFIED` (si no, error + link al dashboard).

---

## 6 · Diferencias por tier

| Aspecto | BÁSICA | MEDIA | ALTA |
|---|---|---|---|
| Medidas Anexo II aplicables | **52** | **68** | **73** (de 73 totales) |
| DdA filas (`DdaEntry`) | 73 (52 aplica / 21 no_aplica) | 73 (68/5) | 73 (73/0, con refuerzos CCN‑STIC 804) |
| Continuidad `op.cont.*` | ninguna | `op.cont.1` (BIA) | `op.cont.1‑4` (BIA+DRP+pruebas+medios alt.) |
| Entregables continuidad | — | E‑400 (BIA) | E‑400 + E‑401 + E‑403 |
| Ruta conformidad (`route_type`) | `declaracion_basica` (autodecl. CCN‑STIC 809, **sin ENAC**) | `certificacion_enac` | `certificacion_enac` |
| Auditoría externa ENAC | NO (autodeclaración) | SÍ (obligatoria) | SÍ (obligatoria) |
| Evidencias mínimas (`_TIER_MIN_EVIDENCE`) | **25** | **50** | **73** |
| Políticas firmadas mínimas (`_TIER_MIN_POLICIES`) | **10** (E‑100/101/102/103/104/105/106/108/117/126) | **18** (+E‑107/109/110/111/114/115/116/119) | **25** (+E‑112/113/118/121/123/124/125) |
| Pentest (`pentest_authorization`) | **skip** (nunca gate) | opcional (no bloquea) | **obligatorio** (gate readiness activo) |
| MAGERIT (`magerit_validation`) | recomendado (blocker readiness lo exige) | obligatorio | obligatorio |
| Cadena de firma readiness | dda + magerit | dda + magerit | dda + magerit + pentest |
| Distintivo E‑049 texto | `autoevaluación CCN‑STIC 809` | `no sustituye al certificado…entidad acreditada` | idem MEDIA |
| Cert externo E‑049‑EXT | rechazado (`DistintivoIssueError`) | adjunto PDF entidad acreditada | adjunto PDF entidad acreditada |
| Validez ruta (todos) | 730 días (2 años) | 730 días | 730 días |
| Precio implantación (informativo) | 3.200€ / 6 sem | 10.700€ / 10 sem | 22.800€ / 16 sem |
| Cascada `mark-audit-passed` | idéntica (result+idempotencia) | idéntica | idéntica |

> Matiz importante verificado en código: en `compute_readiness` el blocker de `magerit_validation` se añade para **todos los tiers** si falta firma (líneas 185‑188); solo el blocker de **pentest** se salta fuera de ALTA (línea 193). Por eso el seed de MAGERIT es práctico también en BÁSICA si se quiere `ready_for_conformity_sign=True`.

---

## 7 · Orden de ejecución recomendado (3 fixtures iterativos)

Construir y validar **un tier a la vez**, cerrando cliente↔admin antes de pasar al auditor.

**Fase A — BÁSICA (`key=conformidad-basica`)**
1. `POST /_dev/reset-test-cycle?project_id=<básica>` (limpio, `audit_passed_at` NULL).
2. `POST /_dev/seed-dda-alta-project?key=conformidad-basica` → setea tier vía paso 6, DdA 73 filas, freeze.
3. `POST /_dev/seed-magerit-alta-data?key=conformidad-basica` (para readiness).
4. `POST /_dev/seed-conformidad-ready?tier=BASICA&key=conformidad-basica` → evidencias 25, políticas 10, firmas dda+magerit, BasicDeclaration `initial`.
5. Asegurar `project_plans`+`wbs_tasks` y un `audit_preparation_runs` con dossier generado (vistas plan/documents).
6. Generar entregables E‑040/E‑160/E‑170 + E‑041 + E‑049 → correr **§4 checks** (sin `{{`, firmas Ed25519, cumplimiento_global, distintivo `autoevaluación`).
7. **Cliente↔admin perfecto**: `compute_readiness().ready_for_conformity_sign==True`; admin UI y portal cliente renderizan reales; ruta → REGISTERED.
8. `POST /api/v1/projects/<básica>/audit/mark-passed` body `{result:'passed', audit_report_ref:'…', cascade_certify:true, cascade_retainer_offer:true}` → 201, `lifecycle_state=CERTIFIED`.
9. **Auditor**: `POST /_dev/auditor-portal-token` → recorrer las 11 vistas (summary/dda/magerit/plan/evidence/e041/audit‑log/pentest[vacío]/documents/gaps/draft‑report) → todo con datos; dossier.zip 10 docs; draft‑report PDF firma Ed25519 OK.

**Fase B — MEDIA (`key=conformidad-media`)**: igual a A pero `tier=MEDIA`; evidencias 50, políticas 18; añadir E‑321/E‑322 (NC auditoría) + `promote_audit_ncs`; route `certificacion_enac`; `attach_external_certificate` (PDF); distintivo `no sustituye`; vista pentest opcional.

**Fase C — ALTA (`key=conformidad-alta`)**: igual + `POST /_dev/seed-pentest-auth-data?key=conformidad-alta` (gate readiness); continuidad E‑400/E‑401/E‑403 con RTO/RPO; firma incluye `pentest_authorization`; evidencias 73, políticas 25; vista pentest con `verification_runs` completado.

**Regresión final (CI mensual)**: `test_sim_basica` / `test_sim_media` / `test_sim_alta` (en `backend/tests/integration/`) contra DEV DB — todos los E‑codes generan, counts DdA 52/68/73, sin Jinja leakage, firmas válidas, transiciones de conformidad ejecutan, portal auditor magic‑link accesible y read‑only.

---

### Referencias de código (file:line) ancladas en el repo

- Medidas autoritativas: `backend/app/motors/m03_dda/anexo2_rd311_2022.py:22` (`ANEXO_II_RD311`), `:117` (`TOTAL/APLICA_*`).
- DdA: `backend/app/motors/m03_dda/service.py:71` (`generate_dda`), `enums.py:21` (`CategoriaSistema`).
- Readiness: `backend/app/motors/m27_conformity/readiness_service.py:30` (`_TIER_MIN_EVIDENCE`), `:41` (`_TIER_MIN_POLICIES`), `:163` (`compute_readiness`), `:193` (pentest solo ALTA).
- Audit gate: `backend/app/motors/m25_lifecycle/lifecycle_paso4.py:197` (`mark_audit_passed`), `:227` (result), `:234` (idempotencia), `:273` (cascade certify), `:292` (cascade retainer).
- Dev seeds: `backend/app/dev/router.py:166` (`_DEDICATED_KEYS`), `:642` (`seed-dda-alta-project`), `:930` (`seed-magerit-alta-data`), `:1104` (`seed-pentest-auth-data`), `:1331` (`seed-conformidad-ready`), `:1619` (`auditor-portal-token`), `:1707` (`reset-test-cycle`).
- Conformidad: `m27_conformity/conformity_service_paso5.py`, `distintivo_persistence.py` (`attach_distintivo_on_registered`, `attach_external_certificate`), `distintivo_generator.py` (`build_distintivo_context`).
