# Ejecutable 8 · Pasada 20 — Cierre del ciclo comercial (contrato → firma → pagos → cobro → estado → export)

> **Tipo:** auditoría READ-ONLY (no se construyó nada · no se propuso plan).
> **Fecha:** 2026-06-02 · **Branch:** radar-v3-pr · **Método:** lectura del CUERPO del
> código (servicio/modelo/endpoint/plantilla/componente), `file:line` del cuerpo real (NO grep
> para concluir).
> **Alcance:** `m14_contracts`, `backend/app/billing/milestone_factory.py`, `m15_billing`,
> `m05_signing/signable_types.py`, `config.py`, frontend admin/cliente.

---

## 0. Veredicto ejecutivo

El ciclo comercial **existe y arranca de verdad** (propuesta `won` → contrato con pricing/hitos reales → milestones ligados a fases → factura fiscal con Verifactu), pero **el último tramo de pulido al cliente está a medias o desconectado** en cinco puntos concretos:

1. El contrato **se rellena con datos del proyecto** (pricing Básica/Media/Alta + hitos), pero el **documento que se exporta es un volcado de parámetros**, no un contrato legal redactado; y existe **un segundo contrato de servicios bien redactado (C‑100) totalmente desconectado** del pricing/ciclo.
2. La firma del contrato comercial **NO usa el canvas Ed25519 + hash chain de m05**; usa un **timestamp de magic‑link**. No queda sellado criptográficamente ni se archiva en IDMS.
3. Los **hitos de pago se generan ligados a las fases** del proyecto y se cablean al alta, pero **sin fechas previstas** (se disparan por evento `phase_complete`, no por calendario).
4. El **IBAN de Marcos** es configurable por env (degradación elegante), pero el **NIF/CIF del consultor es un placeholder** (`__CONSULTOR_NIF__`, `fulkro_cif=""`), no hay ajustes admin, y **el IBAN no entra ni en el PDF de la factura ni en el contrato** (solo en el email, a mano).
5. **No existe vista que cruce avance de implementación con estado de pagos.** Implementación y pagos viven en pantallas separadas (admin: `/finance` vs `/roadmap`; cliente: `/billing` vs `/plan`).

Patrón dominante: **hueco de producto** (motor/datos reales sin cablear el último paso o sin converger dos caminos paralelos), más **un placeholder fiscal** (NIF/CIF consultor) que sí es defecto duro.

---

## 1. Tabla síntesis (clasificación · `file:line` del cuerpo · qué falta · portal)

| # | Ítem | Clase | `file:line` del cuerpo | Qué falta | ¿Frontend? ¿Qué portal? |
|---|---|:--:|---|---|---|
| 1 | Generación adaptada del contrato | **2** | `m14.../contract_service.py:170-283` (`generate_contract_apendice_m`: pricing/hitos/AAPP reales desde `PricingCalculator.get_milestones`) **pero** export `generate_docx:499-536` = volcado de `parametros_xyzpr` en viñetas; rival `legal_templates.py:252-307` (C‑100) bien redactado **pero** "honorarios en propuesta anexa" (`:262-264`), `fulkro_cif=""` | Un **único** contrato bien redactado que **consuma** el pricing/hitos del proyecto. Hoy: datos en C‑001 (mal renderizado) + redacción en C‑100 (sin pricing) = dos mitades sin converger | Sí, admin `/contratos` (genera). **Cliente NO ve el contrato** salvo magic‑link |
| 2 | Firma del contrato por el cliente | **2** (canvas Ed25519 = **3/ausente**) | `contract_service.py:374-415` (`send_for_client_signature` → magic‑link `FIRMA_DOCUMENTO`) + `:417-439` (`register_client_signature` solo pone `firmado_cliente_at` + `estado=vigente`). `m05_signing/signable_types.py:9-40` **NO incluye contrato comercial**; `grep` m14 → 0 refs a `signing_intent`/`ed25519`/`idms` | (a) cliente firma por **magic‑link timestamp, NO canvas**; (b) **NO sellado criptográfico** (solo `hash_sha256` de contenido `:307-322`, que no es firma); (c) **NO se archiva en IDMS** | `(client-portal)/firma/page.tsx` es solo **explicativa** (ADR‑010). El canvas real (`/firmas-pendientes`) es para docs ENS, **no para el contrato** |
| 3 | Calendario de pagos por hitos | **2** | `billing/milestone_factory.py:103-181` (`create_milestones_for_contract`: amounts desde pricing, `workflow_phase_index` mapeado `:56-65`) + **cableado al alta** `m13.../commercial_workflow_service.py:340-390` (best‑effort). Modelo `billing_milestones.py:128-174`: **sin columna de fecha prevista** (solo `billed_at`/`paid_at` de evento) | **Fechas previstas ausentes.** El disparo es por evento `phase_complete`, no por calendario. `billing_trigger="scheduled_date"` existe en el enum (`:46`) pero **no hay columna de fecha que lo soporte** | Admin `/finance` (reconciliación) — ver #5 |
| 4 | Datos de cobro del consultor (IBAN/NIF) | **2** (NIF/CIF = **3**) | IBAN env‑config `config.py:154-157` (`marcos_bank_iban=""`, holder/institution por defecto). **NIF placeholder** `m15.../billing_service.py:434` (`"nif": "__CONSULTOR_NIF__"`). `generate_invoice_pdf:445-509` **no imprime bloque emisor/IBAN**. `legal_templates.py:146` `fulkro_cif=""` nunca se rellena | **NIF/CIF del consultor sin configurar** (placeholder literal en el QR Verifactu); **sin ajustes admin** (solo env); IBAN **no entra en PDF de factura ni en contrato** (solo email, manual) | **No hay UI de ajustes fiscales.** IBAN se muestra "info‑mode" en cliente `/billing` (`BillingHistory`) |
| 5 | Estado implementación × pagos (vista cruzada) | **3** | Admin pagos: `(admin)/admin/finance/page.tsx:82-98` (KPIs + `ReconciliationManualPanel`, solo pagos). Admin implementación: `(admin)/admin/projects/[id]/roadmap/page.tsx:82` (`RoadmapView`, solo fases). Cliente: `(client-portal)/billing/page.tsx` (facturas) vs `/plan` + `/certificacion` (avance) | **No existe la vista cruzada** "dónde vamos / qué se ha pagado / qué toca pagar". El dato para cruzar existe (`ContractMilestone.workflow_phase_index` + `status`) pero **ninguna pantalla lo une** | Falta en **ambos** portales. Natural: admin `/projects/[id]` (estado+pagos) y cliente `/plan` o `/certificacion` (resumen amable R29) |
| 6 | Exportación del contrato | **2** | `m14.../api.py:310-327` `GET /contracts/{id}/docx` (admin‑only, `require_owner` `:25`) → `generate_docx` volcado. Export rico `api.py:404-462` `/legal-templates/{slug}/generate` pero es el **C‑100 legal desconectado**. **Sin PDF de contrato**; sin variante firmado/sin‑firmar | **PDF ausente**; **no hay variante firmada vs sin firmar** (mismo DOCX muestra timestamps); **cliente no puede descargar** el contrato desde su portal; **no se archiva firmado en IDMS** | Solo **admin** (DOCX). Falta descarga en **cliente** + archivado IDMS del firmado |

---

## 2. Detalle por ítem (lo que el cuerpo HACE)

### 1 · Generación adaptada del contrato — **clase 2**
- **Adaptación de datos: REAL.** `generate_contract_apendice_m` (`contract_service.py:170-283`) parte de una `Proposal` y recalcula hitos con `PricingCalculator().get_milestones(categoria, importe_total)` (`:208-212`), inyectando en `parametros_xyzpr`: categoría, total, base, extras, garantía, `hitos` (code+pct+amount), `is_aapp`, `payment_days` (60 AAPP / 30) (`:224-243`). El pricing canónico Básica/Media/Alta proviene de `PricingCalculator` (core). Hay incluso modo LLM (Agente 20) opcional para cláusulas narrativas (`:262-305`).
- **Render del documento: pobre.** `generate_docx` (`:499-536`) produce un DOCX que es un **volcado**: heading + `Plantilla: C-001` + firmante + vigencia + bucle `for k,v in parametros_xyzpr` como viñetas + cláusula + firmas + hash. **No** redacta articulado legal, **no** maqueta la tabla de hitos, **no** renderiza la cláusula LCSP/garantía como texto.
- **Duplicidad C‑001 vs C‑100.** En `legal_templates.py:53-57` existe **C‑100 "Contrato de prestación de servicios de consultoría ENS"** con render rico (`_gen_contrato_prestacion_servicios:252-307`: objeto, plazos/honorarios, responsabilidad, protección de datos, firma) **pero** los honorarios se remiten a "propuesta económica anexa" (`:262-264`) y `fulkro_cif=""`. Es decir: **el contrato bien redactado (C‑100) no consume el pricing/hitos**, y el que sí los lleva (C‑001) se exporta como volcado. **No convergen.**

### 2 · Firma del contrato por el cliente — **clase 2** (canvas Ed25519 = **ausente/3**)
- El flujo es: `sign_marcos` (`:358-372`, pone `firmado_marcos_at`) → `send_for_client_signature` (`:374-415`) genera un **magic‑link `MagicLinkPurpose.FIRMA_DOCUMENTO`** con scope `{contract_id, hash_sha256}` → `register_client_signature` (`:417-439`) en el callback **solo** setea `firmado_cliente_at` + `estado="vigente"`.
- **No usa m05.** `signable_types.py` (catálogo de 14 firmables canvas: dda, conformidad_ens, acta_comite, policy_approval, plan_adecuacion…) **NO incluye el contrato comercial**. La búsqueda en m14 de `signing_intent`/`SigningService`/`ed25519`/`idms` devuelve **0 referencias**.
- Por tanto, respondiendo literal: **(a)** el cliente firma por magic‑link, **no** con el canvas manuscrito; **(b)** lo que queda es un `hash_sha256` del *contenido* (`_compute_hash:307-322`) + timestamps — **no** una firma Ed25519 del trazo ni hash chain; **(c)** el contrato firmado **no** se archiva en IDMS (no hay llamada).
- Matiz honesto: el magic‑link sí da gating + trazabilidad ligera (link_id), y el `hash_sha256` detecta manipulación del contenido. Pero **no es** la firma electrónica simple Ed25519‑canvas que sí usan los documentos ENS.

### 3 · Calendario de pagos por hitos — **clase 2**
- `MilestoneFactory.create_milestones_for_contract` (`milestone_factory.py:103-181`) materializa `ContractMilestone` desde `PricingCalculator.get_milestones`, con `workflow_phase_index` resuelto por `resolve_workflow_phase` (`:74-88`) según mapping canónico (`hito_1_firma→ONBOARDING`, `hito_5_certificacion→CONFORMIDAD`, `:56-65`), `amount_eur`, `vat_percent`, `billing_trigger="phase_complete"`, `blocking_next_phase`, `auto_billing_enabled`. Idempotente por `UNIQUE(contract_id, milestone_index)`.
- **Cableado al alta: SÍ** (best‑effort). `commercial_workflow_service._create_milestones` (`:340-390`) lo invoca cuando el contrato tiene `proposal_id` + categoría + importe resolubles.
- **Fechas previstas: NO.** El modelo `ContractMilestone` (`billing_milestones.py:128-174`) **no** tiene columna de fecha prevista/vencimiento; solo `billed_at`/`paid_at` (timestamps de evento). El calendario es **event‑driven** (al completar la fase), no un cronograma con fechas. El enum `VALID_BILLING_TRIGGERS` incluye `"scheduled_date"` (`:46`) pero **no existe campo de fecha** que lo respalde.

### 4 · Datos de cobro del consultor — **clase 2** (NIF/CIF = **3**)
- **IBAN: env‑config con degradación.** `config.py:146-157`: `marcos_bank_iban` (default `""`), `marcos_bank_holder="Marcos Mata Vega"`, `marcos_bank_institution="Banco Santander"`, `marcos_bank_bic`. Si vacío, el email de factura omite instrucciones de transferencia (Marcos las añade a mano). **No hay UI admin** de ajustes fiscales (es `Settings` pydantic/env).
- **NIF consultor = placeholder.** `billing_service._build_verifactu_qr_payload` (`:423-443`) construye el QR AEAT con `"nif": "__CONSULTOR_NIF__"` **literal hardcodeado** → una factura real lleva ese placeholder en el QR de verificación.
- **PDF de factura sin emisor/IBAN.** `generate_invoice_pdf` (`:445-509`) imprime nº, tipo, fechas, concepto, líneas, totales, hash Verifactu y QR, pero **ningún bloque de identificación del emisor** (nombre/NIF/domicilio) **ni IBAN/instrucciones de pago**.
- **CIF FULKRO legal vacío.** `legal_templates.py:146` `fulkro_cif=""` y `build_legal_context` (`:158-214`) rellena cliente + RSEG/DPO pero **nunca** `fulkro_cif`. El CIF del *cliente* sí se autorrellena (`COALESCE(c.cif,'')` `:169`).
- **El IBAN no entra en el contrato** (ni `generate_docx` ni C‑100 lo incluyen).

### 5 · Vista estado‑implementación × pagos — **clase 3 (ausente; ambas mitades existen sueltas)**
- **Admin pagos:** `admin/finance/page.tsx:82-98` = `FinanceKpis` (billed/paid/pending/overdue) + `ReconciliationManualPanel` (lista pendientes + "marcar pagado"). Pagos puros; sin avance de implementación.
- **Admin implementación:** `admin/projects/[id]/roadmap/page.tsx:82` = `RoadmapView` (PhaseStepper + PhaseCards) + próximas acciones. Implementación pura; sin pagos.
- **Cliente:** `client-portal/billing/page.tsx` (lista de facturas + IBAN info‑mode) vs `/plan` (Gantt) + `/certificacion` (timeline). Separados.
- El dato para cruzar **existe** (`ContractMilestone.workflow_phase_index` + `status` + `mark_milestone_paid` que avanza fase, `billing/api.py:249-296`), pero **no hay pantalla que muestre "fase X pagada / fase Y pendiente de pago"**.

### 6 · Exportación del contrato — **clase 2**
- **Único export real del contrato comercial:** `GET /contracts/{id}/docx` (`api.py:310-327`), router **admin‑only** (`require_owner`, `:22-26`) → `generate_docx` (volcado). **Sin PDF.** **Sin variante firmado/sin‑firmar** (el mismo DOCX muestra `firmado_*_at` o "pendiente").
- **Export rico paralelo:** `/legal-templates/{slug}/generate` (`api.py:404-462`) sí renderiza bien, pero es el **C‑100 legal desconectado** del pricing (ver #1), también admin‑only.
- **Cliente:** no hay endpoint/página de descarga del contrato en el portal (no existe `client-portal/contratos`). El firmado **no** se archiva en IDMS.

---

## 3. Solapes con huecos ya conocidos

| Ítem Pasada 20 | Solapa con hueco conocido | Relación |
|---|---|---|
| #4 NIF/CIF consultor placeholder | **CIF autorrelleno** | El CIF del **cliente** sí se autorrellena (`build_legal_context:169`); lo que falta es el **CIF/NIF del propio consultor** (`fulkro_cif=""` + `__CONSULTOR_NIF__`). Mismo dominio, lado emisor. |
| #3 Hitos sin fechas previstas | **Calendario de pagos** | Es exactamente ese hueco: existen hitos ligados a fase pero **sin cronograma de fechas**; disparo por evento, no por calendario. |
| #1 C‑001 (pricing) vs C‑100 (redacción) + alcance | **Alcance sin trigger** | El "alcance/scope" del contrato no se inyecta para disparar el documento bueno; C‑100 remite a "propuesta anexa". La adaptación por alcance/nivel existe en datos (C‑001) pero **no dispara** el contrato redactado. |
| #5 Sin vista cruzada | (nuevo, adyacente a #3) | Depende de que los hitos (con o sin fecha) se rendericen junto al roadmap; hoy ninguna vista lo hace. |
| #2 Firma contrato ≠ canvas | (nuevo) | El resto de docs ENS sí usan canvas Ed25519 (m05); el **contrato comercial es la excepción** (magic‑link timestamp). Asimetría de firma. |

---

## 4. Lectura senior · hueco‑normativo vs hueco‑de‑producto · prioridad

- **#4 NIF/CIF consultor = el más "duro".** Es el único con un **placeholder fiscal real en producción** (`__CONSULTOR_NIF__` en el QR Verifactu + `fulkro_cif=""` en DPAs). Una factura/QR con NIF placeholder es un defecto fiscal visible. **Hueco de producto, pero con cara legal.** Necesita: configurar NIF/CIF/domicilio del consultor (env o ajustes admin) + inyectarlos en PDF factura y contrato.
- **#1 + #6 (contrato redactado + export) = el más visible para el cliente.** Hoy el cliente recibiría, si acaso, un DOCX volcado o un C‑100 sin precio. **Hueco de producto:** converger C‑001 (datos) + C‑100 (redacción) en un único contrato adaptado y exportarlo PDF, descargable también por el cliente y archivado en IDMS.
- **#2 firma contrato ≠ canvas.** No es ilegal (el magic‑link + hash de contenido es defendible como evidencia), pero es **asimétrico** con el resto del producto y no sella el trazo ni archiva. Subir a canvas Ed25519 + IDMS daría coherencia.
- **#3 calendario + #5 vista cruzada = pulido de gestión.** Hitos por fase reales; faltan **fechas previstas** y la **vista única "avance × pagos"**. Hueco de producto puro; alto valor percibido (admin sabe qué cobrar cuándo; cliente ve "qué toca pagar").

### Dónde debe aparecer el frontend que falta
- **#1/#6:** botón "Generar/Descargar contrato (PDF)" en **admin** `/contratos` (firmado y borrador) + descarga en **cliente** (portal, junto a firma).
- **#2:** firma del contrato en **cliente** vía el mismo canvas de `/firmas-pendientes`.
- **#3/#5:** sección **"Hitos y pagos"** cruzada con fases en **admin** `/projects/[id]` y resumen amable (R29) en **cliente** `/plan` o `/certificacion`.
- **#4:** **ajustes fiscales del consultor** (NIF/CIF/IBAN/domicilio) en **admin** settings; inyección en PDF de factura + contrato.

> **Fin del mapa de Pasada 20.** No se construyó nada. Clasificación con `file:line` del cuerpo leído en la tabla §1; detalle en §2.
