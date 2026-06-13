# AUDITORÍA TOTAL DE FULKRO — informe único exhaustivo

> **Fecha**: 2026-06-13 · **Rama**: `main` · **HEAD**: `9a57c769` (m_remediation ADR-055 desplegado a prod) · **Autor**: auditoría asistida por IA bajo dirección de Marcos Mata.
>
> **Alcance**: TODO el repositorio, leído **archivo a archivo, código a código** (no por grep). 52 lectores profundos recorrieron el backend (~89.000 LOC Python · 44 motores), el frontend (~62.000 LOC TS/TSX · 167 páginas · 417 componentes), la base de datos (253 migraciones · ~246 tablas), la IA (agentes + copilotos + RAG), la capa MCP/pentest, la infraestructura y la spec ENS. Cada hallazgo se **verificó contra el código real**, no contra la documentación: las discrepancias entre lo que `CLAUDE.md`/`docs/` afirman y lo que el código hace están marcadas explícitamente (honestidad empírica — la directiva de Marcos).

## Cómo leer este documento

- **Parte I — Síntesis (cap. 01-09)**: responde directamente a tus preguntas (qué es, a quién sirve, qué cubre del ENS, las fases, la sincronización de portales, la arquitectura, la IA, el compliance propio, el estado de producción y el **veredicto honesto** de qué hace al 100% y qué no).
- **Parte II — Referencia detallada (cap. 10-96)**: una sección densa por cada subsistema (transversales 10-19, los 44 motores 20-47, IA 70-71, frontend 80-86, tests 90-91, infra 92, spec/negocio 95-96). Aquí está «cada fleco»: ficheros, tablas, endpoints, máquinas de estado, medidas ENS, gotchas, dead-code y discrepancias.

**Leyenda de estado**: ✅ completo · 🟡 parcial · 🔴 stub / roto · ⚠️ discrepancia doc-vs-código · 🔒 sólo activable en servidor real (Hetzner).

## Foto del producto en cifras (empíricas, esta auditoría)

| Dimensión | Cifra real verificada | Lo que decía la doc |
|---|---|---|
| Motores backend | **44** directorios `m*` (m01-m31 + 13 transversales `m_*`) | «42 motores» |
| LOC backend / frontend | ~**89.000** Py / ~**62.000** TS-TSX | — |
| Endpoints HTTP | ~**1.191** decoradores (194 routers montados) | «~879» ⚠️ |
| Tablas (ORM + migración) | ~**246** live (237 ORM + 9 sólo-migración) | «~184» ⚠️ |
| Migraciones Alembic | **253** ficheros · 1 head `remediation_agent_001` | «160» ⚠️ |
| Tests backend | **554** ficheros · ~5.642 funciones · **~5.956 PASS / 0 fallos** | «~353» ⚠️ |
| Páginas / componentes FE | **167** páginas · **417** TSX · 62 hooks · 177 lib | — |
| Specs E2E Playwright | **299** (202 e2e + 97 polish a11y) · **230 PASS / 147 deuda-specs** | «140+» ⚠️ |
| Agentes IA | 31 IDs registry → **~14 activos** + copiloto A14 | «31 agentes» ⚠️ |
| Servidores MCP pentest | **14** (5-6 reales validados, resto mock/defer) | «14 · 3 reales» |
| Corpus RAG | **66** docs ES (27 ingestados) | «66» ✅ |
| Medidas ENS por nivel | **BÁSICA 52 · MEDIA 68 · ALTA 73** (BOE RD 311/2022) | «52/68/73» ✅ |
| Precios (proyecto) | **3.200 / 10.700 / 22.800 €** + retainers 150-3.000 €/mes | ✅ |
| Estado | **Producto cerrado** (2026-06-08) · **desplegado en Hetzner** · ADR-055 remediación en prod (2026-06-13) | — |

> Las cifras infladas/desactualizadas en `CLAUDE.md` (endpoints, tablas, tests, agentes) NO son errores de producto: son una **doc que se quedó atrás** respecto a un código que creció mucho. Se detallan en el cap. 09.


## 01 · Qué es FULKRO y para quién

**FULKRO es una plataforma SaaS de implantación del ENS** (Esquema Nacional de Seguridad, RD 311/2022) operada por una **consultora unipersonal** — Marcos Mata, consultor autónomo en Madrid (`backend/app/fulkro_identity.py`). No es un producto que el cliente «usa» solo: es la herramienta con la que **Marcos opera la consultoría** y a través de la cual el cliente participa con mínima fricción.

### El modelo de negocio (verificado en código)
- **Cliente directo = empresa privada** que licita a la Administración Pública y a la que un pliego le exige certificación/conformidad ENS.
- **La AAPP es «customer-of-customer», NUNCA cliente directo** (doctrina AMEND-012, sostenida empíricamente). Fulkro no vende a la administración; vende al proveedor que necesita el ENS para concursar.
- **Multi-tenant real**: un solo consultor gestiona muchos clientes en paralelo, con aislamiento por RLS PostgreSQL (`client_id`/`project_id`) y portal-cliente sin cuentas permanentes (magic-links + login email/password single-user).

### Propuesta de valor
Automatiza el **ciclo completo** de certificación ENS de un cliente — del diagnóstico inicial al mantenimiento post-certificación — combinando **motores deterministas** (decisiones normativas trazables para ENAC, R1: motores > LLM) con **IA de apoyo** (enriquecimiento, copilotos, pentest autopilot) y una **plataforma de producción turnkey**. El consultor hace el trabajo experto; la plataforma le multiplica la capacidad y le da trazabilidad de auditoría (hash-chain, firmas Ed25519, dossier ENAC).

### Precios canónicos (fuente única `pricing_config` BD → `rules.py`, verificado)
| Nivel ENS | Proyecto (fijo) | Plazo | Auditoría externa |
|---|---|---|---|
| **BÁSICA** | **3.200 €** (techo 4.500) | 2-4 sem | NO — autoevaluación (CCN-STIC 809) |
| **MEDIA** | **10.700 €** (techo 13.000) | 2-4 sem + 8-16 sem con ENAC | SÍ — ENAC obligatorio (coste cliente aparte) |
| **ALTA** | **22.800 €** (techo 28.000) | 4-6 sem + ENAC | SÍ — ENAC + SOC + DR + monit. 24/7 |

**Retainers post-certificación** (5 tiers, `pricing_catalog`): R_MICRO 150 € · R_LITE 300 € · **R_STD 700 €** (base del negocio) · R_PLUS 1.200 € · R_CRITICAL 3.000 €/mes. **Excluido del precio**: auditoría ENAC externa, hardware/licencias, hosting, pentest externo.

> Una sola fuente: editar el precio en `/admin/settings/pricing` (tabla `pricing_config`) se propaga a propuesta, contrato, factura y catálogos (no hay «precios sombra»; la antigua divergencia 22.000/22.800 y R_STD 400/700 está resuelta). Caveat menor (cap. 09): el endpoint `_RETAINER_PRICING` del portal cliente y `PRICING_CATALOG` de m13 conservan números hardcodeados que sólo se alinean en runtime tras leer la BD.

### Posicionamiento (docs/differentiators)
Frente a **Audidat** (líder del mercado): Fulkro entra **por debajo en precio** en las tres categorías, con plataforma propia + automatización + presencia in-situ el día de la auditoría. Misión actual: **conseguir el primer cliente piloto pagador** (categoría MEDIA, 10.700 € + retainer R_STD). **El producto está cerrado y desplegado, pero aún no hay cliente piloto pagador real onboardeado** (cap. 08).

### Diferenciador técnico real (no marketing)
El **suelo de riesgo MAGERIT** fiel al Libro III (un activo de valor «muy alto» nunca baja de riesgo «bajo» por muchas salvaguardas) es una propiedad emergente de las tablas de lookup, no un parche — trazabilidad defendible ante un auditor. El catálogo ENS es **transcripción literal del BOE** verificada celda a celda (cap. 02).


## 02 · Cobertura del ENS — ¿lo cubre al 100%?

Respuesta corta y honesta: **el CATÁLOGO normativo del ENS está cubierto al 100% y verificado contra el BOE; la IMPLANTACIÓN del ciclo está casi completa, con flecos concretos** (cap. 09) que hoy impedirían cerrar una certificación real end-to-end sin pasos manuales y sin la activación en Hetzner.

### 2.1 Las medidas — 52 / 68 / 73 (verificado en el código, no en la doc)
La fuente única de verdad es `backend/app/motors/m03_dda/anexo2_rd311_2022.py` (168 LOC), **transcripción literal del BOE-A-2022-7191** verificada celda a celda el 2026-06-07. Contando las tuplas de aplicabilidad:

| Nivel | Medidas aplicables | Cómo se obtiene |
|---|---|---|
| **BÁSICA** | **52** | tuplas `(True, True, True)` |
| **MEDIA** | **68** | BÁSICA + 16 medidas `(False, True, True)` |
| **ALTA** | **73** (todas) | MEDIA + 5 medidas `(False, False, True)` |

`TOTAL_MEDIDAS = 73` (Anexo II completo). Estructura: **4 `org.*` + 33 `op.*` + 36 `mp.*`**. La monotonicidad es correcta (ninguna medida aplica a un nivel inferior y no a uno superior). Esto **corrige una deriva previa** que arrastraba los conteos del derogado RD 3/2010 (46/64/73) — el seed filtra 6 medidas no oficiales (`op.exp.11`, `mp.s.8/9`, `mp.if.9`, `mp.per.9`, `mp.com.9`) del YAML de 79 entradas y un override post-seed reescribe las 73 filas desde la tabla autoritativa. Un test (`test_exactly_73_measures_loaded`) y un `assert` de import en `audit_questions.py` (73 claves) blindan la regresión.

### 2.2 Categorización (M01) — la regla del máximo
Determinista 100% sin LLM: 5 dimensiones DICAT (Disponibilidad, Integridad, Confidencialidad, Autenticidad, Trazabilidad), nivel = máximo de las dimensiones (Anexo I, art. 40). Soporta **suelo AAPP heredado** (`categoria_heredada_aapp`) con guard contractual y arquetipos PYME por CNAE (incluye el caso autónomo individual con nota de proporcionalidad CCN-STIC 801).

### 2.3 Declaración de Aplicabilidad (M03) y refuerzos
`generate_dda` crea las 73 entradas con su aplicabilidad por nivel y los **refuerzos R1-R5** (tabla `ens_measure_refuerzos` con `applicable_categories` JSONB y `source_chunk_id` trazable al corpus). ⚠️ La doc menciona «R1-R9»; el código materializa **R1-R5** — el resto de refuerzos del Anexo no están todos modelados como filas. Freeze/unfreeze con gate del 80 % de medidas valoradas; revisión anual (CCN-STIC 808) que exige reaprobación de Dirección; medidas compensatorias (art. 8) en tabla separada para no corromper la DdA firmada.

### 2.4 El catálogo de entregables documentales (M06)
La fábrica de documentos cubre el corpus documental ENS con **116 módulos de plantilla** reales (35 políticas E-1xx + 39 procedimientos E-2xx + 39 entregables E-0xx/E-4xx/E-7xx + 3 comerciales), 16 plantillas Excel (X-001..X-016: DdA, inventario MAGERIT, gap CCN-STIC 808, RAT RGPD art. 30, BIA, RACI…) y el pipeline DOCX→firma Ed25519→PDF (LibreOffice headless)→MinIO→audit_log. Sign-off tier-aware: BÁSICA 10 / MEDIA 18 / ALTA 25 políticas. ⚠️ La doc dice «96/104 plantillas»; el real son 116 módulos / 86 entradas de catálogo — más, no menos.

### 2.5 Lo que cubre el ciclo completo (resumen, detalle en cap. 03)
Categorización (M01) → MAGERIT v3 (M02) → DdA (M03) → análisis GAP (M04) → obligaciones/medidas (M05) → fábrica documental (M06) → evidencias WORM (M07) → verificación/pentest (M08) → preparación dossier ENAC (M09) → simulacro pre-ENAC (M10) → conformidad/renovación (M27) → acompañamiento de auditoría (m_audit_accompaniment) → retainer post-cert (M23). **Es un ciclo de vida ENS completo, no un conjunto de utilidades sueltas.**

### 2.6 Honestidad: dónde NO llega al 100 %
- **Cierre de BÁSICA bloqueado** hoy: el firmante de la declaración no es RSEG y falta la ingesta manual del CCN-STIC 809 (AMPARO) en el corpus.
- **`op.exp.8` (logs del cliente, retención ≥12 m)** no se recoge del cliente — la retención de 12 m que existe es la de la propia plataforma Fulkro.
- **Sellos de tiempo ALTA (`mp.info.4`)**: el gating en la DdA es correcto pero la integración TSA RFC 3161 es best-effort y no valida la cadena de certificación.
- **PILAR**: exporta XML propio, no el formato `.mgr` nativo del CCN (sin XSD público) → ciclo cerrado con PILAR imposible sin paso manual.
- **Semáforo per-medida (M04)** parcialmente stub en algún punto; varios motores no emiten `audit_log` (cap. 09).

> Conclusión: **como representación del ENS, Fulkro es exhaustivo y fiel al BOE**. Como máquina de certificar de extremo a extremo sin intervención, le faltan flecos concretos y la activación en el servidor real.


## 03 · Las fases — el ciclo ENS de extremo a extremo

La fuente de verdad es `backend/app/core/workflow_phase.py` (`WorkflowPhase`): **10 fases canónicas** en orden, sobre las que se construyen los gates, las notificaciones y el copiloto. El estado de fase vive en `projects.fase` (primario) con un fallback en cascada de 9 subconsultas `EXISTS` que deriva la fase real del estado de los motores.

| # | Fase | Qué ocurre | Motor(es) | Cliente / Admin |
|---|---|---|---|---|
| 1 | **`pre_venta`** | Lead → propuesta hiperpersonalizada (PDF, pricing por categoría) → contrato C-001..C-005 → firma canvas Ed25519 | M13, M14 | Cliente firma; Marcos opera el CRM |
| 2 | **`onboarding`** | Alta del proyecto, cuestionario multi-rol/sector (72 plantillas JSON con branching), conexión cloud OAuth solo-lectura, mini-LMS, consentimiento RGPD art. 13 | M16 | Cliente aporta datos y conecta su cloud |
| 3 | **`diagnostico`** | Diagnóstico organizacional interno (madurez L0-L5 CCN-STIC 804/808, ISO 27001, cross-compliance RGPD/NIS2/DORA, quick-wins → E-090) | M21_diagnosis | Marcos-only (interno) |
| 4 | **`analisis_riesgos`** | MAGERIT v3 completo: activos → dependencias → amenazas → salvaguardas → riesgo intrínseco/efectivo/residual → plan de tratamiento (firmable) | M02 | Cliente revisa (read + review); Marcos opera |
| 5 | **`adecuacion`** | DdA (73 entradas), análisis GAP (CMM L0-L4 desde la DdA), instanciación de obligaciones, plan de adecuación (Gantt, orden topológico) | M03, M04, M05, M17 | Cliente revisa la DdA y firma |
| 6 | **`implantacion`** | Fábrica documental (políticas/procedimientos/entregables), recopilación de evidencias WORM, registros vivos E-300..E-325, gestión de incidentes/riesgo/continuidad | M06, M07, M19, m_live_records | Cliente sube evidencias y firma; el equipo de Fulkro implanta |
| 7 | **`dda_final`** | Congelación de la DdA, verificación de cobertura y firmas | M03, M09 | — |
| 8 | **`verificacion`** | Pentest M8 autopilot (MEDIA/ALTA), simulacro pre-ENAC, preparación del dossier | M08, M10, M09 | Cliente autoriza pentest (OTP step-up) |
| 9 | **`conformidad`** | Auditoría/certificación (MEDIA/ALTA vía ENAC) o declaración (BÁSICA), distintivo CCN-STIC 809, DPC anual, INES/LUCIA | M27, m_audit_accompaniment | Cliente firma la conformidad; auditor ENAC en su portal |
| 10 | **`retainer_cierre`** | Mantenimiento post-cert (vigilancia, comités, renovación bienal) o cierre/exit (grace period + borrado RGPD) | M23, M25 | Cliente recibe el servicio recurrente |

### Gates entre fases (`workflow_gates.py`, HTTP 409 si no se cumplen)
7 gates async deterministas serializan el orden ENS: `require_signed_categorization` (M01→M03), `require_frozen_dda` (M06), `require_magerit_analysis`, `require_some_evidence`, `require_complete_audit_prep` (M09), `require_pentest_authorisation` (M08), `require_clean_audit_sim` (acompañamiento). Además, `WorkflowBlockingService` consulta 5 feature-flags que bloquean la fase 9 (CONFORMIDAD): `media_auditor_enac`, `media_vuln_scan`, `alta_pentest_cpstic`, `alta_criptografia_807`, `alta_productos_cpstic`. ⚠️ Éste último es un **stub permanente** (`return False`): la columna `Asset.cpstic_certified` no existe, así que un proyecto ALTA nunca supera automáticamente el gate de conformidad (deuda real no marcada en la doc — cap. 09).

### Quién hace qué (filosofía «cliente-mínimo»)
El cliente **VE** (categorización, MAGERIT, DdA, plan — solo lectura), **AUTORIZA** (cloud OAuth, pentest con OTP), **FIRMA** (DdA, conformidad, actas, contrato… 9 páginas de firma) y **RECIBE** (remediaciones, certificación, retainer). **NO** redacta políticas, ni opera el ENS técnico, ni decide la normativa: de eso se encarga el equipo de Fulkro desde el panel admin (R29 cliente-friendly + R30-inverso, verificado empíricamente en el frontend, cap. 04).


## 04 · Los portales y su sincronización

FULKRO no es «un portal»: son **cuatro audiencias de autenticación** y varios portales de un solo uso, todos en el mismo backend Next.js 14 / FastAPI con separación estricta.

### 4.1 Los portales (verificados en `frontend/app/` + `main.py`)
| Portal | Ruta | Auth | Para quién |
|---|---|---|---|
| **Admin** (consultor) | `/admin/**` (96 páginas) | sesión Marcos `require_owner` (WebAuthn/TOTP) | Marcos opera TODO |
| **Cliente** | `/client-portal/**` (42 páginas) | `ClientUser` (JWT Ed25519, login email + MFA) | La empresa cliente |
| **Auditor ENAC** | `/auditor-portal/[token]` (12 vistas) | magic-link `AUDITOR_PORTAL_ENAC` + OTP | El auditor acreditado (solo lectura) |
| **Pentester** | `/pentester-portal/[token]` | magic-link + scope firmado | El pentester externo |
| **Remediación** | `/remediation/[token]` | magic-link | Quien aplica las mejoras |
| **Verify-auth** | `/verify-auth/[token]` | magic-link | El RSEG autoriza el pentest |
| **Público** | `/diagnostico`, `/download`, `/sign`, `/ml/consume` | token | Diagnóstico gratis, descargas, firma |
| **Legal** | `/privacy`, `/cookies`, `/dpa-template`, `/sub-processors`, `/trust`, `/terms` | abierto | RGPD/AEPD + Trust Center vivo |
| **Landing** | `landing/*.html` | estático | Marketing (SEO, Schema.org) |

El **ENS Radar** (captación automática de licitaciones defectuosas) **fue eliminado del producto** — confirmado: `drop_ens_radar_001` borra 19 tablas, no existe el motor ni la ruta. El ciclo comercial manual (M13/M14) permanece intacto. ⚠️ El `MASTER_PLAN.md` todavía lo lista — reliquia pre-retiro.

### 4.2 La sincronización admin ↔ cliente (cómo funciona de verdad)
La sincronización en tiempo real se apoya en tres mecanismos verificados:

1. **SSE dispatcher** (`core/sse_dispatcher.py`): canales por proyecto `project:{uuid}`, con **filtrado por audiencia** — `ADMIN_EVENT_TYPES` y `CLIENTE_EVENT_TYPES` son conjuntos **distintos** (no subconjunto), de modo que un evento puramente de cliente no se eco-difunde al admin y viceversa. Incluye `event_id` UUID + ring-buffer (`deque(maxlen=100)`) para replay vía `Last-Event-ID`.
2. **`audit_log` 3-way OR** (Sub-atom 5.A): cada mutación relevante emite un evento con `project_id` + `client_id` (o ambos NULL para la propia Fulkro), encadenado por hash SHA-256 (R6). Es la columna vertebral de la trazabilidad cross-actor.
3. **subscribe-refetch** en el frontend: el hook `useClientProjectEvents` (548 LOC, 27 tipos de evento) escucha el SSE y dispara `invalidateQueries` de TanStack Query → la UI del cliente se actualiza sola cuando el admin avanza el proyecto (categorización, MAGERIT, plan, conexiones cloud, remediaciones, firmas, documentos…).

**El cliente y el admin trabajan sobre el MISMO dato** (mismas tablas, RLS por `project_id`/`client_id`), no sobre copias: el gestor documental (`documents` en MinIO + RLS) lo comparten cliente↔admin. El portal cliente asume single-project (`LIMIT 1`, R27).

### 4.3 Honestidad: las costuras de la sincronización (detalle cap. 09)
- 🔴 **SSE in-memory single-instance**: el dispatcher NO usa Redis pub/sub. Con varias réplicas de backend, un evento emitido en una réplica no llega a los clientes conectados a otra. El multi-instancia está como «futuro» explícito en el docstring → limita el escalado horizontal real.
- 🔴 **Eventos degradados a polling**: `signing.*` y `accompaniment.state.advanced` **no están** en `CLIENTE_EVENT_TYPES`, y el frontend **no envía `Last-Event-ID`** al reconectar → en esos flujos la «sincronización en vivo» cae a refresco/polling y se pierden eventos durante reconexiones. La doc afirma «Pattern #21 replay sostenido»; el backend está listo pero el frontend no lo cierra.
- 🔴 **Copiloto cliente `/coach` roto** (hallazgo HIGH pre-piloto): un `AttributeError` silencioso hace que siempre responda «Todo al día».
- ⚠️ **`FulkroFooter` «cross 4 portales»**: en realidad cubre directamente admin+cliente; los portales token-gated tienen chrome propio y el footer global los excluye.

> En resumen: la **arquitectura de sincronización es correcta y elegante** (SSE + audit_log + refetch, con aislamiento por audiencia), y funciona para el grueso del workflow; pero tiene **costuras concretas** (single-instance, algunos eventos sin wiring de cliente, coach roto) que hay que cerrar antes de un cliente real con varias réplicas.


## 05 · Arquitectura técnica

### 5.1 Stack (verificado)
- **Backend**: Python 3.12 · FastAPI ≥0.115 · SQLAlchemy 2.0 async (asyncpg) · Alembic. ~89.000 LOC en **44 motores** (`backend/app/motors/m*/`) + capa core + agentes.
- **Datos**: PostgreSQL 16 con **5 extensiones** — pgvector (embeddings 1024d), **Apache AGE** (grafo, compilado en imagen propia; `--skip-age-kg` por defecto en deploy → grafo NO construido en prod), pgAudit (DDL), pgcrypto (SHA-256), uuid-ossp.
- **Cache/colas**: Redis 7 + Celery (beats reales: backups, renovación, digests, nudges, deadlines art. 33…).
- **Objetos**: MinIO, bucket `fulkro-evidence-worm` con **Object Lock COMPLIANCE 2555 días (7 años)**.
- **Frontend**: Next.js 14 App Router · React · TypeScript · Tailwind · shadcn/ui (~62.000 LOC).
- **IA**: Anthropic SDK (Sonnet/Haiku/Opus) con prompt caching + fastembed e5-large.
- **Proxy/TLS**: Caddy. **Empaquetado**: Docker Compose (dev 3 servicios / prod **10-12** servicios).

### 5.2 Base de datos y multi-tenancy
- **~246 tablas live** (237 con modelo ORM en 78 ficheros + 9 sólo-migración). 253 migraciones, head único `remediation_agent_001`.
- **RLS multi-tenant en ≥66 tablas** (≥136 políticas) en 3 patrones: `project_id`/`client_id` directo, cadena FK vía JOIN al padre, y 3-way OR en `audit_log`. Mixin principal `FullMixin` (UUID PK + timestamps + soft-delete) en 141 de 237 clases.
- **`audit_log` inmutable R6**: `seq` BIGSERIAL + **hash-chain SHA-256** vía trigger PL/pgSQL bajo `pg_advisory_xact_lock`; triggers que rechazan UPDATE/DELETE; reforzado además por `REVOKE UPDATE,DELETE` a nivel de privilegio. ⚠️ La doc a veces dice «Ed25519» para el audit_log — es **SHA-256**; Ed25519 vive en la firma de PDF (M05).
- **Hardening de roles (2026-06-07)**: `fulkro_app` es **NOSUPERUSER** y sujeto a RLS; `fulkro_app_bypassrls` (BYPASSRLS, sin login) se asume vía `SET LOCAL ROLE` en ~16 puntos para vistas cross-tenant legítimas; `fulkro_migrate` (DDL). Se cerró la escalada a superuser previa (`REVOKE fulkro FROM fulkro_app`).

### 5.3 Autenticación y seguridad (M12 + auth)
- **Admin (Marcos)**: WebAuthn (Yubikey FIDO2) **o** TOTP, MFA obligatorio en 2 pasos antes de emitir la cookie de sesión (8 h). JWT EdDSA Ed25519. R4 cumplido (en prod `APP_ENV=production` desactiva el fallback dev).
- **Cliente**: pool separado (ADR-013 doble pool), JWT Ed25519, login email+password con MFA (TOTP o email-OTP), lockout brute-force.
- **Magic-links Ed25519**: el token NUNCA se guarda en BD (sólo su SHA-256); OTP por canal separado; **37 purposes reales** (⚠️ la doc dice «23»). Clave Ed25519 propia (`FULKRO_ML_PRIVATE_KEY`, separada de la de sesión).
- **CSRF triple-binding** (header == claim JWT == cookie), **prompt-injection guard** determinista (8 categorías), rate-limit dual (IP + per-user), CSP+HSTS, body-limit 100 MB. Un *global dependency* (`authenticate_request`) cubre los ~262 endpoints mutantes con whitelist de públicos.

### 5.4 La capa API
`main.py` (1.003 LOC) monta **194 routers**; ~**1.191 decoradores HTTP** reales (⚠️ la doc dice «~879» — la diferencia son motores añadidos después: remediation, audit_accompaniment, siem, M8 v2, billing ampliado). OpenAPI deshabilitado en prod. Las correcciones de seguridad 2026-06-07 (bypass cross-tenant en `audit_search`/`operations`) están aplicadas con `require_owner` a nivel router.

### 5.5 Core transversal
SSE dispatcher (cap. 04), `emit_audit_log` (writer DRY que reemplaza el INSERT inline de ≥7 motores), `signing_keys` (política env-PEM > fichero > dev, fail-fast en prod — fix P0-1 contra clave efímera por recreación de contenedor), cifrado MultiFernet rotation-aware, EmailSender (3 backends), PDFRenderer (docxtpl + LibreOffice headless), timestamping RFC 3161 best-effort, branding por cliente, validación de uploads por magic-bytes.

> **Veredicto de arquitectura**: sólida y coherente — multi-tenant real con RLS fail-closed, trazabilidad criptográfica, doble pool, hardening de roles aplicado. Las dos limitaciones estructurales a vigilar: **SSE single-instance** (no escala horizontal) y **AGE desactivado en prod** (el «grafo de conocimiento» que la doc presume no se construye; se usa PKG-lite con traversals SQL ≤3 hops).


## 06 · Inteligencia artificial, copilotos y MCP/pentest

### 6.1 Principio rector: el LLM nunca decide la norma
Tres reglas inviolables verificadas en `COMMON_HEADER` y en cada clase de agente: **R1** (motores deterministas > LLM para decisiones normativas — categorización, riesgo, DdA, pricing son funciones puras), **R2** (citas obligatorias RD 311/2022 / CCN-STIC / Anexo II), **R3** (temperatura ≤ 0.2). El LLM **enriquece y asiste; nunca decide solo** y siempre tiene fallback determinista.

### 6.2 Los agentes (`backend/app/agents/registry.py`)
La doc habla de «31 agentes»; el código tiene **31 IDs históricos pero ~14 agentes realmente vivos** + 1 scaffolding (el resto: deprecated, externalizados a motor, o reservados). Vivos verificados: A2 pliegos, A4 (E-090), A6 contratos, A11 auditor virtual, A12 coach cliente, A14 copiloto RAG, A17 cualificador, A18 reunión en vivo, A19 propuestas, A20 negociador, A21 detector de discrepancias (determinista SQL + wrapper LLM), A27 clasificador IDMS, A31 enriquecedor DdA.
- **Modelos por agente** (verificados): Opus 4.7 en A11/A19; Haiku 4.5 en A27; Sonnet 4.5/4.6 en el resto; A21 determinista (T=0). ⚠️ El entorno corre **Opus 4.8** pero no hay alias 4.8 en `_MODEL_ALIAS_MAP` (los agentes están anclados a 4.7) y los model-ids de la doc no coinciden con el código.
- ⚠️ Bug latente: `api.py._AGENT_CLASSES` referencia nombres de clase erróneos para ~9 agentes → el endpoint genérico `/invoke` da 404 para ellos (no afecta a prod: los flujos reales usan endpoints shortcut que importan la clase correcta).
- ⚠️ `AgentBase._call_llm` degrada a respuesta `[MOCK]` silenciosa sin API key → riesgo de placeholder en prod si falla la red/clave.

### 6.3 El copiloto (A14 + suite, 3 superficies)
Un único pipeline RAG (`detect_filters → hybrid_search top-5 → build_system_prompt(role) → LLM → citation_validator → LLMInteractionLog`) sirve a **tres superficies**: admin RAG (Sonnet 4.5), admin persona (Sonnet 4.6) y cliente (Haiku 4.5). Con **memoria N6** por proyecto (admin) y por `client_id+project_id` (cliente), personas YAML, rate-limit derivado de `LLMInteractionLog` (sin tabla nueva, ADR-025), y un bloque de **estado del workflow en vivo** filtrado por rol. Enforcement diferencial: R29 (fallback total ante 10 patrones coercitivos en cliente) vs R30 (enriquecimiento defensivo en admin). Grounding contra alucinación: si la confianza < 0.45 → prompt anti-alucinación que apunta a CCN-CERT/BOE/AEPD. `SYSTEM_KNOWLEDGE` se autogenera del código (nav real de portales) con test anti-drift.

### 6.4 RAG y corpus normativo (M11/corpus)
**66 docs** en el catálogo (27 ingestados, resto pending). Pipeline 3 etapas: BM25 (GIN español) + pgvector coseno (HNSW) + RRF. Embeddings fastembed `intfloat/multilingual-e5-large` 1024d (in-process desde 2026-06-10; el contenedor TEI fue eliminado). El parser de RD 311/2022 genera 73 chunks de medida (1 por medida). 🔴 El **CCN-STIC 809** está `pending_manual` → el copiloto no puede fundamentar el cierre BÁSICA hasta que se ingeste.

### 6.5 MCP / pentest (M8 autopilot)
- **14 servidores MCP** como `server.py` reales (scope_enforcer, recon, vulnscan, webpentest, infra, config, cloud, apisec, sast, mobile, wireless, cracking, phishing, redteam), protocolo JSON-RPC 2.0 sobre stdio.
- Flag central **`USE_MCP_REAL`** (default FALSE): en dev devuelve resultados simulados deterministas honestos (`{_simulated:True}`, no finge cobertura — `assets_scanned=0` + `partial_run=True`). **Reales validados empíricamente** (`docs/mcps/FUNCTIONAL_VERIFICATION.md`): Prowler, Nuclei, Trivy, Lynis, Gophish (5/6); ScoutSuite y OpenVAS quedan en defer honesto. ⚠️ La doc dice «3 reales (Prowler+ScoutSuite+OpenVAS)» — inexacto.
- **Mappings CIS/CVE → ENS Anexo II**: ~37 CVEs explícitos (Log4Shell, ProxyShell, EternalBlue, XZ backdoor…) + ~18 patrones + familias CIS/NVT (⚠️ la doc dice «88»; el agregado real ronda 55 explícitos + reglas de familia). La capa semántica pgvector→ENS es **stub permanente** (`return []`, «Future Checkpoint 3+»).

### 6.6 M8 Autopilot v2.0 — el pentest serio (cap. 26-27)
Production-grade (~18.500 LOC): pipeline ZFP de **5 gates** (dedup → filtro FP → cross-tool → re-test quirúrgico → clasificación), **Finding canónico**, agente de triage **Opus 4.8 (T=0) puramente ADVISORY** (su veredicto NUNCA baja la severidad de un Finding — sólo verificación activa determinista u override humano puede), **anti prompt-injection** (el dato del objetivo se trata como dato, nunca como instrucción; un intento de manipulación se eleva como Finding propio), evidencia `m8_evidence_records` **append-only** espejada al audit_log R6, sesión efímera HMAC (zero standing access, TTL 8 h) y **kill-switch real** (<5 s, mata el grupo de procesos). Severidad = `max(suelo determinista, CVSS/EPSS)` — sólo puede subir.

> **Veredicto IA/MCP**: arquitectura de IA **madura y honesta** — determinismo donde importa, citas obligatorias, fallback, anti-alucinación y anti-inyección reales. El M8 es lo más sofisticado del repo. Los flecos son de doc (model-ids, nº de agentes, «88 mappings») y de activación (binarios de pentest reales sólo con `USE_MCP_REAL` en Hetzner).


## 07 · El compliance propio de Fulkro (dogfooding R7)

Una de las apuestas más distintivas: **Fulkro cumple el ENS sobre sí misma** y monitoriza su propio cumplimiento normativo (R7 «la plataforma cumple ENS Medio sobre sí misma»). Esto vive en dos motores transversales + un Trust Center público, y es **real, no decorativo**.

### 7.1 `m_compliance` — el ciclo RGPD propio
Cubre el ciclo de derechos y obligaciones de Fulkro como responsable de tratamiento:
- **Art. 15** (acceso → ZIP), **Art. 17** (supresión → *tombstone* in-place: `email→anonymised_<uuid>`, `full_name→Eliminado`, DNI/WhatsApp NULL, **preservando el `audit_log`** por la retención de 7 años del ENS), **Art. 20** (portabilidad → JSON-LD), **Art. 30** (RoPA + Excel formato AEPD), **Art. 33/34** (workflow de brecha 72 h con email real a `notificaciones@aepd.es`).
- Erasure idempotente; el `audit_log` NUNCA se borra.

### 7.2 `m_compliance_monitor` — el semáforo de cumplimiento
- **21 checks async funcionales reales** (no stubs) en `CHECK_REGISTRY`, con semáforo de 4 estados (green/yellow/red/unknown), alerta tras 3 `unknown` consecutivos y auto-resolución al volver a verde.
- **7 plugins de norma** registrados por patrón Open/Closed con auto-descubrimiento: **ENS RD 311/2022, NIS2, ISO 27001:2022, RGPD, LOPDGDD, LSSI, cookies AEPD**.
- Checks ENS de dogfooding directos sobre la propia plataforma: `op.exp.8` (continuidad del audit_log), `op.exp.10` (integridad de backups), `op.acc.4` (% de cobertura RLS), `op.acc.5/6` (enforcement MFA), `op.mon.1/3` (detección de intrusión: presencia de fail2ban/auditd), `mp.s.2` (expiración del cert SSL).
- **4 tareas Celery** con beat (diaria 07:30, semanal, mensual, trimestral); cada una sincroniza el registry antes del batch.
- **Auto-trazabilidad genuina**: los propios checks y reports emiten al `audit_log` con `project_id=NULL, client_id=NULL` (la propia Fulkro como «tenant» especial vía 3-way OR). Sin RLS en estas tablas — correcto, son datos de la plataforma, no de clientes.

### 7.3 Trust Center público
`/legal/compliance/status` expone en vivo (API real, no mock): score por norma, nº de sub-procesadores (Art. 28.2 con consent gate idempotente), última brecha (sólo tras notificación AEPD) y salud global. Acompañado de páginas legales completas: privacy (Art. 13-14 RGPD), cookies (banner AEPD 2020 de 3 botones), derechos-RGPD, plantilla DPA (DOCX), sub-procesadores, términos.

### 7.4 Honestidad
- ⚠️ La doc no documenta los 21 checks ni el sistema de 7 plugins individualmente — el subsistema es **más rico** que su resumen.
- 🔴 `Future-1.E.compliance-reports-pdf-export`: **confirmado que NO existe** export PDF — sólo MD + JSON + Excel RoPA.
- ⚠️ `op.exp.8` cliente: los checks `op.mon` dependen de fail2ban/auditd, que se afirman activos en producción pero **no tienen ficheros de configuración en el repo** (config manual en Hetzner, no IaC).
- 🔴 La placa de identidad fiscal (CIF del consultor) está como placeholder «pendiente alta autónomo» en varios sitios — no registrada en BD ni código (cap. 09).

> **Veredicto**: el compliance propio es un diferenciador **real y funcional** (21 checks + 7 normas + RGPD completo + Trust Center vivo), coherente con vender ENS «predicando con el ejemplo». Le falta el export PDF y formalizar el hardening del host como código.


## 08 · Estado de producción, pilotos y despliegue

### 8.1 ¿Está «cerrado»? Sí, con frontera honesta
El informe de aceptación (`docs/ACCEPTANCE_CLOSED_PRODUCT.md`, 2026-06-08) declara FULKRO **producto cerrado**, y la auditoría lo confirma empíricamente:
- **Backend: ~5.956 tests PASS / 0 fallos / 101 skipped** sobre BD reconstruida (`build_test_db.sh` → ~242 tablas). LLM sellado por defecto (`FULKRO_RUN_LLM_TESTS=0` → mock).
- **Frontend: `tsc --noEmit` exit 0** (0 errores de tipos).
- **ENS 52/68/73** verificado en código (cap. 02).
- **E2E Playwright: 230 PASS / 147 «fallos»** — y aquí la honestidad importa: los 147 son **deuda de specs** (selectores viejos, features eliminadas que los tests aún asertan, test-ids renombrados), **NO bugs de producto** (las páginas renderizan 200). Llevar la E2E a verde es una campaña de limpieza de tests, no de producto. Además: el gate CI automático en PR sólo corre los 97 specs de *polish* a11y; los 202 e2e funcionales son `workflow_dispatch` (manual), y `mypy` está en `continue-on-error` → técnicamente un PR puede mergear a main sin pasar tests funcionales.

### 8.2 Despliegue (Hetzner) — turnkey y desplegado
- **Stack prod**: `docker-compose.prod.yml` con **10-12 servicios** (postgres custom con pgvector+AGE+pgAudit+pgBackRest, redis, provision one-shot, backend, celery-worker, celery-beat, frontend, minio, minio-init, clamav, caddy) + red interna `fulkro-net` (PG/Redis/MinIO **sin exposición al host**).
- **Provisión idempotente** (`provision-entrypoint.sh`, orden inviolable de 7 pasos: extensiones → roles → `alembic upgrade head` → seed → `REVOKE UPDATE/DELETE` audit_log).
- **CD GitHub → Hetzner**: push a `main` → `git pull --ff-only` + `docker compose build` + `up -d` vía SSH Ed25519 (sin zero-downtime).
- **Gate post-deploy** (`verify-deploy.sh`, 13 checks: roles, head Alembic, ENS 52/68/73, R6, WORM, servicios, HTTP 200).
- **Backups**: pg_dump diario + pgBackRest (repo1 local activo; ⚠️ repo2 S3 offsite **comentado**) + MinIO `backup-vault`. R8 (restore-test mensual) está cableado en Celery pero la tarea real es **stub** («Pending Hetzner provisioning»).
- **La auto-remediación ADR-055** (motor `m_remediation`) está **desplegada en prod (2026-06-13)**, gateada con kill-switch de 3 capas en OFF por defecto (cap. 47).

### 8.3 Los pilotos — la verdad
**No hay todavía un cliente piloto pagador real onboardeado.** La misión declarada del proyecto es precisamente **conseguir el primer cliente piloto pagador** (categoría MEDIA, 10.700 € + retainer R_STD 700 €/mes). El producto está cerrado y desplegado a la espera de ese primer cliente. Toda la validación E2E corre sobre un **proyecto demo sintético sembrado** (`_dev/seed-rich-demo-project`, UUID determinista `00000000-…-001`, datos ricos ALTA: 8 activos MAGERIT + 12 riesgos + 73 entradas DdA) bajo un cliente dedicado aislado — no es un cliente real.

### 8.4 Fronteras 🔒 Hetzner-only (lo que sólo se valida/activa en el servidor real)
TLS Let's Encrypt + dominio `fulkro.es` · Yubikey/WebAuthn (R4) · `ANTHROPIC_API_KEY` real (sin ella los copilotos no responden) · SMTP real (magic-links + notificaciones) · fastembed con modelo cargado · MinIO WORM runtime (Object Lock real) · ClamAV freshclam · MCP-pentest `USE_MCP_REAL` (binarios reales) · pgBackRest físico/PITR. Los 5 pasos manuales de Marcos: contratar servidor, DNS, enrolar Yubikey, pegar secretos reales (ANTHROPIC/SMTP), cuenta SMTP.

> **Veredicto de estado**: producto **cerrado, verde en backend, desplegado en producción**, con E2E que es deuda de test y con la última gran pieza (auto-remediación) ya en prod. Lo que falta es **estrictamente operativo de servidor** + **el primer cliente real** que ejercite el ciclo de punta a punta.


## 09 · Veredicto honesto — ¿hace absolutamente todo al 100%?

**Respuesta directa**: No al 100% absoluto, pero **mucho más completo de lo que la propia documentación sugiere**. FULKRO es una plataforma ENS **excepcionalmente ambiciosa y, en su grueso, real y funcional** — no un prototipo ni un *vaporware*. Cubre el ciclo de vida ENS de extremo a extremo con motores deterministas, trazabilidad criptográfica y una capa de producción desplegada. Pero tiene **flecos concretos** que hay que conocer antes de cerrar una certificación real, y una **doc que se quedó corta** frente al código.

### 9.1 Lo que SÍ hace al 100% (✅ verificado en código)
- **Catálogo ENS fiel al BOE**: 52/68/73 medidas transcritas literalmente, con tests que blindan la regresión.
- **Categorización, MAGERIT v3, DdA, GAP, obligaciones, pricing**: deterministas, sin LLM, trazables (R1).
- **Fábrica documental** (116 plantillas + 16 Excel) con firma Ed25519 + PDF + WORM.
- **Firma electrónica** (canvas Ed25519 TIER 1 eIDAS Art. 25.1 + OTP step-up + hash-chain + sello RFC 3161).
- **Audit_log inmutable** (hash-chain SHA-256 + triggers + REVOKE por privilegio): R6 sólido.
- **M8 Pentest Autopilot v2.0**: ZFP 5 gates, triage advisory, anti-inyección, evidencia append-only, kill-switch. Lo más maduro del repo.
- **Multi-tenancy RLS fail-closed**, doble pool, WebAuthn/TOTP/magic-links, CSRF triple-binding, hardening de roles.
- **Compliance propio** (RGPD completo + 21 checks + 7 normas + Trust Center vivo).
- **Conformidad/renovación** (M27): FSM 16+11+9 estados, distintivo CCN-STIC 809, DPC anual art. 25, adapters LUCIA/INES/PILAR.
- **Despliegue prod Hetzner** turnkey + CD + auto-remediación ADR-055 en producción.

### 9.2 Lo que es PARCIAL o está roto (🟡/🔴 — los flecos que faltan para «todo»)
| # | Fleco | Impacto |
|---|---|---|
| 🔴 | **Cierre BÁSICA bloqueado** | Firmante no-RSEG + CCN-STIC 809 (AMPARO) sin ingestar → no se cierra una BÁSICA real hoy |
| 🔴 | **`alta_productos_cpstic` stub permanente** (`return False`) | Un proyecto ALTA nunca supera el gate de CONFORMIDAD automáticamente |
| 🔴 | **Copiloto cliente `/coach` roto** | `AttributeError` silencioso → siempre «Todo al día» |
| 🔴 | **SSE single-instance** | No hay Redis pub/sub → no escala a varias réplicas; `signing.*`/`accompaniment` degradados a polling |
| 🔴 | **R8 restore-test mensual = stub** | La «prueba de backup» Celery sólo loguea «Pending Hetzner» (no restaura) |
| 🔴 | **Agente on-prem de remediación inexistente** | `agent/fulkro_remediation_agent.py` y `playbooks.py` que la doc cita **no existen** en el repo (sólo el protocolo server-side) |
| 🟡 | **Verifactu AAPP** (XAdES/FACE), **TSA cadena cert**, **PILAR `.mgr`** | Estructuras completas pero stubs/sin formato nativo → requieren paso manual o cert real |
| 🟡 | **`op.exp.8` logs del cliente** ausente; **semáforo per-medida M04** parcial | Cobertura incompleta de operación del cliente |
| 🟡 | **Mocks en prod** | `useCreateLead`/`useLeads` (mock-fallback), `LeadDrawer.invokeAgent` (setTimeout simulado), `LegacyDocumentSignFlow` mock activo en `/sign` — contradicen R24 «0 mocks» |
| 🟡 | **Motores sin `audit_log`** | M16, M22, M29/30/31, M10 core, CRUD de M04/M05 NO emiten audit_log canónico (confían en triggers BD) → gaps de trazabilidad ENAC |
| 🟡 | **Riesgos de clave efímera** | Sin `FULKRO_REMEDIATION_SIGNING_KEY` en prod, el server genera Ed25519 efímera (cualquier restart invalida los agentes enrolados) |
| 🟡 | **CIF del consultor placeholder** | «pendiente alta autónomo» en /privacy, /imprint, identidad fiscal |

### 9.3 La doc miente por defecto, no por exceso (⚠️ discrepancias doc-vs-código)
Casi todas las discrepancias son la **doc quedándose corta** frente a un código que creció:
- Endpoints: «~879» → **~1.191** reales. Tablas: «~184» → **~246**. Tests: «~353 ficheros» → **554**. Migraciones: «160» → **253**. Specs E2E: «140+» → **299**.
- Agentes: «31» → **~14 vivos**. Plantillas: «96/104» → **116**. Magic-link purposes: «23» → **37**. SignableTypes: «11» → **18**.
- **audit_log es SHA-256, no Ed25519** (Ed25519 es para la firma de PDF). Model-ids de la doc (Sonnet 4.6/Opus 4.7) ≠ código (Sonnet 4.5/Opus 4.8). «88 mappings CIS/CVE» → ~55 explícitos. «navegación admin tri-pestaña» descrita no es la implementada (el Sidebar TOP_NAV de 11 ítems siempre se renderiza). m_legal descrito «dormant» está **activo**. m_live_records descrito «sin frontend» **tiene** `/client-portal/registros`.
- Cifras de motores sin consenso interno: CLAUDE.md «42», README «44», otra auditoría «47». El conteo real de directorios es **44**.

### 9.4 Conclusión
FULKRO **NO hace literalmente todo de la implantación ENS al 100% de forma totalmente automática y sin pasos manuales** — ningún producto serio lo haría, y los flecos de §9.2 lo confirman. Pero **SÍ es una plataforma ENS integral, profunda y, en su núcleo, terminada y desplegada**, que cubre todo el ciclo (comercial → onboarding → riesgos → DdA → documentación → evidencias → pentest → dossier ENAC → conformidad → retainer), con compliance propio y portales sincronizados. La distancia hasta «todo al 100%» es: **(a)** cerrar ~6 flecos funcionales concretos (BÁSICA, gate ALTA, coach, SSE multi-instancia, restore-test real, agente on-prem), **(b)** activar las piezas 🔒 Hetzner-only, y **(c)** ejercitarla con el primer cliente piloto real. La calidad de ingeniería (determinismo trazable, hash-chain, anti-inyección, RLS fail-closed, kill-switches) está **muy por encima** de lo habitual en una herramienta de consultoría unipersonal.


## 10 - Core - Workflow engine ENS (gates, fases, bloqueo, plantillas)

### Propósito

Orquesta el ciclo ENS completo por proyecto (pre-venta → retainer). **Sin almacenamiento propio** (ADR-025): deriva estado en tiempo real desde datos de motores M01-M31. Aplica gates de secuencia que impiden saltar artefactos ENS fuera de orden.

---

### Ficheros clave (1.083 LOC core + 1.656 LOC motor)

- `core/workflow_phase.py` (80): `WorkflowPhase` 10 fases + `ordered()`/`previous()`/`next()`.
- `core/workflow_gates.py` (349): 7 gates async · `WorkflowGateError` · raw SQL sin imports ORM.
- `core/workflow_blocking_service.py` (249): `WorkflowBlockingService` feature-flags YAML → blocking issues.
- `core/workflow_templates.py` (250): `ACTION_TEMPLATES` + `TASK_TEMPLATES` constants Python.
- `core/workflow_state/phase.py` (263): `get_current_phase()` + `_derive_phase_cascade()` 9 EXISTS.
- `core/workflow_state/signals.py` (547): 35 `_signal_*` SQL atómicos + `_TASK_SIGNAL_CHECKERS`.
- `core/workflow_state/views.py` (260): `get_next_actions`, `get_phase_progress`, `get_phase_tasks`, roadmap.
- `motors/m_workflow_engine/` (1.656): view composer enriquecido M21 + `ClientTask` + cross-actor state machine.

---

### Las 10 fases (ADR-026 + SAN-C MB-11.1)

```
PRE_VENTA → ONBOARDING → DIAGNOSTICO → ANALISIS_RIESGOS →
ADECUACION → IMPLANTACION → DDA_FINAL → VERIFICACION →
CONFORMIDAD → RETAINER_CIERRE
```

Persistencia: `projects.fase VARCHAR(50) NOT NULL` (migración `workflow_phase_10_canonical`). `ANALISIS_RIESGOS` y `DDA_FINAL` son las 2 sub-fases nuevas MB-11.1.

---

### `get_current_phase` — estrategia híbrida

1. **Primario**: `projects.fase` persisted.
2. **Fallback CASCADE** (`_derive_phase_cascade`): 9 EXISTS descendentes (retainer → … → pre_venta). Filtra data post último `phase_changed` event (ISSUE-W3 · `COALESCE(MAX(event_date),'1970-01-01')`). Trigger `tg_projects_phase_changed` emite el evento.

**Bug resuelto**: JOIN original con tabla `measures` inexistente → `UndefinedTableError`. Simplificado a `dda_entries.project_id`. **ISSUE-W5 (abierto)**: `conformity_submissions`/`diagnosis_runs` sin `deleted_at`.

---

### 7 Gates (`workflow_gates.py`)

`WorkflowGateError(gate, message)` mapeado globalmente a HTTP 409. Env var `FULKRO_SKIP_WORKFLOW_GATES=1` desactiva todos (conftest).

| # | Función | Precondición | Motor invocador |
|---|---|---|---|
| 1 | `require_signed_categorization` | `categorizations.aprobado_por IS NOT NULL` | M03 DdA |
| 2 | `require_frozen_dda[_if_needed]` | `dda_entries.fecha_aprobacion ≥1` · solo para `{politica,procedimiento,entregable}` | M06 |
| 3 | `require_complete_audit_prep` | `audit_preparation_runs.estado IN (completada,completed,ready,dossier_ready)` | M25 |
| 4 | `require_some_evidence` | `COUNT(evidence) >= minimum` | M09 |
| 5 | `require_magerit_analysis` | `magerit_analysis` existe | M05 obligations |
| 6 | `require_pentest_authorisation` | `magic_links.tipo_operacion='autorizar_accion_tecnica' AND usos>0` | M08 |
| 7 | `require_clean_audit_sim` | Simulacro ejecutado + 0 `critical_gaps` para ENAC/Declaración (override admin `allow_open_nc=True`) | m_audit_accompaniment |

---

### Bloqueo de fase (`workflow_blocking_service.py`)

`check_can_transition(project_id, target_phase_int)` → `WorkflowBlockingResult`. Todas las features declaran `blocks_phase_transition_if_missing: 9` (CONFORMIDAD) en el YAML.

| Feature key | Verificación real | Estado |
|---|---|---|
| `media_auditor_enac` | `ProjectRoleAssignment.role_code IN (auditor,auditor_externo)` | OK |
| `media_vuln_scan` | `VerificationRun.status='completed'` | OK |
| `alta_pentest_cpstic` | `VerificationRun` ALTO + `mode LIKE 'external_%'` + completed | OK |
| `alta_criptografia_807` | `Evidence.evidence_type_id='criptografia_807'` vigente | OK |
| `alta_productos_cpstic` | **STUB hardcoded `return False`** — `Asset.cpstic_certified` no existe en schema | **Bloqueante permanente ALTA** |

Endpoint: `GET /api/v1/projects/{project_id}/workflow/can-transition/{target_phase}` (`require_owner`). `POST /transition` diferido (DEC-5 MB-18).

---

### Plantillas y signals

`ACTION_TEMPLATES`: 2-3 acciones por fase con deeplink y `estimated_minutes`. `TASK_TEMPLATES`: 4-6 tareas por fase · **39 total · 35 con signal · 4 `manual_tracking`** (propuesta, contrato, gap analysis M04, sign-off). Signals críticos: `dda_frozen` → `dda_project_signatures` (NO `dda_entries`); `categorization_signed` → `signature_magic_link_id IS NOT NULL`. `_resolve_task_status` retorna `manual_tracking` si signal=None; warning log si signal sin checker.

---

### Endpoints REST (`require_owner` · admin)

- `GET /api/v1/workflow/current-phase/{project_id}` → `WorkflowPhase`
- `GET /api/v1/workflow/next-actions/{project_id}?limit=5` → `list[NextAction]`
- `GET /api/v1/workflow/phase-progress/{project_id}/{phase}` → `PhaseProgress`
- `GET /api/v1/workflow/phase-tasks/{project_id}/{phase}` → `list[TaskItem]`
- `GET /api/v1/workflow/roadmap/{project_id}` → `WorkflowRoadmap`
- `GET /api/v1/projects/{id}/workflow/can-transition/{target}` → `WorkflowBlockingResult`
- `m_workflow_engine`: 4 admin + 5 reader + 1 cliente (workflow-guide). `portal_workflow.py` + `workflows_simple.py`: 501 LOC adicionales. RLS: `_set_project_rls()` llama `get_project_owner(:pid)` (evita 404 espurios).

---

### Medidas ENS cubiertas

`org.1` (gate 2: políticas post DdA) · `op.exp.1` (gate 1: categorización firmada) · `op.pl.1/op.pl.2` (fases implantacion+dda_final+verificacion) · `op.pl.5` (gate 5: MAGERIT) · `op.exp.9/op.exp.10` (features pentest CPSTIC + criptografía CCN-STIC 807) · `op.acc.5/op.acc.6` (features auditor ENAC + vuln-scan) · `mp.s.4/op.exp.3` (gate 4: evidencias) · `mp.com.1` (gate 7: simulacro pre-ENAC 0 NC mayores).

---

### Tests (`backend/tests/core/test_workflow_*.py` · 1.251 LOC)

`test_workflow_phase_10.py` (78) · `test_workflow_gates.py` (91) · `test_workflow_gates_wiring.py` (204) · `test_workflow_blocking.py` (189) · `test_workflow_state.py` (689 — cascade, signals, views, roadmap).

---

### Discrepancias y gotchas

1. **`alta_productos_cpstic` STUB permanente**: proyectos ALTA nunca superan el gate CONFORMIDAD hasta que exista `Asset.cpstic_certified` en schema (DEC-2 ADR-036 DEFER sin fecha).
2. **Docstring `workflow_schemas.py` dice "8 fases"**: el enum tiene 10. Inconsistencia menor.
3. **DDA_FINAL borde concurrente**: la lógica exige "≥1 `implementado` AND NOT ∃ `en_proceso`"; si coexisten ambos estados en un momento de concurrencia, el cascade puede saltar a `DDA_FINAL` prematuramente — no hay serialización con advisory lock.
4. **`sequences.py` nominalmente fuera de scope "workflow"**: es un helper CR-NNN para `ChangeRequest` (M17 + M19), pero vive en `core/`. Funciona correctamente.
5. **`projects.fase` actualización no garantizada por los motores**: si un motor avanza datos (crea DdA) sin actualizar `projects.fase`, el cascade primario devuelve el valor persisted desactualizado. La actualización de `projects.fase` es responsabilidad del caller (no hay trigger automático que la escriba).

---

### Veredicto: **completo**

Ciclo BÁSICA/MEDIA 100% implementado con 7 gates, 35 signals atómicas, 10 fases, bloqueo declarativo YAML y view composer sin almacenamiento propio. Stub crítico: `alta_productos_cpstic` bloquea ALTA en CONFORMIDAD indefinidamente.


## 11 - Core - Infraestructura (SSE, audit hash-chain, storage, cifrado, email, PDF, timestamping)

**Dominio**: capa transversal `backend/app/core/` reutilizada por los 40+ motores. Leídos íntegros todos los ficheros + verificación cruzada de la migración `d4f8b2a90001`.

### Ficheros clave
- `sse_dispatcher.py` — pub-sub in-memory por canal `project:{uuid}` + `event_id` UUID + ring-buffer `deque(maxlen=100)` (replay Last-Event-ID); sets de audiencia admin/cliente + `event_matches_audience`.
- `audit_writer.py` — `emit_audit_log()`: INSERT central DRY (ex-≥7 motores), `flush` (no commit), best-effort, NO setea seq/hash (los pone el trigger).
- `dashboard_events.py` / `document_events.py` — listeners SQLAlchemy que emiten SOLO en `after_commit` (anti evento-fantasma).
- `storage/minio_client.py` — singleton; `put_object` con retención COMPLIANCE WORM + degradación graceful si el bucket no tiene Object Lock (dev).
- `signing_keys.py` — carga Ed25519 env-PEM > fichero > (dev genera/persiste · prod fail-fast). **FIX P0-1** (evita clave efímera por recreación de contenedor).
- `encryption/` — MultiFernet rotation-aware + TypeDecorator `EncryptedText` NULL-safe.
- `email/sender.py` — 3 backends (smtp/postmark_api/mock) + `email_log` + retry 2/8/32s + CC real.
- `timestamping/rfc3161.py` — sello RFC 3161 best-effort (default OFF).
- `pdf_renderer.py` — docxtpl → LibreOffice headless → PDF. `branding/pdf_context.py` materializa logo cliente desde MinIO.
- `legal.py`/`category_naming.py`/`cif_norm.py`/`fiscal_identity.py` — AAPP por CIF, puente BASICA↔BASICO, identidad fiscal canónica anti-falso-verde.

### Audit hash-chain R6 (verificado)
- Trigger `fn_audit_log_hash_chain` (mig. `d4f8b2a90001`): `pg_advisory_xact_lock('audit_log_chain')` serializa; `hash_current = sha256(prev || campos)`. Es **SHA-256, NO Ed25519** (Ed25519 vive en M05 PDF).
- `fn_audit_log_immutable` RAISE EXCEPTION en UPDATE/DELETE → append-only por trigger (+ REVOKE por privilegio).
- **3-way OR (Sub-atom 5.A)**: `project_id`/`client_id` opcionales; policy `audit_log_isolation = project OR client OR (ambos NULL)`. El bypass admin va por ROL `fulkro_app_bypassrls` (BYPASSRLS), no por OR permisivo. `llm_interaction_log` exenta de RLS deliberadamente.

### SSE realtime (audiencias)
Canal por proyecto; queue `maxsize=100` (drop+warning). **Dos sets distintos que se solapan** (no subconjunto): `ADMIN_EVENT_TYPES` vs `CLIENTE_EVENT_TYPES`. Eventos puramente cliente (client_notification, m01/m02 sync, cloud_remediation, signing, plan, accompaniment, pentest, continuidad) NO se eco-difunden a admin. Filtros cross-actor por `primary_actor`/`sender_type`/`audience`; `document.uploaded` filtra `interno` para cliente.

### Storage / WORM
8 buckets canónicos (documents, evidence, **evidence-worm**, exports, admin-assets, backup-vault, corpus). `put_object` calcula sha256 + soporta `worm_retention_days` (COMPLIANCE) con fallback durable en dev. El Object Lock real se provisiona fuera de Python (vía `mc`, deploy-time).

### Cifrado / firma / timestamping / email / PDF
Master key: env (prod) o derivada SHA256 de `FULKRO_AUTH_PRIVATE_KEY` (dev, warning); MultiFernet para rotación. `signing_keys` prod fail-fast. RFC 3161: verifica message-imprint pero NO la cadena de certificación TSA (honest boundary). EmailSender persiste en `email_log` bajo `SET LOCAL ROLE fulkro_app_bypassrls`; mock in-memory env-gated para E2E. PDFRenderer requiere LibreOffice en runtime (Hetzner).

### Medidas ENS (transversal)
`op.exp.10`/`mp.info.4` (claves cripto: master_key, signing_keys, at-rest) · `op.exp.8`/`org.4` (registro inviolable hash-chain R6) · `mp.info.*` (integridad/sellado, sha256). E-012 vía PDFRenderer+branding.

### Veredicto por componente
Audit writer + hash-chain R6 ✅ · SSE + audiencias ✅ (in-memory single-instance) · MinIO+WORM ✅ (prod-dependiente) · cifrado ✅ · signing_keys ✅ · email ✅ · RFC 3161 🟡 (best-effort, no valida cadena TSA) · PDF ✅ (infra-dependiente) · clients service/api ✅.

### Discrepancias docs vs código
1. **Modelos LLM**: doc dice «Sonnet 4.6 + Opus 4.7»; `llm_router.py` usa `claude-sonnet-4-5` / fallback `claude-opus-4-6` (env-overridable). No coinciden.
2. **Hash-chain «Ed25519»**: es **SHA-256** (Ed25519 solo M05 PDF).
3. **WORM «7 años»**: no hay constante en core; la retención la fija el caller y el Object Lock se provisiona en infra (`mc`).
4. **SSE «realtime maduro»**: in-memory single-instance (no Redis pubsub); multi-instance es futuro explícito → limita escalado horizontal.
5. **`BGE_M3_DIMENSIONS`**: nombre legacy; el modelo real es `multilingual-e5-large` (1024d).


## 12 - Auth & Security (WebAuthn, TOTP, magic-links Ed25519, CSRF, RLS, doble pool)

### Alcance leído

`backend/app/auth/` (11 ficheros), `security/llm_prompt_injection_guard.py`, `middleware/` (3), `models/auth.py`, `motors/m12_magic_link/service.py` + `purposes.py`.

### Ficheros clave

- `auth/crypto.py` — Ed25519 JWT (EdDSA), bcrypt rounds=12, `issue_token`/`decode_token`
- `auth/webauthn_svc.py` — fido2 2.x: begin/complete registration + authentication
- `auth/totp_svc.py` — pyotp TOTP 6 dígitos, window ±1 step (±30s drift)
- `auth/service.py` — Session CRUD, lockout (5 fallos→30min), WebAuthn credential upsert
- `auth/global_dep.py` — `authenticate_request`: dispatcher dual-pool + CSRF + audit user
- `auth/dependencies.py` — `require_owner`, `require_client_user`, `require_marcos_or_client`
- `auth/csrf.py` — triple-binding: header + cookie + JWT claim, `hmac.compare_digest`
- `auth/rate_limit.py` — sliding-window IP en BD (5/15min → 429)
- `auth/tenant_scope.py` — `ensure_client_project_scope`: ownership + contexto RLS
- `auth/api.py` — 11 endpoints: login, webauthn/verify, totp/verify, logout, me, register, public-key
- `middleware/csp.py` — CSP + HSTS 2 años + X-Frame-Options DENY + Permissions-Policy
- `security/llm_prompt_injection_guard.py` — 8 categorías regex, bloqueo críticos
- `m12_magic_link/` — JWT EdDSA hash-only BD, OTP canal separado, 38 purposes

---

### Modelo de datos auth (sin RLS — dato global Marcos)

- **`auth_users`**: email (unique), password_hash (bcrypt), role (String 32), is_active, must_change_password, failed_login_attempts, locked_until, last_login_at.
- **`auth_webauthn_credentials`**: credential_id (LargeBinary unique), public_key, sign_count, transports (JSONB), device_name. FK→auth_users CASCADE.
- **`auth_totp_secrets`**: user_id (unique FK), secret (String 64), verified (Bool).
- **`auth_sessions`**: jti (String 64 unique), expires_at, revoked_at, ip_address (INET), user_agent.
- **`auth_login_attempts`**: email, ip_address, success, reason, user_agent. Append-only.

Sin `client_id`/`project_id` → RLS no aplica. Correcto por diseño.

---

### Flujo de autenticación (R4 verificado)

1. **POST /auth/login**: bcrypt verify + rate-limit IP (5/15min→429) + lockout usuario (5→30min). Emite `mfa_ticket` JWT (5min) con WebAuthn state embebido.
2. **POST /auth/webauthn/verify**: fido2 `authenticate_complete`, bump sign_count, emite session JWT (8h). Cookies `fulkro_session` (HttpOnly) + `fulkro_csrf` (JS-readable), `samesite=strict`, `secure=is_production`.
3. **POST /auth/totp/verify**: pyotp verify window±1 → mismas cookies sesión.
4. **Global dep `authenticate_request`**: wired `main.py`. Whitelist 13 exact + 8 prefix (`/api/v1/_dev/`, magic-link consume, contract-signing públicos).

**R4 cumple**: ningún flujo emite cookie de sesión sin 2FA completado.

---

### CSRF triple-binding (ADR-019)

`verify_csrf`: header `x-csrf-token` == JWT claim `csrf` == cookie `fulkro_csrf`, via `hmac.compare_digest`. No-op GET/HEAD/OPTIONS. Centralizado en `global_dep.py` → cobertura automática todos los endpoints.

---

### Doble pool ADR-013 (verificado)

`global_dep.py` discrimina por prefijo `sub` JWT:
- Sin `"client:"` → pool Marcos: `session_is_active(jti)` + `get_user(uuid)`
- `sub.startswith("client:")` → pool cliente: `auth_service_cliente.verify_session(db, token)`

`require_owner`: verifica `user.role == "owner"` contra **BD** (no claims JWT). Cambio de rol en BD surte efecto inmediato.

`require_client_user`: verifica `role_pool == "cliente"` → 403 si Marcos intenta acceder.

**Impersonación soporte**: claim `support=true` → bloquea mutating en chokepoint global. Única excepción: logout propio.

---

### Magic-links Ed25519 (R5)

Motor `m12_magic_link`:
- **38 purposes** reales (código). Key separada `FULKRO_ML_PRIVATE_KEY`.
- Token NUNCA en BD — solo `token_hash` SHA-256. OTP TOTP canal separado. 3 fallos OTP → link invalidado permanente.
- Purposes críticos con `requires_otp=True` + `requires_geo=True`: `FIRMA_CONTRATO`, `APROBACION_PROPUESTA`, `ACEPTACION_RIESGO_RESIDUAL`, `COMUNICACION_INCIDENTE_SEGURIDAD`.
- **Gotcha**: `requires_geo=True` define intención pero **no hay enforcement real** en service layer — campo JSONB `allowed_countries` preparado, no validado.

---

### Tenant scope y RLS

`ensure_client_project_scope`: query `SELECT client_id FROM projects WHERE id=:pid` → 404 si no existe, 403 si no pertenece. Luego `set_tenant_context(db, client_id, project_id)` fija `app.current_client_id`+`app.current_project_id` como config transaccional PostgreSQL → RLS fail-closed (endpoint que olvide llamar → 0 filas, no fuga).

---

### LLM Prompt Injection Guard

Pure functional, 0 side-effects. 8 categorías regex determinista:
- **Critical** (bloquean): `role_manipulation`, `ignore_previous` (EN+ES), `system_extraction`, `delimiter_injection`.
- **Warning/info** (solo flagean): `base64_obfuscation`, `context_bleed`, `excessive_length` (>10k chars).
- `neutralize_context_value()`: limpia vars de contexto antes de interpolar en prompts (control chars, comillas→simples).
- Deuda: false-positive tracking no implementado (`Future-S5.X.llm-pi-policy-tuning`).

---

### Middleware stack

- `CSPMiddleware`: CSP `script-src unsafe-inline unsafe-eval` (Next.js HMR) + HSTS 2 años + X-Frame-Options DENY + Permissions-Policy. Gotcha: unsafe-inline/eval debilita XSS, inevitable con Next.js.
- `BodySizeLimitMiddleware`: 413 pre-lectura si Content-Length > 100MB.
- `MarcosTimesheetMiddleware`: best-effort auto-track hits Marcos (30s ventana, `fulkro_app_bypassrls`).

---

### ENS medidas cubiertas

| Código | Evidencia real |
|---|---|
| **op.acc.1** | email único + bcrypt rounds=12 |
| **op.acc.5** | WebAuthn hardware (Yubikey) + TOTP software; MFA obligatorio pre-cookie |
| **op.acc.6** | RLS fail-closed + `ensure_client_project_scope` + doble-pool separado |
| **op.exp.6** | CSRF triple-binding + cookies HttpOnly/SameSite/Secure |
| **op.exp.10** | Ed25519 key pairs env vars; ephemeral fallback dev con WARNING |
| **mp.s.2** | CSP + HSTS 2 años + X-Frame-Options + Permissions-Policy + BodySizeLimit |
| **mp.info.3** | JWT EdDSA, bcrypt 12, SHA-256 hash-only tokens magic link |
| **org.mon.1** | `auth_login_attempts` append-only + per-user lockout, cross-worker BD |

---

### Discrepancias CLAUDE.md vs código

1. **Magic link purposes**: CLAUDE.md dice "23 purposes". Código real: **38 purposes** (#38 `DIAGNOSTICO_PRECLIENTE`). Desactualizado.
2. **geo_restriction no enforced**: `requires_geo=True` solo en config, sin validación en service layer. Deuda no documentada.

---

### Veredicto: **COMPLETO**

WebAuthn fido2 + TOTP pyotp + CSRF triple-binding centralizado + doble-pool ADR-013 + magic-links Ed25519 hash-only 38 purposes + LLM PI guard determinista + CSP+HSTS+Permissions-Policy. Deuda menor: geo-restriction preparada no enforced, LLM false-positive tracking pendiente.


## 13 - API layer (routers v1, main.py, montaje de motores, censo de endpoints)

### Ficheros clave

| Fichero | Propósito |
|---|---|
| `backend/app/main.py` (1003 LOC) | App creation, 194 `include_router` calls, middleware stack, lifespan, exception handlers |
| `api/v1/health.py` | `GET /api/v1/health` — ping sin auth |
| `api/v1/public_contact.py` | `POST /api/v1/public/contact` — landing, honeypot anti-spam |
| `api/v1/corpus.py` | `GET /corpus/search|stats` — BM25+pgvector (NO auth gate propio, cubierto global dep) |
| `api/v1/projects.py` | 5 GET composer cross-motor (`/projects/{id}/header|summary|timeline|risk-overview|operations`) |
| `api/v1/dashboard.py` | 4 GET admin cockpit (`/dashboard/kpis|my-day|alerts|activity`) require_owner |
| `api/v1/workflow.py` | 5 GET workflow admin require_owner |
| `api/v1/portal_workflow.py` | 4 GET workflow cliente require_client_user |
| `api/v1/sse_api.py` | `GET /projects/{id}/events` SSE admin (heartbeat 30s) |
| `api/v1/sse_client_api.py` | `GET /client-portal/projects/{id}/events` SSE cliente con audience filtering |
| `api/v1/audit_search.py` | `GET /audit/search` cross-motor — **require_owner post-fix 2026-06-07** |
| `api/v1/operations.py` | `GET /admin/operations/*` cross-motor — **require_owner post-fix** |
| `api/v1/action_plans.py` | `GET /projects/{id}/action-plans` aggregator K.3 (M04+M09+M19+A21) |
| `api/v1/mcps.py` | `GET /mcps` catálogo 14 MCPs — datos estáticos, sin gate admin propio |
| `api/v1/mcps_execute.py` | 6 endpoints MCP execution project-scoped require_owner |
| `api/v1/admin_diagnostico_wizard.py` | `POST /admin/diagnostico-wizard` 6-step atomic provisión |
| `api/v1/workflows_simple.py` | `POST /api/v1/workflows/{id}/run` 5 cadenas agentes require_owner |
| `api/v1/admin_copilot_stub.py` | `POST /admin/copilot/chat` stub LLM |
| `api/v1/client_copilot_stub.py` | `POST /client-portal/copilot/chat` stub LLM R29 |

---

### Arquitectura de montaje (main.py)

**194 `include_router` calls** — monolito FastAPI. Tres bloques: importaciones estáticas (líneas 14–357), creación app con global dep (391–401), y montaje secuencial (444–1003). `FastAPI(dependencies=[Depends(authenticate_request)])` cubre TODOS los endpoints; whitelist 13 paths exactos + 9 prefijos en `global_dep.py`. Dos routers sin prefix explícito (`workflows_simple_router`, `m16_portal_router`) lo definen internamente.

**Portales separados** (ADR-013):
- **Admin (Marcos)**: `/api/v1/admin/*`, `/api/v1/projects/*`, `/api/v1/dashboard/*` — `require_owner` (session cookie + CSRF).
- **Portal cliente**: `/api/v1/client-portal/*`, `/api/v1/portal/*` — `require_client_user` (JWT Ed25519).
- **Auditor ENAC**: `/api/v1/auditor-portal/*` — magic-link `AUDITOR_PORTAL_ENAC`.
- **Público**: `/api/v1/public/*`, `/api/v1/health`, `/api/v1/magic-links/by-token/*`, `/api/v1/contract-signing/*`.

---

### Middleware stack (orden de aplicación)

| Middleware | Propósito | ENS |
|---|---|---|
| `TrustedHostMiddleware` (prod) | Anti host-header injection | `op.exp.2` |
| `CORSMiddleware` (dev only) | `allow_origins=["*"]` dev; prod Caddy gestiona CORS | — |
| `BodySizeLimitMiddleware` | 413 si `Content-Length > 100MB` (configurable) | `op.exp.2` |
| `CSPMiddleware` | CSP + X-Frame DENY + nosniff + HSTS 2yr + Permissions-Policy | `mp.s.2` |
| `MarcosTimesheetMiddleware` | Auto-track requests Marcos en timesheet | — |
| Global dep `authenticate_request` | Dual auth dispatcher + CSRF + `set_config` audit user | `op.acc.1` |
| `WorkflowGateError` handler | 409 (no 500) cuando gate ENS no cumplido | `org.op.1` |

---

### Censo de endpoints

| Área | Aprox. endpoints HTTP |
|---|---|
| Motors backend (43 módulos motors/) | ~871 (decorators `@router.*`) |
| v1 routers directos (22 ficheros api/v1/) | ~42 |
| Agents routers (agents/) | ~24 |
| Auth routers (auth/api.py) | ~11 |
| Admin settings, billing, retainer, notifications | ~26 |
| Core routers (workflow_blocking, feature_flags, clients) | ~18 |
| **TOTAL decoradores HTTP en app/** | **~1 191** |

**Discrepancia con CLAUDE.md**: el documento afirma `~879 endpoints REST`. El recuento empírico de decoradores `@*.{get,post,put,patch,delete}` en `backend/app/` (excluidos tests, 1 decorador en tests) arroja **~1 191**. La diferencia (~312) se debe probablemente a que CLAUDE.md fue escrito antes de añadir motores recientes (`m_remediation`, `m_audit_accompaniment`, `m_siem`, olas 100, `m8-autopilot v2.0`, billing/retainer expanded). La cifra empírica es más alta.

Todos los 43 directorios de motores tienen al menos un `api*.py` con endpoints — ninguno es puramente backend-only sin API.

---

---

### Patrones y hallazgos

- **Global dep coverage real**: `FastAPI(dependencies=[Depends(authenticate_request)])` aplica dispatcher a TODOS los endpoints. Whitelist `WHITELIST_EXACT`+`WHITELIST_PREFIX` 13+9 entries documentadas con ADR-030.
- **Startup checks** (`startup_checks.py`): Ed25519 keys (M05/M06/M07), env vars críticas, defaults inseguros, secret_key robusta, BACKUP_ENCRYPTION_KEY. Skip en `FULKRO_TESTING=1`.
- **Lifespan pricing refresh**: carga `pricing_config` de BD en memoria al arranque (`refresh_pricing_from_db`). Best-effort.
- **Docs apagados en prod**: `docs_url=None`, `redoc_url=None`, `openapi_url=None` (2026-06-07).
- **`corpus.py` sin gate de motor**: `/corpus/search|stats` sin `require_owner` en router. Cubierto por global dep (cualquier sesión válida). No leak de datos cliente pero permite enumeración del corpus normativo por pool cliente.
- **Side-effect imports**: `pentest_auto_trigger_events` y `dashboard_events` importados solo por efecto lateral (SQLAlchemy event listeners → SSE). Patrón frágil si se reordena el import.
- **CORS prod**: comentario `# CORS — restrictive in production` es engañoso — en prod NO se registra `CORSMiddleware` en absoluto; Caddy lo gestiona. Funciona pero confunde la lectura.
- **`mcps.py`** catálogo sin `require_owner` en router — cubierto global dep, accesible a pool cliente (datos estáticos, no sensible).

### ENS measures cubiertas por capa API

- `op.acc.1`, `op.acc.2` — autenticación dispatcher dual + CSRF triple binding global
- `op.acc.5`, `op.acc.6` — separación pools admin/cliente/auditor (ADR-013)
- `op.exp.2` — BodySizeLimitMiddleware anti-DoS + CSP + HSTS + TrustedHostMiddleware
- `mp.s.2` — CSP frame-ancestors none + X-Frame-Options DENY
- `op.mon.2` — SIEM aggregator (`/admin/siem/overview|events`)
- `org.op.1` — WorkflowGateError 409 enforces ordering ENS artefacts (categorización firmada → DdA → plan)
- `op.cont.3` — continuity test API (`/api/v1/motors/m19/continuity-tests/*`)
- Medidas ENS cubiertas vía motores individuales accesibles por la capa API: toda la cobertura de `op.*`, `mp.*`, `org.*` definida en motores específicos se expone a través de esta capa de routing.


## 14 - Notificaciones (orchestrator, canales, DLQ, plantillas, WhatsApp)

**Parcela**: `backend/app/notifications/` · 15 archivos fuente + 13 plantillas YAML.
**Veredicto**: **COMPLETO** con 2 bugs reales encontrados.

---

### Ficheros clave

| Fichero | Propósito |
|---------|-----------|
| `orchestrator.py` | `NotificationOrchestrator` ADR-039 MB-16.2 · enqueue + dispatch sync |
| `tasks.py` | Celery: `dispatch_event` retry + `scan_client_inactivity` daily |
| `dlq_service.py` | DLQ sobre `notification_events` (ADR-025 NO nueva tabla) |
| `dlq_api.py` | 4 endpoints REST admin DLQ |
| `api.py` | `portal_router` (prefs cliente) + `admin_router` (events + redispatch) |
| `dnd.py` | `is_dnd_active()` timezone-aware · ventana cruza medianoche |
| `deep_links.py` | `DeepLinkGenerator` 25+ patrones URL admin/cliente |
| `templates_resolver.py` | Jinja2 `ImmutableSandboxedEnvironment` + `StrictUndefined` + lru_cache |
| `whatsapp_dispatcher.py` | Tier-aware routing (BÁSICA digest / MEDIA-ALTA per-event) |
| `whatsapp_info.py` | Footer WhatsApp informativo (NO link wa.me, texto plano) |
| `motor_adapters.py` | 11 funciones `notify_*` convenientes para motors |
| `workflow_step_notifications.py` | Unblock cliente → in-app + email + WhatsApp flag |
| `post_signoff_hooks.py` | Post-firma cross-motor → M30 log + orchestrator email |

---

### Modelo de datos

**`notification_events`** (`FullMixin`, soft-delete, `project_id` RLS):
- `event_type VARCHAR(60)`, `recipient_user_id→client_users SET NULL`, `project_id→projects SET NULL`, `channels_attempted/succeeded/failed JSONB`, `payload_jsonb JSONB`, `template_used VARCHAR(100)`, `status VARCHAR(20)` CHECK, `error TEXT`, `retry_count INT`, `email_log_id UUID` (soft ref sin FK), `dispatched_at`, `delivered_at`.
- Lifecycle: `queued → dispatching → delivered | failed | suppressed_dnd`.

**`notification_preferences`** (UNIQUE `client_user_id`):
- `email_enabled` (default true), `portal_sse_enabled` (default true), `whatsapp_enabled` (default **false**).
- `dnd_start_local/dnd_end_local VARCHAR(5)` HH:MM · CHECK pair-or-nothing.
- `digest_mode`: schema permite `immediate/hourly/daily` · solo `immediate` implementado (deferido MB-19+).
- `event_opt_outs JSONB` (key=event_type, bool) granular por evento.

**DLQ**: NO tabla propia. `notification_events WHERE status='failed' AND retry_count >= 3` es el DLQ semánticamente (ADR-025 sostenido).

---

### Endpoints

| Método | Ruta | Auth |
|--------|------|------|
| GET/PUT | `/portal/notifications/preferences` | `require_client_user` |
| GET | `/admin/notifications/events` | `require_owner` |
| POST | `/admin/notifications/events/{id}/redispatch` | `require_owner` |
| GET | `/admin/notifications/dlq` | `require_owner` |
| GET | `/admin/notifications/dlq/summary` | `require_owner` |
| POST | `/admin/notifications/dlq/{id}/reprocess` | `require_owner` |
| POST | `/admin/notifications/dlq/{id}/resolve` | `require_owner` |

---

### Lógica de negocio

**Flujo enqueue**: resolve prefs → check DND tz-aware (política conservadora: tz inválida → envío) → persist event → dispatch email + SSE sync → update status.

**Gotcha status**: si email falla pero SSE ok → `status="delivered"` igualmente (líneas 328-330). Política deliberada MVP.

**Celery retry**: `max_retries=3`, `countdown=60s`, `acks_late=True`. EmailSender built-in (2s·8s·32s) → hasta 12 intentos efectivos. Re-dispatch requiere `payload._render_context`; si falta → `failed_no_context` sin más retry.

**WhatsApp**: desacoplado del orchestrator. Routing tier: BÁSICA→digest semanal, MEDIA/ALTA→per-event. Requiere `WhatsAppCriticalEventRouting` row + `whatsapp_opt_in_at` + `whatsapp_number`. Footer email: texto plano NO link wa.me.

**Templates**: Jinja2 sandboxed, `lru_cache(64)`, WhatsApp footer auto-append. `StrictUndefined` falla si variable faltante.

**Post-signoff**: todos los hooks tienen `try/except` debug-log (NUNCA bloquean el signoff).

**Admin step notification**: `send_admin_step_completed_notification` es stub — solo log, Marcos NO recibe notificación cuando cliente completa un paso.

---

### ENS cubierto

- `op.exp.6` (notificación incidentes): `incident_resolved_cliente` template + post-signoff hook.
- `op.mon.3` (alertas): `audit_due` adapter + DLQ widget tracking fallos.
- `mp.com.1` (medios alternativos): canal WhatsApp tier-aware eventos críticos post-cert.
- `op.pl.1` / `org.4`: `phase_changed` + `milestone_billed` integran notificación ciclo ENS.

---

### Bugs reales encontrados

**BUG 1 — Signature mismatch `dispatch_critical_event` (`workflow_step_notifications.py` ~177)**:
Llamada usa `client_user=user, message=body, target_url=target_url` pero la firma real espera `client_user_id: uuid.UUID, payload: dict`. Produce `TypeError` en runtime si WhatsApp flag activo. Falla silenciosamente por `except (ImportError, TypeError): skipped`.

**BUG 2 — Hardcoded `marcosmata@fulkro.es` en 11/13 plantillas YAML**:
A pesar de `fulkro_identity.py` como fuente única, las plantillas YAML tienen email y teléfono hardcoded. `TemplateResolver` NO importa ni interpola constantes `fulkro_identity`. Cambiar contacto requiere editar 11 archivos YAML manualmente.

---

### Discrepancias CLAUDE.md vs código

1. **`fulkro_identity` propagación INCOMPLETA**: CLAUDE.md afirma `11/13 email templates con signature canonical` (Ejecutable 7.6). Real: las 13 plantillas YAML tienen `marcosmata@fulkro.es` hardcoded, NO conectadas a `fulkro_identity.EMAIL_SIGNATURE_*`.
2. **WhatsApp como canal orchestrator**: `CHANNEL_WHATSAPP` existe en orchestrator como constante simbólica pero NO se despacha — comentario línea 69: "decoupled · motors call directly". Orchestrator real solo maneja email + portal_sse.
3. **Admin step stub**: CLAUDE.md no menciona que `send_admin_step_completed_notification` es no-op explícito (solo log).


## 15 - Modelo de datos ORM (censo de modelos y tablas)

**Alcance**: `backend/app/models/*.py` (62 ficheros) + `motors/*/models*.py` (16). Migraciones revisadas para tablas sin ORM.

### Mixins / base
| Mixin | Columnas | Uso |
|---|---|---|
| `FullMixin` | UUID PK + created/updated_at + `deleted_at` soft-delete | **141** clases (principal) |
| `UUIDPK + TimestampMixin` | sin soft-delete | ~31 clases |
| `Base` directo | — | ~48 (logs append-only, catálogos) |
| `ClientReviewMixinA` | `client_review_status/note/at/by` + helpers | 10 (DdaEntry, Document, MageritAsset, Incident, CommitteeMeeting…) |
| `ClientReviewMixinB` | + `client_signing_intent_id` | 3 (VerificationRun, BasicDeclarationRow…) |

### Recuento real de tablas
**237 ORM** (~210 en `models/` + ~27 en `motors/`) + **9 sólo-migración** (acceso SQL raw) = **~246 live**. Sin ORM: `pricing_config`, `assets`, `asset_threats`, `asset_dependencies`, `applied_safeguards`, `ens_reinforcements`, `client_dashboard_state`, `client_workspaces`, `global_search_queries` (las 8 últimas, legacy dead).

### Inventario por dominio (resumen)
- **Auth global** (sin RLS): `auth_users` (WebAuthn+TOTP), `auth_webauthn_credentials`, `auth_totp_secrets`, `auth_sessions`, `auth_login_attempts`.
- **Core/tenant**: `clients` (`cif UNIQUE`, DPA Art.28), `projects` (`fase`, `lifecycle_state`, 19 dims, `audit_passed_at`, `categoria_heredada_aapp` — tabla más densa ~35 cols), `systems`, `information_types/services` (DICAT), `categorizations`, `system_sites`, `scope_exclusions`, `policy_acknowledgments`.
- **Admin**: `admin_settings` singleton (JSONB branding/notifications/smtp/general/fiscal).
- **Comercial/billing**: `leads` (8 estados), `proposals`, `contracts` (`documento_sha256`), `invoices/invoice_lines`, `pricing_models`, `pricing_catalog`, `retainer_contracts/activities/drift_events`, `retainer_quarterly_reports`, `contract_milestones`. **`pricing_config`** (precios) **sin ORM** → SQL raw, Alembic no detecta drift.
- **ENS/DdA**: `ens_measures` (52/68/73), `dda_entries`, `annual_review_records`, `dda_project_signatures`, `controls` (huérfana), `obligations`, `compensatory_controls`, catálogo `ens_measure_refuerzos/dimensiones/guias_ccn/evidencia_types`.
- **Documentos/evidencias**: `documents` (`scan_status` ClamAV, `storage_path` minio://), `document_versions` (SHA256), `evidence` (`firma_ed25519`, mp.s.5), `evidence_renewal_requests`, `procedures`, `templates`, `document_folders/tags`, `idms_document_permissions`.
- **Portal cliente**: `client_users` (MFA email/totp, consent GDPR, UNIQUE(client_id,email)), `client_user_totp_secrets`, `client_user_backup_codes`, `client_sessions` (`is_support_access`), `client_user_audit` (hash-chain per-project).
- **Audit log**: `audit_log` (`seq` BIGSERIAL + SHA256 hash-chain trigger; `project_id`+`client_id` nullable 3-way OR; R6; NO FullMixin).
- **Firma**: `magic_links` (`tipo_operacion`, `token_hash`, `otp_failures`), `signing_intents`+`signing_events` (Ed25519, canvas TIER 1), `signing_otp_codes`.
- **MAGERIT**: catálogos globales (`magerit_asset_types/threats/safeguards/ens_mapping/risk_matrix`) + project-scoped (`magerit_analysis/assets/threat_assessment/dependencies/safeguard_deployment/risk_calculation/economic_values/treatment_plan`).
- **Cloud+remediación**: `cloud_connectors/resources/gaps/sync_jobs/digest_snapshots`, `cloud_remediation_approval_logs`, `remediation_jobs/snapshots/agents/agent_commands`.
- **Pentest M8**: `verification_runs/findings`, `external_pentester_handoffs`, `false_positive_patterns`, `remediation_retests`, `m8_verdicts` (advisory), `m8_evidence_records` (append-only R6).
- **Acompañamiento**: `audit_accompaniment_state/artifacts/transitions`.
- **Otros**: planificación (`project_plans`, `wbs_tasks`, `change_requests`, `project_risks`, `status_reports`); gobernanza (`committee_meetings`, `nominations`, `training_records`, `vendors`); RAG (`knowledge_*`, `llm_interaction_log`); lifecycle (`project_lifecycle_states/events`, `archived_projects`); chat (`chat_threads/messages`, `client_messages`, `client_tasks`, `whatsapp_*`); backup/DR (`backup_jobs`, `dr_drills`); conformity (`conformity_routes/submissions`, `basic_declarations`, `recategorizations`); auditor (`auditor_annotations/clarification_requests`); compliance Fulkro (`compliance_checks/alerts/reports`, `fulkro_breach/erasure_*`); misc (`ai_act_transparency_events`, `golden_eval_runs`, `invoices_aapp`, `pkg_nodes/edges`, `copilot_conversations`).

### Patrón RLS
Directa (`project_id`/`client_id` propios) · FK-chain (hija JOIN al padre, p.ej. `document_versions`→`documents`) · 3-way OR (`audit_log`). Sin RLS legítimas: `auth_*`, catálogos, `admin_settings`. `fulkro_app` NOSUPERUSER (hardening 2026-06-07).

### Discrepancias
| Afirmación | Realidad |
|---|---|
| «~184 tablas live» | **~246** (237 ORM + 9 migración) |
| «52 ficheros modelos» | **78** (62 `models/` + 16 `motors/`) |
| `pricing_config` editable por ORM | **sin ORM** — migración + SQL raw |
| `MageritThreatAssessment` con ClientReviewMixinA | sin FullMixin (sin soft-delete) — inconsistencia |

**Veredicto**: Completo. 237 tablas ORM. Deuda: `pricing_config` sin ORM (drift Alembic) + 8 tablas legacy migration-only.


## 16 - Base de datos & migraciones (Alembic, RLS, hash-chain, roles, extensiones)

### Resumen ejecutivo

253 ficheros `.py` en `backend/migrations/versions/`. **Head único verificado** (`alembic heads` live): `remediation_agent_001` (2026-06-13). Raíz: `1350b2466202` (69 tablas · 2026-04-11). ~251 tablas netas (253 `create_table` − 2 `drop_table` radar-drop). RLS habilitado en ≥66 tablas. Hash-chain SHA-256 R6 funcional como trigger PL/pgSQL inmutable.

---

### env.py

`backend/migrations/env.py`:
- Carga `.env` via `python-dotenv` antes de importar modelos (fix FRENTE K: sin esto `DATABASE_MIGRATE_URL` caía al `alembic.ini` stale).
- `DATABASE_MIGRATE_URL` → convierte `postgresql+asyncpg://` → `postgresql://` (driver síncrono Alembic).
- `_AUTOGEN_EXCLUDE_INDEXES`: 3 índices GIN FTS excluidos del autogenerate.
- `_AUTOGEN_EXCLUDE_TABLES`: 15 tablas sin ORM declaration (catálogos MAGERIT, LUCIA, estados raw) — excluidas para que `alembic check` sea fiable.
- `_process_revision_directives`: filtra ruido (índices + cambios solo-comentario) → `alembic check` verde con drift real solamente.

---

### Topología cadena

| Propiedad | Valor real |
|---|---|
| Ficheros `.py` | 253 |
| Head único live | `remediation_agent_001` |
| Raíz | `1350b2466202` (2026-04-11) |
| Merges intermedios | `sub_atom_5b_magerit_child_rls_001` (3-parent: cluster6 + radar_v9_f + remediation_enhancement) · `merge_heads_radar_magerit_001` (radar_recert + sub_atom_5b) |
| Tables creadas/eliminadas | 253 create / 2 drop |

`1350b2466202` también ensancha `alembic_version.version_num` `VARCHAR(32)→VARCHAR(128)` (fix: revision ids >32 chars como `sub_atom_5b_magerit_child_rls_001`=37 chars).

**Cola reciente**: `ola_d_trusted_timestamps_004` → `remediation_engine_001` → `remediation_agent_001` (HEAD).  
**Cadena RLS hardening** (2026-06-11): `client_mfa_email_code_001` → `unify_pricing_fiscal_rls_001` → `rls_fail_closed_hardening_001` → `rls_canonical_policies_002` → `e155_scope_model_001` → … → `remediation_engine_001`.

---

### Hash-chain audit_log (R6)

`d4f8b2a90001_audit_log_hash_chain_trigger.py`:

**Columnas audit_log**: `id UUID · tabla · registro_id · accion VARCHAR(60) · usuario · timestamp · payload_old/new JSONB · hash_prev VARCHAR(64) · hash_current VARCHAR(64) · seq BIGSERIAL UNIQUE · project_id UUID? · client_id UUID?`

**Triggers**:
- `tg_audit_log_hash_chain` (BEFORE INSERT): `pg_advisory_xact_lock(hashtext('audit_log_chain'))` → `hash = sha256(prev||tabla||registro_id||accion||usuario||timestamp||payload_old||payload_new)`. Lock serializa inserciones.
- `tg_audit_log_no_update` + `tg_audit_log_no_delete`: `RAISE EXCEPTION` `ERRCODE='insufficient_privilege'`.
- `tg_audit_{table}` (AFTER INS/UPD/DEL) en 13 tablas: `evidence, documents, document_versions, contracts, invoices, projects, clients, categorizations, dda_entries, obligations, magerit_analysis, audit_findings, pentest_findings`.

**`fn_audit_log_verify_chain()`**: recorre ORDER BY seq, recalcula payload, retorna `(total, first_bad_seq, ok)`.

**Append-only por privilegio** (step 7 provisioning): `REVOKE UPDATE, DELETE ON audit_log FROM fulkro_app, fulkro_app_bypassrls` — capa adicional sobre el trigger.

**Sub-atom 5.A** (`audit_log_rls_001`): ADD `project_id` + `client_id` nullable + RLS 3-way OR: `project_id = current_project_id() OR client_id = current_client_id() OR (project_id IS NULL AND client_id IS NULL)`.

---

### Roles PostgreSQL

Definidos en `infra/docker/init-roles.sql`:

| Rol | Atributos | Uso |
|---|---|---|
| `fulkro` | SUPERUSER owner | DDL inicial; NO runtime |
| `fulkro_app` | NOSUPERUSER NOBYPASSRLS LOGIN | Pool FastAPI runtime; sujeto a RLS |
| `fulkro_app_bypassrls` | NOSUPERUSER BYPASSRLS NOLOGIN | `SET LOCAL ROLE` en rutas admin cross-tenant (~16 call-sites verificados) |
| `fulkro_migrate` | NOSUPERUSER BYPASSRLS LOGIN + miembro de `fulkro` | Alembic upgrade/seed |

**Escalada**: `GRANT fulkro_app_bypassrls TO fulkro_app` → pool eleva sin superuser. **Hardening 2026-06-07**: `REVOKE fulkro FROM fulkro_app`. **Gotcha**: `fulkro_migrate` miembro de `fulkro` (superuser transitivo) — necesario DDL; mayor superficie documentada.

Helpers `current_client_id()` / `current_project_id()` en `infra/docker/init-extensions.sql` (NO en migraciones Alembic). `database.py::set_tenant_context()` los activa con `set_config(..., true)` (transaction-local).

---

### RLS — cobertura y patrones

**≥66 tablas** con `ENABLE ROW LEVEL SECURITY`. ≥136 `CREATE POLICY` en migraciones.

| Patrón | Ejemplo | Migración |
|---|---|---|
| `project_id = current_project_id()` | `evidence`, `remediation_jobs` | `33cef115cdf5`, `remediation_engine_001` |
| `client_id = current_client_id()` | `client_users` | `33cef115cdf5` |
| OR dual project + client | `audit_log`, `copilot_conversations` | `audit_log_rls_001` |
| EXISTS 1-level FK indirecto | `document_versions`, `services` | `33cef115cdf5` |
| EXISTS MAGERIT multi-nivel | `magerit_assets`, `magerit_threat_assessment` | `sub_atom_5b_magerit_child_rls_001` |
| OR `IS NULL` cross-tenant admin | `llm_interaction_log`, `marcos_timesheet_entries` | `unify_pricing_fiscal_rls_001` |
| Fail-CLOSED dual rol | `signing_intents`, `email_log` | `rls_fail_closed_hardening_001` |

**`rls_fail_closed_hardening_001`**: corrige fail-OPEN (`OR current_project_id() IS NULL`) a dual `FOR ALL TO fulkro_app USING(project_id = current_project_id())` + `FOR ALL TO fulkro_app_bypassrls USING(true)`. **`rls_tenant_hardening_p0_001`** (2026-06-07): 7 tablas sin RLS habilitado (`bia_analyses`, `invoices_aapp`, `aepd_notifications`, `audit_accompaniment_*`); 26 ENABLED NOT FORCED → FORCE añadido.

---

### Extensiones PostgreSQL

| Extensión | Activación | Uso |
|---|---|---|
| `vector` (pgvector) | `init-extensions.sql` + migración `80bebdb183fd` | Embeddings 1024-dim corpus/RAG |
| `age` (Apache AGE) | `init-extensions.sql` + `LOAD 'age'` | Knowledge graph CCN-STIC en `m11_rag` |
| `pgaudit` | `init-extensions.sql` + `shared_preload_libraries=pgaudit` | DDL/DML logging OS |
| `pgcrypto` | `init-extensions.sql` | `digest(payload,'sha256')` en trigger |
| `uuid-ossp` | `init-extensions.sql` | `gen_random_uuid()` PKs |

**AGE**: `--skip-age-kg` por defecto → grafo no construido en prod. **pgaudit**: solo extensión cargada; `pgaudit.log='all'` requiere configuración adicional.

---

### Migraciones ADR-055 (auto-remediación · HEAD)

- **`remediation_engine_001`**: `remediation_jobs` (pending→running→success/failed/rolled_back) + `remediation_snapshots` + extiende `cloud_connectors` con `remediation_enabled BOOL DEFAULT FALSE`, `remediation_policy JSONB`, `grant_write_at`. RLS fail-closed project-scoped.
- **`remediation_agent_001`** (HEAD): `remediation_agents` (pending/active/revoked) + `remediation_agent_commands` + 2 `SECURITY DEFINER` que cruzan RLS por token-hash (`fn_resolve_remediation_agent`, `fn_resolve_remediation_enrollment`).

### Pricing & identidad fiscal (`unify_pricing_fiscal_rls_001`)

- Alinea `pricing_catalog` a 3.200/10.700/22.800€; inserta `R_CRITICAL 3.000€/mes` (lookup latente solucionado).
- Fija NIF `77171140E · Marcos Mata García` en `admin_settings.fiscal` (idempotente).
- Habilita RLS en `llm_interaction_log` + `marcos_timesheet_entries`.

---

### Discrepancias CLAUDE.md vs código real

| Claim | Realidad |
|---|---|
| "160 migraciones Alembic" | **253 ficheros `.py`** (verificado `ls *.py \| wc -l`) |
| "~184 tablas live PostgreSQL" | ~251 netas en migraciones; live 237+ (auditoría 2026-06-07); 184 era cifra pre-merge |
| `provision-entrypoint.sh` comenta "head: `client_mfa_email_code_001`" | Head live real: **`remediation_agent_001`** — comentario STALE |
| "RLS en todas las tablas con client_id/project_id" | 15 tablas catálogo raw sin ORM+RLS (exclusión documentada · drift silencioso posible) |
| "AGE knowledge graph activo" | `--skip-age-kg` en deploy default → grafo no construido en prod |

### Veredicto

**Completo** en hash-chain R6, roles y extensiones. RLS: **mixto** — cobertura real ≥66 tablas con defensa en profundidad (trigger + REVOKE + políticas fail-closed), pero 15 tablas sin ORM declaration con posible drift silencioso, y comentario de `provision-entrypoint.sh` sobre el head Alembic desactualizado.


## 17 - Capa MCP / pentest tooling

**Dominio**: orquestación de escáneres de pentest/cloud vía servidores MCP (JSON-RPC 2.0 sobre stdio) + mapeo de hallazgos a medidas ENS Anexo II. Pertenece a `m08_verification`. Veredicto global: **MIXTO** — wiring/cliente/mappers REALES y testeados; ejecución de binarios reales depende de host (degradación honesta a simulado/fallback).

### Ficheros clave
- `backend/app/mcp_client.py` (373 L) — cliente MCP central: `invoke_mcp`, `try_invoke_mcp_or_none`, flag `USE_MCP_REAL`, matriz `scanner_capability`.
- `mcp_executor_service.py` (743 L) — orquestador project-scoped: catálogo `MCP_TOOLS_CATALOG` (13 tools) + estado in-memory + SSE + auto-attach IDMS.
- `tools/base.py` — contrato runner (`FindingCandidate`, `RunnerResult`, `run_subprocess` con setsid/killpg para kill-switch).
- `tools/{prowler,scoutsuite,openvas,nuclei,lynis,testssl,zap,nmap,nuclei,ad_password,dns}_runner.py` (14 runners reales, subprocess).
- `tools/{prowler_cis,openvas,scoutsuite_cloud}_ens_mapper.py` — mappings CIS/CVE/NVT → ENS.
- `ens_mapper.py` — mapper 3-capas (rule CVE→ENS + pattern + LLM Haiku capa3).
- `external/{findings_ingester,handoff_builder,vpn_manager}.py` — ingesta de pentest externo.
- `backend/mcp_servers/<server>/server.py` (14 servidores) + `shared/{mcp_protocol,scope_check,output_normalizer}.py`.
- `backend/app/api/v1/mcps_execute.py` + `mcps.py` — endpoints.

### Los 14 MCP servers (verificado: 14 `server.py` existen en `backend/mcp_servers/`)
Matriz honesta `_SCANNER_REQUIRED_TOOL` (tool-based, corre REAL si el binario está en PATH vía `shutil.which`) vs `_DEDICATED_ENGAGEMENT` (hardware/infra dedicado, `available=False` con razón física):
| Tier | Servers | Binario / razón |
|---|---|---|
| builtin | `scope_enforcer` | Python puro |
| tool-based | `recon`(nmap) `vulnscan`(nuclei) `webpentest`(testssl.sh) `infra`(nmap) `config`(lynis) `cloud`(prowler) `apisec`(nuclei) `sast`(semgrep) | REAL si binario presente |
| dedicated | `wireless`(antena física) `cracking`(GPU) `mobile`(emulador) `phishing`(GoPhish ofensivo) `redteam`(C2) | NUNCA cloud-auto |

**REALES validados empíricamente** (docs/mcps): Prowler v5.29.0, Nuclei, Trivy, Lynis, Gophish (5/6 vía Docker images). ScoutSuite = defer honesto (sin imagen pública, `pip install` desde source). OpenVAS runner existe (17 KB) pero pesado.

### `USE_MCP_REAL` (flag central)
- `use_mcp_real()` = `os.getenv("USE_MCP_REAL")` in (true/1/yes), default **false**.
- false → `invoke_mcp` devuelve `{"_fallback": True}`; `try_invoke_mcp_or_none` devuelve `None` → caller usa runner subprocess legacy O `_simulated_result` (executor).
- true → `asyncio.create_subprocess_exec(sys.executable, server.py)` + handshake `initialize` → `tools/call` → parse content[0].text JSON.
- Corte limpio si `scanner_capability` no disponible (`_unavailable`, razón física) — **nunca finge findings**.
- Auth se propaga vía env `PENTEST_AUTHORIZATION` heredado al spawn; cada server invoca `shared.scope_check.check_scope` (fail-closed). El cliente NO duplica el check.
- Degradación reforzada (Pasada 16): captura `MCPInvocationError|FileNotFoundError|OSError` → fallback graceful.

### Catálogo executor (13 tools, project-scoped)
`MCP_TOOLS_CATALOG`: `vulnscan`(nuclei/openvas/trivy/grype) · `cloud`(prowler/scoutsuite/pacu/kube) · `config`(clara/cis_cat/lynis/openscap) · `phishing`(gophish). **GOTCHA**: nombres de server del executor (`vulnscan/cloud/config/phishing`) son un SUBCONJUNTO de los 14 de `mcp_client._KNOWN_SERVERS`; pacu/kube/clara/cis_cat/openscap/trivy/grype son descriptores de catálogo sin binario real verificado (degradan a `_simulated_result`).

### Mappings CIS/CVE/NVT → ENS Anexo II
- `prowler_cis_ens_mapper.CIS_TO_ENS`: ~28 checks IAM/S3/EC2/CloudTrail → op.acc.2/4/5, op.exp.2/8/10, mp.com.1/2, mp.info.2/3/4, mp.s.5.
- `scoutsuite_cloud_ens_mapper.SCOUTSUITE_TO_ENS`: 28 checks AWS+Azure+GCP (complementario Prowler; overlap intencional `iam-user-with-password-and-no-mfa`).
- `openvas_ens_mapper`: 3 capas (familia NVT + override por nombre + banda CVSS 9/7/4 → op.exp.3/4/7). Añade op.acc.6, mp.eq.3, mp.sw.1/2, op.cont.2.
- `ens_mapper.CVE_TO_ENS`: ~40 CVEs notorios (Log4Shell, ProxyShell, EternalBlue, XZ backdoor...) → mayoritariamente **op.exp.5** (gestión vulnerabilidades), op.acc.5/6, mp.sw.1/2.
- Catálogo `compliance_check` Prowler incluye `ens_311` como opción (descriptor).

### Endpoints (REALES)
`mcps_execute.py` con `dependencies=[Depends(require_owner)]` (R23, admin-only):
- `GET /mcps/tools` (catálogo), `POST .../projects/{id}/mcps/.../execute`, `GET .../executions`, `GET .../executions/{id}` (SSE), `GET .../report`.
- `mcps.py`: `GET /status` (`scanner_capabilities()` para UI). `mcp_executor_service` lo wirea a SSE `asyncio.Queue` + auto-attach IDMS folder `13_Informes_Tecnicos`.

### Integraciones
- **IDMS (m24)**: `_auto_attach_evidence` sube reporte JSON con tags mcp/tool/execution_id, `clasificacion=informe`.
- **LLM**: solo en `ens_mapper` capa3 (Haiku, `classify_ens_measure_via_llm`) + `findings_ingester` PDF (Haiku). R1 sostenido: pipeline de **ejecución** MCP es determinista, NO LLM.
- **ZFP/hash**: `RunnerResult.raw_output_hash` = SHA-256; ZFP gates dedup/FP/classify.
- **autopilot**: `autopilot/{orchestrator,offensive_engagement}.py` consumen `mcp_client`/`scanner_capabilities`.

### Modelo de datos / RLS
La capa MCP es **stateless en DB**: estado de ejecución in-memory por process (ADR-025, NO new table). Persistencia vía IDMS (`documents`, RLS por project_id) y `VerificationRun`/`VerificationFinding` (models.py, fuera de parcela estricta). `execute_tool` valida params requeridos + abre **sesión propia** en background task (gotcha asyncpg pool poisoning resuelto Pasada 16).

### Tests
- `test_mcp_structure.py` (estructural: dirs/docker compose/14 services).
- `test_mcp_wrappers_smoke.py` (14 smoke: catálogo 13 tools, fallback path, MOCK subprocess JSON-RPC). Empírico runtime de binarios = defer (Docker daemon).

### Dead code / TODOs
- `TODO-FASE-13-MCPS-FULL-MIGRATION-001`: tier 3 (migrar todos los runners a MCP, eliminar path subprocess legacy) sin hacer.
- Coexisten DOS caminos para correr una tool: runner subprocess directo (legacy, default) y spawn MCP server (USE_MCP_REAL). Redundancia intencional pero deuda.
- `nmap_runner`/`zap_runner` presentes pero no en catálogo executor (consumidos por runs M08, no por UI mcps).

### Veredicto por componente
| Componente | Estado |
|---|---|
| `mcp_client` (flag/spawn/capability) | **completo** |
| Mappers CIS/CVE/NVT→ENS | **completo** (cobertura parcial pero real) |
| executor project-scoped + SSE + IDMS | **completo** |
| Ejecución binarios reales | **parcial** (host-dependent; 5/6 validados, ScoutSuite/OpenVAS defer) |
| Servers dedicados (wireless/cracking/mobile/phishing/redteam) | **stub honesto** (declaran no-disponibilidad, no fingen) |


## 18 - Config, identidad Fulkro, pricing canónico, feature flags

**Alcance leído íntegro**: `config.py` · `fulkro_identity.py` · `startup_checks.py` · `core/fiscal_identity.py` · `admin_settings/{schemas,service,api}.py` · `core/pricing/{rules,repository,calculator}.py` · `core/feature_flags/{__init__,models,service,api,dependencies}.py` · `categoria_archetype_features.yaml`.

---

### 1 · `Settings` (config.py) — configuración env

`pydantic_settings.BaseSettings` · `.env` + env vars · `extra="ignore"` · `@lru_cache` singleton.

Campos clave: `database_url` runtime (`fulkro_app` NOSUPERUSER) · `database_migrate_url` DDL (`fulkro_migrate`) · `anthropic_default_model = "claude-sonnet-4-5"` (sin versión fecha pinned) · `app_secret_key` default `"change-this"` (Fernet OAuth m16 + SSH m08; startup check prod) · `email_backend = "mock"` fail-open (startup check fuerza error prod) · `cloud_mock_mode_allowed = False` (guard m_cloud_connectors) · `verifactu_qr_base_url` PRE-PRODUCCIÓN AEAT por defecto (sin startup check) · `use_mcp_real = False` · `offensive_provisioner_enabled = False` · `is_production` = `app_env == "production"`.

**Gotcha**: `FULKRO_REMEDIATION_ENABLED` leído con `os.getenv()` crudo en `m_remediation/policy.py` — no en `Settings` (rompe fuente única). **Gotcha modelo**: `agent_14` hardcodea `claude-sonnet-4-5-20250929`; `Settings.anthropic_default_model` no se consume uniformemente.

---

### 2 · `fulkro_identity.py` — constantes identidad

10 constantes string inmutables. Fuente única cross-outputs (PDFs, emails m20, copilots, frontend footer).

| Constante | Valor |
|-----------|-------|
Constantes: `FULKRO_PHONE` (+34 637 165 328) · `FULKRO_EMAIL` (marcosmata@fulkro.es) · `FULKRO_WEB_URL` · `FULKRO_FOOTER_TEXT` (compuesto) · `FULKRO_EMAIL_SIGNATURE_HTML/TEXT` (11/13 templates m20) · `FULKRO_COPILOT_PRIMARY_CONTEXT` (agent_14) · `FULKRO_DISTINTIVO_COLOR_PANTONE_ORANGE_021C` = `#FE5000` (CCN-STIC 809 · mismo las 3 categorías). Module path `backend.app.fulkro_identity` separado para evitar colisión con `config.py`.

---

### 3 · `startup_checks.py` — fail-fast arranque

6 checks en `run_startup_checks()` · skip si `FULKRO_TESTING=1`: (1) `verify_critical_env` — `DATABASE_URL` + 3 claves Ed25519 env · (2) `verify_no_insecure_defaults` — `MINIO_SECRET_KEY` ≠ `"changeme"` · (3) `verify_app_secret_key` — prod ≥32 chars · (4) `verify_email_backend` — prod ≠ `mock` · (5) `verify_backup_encryption_key` — prod ≥16 chars no `REPLACE_ME*` · (6) `verify_ed25519_keys` — loaders canónicos M05+M06+M07; fallo → `CriticalConfigError` aborta uvicorn. Origen: LECCIÓN-OPS-004.

---

### 4 · `admin_settings/` — settings mutables BD

Tabla `admin_settings` · singleton row · 6 columnas JSONB: `branding`, `notifications`, `smtp`, `general`, `analytics_prefs`, `fiscal`. Trigger `tg_audit_admin_settings` + hash-chain `tg_audit_log_hash_chain` (R6). `set_config('app.current_user', email, true)` antes de UPDATE → actor en audit_log.

**Endpoints** (todos `require_owner`): `GET /admin/settings` · `PATCH` ×5 (branding/notifications/smtp/general/analytics_prefs) · `POST /branding/logo` (PNG/JPG ≤2MB) · `POST /smtp/test` · `PATCH /fiscal` · `GET /about` · `GET+PUT /pricing`.

**Gotcha SMTP password**: `SmtpSettings.password` en JSONB en plano ("BD-encrypted en sub-bloque posterior"). **Gotcha `/about` stub**: `suite_passing_stub = 81` hardcodeado; sistema real >5.950 tests. `corpus_sources_target = 92` hardcoded; real = 66 docs suficientes (MEMORY.md).

---

### 5 · `fiscal_identity.py` — identidad fiscal

`FiscalIdentity` dataclass frozen. `get_fiscal_identity(db)`: lee `AdminSettings.fiscal` JSONB → fallback `Settings.marcos_bank_*` para banca. Defaults neutros (no placeholders). Propiedades: `has_nif`, `has_iban`, `domicilio_completo`, `person_type_code` (F/J Facturae). Consumida por: QR Verifactu, PDF factura, contratos/DPA, RoPA, Facturae.

---

### 6 · Pricing canónico

Flujo: `pricing_config (BD)` → `refresh_pricing_from_db()` → `apply_pricing_overrides()` in-place `BASE_PRICES` → `PricingCalculator` + m13 + m23. Precios (código = BD = seed): BÁSICA 3.200 / MEDIA 10.700 / ALTA 22.800 €. Ceilings sector complejo: 4.500 / 13.000 / 28.000 €.

**Retainer tiers** (hardcoded `rules.py` · **no editables por UI**): R_MICRO 150€ · R_LITE 300€ · R_STD 700€ · R_PLUS 1.200€ · R_CRITICAL 3.000€.

Extras MEDIA: sector regulado +2.000 · multi-sede +1.500 · madurez L0/L1 +2.500 · sistema adicional +1.200. Urgencia: +30% si <42 días. Hitos BÁSICA/MEDIA/ALTA: 3/5/7 hitos. **Gotcha**: `apply_pricing_overrides` in-place solo el worker atendiente; demás sincronizan en restart.

---

### 7 · Feature flags

YAML `categoria_archetype_features.yaml` (`@lru_cache`) + tabla `feature_flag_overrides`. 19 features + 7 `always_required`. Dimensiones: categoría · arquetipo (7 enum lowercase) · `requires_employee_count` · `blocks_phase_transition_if_missing`. Tabla: `FullMixin` · CHECK `project_id OR client_id NOT NULL` · `override_value` JSONB. Precedencia: project > client > YAML. Endpoints: `GET /feature-flags/catalog` (sin auth — gotcha) · `GET /projects/{id}/feature-flags` (`require_marcos_or_client`) · `POST/DELETE/GET /admin/feature-flags/override*` (`require_owner`). Q5.3 INVISIBLE correcto. Gates ENS: `media_vuln_scan` + `alta_pentest_cpstic` + `alta_red_team` + `alta_criptografia_807` bloquean fase 9. `dora_dual_compliance` ENS+DORA art.6+19 para `proveedor_financiero` ≥50 empleados.

---

### Discrepancias CLAUDE.md vs código real

1. **`FULKRO_REMEDIATION_ENABLED` fuera de `Settings`**: `os.getenv()` crudo en `m_remediation/policy.py` — no declarado en `Settings`. Rompe doctrina fuente única.
2. **Retainer tiers no editables por UI**: CLAUDE.md dice pricing editable; solo BÁSICA/MEDIA/ALTA en `pricing_config`. Tiers R_* hardcode en `rules.py`.
3. **`suite_passing_stub = 81`**: CLAUDE.md reporta >5.956 tests; `/about` devuelve 81.
4. **Modelo LLM sin versión pinned en `Settings`**: `agent_14` hardcodea `claude-sonnet-4-5-20250929`; inconsistente cross-agentes.
5. **`verifactu_qr_base_url` sin startup check**: default pre-prod AEAT sin guardia prod.

---

### Medidas ENS cubiertas

- `op.acc.6` — startup check Ed25519 M05+M06+M07
- `op.exp.4` — `verify_no_insecure_defaults` (passwords por defecto)
- `op.exp.6` — `verify_backup_encryption_key` (cifrado backups M26)
- `mp.com.1` — SMTP mutable + test endpoint (TLS)
- `org.2` — audit_log trigger PATCH admin settings (R6 hash chain)
- `org.4` / `mp.s.2` — feature flags YAML gating fases ENS categoría/arquetipo
- `op.pl.1` — `FiscalIdentity` trazabilidad fiscal (Verifactu RD 1007/2023)

**Veredicto**: `complete`. Arquitectura Settings+AdminSettings+FiscalIdentity+pricing fuente-única sólida. Startup checks production-grade. Riesgos: SMTP password en plano JSONB · `verifactu_qr_base_url` sin startup check prod · `FULKRO_REMEDIATION_ENABLED` fuera de `Settings`.


## 19 - Corpus & RAG (RD 311 + CCN-STIC, embeddings, retrieval)

### Ficheros clave

| Fichero | LOC | Rol |
|---------|-----|-----|
| `corpus/catalog.py` | 511 | Catálogo estático 66 docs (`CorpusDoc` frozen dataclass) |
| `corpus/rd311_parser.py` | 375 | Parser HTML BOE → chunks (Anexo II: 73 medidas) |
| `corpus/rd311_ingest.py` | 205 | Ingest RD 311 → `knowledge_sources/documents/chunks` |
| `corpus/rd311_embed.py` | 148 | Embeddings e5-large 1024 dims + L2-norm para RD 311 |
| `corpus/ccn_pdf_ingest.py` | 586 | Ingest 14 PDFs (CCN-STIC 800-808 + EU + AEPD) pdfplumber/pypdf |
| `corpus/retrieval.py` | 284 | BM25 + pgvector cosine + RRF (k=60) híbrido |

---

### Modelo de datos

- **`knowledge_sources`** — fuente editorial (code UNIQUE, publisher, source_url). Sin RLS: corpus compartido globalmente (correcto por diseño).
- **`knowledge_documents`** — (source_id FK nullable, mime_type, content_hash, `sector_aplicacion TEXT[]` DEFAULT `{'publico','privado'}`, version_label).
- **`knowledge_chunks`** — (document_id FK, content TEXT, `embedding VECTOR(1024)`, `content_tsvector TSVECTOR` COMPUTED PERSISTED `to_tsvector('spanish',…)`, measure_code, heading_path, article_ref, chunk_index). Índices: GIN tsvector + HNSW cosine_ops (m=16, ef_construction=64).

Sin RLS deliberado: `service.py:354` anota "corpus público compartido · multi-tenant aplica a tablas con datos del cliente".

---

### Catálogo (`catalog.py`)

- **66 `CorpusDoc` entries** exactas (verificado `grep -c "CorpusDoc("`).
- **27 ingested** (DB con chunks+embeddings), **5 pending_auto**, **37 pending_manual**.
- Grupos: G0 14 ingestados base + G2 CCN-STIC 800-809 (11 entries, 9 ingested) + G1 EUR-LEX 4 + G3 BOE extra 7 + G4 ISO/NIST/OWASP 8 + G5 hardening CCN 8 + G6 MAGERIT+PCE 6 + G7 otros 8.
- **CRÍTICO**: `CCN-STIC-809` (Declaración de Conformidad BÁSICA) = `pending_manual` — copiloto no puede fundamentar cierre BÁSICA hasta ingest manual por Marcos.

---

### Parser RD 311/2022

- Parsea HTML BOE por `div.bloque`. Produce: preámbulo, artículos 1-41, disposiciones, Anexos I/III/IV, y **73 chunks de medida** (uno por medida Anexo II).
- Regex `MEASURE_CODE_RE` cubre todas las familias: `org.*`, `op.pl/acc/exp/ext/nub/cont/mon.*`, `mp.if/per/eq/com/si/sw/info/s.*`.
- Target declarado: ~125-150 chunks totales, 73 measure chunks. Idempotente: borra source existente antes de reinsertar.

---

### Pipeline embeddings

- Modelo: `intfloat/multilingual-e5-large` 1024 dims vía `fastembed 0.4.x`.
- Prefijo doc: `"passage: "` / query: `"query: "`. Batch 32. L2-norm explícita con verificación `|L2-1.0| < 0.01`.
- `rd311_embed.py` solo procesa `source.code = 'RD_311_2022'`; NO toca chunks legacy.
- `ccn_pdf_ingest.py` embebe inline durante ingest (importa `_l2_normalize` de `rd311_embed` — DRY).

---

### Retrieval híbrido (`retrieval.py`)

Pipeline 3 etapas (4ª reranking marcada `TODO-M11-G1 cerrado`, diferido a ≥500 chunks):

1. **BM25**: `ts_rank_cd` sobre `content_tsvector`. Candidates N1=30.
2. **Vector**: `embedding <=> CAST(:qemb AS vector)`. Candidates N2=30. Retorna `top_cosine` → señal `confidence` para corpus_gap.
3. **RRF**: `score(d) = Σ 1/(k+rank_i(d))`, k=60. Top K=5 default.

Filtros: `measure_codes`, `source_codes`, `sector_aplicacion` (array overlap `&&`), `only_with_measure_code`.

---

### R2 (citas obligatorias) — implementación

- **Prompt**: "Las citas son OBLIGATORIAS. Usa el formato [RD 311/2022 medida op.acc.6]".
- **`citation_validator.py`**: `extract_citations()` (regex `\[([^\]]{5,80})\]`), `assess_grounding()` (low si cero citas + respuesta >100 chars), `is_not_in_corpus()` (frase-detect).
- **Corpus gap fallback**: si `confidence < 0.45` (configurable `FULKRO_CORPUS_GAP_CONFIDENCE_THRESHOLD`), el system prompt se extiende con instrucción explícita "NO inventes; sugiere fuente oficial externa (CCN-CERT/BOE/AEPD/EUR-LEX)". Evita hallucination cuando el corpus no cubre la query.
- `low_grounding_confidence` + `corpus_gap` devueltos en `CopilotResponse` para badge frontend.

---

### Endpoints expuestos

| Método | Ruta | Auth |
|--------|------|------|
| `GET` | `/api/v1/corpus/search?q=&limit=` | `get_db` admin interno |
| `GET` | `/api/v1/corpus/stats` | `get_db` admin interno |

No hay endpoint cliente directo al corpus. A14 lo consume internamente.

---

### Tests

8 ficheros en `backend/tests/corpus/` (340+ LOC):
- `test_corpus_catalog.py`: floor ≥60 entries, ≥25 ingested, IDs clave presentes.
- `test_hybrid_search.py`: integración DB live — op.acc.5/6, op.exp.7, sector_aplicacion filter.
- `test_rd311_parser.py`: unit-test parser sin DB.
- Otros: `test_pdf_ingest`, `test_rd311_retrieval`, `test_rd311_vector`, `test_retrieval_sector_filter`, `test_measure_mappings_seed`.

---

### Gotchas / deuda técnica

- **Paths hardcoded**: `rd311_ingest.py` y `rd311_embed.py` usan `/home/usuario/fulkro/...` literal — no parametrizable vía settings. Acoplamiento a entorno dev.
- **CCN-STIC-809 pending_manual**: cierre BÁSICA no fundamentable por RAG hasta ingest manual.
- **27 docs sintéticos purgados**: `catalog.py:L128-131` documenta eliminación de entries `INGESTED-NN` con URL `example.invalid` que inflaban count a "40 ingested" (OPS-049 honesto).
- **Reranker diferido correctamente**: corpus ~127 chunks actual < umbral 500 declarado.
- **ccn_pdf_ingest `measure_code` por regex sobre texto libre**: extrae primera ocurrencia de código en chunk completo — puede no ser la medida principal del documento. Menos preciso que el parser RD 311 que asigna código por heading estructurado.

---

### ENS cubiertos

73 medidas Anexo II RD 311/2022 con chunk dedicado: `org.1-4`, `op.pl.1-6`, `op.acc.1-7`, `op.exp.1-11`, `op.ext.1-4`, `op.nub.1-5`, `op.cont.1-4`, `op.mon.1-5`, `mp.if.1-7`, `mp.per.1-4`, `mp.eq.1-3`, `mp.com.1-4`, `mp.si.1-6`, `mp.sw.1-5`, `mp.info.1-6`, `mp.s.1-4`. Hints adicionales vía CCN-STIC PDFs: `org.2-4` (801), `org.1` (805), `mp.info.3+mp.com.2` (807), `op.exp.7+op.mon.3` (NIS2), `op.cont.1-2+op.ext.2` (DORA), `mp.info.4-5` (eIDAS), `mp.sw.1-2` (OWASP).

---

### Veredicto: **COMPLETO**

Pipeline RAG funcional end-to-end: catálogo declarativo → ingest HTML/PDF → embeddings e5-large 1024 dims → BM25 + vector + RRF → A14 con corpus_gap fallback + citation enforcement R2. Deuda menor: paths hardcoded, CCN-STIC-809 pending_manual, reranker diferido (correctamente).


## 20 - M01 Categorizacion + M03 Declaracion de Aplicabilidad

### Resumen ejecutivo

Ambos motores son production-grade y 100% deterministas (R1). M01 implementa la regla del maximo Anexo I RD 311/2022 sobre DICAT; M03 genera atomicamente las 73 entries del Anexo II con aplicabilidad 52/68/73. Sin LLM en la cadena normativa critica.

---

### M01 — Motor de Categorizacion

**Ficheros clave**: `service.py` (logica pura + ORM), `api.py` (27 endpoints), `pyme_archetypes.py` (7 arquetipos CNAE), `dimensions_service.py` (19 dims proyecto), `floor_elevation_service.py` (suelo AAPP N1-N3), `signature_integration.py`.

**Modelo de datos**:
- `systems`: `project_id` FK, soft delete. RLS via `get_system_owner()` SQL function (sin `client_id` directo).
- `information_types` / `services`: `system_id` FK, 5 columnas `valoracion_{d,i,c,a,t}`, `tipo` (finalista/instrumental E-155).
- `system_sites` + `scope_exclusions`: scope E-155.
- `categorizations`: `system_id`, `categoria_resultante`, `version` auto-incremental, `input_snapshot` JSONB, `fecha_acta`, `aprobado_por`.
- `projects.categoria_heredada_aapp` / `categoria_objetivo` / `archetype` / `archetype_confidence NUMERIC(3,2)`.

**Logica ENS — Regla del maximo** (`compute_category`):
- `max(D,I,C,A,T)` por rank {BAJO:1, MEDIO:2, ALTO:3} → BASICA/MEDIA/ALTA.
- `inherited_floor`: eleva `categoria_objetivo` si suelo AAPP > resultado DICAT (solo sube, con cita normativa en justificacion).
- `compute_for_system`: agrega todos IT + servicios activos, resuelve `inherited_floor` via JOIN `projects`, persiste snapshot JSONB.
- Justificacion cita `Anexo I del RD 311/2022 (regla del maximo)` con dimension determinante — trazabilidad ENAC.

**Suelo AAPP (`floor_elevation_service.py`)**: guard N3 (firmado/factura → 409) > N2.5 (en vuelo → bloquea) > N2 (borrador → eleva+regenera) > N1 (libre).

**Arquetipos** (`pyme_archetypes.py`): 7 valores — SECTOR_SALUD (CNAE 86), SECTOR_EDUCACION (CNAE 85), PROVEEDOR_FINANCIERO (CNAE 64), DESARROLLADOR_AAPP, SAAS_ONLY, TELETRABAJO_TOTAL, AUTONOMO_INDIVIDUAL (≤5 empleados, FRENTE L, ortogonal a nivel ENS), GENERICO. Confianza 0.50-0.95.

**Endpoints** (router `/categorization`, `require_owner`): CRUD sistemas, IT/services batch (replace semantics), tipo servicio, sites/exclusiones E-155, `POST /systems/{id}/categorize` (regla maximo + SSE `m01.categorizacion.completed` + `ClientNotification` Pattern #14), acta E-012 en PDF/DOCX/JSON/MD (PDF y DOCX via m06+LibreOffice — MD DEPRECATED monofirma solo preview), historial versionado con `input_snapshot`, firma simple M05, doble firma competente (RInfo+RServ, art.40.2), `GET`/`PUT /projects/{id}/inherited-floor` (orquestador N1-N3).

**Tests**: 25 unit + 49 API + firma. Total ~74+ funciones.

---

### M03 — Motor DdA (Declaracion de Aplicabilidad)

**Ficheros clave**: `anexo2_rd311_2022.py` (tabla BOE autoritativa), `service.py` (`DdaService`), `api.py` (9 endpoints admin + E-040), `portal_api.py` (5 endpoints cliente), `compensatory_service.py` (Art. 8), `enums.py`, `templates.py`.

**Tabla autoritativa** (`anexo2_rd311_2022.py`): 73 medidas transcritas del BOE-A-2022-7191 verificadas 2026-06-07. `APLICA_BASICA=52`, `APLICA_MEDIA=68`, `APLICA_ALTA=73` — correctos (corrige deriva previa RD 3/2010 que tenia 46/64/73). `resolve_entries()` casa por NOMBRE para resolver desfase numeracion `mp.info` / `op.exp.10`.

**Modelo de datos** (`DdaEntry`): `project_id` FK, `measure_id` FK, `aplicabilidad`, `estado_implementacion`, `refuerzos_aplicados` JSONB, `justificacion_no_aplica`, `version`, `aprobado_por`, `fecha_aprobacion`, `client_review_{status,note,at}`, `annual_review_record_id`. RLS `project_id = current_project_id()`. Sin `client_id` directo (RLS 1-level).

**Logica ENS — Generacion DdA** (`generate_dda`): `require_signed_categorization` (gate) → DELETE previas (replace atomico) → carga 73 `ens_measures` → por medida: `_measure_applies` via booleans `aplica_basica/media/alta` → APLICA[_CON_REFUERZOS]+NO_VALORADO o NO_APLICA+justificacion template → `_applicable_reinforcements` (query `ens_measure_refuerzos` JSONB `+R1..+R9`). Nota proporcionalidad CCN-STIC 801 sec 4.2 añadida si `tamano_empleados in {micro, autonomo}`.

**Freeze/unfreeze**: `freeze_dda` requiere ≥80% medidas aplicables valoradas. `annual_review`: snapshot → `annual_review_records`, bump version, limpia `aprobado_por` (exige reaprobacion Direccion, cadencia anual CCN-STIC 808).

**Medidas compensatorias** (Art. 8): `CompensatoryControl` tabla separada, estados `pendiente_aprobacion → aprobada → rechazada`. NO muta `dda_entries` enlazada (protege DdA firmada).

**Endpoints admin** (router `/dda`, `require_owner`): generate (73 entries atomicas), list entries (MAGERIT enrichment, filtros marco/familia), stats, PATCH entry (bloqueado frozen), freeze (≥80%), unfreeze, catalogo 73 medidas, entry por codigo, status gate UI, firma E-040 RSEG. **Endpoints cliente** (`/portal/dda`): summary frozen/ready_for_signing, list measures (filtro familia/review_status), document-hash SHA256 pre-firma, detalle entry + evidencias, review action. `con_pregunta`/`suggest_change` → `audit_log` 3-way OR (Sub-atom 5.A).

**Tests**: 16 service + 15 API + firma. Verifica 52/68/73 entries por categoria.

---

### Medidas ENS cubiertas

- `org.1-4` — proceso autorizacion documentado en acta E-012 doble firma art.40.2.
- `op.pl.1` — DdA como input AR; gate `require_signed_categorization`.
- `op.pl.2` — dimensiones DICAT por sistema.
- `op.acc.1-6` — dimension A (Autenticidad) determinante; TELETRABAJO_TOTAL marca `op.acc` critico.
- `mp.info.3` — acta E-012 firmada M05 Ed25519 (doble firma RInfo+RServ).
- Todas las **73 medidas Anexo II** cubiertas como entries DdA con estado implementacion.
- E-codes: **E-012** (Acta Categorizacion PDF/DOCX/JSON/MD), **E-040** (DdA firmable RSEG).

---

### Gotchas / deuda

| Item | Impacto |
|---|---|
| `generate_acta_e012` (MD) marcado DEPRECATED — solo preview, path canonical = m06 | Sin impacto funcional; no usar como acta definitiva |
| `dda_project_signatures` sin escritor (dead code) — tabla existe en BD | `is_frozen` corregido a leer `dda_entries.aprobado_por` · correcto |
| `PATCH /entries/{id}` usa `SET LOCAL ROLE fulkro_app_bypassrls` | Aceptable con `require_owner` en router (Marcos-only) |
| `TODO-RBAC-PER-ENDPOINT-001 Cat A` en ambos routers | Pendiente RBAC granular; `require_owner` suficiente pre-piloto |

---

### Discrepancias CLAUDE.md vs codigo

- CLAUDE.md no documenta 27 endpoints M01 (sites/exclusiones/historial versionado/PDF/DOCX/JSON/doble firma) — motor mas completo de lo documentado.
- CLAUDE.md cita 52/68/73 medidas — **confirmado correcto** en `anexo2_rd311_2022.py`.
- `generate_acta_e012` DEPRECATED no mencionado en CLAUDE.md.

---

### Veredicto: COMPLETO

Implementacion fiel de RD 311/2022 Anexo I y Anexo II. Sin LLM en cadena normativa. Tests ~105+ funciones. Unica deuda relevante: `dda_project_signatures` dead code (documentada, sin impacto funcional).


## 21 - M02 Analisis de riesgos MAGERIT v3

**Dominio**: Análisis de riesgos MAGERIT v3 (NIPO 630-12-171-8, Libros I/II/III) integrado con Anexo II ENS. Inventario de activos → dependencias → amenazas → salvaguardas → riesgo intrínseco/efectivo/residual → plan de tratamiento → snapshot firmable (E-028). 17 ficheros, ~6.145 LOC. Leído íntegro salvo tramos repetitivos de `api.py`/`exporters.py` (muestreados).

### Ficheros clave
- `models.py` — 13 modelos ORM (5 catálogo + matriz + 7 análisis con RLS).
- `service.py` (1.549 LOC) — `MageritService`: motor de cálculo cualitativo/cuantitativo, dispatcher por `calculation_mode`, snapshot/freeze.
- `api.py` (1.293 LOC) — 30 endpoints admin `/magerit/*` (`require_owner`).
- `portal_api.py` — 7 endpoints cliente `/portal/magerit/*` (read + review).
- `quantitative_service.py` + `quantitative_api.py` — capa económica ALE (Ola D).
- `threat_auto_mapper.py` (+api) — auto-genera assessments desde catálogo Libro II.
- `libro_ii_loader.py` — carga `docs/magerit_catalog/threats.yaml` (lru_cache).
- `signature_integration.py` — firma E-028 vía magic-link (M12).
- `exporters.py`/`exporter_mgr.py` — XLSX + `.mgr` XML para PILAR.
- `pilar_importer.py` (+api) — import XML PILAR.

### Modelo de datos / RLS
- **Catálogo (sin tenant)**: `magerit_asset_types`, `magerit_threats` (+`official_description`/`official_source` trazabilidad ENAC), `magerit_safeguards`, `magerit_ens_mapping`, `magerit_risk_matrix` (25 filas 5×5 precargada).
- **Análisis (RLS)**: `magerit_analysis` (`project_id` FK, `status` draft/in_progress/completed/approved, `calculation_mode`, `result_snapshot` jsonb, `snapshot_frozen_at`, `signature_magic_link_id`).
- **Child (analysis_id, sin project_id/client_id directo)**: `magerit_assets` (DICAT `value_*`/`accumulated_*` + ClientReviewMixinA), `magerit_asset_dependencies`, `magerit_threat_assessment` (+ClientReview), `magerit_safeguard_deployment`, `magerit_risk_calculation`, `magerit_treatment_plan`, `magerit_economic_values`.
- **RLS**: parent `magerit_analysis` tiene `project_isolation` (33cef115cdf5). 6 child via `sub_atom_5b_magerit_child_rls_001` con EXISTS 1-level por `analysis_id` (NO 3-way OR; tenant solo por `analysis_id`→`project_id`). `magerit_economic_values` tiene RLS propia en `ola_d_..._003` (EXISTS via análisis). Resolución chicken-and-egg vía SECURITY DEFINER `get_magerit_analysis_owner()`.

### Algoritmos (todos deterministas, R1)
- Propagación cualitativa: `accumulated = max(propio, superiores)` (Libro III 2.2.1). Cuantitativa: cierre transitivo COMPLETO vía `networkx` (`all_simple_paths` + suma MAGERIT `1-(1-a)(1-b)`) — contradice el README (ver discrepancias).
- Impacto cualitativo: tabla 5×5 (`IMPACT_TABLE`) extendida de la oficial 3-col. Riesgo: lookup en `magerit_risk_matrix` BD.
- Cuantitativo: `impacto=v×d`, `riesgo=impacto×frecuencia` (`FREQUENCY_MAP` MB=0.01…MA=365).
- Riesgo efectivo: eficacia de paquete (media) descompuesta `ei`/`ep` por `effect_type`.
- Residual: eliminar=0, transferir=×0.5, mitigar=target (factores FULKRO convention, declarados honestamente).
- ALE económico: `SLE=valor€×exposure×(degr/100)`, `ALE=SLE×ARO`, derivado on-query (sin persistir → sin staleness).
- `_map_value_to_level`, `_map_degradation_to_level`, umbrales tratamiento: convención FULKRO, NO MAGERIT oficial (documentado en docstrings).

### Endpoints (rutas reales, prefix `/api/v1`)
- Admin pipeline `/magerit/projects/{id}/analysis`, `/analysis/{id}/{assets,dependencies,propagate,threats,calculate-intrinsic,safeguards,calculate-effective,treatment-plan,calculate-residual}`.
- Reporting: `/analysis/{id}/{report,report.pdf,report.docx,snapshot}`, `freeze`/`unfreeze`, `export-xml`/`export-pilar`/`export-mgr`, 7× `export/*.xlsx`, `assets/import`.
- Firma E-028: `/analysis/{id}/report-e028/request-signature`, `/signature-status`.
- Cuantitativo: `/magerit/analysis/{id}/economic-values` (POST), `/quantitative-report` (GET).
- Auto-map: `POST /projects/{id}/threats/auto-map`.
- PILAR import: `pilar_import_api` 2 POST.
- Cliente `/portal/magerit/`: `projects/{id}/{summary,assets,risks,document-hash}`, `assets/{id}`+`/review`, `risks/{id}/review` (review = `revisada_ok|con_pregunta|suggest_change`, READ + review-only, Q5.3).

### Medidas ENS / integraciones
- `magerit_ens_mapping` modela salvaguarda→medida ENS (`org.*/op.*/mp.*`) pero el motor M02 **no lo consulta**; lo usa M03 (DdA). El motor M02 NO mapea riesgos a E-codes/medidas en su propio output. E-code propio: **E-028** (informe MAGERIT firmable).
- Integraciones: **M12 magic-link** (firma E-028, `FIRMA_DOCUMENTO`, revoca link previo, hash SHA-256 del snapshot congelado), **M27/PILAR** (export `.mgr`), **SSE** (`sse_dispatcher` importado en api), **audit_log** en `portal_api` (`magerit.review.flagged` + `cliente.magerit.viewed`, 3-way OR Sub-atom 5.A), hash-chain trigger global (`d4f8b2a90001`) cubre estas filas. **LLM: ninguno** (motor 100% determinista, cumple R1).

### Gotchas / dead code / TODOs
- `quantitative_api._ensure_analysis_rls` y `threat_auto_mapper` hacen `db.get`/escriben **antes** de fijar contexto tenant fiable; dependen de RLS app-role activa por defecto. `quantitative` setea `app.current_project_id` DESPUÉS del primer `db.get` → posible lectura cross-tenant si rol no fuerza RLS. Menor pero señalable.
- `magerit_ens_mapping` = tabla definida y seedeada pero **sin lector en M02** (consumida solo por M03).
- Modo `hybrid`: aceptado en schema/CHECK pero `NotImplementedError` explícito en cálculo (no es deuda, decisión).
- README declara propagación "1-hop únicamente / networkx pendiente" → **OBSOLETO**: el código ya implementa networkx multi-hop completo en modo cuantitativo.
- TODO-RBAC-PER-ENDPOINT-001: router admin entero `require_owner` (Cat A Marcos-only), pendiente RBAC granular.

### Veredicto: **COMPLETO** (production-grade)
Pipeline MAGERIT v3 íntegro cualitativo + cuantitativo, dependencias multi-hop reales (networkx), freeze/snapshot + firma E-028, import/export PILAR, portal cliente review, RLS en parent+7 child. Determinista con citas literales Libro I/II/III en cada docstring (trazabilidad ENAC). Convenciones no-oficiales declaradas honestamente.

### Discrepancias docs vs código
- README "propagación 1-hop, networkx no implementado" **FALSO**: `_propagate_values_quantitative` usa `nx.all_simple_paths` + cierre transitivo completo.
- CLAUDE.md "11 child tables magerit RLS" → real **6 child** (+ economic_values aparte). La propia migración 5.B documenta el claim "11 INCORRECTO empirical".
- README "integrado con las 80 medidas Anexo II": el catálogo `magerit_ens_mapping` existe pero M02 no genera salida por medida ENS; la integración real es indirecta (M03 consume).
- Memoria afirma "DB upgrade BLOCKED phantom revision" para 5.B; el código de migración existe y consolida 3 heads — verificar aplicación en BD live no hecho aquí.


## 22 - M04 Analisis GAP + M05 Obligaciones/medidas

**Alcance leido**: M04 todos los .py (`service.py` 733L, `api.py`, `control_status_service.py`, `control_status_api.py`, `catalog_loader.py`, `enums.py`); M05 `instantiation_service.py`, `api.py`, `library_loader.py`, `gantt_planner.py`, `gantt_service.py`, `personalization.py`. Muestreados: catalogo YAML + library JSON (conteos), modelos `Finding`/`Obligation`, routers en `main.py`.

### Proposito / dominio
- **M04 Gap Analysis**: compara estado actual (CMM derivado de la SoA) vs target por categoria ENS; genera `Finding` por gap. Determinista (R1) + LLM opcional para re-ranking.
- **M05 Obligations**: instancia obligaciones desde plantillas library a partir de gaps M04; planifica via Gantt determinista (orden topologico + dias laborables). Sin LLM salvo personalizacion opcional de descripcion.

### Modelo de datos / RLS
- M04 NO tiene tablas propias: usa `findings` (`fuente='gap_analysis'` discrimina), join `DdaEntry`+`EnsMeasure`, lee `Evidence`/`Document`/`categorizations`.
- M05 usa `obligations` (modelo en `models/ens.py`). Plantillas en JSON, no en BD.
- **RLS**: ambas tablas tienen `project_id` (FK) pero **NO columna `client_id`**. Aislamiento via `set_tenant_context(client_id, project_id)` + `get_project_owner(pid)` lookup. `_set_gap_rls` usa `SET LOCAL ROLE fulkro_app_bypassrls` para resolver el project del gap antes de fijar RLS (defendible, scoped).

### Endpoints REALES (todos `/api/v1` + `require_owner` Cat A)
M04 (`gap_router`): `POST /projects/{id}/gaps/analyze` · `GET /gaps/{id}` · `GET /projects/{id}/gaps` · `PATCH /gaps/{id}` · `DELETE /gaps/{id}` · `POST /gaps/{id}/close` · `GET .../gaps/dashboard` · `GET .../gaps/quick-wins` · `POST .../gaps/prioritize-llm`.
Control-status (M04): admin `GET /admin/projects/{id}/controls/status` + `/cmm`; cliente (`get_current_client_user`) `GET /client-portal/controls/status` + `/cmm`.
M05 (`obligations_router`): `POST .../obligations/instantiate` · `GET .../obligations/gantt?format=json|xlsx` · CRUD `POST/GET/PATCH .../obligations[/{id}]` · `GET .../summary` · transiciones `start`/`complete`/`verify`.

### Logica / algoritmos
- **CMM** (`enums.ESTADO_IMPL_TO_CMM`): `no_aplica→None`, `no_valorado/no_implantada→L0`, `parcial→L1`, `implantada→L3`. `effective_cmm_level` sube a **L4** si semaforo evidencia VERDE (acople #20→#21). Target por categoria: BASICA=L2, MEDIA=L3, ALTA=L4 (`CATEGORY_TARGET_LEVEL`). Gap si `actual_order < target_order`.
- **Fix #21 (en codigo)**: antes leia `controls.estado` (tabla VACIA → siempre L0 = "gap maximo falso"); ahora deriva de `dda_entries.estado_implementacion`. `controls` queda **huerfana (0 lecturas, no se borra)**.
- **Severidad/esfuerzo/quick-win/nuclear**: `catalog_loader` sobre `gap_severity_rules_v1.yaml` (v1.0, **73 medidas**). quick-win = flag + sev∈{alta,critica} + esf≤threshold. Semaforo dashboard: score=sev_num×max(gap_mag,1); rojo≥15, amarillo≥6.
- **control_status_service** (R1 puro, anti-falso-verde): por `measure_code`→Evidence (verde solo si ≥1 evidencia + vigentes + ninguna caducada + `scan_status=clean`); por `control_id`→Document (approved+revisada_ok+firmada+no caducada). Caducado/infectado→rojo.
- **M05 Gantt**: Kahn topo-sort, dias Mon-Fri, capacidad diaria=h/semana÷5, encadena por ultimo predecesor; `CircularDependencyError` si ciclo. Export XLSX openpyxl.
- **Instantiation**: idempotente por `(project_id, template_id)`; filtra por categoria; copia verbatim `criterios_aceptacion`+`fuente_normativa` (nunca tocado por LLM); **gate `require_magerit_analysis`** (M02) antes de instanciar plan.
- **Estados obligacion**: 2 vocabularios coexisten — instantiation crea `estado="pending"` (ingles); CRUD/transiciones usan `{pendiente,en_curso,completada,verificada,bloqueada}`. Posible drift (ver discrepancias).

### Medidas ENS cubiertas
- Catalogo severidad: 73 medidas (familias `org.* op.* mp.*`). Nucleares: `org.1, op.pl.1, op.acc.6, op.exp.1/4/7, ...`.
- Library obligaciones: **250 plantillas v3.0** sobre 73 `measure_code` distintos (familias completas). E-codes: NO referenciados directamente; vinculo a entregables via `entregable_tipo`/`entregable_esperado` (texto), no codigos E-3xx.

### Integraciones
- **M04→M05 hook**: `_trigger_obligations_hook` tras `analyze_project` instancia obligaciones (best-effort, try/except silencioso). M04 tambien lee esfuerzo agregado de la library M05 (`_M5_EFFORT_CACHE`).
- **M02 gate** (MAGERIT), **M07** Evidence, **M03** DdA, **M01** categorization, **M21** ClientNotification (`cliente_aporta_evidencia`→`emit_client_notification`, NO magic-link real).
- **LLM**: `llm_prioritizer` (re-rank, fallback) + `personalization.enrich_description_with_llm` (temp 0.2 R3, fail-soft).
- **audit_log**: control_status emite Sub-atom 5.A 3-way OR (`admin/cliente.control.status.viewed`) best-effort. **M04 gaps CRUD y M05 obligations NO emiten audit_log** (gap de trazabilidad ENAC).

### Veredicto: **COMPLETO (production-grade) con matices**
Logica densa, real, conectada E2E (analyze→hook→instantiate→gantt). Anti-falso-verde y fix CMM #21 son robustos y honestos. No es stub.

### Discrepancias docs vs codigo
- README M05: "**30-template** obligations library" → real **250 plantillas v3.0** (library_loader docstring dice 30; library_loader.py cabecera tambien). Desfase grande.
- README "RLS por `obligations`/`findings`" → no hay `client_id`; aislamiento **project-scoped** via tenant context, no columna RLS de cliente.
- README M05 dice `library/` "YAML/JSON" → es **solo JSON**.
- `controls` tabla declarada huerfana en codigo (0 lecturas) — no en READMEs.
- Drift estados (`pending` vs `pendiente`): instantiation produce `pending`, fuera de `VALID_ESTADOS_OBLIGATION`; `summary` lo agrupa por key cruda → buckets duplicados posibles.
- `_trigger_cliente_aporta_magic_link` emite notificacion in-portal, NO magic-link (nombre engañoso, docstring lo aclara).


## 23 - M05 Firma electronica + M24 IDMS (gestor documental)

### M05 — firma electronica in-portal

**Proposito**: firma electronica simple eIDAS Art. 25.1. Dos paths: OTP step-up email (6 digitos, 5 min TTL, max 5 intentos) para tipos criticos; canvas TIER 1 (trazo + nombre + apellido, sin OTP re-prompt) para todos.

**Ficheros** (9): `models.py`, `signable_types.py`, `keypair.py`, `service.py`, `api.py`, `pdf_signature_embed.py`, `email_templates.py`, `schemas.py` (168 LOC), `timestamp_api.py`.

**Tablas**:
- `signing_intents` — `project_id` NOT NULL; RLS fail-closed `signing_intents_tenant_isolation` (`project_id = current_project_id()` para `fulkro_app`; bypass `fulkro_app_bypassrls` admin)
- `signing_events` — INMUTABLE (NO update/delete grant); columnas canvas TIER 1 nullable (`signature_canvas_dataurl`, `signed_name`, `signed_surname`); `project_id` NOT NULL
- `signing_otp_codes` — ephemeral, FK a `signing_intents`, unicidad `(signing_intent_id, user_id)`; sin RLS propia
- `trusted_timestamps` — append-only RFC 3161 TSA

**SignableTypes reales**: **18** en `signable_types.py` (incluye tipos governance FASE 0 y `contrato_comercial`). `REQUIRES_STEP_UP_OTP` frozenset: 7 tipos (`dda`, `pentest_authorization`, `conformidad_ens`, `declaracion_conformidad_basica`, `dpc_anual`, `renewal`, `retainer_quarterly_signoff`).

**Keypair**: `FULKRO_M05_SIGNING_PRIVATE_KEY` env via `core/signing_keys.py`; fallback dev a `var/keys/m05_signing_dev.ed25519.pem`; cacheado module-level con lock threading; NO clave efimera en prod (fix P0-1).

**Hash chain**: `previous_signature_hash = SHA256(bytes_firma_anterior)`. `event_hash_sha256 = SHA256(message_bytes + prev_hash + sig_bytes)`. `created_at` fijado Python-side (OPS-047) para evitar timestamps identicos en misma transaction. Verificacion admin: `verify_chain_integrity()` recorre todos `signature_generated` del proyecto ordenados por `created_at`.

**Maquina de estados**: `pending | otp_required | otp_verified | signed | rejected | expired`. `sign_canvas` acepta cualquier estado no-terminal sin exigir `otp_verified`. Advisory lock por `document_id` (Pattern #22) en `sign_canvas`.

**Endpoints** (14): cliente `client_router` bajo `/portal/signing/`: `POST /intents`, `POST /intents/{id}/request-otp`, `POST /intents/{id}/verify-otp`, `POST /intents/{id}/sign`, `POST /intents/{id}/reject`, `GET /intents/{id}`, `GET /projects/{id}/history`, `POST /intents/{id}/sign-canvas`, `GET /projects/{id}/pending`. Admin `admin_router` bajo `/admin/signing/` (`require_owner`): `GET /projects/{id}/chain-integrity`, `POST /intents/request`, `GET /intents/{id}/verify`, `POST /events/{id}/timestamp`, `GET /events/{id}/timestamp`.

`sign-canvas` emite audit_log Sub-atom 5.A (`signature.signed`) + SSE `signing.signed` post-commit (Pattern #14). `sign` legacy actualiza `basic_declarations.signed_at/signed_hash` si `signable_ref_type == "basic_declaration"`. `pdf_signature_embed.py`: `append_signature_page()` appends pagina con imagen canvas, badge Ed25519+hash chain, footer Fulkro; graceful degradation dataurl invalido.

**Tests**: 5 ficheros, 1192 LOC. Cubre OTP path, TIER 1 canvas, history, PDF embed, RFC 3161 (mocked, sin TSA real).

---

### M24 — IDMS gestor documental

**Proposito**: gestion documental project-scoped para ciclo ENS: ingesta SHA-256 + dedupe exacta, clasificacion automatica keyword→carpeta, arbol 15 carpetas estandar, versionado con advisory lock, workflow doc, caducidad, permisos granulares, busqueda ILIKE, awareness formacion.

**Ficheros** (4): `idms_service.py` (1033 LOC), `api.py` (880 LOC), `awareness_api.py`, `awareness_tracker.py`.

**Tablas/modelos** (`models/documents.py` + `models/idms.py`):
- `Document` — `project_id` NOT NULL; `client_id` via `ClientReviewMixinA`; `storage_path` MUST be `minio://{bucket}/{key}` (fix #36); campo `interno` bool para ocultar al cliente; `estado` reutilizado para workflow IDMS
- `DocumentVersion` — version MAX+1 bajo `pg_advisory_xact_lock(hashtext('idms_doc_{id}'))` (Pattern #22); unique `(document_id, version)`
- `DocumentFolder` — 15 estandar codigos `00`-`13`+`99`; idempotent init; `client_id` nullable
- `DocumentTag` — `tag_type`: measure_ens/category/phase/custom; `confidence` float; `source`: manual/rule/llm
- `IdmsDocumentPermission` — modelo hibrido: 0 rows → fallback RLS project; >0 rows → jerarquia owner>editor>viewer (soft delete)

**Storage path critico** (#36): `_persist_to_minio()` sube bytes reales a MinIO; retorna `minio://{BUCKET}/{key}`. `download_document` resuelve prefijo; fallback local dev. Pre-#36 los bytes se descartaban.

**Cross-tenant guard** (#5): contextvar `_current_subject` por request; `_set_project_rls()` compara `caller.client_id` vs owner del project; 404 si mismatch (no 403).

**Workflow**: `draft→review→approved→archived/deprecated`. `VALID_TRANSITIONS` dict. `auto_deprecate_expired()` candidato cron. Caducidad default: politica/informe 12m, procedimiento/contrato 24m.

**Clasificacion**: 13 reglas keyword sobre nombre en lowercase → carpeta estandar. Sin LLM (determinista R1). Fallback `99_Misc`.

**Tests**: 7 ficheros, 1495 LOC. Cubre intake, dedup, workflow, expiration, permissions, download (#32), minio persist (#36), awareness.

---

### Medidas ENS cubiertas

| Codigo | Aplicacion |
|---|---|
| `op.exp.10` | Claves criptograficas — Ed25519 keypair + rotacion via env |
| `mp.info.3` | Firma electronica — eIDAS Art.25.1 simple; OTP step-up para DdA/conformidad |
| `mp.info.6` | Sellos de tiempo — RFC 3161 TSA `trusted_timestamps` append-only |
| `mp.info.4` | Control de versiones — `DocumentVersion` + advisory lock |
| `org.3`/`mp.com.1` | Control de acceso — RLS project + permisos granulares IdmsDocumentPermission |
| `mp.per.4` | Formacion — awareness sessions + asistencia + cobertura |

---

### Discrepancias CLAUDE.md vs codigo

1. **"11 SignableTypes catalog"** (registrado sesion 3B-2B.7): codigo real tiene **18** tipos; diferencia no documentada en CLAUDE.md posterior.
2. **`signing_events` sin `client_id`**: CLAUDE.md menciona "Sub-atom 5.A 3-way OR" para signing, pero `signing_events` solo tiene `project_id`. El 3-way OR aplica a `audit_log`, no a esta tabla.
3. **`signing_otp_codes` sin RLS propia**: el fail-closed aplica a `signing_intents` y `signing_events`; OTP codes acceso indirecto via sesion ClientUser.

**Veredicto**: **completo** — ambos motores production-grade sin dead code ni stubs detectados.


## 24 - M06 Fabrica de documentos / plantillas ENS

**Auditado**: 2026-06-13 · Código fuente leído directamente.
**Alcance**: 474 ficheros totales · ~30 módulos Python · 131 `.md` cuerpos plantilla · 86 entradas `template_catalog_v1.yaml`.

---

### Propósito

Motor de generación documental ENS: políticas E-1xx, procedimientos E-2xx, entregables E-0xx/E-4xx/E-7xx, comerciales C-001/C-003/P-001. Pipeline completo: catálogo YAML → render DOCX (docxtpl+Jinja2) → firma Ed25519 → PDF (LibreOffice headless) → MinIO → audit_log.

---

### Taxonomia real de plantillas

**86 entradas** `template_catalog_v1.yaml` (fuente autoritativa) · **83** en `TEMPLATE_REGISTRY`. Desglose `.md` de cuerpo: `policies` E-1xx (42) · `procedures` E-2xx+EIT/EPF (40) · `deliverables` E-0xx/E-4xx/E-7xx (46) · `commercial` (3). Total: 131 `.md`.

Adicional: **16 plantillas Excel** X-001–X-016 (`excel_generators/registry.py`): inventario activos MAGERIT · DdA 73 medidas · gap CCN-STIC 808 · RAT RGPD art.30 · BIA · RACI · SLA · CAIQ.

---

### Ficheros clave

- `service.py` — `DocumentFactoryService` (generar, listar, dashboard, soft-delete, mark-delivered)
- `api.py` — Router admin `require_owner` · ~18 endpoints
- `portal_api.py` — Router cliente · 5 endpoints policy signoff (ADR-013 doble pool)
- `template_registry.py` — `TEMPLATE_REGISTRY` dict 83 entradas + `load_template_module()`
- `catalog_loader.py` — carga/valida YAML · normaliza placeholders legacy→nuevo
- `rendering.py` — `render_docx()` docxtpl+Jinja2 · `convert_docx_to_pdf()` LibreOffice 60s
- `signing.py` — SHA-256 + Ed25519 via `FULKRO_M06_SIGNING_PRIVATE_KEY` env
- `policy_signoff_service.py` — tier-aware (BÁSICA 10/MEDIA 18/ALTA 25) · bulk SHA-256 → M05
- `documentation_levels.py` — 4 niveles CCN-STIC 805 derivados dinámicamente del registry (R25)
- `governance_context.py` — roles art.11 best-effort desde m30 `client_contacts` · NUNCA lanza
- `informe_final_generator.py` / `continuity_generator.py` / `alcance_generator.py` — context E-040/BIA/E-155
- `rectores_generator.py` — E-160 Manual SGSI + E-170 Plan Director programático python-docx
- `filters.py` — filtros Jinja2 ES: `fecha_es`, `lista_es`, `mayusculas`

---

### Modelo de datos

**`templates`** (catálogo global · SIN RLS · `FullMixin`): `codigo` UNIQUE · `nombre` · `categoria` · `familia_ens` · `aplica_desde` · `docx_path` String(512) · `placeholders_requeridos` JSONB · `is_active`.

**`documents`** (`FullMixin` + `ClientReviewMixinA` · RLS via `set_tenant_context`): `project_id` FK · `template_codigo` · `docx_path`/`pdf_path` · `storage_path` `minio://` · `rendered_hash` SHA-256 · `signature_ed25519` · `context_snapshot` JSONB · `client_review_status` · `client_signing_intent_id` (bulk M05) · `interno` Boolean · `folder_id` FK m24 IDMS.

**`policy_acknowledgments`**: evidencia acuses de recibo empleados (mp.per.3).

---

### Endpoints

**Admin** (`require_owner`): `GET/POST /templates[/{codigo}]` · `POST /templates/sync-catalog` · `POST /projects/{id}/documents/generate` + 7 variantes contextualizadas (E-040/400/401/403/155/160/170) · `/excel-templates/{slug}/generate` (16 slugs) · `/documents/preview` · CRUD documentos · `/documentation-levels` · `/excel-templates` · `/policy-acknowledgments[/summary]`.

**Portal cliente**: `GET /portal/policies/projects/{id}[/list]` · `POST /portal/policies/documents/{id}/review` · `GET .../document-hash` · `POST .../finalize-signoff`.

---

### Pipeline generación

`template_codigo` → Template ORM → **GATE** `require_frozen_dda_if_needed()` (bypass E-155) → `build_governance_context()` roles art.11 best-effort → `build_branding_pdf_context()` logo MinIO → `render_docx()` [docxtpl · `_SilentUndefined` · `_inject_brand()` logos · `_default_firmas()` · filtros ES] → `sign_document()` SHA-256+Ed25519 → `convert_docx_to_pdf()` LibreOffice 60s → `put_object()` MinIO best-effort → `Document` INSERT `storage_path minio://` → `_emit_audit_log()` `document.generated` Sub-atom 5.A.

**Estados**: `generado` → `firmado` → `entregado` → `obsoleto`.

---

### Lógica negocio notable

- **GATE DdA congelada** para políticas/procedimientos/entregables · `enforce_gates=False` solo E-155 (upstream DdA).
- **Tier-aware policy signoff**: BÁSICA 10 / MEDIA 18 / ALTA 25 políticas · bulk SHA-256 deterministic input M05.
- **4 niveles CCN-STIC 805** derivados dinámicamente del registry (R25 drift-proof) · nivel 4 vacío hasta primer cliente.
- **POS acumulativo**: BÁSICA 17 POS ⊆ MEDIA ⊆ ALTA (todos) · E-235 sellado tiempo solo-ALTA.
- **`aplica_micro`** flag catalog: excluye plantillas desproporcionadas para autónomos/microempresas.
- **MinIO durable**: key `fulkro/projects/{id}/m06/{hash12}_{codigo}_{ts}.{ext}` · best-effort graceful degradation.

---

### Integraciones cross-motor

M01 (DICAT E-155) · M02 (activos/riesgos E-040) · M03 (cumplimiento DdA E-040) · M05 (bulk signing intent) · M09 (auditoría E-040) · M21 (portal auth) · M24 IDMS (`folder_id`) · M30 (roles art.11) · MinIO `fulkro-documents` · `fulkro_identity` constantes rendering (F-14-01).

---

### Tests

32 ficheros · **104 funciones** · ~7.157 LOC. Cubre catalog_loader · service · rendering · signing · policy_signoff · documentation_levels R25 · governance_context · registry · excel_generators · generadores especializados.

---

### Patrones / gotchas

- **`docxtpl` requiere raster PNG**: logo SVG no embebible · `fulkro-logo.png` generado desde SVG (F-14-02).
- **LibreOffice headless**: dependencia infra · 60s timeout · ausencia = `PDFConversionError` non-fatal (`pdf_warning`).
- **`copy.deepcopy(context)`** antes de inject brand: evita tipos no-JSON en `context_snapshot` JSONB.
- **`_set_document_rls`**: `SET LOCAL ROLE fulkro_app_bypassrls` + `RESET ROLE` para lookup pre-RLS.
- **E-PF-001/E-IT-001**: procedimientos que vivían como bloques Jinja descartados silenciosamente (R13) — ahora separados.
- **Firmado graceful**: sin clave Ed25519 test env → fallback solo SHA-256.

---

### Veredicto: COMPLETO

Motor production-grade. 86 plantillas YAML + 83 en registry + 131 cuerpos .md. Pipeline render→sign→PDF→MinIO implementado end-to-end. Portal cliente policy review + bulk signoff integrado M05. 16 Excel generators. 104 tests cross-paths críticos. Integraciones M01/02/03/05/09/21/24/30 verificadas en código.

---

### Discrepancias CLAUDE.md vs código

1. **CLAUDE.md afirma "96 plantillas" (tag s1B) y "104 entries" (1.D.F.tris)** · código real: 86 entradas `template_catalog_v1.yaml` · 83 en `TEMPLATE_REGISTRY` · 131 `.md` (incluye extras no registrados). Ninguna cifra coincide con las 3 afirmaciones históricas.
2. **`template_resolver.py`** presente en directorio pero no documentado en CLAUDE.md.
3. **`stakeholders_helper.py`** presente sin mención en CLAUDE.md.
4. **`templates/other/`** vacío — categorías `apendice_f`/`instruccion_tecnica`/`registro` definidas en `enums.py` pero sin plantillas `.md` reales.

---

### Medidas ENS cubiertas

`org.1/2/3` · `op.acc.1-6` · `op.exp.4/5/7/8` · `op.cont.1-4` · `op.ext.1-4` · `mp.per.1-4` · `mp.info.2-6` · `mp.info.4` (E-235 ALTA) · `mp.com.1/3` · `mp.sw.1` · `mp.si.1-5` · `mp.if.*` · `mp.eq.7` · E-041 Declaración Conformidad · E-808 Autoevaluación DdA CCN-STIC 808/809.


## 25 - M07 Evidencias (WORM) + M10 Simulacro auditoria pre-ENAC

### Alcance leido
15 .py M07 + 4 .py M10 + ORM models + 11 test files M07 + 1 test M10 + migraciones `e41cd7163c02`, `evidence_requests_001`, `97cf56901d4a`.

---

## M07 Evidencias

**Proposito**: pipeline upload evidencias ENS: MIME + magic-bytes, SHA-256, Ed25519, ClamAV async, WORM post-clean, caducidad, renovacion, verificacion.

**Ficheros**: `api.py` · `public_router.py` (sin auth) · `ingestion_service.py` (10 pasos) · `signing.py` (Ed25519 `FULKRO_M07_SIGNING_PRIVATE_KEY`) · `verification_service.py` (GOTCHA) · `antivirus_scan_service.py` (ClamAV+WORM+cuarentena) · `freshness_service.py` · `renewal_service.py` · `ai_classifier_service.py` (18 reglas R1) · `content_extraction_service.py` (PDF/OCR) · `request_service.py` (FSM 6 estados) · `tasks.py`.

### Tabla `evidence`
`project_id` FK (sin `client_id`) · `measure_id`+`measure_code` · `hash_sha256` · `firma_ed25519` hex · `scan_status` server_default='scanning' · `scan_result_jsonb` (incluye `worm_uri`) · `metadata_extra` JSONB (`lectura_ia`) · `vigente` · 2 partial indexes scan_status. **RLS**: `project_isolation` via `e41cd7163c02`.

Aux: `evidence_renewal_requests` (idempotente) · `evidence_requests` FSM 6 estados RLS via `evidence_requests_001`.

**Storage**: disco `var/evidences/{pid}/{eid}{ext}` primario. Post-scan-limpio → MinIO `fulkro-evidence-worm` Object Lock COMPLIANCE (`FULKRO_WORM_RETENTION_DAYS`=2555d). URI en `scan_result_jsonb["worm_uri"]` (sin columna dedicada).

### Endpoints
`POST /evidence/projects/{pid}/upload` · `GET .../list` · `GET .../expiring` · `POST .../evidence/{eid}/renew` · `GET .../evidence/{eid}/verify` · `GET /evidence/public-key` (sin auth). Auth: `require_marcos_or_client` + guard cross-tenant (404 mismatch, no 403).

### Logica critica + gotchas
- **Ingestion**: magic-bytes HTTP 415 pre-ingest + 10 pasos con `flush()` antes de Celery `.delay()`.
- **GOTCHA verificacion**: `verify_evidence` comprueba SHA-256 OK y que firma tiene 64 bytes, pero NO re-verifica Ed25519 criptograficamente (timestamp del payload no se almacena). `signature_valid=True` es estructural, no criptografico.
- **Celery**: `scan_evidence_file_task` usa `asyncio.run()` dentro task sincrono (conflicto potencial eventlet/gevent).
- **Janitor**: re-encola stuck >5 min, marca error >30 min (cada 10 min via Celery beat).
- **WORM**: solo post-antivirus-clean, best-effort (fallo no bloquea).

### ENS cubiertas (M07)
`mp.info.3/6` (integridad+WORM 7a) · `mp.s.5` (ClamAV) · `op.acc.5/6` (MFA) · `op.exp.10` (pentest) · `org.1-3` · `op.pl.1-2` · `mp.per.3` · `mp.com.4`.

### Tests M07: 11 ficheros ~2.200 LOC (ingestion, signing, verification, freshness, renewal, catalogo, antivirus, FSM, classifier, API).

---

## M10 Simulacro Auditoria pre-ENAC

**Proposito**: auditor virtual ENAC determinista (R1, 0 LLM). 73 medidas Anexo II cruzando M6+M7+M3+M8. Score 0-100, madurez L0-L4, DOCX export.

**Ficheros**: `audit_simulator.py` (`AuditSimulatorService` orquestador ~625 LOC) · `audit_questions.py` (73 preguntas + assert 783 LOC) · `api.py` (10 endpoints `require_owner` Marcos).

### Tablas ORM
**`audit_simulation_runs`**: `project_id` · `categoria` · `estado` · contadores · `score_global` · `nivel_madurez_global` · `scores_por_familia` JSONB · `recomendacion`. **Sin RLS propia**.
**`audit_simulation_findings`**: `run_id` · `measure_code` · `evaluacion` (5 valores) · `nivel_madurez` L0-L4 · `contradiccion_detectada` · `evidencia_ids` JSONB · `pentest_finding_id`. **Sin RLS propia**.

### Algoritmo evaluacion (7 pasos deterministas por medida)
1. DdA `no_aplica` → salida
2. Documento por `template_codigo` en `documents`
3. Evidencias por `measure_code` en `evidence`
4. Hallazgo pentest critical/high via M8
5. Contradiccion: DdA=implantado sin evidencia OR con pentest critico
6. `_evaluate()`: NC_mayor si sin_nada|pentest_sin_evidencia · NC_menor si doc_falta|evidencia_caducada · conforme si vigente+suficiente
7. Madurez: L0(nada) L1(doc_sin_ev) L2(ev_caducada) L3(vigente)

**Score**: conforme=100, obs=75, nc_menor=25, nc_mayor=0 — media sobre evaluables.
**Recomendacion thresholds**: >=85&&nc_mayor==0→`apto` · >=70&&<=2→`remediacion_menor` · >=50→`remediacion_mayor` · else→`no_presentar`.

**Assert**: `assert _aq_codes == _anexo_codes` falla en import si falta/sobra medida. Alineado 2026-06-07 con RD 311/2022 (antes 58 con codigos RD 3/2010 derogados).

**Endpoints** (10): preguntas catalogo · families · por code · POST runs · GET runs/run/findings/report/docx/summary.

**ENS M10**: las 73 medidas Anexo II completo (16 familias org/op.pl/op.acc/op.exp/op.ext/op.nub/op.cont/op.mon/mp.if/mp.per/mp.eq/mp.com/mp.si/mp.sw/mp.info/mp.s).

---

## Discrepancias CLAUDE.md vs codigo real

| # | CLAUDE.md afirma | Codigo real |
|---|---|---|
| D1 | `SimulacroPreEnacService` (Sesion 3B-2B.10) genera PDF reportlab ~9.209 bytes + Ed25519 como parte de M10 | Este servicio NO existe en `m10_audit_sim/`. M10 genera DOCX via python-docx. El servicio PDF mencionado es externo a la parcela. |
| D2 | `corrective_loop_service` como parte del ecosistema M10 | No existe en `m10_audit_sim/`. Vive fuera de la parcela. |
| D3 | Verificacion Ed25519 de evidencias correcta | `verification_service.py` solo verifica longitud 64 bytes, NO re-verifica criptograficamente (timestamp perdido). |
| D4 | `audit_simulation_runs` + `findings` con RLS | Sin policy RLS propia en BD verificada. Aislacion solo via `set_tenant_context` API. |

## Veredicto
- **M07**: **completo** — pipeline productivo, 11 test files ~2.200 LOC, WORM real, ClamAV real (Hetzner-only). Gotcha: verificacion Ed25519 estructural, no criptografica real.
- **M10**: **completo** (core) — 73 medidas RD 311/2022, determinista L0-L4, DOCX, 470 LOC tests. Gaps: sin RLS BD propia, sin audit_log (Sub-atom 5.A no propagado), `SimulacroPreEnacService` con PDF+Ed25519 citado en CLAUDE.md esta fuera de esta parcela.


## 26 - M08 Verificacion - nucleo autopilot pentest

**Dominio**: motor de verificacion tecnica (pentest) autopilot. Entre Gate humano 1 (autorizacion/scope) y Gate humano 2 (atestacion solo ALTO) todo es automatico: recon -> deteccion (MCP) -> normalizacion -> ZFP 5 gates -> enrich CVSS/EPSS + dedup -> mapeo ENS/MITRE -> Finding canonico -> triage agentico (Verdict advisory anti-injection) -> asset graph -> evidencia R6 -> coverage% + golden drift -> revoca sesion. Implementa `ADR-055`/`M8_AUTOPILOT_ARCHITECTURE_v2`. Alcance leido: todos los ficheros de la parcela (`models`, `finding_state_machine`, `gates`, `orchestrator`, `agent/*`, `determinism`, `normalization`, `enrichment`, `fp_patterns`, `autopilot_api`, `ephemeral_connector`, `offensive_*`); `fp_patterns/catalog.py` (781 LOC) y `zfp_engine.py` muestreados.

### Ficheros clave
- `autopilot/orchestrator.py` (587) - pipeline `orchestrate_run` + `process_and_persist` + `collect_candidates`; fail-closed.
- `finding_state_machine.py` (141) - 9 estados + transiciones + guard anti-injection en `false_positive`.
- `gates.py` (93) - capa fina §5 (visibilidad + verification_level) sobre `zfp_engine`.
- `agent/injection_guard.py` (158) - 11 regex injection + wrap dato/instruccion + `validate_verdict_output` fail-closed.
- `agent/triage_agent.py` (200) - LLM Opus 4.8 temp 0, structured JSON, advisory.
- `determinism/manifest.py` (122) - `run_manifest_hash` sha256 canonico + golden drift.
- `normalization/{adapters,sarif}.py` - MCP->candidate + SARIF 2.1.0 bidireccional.
- `enrichment/{epss,scoring}.py` - cache EPSS offline + `effective_severity` (max con suelo).
- `fp_patterns/{catalog,learner}.py` - 120 patrones FP + aprendizaje.
- `autopilot_api.py` (260) - 6 endpoints admin. `offensive_{provisioner,engagement}.py` - box ofensiva Hetzner efimera.

### Modelo de datos (migracion `m8_autopilot_canonical_001`, down_revision `drop_ens_radar_001`)
- `verification_runs` (extendida) - `run_manifest_hash`, `golden_run_id`, `coverage_pct`, `assets_in_scope/scanned`, `autopilot_status/phase`, `partial_run`, `tools_attempted/failed`, `ephemeral_session_id/expires_at/revoked_at`.
- `verification_findings` (extendida) - `epss_score`, `verification_level` (unverified|passive|active_safe|exploitation), `finding_state`, `dedup_group_id`, `source_engine/engine_version/rule_id`, `asset_node_id`, `sarif_ref`, `risk_accepted_*`.
- `m8_verdicts` (NUEVA, advisory mutable) - `project_id`+`run_id`+`finding_id`, `model_version`, `prompt_hash`, `triage` jsonb, `structured_output_valid`, `human_override`. RLS `project_isolation`.
- `m8_evidence_records` (NUEVA, append-only) - `project_id`/`client_id` RLS, `run_manifest_hash`, `actor`/`action`/`component`, `input_hash`/`output_hash`, `payload`. Triggers `fn_audit_track` (espeja a `audit_log` R6 hash-chain) + `fn_audit_log_immutable` (rechaza UPDATE/DELETE). RLS `project_isolation` + INSERT permisivo.

### Endpoints (admin `require_owner`)
- `POST /projects/{id}/verification/autopilot/start` - Gate 1 done, lanza bg task (sesion propia).
- `GET .../autopilot/status` · `GET .../verification/metrics` (§12) · `GET .../runs/{rid}/evidence-pack` (§16).
- `POST .../findings/{fid}/accept-risk` (§8) · `POST .../runs/{rid}/attest` (Gate 2 ALTO).

### Logica / maquinas de estado / algoritmos
- **5 gates** (en `zfp_engine`, semantica §5 en `gates.py`): G1 dedup, G2 FP-filter determinista (unico que rechaza), G3 umbral confianza (nunca descarta: <0.70 -> anexo tecnico), G4 verificacion (re-test si conf<0.85; aqui vive Zero-FP), G5 clasificacion (confirmed|probable|needs_review|rejected).
- **verification_level** (`derive_verification_level`): solo `active_safe`/`exploitation` sostienen claim Zero-FP; `passive`/`unverified` van etiquetados (honest boundaries).
- **finding_state_machine**: `detected->triaged->verified->reported->in_remediation->retested->closed`; `false_positive` exige `by_active_disproof` O `human_override` (NUNCA por LLM); `risk_accepted` terminal-con-caducidad. `STATE_EVENT_MAP` -> eventos `m08.finding.*`.
- **effective_severity** = `max(suelo_motor, computed(CVSS,EPSS))` - el enrich JAMAS rebaja (regla dura §4).
- **manifest hash** = sha256(canonical_json scope+tools+templates+config+model+snapshot); golden drift por comparacion de hash + drift_fields.
- **CATEGORY_PLAN**: BASICO 4 tools, MEDIO 12, ALTO 18 (nmap/httpx/nuclei/openvas/zap/prowler/semgrep...). safe-by-default; exploitation = Gate 2 humano. ALTO -> `paused_gate2`.
- **dedup_group_id** = uuid5(namespace fijo, finding_hash) estable cross-run/motor.

### Anti-injection (control 1a clase, §7)
- `wrap_untrusted_target_data` separa dato/instruccion y neutraliza cierres de delimitador.
- `detect_injection_attempt` (11 regex ES+EN) -> si match, orquestador genera **finding sintetico** high `M8-INJECTION-GUARD` (mp.sw.1 + op.exp.6); NUNCA suprime.
- `validate_verdict_output` fail-closed: salida invalida -> `structured_output_valid=False`, verdict NO aplicado, finding intacto. `recommended_severity_adjustment=down` validado pero NUNCA auto-aplicado.
- Triage `claude-opus-4-8` temp 0; sin API key -> fail-closed sin LLM (el backbone no depende del agente).

### Medidas ENS
Mapeo real lo hace `ens_mapper.EnsMapper` (fuera de parcela; invocado `enable_llm=False`). Codigos hardcoded en parcela: `mp.sw.1`, `op.exp.6` (injection guard), `mp.s.3` (engagement ofensivo ALTA -> pentester independiente). Informe cliente = E-702 (ref `zfp_engine`). `ens_relevance` se persiste por evidencia (medida primaria del finding).

### Integraciones
- **MCP**: `mcp_client.try_invoke_mcp_or_none`; `USE_MCP_REAL=false` -> None -> 0 candidates -> run PARCIAL coverage 0% (honesto). Auth env `PENTEST_AUTHORIZATION`+`_SIG` (HMAC) -> scope_enforcer fail-closed.
- **LLM**: triage Opus 4.8 advisory; ens/mitre mappers con LLM off en autopilot.
- **SSE**: canal `project:{id}` (`m08_autopilot_started`/`_phase_change`/`_run_completed`), best-effort.
- **audit_log R6** via triggers sobre `m8_evidence_records`/`m8_verdicts`. **magic_links** FKs (authorization + external_portal). `asset_graph` PKG-lite fail-soft, `remediation/risk_acceptance`, `observability`.

### Patrones / gotchas / dead code
- **GOTCHA env-var global**: `collect_candidates`/`offensive_engagement` mutan `os.environ["PENTEST_AUTHORIZATION"]` (restaurado en finally) - NO thread-safe con runs bg concurrentes en el mismo proceso.
- `engine_version=None` hardcoded en `process_and_persist` (col existe, no se rellena en ese path).
- `client_id=None` siempre en EvidenceRecord desde orchestrator -> RLS por `client_id` inactiva en evidencia (solo `project_id`).
- `_safe_llm_available` duplicado orchestrator vs triage_agent (DRY menor). `model_version` Opus hardcoded en manifest aunque no corra triage.

### Veredicto: MIXTO (backbone COMPLETO + ejecucion real DIFERIDA a Hetzner)
- **Completo/produccion**: state machine, gates/verification_level, injection guard, manifest determinista, EPSS offline, scoring, SARIF, FP learner, evidencia R6 append-only, RLS, endpoints, fail-closed. Tests: `test_autopilot_pure` 61, `test_autopilot_integration` 16, `test_f3_anti_injection` 3, `test_offensive_engagement` 4 (~84 def test_).
- **Diferido honesto**: ejecucion MCP real (`USE_MCP_REAL=false` por defecto -> 0 findings en dev/CI); box ofensiva mock-by-default sin `HETZNER_CLOUD_TOKEN`; cache EPSS depende de seed. Frontera honesta declarada, no deuda oculta.


## 27 - M08 Verificacion - tools, integraciones, reports, MCP wiring

**Veredicto**: COMPLETO (produccion-grade). ~18 500 LOC Python. Motor autopilot v2.0 operativo: 7 tablas, 35+ endpoints en 4 routers, pipeline ZFP 5-gates, agente Opus 4.8 anti-injection, observabilidad ENAC, kill switch real, fallback `USE_MCP_REAL=false` seguro para dev/CI.

---

### Ficheros clave

| Fichero | Proposito |
|---------|-----------|
| `models.py` | 7 tablas ORM (ver modelo de datos) |
| `api.py` | 16 endpoints admin runs/findings + kill + reports |
| `public_api.py` | 13 endpoints magic-link: remediation cliente + pentester portal + verify-auth OTP |
| `portal_api.py` | 3 endpoints ClientUser: in-portal pentest authorization (ADR-020 v6) |
| `autopilot_api.py` | 5 endpoints autopilot: run/status/metrics/evidence-pack/accept-risk/attest |
| `mcp_executor_service.py` | Orquestador MCP; catalogo 13 tools; singleton in-memory; auto-attach IDMS folder 13 |
| `ens_mapper.py` | 3-capas CVE→ENS: rule (37 CVEs + 18 patrones), semantica pgvector (stub), LLM Haiku |
| `zfp_engine.py` | Motor Zero-False-Positives 5 gates |
| `finding_state_machine.py` | FSM 9 estados; anti-injection guard (`false_positive` SOLO desmentido activo o override humano) |
| `kill_switch.py` | KillWatcher asyncio 1s tick; SIGTERM→3s→SIGKILL; garantia <5s |
| `autopilot/orchestrator.py` | Backbone: scope→efimera→MCP→ZFP→EPSS/dedup→ENS/MITRE→Verdict→EvidenceRecord R6 |
| `autopilot/ephemeral_connector.py` | Sesion efimera HMAC-firmada TTL 8h; zero standing access; scope-enforcer |
| `agent/triage_agent.py` | Agente Opus 4.8 T=0 ADVISORY; structured JSON; fail-closed si LLM cae |
| `agent/injection_guard.py` | 11 patrones regex anti-injection ES+EN; wrap canal delimitado; validate_verdict_output |
| `tools/base.py` | Contrato `BaseRunner`: `FindingCandidate`, `RunnerResult`, `run_subprocess` SIGTERM/SIGKILL |
| `reports/heatmap_generator.py` | Heatmap 73 medidas ENS Anexo II (compliant/partial/non_compliant/not_verified) |
| `reports/report_generator.py` | E-702/E-703/E-704 via M6 DocumentFactory + firma Ed25519 |
| `normalization/sarif.py` | SARIF 2.1.0 schema comun pure functional |
| `observability/evidence_pack.py` | Pack ENAC: PTES/OWASP WSTG/OSSTMM/CCN-STIC 808/809, RoE, EvidenceRecord, fn_audit_log_verify_chain() |
| `integrations/m3_dda_updater.py` | DdA↔findings cruce bidireccional; detecta contradicciones "implantado"+critical/high |

---

### Modelo de datos y RLS

| Tabla | RLS | Destacado |
|-------|-----|-----------|
| `verification_runs` | SI (`33cef115cdf5` project_id) | `scope_jsonb`, `run_manifest_hash`, `ephemeral_*`, `autopilot_status/phase`, `ssh_credentials` Fernet, `cancel_requested_at` |
| `verification_findings` | SI (misma migracion) | `finding_hash`, `zfp_gate1-5`, `confidence_score`, `ens_measures[]`, `mitre_techniques[]`, `finding_state`, `verification_level`, `epss_score`, `dedup_group_id`, `sarif_ref` |
| `external_pentester_handoffs` | project_id FullMixin | `portal_magic_link_id`, `vpn_credentials_encrypted`, `status` (draft→closed) |
| `false_positive_patterns` | **SIN RLS** (catalogo global Marcos-owned) | `tool`, `pattern`, `times_matched` |
| `remediation_retests` | **SIN RLS propia** (FK via findings) | `retest_type`, `result` (fixed/still_present/error/inconclusive) |
| `m8_verdicts` | RLS permissive + trigger audit_log (`m8_autopilot_canonical_001`) | `triage` JSONB, `structured_output_valid`, `human_override` |
| `m8_evidence_records` | **APPEND-ONLY** triggers PL/pgSQL: INSERT→espeja audit_log R6; UPDATE/DELETE→RECHAZADOS | `actor`, `action`, `input_hash`, `output_hash`, `ens_relevance`, `run_manifest_hash` |

---

### Endpoints (resumen por router)

**Admin** (require_owner · `/projects/{pid}/verification/...`): POST run, GET runs/runs/{rid}/findings, PATCH finding/mapping, POST retest/handoff/ingest/report, GET remediation-plan/heatmap/score/delta/by-measure, POST kill.

**Autopilot** (require_owner): POST autopilot/run, GET autopilot/status, GET metrics, GET runs/{rid}/evidence-pack, POST findings/{fid}/accept-risk, POST runs/{rid}/attest.

**Publico magic-link**: GET/POST remediation/{token}/*, GET pentester-portal/{token}/documents/vpn-config, POST findings/upload-pdf/complete, GET/POST verify-auth/{token}/request-otp/submit.

**Cliente portal**: GET authorization, POST mark-reviewed, GET document-hash.

**MCP executor**: POST execute, GET executions/catalog, SSE events stream.

---

### Pipeline ZFP 5 gates

1. **Dedup**: `finding_hash = SHA256(title+host+port)` → acumula `tool_sources`
2. **FP filter**: consulta `false_positive_patterns` (~500 patrones); match → `rejected`
3. **Cross-tool**: si `len(tool_sources) > 1` → `confidence += 0.15`
4. **Retest**: si `confidence < 0.85` y categoria >= MEDIO → retest nuclei/testssl/nmap
5. **Clasificacion**: `confirmed ≥0.85 | probable 0.65-0.84 | needs_review 0.40-0.64 | rejected <0.40`

Solo `confirmed` y `probable` van al informe E-702.

---

### ENS Mapper 3 capas

- **Capa 1a** rule CVE (confidence 0.95): 37 CVEs explicitos (Log4Shell, ProxyShell, EternalBlue, BlueKeep, Heartbleed, pwnkit, XZ backdoor, Fortinet, ConnectWise, MOVEit, etc.)
- **Capa 1b** rule patron (confidence 0.85): 18 patrones titulo/descripcion (TLS 1.0, weak cipher, SQLi, XSS, CSRF, DNSSEC, SPF/DKIM/DMARC, AD password policy, SSH hardening, default creds, backups expuestos)
- **Capa 2** semantica pgvector: **STUB** — devuelve `[]` permanentemente. Comentario "Future Checkpoint 3+".
- **Capa 3** LLM Haiku 4.5 structured output: activa cuando capas 1+2 fallan; umbral confidence 0.5; fail-graceful

---

### Agente y anti-injection

- Opus 4.8, T=0, max_tokens 800. Rol: ADVISORY puro; emite Verdict JSONB (`exploitability_in_context`, `false_positive_likelihood 0-1`, `recommended_severity_adjustment`).
- **Regla dura**: Verdict NUNCA muta Finding. Bajar severidad → verificacion activa determinista u override humano. Jamas auto-aplica.
- `injection_guard`: 11 patrones regex (ignore_previous, you_are_now, mark_false_positive, declare_safe, suppress_findings, override_severity…). Detection → finding `high` elevado (`M8-INJECTION-GUARD`).
- Fail-closed: salida invalida → `structured_output_valid=False`; finding permanece.

---

### Integraciones cross-motor

| Motor | Modulo | Tipo |
|-------|--------|------|
| M3 DdA | `integrations/m3_dda_updater.py` | Read-only; contradicciones implantado+critical |
| M5 Signing | `integrations/m5_obligations.py` | Ed25519 informes E-702/E-704 |
| M6 DocumentFactory | `reports/report_generator.py` | DOCX+PDF E-702/E-703/E-704 |
| M7 Evidence | `integrations/m7_evidence.py` | EvidenceRecord por finding (idempotente) |
| M9 Audit prep | `integrations/m9_audit_prep.py` | Summary tecnico + matriz 99 findings-by-measure |
| M24 IDMS | `mcp_executor_service` | Auto-attach JSON resultado a folder "13_Informes_Tecnicos" |
| MCP Arsenal | `try_invoke_mcp_or_none` | 13 tools; USE_MCP_REAL gated |

---

### Medidas ENS cubiertas directamente

`op.acc.4/5/6` · `op.exp.3/4/5/6/10` · `mp.com.2/3` · `mp.s.1/2` · `mp.sw.1/2` · `mp.info.6`. Heatmap evalua las 73 medidas ENS Anexo II (not_verified cuando no hay findings).

---

### Patrones y gotchas

- **USE_MCP_REAL=false** (default): `fase_runner` devuelve 0 candidates honestos; `mcp_executor_service` retorna `{_simulated: True}`. NO inventa hallazgos.
- **Binarios reales**: requieren imagen `fulkro-scanner` en Hetzner. `shutil.which()` check → `RunnerNotInstalled`.
- **Sesion efimera**: HMAC `app_secret_key`; TTL 8h; `ephemeral_*` en `verification_runs`; revocacion al cierre.
- **Background tasks**: `_tasks: set[asyncio.Task]` previene GC mid-op; `wait_pending_tasks()` shutdown limpio.
- **TODO abiertos**: G1 ML auto-FP (post-MVP), G2 Lynis-SSH remoto (Fernet parcial), G3 scan_window via M14 (parcial en scope_deriver).

---

### Discrepancias con CLAUDE.md

- CLAUDE.md: "88 mappings CIS/CVE → ENS Anexo II". Codigo real: **37 CVEs + 18 patrones** = 55 mappings explicitos en `ens_mapper.py`.
- CLAUDE.md: presenta capa 2 semantica pgvector como existente. Codigo real: **stub permanente** `return []` con comentario "Future Checkpoint 3+".
- CLAUDE.md: "14 MCP servers". Codigo real: **13 tools** en `MCP_TOOLS_CATALOG` (4+4+4+1).
- `false_positive_patterns` y `remediation_retests`: **sin RLS row-level**. No mencionado en CLAUDE.md. Mitigado por require_owner pero es deuda de hardening menor.


## 28 - M09 Preparacion auditoria / dossier ENAC

### Proposito

Motor de preparacion auditoria ENS. Dos sub-motores: **M9-A** checklist pre-auditoria (5 checks, readiness score 0-100, blockers gate) y **M9-B** generacion dossier ENAC (ZIP 15 carpetas, MANIFEST Ed25519, Matriz-99 XLSX, portal auditor magic-link). Aloja servicios transversales reutilizables cross-motores.

### Ficheros clave

| Fichero | Rol |
|---|---|
| `api.py` | 22 endpoints admin `require_owner` prefix `/audit-prep/projects/{id}/*` |
| `checklist_service.py` | 5 checks + readiness score + blockers gate ≥85 + readiness_quick |
| `dossier_generator.py` | ZIP 15 carpetas + MANIFEST firmado Ed25519 + DEC-4 caps binarios MinIO |
| `public_api.py` | 14 endpoints portal auditor `/public/auditor-portal/{token}/*` magic-link |
| `simulacro_pre_enac_service.py` | Orchestrator ~80 LOC: 6 servicios compuestos + pentest_summary |
| `dda_evidence_gap_service.py` | Gap matrix DdA ↔ Evidence por medida ENS (pure functional) |
| `draft_report_generator.py` | PDF 9 secciones reportlab platypus + firma Ed25519 (weasyprint NO instalado) |
| `audit_log_integrity_checker.py` | Wrapper `fn_audit_log_verify_chain()` + SHA-256 per-proyecto |
| `corrective_loop_service.py` | SM `open → in_progress → closed` sobre `audit_log` (ADR-025) |
| `matriz_99.py` | XLSX openpyxl medida × evidencia × documento × gap × carpeta |
| `coaching.py` | Preguntas role-based (direccion/rseg/admin/tecnico) + medida ENS |
| `internal_auditor.py` | Agente 11 — 10-15 preguntas deterministas E-701 (sin LLM) |
| `audit_events.py` | 39 constantes canonicas `accion` audit_log — fuente unica |

### Modelo de datos

**Tablas propias** (RLS via `project_id`):

- `audit_preparation_runs`: `project_id` FK, `categoria`, `estado`, `readiness_score`, `checklist_results` JSONB, `dossier_generated_at`; cols `dossier_zip_path` / `matriz_99_path` presentes pero **no usadas** (ZIP on-demand en memoria — dead columns)
- `audit_checklist_items`: `run_id` FK, `project_id` FK, `categoria_check`, `referencia`, `estado`, `severidad`, `resuelto`, `resuelto_por`

**Corrective loops**: NO tienen tabla propia; estado derivado de `audit_log ORDER BY seq DESC LIMIT 1` por `loop_id` (ADR-025 sostenido).

**Tablas externas**: `dda_entries`/`ens_measures` · `evidence` · `documents`/`document_versions` · `audit_log` · `verification_runs`/`verification_findings` · `basic_declarations` · `magerit_analysis`/`magerit_assets` · `project_plans`/`wbs_tasks`

### Endpoints

**Admin** (prefix `/api/v1/audit-prep`, `require_owner`): POST/GET runs · GET/PATCH/DELETE items · GET contradictions/summary/readiness · POST generate-dossier/generate-signed-zip/cleanup · GET dossier-download/matriz-99/coaching · POST simulacro-pre-enac/execute · GET simulacro-pre-enac/last-report

**Portal auditor ENAC** (`/api/v1/public/auditor-portal/{token}`): GET metadata · POST session (OTP step-up) · GET summary/dda/magerit/plan/evidence/e041/audit-log/pentest/documents/dossier.zip/audit-log.csv · GET evidence/{id}/download

### Logica de negocio

**Checklist M9-A** — `run_full_checklist` (5 pasos): (1) `check_deliverables` E-XXX vs `documents.template_codigo` (BASICA 43 · MEDIA 81 · ALTA 107); (2) `check_evidence_freshness` por DdA aplicable, warning <30d; (3) `check_operational_records` 6 meses por mes; (4) `check_signatures` `REQUIRE_SIGNATURE` set (E-001/005/012/040/050 + E-100..E-126 + criticos); (5) `cross_validate_dda_evidence` `implantado` sin evidencia + findings M08 high/critical. **Readiness score**: entregables 30% + evidencias 30% + sin contradicciones 20% + firmas 10% + registros 10%. Gate dossier final: ≥85 Y blockers vacios.

**Dossier generator**: 15 carpetas `00_INDICE`..`99_MATRIZ_CRUZADA`. `classify_folder(E-XXX)` tabla + fallback prefijo numerico. DEC-4: BASICA 200 MB / MEDIA 500 MB / ALTA 1 GB total; 50 MB/doc; artefactos canonicos (`E-040 E-041 E-808C E-130 E-131 E-049`) whitelist NUNCA omitidos. `sign_manifest=True AND force=True` → DossierError. Binarios MinIO embebidos solo en dossier firmado.

**Simulacro Pre-ENAC**: pipeline dry-run A11 → gap matrix → workflow state M11 → integrity check → open corrective loops critical/high → draft report PDF. Bug fix P0-2 en prod: `critical_gaps` leia `severity_summary.critical_count` (inexistente) — corregido a `severity_summary.critical_missing`; sin fix GATE-7 era ciego a NC mayores.

**Portal auditor**: rate-limit SOLO path invalido (10 fallos/60s) — bug historico corregido (el valido no limita a auditor navegando). OTP step-up si `otp_hash`. `_validate_token_peek` usa `SET LOCAL ROLE fulkro_app_bypassrls`. `emit_auditor_event` inserta ClientInteraction + audit_log (Sub-atom 5.A 3-way OR).

### Medidas ENS cubiertas

Todas las familias Anexo II RD 311/2022: `org.*` (politica, normativa, autorizacion) · `org.pl.*` (planificacion) · `op.acc.*` (≥3 evidencias) · `op.exp.*` (registros 6m) · `op.mon.*` · `op.cont.*` (E-400/E-500..E-504) · `mp.s.*` (`mp.s.2` pentest + vuln-scan) · `mp.com.*` · `mp.info.*` · `mp.sw.*` · `mp.if.*` · `mp.per.*`. Cobertura empirica BASICA ~46/52 aplicables.

### Integraciones

**M05** sign_payload + get_public_key_pem (MANIFEST + draft PDF) · **M06** documents E-XXX · **M07** evidencias vigentes + scan_status + descarga fichero · **M08 v5.1** collect_findings_for_dossier + count_findings_by_measure + pentest_summary raw SQL · **M11** compute_workflow_state (simulacro) · **M12** AUDITOR_PORTAL_ENAC purpose + OTP step-up · **M24** STANDARD_FOLDERS alias legacy · **M27** ConformityServicePaso5 + BasicDeclarationRow dossier · **audit_log R6** fn_audit_log_verify_chain + triggers SHA-256 · **MinIO** get_object binarios dossier firmado

### Tests

21 ficheros · **256 funciones** en `backend/tests/motors/m09_audit_prep/`. Paths: checklist (28) · dossier (44+11 signed) · paso4 (30) · gap service (20) · corrective loop (10) · integrity (6) · simulacro (4) · auditor portal A/B/C (30) · annotations+clarifications (20) · draft report (20) · audit events (14).

### Gotchas y deuda tecnica

1. **N+1 `list_open_loops`**: un SELECT por loop_id; sin cache. No bloquea piloto.
2. **`classify_folder` fallback** retorna `"08_REGISTROS_OPERATIVOS"` (legacy incorrecto) — `_LEGACY_FOLDER_ALIASES` lo mapea en el ZIP pero el string es inconsistente.
3. **Portal auditor `evidence/{id}/download`** usa `fichero_path` filesystem, NO MinIO. Si evidencia solo tiene `storage_path minio://...` → 404.
4. **`check_evidence_freshness`** `pass` silencioso cuando `measure_code is None` y `measure_id not None` — esas evidencias no se indexan (sub-conteo potencial).
5. **`pdf_master_generator`** requiere LibreOffice headless; graceful-fallback (warning). En Hetzner piloto LibreOffice no confirmado.

### Discrepancias CLAUDE.md vs codigo

- "18 backend tests NEW PASS" Ejecutable 5: consistente — Ejecutable 5 solo anadio 18; los 238 previos son de sesiones anteriores.
- "9209 bytes typical PDF simulacro": no verificable (tests simulacro son scaffold-level, sin fixture de tamano).
- `dossier_zip_path` / `matriz_99_path` presentes en ORM pero son dead columns (ZIP siempre on-demand en memoria).

### Veredicto: COMPLETO

Motor production-grade y el mas rico en logica de todo el backend. 256 tests cubren paths criticos. Deudas menores (N+1 loops, fichero_path vs storage_path auditor, dead columns) no bloquean piloto. Portal auditor ENAC funcional end-to-end (magic-link gated, OTP, 39 eventos canonicos, hash chain verifiable, ZIP firmado Ed25519).


## 29 - M11 Copiloto (motor)

### Propósito y dominio

Motor de asistencia RAG-backed para Marcos (admin) y clientes del portal. Orquesta el pipeline A14 (`agents/agent_14_copiloto/`) sin reimplementarlo: m11 provee endpoints HTTP, persistencia de conversaciones, scheduler de nudges proactivos y el `workflow_state_scanner` reutilizable cross-motor (simulacro, admin dashboards, etc.).

### Ficheros clave

| Fichero | LOC | Rol |
|---|---|---|
| `api.py` | 921 | Endpoints admin: chat, stream, hint, CRUD conversaciones, context, summary, quick-actions, projects-selector, admin-nudges |
| `portal_api.py` | 857 | Endpoints cliente: chat, stream, coach, hint, quick-actions · RLS F-18-01 |
| `workflow_state_scanner.py` | 909 | `compute_workflow_state` pure functional (10 fases, 2 roles, governance FASE 0 lazy) |
| `conversation_service.py` | 192 | CRUD conversaciones + `persist_message_best_effort` (OPS-047 timestamp μs) |
| `inline_agents_api.py` | 234 | 10 agentes inline tier-aware (A04/A06/A11/A12/A18/A19/A20/A21/A27/A31) |
| `nudge_scheduler.py` | 381 | Nudges cliente (Pattern #15 · cooldown 24h · priority cap "high" · R29) |
| `admin_nudge_scheduler.py` | 309 | Nudges admin (72h inactividad · cooldown 7d · solo urgent · in-app) |
| `coach_tasks.py` | 110 | Celery tasks `scan_pending_nudges` + `scan_pending_admin_nudges` (beat daily 09:15) |

### Modelo de datos (`models/copilot.py`)

| Tabla | RLS relevante | Notas |
|---|---|---|
| `copilot_conversations` | `project_id` FK projects, `client_id` FK clients nullable | `FullMixin` UUID PK + soft-delete. `client_id` backfill vía `s3b2b4_copilot_client_id_001` |
| `copilot_messages` | `conversation_id`, `project_id` | JSONB citations + chunk_ids_used. Tokens input/output almacenados. |

RLS 3-way OR (`project_id OR client_id OR NULL-NULL`) fijada via `_set_project_rls` / `_set_client_rls` + WHERE explícito (belt+suspenders).

### Endpoints reales

**Admin** (`/api/v1/` · `require_owner`): POST `/copilot/chat`, POST `/copilot/chat/stream`, GET `/copilot/quick-actions`, GET `/copilot/hint`, GET `/copilot/projects`, GET `/copilot/admin-nudges`, POST/GET/DELETE `/projects/{id}/copilot/conversations[/{conv_id}]`, GET `/clients/{id}/copilot/conversations`, POST `/projects/{id}/copilot/conversations/{conv_id}/chat`, POST `/projects/{id}/copilot/context`, GET `/projects/{id}/copilot/summary`.

**Cliente** (`/api/v1/client-portal/copiloto/` · `get_current_client_user`): POST `/chat`, POST `/chat/stream`, POST `/coach`, GET `/coach/next-step`, GET `/quick-actions`, GET `/hint`.

**Inline agents** (`/api/v1/client-portal/inline-agents/`): lista + invoke 10 agentes tier-filtrados.

### Lógica de negocio

- **Pipeline RAG**: delegado íntegro a `agents/agent_14_copiloto/service.py` (717 LOC). Pasos: detect_filters → hybrid_search (fastembed e5-large 1024dim + pgvector) → build_messages → LLM claude-sonnet T≤0.2 (R3) → citation_validator → `LLMInteractionLog`. m11 solo llama `answer_question` / `stream_answer_question`.
- **`compute_workflow_state`**: pure functional (NO HTTP, NO side-effects, JSON-serializable). 10 fases `WorkflowPhase` → catálogo `_PHASE_ACTIONS` (admin+cliente) → governance FASE 0 (m17 import lazy) → `_apply_level_adaptations` por categoría (BÁSICA autodeclaración, MEDIA vuln-scan, ALTA pentest CPSTIC). `_detect_blockers` (DB-backed): DdA sin firma (IMPLANTACION), pentest auth pendiente (ALTA), espera ENAC (CONFORMIDAD), separación roles (m30), cadencia comité. `_detect_evidence_gap_measures` SQL cruzado dda_entries+ens_measures+evidence `scan_status='clean'` → top-3 medidas con gap (admin R30 only, NUNCA cliente R29).
- **Rate limit** (F-13-01, `copilot_rate_limit.py` 234 LOC): `enforce_rate_limit_or_raise(tier, project_id)` derivado de `LLMInteractionLog` (ADR-025 sin nueva tabla). Por-proyecto para cliente (evita quota poisoning cross-tenant).
- **Memoria N6** (`copilot_memory.py` 121 LOC): `load_conversation_history` + `persist_exchange` (client_id+project_id+client_user_id). Sesión separada best-effort.
- **Coach mode** (Phase 4A): inject `coach_mode=True + current_phase + pending_action` en `PageContext` → `build_base_system_prompt` añade sección R29.

### Integraciones

- **A14** (`agents/agent_14_copiloto/`): único pipeline RAG real, m11 lo consume sin duplicar.
- **M17 FASE 0** (`fase0_governance.compute_fase0_governance_state`): import lazy en scanner.
- **M30 contactos**: inyectado en user message por A14 service.
- **M20 Notifications** (`NotificationEvent` event_type `admin.copilot.nudge`): nudges admin.
- **audit_log** Sub-atom 5.A 3-way OR: hint, asked, answered, coach (best-effort, never blocks Q&A).
- **Celery beat**: `scan_pending_nudges` (cliente) y `scan_pending_admin_nudges` (admin) daily.
- **`admin-nudges` endpoint**: bypass RLS via `SET LOCAL ROLE fulkro_app_bypassrls` inline (funcional pero inconsistente con constante nombrada del resto).

### Medidas ENS (indirectas)

m11 no implementa medidas ENS directamente; actúa como orquestador de conocimiento normativo que cita `op.acc.*`, `op.exp.*`, `mp.s.*`, `org.*` via corpus RAG. Por su rol en el workflow:
- `op.pl.1` / `org.4`: governance hints FASE 0 (kickoff, alcance, comité, plan adecuación E-150)
- `op.mon.1`: workflow hint detecta blockers + evidence gaps en fases de implantación/verificación
- `op.exp.3`: copiloto guía estado del proyecto (configuración y estado de medidas)

### Gotchas / Deuda técnica

- **Bug latente nudge_scheduler.py**: `compute_pending_nudges` hace SELECT projects sin fijar RLS context previo → en prod (fulkro_app, sin bypassrls) devolvería 0 proyectos. El admin_nudge_scheduler sí itera por cliente (fix consciente). El cliente nudge NO tiene el fix análogo. Comentado en el código pero no corregido.
- **TODO-RBAC-PER-ENDPOINT-001** (api.py L45): RBAC por endpoint pendiente; actualmente require_owner cubre todo el router admin.
- **Inline agents rate-limit**: comentario L15 "Rate limit deferred to atom 7.5 with Redis" → no implementado.
- **workflow_state_scanner %**: heurístico 50% para fases post-ADECUACION (Future-X `workflow-scanner-percentage-refinement`).

### Discrepancias con CLAUDE.md

- CLAUDE.md nombra el motor como `m11_rag` y lo clasifica "backend-only · NO UI". Empíricamente se llama `m11_copiloto` y tiene UI cliente completa (`portal_api.py` 857 LOC activo en main.py).
- CLAUDE.md clasifica A14 "service-level NO UI dedicada". Empíricamente m11 expone UI cliente en `/client-portal/copiloto/*` (chat+stream+coach+hint+quick-actions) que consume A14 directamente.

### Veredicto: **completo**

9 ficheros Python (~3.900 LOC), 19+ endpoints admin+cliente operativos, 18 ficheros de test en `tests/motors/m11_copiloto/` + `tests/agents/agent_14_copiloto/`. Deuda acotada: bug RLS nudge cliente + rate-limit inline agents pendientes (no bloquean piloto).


## 30 - M12 Magic links (Ed25519, 23 purposes)

### Propósito

Motor de autenticación sin cuentas permanentes (R5). JWTs firmados con Ed25519 para que clientes externos (RSEG, auditor, pentester, leads) ejecuten operaciones sensibles sin tener cuenta en la plataforma. Clave en `FULKRO_ML_PRIVATE_KEY`; dev genera par efímero con WARNING.

### Ficheros clave

| Fichero | Contenido |
|---|---|
| `purposes.py` | Enum `MagicLinkPurpose` (37 valores) + `PURPOSE_CONFIG` TTL/max_uses/otp/geo |
| `service.py` | `MagicLinkService` — generate / consume / revoke / status / list / by-token |
| `api.py` | Router 6 endpoints `/magic-links/…` |
| `policy_enforcer.py` | ADR-042 categorías A-F, 15 ok + 22 hard-rejected |
| `emails/renderer.py` | 32 plantillas HTML/text Jinja2 |
| `schemas.py` | Pydantic I/O Generate / Consume / ListItem / PublicStatus |

### Modelo — tabla `magic_links`

Columnas: `project_id` (FK RLS), `tipo_operacion` (String 50), `scope` (JSONB), `token_hash` SHA-256 (**nunca** JWT), `otp_hash` SHA-256, `expira_at`, `max_usos`, `usos`, `revocado`+`revoked_at`, `otp_failures` (≥3 bloqueo), `recipient_email`, `allowed_countries` JSONB, `sent_to_contact_id` FK M30 ON DELETE SET NULL, `cc_emails` TEXT[], `custom_subject`, `custom_body_intro`.

`client_interactions`: audit trail append-only (magic_link_id, accion, ip, user_agent, timestamp, payload JSONB). RLS: consume/revoke/list bypassan vía `bypassrls` (token_hash cross-project).

### Enum MagicLinkPurpose — 37 purposes (no 23)

| Grupo | Count |
|---|---|
| Base original | 8 (`FIRMA_DOCUMENTO`…`DESCARGA_DOSSIER_FINAL`) |
| M8 verificación | 5 (`AUTORIZAR_PENTEST_EXTERNO`, `PORTAL_REMEDIACION`…) |
| M25 lifecycle | 3 (`OFERTA_RETAINER`…) |
| M21 portal + A15 | 3 (`PRIMER_ACCESO_CLIENTE`…) |
| M23/M27 reporting | 3 (`REPORTE_TRIMESTRAL`…) |
| FASE 4.5 ADR-011 | 12 (`FIRMA_CONTRATO`, `APROBACION_FACTURA`…) |
| Auditor + lead | 2 (`AUDITOR_PORTAL_ENAC`, `DIAGNOSTICO_PRECLIENTE`) |

TTL: 24h (`COMUNICACION_INCIDENTE_SEGURIDAD`) → 120d (`RENEWAL_CAMPAIGN_DETAILS`). OTP requerido: ~18 purposes. Geo: 6+ purposes (campo persiste; enforcement comentado).

### Endpoints (prefijo `/magic-links`)

- `POST /generate` — RLS owner; genera JWT+OTP, token devuelto 1 vez
- `POST /generate-and-send` — `require_owner`; genera + email en 1 paso
- `POST /consume` — **Público**; verifica JWT+OTP, incrementa usos
- `POST /{id}/revoke` — bypassrls; idempotente
- `GET /` — `require_owner`; lista filtrada
- `GET /by-token/{token}` — **Público**; estado enmascarado, no consume
- `GET /{id}/status` — bypassrls; estado admin

### Lógica consume (ruta crítica)

9 checks secuenciales: JWT firma Ed25519 → hash lookup DB → no deleted → no revocado → no expirado → usos < max → OTP correcto → otp_failures < 3 → geo (**skipped**). Cualquier fallo → HTTP 403 uniforme (`"Invalid magic link"`) sin revelar causa. OTP generado con `pyotp.random_base32()` + `TOTP.now()` — funcionalmente código random 6 dígitos.

### Policy Enforcer ADR-042

15 purposes "ok" (cats. A-F) · 22 hard-rejected (`is_ok=False`, `deprecated_soft`): 2 legacy + 20 in-portal. `APROBACION_ACTA` = "ok" (terceros sin cuenta). Header `X-Deprecated-Purpose` en `/generate`.

**Inconsistencia**: docstring dice deprecated_soft devuelve `is_ok=True` pero código ejecuta hard-reject. Comentario inline "MB-4.bis3 IMPLEMENTED FULLY" es autoritativo.

### Email renderer

32/37 purposes con plantilla HTML Jinja2. Sin plantilla: `APROBACION_FACTURA`, `VALIDACION_CAMBIO_ALCANCE`, `ACEPTACION_RIESGO_RESIDUAL`, `CONSENTIMIENTO_TRATAMIENTO_DATOS` (eliminados sprint Opción α por deprecated v3), `DIAGNOSTICO_PRECLIENTE` (nuevo, pendiente). `generate-and-send` maneja gracefully: `email_sent=False` + `email_error`. OTP **nunca** viaja en el email del enlace (canal separado obligatorio).

### Tests

33 tests, 765 LOC — service (18) + API (15). No tests directos de `policy_enforcer` ni renderer en este subdirectorio.

### Integraciones

- **M30**: consume loggea `magic_link` en timeline contacto (silent fail si eliminado)
- **M05 signing**: `FIRMA_CONTRATO` gatea canvas Ed25519
- **M16/auditor**: `PRIMER_ACCESO_CLIENTE` + `AUDITOR_PORTAL_ENAC` gatean portales
- **audit_log R6**: NO escribe hash-chain — solo `client_interactions` (sin chain)

### ENS

`op.acc.1` identidad efímera · `op.acc.2/6` OTP 2º factor sin cuentas permanentes (R5) · `mp.info.3` hash en BD JWT solo en tránsito · `org.4` trazabilidad T (AUTORIZACION_ACCION_REMOTA) · `op.exp.3` notificación incidentes art.13 RD 311/2022

### Gotchas y deuda

- **Geo enforcement nulo**: `allowed_countries` persiste pero verificación comentada — `requires_geo=True` sin efecto real
- **Dead code**: `return None` inalcanzable `api.py:402`
- **`DIAGNOSTICO_PRECLIENTE` sin email template**: `generate-and-send` falla silencioso
- **Dos pares Ed25519**: `FULKRO_ML_PRIVATE_KEY` (magic links) vs `FULKRO_AUTH_PRIVATE_KEY` (sesión) — correcto, 2 secrets prod

### Veredicto: **COMPLETO** (núcleo operativo). Deuda menor: geo sin implementar, 5 purposes sin email template, dead code puntual.


## 31 - M13 Ciclo comercial (leads/propuestas) + M14 Contratos

### Propósito y dominio

M13 gestiona el pipeline CRM: leads, propuestas (pricing determinista + LLM Agente 19), conversión lead→cliente. M14 cubre el ciclo contractual: generación C-001..C-005, firma magic-link OTP+geo+canvas Ed25519, adendas proveedores, 7 modelos legales DOCX. Ambos **admin-only** (`require_owner`) excepto router público de firma (#43).

---

### Ficheros clave

| Fichero | Propósito |
|---|---|
| `m13/api.py` | 14 endpoints admin (leads + proposals + pricing); mapping stage ↔ estado_contacto ES↔EN |
| `m13/pricing_service.py` | `PricingService` in-memory: PRICING_CATALOG 5 modelos + `_refresh_model_from_single_source` |
| `m13/proposal_service.py` | `generate_proposal` (legacy), `generate_proposal_apendice_m` (canónico), revisions, DOCX |
| `m13/services/lead_service.py` | `LeadService`: create dedup, `transition_estado_contacto`, `list_pipeline` |
| `m13/services/contract_signing_flow.py` | `ContractSigningFlow`: `send_for_signing`, `confirm_signing`, WYSIWYS preview |
| `m13/services/commercial_workflow_service.py` | Auto-conversión lead→Client+Project+Milestones idempotente + advisory lock |
| `m13/services/project_provisioning_service.py` | Fuente única creación proyecto; `emit_conversion_audit_log` R6 |
| `m13/contract_signing_public_api.py` | Router público firma: `GET /preview` + `POST /confirm` |
| `m14/contract_service.py` | `ContractService`: generate legacy + Apéndice M, sign_marcos, retract, hash SHA-256 |
| `m14/api.py` | 13 endpoints admin + 2 legal-templates; `send-client` redirigido a `ContractSigningFlow` |
| `m14/legal_templates.py` | 7 modelos legales DOCX C-100..C-160 + `render_canonical_contract_docx` C-001 |
| `m14/adenda_generator.py` | `AdendaGenerator`: E-604 DOCX proveedor → MinIO → `provider_addendums` |
| `m14/workflow_hooks.py` | Hook event-driven `maybe_dispatch_adenda_on_step_completed` |

---

### Modelo de datos

| Tabla | RLS | Columnas clave |
|---|---|---|
| `leads` | App-level (sin `client_id`) | `estado_contacto` (8 estados), `lead_score`, `convertido_a_proyecto_id`, `cif_norm`, `papel_aapp` |
| `proposals` | App-level `set_tenant_context` | `lead_id`, `project_id`, `version`, `importe_total`, `importe_desglose` JSONB, `superseded` bool |
| `contracts` | App-level `set_tenant_context` | `hash_sha256`, `documento_sha256`, `signing_intent_id` FK, `firmado_marcos/cliente_at`, `scan_window` JSONB |
| `client_commitments` | `project_id` | `contract_id`, `tipo`, `valor_esperado`, `valor_actual`, `cumplido` |
| `lead_stage_history` | Sin RLS (append-only) | `lead_id`, `estado_anterior/nuevo`, `cambiado_por_user_id`, `metadata_jsonb` |

---

### Endpoints

**M13 admin** (`/api/v1/commercial`): pricing-models CRUD+calculate · leads list/detail/stage/estado-contacto · proposals generate/generate-llm/list/get/patch/send/version/docx.

**M14 admin** (`/api/v1/contracts`): templates · legal-templates · client-prefill · contracts generate/generate-llm/list/get/sign-marcos/send-client/docx/commitments/check-commitments/scan-window · retract · legal-templates/{slug}/generate.

**Público**: `GET /contract-signing/preview` (WYSIWYS, sin consumir usos) · `POST /contract-signing/confirm` (OTP + canvas Ed25519).

---

### Lógica de negocio

**CRM 8 estados**: `nuevo → enviado → respondio → reunion_agendada → propuesta_enviada → ganado` (terminal). `descartado`/`no_interesa` → `nuevo` (re-engagement). `VALID_TRANSITIONS` enforced + `LeadStageHistory` audit trail.

**Pricing (doble vía)**: Legacy `generate_proposal` usa PRICING_CATALOG in-memory (bases stale 6.500/22.000/48.000) sobreescritas runtime por `_refresh_model_from_single_source` → `get_base_prices()` BD. Canónico `generate_proposal_apendice_m` usa `PricingCalculator` → `BASE_PRICES` 3.200/10.700/22.800 (recargo urgencia +30% plazo <6 sem, hitos oficiales, 60d AAPP/30d privado).

**Flujo firma** (una transacción): `send_for_signing` → DOCX render → `documento_sha256` SHA-256(bytes) → IDMS → `SigningIntent` m05 → magic-link `FIRMA_CONTRATO` (TTL 72h, OTP, geo). `confirm_signing` → consume OTP → `handle_contract_signed` (conversión idempotente) → `sign_canvas` Ed25519 → certificado PDF IDMS (Pattern #24) → `"vigente"`. Idempotencia: `intent.status == "signed"` → no-op. `retract_in_flight_contract`: revoca magic-link + cierra intent + `"anulado_recategorizacion"`.

**Dos hashes**: `hash_sha256` = SHA-256 JSON parámetros. `documento_sha256` = SHA-256 bytes DOCX (WYSIWYS, lo que firma el cliente).

---

### Integraciones

- **M05**: `sign_canvas` Ed25519 hash-chain; `pdf_signature_embed` Pattern #24.
- **M12**: `FIRMA_CONTRATO` #36 OTP+geo; `revoke_magic_link` en retract.
- **M17**: `estimate_duration_weeks`, `estimate_effort` vía legacy.
- **M21**: `create_user` → ClientUser firmante en `_resolve_or_create_signer`.
- **M24 IDMS**: DOCX pre-firma + certificado PDF post-firma archivados.
- **M28/M30**: hook adenda auto-trigger; `ClientContactService.log_interaction`.
- **Agente 19/20**: narrativa opt-in LLM; fallback determinista.
- **audit_log R6**: `emit_conversion_audit_log` best-effort SAVEPOINT (#7.6).
- **SSE**: dispatch admin post-firma.

---

### Gotchas y deuda técnica

- **PRICING_CATALOG stale** (6.500/22.000/48.000 hardcoded): mitigado runtime; peligroso en tests sin seed BD.
- **`register_client_signature`**: método conservado deprecated (#43) sin endpoint activo. Dead code documentado.
- **`_PROJECT_PRICING_MODEL`**: anotado `# SUPERSEDED por BUG5`. Dead code histórico.
- **`contact_name`** en `_serialize_lead_for_crm`: `lead.notas[:80]` — notas ≠ nombre contacto. Semántica errónea.
- **`check_commitments`**: `await db.commit()` antes de lógica → vacía RLS `SET LOCAL`. Bug potencial.
- **TODO-RBAC-PER-ENDPOINT-001**: granularidad per-endpoint pendiente.
- **RLS app-level** (no PG-nativa) para `leads`/`proposals`/`contracts`.

---

### Tests

8 ficheros: `tests/motors/m13_commercial/` (lead\_service, lead\_detail\_api, contract\_signing\_flow, contract\_signing\_canvas, contract\_signing\_endpoint, commercial\_workflow\_service, m13\_commercial) + `tests/motors/m14_contracts/test_m14_contracts.py`. Cobertura **completa** en caminos críticos.

### Medidas ENS cubiertas

`op.ext.1/2` (adendas E-604, C-120/C-130/C-150: RGPD Art.28, CCN-STIC 823, DPA Schrems II) · `op.pl.1` (`alcance_snapshot` congelado, trazabilidad ENAC) · `op.acc.6` (OTP+geo firma) · `mp.info.3` (`documento_sha256` SHA-256 + Ed25519 hash-chain) · `mp.s.2` (`scan_window` wired M08) · `org.4/op.pl.5` (hitos pago, XYZPR, compromisos cliente).

### Veredicto: **completo** (producción)

M13+M14 es el módulo más elaborado del repo: CRM 8 estados, pricing doble vía Apéndice M, firma eIDAS Art.25.1 WYSIWYS atómica, conversión idempotente lead→proyecto, 7 modelos legales DOCX, adendas event-driven, certificados Ed25519. Déficits menores: PRICING\_CATALOG stale (mitigado runtime), dead code documentado, RLS app-level no PG-nativa, `contact_name` semántica incorrecta, `check_commitments` bug post-commit.

### Discrepancias CLAUDE.md vs código

1. **Pricing**: CLAUDE.md afirma "3.200/10.700/22.800 en todo el sistema"; `PRICING_CATALOG` tiene hardcoded 6.500/22.000/48.000 mitigados runtime. Correcto funcionalmente, oculta riesgo en tests sin seed.
2. **Docstring obsoleto**: `generate_proposal_apendice_m` cita "BASICA 3.900 / MEDIA 9.500 / ALTA 25.000" — valores no actualizados al canónico 3.200/10.700/22.800.
3. **Dead code**: CLAUDE.md afirma `register_client_signature` eliminado (#43) — el método de servicio **existe** en `contract_service.py`; sólo el endpoint fue retirado.


## 32 - M15 Facturacion + M23 Retainers post-cert

**Alcance leido**: todos los ficheros de `motors/m15_billing/` (9 ficheros, ~1 900 LOC) y `motors/m23_retainer/` (20 ficheros, ~5 500 LOC), mas `app/billing/` y `app/retainer/` (~1 200 LOC). Modelos `commercial.py` y `retainer.py` muestreados. 8 ficheros de test revisados.

---

### M15 — Facturacion fiscal

**Ficheros clave**: `billing_service.py` (807 LOC, nucleo) · `api.py` (313) · `financial_extensions_api.py` (286) · `facturae_generator.py` (211, XML 3.2.x Orden HAP/1074/2014) · `invoices_aapp_api.py` (302) · `xades_signer.py` (93, **stub** TODO-FACE-XADES-CERT-FNMT-001) · `face_submitter.py` (62, **stub** TODO-FACE-API-INTEGRATION-001).

**Modelo de datos — `invoices`**
- `client_id` NOT NULL + `project_id` nullable → RLS via `set_tenant_context`
- `numero_correlativo` — formato `FULKRO-{año}-{NNNN}`
- `tipo` — `ordinaria | rectificativa | proforma`
- `estado_pago` — `pendiente | vencida | pagada | anulada`
- `verifactu_hash VARCHAR(64)` — SHA-256 encadenado (cadena fiscal independiente de R6 audit_log)
- `email_enviado_at` — campo dedicado post-fix (antes se reutilizaba `verifactu_enviado_at`)
- **Gotcha**: `paron_asociado` en `InvoiceLine` — tipografia inconsistente, posible typo de `patron_asociado`, sin documentacion ni uso en logica activa

**Endpoints** (todos `require_owner`): `POST /billing/projects/{id}/invoices/generate|from-milestone` · `GET|POST /invoices/{id}` (detalle, mark-paid, cancel, reminders, pdf-DOCX) · `GET /billing/clients/{id}/invoices` (cross-project) · `GET /projects/{id}/financial-summary` · `POST /projects/{id}/invoices/{id}/send` (portal+email).

**Logica de negocio**
- Correlativo fiscal: `pg_advisory_xact_lock(hashtext('invoice_seq_{año}'))` serializa emisiones concurrentes (Pattern #22); red de seguridad: indice unico parcial `invoice_correlative_unique_001`.
- Verifactu hash: SHA-256(`prev_hash|numero|fecha|base|total`). Primer del año: `INICIO-{año}`.
- IVA 21% / IRPF 15% con `Decimal` (precision fiscal correcta).
- Cancelacion: rectificativa negativa automatica, estado original → `anulada`.
- AAPP LCSP: plazo 60 dias (art. 198.4) si `is_aapp(cliente)`.
- PDF DOCX + QR AEAT, NIF desde `get_fiscal_identity()` (fuente unica). Degradacion elegante sin datos fiscales.
- `AutoBillingService` (`app/billing/auto_billing.py`): trigger por fase completada → `ContractMilestone` → `BillingService.generate_invoice` → avance `projects.fase` si `blocking_next_phase`. Notificacion best-effort.
- `stage_verifactu` hardcoded `"pending"` en `/aapp-billing/status` — informacion incompleta para UI.

---

### M23 — Retainers post-certificacion

**Ficheros clave**: `retainer_service.py` (942 LOC) · `api.py` (609, 20+ endpoints) · `billing_integration.py` (218, M23→M15) · `tasks.py` (703, 13 Celery tasks) · `retainer_checkin_service.py` (632, E-801/E-802) · `drift_compute_service.py` (329) · `pricing_catalog_seed.py` (seed 5 tiers).

**5 Tiers retainer**

| Tier tecnico | precio/mes | SLA (h) | h/año | Tier comercial |
|---|---|---|---|---|
| `R_MICRO` | 150 € | 120 | 12 | R_BASICO |
| `R_LITE` | 300 € | 72 | 25 | R_BASICO |
| `R_STD` | 700 € | 48 | 40 | R_MEDIO |
| `R_PLUS` | 1.200 € | 24 | 80 | R_ALTO |
| `R_CRITICAL` | 3.000 € | 8 | 150 | R_ALTO |

`COMMERCIAL_TIER_LABELS` en `retainer_service.py` — presentacion API, NO renombra BD.

**Tablas principales**
- `retainer_contracts` — `client_id` (NOT NULL), `project_id`, `perfil`, `precio_mensual`, `estado`, `rag_status`, `renewal_status`, `next_renewal_date`, horas consumidas/previstas
- `retainer_activities` — `project_id`, `tipo_actividad`, `estado`, fechas, horas
- `retainer_drift_events` — `retainer_contract_id`, `dimension`, `severidad`, `impacto`, `estado`
- `retainer_billing_events` — `invoice_id` FK M15, `billing_period_start/end`, `amount`, idempotencia
- `retainer_quarterly_reports` — unico `(project_id, period_quarter)`, workflow curation/sign
- `pricing_catalog` — `category`, `tier_code`, `base_price`, `is_active`

**Logica de negocio**
- Renewal clock 7 estados: `null → T_MINUS_180..30 → LAPSED | RENEWED`. Celery daily `update_all_renewal_statuses`.
- RAG: RED si overdue>2 o CRITICAL drift o LAPSED. AMBER si overdue≥1 o HIGH o 2+ MEDIUM o T_MINUS_30/60.
- `generate_annual_activities(year)`: materializa tabla completa segun `CADENCES_BY_PROFILE` por tier (9-10 tipos por tier, distintas frecuencias).
- `execute_activity`: branching real por tipo → M08/M10/M18/M03. Best-effort: fallo revierte a `programada`.
- `dispatch_due_activities`: encola actividades DUE por `.delay()` (antes nada disparaba `execute_scheduled_activity`).
- Facturacion recurrente idempotente por `(retainer_id, period_start, end)`; precio de `pricing_catalog` (BD); Celery 1er mes 04:00.
- Trigger post-certification: orquestado por M25 `mark_audit_passed(cascade_retainer_offer=True)` — M23 no lo inicia.
- Dashboard global: `SET LOCAL ROLE fulkro_app_bypassrls` explícito para Marcos.
- Drift semanal: queries read-only cross-motor, CRITICAL → `rag_status="red"` inmediato.
- Checkin E-801/E-802 idempotente por `(project_id, period_quarter)`, firma step-up OTP.
- `ccn_stic_daily_scrape` → A15 vigilancia normativa.

**Tareas Celery (13)**: overdue · renewal · execute_activity · dispatch_due · monthly_invoices · renewal_trigger · agent_26 · quarterly_reports · annual_reports · ccn_stic_scrape · drift_compute · m31.media_digest · m31.basica_digest.

---

### Medidas ENS cubiertas

- `op.mon.1` vigilancia continua via M08; `op.exp.10` Verifactu hash SHA-256; `op.cont.4`/`mp.com.3` prueba_continuidad + comite_seguridad; `org.4`/`op.pl.1` revision_ar_dda anual M03; `mp.info.6` E-801/E-802; `op.ext.1` revision_proveedores; `op.acc.5/6` revision_privilegios; `mp.if.7` formacion_anual; LCSP art.198.4 Facturae/FACE/XAdES (stub pre-prod).

---

### Discrepancias CLAUDE.md vs codigo

1. **"codigo `RETAINER_TIERS`"** — no existe ninguna constante con ese nombre. Las reales son `VALID_PROFILES` (m23) y `VALID_RETAINER_TIERS` (m25_lifecycle). El catalogo vive en `pricing_catalog`.
2. **"R_STD = 700€ resuelta"** — el seed lo tiene correcto (700). Pero la fuente de verdad en prod es la BD; si la BD tiene 400 y el seed no se re-ejecuto post-unify, la divergencia persiste hasta re-seed o edicion via UI `/admin/settings/pricing`.
3. **`paron_asociado`** — campo undocumented en `InvoiceLine`, aparenta typo de `patron_asociado`, sin logica activa.
4. **XAdES/FACE "implementados"** — son stubs documentados con TODO. No ejecutables sin cert FNMT real.
5. **`stage_verifactu` hardcoded `"pending"`** en endpoint `/aapp-billing/status` — misleading para admin UI.
6. **Tasks `m31.*` en `m23/tasks.py`** — WhatsApp MEDIA/BASICA digests definidos fisicamente en modulo m23 con prefijo m31 — inconsistencia de separacion.

---

### Veredicto

**M15**: **completo** para facturacion fiscal espanola (Verifactu, IVA/IRPF, correlativo serializado, rectificativa, PDF QR). AAPP pipeline (XAdES + FACE) **parcialmente stub** pre-piloto, documentado honestamente con TODOs.

**M23**: **completo** — 5 tiers cableados, cadencias por perfil, renewal clock 7 estados, RAG, drift 10 dims auto-compute, checkin E-801/E-802, facturacion recurrente idempotente M23→M15, 13 Celery tasks funcionales. Sin dead code relevante. Trigger post-certification correctamente delegado a M25.


## 33 - M16 Onboarding cliente

**Parcela**: `backend/app/motors/m16_onboarding/` · 31 ficheros fuente + `connectors/` (7) + 72 plantillas JSON · 3.268 LOC tests (18 ficheros).

---

### Propósito y dominio

Motor de onboarding adaptativo. Cubre: (1) wizard cuestionario multi-rol/sector con branching; (2) captura 10 dimensiones canónicas → M01; (3) OAuth PKCE para 5 proveedores + AWS IAM-paste; (4) mini-LMS (E-502/E-503); (5) flujo precliente account-less (magic-link + consentimiento Art.13 RGPD); (6) Portal API separado `/api/v1/portal/onboarding/` autenticado `ClientUser`.

---

### Ficheros clave

| Fichero | Rol |
|---------|-----|
| `enums.py` | `Sector` (12 incl. PRECLIENTE+INDIVIDUAL), `Role` (7), `SessionState` (6), `QuestionType` (9) |
| `types.py` | Pydantic `OnboardingTemplate`, `Question`, `BranchingCondition`, validadores regex |
| `catalog_loader.py` | `lru_cache` carga 72 JSON; unicidad (id, sector×role×version) |
| `service.py` | CRUD admin sessions · ADR-020 v3 magic_link_id=None por defecto |
| `client_service.py` | Branching engine + save_answer upsert + submit → `apply_dimensions_from_responses` |
| `dimensions_capture.py` | 10 q-IDs canónicos → `DimensionsService.patch_dimensions_partial` (non-invasive OPS-040) |
| `oauth_service.py` | OAuth PKCE (microsoft/azure/google/base) + no-PKCE (github) + AWS STS validate |
| `oauth_state_service.py` | Anti-CSRF state 10min TTL · PKCE S256 · `consumed_at` replay-guard |
| `token_encryption.py` | Fernet AES-128-CBC+HMAC-SHA256 · clave derivada SHA-256 de `app_secret_key` |
| `api.py` | Router `/onboarding` admin + M16-B cliente (headers `X-Onboarding-Session-*`) |
| `portal_api.py` | Router `/api/v1/portal/onboarding/` · 11 endpoints ClientUser |
| `addendum_v22.py` | `route_gate_block`, `role_topology_designer`, `overlay_detection_block`, `retainer_profile_predictor` |
| `art13_precliente.py` | Texto Art.13 RGPD versionado (v2 · `marcosmata@fulkro.es`) |
| `lms_service.py` | `lms_courses_v1.json` lru_cache · assign · E-502 asistencia · E-503 quiz |
| `connectors/` | ABC `BaseConnector` + 5 implementations + `registry.py` |

---

### Modelo de datos

| Tabla | project_id | client_id | RLS |
|-------|-----------|-----------|-----|
| `onboarding_sessions` (FullMixin) | FK directo | — | Sí (`e41cd7163c02`) |
| `onboarding_responses` | via session FK | — | CASCADE; unique idx (session_id, question_id) |
| `connector_configs` | directo | — | **EXCLUIDA deliberadamente** (ver §Gotchas) |
| `oauth_state_tokens` | FK directo | FK `client_users.id` | Sí FORCE (`rls_fail_closed_hardening_001`) |
| `precliente_diagnostic_consents` | via session | — | Propia migración |
| `lms_assignments` (FullMixin) | FK directo | — | Sí (`33cef115cdf5`) |

`OnboardingSession` tiene campos legado JSONB (`preguntas`, `respuestas`) que coexisten con columnas M16-A (`template_id_str`, `total_questions`, `answered_questions`). El nuevo motor usa exclusivamente M16-A + `onboarding_responses`.

---

### Endpoints (resumen)

**Admin** (`/api/v1/onboarding/`, `require_owner`): catalog (GET/GET-detail) · sessions CRUD (POST create, POST precliente, GET list, GET detail, POST mark-sent, POST cancel, GET expired) · client M16-B via headers (consent-text, consent, next-question, answer, final-submit, progress).

**Portal ClientUser** (`/api/v1/portal/onboarding/`): status · next-question · answer · connectors list · oauth-init · oauth-callback · aws/credentials · sync (**STUB**) · lms list/complete · finish.

---

### Lógica de negocio y máquinas de estado

**Session state**: `CREATED → SENT → IN_PROGRESS → COMPLETED` / `→ EXPIRED` (auto-check on read) / `→ CANCELLED` (revoca magic-link M12).

**Branching engine**: puro funcional · `_effective_question_sequence` evalúa `skip_if` con operadores `equals/not_equals/in/contains` · recalculado por request desde BD.

**Dimensions bridge**: `apply_dimensions_from_responses` mapea 10 q-IDs canónicos → `DimensionsService.patch_dimensions_partial`. Non-invasive (`logger.warning` en error). Antes de Ejecutable 8 OLA 0 era dead-code; ahora activado en `submit_onboarding`.

**OAuth anti-CSRF + PKCE**: token 64-char URL-safe, TTL 10min, 1-time-use. `portal_api` eleva a `SET LOCAL ROLE fulkro_app_bypassrls` para lookup/consume (RLS fail-closed sin contexto tenant en callback).

**Precliente**: sector PRECLIENTE + magic-link `DIAGNOSTICO_PRECLIENTE` + consent gate Art.13 v2 + `precliente_diagnostic_consents` append-only, versión server-side. `#7.3`: `lead_id` → proyecto ligero via `CommercialWorkflowService`.

**Plantillas**: 72 JSON · ID `onb-{sector}-{role}-v1` · Pydantic valida (3-80 preguntas, unique ids, min 2 opciones). Muestra fintech/sponsor: 15 preguntas, 7 secciones. `internal_tag` para análisis Marcos (no renderizado al cliente).

---

### Medidas ENS cubiertas

- `op.acc.1` – Identificación usuarios: discovery identidades cloud
- `op.acc.5` – Privilegios: `DiscoveredIdentity.es_privilegiada` vía M365 `/directoryRoles`
- `op.acc.6` – MFA: `mfa_enabled` vía `/reports/authenticationMethods`
- `mp.s.2` – Servicios: SharePoint/Shared drives sharing detection
- `op.exp.10` – Criptografía: credentials Fernet AES-128-CBC
- `mp.info.3` – Clasificación: dims arquitectura, multi-tenancy, datos sensibles RGPD art.9
- `mp.per.1/4` – Formación/concienciación: LMS E-502/E-503; DPO capture (`q-dpo-designado`)
- `org.4` – RGPD: consentimiento Art.13, `q-procesa-datos-sensibles`, `q-aplica-nis2/dora/ai-act`

---

### Gotchas y deuda

1. **STUB `portal_connector_sync`**: solo actualiza `last_discovery_at + status="sync_triggered"`. Nota explícita en respuesta `"Sync M22 discovery wiring pendiente"`. No lanza discovery real.
2. **Sin `audit_log`**: ningún emit en `service.py`, `client_service.py` ni `portal_api.py`. Acciones onboarding (create session, answer, finish, OAuth connect) NO generan entradas hash-chain R6. **Gap trazabilidad ENAC para el proceso de onboarding**.
3. **`connector_configs` sin RLS DB**: excluida por diseño en `33cef115cdf5` ("cross-tenant audit operacional"). Protección activa es Python scope-check `project.client_id != client_user.client_id` en portal_api. Aceptable pre-piloto; recomendable añadir RLS post-piloto.
4. **`cleanup_expired` sin caller**: `oauth_state_service.cleanup_expired()` existe pero no hay cron ni endpoint activo. Tokens expirados acumulan en BD (minor).
5. **LMS dependiente de fichero**: `lms_service` carga `docs/catalogs/lms_courses_v1.json` con lru_cache. Ausencia del fichero en prod = 500 en todos los endpoints LMS.
6. **Legado JSONB `preguntas`/`respuestas`**: columnas de la era pre-M16-A en `onboarding_sessions`. Sin código activo que las lea; generan ruido en esquema.

---

### Tests

3.268 LOC · 18 ficheros: sessions CRUD (224), client flow (392), connectors (228), LMS (433), precliente consent+RLS F-18 (102+99+96+196), portal api (270), RBAC (128), oauth service (124+125), tools (138), catálogo (65). Cobertura sustancial happy-path + error paths. Sin tests de `cleanup_expired` ni del sync wiring real.

---

### Veredicto

**COMPLETO** con deuda menor documentada. Wizard+branching+dimensions+OAuth+precliente: operativos. Único gap funcional real: `portal_connector_sync` stub (wiring M22). Gap de governance: ausencia total de `audit_log` emit en el motor. `connector_configs` sin RLS DB es decisión de diseño explícita, no bug silencioso.


## 34 - M17 Planificacion (Gantt) + M20 Workspace

**Alcance**: M17 (7 .py) + M20 (2 .py) + modelos `planning.py`/`collaboration.py` + wiring `main.py`. `pda_generator.py` muestreado; `effort_formulas_v1.json` confirmado.

### M17 `m17_planning` — Plan ENS (WBS + CPM + Gantt + replan)
- **Ficheros**: `planning_service.py` (core), `wbs_catalog.py`, `effort_estimator.py` (Apendice N, JSON-driven), `pda_generator.py` (DOCX E-150 CCN-STIC 806), `fase0_governance.py` (composer puro), `api.py` (admin), `portal_api.py` (cliente READ-ONLY).
- **Tablas** (FullMixin → RLS `e41cd7163c02`): `project_plans` (`project_id`, categoria, `critical_path_tasks`, `baseline_snapshot`, `mermaid_gantt`, `meeting_plan`, `milestones`); `wbs_tasks` (`project_plan_id`+`project_id`, dependencies, `deliverable_e_code`, `is_critical_path`, `slack_days`, `progress_pct`, baseline_*); `change_requests` (`CR-NNN`, impactos, estado).
- **Algoritmos deterministas (NO LLM)**:
  - `generate_plan`: 1 plan/proyecto (bloquea dup), instancia WBS por categoria, forward-pass topologico fechas, **CPM real** (ES/EF/LS/LF + slack=0→critico), Mermaid gantt, estado→`active`.
  - `replan` (#5 cabo N2): soft-delete plan+tasks, regenera nueva categoria preservando start_date/capacidades. Solo borradores sin firma (orquestado `floor_elevation_service`).
  - `set_baseline` (snapshot 1 vez), `detect_delays` (vs baseline), `get_plan_progress`, CR `propuesto→aprobado/rechazado` (al aprobar aplica impacto plazo/esfuerzo al plan; code serializado por advisory lock m17+m19).
- **effort_estimator**: `estimate_effort` legacy (3 factores) + `estimate_full` (JSON, breakdown auditable horas_base×sector×madurez×size×complejidad, caps 0.40–3.5, 95€/h). 6 status, 5 sizes, 4 complexity, 3 categorias.
- **fase0_governance**: composer puro sin side-effects · pasos kickoff→decision(E-010)→alcance(E-155)→roles(E-002)→comite(E-003 MEDIA/ALTA)→plan(E-150); lee `documents.template_codigo`, valida RSeg≠RSis (m30 CCN-STIC-801) + cadencia comite (m_meetings). Branch BASICO/MEDIO_ALTO.
- **Endpoints** `/api/v1/planning/*` (`require_owner` admin, RLS `get_project_owner`): POST `/generate`, GET `/{id}`, POST `/baseline`, GET `/progress`|`/delays`|`/mermaid`|`/fase0-governance`|`/export/xlsx`, POST `/pda/generate` (DOCX), GET `/tasks`+`/tasks/critical-path`+`/tasks/{id}`, PATCH `/tasks/{id}`, CRUD `/change-requests/*`, POST `/estimate-effort`+`/estimate-full`, GET `/effort-formulas`.
- **portal_api** `/api/v1/client-portal/plan` (`require_client_user`): GET timeline READ-ONLY. F-18-01b: setea RLS `client_id` ANTES de resolver `project_id` (sin esto RLS ciega→404 al dueño). Emite `cliente.plan.viewed` 3-way OR. Expone `responsible` para "Mis tareas".

### M20 `m20_workspace` — FULKRO Room
- **Ficheros**: `workspace_service.py` (`WorkspaceService`+`WorkspaceError`), `api.py`. NO `service.py`.
- **Tablas** (`collaboration.py`, RLS `e41cd7163c02`): `collaborative_workspaces` (unique `project_id`), `workspace_files`, `workspace_feed_items`, `workspace_chat_messages`, `videocall_sessions`. Todas con `project_id`.
- **Logica**: lifecycle `active→archived→destroyed` (destroy exige `caducidad_at` vencida salvo `force`); `_ensure_writable` bloquea write. Files SHA-256 obligatorio + feed item automatico. Chat/feed append-only. Videocall **state machine** `solicitada→aceptada→en_curso→finalizada`/`cancelada` SIN LiveKit. Integra M25 lifecycle via BD (SQL-first).
- **Endpoints** `/api/v1/workspace/*` (`require_marcos_or_client` ambos pools): lifecycle, files (base64/tree), feed, chat (thread), videocalls.

### Medidas ENS / E-codes
E-001/002/003/005/010/012/040/050/150/155/400/702-705 (deliverables WBS+FASE 0). PDA→**E-150** (CCN-STIC 806). fase0→**RD 311/2022 art.11 · CCN-STIC 801 · org.1**. M17/M20 orquestan, NO implementan medidas tecnicas.

### Integraciones
audit_log hash-chain; SSE `m17.plan.updated`+ClientNotification dual (Pattern #14) en PATCH task; advisory lock CR; PDA cross-motor M01-M04; m30 roles + m_meetings. **Sin LLM**.

### Veredicto: COMPLETO (videocall = stub deliberado ADR-004)
- M17 production-grade: CPM real correcto, replan, baseline, CR con impacto, XLSX/DOCX, FASE 0, portal cliente con fix RLS F-18-01b.
- M20 production-grade core; videocall state machine sin engine video (no deuda).
- **Gotchas**: M17 admin `require_owner` (no doble pool); RLS manual por endpoint; CPM ignora ciclos silenciosamente.
- **Legacy/dead**: `estimate_effort` legacy (tests v1); cols `wbs`/`critical_path`/`resource_allocation` en model NO usadas.

### Discrepancias docs vs codigo
- README M17 **omite el portal cliente** `/api/v1/client-portal/plan` (existe `portal_api.py`).
- README M17 "Outbound: ninguno" **falso**: emite SSE+ClientNotification + DOCX cross-motor. LOC "2.074/6 files" desactualizado (7 ficheros: anade `fase0_governance`+`portal_api`).
- README M20 nombra `WorkspacePost`/`WorkspaceMessage`/`VideocallState` y `models/workspace.py` — **falso**: reales `WorkspaceFeedItem`/`WorkspaceChatMessage`/`VideocallSession` en `models/collaboration.py`. CLAUDE.md `m17.plan.updated` SSE verificado.


## 35 - M18 Comunicacion + M29 Mensajeria cliente + M30 Contactos + M31 WhatsApp

Auditoria empirica leyendo codigo fuente (no docs). Alcance: M18 14 ficheros (leidos `api.py`, `escalation_service.py`, `alert_service.py`, `report_generator.py` cabecera, `aepd_decision_tree.py`; muestreados resto), M29 9 ficheros completos, M30 13 ficheros (core completo; muestreados `department_*`, `*_api`), M31 6 ficheros completos.

### Proposito por motor
- **M18 Communication & Reporting**: reportes deterministas (anti-alucinacion, NO LLM), plan comunicacion, escalados, actas comite DOCX firmadas, arbol decision AEPD brecha RGPD. Prefijo real `/api/v1/communication/*`. `require_owner` router-level (Marcos-only).
- **M29 Client Messaging**: mensajeria bidireccional cliente<->admin con threads, adjuntos MinIO, email forward, mark-read, soft-delete. Routers `/api/v1/admin/messages/*` (require_owner) + `/api/v1/client-portal/messages/*` (cookie+CSRF).
- **M30 Client Contacts**: agenda profesional por cliente (NO portal users), timeline cross-motor, roles ENS, import/export CSV. Prefijo `/api/v1/clients/{client_id}/contacts/*`. `require_owner`.
- **M31 WhatsApp**: integracion Dialog360 BSP, opt-in OTP, bidireccional, webhook, SSE inbound, export RGPD art.15. Routers `/api/v1/admin/whatsapp/*` + `/api/v1/client-portal/whatsapp/*` + `/api/v1/webhooks/360dialog`.

### Modelo de datos (tablas + RLS)
| Tabla | Motor | Cols tenant | RLS |
|---|---|---|---|
| `client_messages` | M29 | `client_id` (CASCADE) NOT NULL, `project_id` (SET NULL) | `client_isolation` USING client_id; admin via `SET LOCAL ROLE fulkro_app_bypassrls` |
| `client_message_attachments` | M29 | via `message_id` CASCADE | CHECK size<=10MB + MIME whitelist en BD |
| `client_contacts` | M30 | `client_id` (CASCADE), `project_id` (CASCADE) opcional | RLS `USING (true)` + RBAC require_owner (admin-only) |
| `client_contact_interactions` | M30 | via `contact_id` CASCADE | hereda |
| `whatsapp_threads` | M31 | `project_id` (CASCADE) NOT NULL, `client_user_id` (SET NULL) | RLS por project_id (`app.current_project_id`) |
| `whatsapp_messages` | M31 | `project_id` (CASCADE) NOT NULL | idem |
| `whatsapp_critical_events_routing` | M31 | ninguna (catalogo global) | matriz tier basica/media/alta |

- M18 NO declara tablas propias: usa `EscalationEvent`, `Alert`, `committee_meetings`(minutes), `CommunicationPlan`, `StatusReport`, `AepdNotification` desde `models/` compartido.
- M31 estado opt-in vive en `client_users` (`whatsapp_number`, `whatsapp_verification_otp`, `whatsapp_otp_sent_at`, `whatsapp_verified_at`, `whatsapp_opt_in_at`), NO en tabla M31.

### Logica/maquinas de estado
- **M29**: `thread_id` UUID agrupa conversacion; sender (`from_role` client|admin, `from_user_id` sin FK por polimorfismo auth_users/client_users); doble flag `is_read_by_admin/client`; `_list_threads` agrega con subquery MAX(created_at) + N queries por thread (posible N+1 en inbox grande).
- **M30**: CRUD + `is_active` soft-state (distinto de `deleted_at`); `is_primary` unicidad via `_unset_other_primary`; `log_interaction` = entry point cross-motor (silent-fail si contacto borrado); roles ENS_REQUIRED (6) con assign/vacate exclusivo por client.
- **M31**: OTP 6 digitos TTL 10 min; `verify_otp` set `verified_at`+`opt_in_at`; `handle_inbound` resuelve user por phone+verified, proyecto por `LIMIT 1` (R27); delivery status sent/delivered/read/failed.
- **M18**: minutes state draft->reviewed->signed (firma Ed25519 via M05, hash SHA256); reports estado generado->revisado->enviado; escalation resuelto/auto_resolve_days; AEPD decision tree determinista 2 steps.

### Medidas ENS / E-codes (ver ens_measures)
- M30 `roles_ens.py`: roles canonicos CCN-STIC 801 (RI/RS/RSEG/RSIS/POC/Comite) + `validate_role_segregation` (RSEG!=RSIS, severidad category-aware mayor en MEDIA/ALTA, menor BASICA) -> mp.per.* / org.*.
- M30 `ens_required.py`: 6 roles RD 311/2022 art.11(a-e)+sponsor -> auto-populate E-002/E-012/E-040/E-027/E-028/E-041/E-042/E-006.
- M18 escalation: triggers `incidente_deadline_notificacion_lucia` (Art.33 CCN-CERT/LUCIA), `aepd_deadline_notificacion_72h` -> op.exp.7 gestion incidentes.
- M18 AEPD decision tree: RGPD art.33/34 (72h) -> notificacion brecha datos personales (legal, no Anexo II directo).
- M18 minutes E-005 actas comite; M18 alerts categoria `rgpd_72h`, `audit_due`.

### Integraciones
- **Audit_log hash-chain**: NO hay emision explicita de audit_log en M29/M30/M31 (grep 0 matches en M29; M30/M31 idem). Confian en triggers BD row-level (mencionado en docstrings M30). Discrepancia con motores Sub-atom 5.A que emiten eventos canonicos.
- **SSE**: M31 propio (`sse_endpoint.py` polling 1.5s, sesion efimera por poll — fix P1-3 anti pool-exhaustion). M18 alert via `core.sse_dispatcher` canal `project:{id}`. M29 NO emite SSE.
- **Magic-links / M05**: M18 minutes `send-for-signature` + `register_signature` Ed25519. M29/M30 sin firma.
- **Cross-motor**: M29.send_as_admin -> M30.log_interaction; M18.escalation -> M20 workspace feed (best-effort); M30.get_for_copilot_context -> A14; M30.get_stakeholders_for_template -> M6.
- **Dialog360**: wrapper httpx con `mock_mode` default True (sin red); `get_default_client` real solo si `whatsapp_provider == "360dialog"`.

### Patrones / gotchas / dead code
- M29 `from_user_id` polimorfico SIN FK (coherencia solo service-layer) — gotcha integridad.
- M31 webhook fail-open si `dialog_360_webhook_secret` vacio (return True) — aceptable dev, riesgo si prod sin secret.
- M31 inbound dispatcha `SET LOCAL ROLE fulkro_app_bypassrls` antes de handle_inbound (necesario: webhook anonimo).
- M29 `_list_threads` ejecuta ~4 subqueries por thread (N+1) — perf en inbox grande.
- M30 `import_csv` silencia duplicados sin reportar filas omitidas.
- M30 TODO-M30-M12-INTEGRATION-001: FK `sent_to_contact_id` magic-links diferido.
- M18 `email_signature.py` mencionado en README NO existe en listado real de ficheros (falta).

### Veredicto: COMPLETO/PRODUCTION-GRADE (con matices)
Los 4 motores tienen modelo+service+API+tests coherentes y wiring real en `main.py`. M31 Dialog360 funciona en mock; integracion real depende de KYC/env (honest boundary). M18 reports verdaderamente deterministas (datos de M17/M19/M5/M7/M10/M14, sin LLM — confirmado en cabecera report_generator). Mixto solo en: audit_log no-explicito y alert channels no-implementados.


## 36 - M19 Riesgo continuo + m_live_records (registros vivos)

> Parcela: `backend/app/motors/m19_risk/` (14 ficheros, ~2.700 LOC) + `backend/app/motors/m_live_records/` (6 ficheros, ~1.890 LOC). Código leído archivo a archivo.

### 1. Propósito
**m19_risk** es un motor **cuádruple**: (a) riesgo de proyecto (`ProjectRisk`, catálogo YAML R-001..R-031, semáforo `score = probabilidad × impacto_dias`); (b) **incidentes de seguridad** CCN-STIC 817 (6 estados + decision tree CCN-CERT + auto-notificación LUCIA art. 33 + firma cliente); (c) **BIA** (RTO/RPO/impacto € por servicio); (d) **continuidad** (cuestionario cliente + aprobación + ejecución de pruebas DRP). **m_live_records** gestiona los **26 registros vivos operativos** E-300..E-325 en tabla genérica `live_records` (discriminador `register_type`), con auto-población desde M19/M28/M14, export CSV/XLSX y proyección de NC.

### 2. Modelo de datos
- `project_risks`: FullMixin + `risk_code`/`probabilidad`/`impacto_dias`/`impacto_euros`/`status`(4)/`materialization_evidence` JSONB. **Sin `client_id`** → RLS por `project_id` (`get_project_owner` + `set_tenant_context`; `_set_risk_rls` usa `ROLE bypassrls` para el lookup).
- `live_records`: `register_type` String(10) + `entry_data` JSONB + CHECK `^E-3(0[0-9]|1[0-9]|2[0-5])$` + GIN index. Sin `client_id`.
- `bia_analysis`: `service_name`/`rto_hours`/`rpo_hours`/`daily_impact_eur`. **Sin RLS de tabla** (solo `require_owner`).
- `incidents` (CCN-STIC 817), `continuity_test_execution`, `cliente_continuidad` (1-row/proyecto).

### 3. Endpoints (verificados en `main.py`)
- **Riesgos** (`/api/v1`, `require_owner`): 11 endpoints — CRUD + `monitor`/`materialize`/`close` + `instantiate-catalog` + `dashboard` semáforo.
- **Incidentes**: 3 admin (`report`/`transition`/`classify`) + 5 cliente (`list`/`detail`/`review`/`document-hash`/`finalize-close`).
- **BIA**: 3 admin · **Continuidad**: 5 cliente + 2 admin + 4 continuity-test-execution.
- **m_live_records** (`/projects/{id}/records/...`, admin-o-cliente): dashboard + categorías requeridas + CRUD genérico por tipo + export CSV/XLSX + `/nc/promote` + `/nc/structured` (require_owner).

### 4. Máquinas de estado y lógica
- **Riesgo**: `identificado → monitorizado → materializado → cerrado`. Hooks reactivos en materialización: crea `escalation_event` (M18) + `ChangeRequest` (M17) si impacto>5d o prob≥0.7 (best-effort).
- **Incidente** CCN-STIC 817: `created→triaged→investigated→mitigated→resolved→closed`; **cliente solo ve `resolved`+`closed`**. Decision tree determinista (`ccn_cert_decision_tree.py`): medium/low → internal_only; critical/high → `lucia_federation` (24h) o `manual_notification` (72h) — art. 33 RD 311/2022. **Auto-submit LUCIA (#32)** cableado (antes dead-code): best-effort pero SIEMPRE emite `audit_log` R6. Cierre con firma cliente (SHA256 canonical 7 campos → M05 SigningIntent).
- **Celery C#35** (`tasks.py`): reloj de deadlines art. 33 cada hora; escala a M18 si el plazo CCN-CERT/LUCIA vence o está a <6h. Idempotente.
- **Auto-population**: `after_insert` listeners SQLAlchemy (Incident→E-305, Change→E-308, ProviderAssessment→E-312), sesión async post-commit, fallo = warning. **NC promotion R26**: E-321+E-322 JSONB → `audit_sessions`+`audit_findings`, upsert idempotente, valida PAC ≤90d para NC mayor.
- **m_live_records** matriz por categoría: BÁSICA=17, MEDIA=24, ALTA=26 tipos (26 schemas Pydantic `extra=forbid`).

### 5. Medidas ENS
`op.exp.3` (incidentes 817) · `op.exp.5`/E-306 (vulnerabilidades) · `op.exp.1`/E-308 (libro cambios) · `op.cont.3`/E-317-319 (BIA+DRP) · `op.cont.4` (pruebas continuidad) · `op.pl.1` (catálogo 31 riesgos) · `org.2`/`org.4` (notificación art. 33 LUCIA/CCN-CERT) · `mp.per.3`/E-303-304 (inventario empleados) · `mp.s.1`/E-300-302 (inventario activos) · E-320/321/322 (auditorías/NC) · E-323/324/325 (comité SGSI/KPI).

### 6. Integraciones
M05 (firma `incident_close`), M12 (`triggers.py` magic-links auto en `phase_changed` — 4 milestones), M17 (`ChangeRequest` auto), M18 (escalation + reloj LUCIA), M27 (`lucia_federation.submit_incident`), M14/M28 (auto-populate E-312/E-308), audit_log R6 Sub-atom 5.A.

### 7. Gotchas / dead code
- **Severidad divergente**: `classify` acepta ES (`baja/media/alta/critica`) y hace UPDATE SQL directo sin normalizar, mientras `create_incident` espera EN — posible severidad ES en DB.
- **Magic-link trigger inert**: `triggers.py` depende de `project_lifecycle_events.event_type='phase_changed'` (trigger BD MB-6.1 **pendiente**) → en prod queda inerte hasta activarlo.
- **Typo persistido**: campo `leciones_aprendidas` (falta «c») en `E305LibroIncidentesEntry` schema y JSONB.
- **BIA sin RLS** de tabla (solo require_owner). Catálogo YAML 31 entradas vs «30 riesgos base» documentados.

### 8. Tests
m19_risk: 11 ficheros (~2.300 LOC: service/api/bia/triggers/incident_workflow/lucia_32/deadline_35/continuidad). m_live_records: 5 ficheros (~1.190 LOC: schemas/auto_population/r26/categories).

### 9. Discrepancias CLAUDE.md vs código
| Claim | Realidad |
|---|---|
| «m_live_records backend-only · scope-out frontend» | **FALSO**: existe `/client-portal/registros/[tipo]` con los 26 tipos + `LiveRecordCreate`/`LiveRecordDetail` + hook `useLiveRecords`. Frontend dedicado real. |
| «E-303/304/305/308 dentro M16/M19» | El catálogo real cubre **E-300..E-325** (26 tipos en 9 bloques), incl. continuidad E-317/318/319 y comité SGSI E-323/324/325. |

### 10. Veredicto
**m19_risk = completo** (producción-grade, máquinas de estado, LUCIA auto-submit, firma cliente; dependencia trigger BD MB-6.1 pendiente). **m_live_records = completo** (26 schemas, 3 flujos auto-populate, R26, frontend cliente; typo cosmético).


## 37 - M21 Diagnostico gratuito (lead magnet)

> **DISCREPANCIA RAIZ (critica)**: la parcela describe un *diagnostico ENS gratuito publico (token, cuestionario, captacion de leads, sin cuenta)*. **El codigo real de `m21_diagnosis` NO es eso**: es un **Diagnostico Organizacional interno, project-scoped, Marcos-only** (`require_owner`), alimentado por las respuestas de M16 Onboarding. NO hay token publico, NO flujo "sin cuenta", NO captacion de leads. El lead-magnet/precliente con magic-link vive en **M16/M12/M13** (grep apunta a `m16_onboarding`, `m12_magic_link`, `m13_commercial`).

### Proposito y dominio (REAL)
- Diagnostico de madurez ENS de proyecto/cliente ya contratado: madurez L0-L5, ISO27001 coverage, cross-compliance (RGPD/NIS2/DORA/AI Act), stakeholders, procesos, quick-wins. Entregable **E-090** para el Comite del cliente (fase K.4 / "Paso 5"). Sibling de `m21_portal_cliente` (numbering anomaly intencional).

### Ficheros clave
- `api.py` (440) — router `/diagnosis/*`, `require_owner` global, RLS via `get_project_owner(pid)`.
- `service.py` — `run_diagnosis` orquesta 4 sub-analisis + `DiagnosisRun` + commit explicito.
- `maturity_service.py` (253) — scoring L0-L5 determinista, `SCORING_CONCEPTS` + alias anti-drift #6.
- `cross_compliance_service.py` (456) — reglas RGPD/NIS2/DORA/AI Act/ENS por sector+tamaño+datos.
- `compliance_service.py` — `detect_compliance_obligations` (variante usada por `service.run_diagnosis`).
- `iso27001_coverage.py` — cobertura ENS desde controles ISO via `ens_iso27001_mapping` (CCN-STIC 825).
- `{stakeholders,processes}_service.py` + `{stakeholder,process}_service.py` — **pares duplicados**.
- `quickwins.py` — 8 reglas deterministas (`lambda condition` + `medida_ens`).
- `report_generator.py` — `generate_report` (JSON) + `generate_report_docx` (docxtpl, 501 si ausente).
- `paso5_orchestrator.py` — `run_full_diagnosis_paso5` + `build_e090_context`.
- `dashboard_*.py` — dashboard home admin (next-actions+readiness M09, ADR-035), NO es diagnostico.

### Modelo de datos (`backend/app/models/diagnosis.py`)
| Tabla | Cols clave | Tenant |
|---|---|---|
| `diagnosis_runs` | status, triggered_by, *_analysis JSONB, summary, `confidential_notes_encrypted` (Fernet/M16), report_data/docx/pdf_path | `project_id` (NO FK, indexada) |
| `stakeholders` | nombre, poder/interes 1-5, actitud, `notas_confidenciales` | `project_id` FK projects |
| `business_processes` | criticidad, rto/rpo_horas, bpmn_mermaid | `project_id` FK |
| `legal_obligations` | normativa, articulo, impacto_ens, `measure_codes_relacionadas` JSONB | `project_id` FK |

RLS via `33cef115cdf5_san_b_rls_21_tablas`. Migraciones `e09fe52908a7` (diagnosis_runs) + `b5d2a81f4e93` (C4). `diagnosis_runs.project_id` desnudo (sin FK ni `client_id`); RLS via `set_tenant_context`.

### Endpoints (todos `require_owner`, prefijo `/api/v1/diagnosis`)
- `POST /projects/{pid}/run` · `GET .../latest|runs|maturity|stakeholders|compliance`
- `POST .../runs/{rid}/generate-report|generate-docx` · `GET .../download-docx|quick-wins`
- CRUD `POST/GET .../diagnosis/{stakeholders|processes|legal-obligations}`
- `POST .../diagnosis/export-to-magerit?magerit_analysis_id=` → crea `MageritAsset` (asset_type S, criticidad→valor DICA)
- `POST .../cross-compliance/iso27001/coverage`
- (dashboard_api) `GET /api/v1/projects/{pid}/dashboard`

### Logica / algoritmos
- **Madurez ≠ conformidad** (documentado explicito): mide madurez para dimensionar propuesta; conformidad la fija la SoA. `_points_to_level` (>=0.9 L5 … >0 L1). 7 dominios. `_NEUTRAL_VALUES` (`no_obligatorio` no penaliza). Multi-select toma el max.
- Fuente de respuestas: `OnboardingResponse` de sesiones M16 `COMPLETED` + roles via PKG graph (`pkg_get_stakeholder_roles`).
- Cross-compliance: reglas por norma (`_rgpd_obligations`, etc.) con `Obligation.measure_codes`.
- Sin maquina de estados formal: `DiagnosisRun.status` running→completed/failed (try/except traga la excepcion → status failed, NO re-raise).

### Medidas ENS cubiertas (referenciadas en codigo)
- quickwins: `org.1`, `op.ext.1`, `op.acc.6`, `mp.info.9`, `mp.info.1`, `op.mon.1`, `op.exp.2`, `mp.s.2`
- cross_compliance RGPD: `mp.info.1`, `op.exp.4`
- E-codes: **E-090** (informe diagnostico, via M6 Document Factory)

### Integraciones
- M16 (respuestas + `token_encryption` Fernet), M01 (category hint), M02 MAGERIT (export assets), M09 (readiness dashboard), M06 (E-090). **Sin LLM/MCP/SSE/audit_log hash-chain/magic-links** (determinista puro).

### Gotchas / dead code
- Duplicidad: dos orquestadores (`service.py` vs `paso5_orchestrator.py`) y dos impls stakeholders/processes (`*_service.py` vs `*s_service.py`) — riesgo de divergencia.
- Dos motores de obligaciones: `compliance_service` vs `cross_compliance_service`.
- `TODO-RBAC-PER-ENDPOINT-001` en `api.py`. `run_diagnosis` traga excepciones (status=failed silencioso, sin telemetria). `generate-docx` → 501 si `docxtpl` ausente.

### Veredicto: **COMPLETO** (production-grade) para lo que ES (diagnostico organizacional interno), pero **NO IMPLEMENTA** la parcela nominal (lead magnet publico gratuito). Funcionalidad real solida y determinista; la deuda es duplicidad de servicios y mismatch de naming/spec.


## 38 - M21 Backend portal cliente (read APIs LIMIT 1)

**Parcela**: `backend/app/motors/m21_portal_cliente/` · 21 .py + 1 YAML · ~6 500 LOC auditadas completas.

---

### Propósito y dominio

Portal persistente cliente↔Marcos: login email/password (SAN-E v3.MB-1.1), sesiones httpOnly + CSRF triple binding, vistas read-only del proyecto (R27 LIMIT 1), chat SSE, tareas workflow, upload evidencias/documentos, notificaciones inbox, MFA TOTP/email, cockpit Marcos, acceso soporte trazado. ADR-013 v3 single-user-RW — 1 usuario por cliente, rol `rw` único.

---

### Ficheros clave

- `api.py` (2 079 LOC): 4 routers · 29 endpoints: auth_router, portal_router, cockpit_router, support_router
- `auth_service.py` (626): login/logout/sessions/lockout/password-policy/`mint_support_session`
- `chat_service.py` (570): ChatService SSE + SLA 2h + WhatsApp bridge M31
- `mfa_service.py` (464): TOTP + backup-codes + email-OTP (TTL 10 min, 5 intentos)
- `notification_service.py` (356): `emit_client_notification` + SSE + audit_log Sub-atom 5.A centralizados
- `task_service.py` (348): `ClientTaskService` regeneration idempotente por phase + lifecycle
- `audit_log_service.py` (215): hash chain SHA-256 per proyecto · verify + export
- `models_chat.py` / `models_tasks.py`: `ChatThread`+`ChatMessage` (read_at) · `ClientTask` UniqueConstraint
- `branding_service.py`: per-cliente color/logo MinIO · `ClientBrandingView`
- `task_templates.yaml` (1 117 LOC): 18+ templates workflow phase × categoría × arquetipo
- Sub-routers: `audit_api`, `task_api`, `chat_api`, `evidencias_upload_api`, `mfa_api`, `notifications_inbox_api`, `recent_activity_api`

---

### Modelo de datos / tablas

| Tabla | RLS | Notas clave |
|---|---|---|
| `client_users` | `bypassrls` | `mfa_enabled`, `locked_until`, `failed_attempts` |
| `client_sessions` | `bypassrls` | `is_support_access`, `support_admin_user_id`, `revoked_at` |
| `client_user_audits` | `bypassrls` | `chain_index`, `prev_hash`, `current_hash` SHA-256 |
| `chat_threads` | FullMixin | `last_client_message_at`, `last_admin_response_at` (SLA) |
| `chat_messages` | FullMixin | `read_at` nullable · unread tracking |
| `client_tasks` | FullMixin | UniqueConstraint(project_id, template_id) idempotente |

**R27 LIMIT 1**: verificado en 7 endpoints — `portal_project`, `portal_retainer`, `portal_retainer_offer`, `portal_categorizacion`, `portal_documents_upload`, `cockpit_create_user`, `open_support_access`. Todos usan `ORDER BY created_at DESC LIMIT 1` sobre `projects WHERE client_id = :cid AND deleted_at IS NULL`.

**RLS**: `SET LOCAL ROLE fulkro_app_bypassrls` (scope transacción) + cross-tenant check manual `str(row["client_id"]) != str(user.client_id)` en downloads — doble defensa.

---

### Endpoints reales (rutas verificadas en código)

**`/api/v1/client-auth`**: `POST /login` · `/logout` · `/change-password`

**`/api/v1/client-portal`** (19 endpoints): `/me` · `/project` (LIMIT 1) · `/documents` (ILIKE+folder_id+sort) · `/folders/tree` · `/documents/upload` (→MinIO) · `/documents/{id}/versions|preview|download` · `/evidence` (scan_status filter) · `/evidence/{id}/preview|download` (403 si not clean) · `/retainer` · `/invoices` · `/dashboard/adaptive` (cross-motor M01/M02/M03/M07/M18/M19) · `/branding` · `/branding/logo` · `/categorizacion` · `/retainer-offer` · `/retainer-offer/{id}/decision` (→LifecyclePaso4Service)

**`/api/v1/clients/{client_id}/users`** (`require_owner` · 6 endpoints): crear, resend-invite, listar, reset-password, PATCH, DELETE

**`/api/v1/clients/{client_id}/support-access`** (`require_owner`): JWT TTL 45 min + `support=true` + audit_log

**Sub-routers en main.py**: `client_audit_router` · `client_tasks_router` · `admin_tasks_router` · `client_chat_router` · `admin_chat_router` · `client_evidencias_router` · `recent_activity_router` · `client_inbox_router` · `client_portal_mfa_router`

---

### Lógica de negocio crítica

- **CSRF triple binding**: `header_csrf == cookie_csrf == JWT.claims["csrf"]` vía `crypto.constant_time_eq` — solo métodos mutating. Correcto.
- **Hash chain (R6)**: `SHA256(canonical_json + "|" + prev_hash + "|" + chain_index)`. `verify_chain_integrity` ASC hasta 1 000 registros. Best-effort en login/logout: skip silente si project no resolvable.
- **Soporte impersonation**: `mint_support_session` JWT `support=true` TTL 45 min + `is_support_access=True`. Logout emite `support.access.ended` (RGPD art.15).
- **ChatService advisory lock**: `pg_advisory_xact_lock(hashtext('chat_thread_{project_id}'))` evita duplicate threads. Pattern #22.
- **MFA email**: OTP enviado en step-1 si `mfa_method='email'`, TTL 10 min, 5 intentos.
- **`send_magic_link=True`** (cockpit): MB-4.bis3 ADR-020 v3 envía email con temp_password, NO magic-link. Nombre de parámetro vestigio engañoso.

---

### Medidas ENS cubiertas

`op.acc.1` password policy backend autoridad · `op.acc.4` lockout 5/30 min · `op.acc.5` MFA TOTP+email OTP opt-in · `op.acc.6` sesiones TTL 12h revocables + httpOnly · `op.exp.10` CSRF triple binding + impersonation trazado · `mp.info.3` flag `interno=false` docs · `mp.info.6` gate `scan_status='clean'` evidencias · `org.2` hash chain SHA-256 Sub-atom 5.A · `org.3` `export_chain` para auditor ENAC · `org.4` `support.access.started/ended` audit_log art.15 RGPD

---

### Gotchas y deuda técnica

**G1 — Evidence preview/download usa filesystem local, NO MinIO**: `_resolve_local_path(row["fichero_path"])` en preview+download. En prod Hetzner rutas efímeras → 404 en restart. Upload de *documentos* sí usa MinIO. Inconsistencia conocida.

**G2 — `_RETAINER_PRICING` hardcodeado** (api.py:1952-1963): dict estático. Si Marcos edita en `/admin/settings/pricing`, `/retainer-offer` NO refleja cambios.

**G3 — `resolve_primary_actor` misclasifica DPO/CISO**: heurística "primer actor != Marcos → cliente". Señalado en MEMORY, sin corregir. Afecta potencialmente routing notificaciones.

**G4 — Bearer token legacy**: `get_current_client_user` acepta Authorization Bearer (deprecación en BLOQUE 5/7 no ejecutada). No bug de seguridad, pero amplía superficie.

**Dead code**: `build_logo_url` retorna siempre `None`. Parámetros `magic_link_id`+`ttl_hours` en `_enqueue_client_user_invited` siempre `None`/`0` post-MB-4.bis3.

---

### Discrepancias CLAUDE.md vs código

1. **"fuente única pricing_config BD"**: `api.py:1952` tiene `_RETAINER_PRICING` dict estático — NO lee BD. Si Marcos edita UI, retainer-offer no cambia.
2. **"magic links para clientes"**: `send_magic_link=True` ya NO envía magic-link (MB-4.bis3). Envía email temp_password. Nombre vestigio engañoso.
3. **"21 ficheros"**: correcto solo contando .py (excluye .yaml y README.md).

**Veredicto: COMPLETO** con 2 gotchas menores (evidence preview usa filesystem local, _RETAINER_PRICING estático). 29 endpoints con lógica real. R27 LIMIT 1 universal. R29 friendly (español, sin coerción). R6 hash chain operacional.


## 39 - M22 Discovery (descubrimiento de activos)

### Proposito y dominio

Motor de descubrimiento tecnico integral. Orquesta 8 modulos: inventario MAGERIT de activos cloud/on-prem, identidades con alertas deterministicas, configuraciones de seguridad (TLS/DNS/cloud), importacion de vulnerabilidades (NO escaneo propio), data stores con patrones PII, logging/SIEM assessment, DFDs Mermaid, y continuidad/DRP. Alimenta M21 (E-090 seccion 3.2), M8 (contexto inicial pentest), MAGERIT M2, PKG-lite grafo activos.

---

### Ficheros clave (23 ficheros Python + 1 template DOCX)

- `api.py`: 29 endpoints REST admin-only bajo `/api/v1/discovery/projects/{id}/...`
- `orchestrator.py`: `create_run`/`execute_run`; 8 modulos independientes; estados `pending→running→completed/failed/cancelled`
- `asset_discovery.py`: DTOs M16 → `DiscoveredAsset` + PKG-lite; criticidad heuristica (produccion/PII/internet)
- `identity_discovery.py`: 7 `ALERT_RULES` deterministicas; `DiscoveredIdentity` + `DiscoveryAlert`; MFA coverage
- `magerit_categories.py`: Enum `MageritCategory` 9 categorias v3; `_RESOURCE_TYPE_MAP` 34 tipos cloud (M365/AWS/Azure/GitHub/GWS)
- `vuln_discovery.py`: Importador OpenVAS/Nuclei/Trivy/generic; mapeo CVE→ENS por 10 regex patterns
- `config_discovery.py`: Checks TLS/DNS/cloud; checkers inyectables prod/tests; `TLS_BASELINE`/`DNS_BASELINE` deterministicos
- `data_discovery.py`: Patrones regex PII espanol (DNI, NIF, IBAN, tarjeta, NSS, salud); clasifica `discovered_data_stores`
- `log_assessment.py`: Madurez L0-L5 SIEM; 6 controles `op.exp.8`; retenciones ENS 90/180/730 dias por categoria
- `continuity_service.py`: Madurez L0-L5 DRP; backups cifrado/offsite/prueba; SPOFs criticos
- `dataflow_service.py`: DFDs Mermaid flowchart cruzando assets+identities+data_stores
- `report_generator.py`: Consolida 8 modulos → JSON + DOCX (docxtpl graceful 501 si no disponible)
- `paso6_orchestrator.py`: Orquestador Paso 6: M365+AWS → M21+M8+MAGERIT feed
- `paso6_m365_connector.py`: Graph API + Beta; 8 scopes delegados; refresh automatico; pagination `@odata.nextLink`
- `paso6_aws_connector.py`: AssumeRole STS 3600s; IAM+EC2+S3+RDS+CloudTrail+GuardDuty+SecurityHub
- `paso6_demo_mocks.py`: Mocks DataForma: 20 usuarios, 45 activos, 15 vulns, madurez L1
- `paso6_e090_technical.py`: Seccion 3.2 E-090 (NO LLM); score L0-L5 CMMI-like; trazable ENAC
- `paso6_config_detector.py`: Checks ENS baseline: MFA%, cifrado at-rest, logging, backup
- `paso6_vuln_inventory.py`: ASFF Security Hub + M365 Defender + Nuclei → `VulnerabilityFinding`; feed M8
- `paso6_asset_discoverer.py`/`paso6_data_flow_mapper.py`/`alerts_service.py`: helpers Paso 6

---

### Modelo de datos (8 tablas propias M22 + 2 compartidas M16)

| Tabla | Columnas destacadas | RLS propia |
|---|---|---|
| `discovery_runs_m22` | `project_id`, `modules[]`, `connector_sources{}`, `status`, `progress{}` | NO |
| `discovery_alerts` | `project_id`, `modulo`, `severidad`, `codigo`, `medidas_ens_afectadas[]`, `gap_volcado` | NO |
| `discovered_configurations` | `project_id`, `control_id`, `estado`, `gap_severidad`, `medidas_ens_afectadas[]` | NO |
| `vulnerability_inventory` | `project_id`, `cve_id`, `cvss_score`, `cvss_severity`, `estado`, `mitre_tactics[]` | NO |
| `discovered_data_stores` | `project_id`, `clasificacion_inicial`, `patrones_detectados[]`, `cifrado_en_reposo` | NO |
| `logging_assessments` | `project_id`, `nivel_madurez_logging`, `cumple_op_exp_8`, `gaps_op_exp_8[]` | NO |
| `data_flow_diagrams` | `project_id`, `nodos[]`, `flujos[]`, `mermaid_code`, `clasificacion_max_datos` | NO |
| `continuity_assessments` | `project_id`, `tiene_drp`, `drp_probado`, `nivel_madurez_continuidad` | NO |
| `discovered_assets` (M16) | `project_id`, `tipo_magerit`, `criticidad_propuesta`, `discovery_run_id`, `pkg_node_id` | NO |
| `discovered_identities` (M16) | `project_id`, `es_privilegiada`, `mfa_activo`, `tipo_cuenta`, `discovery_run_id` | NO |

**BRECHA RLS**: ninguna tabla M22 tiene `client_id` ni politica de fila PostgreSQL. Aislacion solo via `set_tenant_context` por sesion (project-scoped). No cumple el estandar FULKRO para tablas con datos sensibles de cliente.

---

### Endpoints (29, todos `require_owner`)

Prefijo `/api/v1/discovery/projects/{project_id}/`: `runs` (5), `assets` (4), `identities` (4), `alerts` (2), `configurations` (3), `vulnerabilities` (5 incl. PATCH estado + POST import openvas|nuclei|trivy|generic), `data-stores` (4), `logging` (2), `dataflows` (3), `continuity` (2), `report` (2 JSON+DOCX), `summary` (1).

---

### Logica de negocio clave

- **Modulos independientes**: try/except por modulo en `execute_run`; `vulnerabilities` es `awaiting_import` (M22 no escanea).
- **7 reglas identidad**: `PRIV_NO_MFA` (critica), `INACTIVE_90D` >90d (alta), `SHARED_ACCOUNT` (alta), `EXTERNAL_PRIVILEGED` (critica), `PASSWORD_POLICY_FAIL` (alta), `SERVICE_NO_OWNER` (media), `NO_MFA_STANDARD` (media).
- **Criticidad**: base MAGERIT (COM/D=alta) + bump +1 si produccion/PII/internet_facing.
- **Madurez L0-L5**: 3 implementaciones CMMI-like independientes (logging/continuity/e090_technical).
- **Paso 6**: M365 Graph v1.0+beta (8 scopes, pagination max 3p) + AWS AssumeRole (8 servicios, eu-west-1).

---

### Integraciones verificadas

- **M16**: DTOs `DiscoveredAssetDTO`/`DiscoveredIdentityDTO` compartidos; `pkg_service.add_node()` → PKG nodos `asset`/`identity`
- **M21**: `paso6_e090_technical` → E-090 seccion 3.2; `feed_magerit_assets()` → `magerit_assets`
- **M8**: `feed_m8_initial_context()` → subset findings fase 1 diagnostico
- **audit_log/SSE/R6/LLM**: NINGUNO integrado (0 imports empiricamente verificados; 100% determinista)

---

### Tests, Frontend, Migraciones

- **Tests**: 6 ficheros ~2534 LOC. Inyeccion fetchers/checkers; sin credenciales cloud reales.
- **Frontend**: `/admin/projects/[id]/discovery` → `DiscoveryPanel.tsx` + 9 tabs TSX (2263 LOC). Admin-only correcto.
- **Migraciones**: 3 Alembic (`m22_a` runs+alertas · `m22_b` configurations+vulns+data_stores · `m22_c` logging+DFD+continuity).

---

### Medidas ENS cubiertas

`op.acc.1/2/4/5/6` · `op.exp.4/6/8` · `op.cont.1` · `op.ext.1` · `mp.com.1/2/3/4` · `mp.info.3` · `mp.sw.1/2` · `mp.s.2`

---

### Gotchas y discrepancias

- **RLS ausente en 10 tablas**: Sub-atom 5.A no aplicado en M22; aislacion solo via `set_tenant_context` session.
- **audit_log no integrado**: M22 no emite eventos al hash-chain R6 ni canonical events (0 imports confirmado empiricamente).
- **Legacy "D" vs "I" MAGERIT**: `MageritCategory.INFORMACION = "D"` vs canonical `[I]`. Documentado en modulo; migration ~30+ sitios pendiente.
- **`TODO-RBAC-PER-ENDPOINT-001`**: granularidad por endpoint pendiente; router global `require_owner`.
- **`DiscoveryAlert` hereda `Base` no `FullMixin`**: sin `deleted_at` ni soft-delete.
- **SSE ausente**: frontend usa polling; runs largos no notifican push.

---

### Veredicto

**COMPLETO**. 8 modulos de discovery plenamente implementados, production-grade con ~2500 LOC tests, 3 migraciones, 29 endpoints, 10 componentes frontend. 100% determinista (sin LLM), trazable para ENAC. Gaps operativos: RLS de fila ausente (10 tablas), audit_log no integrado, SSE ausente (polling), deuda nomenclatura MAGERIT "D"/"I" documentada.


## 40 - M25 Ciclo de vida implantacion + M28 Gobierno del cambio

### Proposito y dominio

**M25** gestiona el ciclo de vida completo del proyecto ENS (DRAFT→PURGED), archival ZIP Ed25519, grace period GDPR 8 meses y reactivacion desde backup. Cubre el "Paso 4" post-certificacion: oferta retainer, decision cliente y borrado honesto.

**M28** gobierna cambios organizativos: motor de materialidad determinista (10 preguntas binarias → MINOR/RELEVANT/MATERIAL), topologia de roles ENS (5 patrones CCN-STIC 801), recategorizacion con guards por nivel N1-N3 y auditorias extraordinarias.

---

### Ficheros clave

**M25 (~3.200 LOC + 990 tests)**

| Fichero | Contenido |
|---------|-----------|
| `lifecycle_service.py` (436L) | FSM 10 estados + archival ZIP SHA-256 + purge |
| `lifecycle_paso4.py` (1111L) | Grace period 8m, backup Ed25519, GDPR delete, reactivacion |
| `backup_builder.py` (495L) | ZIP 8 secciones (dossier+docs+evidencias+facturas+findings+audit_log+manifest) |
| `api.py` / `api_paso4.py` | REST FSM basica (243L) + cockpit Marcos (449L) |
| `public_api.py` | Portal magic-link descarga; cert+dossier → 501 stubs |
| `exit_checklist_service.py` | 16 items pre-cierre 4 categorias + readiness gate |
| `tasks.py` | 2 Celery tasks diarias (04:30 grace, 05:00 backup expiration) |

**M28 (~820 LOC + 554 tests)**

| Fichero | Contenido |
|---------|-----------|
| `materiality_engine.py` (125L) | Arbol decision determinista 10 preguntas puro (NO-LLM) |
| `topology_service.py` (109L) | 5 patrones TOPOLOGY_LIBRARY + recommend_pattern |
| `recategorization_service.py` (112L) | Guards N1/N2/N2.5/N3 via floor_elevation_service OPS-026 |
| `role_topology_extensions_api.py` | 4 endpoints assign/vacate/topology/drift-summary |
| `api.py` (472L) | 8 endpoints change governance + cascade adenda M14 |

---

### Modelo de datos y RLS

| Tabla | Motor | RLS | Politica |
|-------|-------|-----|---------|
| `project_lifecycle_states` | M25 | SI | project_id isolation |
| `project_lifecycle_events` | M25 | SI | project_isolation |
| `project_archived_backups` | M25 | SI | client_isolation |
| `exit_checklist_items` | M25 | SI | project_isolation |
| `archived_projects` | M25 | SI | via client_id |
| `change_topologies` | M28 | SI | admin_all (fulkro_app USING true) |
| `project_role_assignments` | M28 | SI | project_isolation |
| `changes` (M27-shared) | M28 | SI | project_isolation ADR-023 |

Patron comun: `get_project_owner(pid)` SECURITY DEFINER → `set_tenant_context` establece `app.current_*`.

---

### FSM M25 - Estados

```
DRAFT → NEGOTIATING → SIGNED → ACTIVE → CERTIFIED → RETAINER → ENDED_RENEWAL_OK ─┐
             ↘ DRAFT                               ↘ ENDED_CHURN                   │
                                                             → ARCHIVED → PURGED ←─┘
```

- Gate `ACTIVE→CERTIFIED`: `require_complete_audit_prep` (M09 dossier completo)
- Hook SIGNED→ACTIVE: crea workspace M20 (best-effort)
- Hook CERTIFIED→RETAINER: crea retainer M23 R_STD (best-effort)
- `mark_audit_passed()`: cascade opcional → `mark_certified()` → `offer_retainer()` (ClientNotification in-portal M21, NO magic link post ADR-020 v3)

### Grace period Paso 4

Celery `lifecycle_grace_period_check` diario sobre `ENDED_CHURN`:
- Dia 150 → warning Marcos; dia 180 → reconsideration cliente (M21); dia 210 → backup ZIP + magic link; dia 240 → GDPR hard delete (documents NULL, evidence/findings DELETE, client_users deactivate)

---

### Endpoints expuestos (summary)

**M25 admin (require_owner):** FSM state/transition/history/archive/purge, mark-certified, audit/mark-passed, offer-retainer, start-grace-period, generate-backup, lifecycle/status|events, lifecycle/decision, exit-checklist CRUD.

**M25 publico (magic link peek-no-consume):** `/public/download/{token}` metadata + stream ZIP (`DESCARGA_BACKUP_ARCHIVO` funcional); `/public/retainer-offer/{token}` GET + POST respond.

**M28 admin (require_owner):** changes intake+assess+open, recategorizations, extraordinary-audits, roles/topology review+get, role-topology assign+vacate, drift-summary.

---

### Logica de negocio clave

**M28 materiality engine** (R1: determinista, NO LLM):
- `_MATERIAL_TRIGGERS` → score 70+5n, deadline 1d, signoffs [rseg, sponsor, comite], docs E-046+E-615
- `_RELEVANT_TRIGGERS` → score 30+5n, deadline 5d, docs E-046+E-047
- MINOR → deadline 10d, solo E-046
- Cascade MATERIAL: `maybe_dispatch_adenda_on_materiality_assessed` M14 (graceful ImportError)

**Recategorizacion (C#55)** — reutiliza `floor_elevation_service` M01 (OPS-026 DRY):
- N3 (firmado) → blocked_signed; N2.5 (en vuelo) → blocked_in_flight; N1/N2 → aplica + regenera borradores

**Topology** (5 patrones deterministicos): multi_site|ALTA → E; <25emp → D; CISO interno → C; TI interno → A; MSP → B. PATTERN_D exige memo justificacion.

---

### Integraciones cross-motor

- **M09**: gate CERTIFIED + dossier best-effort en backup ZIP
- **M20**: workspace en SIGNED→ACTIVE
- **M21**: `emit_client_notification` retainer offer + reconsideration
- **M23**: `create_retainer` en CERTIFIED→RETAINER + decision accept
- **M12**: magic links DESCARGA_BACKUP_ARCHIVO, OFERTA_RETAINER, RECONSIDERACION_RETAINER
- **M01**: floor_elevation_service DRY en recategorizacion M28
- **M14**: cascade adenda hook en assess MATERIAL
- **M30**: `ClientContact` FK en `project_role_assignments`
- **MinIO**: exports bucket backup ZIP (`minio://` path; fallback `local://` dev)
- **audit_log**: backup_builder exporta audit_log proyecto al ZIP (hash chain); M25/M28 NO emiten a audit_log directamente (usan `ProjectLifecycleEvent` separado)

---

### Frontend coverage

| Area | Componentes |
|------|-------------|
| M25 exit checklist | `ExitChecklist.tsx` + `/admin/projects/[id]/exit/page.tsx` |
| M25 audit/mark-passed | `MarkAuditPassedDialog.tsx` |
| M25 retainer cliente | `/client-portal/retainer/page.tsx` |
| M28 changes | `/admin/projects/[id]/changes/page.tsx` + `ChangeRequestWizard.tsx` + `ChangeImpactConsole.tsx` |
| M28 role topology | `/admin/projects/[id]/roles/page.tsx` + `RoleTopologyPanel.tsx` + `AssignContactModal.tsx` |
| M28 drift summary | `OperationsConsole.tsx` (parcial) |

---

### ENS / E-codes cubiertos

- `org.3` Roles y responsabilidades — 5 patrones + ProjectRoleAssignment (5 ENS + 6 cross-compliance)
- `org.4` Politica seguridad — responsable_informacion / servicio / sistema / seguridad obligatorios
- `org.6` Plan de adecuacion — FSM lifecycle DRAFT→CERTIFIED→RETAINER completo
- `op.exp.1` Gestion de cambios — FSM M28 MINOR/RELEVANT/MATERIAL determinista
- `op.exp.2` Gestion configuracion — recategorizacion gobernada guards N3/N2.5
- `mp.s.2` Cierre ordenado — grace period 8m + GDPR delete + backup descargable
- `mp.s.3` Continuidad — backup ZIP con reactivacion (GDPR art.20 portabilidad)
- `mp.info.3` Cifrado — ZIP SHA-256 + Ed25519 + MinIO WORM
- E-046, E-047, E-048, E-615 — documentos requeridos por nivel materialidad

---

### Gotchas y discrepancias

1. **BUG firma archival**: `lifecycle_service._sign_ed25519` usa `Ed25519PrivateKey.generate()` ephemeral (no lee `FULKRO_ML_PRIVATE_KEY`). El ZIP `archived_projects` tiene firma no-verificable externamente en produccion. `backup_builder.py` correctamente usa `FULKRO_BACKUP_SIGNING_KEY || FULKRO_ML_PRIVATE_KEY || ephemeral`.
2. **Auth gap `download_archived_backup`**: endpoint `GET /archived-backups/{id}/download` descarga sin consumir magic link — autorizacion unica via TTL+RLS (documentado como pre-cliente).
3. **Duplicado**: `_validate_token_peek` identico en M08 y M25 (`TODO-MB-4-CLEANUP-VALIDATE-PEEK-001`).
4. **501 stubs**: `DESCARGA_CERTIFICADO_CONFORMIDAD` y `DESCARGA_DOSSIER_FINAL` retornan 501 explicitamente documentado.
5. **`mv_drift_summary_10x4`**: vista materializada usada en drift-summary endpoint — no visible en migraciones M28; si no existe, endpoint devuelve lista vacia silenciosamente.
6. **CLAUDE.md afirma**: "m25_dpc + m25b_revision_anual = UI cubierto /dossier + /audit + /conformity" — en realidad el motor se llama `m25_lifecycle` (no `m25_dpc`); CLAUDE.md tiene nomenclatura incorrecta para este motor.

---

### Veredicto

**M25 COMPLETO** — FSM 10 estados, Paso 4 grace period con Celery operativo, backup builder Ed25519 completo, exit checklist 16 items, public API funcional. Stubs limitados (cert+dossier) justificados y honestamente documentados.

**M28 COMPLETO** — Materiality engine determinista, 5-pattern topology DB-backed, recategorizacion con guards, role assignment ENS 5+6 cross-compliance. Sin emision directa a audit_log (deuda menor).


## 41 - M26 Backup probado + m_audit_accompaniment

### M26 Backup & Disaster Recovery

**Propósito**: R8 (backup probado mensualmente), `op.cont.2/4`, `mp.com.9`. Platform-global, sin RLS tenant.

**5 tablas** (sin RLS): `backup_jobs` (status pending/running/completed/failed, `hash_sha256`, `encryption_key_id`) · `backup_retention_policies` (daily/weekly/monthly/yearly) · `backup_restore_tests` (`rto_seconds`, `validation_report` JSONB) · `dr_drills` (RTO/RPO objetivo vs actual) · `integrity_verifications` (discrepancies_found).

**9 endpoints** `/api/v1/backup/*` todos `require_owner` + `POST /backup-policy/3-2-1/evaluate` (sin auth, stateless — TODO-RBAC-PER-ENDPOINT-001).

**Lógica**:
- `_evaluate_health()`: green = backup <7d + restore passed <35d; yellow = sin restore/>35d; red = sin backup/>7d.
- RTO 4h, RPO 24h objetivos. `evaluate_3_2_1()`: ≥3 copias, ≥2 media_types, ≥1 offsite.
- Beat: full dom 02:00 · incr diario 03:00 · `monthly_restore_test` 1°mes 04:00 · verify_integrity dom 03:00.
- Fernet(SHA256(BACKUP_ENCRYPTION_KEY)). lru_cache. Fingerprint SHA256[:16] en `BackupJob.encryption_key_id`.
- Offsite: bucket `backup-vault-fulkro` privado. Key: `{backup_type}/{yyyymmddTHHMMSS}-{basename}.enc`.

**CRITICO — `monthly_restore_test` task es STUB**: retorna `{"status": "scheduled", "message": "Pending Hetzner provisioning"}`. NO restaura BD real. `dr_drill` ídem. Ambos `# pragma: no cover`. R8 cumplido en scheduler, restauración efectiva **pendiente Hetzner**.

**Tests**: 42 — 16 service, 10 encryption, 9 offsite (fake_minio), 7 policy 3-2-1.

---

### m_audit_accompaniment

**Propósito**: acompañamiento ciclo ENS post-implantación (CCN-STIC-808 BÁSICO autodeclaración + CCN-STIC-809/IC-01+IC-02 MEDIA/ALTA vía ENAC). Pattern #23 estado por rama.

**3 tablas** (FullMixin soft-delete, `project_id` FK CASCADE, sin `client_id` — resuelto por `get_project_owner()` SECURITY DEFINER + `set_tenant_context`): `audit_accompaniment_state` (current_state, category_branch, accompaniment_metadata JSONB) · `audit_accompaniment_artifacts` (state, artifact_type, sha256, file_path) · `audit_accompaniment_transitions` (from_state, to_state, advanced_by, transition_metadata JSONB).

**State machine (verificado en código)**:

BÁSICO 7 estados (NO ENAC): `not_started→declaration_drafted→declaration_signed→declaration_published→ccn_communicated→periodic_review_scheduled→completed` (terminal).

MEDIO/ALTO 11 estados (ENAC + renovación bianual): `not_started→preparation→docs_collected→internal_audit_scheduled→internal_audit_completed→enac_audit_scheduled→enac_audit_in_progress→{enac_findings_resolution|}enac_audit_passed→certificate_issued→biannual_renewal_scheduled→preparation` (ciclo).

**4 endpoints** (`/api/v1`): `POST /admin/projects/{id}/accompaniment/advance` · `POST /admin/projects/{id}/accompaniment/artifacts` (multipart) · `GET /admin/projects/{id}/accompaniment/timeline` (todos require_owner) · `GET /client-portal/accompaniment/timeline` (require_client_user, R27 LIMIT 1).

**Lógica clave**:
- Advisory lock `pg_advisory_xact_lock(hashtext('accompaniment_' || project_id))` (Pattern #22).
- GATE-7 (`require_clean_audit_sim`): bloquea `enac_audit_scheduled`/conformidad si NC mayores abiertas o sin simulacro. `allow_open_nc=True` trazado en audit_log (`"nc_override": True`). HTTP 409.
- audit_log Sub-atom 5.A: 5 eventos canónicos, project_id + client_id propagados.
- SSE Pattern #14: `dispatch(f"project:{project_id}", "accompaniment.state.advanced")` best-effort.
- Artifacts MVP: `/tmp/fulkro_accompaniment_artifacts`. SHA256 en memoria. S3 = Future-X.

**Tests**: 18 (15 state machine/service + 3 GATE-7): ciclo BÁSICO 7 transiciones · `ccn_communicated` AMPARO artifact vinculado · ciclo MEDIO/ALTO + renovación bianual · skip/back raises · audit_log emit · advisory lock inspect · SSE buffer · timeline snapshot · sha256 persist · GATE-7 NC mayores + simulacro.

**Gotchas**: cliente timeline LIMIT 1 sin project_id (multi-proyecto = cambio API). Artifacts `/tmp` no WORM-compliant (MVP explícito).

---

### Discrepancias CLAUDE.md vs código

1. **BÁSICO "6 states"** en CLAUDE.md → código real tiene **7 estados** (`ccn_communicated` añadido Ola 7). Test `test_basico_states_count_7` confirma.
2. **R8 "backup probado mensualmente"** descrito como cumplido → task `monthly_restore_test` es **stub** sin restauración real. Hetzner-dependiente.

### ENS cubierto

`op.cont.2` (continuidad/DR drills) · `op.cont.4` (pruebas periódicas, scheduler) · `op.exp.8` (registro actividad) · `mp.com.9` (copias seguridad + 3-2-1 compliance) · `mp.info.3` (cifrado en reposo Fernet) · `mp.info.6` (soporte físico offsite MinIO) · `org.3` + trazabilidad ENAC (state machine + audit_log R6 hash-chain).

**Veredicto**: M26 = **completo** con stub honesto en DR real (Hetzner-dependiente). m_audit_accompaniment = **completo** (7+11 estados, 3 tablas, 4 endpoints, GATE-7, 18 tests, SSE + audit_log).


## 42 - M27 Conformidad / revision anual / renovacion

### Proposito y dominio

Ciclo conformidad ENS post-implantacion: eleccion ruta (autodeclaracion BASICA vs certificacion ENAC MEDIA/ALTA), submissions a organismos (INES/LUCIA/PILAR/Registro), clock renovacion bienal, Declaracion E-180 DOCX, distintivo CCN-STIC 809 SVG, DPC anual (art.25), overlays PCE y readiness pre-firma cliente.

Alcance: todos los `.py` leidos + 5 YAMLs catalogs (520 LOC) + ORM `conformity_lifecycle.py` + tests 668 LOC.

---

### Ficheros clave

| Fichero | Proposito |
|---|---|
| `route_machine.py` | FSM conformity route · 16 estados · 2 tipos (DECLARATION/CERTIFICATION) |
| `submission_machine.py` | FSM submission · 11 estados (DRAFT→COMPLETED/REJECTED/WITHDRAWN) |
| `service.py` | Logica stateless: invariantes, renewal clock, overlay detection, PCE |
| `api.py` | 26 endpoints admin `/api/v1/conformity/*` (`require_owner`) |
| `api_paso5.py` | 16 endpoints admin lifecycle `/api/v1/projects/{id}/conformity/*` |
| `renewal_extensions_api.py` | 3 endpoints `/projects/{id}/renewal/timeline|contact-auditor|auditor-info` |
| `portal_api.py` | 7 endpoints cliente `/portal/conformidad/*` (declaration + firma) |
| `portal_api_dpc.py` | 5 endpoints cliente `/portal/dpc-anual/*` |
| `public_api.py` | `GET /api/v1/public/conformity/badge/{cert_id}/badge.svg` (sin auth) |
| `readiness_service.py` | Readiness pre-firma tier-aware: DdA+MAGERIT+Pentest+evidencias+politicas |
| `dpc_anual_service.py` | DPC anual art.25: draft idempotente + 4 secciones contexto + SHA256 + M05 |
| `renewal_scheduler.py` | Celery daily: 6m/3m/1m checkpoints bienales + auto-campana |
| `biannual_alert_task.py` | Celery `check_biannual_audits_due` · alertas art.31 |
| `distintivo_generator.py` | SVG + DOCX E-180 · cert_id uuid5 deterministico · CCN-STIC 809 |
| `distintivo_persistence.py` | Document E-049 + `emit_audit_log` best-effort |
| `ines_generator.py` | JSON CCN-STIC 824 + DOCX INES anual |
| `lucia_federation.py` | Submissions LUCIA CCN-CERT (httpx) · fallback pending_credentials |
| `conformity_service_paso5.py` | Materiality scoring + role topology patterns |
| `catalogs/pce_*.yaml` | 5 YAMLs PCE (NIS2/SSG/AWS/Azure/GCP) |

---

### Modelo de datos

13 tablas ORM todas con `project_id` (RLS via `set_tenant_context`). Principales:

| Tabla | Descripcion |
|---|---|
| `conformity_routes` | Ruta activa por proyecto |
| `conformity_submissions` | Submissions (6 targets: AUDITOR/REGISTRO/AAPP/PILAR/LUCIA/INES) |
| `basic_declarations` | Declaraciones inicial + DPC anuales (discriminado por `declaration_type`) |
| `material_changes` | Cambios materiales con scoring ENS |
| `renewal_campaigns` | Campanas bienales auto-triggered/manuales |
| `pce_overlays` / `conformity_state_snapshots` | Overlays + historial transiciones jsonb |
| `renewal_campaign_milestones` / `lucia_credentials` | Milestones + OAuth Fernet at-rest |

`basic_declarations` tiene UNIQUE partial `(project_id, anniversary_year) WHERE declaration_type='dpc_anual'`.

---

### Maquinas de estado

**RouteState** (16 estados): `ROUTE_PENDING→ROUTE_LOCKED→{DECLARATION|CERTIFICATION}_IN_PROGRESS→READY_FOR_{DECLARATION|AUDITOR}→UNDER_REVIEW→{OBSERVED|CORRECTION_REQUIRED|CONFORMANT}→REGISTERED→ACTIVE→{RENEWAL_DUE→RENEWAL_PENDING→ACTIVE|EXPIRED}|SUSPENDED`. Terminal: `{EXPIRED}`.

**SubmissionState** (11 estados): `DRAFT→GENERATED→READY_FOR_SIGNATURE→READY_FOR_SUBMISSION→SUBMITTED→UNDER_REVIEW→{OBSERVED|CORRECTION_REQUIRED|COMPLETED}`. Terminales: `{COMPLETED, REJECTED, WITHDRAWN}`.

**Renewal clock**: 9 estados `T-180→T-120→T-90→T-60→T-30→DUE→IN_PROGRESS→COMPLETED|LAPSED`. Celery daily. Checkpoints 6m/3m/1m.

**DPC anual**: draft idempotente + review (`revisada_ok|con_pregunta|suggest_change`) + signoff via M05 con SHA256 deterministico.

---

### Logica de negocio notable

- **cert_id deterministico**: `uuid5(NAMESPACE_OID, f"fulkro-conformity:{project_id}")` → URL publica estable sin tabla auxiliar.
- **Readiness pre-firma tier-aware**: BASICA (evidencias≥25, politicas≥10), MEDIA (50/18), ALTA (73/25 + pentest blocker). Pentest NO blocker en BASICA/MEDIA (fix #15 Ola 7).
- **Overlay detection**: prioridad SSG > NIS2 > SALUD > AAPP-LOCAL > PCE-PYME. Confidence 0.85 hardcoded.
- **LUCIA fallback**: sin credenciales OAuth → `pending_credentials` + JSON CCN-STIC 845 subida manual.
- **Distintivo SVG**: Pantone Orange 021C (#FE5000) unico para todas las categorias (fix F-14-06 · antes verde/azul/violeta = incorrecto vs CCN-STIC 809).
- **DOCX E-180**: firmante = Direccion (CCN-STIC 809 Anexo A) NO RSeg. BASICA autodeclaracion · MEDIA/ALTA NO sustituye cert ENAC.
- **INES**: cross-motor M01+M27+M18+M21+M15 por `organization_id`. JSON CCN-STIC 824 + DOCX.
- **Cambios sustanciales**: 5 tipos (cloud_migration/datacenter_change/merger/categoria_change/scope_expansion) disparan auditoria extraordinaria.

---

### Medidas ENS cubiertas

`org.3` (material_change scoring) · `org.4` (route lock autorizacion) · `org.5` (politica readiness gate) · `op.exp.7` (overlays terceros) · `op.exp.10` (Lucia Fernet claves) · `op.mon.1` (auditoria bienal art.31 + extraordinaria) · `op.pl.1` (route states + submissions) · `mp.info.5` (payload + firma). Ademas: art.25 RD 311/2022 (DPC anual) · CCN-STIC 809/824/844/845/892/896.

---

### Integraciones

- **M05 signing**: `SigningIntent`+`SigningEvent` para conformidad + DPC. SHA256 deterministico input.
- **M09 dossier**: `renewal_scheduler` llama `generate_dossier()` best-effort campanas bienales.
- **M18 alerts**: `AlertService` alertas art.31 + DPC anual 30 dias antes.
- **M22/M30**: activos esenciales + RSeg/sponsor desde `magerit_assets` + `client_contacts`.
- **audit_log**: `emit_audit_log` en `distintivo_persistence` best-effort non-fatal.
- **SSE**: NO integrado — sin dispatch al cambio de estado (gap UX).

---

### Gotchas y bugs detectados

1. **BUG `compute_renewal_state` L148-150**: `elif delta > 120: state = "T-180"` — deberia ser `"T-120"`. Rango 121-180 dias emite T-180. Tests no cubren este edge case.

2. **`submitted_by="marcos"` hardcoded** (api.py L464): deberia ser el usuario autenticado. TODO-RBAC-PER-ENDPOINT-001.

3. **Public badge O(n) scan**: hasta 1000 proyectos para resolver cert_id. Piloto-safe · future index.

4. **Invariante `NEVER_ACTIVE_AND_EXPIRED_TOGETHER` dead logic** (service.py L83-85): `ACTIVE` no en `TERMINAL_STATES` → condicion siempre falsa.

5. **Sin SSE dispatch**: cambios route/renewal sin eventos SSE. Cliente hace polling manual.

---

### Discrepancias CLAUDE.md vs codigo

- CLAUDE.md menciona `m25_dpc` y `m25b_revision_anual` como motores separados. La DPC anual esta integrada dentro de m27 (`dpc_anual_service.py` + `portal_api_dpc.py`) — no existe motor `m25b` separado.
- CLAUDE.md no menciona los 5 YAMLs PCE en `catalogs/` ni los adapters LUCIA/INES/CLARA/PILAR/Registry como parte del scope m27.

---

### Veredicto

**COMPLETO** (production-grade, 1 bug logico menor). Motor exhaustivo: FSMs robustas, DPC anual + M05 firma, renewal Celery bienal, 5 PCE overlays YAML, distintivo CCN-STIC 809 SVG+DOCX cert_id idempotente, LUCIA/INES/PILAR adapters, readiness tier-aware, 40+ tests. Bug `T-180` duplicado en renewal clock no bloquea flujo principal.


## 43 - m_cloud_connectors (AWS/Azure/M365/Google/GitHub)

**Ruta**: `backend/app/motors/m_cloud_connectors/` · 15 ficheros · 7.300 LOC  
**Tests**: 24 ficheros · 183 funciones + 11 E2E integración (M365+GWorkspace mock httpx)

---

### Propósito

Capa unificada SOBRE `m16_onboarding` (ADR-025 DRY): delega OAuth + discovery a las 5 clases M16. Añade: persistencia en `cloud_resources`, motor diagnóstico ENS determinístico (R1), workflow aprobación remediación, digest mensual (retainer L), integraciones M03/M04/M07.

---

### Ficheros clave

| Fichero | LOC | Rol |
|---|---|---|
| `integrations.py` | 960 | Cross-motor M03/M04/M07 enrichment |
| `api.py` | 856 | Admin endpoints (connectors+gaps+diagnosis+integrations) |
| `remediation_orchestrator.py` | 785 | State machine + SSE + audit trail inmutable |
| `gap_rules.py` | 637 | RULE_CATALOG 10 reglas + CONNECTOR_PROVIDER_ENS_GUIDANCE |
| `models.py` | 623 | 5 tablas ORM + 7 enums |
| `service.py` | 594 | CloudConnectorService: CRUD + sync + UPSERT resources |
| `remediation_api.py` | 524 | REST approve/reject/execute/verify |
| `api_cliente.py` | 480 | Portal cliente R29: list + connect + request-disconnect |
| `system_consciousness_hooks.py` | 419 | 7 subsistemas best-effort post-VERIFIED |
| `digest_service.py` | 416 | Snapshot mensual SQL determinístico 0 LLM |
| `diagnostic_gap_engine.py` | 290 | Engine UPSERT idempotente + auto-resolve |
| `base_connector.py` | 129 | M16 DTO → CloudResource dict (pure functions) |

---

### Modelo de datos (5 tablas · todas `project_id FK`)

| Tabla | RLS vía | Notas |
|---|---|---|
| `cloud_connectors` | `project_id` | `UniqueConstraint(project_id, provider)` · `remediation_enabled` bool OFF · `auto_remediation_policy` (off/safe_auto_only/full) · `granted_write_scopes` JSONB (ADR-055) |
| `cloud_resources` | `project_id` + `connector_id` | `UniqueConstraint(connector_id, resource_external_id, resource_type)` · `checksum` SHA-256 MoM |
| `cloud_gaps` | `project_id` | `ens_measure_code` + `approval_status` 9 estados · `raw_evidence` JSONB trazabilidad ENAC |
| `cloud_sync_jobs` | `project_id` + `connector_id` | pending/running/completed/failed/cancelled |
| `cloud_digest_snapshots` | `project_id` | `compliance_score` 0-100 · `open_gaps_by_severity` JSONB |
| `cloud_remediation_approval_logs` | `project_id` directo | NO FullMixin · inmutable · `idempotency_key` SHA-256 · `created_at` via Python lambda (OPS-047 ordering estable) |

RLS enforced: `set_tenant_context(db, project_id=project_id)` antes de cada query en endpoints. Celery task bypasa RLS en primer query de listado de projects (corre como `fulkro_migrate`).

---

### Endpoints REST (resumen)

**Admin** (`require_owner` · project-scoped): list/link/revoke connector; trigger sync (202); browse resources/sync-jobs; list/resolve cloud-gaps; run gap engine; bulk measure-status (M03); plan-suggestions (M04); propose/execute/mark-executed/mark-failed/audit-log (remediación); catalog providers/supported-measures.

**Cliente** (`require_client_user` · ADR-013): list connectors (R29 friendly); init OAuth connect (delega M16); request-disconnect (chat-mediated ADR-014); approve/reject gap; list pending approval.

---

### Gap engine · 10 reglas determinísticas (R1 inviolable)

| Regla | ENS | Severidad | B/M/A |
|---|---|---|---|
| `rule_users_no_mfa` | `op.acc.6` | CRITICAL | B/M/A |
| `rule_excess_privileged` | `op.acc.5` | HIGH | M/A |
| `rule_inventory_coverage` | `op.exp.1` | MEDIUM | B/M/A |
| `rule_unencrypted_storage` | `mp.info.3` | CRITICAL | B/M/A |
| `rule_public_buckets` | `mp.s.2` | CRITICAL | B/M/A |
| `rule_logging_disabled` | `op.exp.8` | HIGH | M/A |
| `rule_log_retention_insufficient` | `op.exp.8` | HIGH | M/A |
| `rule_ntp_not_synced` | `op.exp.8` | MEDIUM | M/A |
| `rule_no_backup` | `op.cont.3` | HIGH | M/A |
| `rule_org1_documental` | `org.1` | MEDIUM | B/M/A |

`detect_public_buckets` incluye `asset.sharepoint_site` + `asset.shared_drive` (Phase 7.1.1).  
`_render_explanation` usa Python `.format()` con `raw_evidence` como kwargs; LLM solo por petición explícita.  
1-row-per-(project_id, ens_measure_code): re-diagnóstico auto-resuelve gaps que dejan de emitir.

`CONNECTOR_PROVIDER_ENS_GUIDANCE`: guidance real solo para `microsoft_365` y `google_workspace` (scopes, medidas detectable, blurb R29). AWS/Azure/GitHub marcados DEFER en comentario.

---

### State machine remediación (CloudGap.approval_status · 9 estados)

```
detected → proposed_to_cliente → approved → executing → executed → verification_pending → verified [TERMINAL]
                               └→ rejected                        └→ failed
```

Por transición: UPDATE CloudGap + INSERT audit log inmutable + SSE dispatch (audience-aware) + `system_consciousness_hooks` (7 subsistemas best-effort: compliance_monitor, M9 dossier, M14 adenda, M22 events, SSE dashboards, NotificationOrchestrator).

---

### Integraciones

- **M16**: `base_connector.py` adapta `DiscoveryResult`→dicts; `service._resolve_m16_credentials()` descifra via `m16_onboarding.token_encryption.decrypt_credentials` (graceful degradation → mock_mode si falla)
- **audit_log**: emite `cliente.cloud_connector.*` con `project_id + client_id` (Sub-atom 5.A 3-way OR)
- **Celery beat**: `cloud_connectors.daily_diagnosis` 04:00 ES + `monthly_digest` día 1 09:00 ES
- **ADR-055 / m_remediation**: `CloudConnector.remediation_enabled` es kill-switch capa 2; ejecución real en `m_remediation/cloud_writers/`

---

### Gotchas

- **MockModeNotAllowedError**: sync sin credenciales + provider no MANUAL_IMPORT requiere `CLOUD_MOCK_MODE_ALLOWED=true`; guard pre-DB evita silenciar gaps reales con dataset vacío.
- **UPSERT resources NO borra ausentes**: delta detection intencionado retainer L; track de recursos desaparecidos es Future-X.
- **`catalog_router` usa `require_owner`** en `/cloud-connectors/providers/catalog` (no público); ruta equivalente cliente en `api_cliente.py` usa `require_client_user`.
- **`list_projects_with_active_connectors`** (Celery) no setea tenant context pre-listado → bypasa RLS; corre como sesión privilegiada.

---

### Veredicto: **Completo** para MVP piloto

Funcionalidad producción-grade para M365 + GWorkspace. AWS, Azure y GitHub tienen enum + catalog entry pero sin gap rules ni guidance ENS propios (Future-3B-2B-7-EXPANDED · post-piloto). 10 reglas cubren los nucleares BÁSICA/MEDIA. La expansión a 73 medidas es Future-X declarado.

---

### Discrepancias vs CLAUDE.md

1. **CLAUDE.md implica 5 providers operativos con gap engine**: `CONNECTOR_PROVIDER_ENS_GUIDANCE` solo tiene M365 y GWorkspace con `measures_detectable` reales; AWS/Azure/GitHub tienen enum + catalog entry pero sin gap rules propias (Future-X real, no parcial).
2. **"50 failures empirical baseline" (Ejecutable 4)**: esta auditoría cuenta 183 funciones test en el directorio; PASS/FAIL runtime no verificado (suite no ejecutada).
3. **E2E integration tests M365+GWorkspace "scaffold mock httpx"**: confirmados en `backend/tests/integration/` (6+5 tests); status PASS/FAIL consolidado no verificado aquí.


## 44 - m_compliance + m_compliance_monitor (Fulkro dogfooding)

### Propósito y dominio

`m_compliance` gestiona derechos RGPD propios de la plataforma FULKRO (Art.15/17/20/30/33/34), RoPA, cookies, DPA y traducción de medidas ENS a lenguaje cliente. `m_compliance_monitor` es el motor de auto-monitorización continua (R7 dogfooding ENS Medio): 21 checks funcionales, Celery beat, alertas, reports semanales y sistema de plugins por norma.

---

### Ficheros clave

**m_compliance**: `rgpd_api.py` (Art.15/17/20 cliente) · `rgpd_services.py` (ZIP+tombstone) · `compliance_admin_api.py` (7 admin) · `breach_service.py` (72h SLA + email AEPD) · `ropa_service.py` (RoPA + Excel openpyxl) · `measure_translation_service.py` (R1 puro: 13 overrides + fallback) · `email_design/` (5 MJML templates)

**m_compliance_monitor**: `checks.py` (21 checks pure async + `CHECK_REGISTRY`) · `service.py` (`ComplianceMonitorService`) · `api.py` (7 admin + `_emit_monitor_audit()` R6) · `norma_reports_api.py` (5 endpoints) · `norma_reports_service.py` (score+persist+MinIO) · `tasks.py` (4 Celery tasks) · `public_api.py` (Trust Center + subscribe) · `normas/` (plugin system: `NormaModule` ABC + `NormaRegistry` + 7 módulos)

---

### Modelo de datos (tablas · sin RLS — platform-global)

| Tabla | Notas |
|---|---|
| `compliance_checks` | 21 rows (una por check); `status`, `last_run_at`, `last_result` jsonb |
| `compliance_alerts` | open/resolved; `auto_resolved` bool |
| `compliance_reports` | informes semanales MD |
| `fulkro_compliance_norma_reports` | score float, md + json content, `reviewed_by_marcos_at` |
| `fulkro_breach_notifications` | `breach_code`, `notification_status`, `affected_client_user_ids` JSONB |
| `fulkro_erasure_requests` | `tenant_client_id` denormalizado (RLS bypass admin), `tombstone_data` JSONB |
| `fulkro_ropa_treatments` | Art.30; `dpa_expires_at`, `last_reviewed_at`, `is_sub_processor` |
| `sub_processor_subscribers` | email + `consent_given_at` |

**Sin RLS**: deliberado — datos propios de Fulkro, no de tenants cliente.

---

### Endpoints expuestos (resumen)

- `require_client_user`: 3 endpoints `/portal/rgpd/{access,erasure,portability}`
- `require_owner`: 7 en `/admin/compliance/*` (erasure+breach) · 7 en `/admin/compliance/monitor/*` · 5 en `/admin/compliance/norma-reports/*`
- Públicos: `GET /legal/compliance/status` (Trust Center) · `POST /legal/sub-processor-notifications/subscribe`

---

### 21 checks funcionales — categoría + cadencia

| Check | Cadencia | ENS/norma clave |
|---|---|---|
**Daily (7 checks)**: `cookies_banner_functional`(HIGH/AEPD) · `rgpd_endpoints_responding`(HIGH/Art.15-20) · `ssl_cert_expiry`(HIGH/ISO+NIS2) · `audit_logs_continuity`(MED/op.exp.8) · `admin_actions_audit_logged`(HIGH/art.24.1) · `intrusion_detection_present`(HIGH/op.mon.1) · `mfa_enforcement`(HIGH/op.acc.5)

**Weekly (6 checks)**: `marketing_analytics_opt_in_only`(HIGH/Art.7) · `dpo_email_working`(HIGH/Art.37.7) · `security_txt_reachable`(MED/NIS2+RFC9116) · `nis2_vulnerability_inbox`(MED/NIS2) · `rls_coverage_percentage`(MED/op.acc.4) · `backups_integrity`(HIGH/op.exp.10)

**Monthly (5 checks)**: `privacy_policy_freshness`(MED) · `breach_workflow_ready`(HIGH/Art.33-34) · `sub_processor_dpa_expirations`(MED/Art.28) · `dpa_template_version`(MED) · `sub_processors_list_freshness`(LOW)

**Quarterly (3 checks)**: `ropa_review_due`(MED/Art.30) · `isms_docs_review_due`(MED/ISO§7.5) · `cookie_consent_renewal_24month`(MED/AEPD2020)

Semáforo: `green/yellow/red/unknown`. Alert tras 3 `unknown` consecutivos. Auto-resolve cuando vuelve `green`.

---

### Plugin normas (Open/Closed)

7 plugins: `ENS_RD_311_2022`, `NIS2_UE_2022_2555`, `ISO_27001_2022`, `RGPD_UE_2016_679`, `LOPDGDD_3_2018`, `LSSI_CE_34_2002`, `AEPD_COOKIES_2020`. Auto-descubrimiento por glob en `normas/__init__.py`. Score ponderado (green=1.0, yellow=0.5, unknown=0.5, red=0.0); suma pesos = 1.0 validada al registro. Umbral email alerta: score < 85 o prioridad `critical`.

---

### Lógica business clave

**Erasure workflow (Art.17)**: `pending → processing → completed | rejected_audit_retention`. Tombstone in-place: email → `anonymised_<uuid>@removed.fulkro.local`, full_name → `Eliminado por solicitud · <date>`, dni/whatsapp = NULL. `audit_log` NUNCA borrado (ENS retención 7 años). Idempotente: rechaza duplicado pending.

**Breach (Art.33/34)**: código `BREACH_YYYY_NNN`. Status `pending → aepd_notified → clients_notified`. Email a `notificaciones@aepd.es` real. Skip de emails tombstoned.

**Audit_log dogfooding R6+R7**: `_emit_monitor_audit()` emite con `project_id=NULL, client_id=NULL` (3-way OR Sub-atom 5.A). Los 4 beats + norma reports también emiten.

**Celery beat**: cada task llama `sync_registry()` antes del batch para mantener `compliance_checks` alineado con `CHECK_REGISTRY`.

---

### Medidas ENS cubiertas (dogfooding directo)

`op.exp.8`, `op.exp.10`, `op.acc.4`, `op.acc.5`, `op.acc.6`, `op.mon.1`, `op.mon.3`, `mp.s.2`

---

### Gotchas y dead code

- `check_audit_logs_continuity` usa columna `timestamp` (no `created_at`) — bug corregido in-code con comentario adversarial.
- `hours_remaining_for_aepd()` en `breach_service.py` — nunca llamado por endpoints. Dead code menor.
- `intrusion_detection_present` acepta `FULKRO_IDS_ENABLED=1` como atestación manual (correcto post-Hetzner).
- `mfa_enforcement` guard implícito: SQLAlchemyError → unknown si tablas WebAuthn/TOTP ausentes.
- Celery `asyncio.run()` por task: funcional, no aprovecha loop async del worker.

---

### Discrepancias docs/CLAUDE.md vs código real

- CLAUDE.md no documenta los 21 checks ni el plugin system de 7 normas — subsistema más rico de lo que sugiere el resumen.
- `Future-1.E.compliance-reports-pdf-export` — CONFIRMADO no existe: solo MD + JSON + Excel RoPA.
- `Future-1.E.compliance-checks-dedicated-page` — CONFIRMADO: no existe página frontend específica.
- UI top-level `/admin/compliance/*` cross-cliente R23 sostenido — CORRECTO.

---

### Veredicto

**COMPLETO**. m_compliance cubre ciclo RGPD completo propio + RoPA + cookies + breach + measure translation. m_compliance_monitor tiene 21 checks funcionales (no stubs), 7 plugins norma con scoring ponderado, Celery beat wired, Trust Center público. Dogfooding R7 genuino con audit_log propio. Dead code menor aislado. Sin RLS (correcto — datos plataforma, no tenant).


## 45 - m_legal + m_meetings + m_workflow_engine

---

### 1. m_legal — Catálogo Legal Cross-Compliance

**Propósito**: catálogo READ-ONLY global de 250 obligaciones legales (RGPD, LOPDGDD, NIS2, DORA, AI_Act) con reverse-lookup a medidas ENS Anexo II.

**Ficheros**: `orm.py` (tabla `legal_obligations_catalog` · sin RLS · `fulkro_app` GRANT SELECT only · JSONB: `sector_aplica`, `ens_categoria_aplica`, `vinculo_medida_ens`) · `service.py` (5 funciones by_codigo/regulation/ens_measure/sector/ens_category · JSONB containment `@> CAST(:x AS jsonb)`) · `api.py` (2 GET · `require_marcos_or_client`) · `schemas.py`.

**Endpoints**: `GET /api/v1/legal-obligations/catalog?{1 filtro exacto}` + `GET …/{codigo}`. **Tests**: 238 LOC. **Veredicto**: completo — catálogo global narrow. Sin audit_log/SSE/LLM.

---

### 2. m_meetings — Reuniones Externas + Actas

**Propósito**: gestión reuniones externas (Meet/Zoom/Teams), actas formales 4 subtipos signable, 4 acciones post-meeting cross-motor. Sin engine de video propio (ADR-024).

**Ficheros**: `service.py` (MeetingService CRUD+workflow+FTS+SSE-init) · `api.py` (11 endpoints admin) · `actas_service.py` (ActasService draft→curated→sent_to_client+signoff) · `actas_portal_api.py` (5 endpoints portal cliente) · `actions.py` (4 handlers post-meeting) · `schemas.py`

**Modelos**: `ExploratoryMeetingRow` (en `models/conformity_lifecycle.py`) + `CommitteeMeeting` (en `models/governance.py`) — ambos shared, sin ORM propio. RLS vía `SET LOCAL ROLE fulkro_app_bypassrls`.

**Endpoints admin** (11, `require_owner`): `POST/GET /api/v1/admin/meetings`, `GET …/search` (FTS GIN español), `GET …/by-client/{id}`, `GET/PATCH/DELETE …/{id}`, `POST …/{id}/complete|cancel|sse-init|post-action`.

**Endpoints portal cliente** (5, `get_current_client_user`): list + detail + review + document-hash + finalize-signoff actas.

**State machines**: reuniones `scheduled→completed/cancelled` (idempotente). Actas `draft→curated_by_admin→sent_to_client` → cliente review (revisada_ok/con_pregunta/suggest_change) → `fully_signed`.

**`evaluate_comite_cadence`**: función pura periodicidad CCN-STIC 801: BÁSICA 6m, MEDIA/ALTA 3m. Alerta pre-auditoría si sin actas firmadas o fuera de cadencia.

**Integraciones**: M05 Signing (multi-sig actas), M12 Magic Link (k6_signature→FIRMA_DOCUMENTO), M18 EmailSender, M30 auto-log interaction, A19 propuestas, A18 SSE stream.

**Gotchas**: `cancel_meeting` trunca reason a 40 chars en `lead_source` (repurposeado). `assert meeting is not None` en `get_acta_hash` (debería ser raise). Sin `audit_log` hash-chain para reuniones/actas.

**ENS**: `org.com.3` (comités seguridad · cadencia CCN-STIC 801), `mp.s.3` (acuerdos · actas firmadas). **Veredicto**: completo — producción-grade. Gap: sin audit_log. Tests `tests/motors/m_meetings/` no encontrado.

---

### 3. m_workflow_engine — Orquestador Workflow

**Propósito**: view composer cross-data (ADR-025, sin tablas propias) que cruza YAML template catalog + 19 dims proyecto + `client_tasks` → vista enriched con urgencia, dependencias cross-actor, progress per-phase.

**Ficheros**: `engine.py` (compute_steps/progress/current_step) · `service.py` (advance_step admin override) · `dependency_resolver_service.py` (state machine + SSE propagation) · `deliverables_service.py` (E-XXX → Evidence Vault) · `api.py` (2 routers, 12 endpoints)

**Sin tablas propias** — consume `client_tasks`, `evidence`, `projects` (ADR-025 sostenido).

**Endpoints** (12 total): admin `GET /api/v1/admin/workflow-command-center`, `GET …/projects/{id}`, `POST …/steps/{tmpl}/advance`, `POST …/steps/{tmpl}/remind`. Shared reader: `GET /api/v1/projects/{id}/workflow-engine/{catalog|current-step|progress|timeline}`, `GET …/workflow-guide`, `GET …/steps/{tmpl}/deliverables`, `GET …/deliverables/bulk-zip`, `GET …/deliverables/{ev_id}/download`.

**Algoritmo** `compute_steps_for_project`: (1) carga 19 dims, (2) filtra templates por dims, (3) carga `client_tasks` en map, (4) por template: archetype variant + dependency resolver, (5) `urgency_score = priority*5 + urgencia_boost(0-40) + horas_factor`. Retorna `list[EnrichedStepState]`.

**State machine cross-actor**: `blocked→available→in_progress→done`. Dual alias backward-compat: `{"done","completed"}` = terminal. `blocker_reason` friendly por actor: "Esperando Marcos termine: X" / "Esperando cliente complete: X".

**SSE** (best-effort post-commit): `step_completed` + `step_unblocked` + `step_blocked` → canal `project:{id}`. **Deliverables**: match E-XXX `evidence_type_id OR measure_code`. Status `available/needs_regen/missing`. Bulk ZIP streaming on-the-fly. **Command Center**: 4 buckets urgencia (≥75/50-74/25-49/<25) sobre proyectos activos (6 lifecycle_states).

**Tests**: `test_workflow_state.py` (689 LOC) + `test_workflow_blocking.py` (189 LOC) + `test_workflow_gates*.py` + `test_workflow_phase_10.py`.

**Gotchas**:
- **N+1 en Command Center**: `compute_current_step` + `compute_progress` por proyecto sin batch loader. OK piloto <10 proyectos; Future-1.E.workflow-scanner-cache-redis pendiente.
- `advance_step` hace `db.commit()` dentro del service — patrón divergente pero correcto.
- **Bug real**: `download_deliverable` devuelve `FileResponse(path=filesystem)` — en producción Hetzner con MinIO `fichero_path = minio://...` no existe en filesystem local → 404.
- `remind` devuelve 200 OK si `workflow_step_notifications` unavailable (ImportError swallowed silently).

**ENS**: catálogo completo 52/68/73 medidas B/M/A via deliverable E-codes YAML. `org.1`, `op.pl.1-4`, `op.exp.*`, `mp.sw.*` wired. **Veredicto**: completo — motor central. ADR-025 DRY sostenido. Bug FileResponse MinIO a corregir antes de Hetzner.

---

### Discrepancias vs CLAUDE.md

- **m_legal "dormant · activación T2"** → FALSO: router montado en `main.py:465`, 2 endpoints GET funcionales, 250 entries seed. Está ACTIVO.
- **ADR-046 auto-detect NIS2 en m_legal** → FALSO: la detección automática vive en `m21_diagnosis/cross_compliance_service.py` (tabla `legal_obligations` per-proyecto). m_legal es catálogo global read-only. Nombres similares, entidades distintas.
- **m_meetings tests en `tests/motors/m_meetings/`** → directorio no encontrado en glob. Cobertura real desconocida.


## 46 - m_observability (LLM cost) + m_siem

Alcance: TODOS los `.py` (13 obs + 2 siem), `main.py` wiring, `LLMInteractionLog`, 2 migraciones. `eval_runner.py` y evaluator leídos parcial (núcleo verificado).

### Propósito
- **m_observability**: 2 subsistemas — (a) observabilidad coste LLM sobre `llm_interaction_log`; (b) AI Act art.50 transparency + golden-dataset eval/regression runner. Admin-only salvo 1 endpoint cliente.
- **m_siem**: correlación SIEM ON-QUERY (ADR-025, sin tablas nuevas) sobre 4 fuentes. Read-only (ADR-014), determinista (R1).

### Ficheros clave
- `llm_observability_service.py` · agregaciones coste/tokens/cache/anomalías (raw SQL).
- `api.py` (obs) · 6 endpoints admin. `models.py` · `AIActTransparencyEvent` (RLS) + `GoldenEvalRun` (NO RLS).
- `transparency_service.py`+`_api.py` · log AI Act art.50 (admin+cliente, helper escritura service-to-service).
- `golden_datasets_loader.py` · carga/valida JSON Pydantic frozen + singleton cache.
- `eval_runner.py` · runner agent-agnóstico + CLI + registry + report MD/JSON. `golden_eval_runs_service.py`+`_api.py` · trigger/history (4 endpoints). `tasks.py` · Celery opcional.
- m_siem: `service.py` (agregación+correlación+counts) + `api.py` (2 endpoints).

### Modelo de datos
| Tabla | RLS | Columnas RLS | Notas |
|---|---|---|---|
| `llm_interaction_log` (en knowledge.py) | NO | `tenant_id`,`project_id` nullable (sólo index) | PK BigInt; `cached_input_tokens`, `cost_usd`, `latency_ms`, `feature`, `status` |
| `ai_act_transparency_events` | SÍ | `project_id` (FK CASCADE, NOT NULL), `client_id` (FK SET NULL, nullable) | retention 6 años; policy `FOR ALL` por `app.current_project_id` |
| `golden_eval_runs` | NO (platform-global) | — | metadata de runs, no decisiones IA |

### Endpoints REALES (todos `prefix=/api/v1`)
- `GET /admin/llm-observability/{cost-summary,interactions,top-consumers,anomalies}` + `/projects/{id}/token-usage` + `/agents/{name}/cache-stats` · `require_owner`.
- `GET /admin/projects/{id}/transparency/log` (owner) · `GET /client-portal/transparency/log` (`require_client_user`, cross-project por `client_id`).
- `GET /admin/observability/golden-eval/{datasets,runs,runs/{id}}` + `POST /run` · owner.
- `GET /admin/siem/{overview,events}` · owner + `SET LOCAL ROLE fulkro_app_bypassrls`.

### Lógica / algoritmos
- Coste: `SUM(prompt/completion/total/cached/cost) + AVG(latency)`; `cache_hit_rate = cached/(prompt+cached)`.
- Anomalías deterministas: `cost>=10$ OR latency>=60s OR status!=success` (umbrales por query).
- SIEM normaliza severidad ES/EN (`_SEVERITY_ALIASES`), agrega 4 fuentes (`verification_findings` M8, `incidents` M19, `escalation_events` M18, `compliance_alerts`), ordena por severidad+recencia. Counts exactos vía `COUNT GROUP BY` (no truncados) + `CORRELATION_SCAN_CAP=2000` para no perder críticos.
- 3 reglas correlación: `multiple_critical_pentest_findings` (≥3), `incident_plus_critical_vuln` (mismo proyecto), `incident_not_notified_lucia` (Art.33 24/72h).
- Eval runner: skeleton (dataset vacío → `pass_rate=1.0` vacuously true); severidad ok/warn/alert por thresholds; exit codes 0/1/2; LLM saltado sin `ANTHROPIC_API_KEY`.

### Medidas ENS / normativa
- m_siem → `op.mon.1` (detección intrusión) + `op.mon.2` (métricas, ALTA). Correlaciones citan `mp.s.2`, `op.exp.*`, CCN-STIC 817, Art.33 (CCN-CERT/LUCIA 24/72h).
- AI Act art.50 (transparency) + retención 6 años (RGPD art.83.5).

### Integraciones
- `llm_interaction_log` = fuente única coste (escrito por `core/ai/llm_router.py`, no por este motor).
- `transparency_service.log_transparency_event()` = helper service-to-service (commit explícito); NO endpoint escritura. SIEM lee 4 motores, no escribe. audit_log/SSE/magic-links NO usados aquí.

### Veredicto: MIXTO
- **Production-grade** (wired en `main.py`): coste LLM, anomalías, transparency, correlación SIEM.
- **Skeleton honesto**: golden-eval runner — evaluators deterministas, LLM real DIFERIDO; datasets dependen de input Marcos; entries se *saltan* sin capability. `tasks.py` Celery sólo si `_CELERY_AVAILABLE`.

### Gotchas
- **RLS (potencial fuga cliente)**: `client_transparency_log` filtra por `client_id` en SQL, pero la policy RLS sólo aísla por `project_id` (`app.current_project_id`). El aislamiento cliente depende del filtro app-level `WHERE client_id=`; RLS no cubre esta query cross-project — barrera única = código.
- `SET LOCAL ROLE fulkro_app_bypassrls` (SIEM) requiere transacción viva.

### Discrepancias docs vs código
- README: "SMALLEST motor · 355 LOC · 3 files" FALSO → hoy ~13 ficheros, ~73KB (incluye transparency + golden-eval).
- README "NO existe service.py": cierto para obs; m_siem SÍ tiene `service.py`.
- README "NO RLS platform-global": cierto para `llm_interaction_log`/`golden_eval_runs`, pero `ai_act_transparency_events` SÍ tiene RLS — README omite todo el subsistema transparency.
- CLAUDE.md "m_observability utility transversal NO UI": coherente, pero m_siem (FRENTE N) tiene consola admin propia y existe endpoint cliente de transparency.


## 47 - m_remediation (ADR-055) + agente on-prem

**Parcela**: `backend/app/motors/m_remediation/` (12 ficheros + 4 cloud-writers) + migrations + tests. Auditado: 2026-06-13.

### Propósito
Motor de auto-remediación segura de gaps cloud/host. ADR-055: escritura opt-in (default OFF · fail-closed), kill-switch 3 capas, ciclo preflight→snapshot→apply→verify→rollback, canal agente on-prem firmado Ed25519. R1 inviolable: sin LLM, todo determinista desde catálogo.

### Ficheros clave

| Fichero | Rol |
|---|---|
| `catalog.py` | 15 acciones inmutables: tier, provider, ens_measures, blast_radius_max, cliente_blurb |
| `policy.py` | Kill-switch 3 capas + `resolve_execution_mode` determinista |
| `models.py` | ORM `RemediationJob` + `RemediationSnapshot` (Fase 1 cloud) |
| `agent_models.py` | ORM `RemediationAgent` + `RemediationAgentCommand` (Fase 3 on-prem) |
| `service.py` | `RemediationService`: ciclo completo + audit R6 |
| `agent_service.py` | `RemediationAgentService`: enrollment, poll, report, revoke |
| `agent_protocol.py` | Ed25519 puro: sign/verify/validate_command + `PLAYBOOK_ALLOWLIST` |
| `writers.py` | Interfaz `RemediationWriter` (Protocol) + registro opt-in `_WRITER_REGISTRY` |
| `cloud_writers/__init__.py` | Fábrica `build_writer_for_connector` (descifra creds M16 · DRY OPS-026) |
| `cloud_writers/aws.py` | boto3: 6 acciones S3+IAM+CloudTrail (AssumeRole) |
| `cloud_writers/microsoft365.py` | Graph httpx: MFA report-only, MFA enforce, legacy auth |
| `cloud_writers/azure.py` | ARM httpx: public blob disable, HTTPS-only storage |
| `cloud_writers/google_workspace.py` | Drive API: restrict external sharing unidad compartida |

### Modelo de datos / tablas y RLS

**`remediation_engine_001`** (revisa `ola_d_trusted_timestamps_004`):
- `remediation_jobs`: `project_id` FK · `client_id` nullable · `source_gap_id` FK `cloud_gaps` · `action_type/tier/status/dry_run` · `authorized_by_user_id/at` · `result` JSONB. RLS `project_isolation`.
- `remediation_snapshots`: `project_id + job_id` · `state_before` JSONB NOT NULL · RLS ídem.
- `cloud_connectors` ALTER ADD: `remediation_enabled DEFAULT false` · `auto_remediation_policy DEFAULT 'off'` · `granted_write_scopes` JSONB.

**`remediation_agent_001`** (revisa `remediation_engine_001`):
- `remediation_agents`: `project_id` · `enrollment_token_hash` SHA-256 · `agent_pubkey_hex/token_hash` 64-char · `capabilities` JSONB · `status` CHECK('pending','active','revoked'). RLS `project_isolation`. 2 SECURITY DEFINER cross-RLS: `fn_resolve_remediation_agent/enrollment`.
- `remediation_agent_commands`: `server_signature/report_signature` TEXT Ed25519 · `status` ('pending','delivered','reported').

RLS: 4 tablas filtran solo por `project_id`. `client_id` solo propagado en `emit_audit_log` (Sub-atom 5.A), no en políticas RLS.

### Endpoints (verificados en main.py · prefix `/api/v1`)

**Admin (require_owner · project-scoped)**: catalog · jobs CRUD · jobs/{jid}/authorize · jobs/{jid}/execute · connectors (list + PATCH activation + POST grant-write) · agents (issue enrollment + list + revoke + enqueue-command). Total 13 endpoints.

**Cliente (require_client_user · ADR-013)**: `GET /client-portal/remediation/jobs` (R29 friendly: `_job_to_cliente_dict` + `_CLIENTE_STATUS_LABEL`) · `POST /jobs/{jid}/authorize`. Total 2 endpoints.

**Agente (Bearer token · SIN require_owner)**: `POST /agent/remediation/enroll` · `GET /commands` · `POST /commands/{cid}/report`. Total 3 endpoints.

### Kill-switch y ciclo de ejecución

**3 capas (basta UNA off)**:
1. `FULKRO_REMEDIATION_ENABLED` env (default `false`)
2. `cloud_connectors.remediation_enabled` (default `false`)
3. `auto_remediation_policy` ∈ {`off`|`safe_auto_only`|`full`}

`BLOCKED` prevalece SIEMPRE. Kill-switch **revalidado en ejecución** (defensa en profundidad).

**Tiers (15 acciones catálogo)**:
- `SAFE_AUTO` (9): S3 cifrado/bloqueo-público/versionado, CloudTrail, IAM password, MFA report-only M365, Azure blob/HTTPS, SSH host, firewall host.
- `GUARDED` (4): MFA enforce M365, rotate-key AWS, legacy-auth M365, Drive restrict Google, package-update host.
- `BLOCKED` (2): delete-public-resource, remove-IAM-principal.

**Ciclo service.py**: PREFLIGHT (read_state idempotente) → SNAPSHOTTING → [dry_run→SUCCEEDED] → APPLYING → VERIFYING → rollback automático si verify falla → ROLLED_BACK/FAILED. Blast-radius guard: `affected_count > blast_radius_max` → FAILED.

### Seguridad agente on-prem

- Enrollment un solo uso (hash SHA-256 borrado tras canjear; TTL 5-1440 min). Token de operación separado.
- Comandos Ed25519 firmados por servidor. Agente valida: (1) `playbook_id ∈ PLAYBOOK_ALLOWLIST`, (2) firma válida. NUNCA shell arbitrario. Allowlist: `{harden_sshd_root_login, enable_host_firewall_rule, apply_package_security_update}`.
- Reports firmados Ed25519 por el agente; servidor verifica con pubkey fijada en enrollment.
- Kill-switch: `revoke_agent()` → `agent_token_hash=NULL`.

### Medidas ENS cubiertas (Anexo II RD 311/2022)

`op.acc.4/5/6` · `op.exp.4/5/8` · `op.mon.1` · `op.cont.2` · `mp.com.1/2/3` · `mp.info.3/6` · `mp.s.2/8`

### Integraciones

- **R6 audit**: `emit_audit_log` en cada transición (Sub-atom 5.A 3-way OR). 11 eventos job + 6 agent + 2 connector.
- **M16**: fábrica importa `decrypt_credentials` de `m16_onboarding.token_encryption` (DRY · OPS-026).
- **m_cloud_connectors**: `source_gap_id` FK a `cloud_gaps`. Sistema legacy (524+785 LOC · 49 tests) coexiste sin unificación.
- **Frontend**: `app/(admin)/admin/projects/[id]/remediation/page.tsx` + `app/(client-portal)/client-portal/remediaciones/page.tsx`. APIs TS en `lib/api/`. E2E: 3 specs `fase_38/client/`.

### Tests

- `test_remediation_service.py` **13 tests** · `test_remediation_api.py` **7 tests**. Total m_remediation: **20 tests directos**.

### Gotchas / discrepancias

1. **`fulkro_remediation_agent.py` y `playbooks.py` NO EXISTEN** en el repo. CLAUDE.md los menciona como `agent/(fulkro_remediation_agent.py, playbooks.py)`. El protocolo está en `agent_protocol.py` (server-side) pero no hay binario ejecutable de agente. El agente on-prem es solo un control-plane; el cliente tendría que implementar el pull/execute por su cuenta.
2. **`FULKRO_REMEDIATION_SIGNING_KEY` efímera en prod**: sin esta env el servidor genera clave Ed25519 en memoria. Cualquier restart invalida los agentes enrolados. El código avisa con `logger.warning` pero NO falla. Riesgo operativo real en Hetzner.
3. **`google_workspace.py`** importa `google.oauth2` + `google.auth` que pueden no estar instalados en el venv principal (dependen del connector M16).
4. **CLAUDE.md afirma "ENABLED=true desplegado a prod 2026-06-13"**: el default en `policy.py` es `false`. La env debe estar explícita en `docker-compose` prod. No verificable desde este repo.
5. **RLS `client_id` parcial**: la política `project_isolation` filtra solo por `project_id`. `client_id` en jobs/agents no participa en la RLS (solo en audit_log). Coherente con el resto del sistema pero distinto de Sub-atom 5.A completo.

### Veredicto: **COMPLETO** (con deuda operativa)

Motor ADR-055 completo end-to-end: catálogo, kill-switch, ciclo, 4 writers cloud reales, protocolo criptográfico agente, 4 tablas RLS, 22 endpoints, 20 tests. Deuda: (a) binario de agente on-prem no existe en repo; (b) `FULKRO_REMEDIATION_SIGNING_KEY` debe configurarse en prod para estabilidad agentes; (c) coexistencia legacy+nuevo no unificada.


## 70 - IA - Agentes de negocio (registry 31 agentes)

**Parcela**: `backend/app/agents/` (registry, base, validators, api, dry_run, A2/A4/A6/A11/A12/A14/A17/A18/A19/A20/A21/A27/A31). Verificado leyendo código fuente real (no docs).

### Veredicto honesto: **MIXTO** (núcleo completo + 1 bug latente + sobre-claims menores)

- 14 agentes `activo` con clase Python real e invocable + 1 `scaffolding_covered_by_engine` (A2). El resto de los 31 IDs son `deprecated` (12), `externalized_to_motor` (3: A15/A26/A28... realmente A15+A26 + ext refs) o `reservado` (2: A9/A10 Pentest demolido). **"31 agentes" = espacio de IDs histórico, NO 31 agentes vivos.**

### Taxonomía real (registry.py · IDs vivos)

| ID | Nombre | Status | Modelo | Temp | Motor | Función |
|----|--------|--------|--------|------|-------|---------|
| 2 | Analizador Pliegos | scaffolding_covered | sonnet-4.5 | 0.1 | — | Extrae requisitos ENS de pliegos PLACSP (stub funcional) |
| 4 | Redactor E-090 | activo | sonnet-4.6 | 0.2 | m22 | Narrativa E-090 secs 1/2/6 (NO toca 3.1/3.2/4/5 deterministas) |
| 6 | Analista Contratos | activo | sonnet-4.6 | 0.1 | m14 | Gaps ENS+RGPD + adenda jurídica |
| 11 | Auditor Virtual | activo | **opus-4.7** | 0.1 | m10 | PAC priorizado + preguntas sector + narrativa dry-run |
| 12 | Coach Cliente | activo | sonnet-4.6 | 0.2 | m09 | Scorea respuestas cliente L0-L5 + 3 dims (NO genera preguntas) |
| 14 | Copiloto RAG | activo | sonnet-4.5 | 0.2 | m11 | Chat RAG ENS (subpaquete `agent_14_copiloto/`) |
| 17 | Cualificador | activo | sonnet-4.6 | 0.1 | m13 | Lead 6 dims + A/B/C/DESCARTAR + red_flags |
| 18 | Reunión Exploratoria | activo | sonnet-4.6 | 0.1 | m13 | Panel IA live JSON strict K.4 (+stream SSE) |
| 19 | Propuestas P-001 | activo | **opus-4.7** | 0.15 | m13 | Propuesta senior (16k tokens) + validador anti-alucinación |
| 20 | Negociador C-001 | activo | sonnet-4.6 | 0.15 | m14 | Cláusulas dinámicas (usa validators.py compartido) |
| 21 | Detector Discrepancias | **deterministic** | — | 0.0 | m04 | `DiscrepancyDetectorService` SQL (5 detectores) + wrapper LLM legacy |
| 27 | Clasificador IDMS | activo | **haiku-4.5** | 0.1 | m24 | Clasifica docs → folder 00-13/99 + tags |
| 31 | Enriquecedor DdA | activo | sonnet-4.6 | 0.2 | m03 | Narrativa justificación `no_aplica` 60-200 palabras |

Externalizados (410 Gone /invoke): **A15** (RSS vigilancia → `m23_retainer.agent_15_vigilancia`), **A26** (retainers → `m23_retainer.agent_26`). Deprecados: A1/A3/A5/A7/A8/A13/A16/A22-A25/A28-A30 (cubiertos por M02/M04/M05/M09/M21/M22/M27/M28/M23 deterministas).

### Cumplimiento reglas inviolables (verificado en código)

- **R3 (temp ≤ 0.2)**: ✅ todas. Máx 0.2 (A4/A12/A31); comerciales 0.15 (A19/A20). `COMMON_HEADER` declara "objetivo 0.1-0.2".
- **R2 (citas)**: ✅ `COMMON_HEADER` exige `[RD 311/2022 Art.X]`/`[CCN-STIC NNN]`/`[Anexo II medida]`. `AgentBase._extract_citations` extrae `[...]` por keywords. Es post-extracción, **sin enforcement que rechace respuesta sin citas**.
- **R1 (deterministas > LLM)**: ✅ `COMMON_HEADER` regla 3 ("JAMÁS decidas DdA/categorización/riesgo"). A21 canónico: SQL determinista + wrapper LLM solo "reasoning narrativo opcional".

### `AgentBase` (base.py)

- `invoke`: monta contexto proyecto+extra+JSON → `_call_llm` → parse JSON opcional + citations + log.
- `_call_llm`: sin `anthropic_api_key` → `_mock_response` `[MOCK]` (CI/tests); real vía `llm_router.complete` en executor con caching. Fallback `[MOCK-FALLBACK]` ante cualquier excepción (graceful, **enmascara fallos** en prod).
- `_resolve_model`: `opus-4.7`→`claude-opus-4-7`. **Sin alias para opus-4.8** (entorno corre 4.8; agentes en 4.7).
- `_log_interaction`: `LLMInteractionLog` best-effort en SAVEPOINT (`begin_nested`). **NO escribe audit_log hash-chain** (R6) ni SSE desde base; lo hacen consumidores.
- `ENABLE_PROMPT_CACHING` opt-in por clase (TRUE salvo A2).

### Endpoints REST reales

- `agents/api.py` (`/api/v1/agents`): `GET /`, `GET /{id}`, `POST /{id}/invoke` (genérico, 410 deprecated / 404 reservado-unknown) + shortcuts: `POST /2/analyze-pliego`, `/4/generate-e090-narrative`, `/11/run-supplementary-audit`, `/6/analyze-contract`, `/17/qualify-lead`, `/18/meeting-update`, `/18/meeting-update/stream` (SSE), `/12/evaluate-response`, `/12/evaluate-batch`, `/31/enrich-measure`, `/31/enrich-batch`, `/27/classify-document`, `/27/classify-batch`.
- `dry_run_api.py` (A11+M10): `POST/GET /projects/{id}/audit-dry-run/{execute,summary,results/{rid}}` — protegido `require_owner`.
- `agent_11_wrapper.py`: `POST /api/v1/projects/{id}/agents/11/run-supplementary-audit` (auto-compone body desde último M10 run; RLS vía `get_project_owner`).
- `agent_21_api.py`: scan_project + list + get + PATCH (resolución discrepancias).

### Modelo de datos / RLS

- `audit_dry_run_results` (models/dry_run.py): `FullMixin` + `project_id` FK (CASCADE) + `m10_run_id` FK + payloads JSONB `m10_payload`/`a11_payload`. **Solo `project_id`, NO `client_id`** (RLS derivada de project). Histórico M10+A11.
- A21: `a21_discrepancies` + `a21_scan_runs` (modelos en `models/a21_discrepancies.py`, fuera de parcela). `project_id` scoped.
- Agentes LLM puros **no tienen tablas propias**; su único rastro es `LLMInteractionLog` (project_id, feature `agent_NN_slug`, tokens, prompt_hash sha256, latency).

### Validador anti-alucinación (`validators.py`)

- `parse_spanish_amount` (ES "14.200,00"→Decimal) + `detect_unknowns_in_text`: clasifica tokens como cita compuesta / importe EUR vs `known_amounts` / whitelist bare (RD/CCN-STIC/ISO/años/%) / alucinación. Regex con boundaries (no parte CIFs/UUIDs).
- **A19 NO usa validators.py**: copia local `_WHITELIST_BARE` + `_detect_unknown_numbers_v2` (es el origen). Retry hasta 1, luego `_deterministic_fallback`. **Solo A20 importa el módulo compartido.**

### A11 dry-run (orquestador completo)

`AuditDryRunService`: M10 `run_simulation` (58 preguntas ENAC deterministas L0-L5) → A11 `generate_supplementary_audit` (Opus, PAC + 3-5 preguntas sector + narrativa) → persist `audit_dry_run_results` → `AlertService` si critical_gaps>0. **1 LLM call (no 58)** por coste. Schema strict + fallback determinista (PAC tabular) si falla validación.

### Medidas ENS cubiertas

Agentes **referencian transversalmente** todo el Anexo II vía corpus, no implementan medidas. A21 detecta NCs sobre `mp.*`/`op.*`/`org.*` (5 detectores). A4→E-090; A11→PAC sobre NCs M10. Whitelist validador: CCN-STIC 800-885, ISO 27001/27701/22301, RGPD 2016/679, NIS2 2022/2555, DORA 2022/2554.

### Discrepancias docs/CLAUDE.md vs código

1. **BUG LATENTE — `_AGENT_CLASSES` con nombres de clase erróneos**: el genérico `POST /{id}/invoke` mapea a `RedactorPoliticasAgent`(A4), `AnalistaContratosAgent`(A6), `AuditorInternoVirtualAgent`(A11), `CualificadorComercialAgent`(A17), `RedactorPropuestasAgent`(A19), `AsistenteNegociacionAgent`(A20), `ClasificadorIDMSAgent`(A27)... pero las clases reales son `Agent04RedactorDiagnosticos`, `Agent06AnalistaContratos`, `Agent11AuditorVirtual`, `Agent12CoachClienteEvaluador`, `Agent17CualificadorComercial`, `Agent18ReunionExploratoria`, `Agent19Proposals`, `Agent20NegociadorContractual`, `Agent27ClasificadorIDMS`. `getattr(mod, class)`→None→**404 "no implementado"**. Solo A2/A21/A14/A31 coinciden. Shortcuts específicos importan la clase correcta directamente → la genérica /invoke está rota para ~9 agentes pero **no es la usada en prod** (flujos reales usan shortcuts).
2. **validators.py docstring sobre-afirma**: dice "Reutilizado por A20/A4/A14/A11" — empíricamente **solo A20** lo importa. A19 tiene copia local (duplicación DRY).
3. **"31 agentes registry"** (CLAUDE.md): real = 14 activos + 1 scaffolding; resto IDs históricos. `AgentBase` docstring dice "27 agentes" (obsoleto).
4. **Opus**: código `opus-4.7`; entorno corre Opus 4.8, sin alias 4.8 en `_MODEL_ALIAS_MAP` (agentes anclados a 4.7).
5. **Fallback MOCK silencioso**: `_call_llm` degrada a `[MOCK-FALLBACK]` ante cualquier error sin alertar (gotcha: placeholder en prod si key/red falla).


## 71 - IA - Suite Copiloto (3 superficies, memoria, personas)

**Auditoría**: 2026-06-13 · código fuente leído directamente · sin proxy CLAUDE.md

---

### Propósito y dominio

A14 es el copiloto conversacional ENS. Implementa **3 superficies** sobre un pipeline RAG común (`agent_14_copiloto/service.py`):

| Superficie | Role | Modelo real | Endpoint |
|---|---|---|---|
| Admin RAG | `admin` | `claude-sonnet-4-5-20250929` T=0.1 | `POST /api/v1/copilot/chat` + `/chat/stream` |
| Admin Persona | `admin` | Sonnet 4.6 (YAML alias) | `POST /api/v1/admin/copilot/chat` |
| Cliente RAG | `cliente` | misma instancia A14 | `POST /api/v1/client-portal/copiloto/chat` + `/chat/stream` |
| Cliente Persona | `cliente` | Haiku 4.5 (YAML alias) | motor `copilot_cliente_service` |

Pipeline A14: detect_filters → hybrid_search(top_k=5) → build_system_prompt(role) → LLM → citation_validator → LLMInteractionLog → response.

---

### Ficheros clave (1 línea c/u)

| Fichero | Función |
|---|---|
| `agent_14_copiloto/service.py` | Pipeline `answer_question` + `stream_answer_question` (718 LOC) |
| `agent_14_copiloto/prompts.py` | `build_base_system_prompt(role)` role-aware · FULKRO identity wired |
| `agent_14_copiloto/types.py` | `CopilotQuery`, `CopilotResponse`, `PageContext` dataclasses |
| `agent_14_copiloto/filters.py` | `detect_filters` regex ENS codes / CCN-STIC / RD311 / frameworks |
| `agent_14_copiloto/citation_validator.py` | `extract_citations`, `assess_grounding`, `is_not_in_corpus` |
| `copilot_memory.py` | N6 memoria: `load_conversation_history` + `persist_exchange` sesión separada |
| `copilot_admin_service.py` | `CopilotAdminLLMService` R30 boundary check + defensive enrich |
| `copilot_cliente_service.py` | `CopilotClienteLLMService` R29 boundary check + fallback stub total |
| `copilot_persona_service.py` | Context builders por rol (DB → system prompt render) |
| `copilot_personas_loader.py` | Loader YAML `copilot_personas_v1.yaml` + `lookup_screen_reference` |
| `copilot_project_state.py` | `build_project_state_block` estado EN VIVO (compute_workflow_state) |
| `copilot_rate_limit.py` | Caps LLM por tier (ADR-025, NO new table) |
| `copilot_stub_service.py` | Canned responses por `action_id` cuando LLM deshabilitado |
| `system_knowledge.py` | `SYSTEM_KNOWLEDGE_CLIENTE/ADMIN` + import auto-generado |
| `system_knowledge_generated.py` | AUTO-GENERADO: 20 rutas cliente · 45 proyecto admin · 12 agentes |

---

### Modelo de datos / tablas

| Tabla | RLS | Uso |
|---|---|---|
| `copilot_conversations` | `project_id`, `client_id` | Conversaciones persistentes |
| `copilot_messages` | `conversation_id` FK | Historial turnos |
| `llm_interaction_log` | `project_id`, `feature` | Logging + base rate-limit (ADR-025) |
| `audit_log` | `project_id`, `client_id` 3-way OR | `cliente.copilot.asked/answered` |

RLS `copilot_isolation` 3-way OR. Memoria admin: `project_id` only; cliente: `client_id + project_id`. `copilot_memory.py` usa sesión separada — fallo degrada a stateless sin corromper transacción principal. `knowledge_chunks` sin `client_id` — contenido regulatorio público.

---

### Endpoints

**Admin** (`require_owner`): `POST /copilot/chat` · `POST /copilot/chat/stream` · `POST /admin/copilot/chat` (5 action_ids) · `GET /copilot/quick-actions` · CRUD `/copilot/conversations/*`

**Cliente** (`get_current_client_user`): `POST /client-portal/copiloto/chat` · `POST /client-portal/copiloto/chat/stream` · `POST /client-portal/copilot/chat` (5 action_ids)

---

### Lógica de negocio

**Pipeline RAG** (stream y non-stream):
1. **PI-guard** pre-LLM: `sanitize_user_input` bloquea jailbreak
2. `detect_filters`: regex ENS codes / RD311 / CCN-STIC / NIST/RGPD/MAGERIT/DORA/NIS2
3. `hybrid_search(top_k=5)` fastembed e5-large 1024 dim · source/measure filters
4. **corpus_gap** `confidence < 0.45` → appends fallback prompt (prohibición alucinar + URLs CCN-CERT/BOE/AEPD)
5. `_enrich_user_message_with_m30`: M30 contacts injection (client_id desde page_context > project_id)
6. `_build_system_prompt(role, page_context, corpus_gap)`:
   - `build_base_system_prompt(role)` → `SYSTEM_KNOWLEDGE_ADMIN/CLIENTE` + intro + reglas RAG + citas + completitud 3 categorías + Art.11 autónomo
   - Screen actions: `screen_references_catalog` YAML → botones concretos pantalla activa
   - `project_state`: compute_workflow_state serializado role-filtered (admin: DdA/pentest/simulacro; cliente: solo acciones friendly)
   - `_CATEGORY_GUIDANCE[BASICA|MEDIA|ALTA]` + coach mode (Phase 4A)
7. `history` turnos E-4 pre-pregunta → LLM threadpool → citations + grounding → `LLMInteractionLog`

**Streaming**: cola asyncio + productor threadpool → frames: `start` → `delta`×N → `citation` mid-stream → `done`.

**R29** (cliente): regex 10 patrones coercitivos + 6 admin lingo → violación → fallback stub total.

**R30** (admin): 10 patrones "assume ENS" + jargon sin definition trigger ±50 chars → violación → defensive enrich footer (NO full fallback).

**Memory N6**: `HISTORY_LIMIT = 8`. Admin sentinel `_ADMIN_AUTHOR = UUID(…0a11)`. Best-effort.

**Rate limit** (ADR-025, NO new table): feature filters reales — cliente: `("copilot_cliente_1d_b_1",)`; admin: `("copilot_chat","copilot_chat_stream","copilot_admin_1d_b_2")`. Caps: cliente 100/30k/€6; admin 500/100k/€40. FIX P1-1: cliente exige `project_id` obligatorio (anti quota poisoning). USD→EUR 1:1 simplificado.

**Personas YAML**: Pydantic valida 2 personas. Cache singleton (NO hot-reload). Admin: `screen_references_catalog` ~43 rutas. `normalize_screen_pattern` elimina UUID para match exacto.

**System knowledge auto-generado**: desde nav portales + WorkflowPhase + AGENT_REGISTRY. Drift bloqueado por `test_system_knowledge_coherence.py`.

---

### Medidas ENS cubiertas

- `op.acc.6`, `op.exp.10` — citados en completitud por categoría y corpus_gap fallback
- Todos los prefijos Anexo II: `org.N`, `op.pl/acc/exp/ext/nub/cont/mon.N`, `mp.if/per/eq/com/si/sw/info/s.N` — detect_filters regex los captura
- Art. 11 RD311/2022 — acumulación roles autónomo en `INDIVIDUAL_AUTONOMO_CONTEXT`
- Art. 38 + Art. 34 + Anexo III — ejemplos completitud BÁSICA/MEDIA/ALTA
- R1 inviolable: copiloto NO toma decisiones normativas

---

### Integraciones

`corpus/retrieval.hybrid_search` · `m11_copiloto.conversation_service` (memoria) · `m11_copiloto.workflow_state_scanner.compute_workflow_state` (estado EN VIVO) · `m30_client_contacts.ClientContactService` (M30 injection) · `security.llm_prompt_injection_guard` (PI guard ambas rutas) · `models.knowledge.LLMInteractionLog` (observabilidad) · `fulkro_identity.FULKRO_COPILOT_PRIMARY_CONTEXT` (anti-hallucination identidad) · `audit_log` hash-chain Sub-atom 5.A

---

### Gotchas / discrepancias

- **tokens stream = 0**: `LLMInteractionLog` en streaming almacena `prompt/completion_tokens=0` — Anthropic streaming no devuelve usage. Afecta precisión rate-limit mensual.
- **Admin Q&A rápido sin memoria N6**: `POST /copilot/chat` (admin RAG) no llama `load_conversation_history` — stateless. Solo la ruta persona-admin recibe `history` si el caller lo pasa. CLAUDE.md afirma memoria admin sin matizar la distinción entre rutas.
- **`prompts/agent_14_copiloto.py`** spec-level: usa intro `_INTRO_CLIENTE` aunque el módulo describe "copiloto interno Marcos". Es backward-compat export; producción usa `build_base_system_prompt(role)`. No es bug runtime.
- **`CORPUS_GAP_CONFIDENCE_THRESHOLD = 0.45`** sin calibración empírica. Corpus escaso puede sobretriggear fallback.
- **TODO-RBAC-PER-ENDPOINT-001** L45 `api.py`: RBAC Cat A pendiente.
- CLAUDE.md dice "14 agentes" — `system_knowledge_generated.py` lista 12 agentes activos (empírico real).

---

### Veredicto: COMPLETO

Pipeline RAG A14 production-grade: PI-guard, corpus_gap fallback, citation grounding, SSE streaming, rate-limit por tenant, memoria N6 persistente, personas YAML validadas, system knowledge auto-generado con CI gate. 3 superficies diferenciadas por role con R29/R30 enforcement post-respuesta empírico.


## 80 - Frontend - Paginas portal admin

**Alcance leido**: 96 `page.tsx` + 5 `layout.tsx` bajo `frontend/app/(admin)/admin/**`. Completos: `(admin)/layout.tsx`, `projects/[id]/layout.tsx`, `Header.tsx`, `Sidebar.tsx`, `ProjectTabs.tsx`, `HeaderProjectChip.tsx`, `projects/page.tsx`. Muestreados (head): ~30 paginas.

### Arquitectura de navegacion REAL (verificada en codigo)
- `(admin)/layout.tsx`: `AuthGuard requiredRole="owner"` envuelve TODO. Layout = `Sidebar` (lateral fijo `hidden lg:flex` + drawer movil) + columna con `Header` + `CopilotNextStepBanner` + `<main>` + `CommandPalette` (⌘K) + `CopilotPanel` + `OnboardingTourAdmin`.
- **Sidebar = navegacion global UNICA** (`TOP_NAV` 11 entradas): `Dashboard · Reuniones · Proyectos · Copiloto · Operaciones · SIEM · Compliance · Mensajes · Notificaciones · Finanzas · Ajustes`. SIEMPRE renderizado (NO condicional). Bajo el nav: secciones "Clientes activos" + "En retainer" (via `/retainer/active-client-ids`) + buckets estaticos Archivables/Archivados→`/operations`.
- **Header** (`Header.tsx`): solo `HeaderProjectChip` + `PortalSwitcher` + `AlertBell` + boton Salir. **NO existe header tri-pestaña** (Proyectos·Compliance). `grep` en Header.tsx = 0 matches de "tab/Proyectos/Compliance".
- **`projects/[id]/layout.tsx`** (project-scoped): `ProjectFeaturesProvider` + `ActiveProjectSync` (ADR-054, sincroniza Zustand `active-project-store` con URL) + `ProjectBreadcrumb` + `ProjectHeader` + `ProjectCategoryBanner` + `QuickActions` + **`ProjectTabs`** (la "navegacion por pestañas" real, dentro del contenido, NO en chrome global).
- **`ProjectTabs`**: 3 niveles → `MAIN_TABS` (15: Resumen/Workflow/Dimensiones/Roadmap/Diagnostico/Obligaciones/Plan/Implantacion/DdA/Evidencias/Dossier/Financiero/Comunicacion/Riesgos/MAGERIT) + `SUB_TABS` "Extras" (~35) + `PROFILE_TABS` "Especifico" (gated `feature`/`categories`/`archetypes`). `verification`/`audit` solo `MEDIA|ALTA`.
- **Selector hub** = `projects/page.tsx`: landing post-login, GATE explicito (auto-redirect retirado a proposito 2026-06-10). Busqueda+filtro sector+sort (`recent`/name/sector). `ProjectCard` navega a `/projects/{project_id}/roadmap` usando `client.project_id` REAL (comentario: `client.id` da 404). Empty-state friendly + crear proyecto.
- `HeaderProjectChip`: visible solo en `/admin/projects/*` con `activeProject`, badge categoria BASICA/MEDIA/ALTA → link a `/projects/{id}/dashboard`.

### Inventario top-level (24 dirs)
| Pagina | LOC | Tipo | Nota |
|---|---|---|---|
| `dashboard` | 49 | real | KpiRow+MyDay+Activity+Alerts+ChurnRisk widgets |
| `projects` (selector) | 387 | real | landing/GATE |
| `clients` | 17 | **redirect** legacy → `/admin/projects` (R23) |
| `clients/[id]` + `/branding` + `/meetings` + `/new` | 95.. | real | entidad cliente residual |
| `compliance` | 725 | real | self-dogfooding ENS |
| `compliance/monitor` `/projects` `/norma-reports[/key]` | 561/142/237 | real | |
| `cross-project-compliance` | 48 | **redirect** → `/admin/compliance/projects` |
| `copilot` | 23 | real | `CopilotMemoryWorkspace` (memoria por proyecto) |
| `finance` | 101 | real | KPIs + reconciliacion manual |
| `inbox` | 50 | **stub** | hint "abre proyecto"; cross-project diferido MB-19+ |
| `llm-observability` `/golden-eval` | 262 | real | coste LLM, admin-only |
| `magerit-analyses/[id]/import` | 9 | real | wrapper import panel |
| `magic-links` | 24 | **redirect** → selector (consolidado en `auditor-handoff`) |
| `meetings` `/[id]` `/new` | real | m_meetings cross-cliente |
| `messages` | 108 | real | bandeja cross-cliente |
| `notifications` | 198 | real | NotificationOrchestrator + redispatch |
| `operations` | 9 | real | wrapper `OperationsConsole` |
| `pipeline` `/leads/[id]` | 25.. | real | Kanban comercial |
| `retainers` `/churn-risk` | 21 | **redirect** legacy (retainer per-proyecto) |
| `settings` | 127 | real | Tabs: General/Branding/Fiscal/Pricing/SMTP/Notifications/About |
| `siem` | 226 | real | correlacion pentest M8+M19+M18; op.mon.1/op.mon.2 |
| `system-health` | 251 | real | |
| `timesheet` | 330 | real | |
| `whatsapp` | 209 | real | threads + SSE inbound |
| `alerts` | 274 | real | alertas globales + acknowledge |
| `workflow-command-center` `/projects/[id]` | 34/30 | real | dashboard multi-cliente + vista cronologica |

### Project-scoped `projects/[id]/*` (62 paginas)
Casi todas **thin route wrappers** (8-16 LOC) que delegan a componentes de motor: `dda`(M03), `dossier`(M09), `remediation`(ADR-055), `cloud-connectors`(M16), `contratos`(M14), `conformity`(M05), `transparency`(AI Act art.50), `exit`(M31) + magerit/plan/evidence/audit[annotations,clarifications,dda-evidence-gaps,draft-report]/verification/mcps/aepd/bia/renewal/retainer/providers. `projects/[id]/page.tsx`→`redirect(.../summary)`. Varias inyectan `CopilotGuidedFlow` (`PHASE_GUIDES`).

### Medidas ENS observables en UI
- `siem` → `op.mon.1` (deteccion) + `op.mon.2` (metricas). `dda` tab → 73 medidas Anexo II (M03); `verification`/`audit` gated MEDIA/ALTA. Tabs ENS-centricos: Dimensiones (19 dims), Riesgos, MAGERIT, Plan, Obligaciones, Backups (M26), Concienciacion.

### Integraciones / patrones
- Estado: tanstack-query (`useClients`, `useComplianceSidebarStatus` poll 60s, `retainer/active-client-ids`). Zustand `active-project-store` persist. SSE: `whatsapp` inbound, `summary` `ProjectEventsWrapper`.
- `R23` fuerte: 4 redirects legacy (`clients`, `retainers`, `magic-links`, `cross-project-compliance`). Dead-ish: `inbox` stub; `ThemeToggle` comentado.

### DISCREPANCIAS docs vs codigo
1. **CLAUDE.md "Header global tri-pestaña (Proyectos · Compliance) SIEMPRE visible"**: FALSO. `Header.tsx` no tiene pestañas; la nav global vive en `Sidebar` (`TOP_NAV` 11 items, no 2). 0 matches grep.
2. **"Sidebar lateral CONDITIONAL render solo project context"**: FALSO. `Sidebar` se renderiza siempre. Lo condicional/project-scoped es `ProjectTabs` (dentro del contenido del layout `[id]`), no el sidebar.
3. **"L3 hybrid auto-enter REMOVED · selector gate unico"**: CONFIRMADO en codigo (comentario explicito, auto-redirect retirado).
4. **"19 top-level admin pages catalogadas" (R23 exception)**: el conteo real top-level con contenido propio es mayor (~20 con render + ~4 redirects + stub `inbox`).
5. **Ruta duplicada**: `projects/[id]/workflow` y `workflow-command-center/projects/[id]` ambas renderizan `ProjectCronologicaView` (OPS-026 DRY a nivel componente, pero 2 rutas coexisten).
6. Sidebar comenta haber eliminado "Clientes/Retainer/Churn/MCPs" del nav global (coherente con R23), pero el item global "Mensajes/Notificaciones/Finanzas" sigue siendo cross-cliente top-level (legitimo).

**Veredicto**: MIXTO tirando a COMPLETO. Mayoria de paginas reales y bien delegadas; 4 redirects legacy intencionales + 1 stub (`inbox`). Navegacion solida pero la documentacion (header tri-pestaña / sidebar condicional) describe un diseño NO implementado: el patron real es Sidebar-global-siempre + ProjectTabs-in-content.


## 81 - Frontend - Componentes admin

**Alcance leido**: 80+ TSX en `frontend/components/`: `admin/`, `admin-meetings/`, `dashboard/`, `pipeline/`, `operations/`, `workflow-command-center/`, `financial/`, `roles/`, `providers/`, `project/`, `project-wizard/`, `magic-links/`, `notifications/`, `observability/`, `mcps/`, `discovery/`, `exit/`, `renewal/`, `idms/`, `dimensions/`. Ficheros >200 LOC muestreados primeras 60-80 lineas.

---

### Inventario por area (ficheros clave)

| Directorio | Ficheros clave | Proposito real |
|---|---|---|
| `workflow-command-center/` | `WorkflowCommandCenterDashboard`, `AdaptationBadge`, `ProjectCardUrgent`, `ProjectCronologicaView`, `CopilotoAdminSidebar` | 4 zonas cronologicas (urgente/semana/marcha/30d) · polling 30s via `useCommandCenterMultiClient` |
| `dashboard/` | `KpiRow`, `ReadinessScoreCard`, `WorkflowBlockingAlert`, `ChurnRiskWidget` | 4 KPI cards (proyectos/leads/retainers/tesoreria) + alertas bloqueantes |
| `pipeline/` | `PipelineKanban`, `LeadDrawer`, `LeadCard`, `LeadColumn` | CRM kanban drag-and-drop `@dnd-kit` + drawer detalle lead |
| `project/` | `ProjectTabs`, `MageritPanel`, `PlanGantt`, `EvidenceVault`, `RiskDashboard` | 22 ficheros nucleo proyecto: tabs navegacion + motores surfaceados |
| `project-wizard/` | `ProjectDiagnosticoWizard` + 6 steps | Wizard creacion atomico 6 pasos: cliente+ENS+categoria+activos+user |
| `idms/` | `DocumentTreeAdmin`, `IdmsAdminLayout`, `UploadDocumentModal` | 15 carpetas K.0-K.6+retainer; conteo docs client-side (evita N+1) |
| `discovery/` | `DiscoveryPanel` + 9 tabs | Cloud discovery: activos/identidad/datos/vulns/config/flujos/continuidad/logs/consolidado |
| `mcps/` | `McpProjectScopedPanel`, `McpToolCard`, `McpExecutionProgress`, `MCPStatusGrid` | Pentest MCPs 4 familias (vulnscan/cloud/config/phishing) project-scoped R23 |
| `roles/` | `RoleAssignmentCard`, `RoleTopologyPanel`, `RolesSegregationAlert` | 8 roles ENS: RI/RS/RSEG/RSIS/DPO/CISO/Auditor/Sponsor con badge+tooltip |
| `financial/` | `FinancialPanel`, `MilestoneTimeline`, `InvoicesList`, `AAPPBillingStatusCard` | M15: 4 KPIs facturacion + cadena AAPP + facturas DataTable |
| `providers/` | `ProvidersGrid`, `ProviderCard`, `C002GapsPanel`, `AddProviderModal` | M14 proveedores: grid filtrable WCAG-700 + gaps C.002 |
| `admin-meetings/` | `MeetingLivePanel`, `MeetingNotes`, `PostMeetingActions` | A18 SSE streaming insight + timer + actas |
| `operations/` | `OperationsConsole`, `NotificationsDlqWidget` | Ops cross-tenant: backups M26 + renovaciones 90d + DLQ |
| `renewal/` | `RenewalWarRoom`, `DriftMatrix`, `RenewalTimeline` | M27+M28: countdown + drift 10x4 + 8 milestones + form auditor |
| `magic-links/` | `MagicLinkGenerator`, `MagicLinkHistoryTable` | 23 purposes enum; ContactQuickPicker M30 integrado |
| `admin/` (nested) | `CopilotGuidedFlow`, `DdaEvidenceGapsAdminView`, `AdminClarificationsInbox`, `AdminChatPanel` | Copiloto per-fase + heatmap gaps DdA + inbox clarifications auditor + chat SSE |

---

### Tanstack-query (R24) — cumplimiento verificado

- `useQuery`/`useMutation`/`useQueryClient` en TODOS los componentes de datos. Ningun fetch directo detectado.
- `refetchInterval`: `NotificationsDlqWidget` 60s; `WorkflowCommandCenterDashboard` 30s.
- `invalidateQueries` on mutation verificado en DLQ reprocess, clarifications patch, `AdminChatPanel` send.
- `staleTime` explicito: `DocumentTreeAdmin` 30s/15s + `useMemo` countsByFolder (evita N+1).
- R24 **CUMPLIDO** empiricamente.

---

### Patron error-retry

- `WorkflowCommandCenterDashboard`: `isError` → texto + `<button onClick={() => refetch()}>Reintentar</button>` (sin `data-testid`).
- `RiskDashboard`: `<Alert variant="danger">` + `<Button onClick refetch>` con `aria-busy` — patron canonico de CLAUDE.md.
- `OperationsConsole`: `Alert` + retry inline.
- `NotificationsDlqWidget`: **sin retry en error** (gap menor; carga silenciosa).
- Discrepancia: patron canonico con `data-testid="{component}-retry"` no esta en todos los componentes.

---

### Motores surfaceados en UI (muestra)

| Motor | Componente admin |
|---|---|
| M01 | `ProjectDiagnosticoWizard` step3, `ArchetypePanel` |
| M02 MAGERIT | `MageritPanel` (intrinsic/effective/residual+freeze+treatment), `RiskDashboard` |
| M03 DdA | `DdaEvidenceGapsAdminView` heatmap + tab `/dda` |
| M04 Plan | `PlanGantt` SVG barras+milestones diamantes, critical path rojo |
| M07 Evidencias | `EvidenceVault` status derivado (valid/expiring_soon/expired/pending_signature) |
| M08 Pentest | `McpProjectScopedPanel` 4 familias launcher+progress+history |
| M10 CRM | `PipelineKanban` dnd-kit, `LeadDetailView` 5 tabs |
| M15 Financiero | `FinancialPanel`, `AAPPBillingStatusCard`, `InvoicesList` |
| M16 Cloud | `DiscoveryPanel` 9 tabs + `/cloud-connectors` |
| M24 IDMS | `DocumentTreeAdmin` 15 carpetas, `UploadDocumentModal` |
| M26 Backup | `OperationsConsole` (last_backup + restore_test + archivable_count) |
| M27/M28 | `RenewalWarRoom` + `DriftMatrix` 10x4 |
| A18 Meetings | `MeetingLivePanel` SSE + `PostMeetingActions` |
| m_remediation | tab `/remediation` `ProjectTabs` (ADR-055 · 2026-06-13) |

---

### R30 TooltipENS — presencia verificada

Importado en: `NotificationsDlqWidget`, `ProvidersGrid`, `FinancialPanel`, `DimensionsWizardPanel`, `MageritPanel`, `RenewalWarRoom`, `RoleAssignmentCard` (8 roles via `ROLE_TERM_KEY`→`GlossaryKey`), `MagicLinkGenerator`, `DiscoveryPanel`.

`AdaptationBadge` (R28): popover per-dim + `variant_extra_focus` por arquetipo. Materializa 19 dims visualmente.

`CopilotGuidedFlow`: generico per-fase (props `phaseId`, `intro`, `whyImportant`, `steps`, `commonMistakes`, `estimatedTime`, `nextAction`). Dismiss localStorage per-fase. R30 asume cero ENS.

---

### ProjectTabs — cobertura rutas project-scoped (R23)

35 entradas total (`MAIN_TABS` 15 + `SUB_TABS` 20+). Todas bajo `/admin/projects/[id]/X`. R23 **sostenido**.

- Condicionadas por categoria: `Verificacion` + `Auditoria` solo `["MEDIA","ALTA"]` (correcto: BASICA autodeclaracion).
- Tab `Remediacion` wired (ADR-055 motor `m_remediation` 2026-06-13).
- Tab `Transparencia IA` (1.E.1.B.2).
- `DiscrepanciasCriticalBadge` activo en tab Discrepancias.

---

### Dead code / gotchas / TODOs

- **`LeadDrawer.invokeAgent`**: `setTimeout(350ms)` + `toast.success("(simulado)")`. Comentario: `"Sprint 2: real agent invocation wired when backend lead model exists"`. Dead code — botones agentes NO llaman backend.
- **`MeetingLivePanel`**: split markdown → 6 bloques A-F en frontend (fragil si Marcos cambia formato; deberia ser backend).
- **`AdminGoldenEvalView`**: badge `capability_pending_build` — wiring backend parcial.
- **`DocumentTreeAdmin`**: conteo docs via client-side aggregation (carga lista completa; puede degradar >500 docs).

---

### Medidas ENS cubiertas

`op.pl.1-4`, `op.acc.1-6`, `op.exp.1-10`, `op.mon.1-3`, `op.cont.1-4`, `op.ext.1-4`, `mp.s.1-4`, `mp.si.1-5`, `mp.per.1-4`, `mp.info.1-6`, `org.1-9`.

---

### Veredicto

| Area | Estado |
|---|---|
| Workflow Command Center / dashboard | Completo |
| Pipeline CRM (kanban + drawer) | Parcial — invokeAgent dead code |
| Project tabs (35 rutas R23) | Completo |
| MAGERIT / riesgos | Completo |
| MCPs pentest | Completo |
| IDMS documental | Completo |
| Discovery cloud (9 tabs) | Completo |
| Financiero / renovacion / roles | Completo |
| DLQ operaciones | Completo |
| Meetings A18 | Completo |
| Golden eval observabilidad | Stub/parcial |

**Global**: **mixto** — motores ENS core completamente surfaceados; dead code en CRM agents (invokeAgent simulado) y observabilidad LLM golden eval parcial.


## 82 - Frontend - Paginas portal cliente

**Alcance**: 42 `page.tsx` + 1 `layout.tsx` bajo `frontend/app/(client-portal)/client-portal/`. Lectura directa de todos los ficheros. Componentes hijo referenciados por nombre, no auditados en profundidad.

---

### Inventario (42 paginas)

| Ruta (`/client-portal/…`) | Rol | Patron |
|---------------------------|-----|--------|
| `page.tsx` | Redirect root → dashboard o login via `/me` | thin |
| `login/` | Credentials + MFA 2-step (email OTP o TOTP) | auth |
| `dashboard/` | → `ClientDashboardV3` | thin |
| `workflow/` | Progreso cronologico: progress bar + timeline + FAQ + copilot | core |
| `onboarding/` | 4 tabs: connect→wizard→connectors→lms | core |
| `onboarding/oauth-callback/` | code+state OAuth → `oauthCallback` → redirect | callback |
| `categorizacion/` | READ-ONLY M01 + SSE `m01.categorizacion.completed` | read+sse |
| `magerit/` | Activos (30-cap) + form aportar info + firma gated | read+sign |
| `dda/` | Summary DdA + pregunta form + firma gated | read+sign |
| `plan/` | `GanttView` DRY + toggle "Solo mis tareas" + SSE `m17.plan.updated` | read+sse |
| `evidencias/` | → `EvidenciasUploadPage` + `AgentSuggestionBanner` | thin |
| `cloud-connections/` | Activas cards + `CloudConnectFirstStep` reuse + modal disconnect chat-mediated | read+sse |
| `remediaciones/` | 3 secciones + `ApprovalModal` + `RemediationClienteView` (ADR-055) | read+sse |
| `cumplimiento/` | Aggregator 5 areas overall health badge | read |
| `conformidad/` | Tier-aware BASICA/MEDIA/ALTA 6 secciones + readiness + firma | read+sign |
| `certificacion/` | → `AuditAccompanimentClienteView` | thin |
| `continuidad/` | → `ContinuidadClienteView` SSE `continuidad.*` | thin |
| `pentest-authorization/` | 6 secciones + firma OTP step-up | read+sign |
| `policies/` | Accordion familia + review per policy + `PolicyBulkSignButton` | read+sign |
| `dpc-anual/` | 4 subsecciones + review actions + firma + historico | read+sign |
| `firmas-hub/` | Progress bar + chain integrity + 4 SignatureCard + ChainVisualizer | read |
| `firmas-pendientes/` | Lista + `SignatureCanvas` TIER 1 inline + SSE signing.* | sign+sse |
| `firma/` | Estatica explicativa eIDAS Art.25.1 + `PublicKeyVerifier` | static |
| `chat/` | → `ClientChatPage` | thin |
| `inbox/` | `ClientInboxList` + Sheet thread + Dialog composer + NotificationsPanel | messaging |
| `incidents/` | Counters + lista resolved/closed + `IncidentDetail` + AgentBanner | read+sign |
| `actas/` | 4 subtypes filter chips + lista + `ActaDetail` firma | read+sign |
| `retainer/` | Oferta post-cert: 3 tier cards + accept/thinking/decline | sign |
| `retainer-checkin/` | Comites trimestrales + `CheckinDetail` + `ClientDigestCard` | read+sign |
| `files/` | Sidebar tree + 2 tabs docs/evidence + search + scan toggle + upload + SSE | gestdoc |
| `billing/` | Listado facturas + IBAN info-mode (NO boton copiar per directiva Marcos) | read |
| `registros/` | Redirect 2.5s → `/tasks` + mensaje explicativo (backward-compat) | redirect |
| `tasks/` | → `ClientTasksList` | thin |
| `transparency/` | AI Act art.50 log 180 dias | static |
| `whatsapp/` | 3 estados opt-in/otp/thread + SSE inbound + export RGPD art.15 | messaging |
| `account/` | Links billing/notifications + cambio contraseña form | settings |
| `settings/` | Hub 4 links: avisos/MFA/cuenta/whatsapp | hub |
| `settings/mfa/` | MFA email: idle→start→code→confirm; disable directo | auth |
| `settings/notifications/`, `account/notifications/`, `registros/[tipo]/` | no leidas en detalle | — |

---

### Layout y autenticacion

- `layout.tsx`: Server Component (`metadata` robots noindex) → `ClientPortalChrome` ("use client") detecta paths publicos y suprime sidebar/header.
- Root: `clientApi("/client-portal/me")` → redirect. Sin SSR auth check.
- `login`: 2-step real. `{requires_mfa: true}` en 401 → step MFA. Reenvio implementado. `must_change_password` → `?force_change=1`.

### Filosofia cliente-minimo verificada empiricamente

**VE**: `categorizacion` (M01 read-only), `magerit` (assets 30-cap), `dda` (summary), `plan` (Gantt + "Solo mis tareas"), `cumplimiento` (5-area aggregator), `firmas-hub`.

**AUTORIZA**: `cloud-connections` disconnect chat-mediated (`requestDisconnect` → admin decide, ADR-014 sostenido); `pentest-authorization` firma OTP step-up.

**FIRMA**: `dda` (DdaSignFinalButton), `magerit` (MageritSignValidationButton), `conformidad` (ConformidadSignButton tier-aware), `firmas-pendientes` (SignatureCanvas TIER 1 Ed25519), `policies` (PolicyBulkSignButton), `actas`, `dpc-anual`, `retainer-checkin`.

**RECIBE**: `remediaciones`, `certificacion`, `continuidad`, `retainer` (oferta post-cert).

### SSE auto-update (9 puntos)

`categorizacion` `m01.categorizacion.completed` · `magerit` `m02.magerit.updated` · `plan` `m17.plan.updated` · `cloud-connections` `cloud.connector.*`+`cloud_remediation_*` · `remediaciones` `cloud_remediation_*` · `firmas-pendientes` `signing.*` · `files` `document.uploaded` · `whatsapp` `useInboundWhatsAppSSE` · `continuidad` via hijo.

### R29 y TooltipENS verificados en codigo

- "Sin prisa por tu parte" en 8+ paginas. Errores espanol amigable (NO stack trace). `billing`: "avisa a Marcos". `retainer`: "Me lo pienso"/"De momento no". `registros`: redirect amigable NO 404. NUNCA `text-red-*` directo.
- 10+ paginas usan `<TooltipENS>` para ENS/DdA/MAGERIT/ENAC/Ed25519/OTP (R30-inverso). `firma/` usa `<InfoTag>` equivalente.

### Gotchas

- `magerit`: `assets.slice(0, 30)` hardcoded — cliente no ve activos >30 (consultor ve 100%).
- `files`: arbol carpetas reconstituido client-side desde lista flat; fragil si hay anidamiento profundo.
- `remediaciones`: combina approval manual + `RemediationClienteView` ADR-055 — dos flows en una pagina.
- `account/` duplica links de `settings/` hub. `registros/[tipo]/` no leida.

### Medidas ENS cubiertas

`op.acc.5`/`op.acc.6` MFA; `op.exp.1` categorizacion; `op.exp.2` magerit; `op.exp.4`/`op.exp.5` DdA E-040; `op.exp.7`/`org.2` policies CCN-STIC 805; `op.exp.10` incidents CCN-CERT; `mp.s.2` cloud sync; `mp.s.8` remediation; `org.8` continuidad BIA/DRP; `org.9` retainer trimestral; `op.pl.1`/`op.pl.2` plan Gantt; eIDAS Art.25.1 (E-040/E-041) firmas-hub + firmas-pendientes + dda + magerit + conformidad + actas + dpc-anual.

### Discrepancias CLAUDE.md vs codigo real

1. SSE Pattern #14 "a nivel pagina": en `conformidad`, `actas`, `incidents` el SSE esta delegado a componentes hijo, no en el `page.tsx` directamente.
2. `magerit` usa `assets.slice(0, 30)` hardcoded — no documentado en CLAUDE.md.
3. Todo lo demas (radar retirado, disconnect chat-mediated, tier-aware conformidad) confirmado correcto.

### Veredicto

**Completo**. Ciclo ENS completo cubierto: login (MFA) → onboarding (OAuth) → categorizacion → magerit → DdA → plan → cloud → politicas → conformidad → certificacion → firmas → retainer. Cliente-minimo 100% sostenido empiricamente. SSE en 9 puntos. TooltipENS sistematico. R29 sin violaciones. Dead code minimo (solo `registros` redirect backward-compat).


## 83 - Frontend - Componentes portal cliente

**Parcela**: `client-portal/` (85 TSX), `sign-flows/` (11), `copilot/`+`copiloto/` (7), `signatures/` (1), `workflow-guide-client/` (8), `remediation/`, `transparency/`, `audit/`, `conformity/`, `onboarding/` (cliente). ~18 000 LOC. Repetitivos muestreados 1-2/familia.

---

### Ficheros clave

- `dashboard/ClientDashboardV3.tsx` — 3 zonas: hero adaptativo + "trabajo de hoy" + resumen. `useClientDashboard`.
- `copiloto/CopilotoDock.tsx` — Dock flotante cliente (332 LOC). SSE streaming + proactive hint Phase 1D. Evento DOM `fulkro:open-cliente-copiloto`.
- `copilot/CopilotPanel.tsx` — Panel admin Sheet (174 LOC). Zustand + ⌘J. Contexto por motor (magerit/conformity…).
- `signatures/SignatureCanvas.tsx` — Canvas TIER 1 (react-signature-canvas). Nombre+apellido+WCAG 2.2 AA. Emite `SignatureSubmitPayload`.
- `sign-flows/BaseSignFlow.tsx` — Esqueleto 6 sign-flows magic-link. OTP 6 dígitos condicional + rechazo ≥5 chars.
- `sign-flows/ContractCanvasSignFlow.tsx` — Firma contrato: OTP + preview WYSIWYS + `SignatureCanvas` + geolocalización opcional.
- `AuditAccompanimentClienteView.tsx` — Timeline read-only certificación. BASICO 6 / MEDIO_ALTO 11 estados. SSE auto-update.
- `remediations/RemediationCard.tsx` — Card gap remediation. Ámbar empático, NO rojo. `friendly_message` server-side.
- `remediations/ApprovalModal.tsx` — Modal aprobar/rechazar gap cloud. "No hay prisa". R29 explícito.
- `RemediationClienteView.tsx` — Lista remediaciones + autorización. Chips ámbar/esmeralda.
- `workflow-guide-client/WorkflowGuideTimelineClient.tsx` — 3 zonas (COMPLETADO celebratorio / SIGUIENTE PASO / PRÓXIMOS). Sin deadlines.
- `ConnectorsClientView.tsx` — Grid 6 proveedores (GitHub/M365/Azure/AWS/GWorkspace/Base). OAuth + IAM AWS. `TooltipENS`.
- `CloudConnectFirstStep.tsx` — Onboarding. "saltar y conectar después" prominente.
- `firmas-hub/ChainIntegrityBanner.tsx` — Banner cadena SHA-256+Ed25519. 3 estados (sin firmas/roto/intacto).
- `pentest/PentestAuthorizeButton.tsx` — 2-step: mark-reviewed + OTP via `SigningFlow` shared.
- `EvidenciasUploadPage.tsx` — Upload evidencias. Toast ClamAV post-upload (ENS mp.s.5).
- `policies/PolicyRow.tsx` — 3 acciones: `revisada_ok`/`con_pregunta`/`suggest_change`.
- `TransparencyLogCard.tsx` — Log AI Act art.50 cliente. NO expone `llm_provider`/`llm_model`.
- `transparency/AdminTransparencyView.tsx` — Log transparencia admin + campos técnicos para auditor ENAC.

---

### Modelo de datos (tipos API observados)

Sin acceso directo a BD. Wrapper `clientApi` OPS-044 (`/segment`) salvo `EvidenciasUploadPage`. Tipos clave: `RemediationGap` (severity/approval_status/explanation_es) · `AccompanimentTimeline` (current_state/category_branch/transitions[]) · `EnrichedStepState` (primary_actor/cta_url) · `SignatureSubmitPayload` (dataurl/nombre/apellido) · `PolicyClientView` (template_codigo/client_review_status).

---

### Endpoints llamados desde componentes

- `POST /api/v1/client-portal/evidencias/upload` — `EvidenciasUploadPage`
- `GET /api/v1/client-portal/transparency/log` — `TransparencyLogCard`
- `GET /api/v1/admin/projects/{id}/transparency/log` — `AdminTransparencyView`
- `POST /api/v1/client-portal/copiloto/chat/stream` (SSE) — `CopilotoDock`
- `POST /api/v1/client-portal/remediations/{id}/approve|reject` — `ApprovalModal`
- `POST /contract-signing/confirm` — `ContractCanvasSignFlow`
- `GET /api/v1/client-portal/audit-accompaniment/timeline` — `AuditAccompanimentClienteView`
- `GET|POST /api/v1/client-portal/connectors/*` — `ConnectorsClientView`

---

### Máquinas de estado

- **`AuditAccompanimentClienteView`**: rama BASICO 6 / MEDIO_ALTO 11 estados (mirror exacto `state_machine.py`). `currentIdx = orderedStates.findIndex(...)` → icono CheckCircle/Circle-pulse/Circle-gris.
- **`WorkflowGuideTimelineClient`**: segmenta pasos en completed/current/proximos. Fuente: hook `useClientWorkflowGuide`.
- **`BaseSignFlow`**: `done`+`decision` local. OTP gate condicional vía `MAGIC_LINK_OTP_REQUIRED` set.

---

### Medidas ENS cubiertas

- `mp.s.5` (antimalware) — `EvidenciasUploadPage`: toast ClamAV, cuarentena
- `op.acc.6` (MFA/OTP) — `PentestAuthorizeButton`, `BaseSignFlow`: OTP step-up
- `mp.com.3` (cifrado canales) — `ConnectorsClientView`: token OAuth cifrado inmediatamente
- `op.exp.2`/`op.exp.8` (audit log) — `EvidenciasUploadPage`, `ChainIntegrityBanner`
- `mp.info.3` (firma documentos) — 6 sign-flows Ed25519; `ContractCanvasSignFlow`
- `op.pl.2` (plan implantación) — `WorkflowGuideTimelineClient`: roadmap ENS cliente
- `mp.s.2` (conectores cloud read-only) — `ConnectorsClientView`, `CloudConnectFirstStep`
- `op.acc.7` (trazabilidad) — `ChainIntegrityBanner`: SHA-256+Ed25519 visible cliente
- AI Act art.50 — `TransparencyLogCard` (cliente) / `AdminTransparencyView` (auditor)

---

### Integraciones

- **SSE Pattern #14+#21**: `useClientProjectEvents` en 5 componentes (accompaniment, continuidad, chat, notificaciones, coach). event_id + replay buffer.
- **TanStack Query**: `useQuery`/`useMutation` en remediation, connectors, accompaniment. `invalidateQueries` post-SSE.
- **Zustand** (`copilot-store`): `open`, `panelContext`, `activeMotor`, `projectId` para panel admin.
- **Magic-links**: `useMagicLinkConsume` en todos sign-flows. `MAGIC_LINK_OTP_REQUIRED` set en `lib/magic-link-types`.
- **LLM**: `CopilotoDock` SSE streaming. Sin exposición temperatura/proveedor al cliente (R30 inverso).
- **Evento DOM**: `CopilotoDock` escucha `fulkro:open-cliente-copiloto` — único dock cliente consolidado.

---

### Patrones, gotchas y dead code

- **R29 verificado empíricamente**: 0 clases `text-rose-*`/`text-red-*`/`bg-red-*` en client-portal. Comentario explícito en `RemediationClienteView`: "NUNCA rojo (R29)".
- **Overlap `CloudConnectFirstStep` ↔ `ConnectorsClientView`**: funcionalidad solapada. `Future-1.E.cloud-connectors-consolidation` documentado, no resuelto.
- **`EvidenciasUploadPage` desvía OPS-044**: `fetch()` directo + X-CSRF-Token manual en lugar de `clientApi` wrapper. Sin impacto funcional.
- **`PolicyRow` catch vacíos**: `catch { // error toast viene del hook }` — correcto pero confuso.
- **Geolocalización en `ContractCanvasSignFlow`**: timeout 8s, graceful `geo=null`. Backend acepta `null` en `geo_lat`/`geo_lon`.
- **`TransparencyLogCard` vs `AdminTransparencyView`**: separación correcta — cliente NO ve `llm_provider`/`llm_model`. R30 inverso cumplido.

---

### Veredicto

**Completo**. Dashboard, 6 sign-flows Ed25519, canvas firma contrato, copiloto (dock cliente + panel admin), conectores cloud 6 proveedores, remediation aprobación cliente, timeline acompañamiento BASICO/MEDIO_ALTO, workflow guide R29, transparencia IA dual, upload evidencias. Filosofía cliente-mínimo verificada (0 endpoints destructivos desde portal cliente). R29 confirmado (0 clases CSS rojas). Deudas: overlap CloudConnect (Future-X documentado) + `EvidenciasUploadPage` fuera de OPS-044.


## 84 - Frontend - Portales (auditor/pentester/remediation), publico, legal, landing

**Alcance**: 31 TSX en `(portal)/`, `(public)/`, `(legal)/` + 16 componentes en `/components/{auditor-portal,pentester-portal,remediation-portal,public,legal,verify-auth,diagnostico}/` + middleware + 14 HTML en `landing/`. Cobertura 100% rutas objetivo.

---

### 1. Portal Auditor ENAC (`/auditor-portal/[token]/*`)

Token magic-link `AUDITOR_PORTAL_ENAC`. Gate: GET metadata (peek, NO consume) → OTP step-up opcional → POST `/session` → render.

**Componentes clave**:
- `AuditorPortalEntry.tsx` — validacion token + OTP gate (`otp_required`)
- `AuditorPortalChrome.tsx` — top-bar cliente-branded (CSS vars `--client-primary-color`) + sidebar 11 secciones + footer Ed25519
- `views/*.tsx` (11): Summary, DdA, Magerit, Plan, Evidence, E041, AuditLog, Pentest, Documents, DraftReport, DdaEvidenceGaps
- `AnnotationPanel.tsx` — 7 target_types, 4 severidades, 24h delete window
- `ClarificationButton.tsx` — topbar global + anclar por medida

API `lib/api/auditor-portal.ts` (BASE `/api/v1/public/auditor-portal`): 15 endpoints (metadata, session, dda, magerit, plan, evidence, e041, audit-log, pentest, documents, draft-report, dda-evidence-gaps, annotations CRUD, clarifications CRUD). Middleware: `NextResponse.next()` — auth real via backend por request. `robots: noindex` en `(portal)/layout.tsx`.

---

### 2. Portal Pentester (`/pentester-portal/[token]`)

`PentesterPortal.tsx` (794 LOC, single-file). Token `portal_pentester_externo`.

- Scope: targets, web_apps, exclusions, scan_window, deadline, categoria ENS
- 7 documentos SHA-256 visibles; VPN `.ovpn` descargable
- Findings: formulario CVSS v3.1 + CVE O upload PDF — ambos activos; autosave localStorage 1s
- `completePentesterEngagement()` irrevocable → `report_received`; contacto emergencia con phone

**Endpoints** (BASE `/api/v1/public/pentester`): GET data, GET doc/{idx}, GET vpn, POST findings, POST upload-pdf, POST complete.

---

### 3. Portal Remediacion (`/remediation/[token]`)

`RemediationPortal.tsx` + `RemediationGuideModal.tsx`. Token `portal_remediacion`.

- Progress bar ARIA; severity buckets 4 niveles (pending/total)
- Findings: `summary_non_technical` R29, time_estimate, requires_restart/maintenance_window
- `markRemediationFixed()` → retest `fixed` | `still_present` (modal guia)
- Resolved: colapsable `aria-expanded`

**Endpoints** (BASE `/api/v1/public/remediation`): GET data, GET findings/{id}/guide, POST findings/{id}/fixed.

---

### 4. Verify-Auth (`/verify-auth/[token]`)

`VerifyAuthPortal.tsx`. RSEG autoriza pentest run: scope completo + declaracion legal server-side + checkbox + OTP opcional → confirmacion `signature_hash` SHA-256. Endpoints: GET data, POST /otp, POST /sign.

---

### 5. Flujos publicos (`(public)/`)

| Ruta | Estado |
|---|---|
| `/ml/consume?token=` | Completo — redirect `→ /sign/{token}` |
| `/sign/[token]` | **Mixto** — 7 purposes reales + redirect a portales + `LegacyDocumentSignFlow` mock para `firma_documento`/`aprobacion_acta` (deuda `FASE-9-MAGIC-LINK-MOCKS-CLEANUP-001`) |
| `/download/[token]` | **Mixto** — `descarga_backup_archivo` activo; otros 2 en 501 mostrado gracefully |
| `/diagnostico/[token]` | Completo — consume → consentimiento Art.13 → cuestionario paginado → submit |

`components/sign-flows/`: 8 componentes reales (ContractCanvas, ApprovePropuesta, ApproveFactura, ValidateScopeChange, AcceptResidualRisk, SignDPA, ConfirmConformidad, Legacy).

---

### 6. Paginas legales (`(legal)/`)

| Ruta | Estado | Nota |
|---|---|---|
| `/privacy` | Completo | CIF/NIF `[pendiente · alta autonomo]` |
| `/cookies` | Completo | COOKIE_INVENTORY + banner AEPD 3-botones |
| `/derechos-rgpd` | Completo | Arts.15-22 RGPD + self-service endpoints |
| `/dpa-template` | Completo | DOCX via `/api/v1/legal/dpa-template/download` · 3 anexos |
| `/sub-processors` | Completo | Tabla + GDPR mechanism + DPA status + subscribe (Art.28.2) |
| `/trust` | **Mixto** | Live compliance_status API; `privacy`/`cookies` marcados "disp. en breve" aunque existen |
| `/terms` + `/imprint` | Completo | `/imprint` CIF/NIF pendiente |

`CookieConsentBanner.tsx`: 3 opciones visibilidad igual (Rechazar/Configurar/Aceptar) — cumple Guia AEPD 2020. Persiste via POST `/api/v1/legal/cookies/consent`.

---

### 7. `/docs/verify-signature`

Pagina publica sin auth: openssl CLI + Python + API POST `/api/v1/auth/verify-signature`. Util para auditor ENAC externo sin acceso al sistema.

---

### 8. Landing estatica (`landing/`)

14 HTML (~1.400-1.800 LOC c/u). `robots.txt` + `sitemap.xml` presentes. Schema.org `Organization`+`ProfessionalService` en `index.html`. OG tags completos. Pricing NO muestra numeros canonicos — copy "precio a tu medida" deliberadamente generico (eleccion comercial).

**AUSENCIA**: `security.txt` (RFC 9116) referenciado en `/trust` como `/.well-known/security.txt` pero NO existe en el repo.

---

### ENS Medidas cubiertas

- `op.acc.6` — autenticacion step-up OTP (auditor portal + verify-auth)
- `op.exp.1` — gestion vulnerabilidades (pentester findings submission)
- `op.exp.2` — correctivos post-pentest (remediation fixed/retest)
- `op.exp.4` — autorizacion pentest firmada (verify-auth sign + SHA-256)
- `mp.s.3` — proteccion aplicaciones web (pentester scope + VPN)
- `org.4` / `mp.info.6` — trazabilidad audit-log inmutable visible auditor ENAC
- `E-702` — reporte pentest (upload PDF + findings estructurados CVSS v3.1)
- `mp.com.3` (parcial) — descarga E-041 / dossier final en 501 stub

---

### Discrepancias CLAUDE.md vs codigo real

1. **Subrutas auditor portal**: memoria `auditor-portal-architecture.md` dice 11 rutas; filesystem real tiene **12 TSX** (`audit/dda-evidence-gaps` ruta doble segmento + raiz).
2. **Trust Center UI**: `/trust` marca `privacy`/`cookies` `available={false}` ("disp. en breve") pero ambas paginas **existen y tienen contenido completo** — bug UI.
3. **`security.txt`** (RFC 9116): `/trust` lo enlaza como `/.well-known/security.txt` pero no existe en el repo. No documentado en CLAUDE.md.
4. **NIF/CIF** pendiente en `/privacy` e `/imprint`: no consta en Future-X de CLAUDE.md.
5. **`LegacyDocumentSignFlow`** mock activo (`FASE-9-MAGIC-LINK-MOCKS-CLEANUP-001`): no en Future-X CLAUDE.md.
6. **`descarga_certificado_conformidad`/`descarga_dossier_final`** en 501: no en Future-X CLAUDE.md.

---

### Veredicto

**MIXTO** — portales gated (auditor ENAC, pentester, remediation, verify-auth) **COMPLETOS y production-grade** con OTP step-up, branding cliente, ARIA correcto, R29 aplicado. Flujos publicos **MIXTOS**: `/sign` con deuda LegacyDocumentSignFlow activa, `/download` con 2/3 purposes en 501. Paginas legales **COMPLETAS** salvo NIF pendiente e incoherencia UI en Trust Center. Landing **COMPLETA** salvo ausencia `security.txt`. Sin dead code relevante en porcion leida.


## 85 - Frontend - lib (API clients, stores, contexts, auth, branding, types)

**Alcance**: 177 ficheros en `frontend/lib/`. Lectura completa de la infraestructura central + 35/91 módulos `lib/api/*` representativos (el resto sigue el mismo patrón wrapper+interfaz TS).

### Infraestructura fetch (OPS-044 verificado)
| Wrapper | Fichero | Base URL real | Uso |
|---|---|---|---|
| `api<T>` | `lib/api.ts` | vacía (el caller pone `/api/v1/...`) | Admin + auditor |
| `clientApi<T>` | `lib/client-portal-api.ts` | `const API_BASE = "/api/v1"` | Portal cliente |

CSRF: `getCsrfToken()` lee cookie `fulkro_csrf` (header `X-CSRF-Token` en mutantes, ADR-019 triple binding). Clases de error `ApiError`/`ClientApiError` con `.status` para discriminar 404 vs 401.

### Zustand stores
- **`active-project-store`** (ADR-054): persist sólo `lastUsedProjectId`; `activeProject` se hidrata desde la URL. **L3 auto-redirect retirado** (`redirect.ts`, 2026-06-10): el admin SIEMPRE va a `/admin/projects`.
- **`copilot-store`**: `mergePanelContext()` filtra `undefined` (fix race ActiveProjectSync vs `useCopilotPageContext`).
- **`auth-store`**: `{user, csrfToken, ready}`; `logout()` llama `clearActiveProject()`.

### Auth / contexts / branding
- `auth/roles.ts`: `ADMIN_ROLE="owner"`, `CLIENT_PORTAL_SCOPE="rw"`. `auth/redirect.ts`: rechaza externos / protocol-relative (`//`) / fuera de rol.
- `ProjectFeaturesContext` (ADR-036): TanStack Query staleTime 60s; `hasFeature(key)`; **17 FeatureKeys** (`media_auditor_enac`, `alta_pentest_cpstic`, `art9_rgpd_data`, `dora_dual_compliance`, `ztna_mfa_obligatorio`, `pce_nis2`…), gates por categoría + 7 arquetipos.
- `ClientBrandingProvider`: inyecta CSS vars `--client-primary/secondary-color` en `<html>` con degradación graceful.
- `fulkro-identity.ts`: single source of truth FE (phone +34 637 165 328, email marcosmata@fulkro.es, distintivo Pantone Orange 021C `#FE5000`).

### Magic links / glosario
`magic-link-types.ts`: **36 purposes** (9 base + 5 M8 + 3 M25 + 3 M21 + 3 M23 + 12 FASE4.5 + auditor + contrato); `MAGIC_LINK_OTP_REQUIRED` = Set de 21 que exigen OTP; `isMagicLinkActive()` puro FE. `glosario-ens.ts`: **134+ entradas** cliente-friendly (ENS normativo, MAGERIT, eIDAS/firma, Auth) con tuteo y analogías.

### Mock data (`mock.ts`) — ⚠️ contradice R24
`MOCK_KPIS/MY_DAY/ALERTS/ACTIVITY/LEADS`. `useLeads` tiene **mock-fallback activo en producción** (BD vacía → `MOCK_LEADS`); `useCreateLead()` es **100% mock** (UUID con `Math.random()`). `DashboardKpis` marcado «not yet in backend».

### Módulos `lib/api/*` (muestra)
`remediation-admin` (catalog/jobs/authorize/execute/grantWrite) · `remediation-client` (⚠️ usa `api` no `clientApi`) · `cloud-connectors-admin/client` (sync/gaps/diagnosis/requestDisconnect chat-mediated ADR-014) · `signing` (createIntent/requestOtp/signIntentCanvas/listPending) · `audit-accompaniment` (advanceState/uploadArtifact) · `simulacro-pre-enac` · `audit-dry-run` · `dda-evidence-gaps` (auditor+admin) · `notifications-dlq`. Helpers: `adaptive-dashboard` (10 fases), `labels.ts` (enum→ES), `cookies/*` (consent RGPD + inventario AEPD 2020), `inline-agents/` (10 agentes inline cliente a04..a31).

### Medidas ENS
`op.acc.5/6` (cloud M365, `ztna_mfa_obligatorio`) · `mp.s.2` (sharing SharePoint/GDrive) · 73 medidas vía `dda-evidence-gaps.ts` · eIDAS Art.25.1 (`signing.ts` Ed25519+OTP, 21 purposes) · R6 hash-chain · ENAC (state machine acompañamiento).

### Discrepancias CLAUDE.md vs código
1. **Purposes**: doc «23» → `magic-link-types.ts` tiene **36**.
2. **L3 redirect**: doc describe auto-redirect a `lastUsedProjectId`; el código lo **retiró** (admin siempre a `/admin/projects`).
3. **OPS-044 base clientApi**: doc dice `/segment`; el código usa `/api/v1`.
4. **R24 «0 mocks»**: `useCreateLead` 100% mock + `useLeads` mock-fallback en prod.
5. **`remediation-client.ts`** usa `api` no `clientApi` (anomalía OPS-044 no documentada).


## 86 - Frontend - hooks, UI primitives, shared, layout, design system

**Alcance**: 62 hooks (todos), 17 layout components (todos), 28 UI primitives (todos), agents/brand/auth/data/copiloto/ (muestra). ~4.200 LOC leídas directamente.

---

### Hook SSE central: `useClientProjectEvents` (548 LOC)

Usa `EventSource` nativo con `withCredentials:true` → `/api/v1/client-portal/projects/{id}/events`.

**27 tipos de evento** en union `ClientSseEventType`: workflow (step_*), cloud remediation (6), sync admin→cliente (m01/m02/m17), cloud connectors (5), client_notification.created, chat_message_new, firma (signing.*), phase_changed, document.uploaded, continuidad.draft_ready, retainer.checkin.sent, accompaniment.state.advanced, heartbeat.

**Patrón subscribe-refetch**: `invalidateQueries` centralizado por tipo (signing → `pending-signatures`+`signing-history`; notification → `client-inbox`; chat → `client-chat`; phase → `portal-workflow`+`client-workflow-guide`).

**Gaps**:
- `accompaniment.state.advanced` registrado como listener y en la union, pero **sin `onAccompanimentStateAdvanced` callback en `UseClientProjectEventsOptions`** ni invalidateQueries automática — incompleto respecto al patrón uniforme.
- **No implementa `Last-Event-ID`**: el backend (Ejecutable 6) emite `id:` en frames SSE y tiene ring-buffer de 100 eventos, pero el frontend NO envía `Last-Event-ID` al reconectar. Eventos perdidos durante gap de reconexión se pierden en cliente.

**Auto-reconnect**: delegado al browser (`onerror` es no-op). Adecuado MVP.

---

### Otros hooks SSE

| Hook | Patrón | Endpoint |
|------|--------|----------|
| `useInboundWhatsAppSSE` | EventSource, mode admin/client | `/api/v1/admin/whatsapp/threads/{id}/sse` |
| `useMeetingSSE` | `fetch` + ReadableStream manual (POST) | `POST /api/v1/agents/18/meeting-update/stream` |

`useMeetingSSE` usa fetch porque el backend requiere POST con payload grande — correcto.

---

### Hooks TanStack Query (muestra)

OPS-044 sostenido: admin usa `api` (BASE `/api/v1/...`), cliente usa `clientApi` (BASE `/segment`).

| Hook | staleTime | Notas |
|------|-----------|-------|
| `useClientNotifications` | inbox 30s, unread 15s | refetchInterval activo |
| `useClientDashboard` | — | useState + setInterval 30s; NO TanStack; cancelRef cleanup |
| `useWorkflowAdmin` | 30s | 5 queries (phase/actions/progress/tasks/roadmap) |
| `useRemediationAdmin` | catalog 5min, jobs 10s | mutations c/ invalidateQueries |
| `useAutopilot` | polling 2s en `authorized|running` | refetchInterval condicional; keys centralizadas |
| `useCopilot` | — | fetch streaming Agent 14; abortRef cancelación |
| `magic-link/index` | — | 5 hooks TanStack (list/generate/status/consume/revoke) |

`useClientDashboard` usa patrón propio (no TanStack), comentado como intencional por consistencia con siblings `useActasClient`/`useDdaClient`.

---

### Layout components

**`FulkroFooter`**: importa `FULKRO_IDENTITY` de `lib/fulkro-identity`. WCAG 2.2 AA: `role="contentinfo"`, `aria-label` en cada enlace, iconos `aria-hidden`. `data-testid="fulkro-footer"`.

**`GlobalFulkroFooter`**: suprime footer en `/auditor-portal`, `/pentester-portal`, `/remediation`, `/verify-auth` (tienen chrome propio).

**`ActiveProjectSync`**: ADR-054 implementado. Sync Zustand `active-project-store` con URL param `projectId`. Query `["project-composer","header",projectId]` staleTime 60s. Error → `clearActiveProject` + toast + redirect. También sincroniza `copilot-store.panelContext` y limpia mensajes copiloto al cambiar proyecto. Retorna null (lógica pura).

**`Header`** (admin): `ThemeToggle` importado pero comentado (`TODO-FE-DARK-MODE-COMPLETO-001`). Componente `ThemeToggle.tsx` existe con botones `disabled`+`aria-disabled`. Consistente con `Future-1.F.dark-mode-completo`.

**`HeaderProjectChip`**: visible solo en `/admin/projects/*`. Badges de categoría con `chromeClass` hardcodeado para contraste AA sobre topbar oscuro (fix 2026-06-09).

**`ActiveProjectBanner`**: sidebar admin. Branding per-cliente via `getClientBranding` con `retry:false`. Valida hex color con `/^#[0-9A-Fa-f]{6}$/` antes de `borderLeft` inline. `ProjectSwitcherDropdown` integrado.

**`ClientPortalChrome`**: wrapper layout cliente. Rutas públicas sin chrome. Monta `AuthGuard`, `ClientBrandingProvider`, `ProjectFeaturesProvider`, `CopilotoDock`, `CoachNextStepStrip`, `OnboardingTutorial`.

**`CommandPalette`**: usa `cmdk`. Registra `Ctrl+K`/`Cmd+K` via `keydown`. Sin personalización (Future-1.E.2.advanced-switcher).

---

### UI primitives

| Componente | Variantes clave | WCAG |
|---|---|---|
| `Button` | primary(gradient)/secondary/accent/outline/ghost/link/danger · 4 sizes | focus-visible ring fulkro-primary-700 |
| `Badge` | 8 variantes; success/warning/info -700 shades ≥4.74:1 AA | fix 3B-2B.2 Phase A.1 |
| `Alert` | info/success/warning/danger; texto -700 | `role="alert"` · fix 2026-06-09 |
| `DataTable` | sort/filter/pagination/skeleton | sort `aria-label` fallback a `column.id` · WCAG 2.4.4 fix |
| `TooltipENS` | term (glosario) / text libre / docLink | min 24×24px tap target; focus ring |
| `InfoTag` | underline dotted + Info icon inline | wraps TooltipENS |
| `Stepper` | horizontal · `ol`+`li` · check completo | `aria-label="Wizard progreso"` |
| `ThemeToggle` | tri-state todos disabled | `aria-disabled` correcto |

**`DataTable`**: cabeceras no ordenables tienen botón `disabled` — evita focus inutilizable. Fix 3B-2B.2/3 sostenido.

---

### Design system tokens

Tailwind extendido: `fulkro-primary-{50..900}`, `fulkro-ink-*`, `fulkro-success/warning/info/danger`. Clases custom `btn-action`, `btn-outline-fulkro`. CSS var `--fulkro-topbar-gradient` en Header. Pattern #1 (sidebar `::before` gradiente, no `bg-image`) sostenido — axe-core no evalúa `bg-image` para contraste.

---

### Discrepancias CLAUDE.md vs código real

1. **"Pattern #21 event_id replay sostenido"** — backend implementa ring-buffer y `id:` en frames SSE; frontend **NO envía `Last-Event-ID`** al reconectar. Brecha real: eventos perdidos en gap de reconexión se descartan.
2. **"FulkroFooter cross 4 portales"** — en realidad cubre admin + cliente directamente. Portales token-gated (`auditor-portal`, `pentester-portal`) tienen chrome propio; `GlobalFulkroFooter` los excluye explícitamente. La afirmación "4 portales" es imprecisa.
3. **`accompaniment.state.advanced`** en union y listener pero sin callback option en `UseClientProjectEventsOptions` — gap de completitud.

---

### Veredicto: **completo**

Hooks SSE y TanStack, layout (ADR-054/R29/R30) y primitivas UI implementados y en producción. WCAG AA sostenido en Badge/Alert/DataTable post-fixes. Gap no-bloqueante: frontend no consume `Last-Event-ID` (backend listo, cliente no lo aprovecha).


## 90 - Tests backend (554 ficheros)

### Metrica real verificada

| Metrica | Valor empirico |
|---|---|
| Ficheros `test_*.py` | **554** |
| Funciones `def test_*` totales | **5.642** |
| Ficheros Python en `tests/` (incluyendo conftest, __init__) | **628** |
| Subdirectorios de test | **67** |

> DISCREPANCIA: CLAUDE.md afirma "~353 archivos test_*.py". Empirico: **554** (+57%). La diferencia refleja el crecimiento de sesiones 3B-2B.7-11, Ejecutables 4-8 y m_remediation (ADR-055) añadidos tras la redaccion del CLAUDE.md.

---

### Distribucion por area

| Area | Ficheros | Funciones |
|---|---|---|
| `motors/` (47 subdirs) | 401 | **4.190** |
| `agents/` | 31 | 362 |
| `core/` | 23 | 253 |
| `notifications/` | 15 | 149 |
| `api/` | 14 | 113 |
| root-level `test_*.py` | 9 | 135 |
| `billing/` | 8 | 78 |
| `auth/` | 8 | 65 |
| `corpus/` | 8 | 56 |
| `audit_fixes/` | 8 | 50 |
| `security/` | 7 | 46 |
| `mcp_servers/` | 2 | 39 |
| `middleware/` | 2 | 19 |
| `integration/` | 6 | 18 |
| `scripts/` | 3 | 18 |
| `models/` | 3 | 17 |
| `admin_settings/` | 4 | 23 |
| `services/` + `clients/` | 2 | 10 |

---

### Ficheros clave de infraestructura

- `conftest.py` — fixture raiz: `db` (transaccion rollback sobre `fulkro_test`), `async_client` (ASGI+httpx), `analysis_factory`, `patched_settings`, `auth_override_default` (autouse · stub Marcos owner · opt-out via `@pytest.mark.real_auth`)
- `conftest._admin_setup()` — `SET LOCAL ROLE fulkro_app_bypassrls` para setup · `RESET ROLE` → RLS vuelve para el SUT
- `conftest.setup_test_project()` — helper global crea `clients` + `projects` + `set_config app.current_{project,client}_id`
- `tests/fixtures/` — solo corpus datos XML/SQL (`corpus_seed.sql.gz`, pilar_compat XML); NO hay factories Python aqui

---

### Patron RLS multitenancy

- BD de test = `fulkro_test` (reescritura de `DATABASE_URL` en conftest)
- Rol SUT = `fulkro_app` (NOSUPERUSER): RLS enforced
- `test_rls_multitenancy.py` (8 tests): 2 tenants A/B, verifica invisibilidad cross-tenant en `systems`, `projects`, `magerit_analysis`
- `security/test_audit_log_rls_isolation.py` (4 tests): audit_log 3-way OR (project_id OR client_id OR NULL legacy) — Sub-atom 5.A
- `security/test_cross_portfolio_isolation.py` (5 tests): aislamiento cross-portfolio
- `motors/m_cloud_connectors/test_rls_cloud_connectors.py` (3 tests)

---

### Patron mock LLM (suite fiable)

`conftest.py` L52: si `FULKRO_RUN_LLM_TESTS != "1"` → `ANTHROPIC_API_KEY = ""` → `_call_llm()` usa `_mock_response` interno. Evita stalls TLS en CI. Opt-in real con `FULKRO_RUN_LLM_TESTS=1`. `pytest.mark.llm` salta automaticamente via `pytest_collection_modifyitems`. 41 lineas `pytest.skip(...)` condicionadas a API key.

---

### Cobertura por motor (top 15)

| Motor | Funciones | Que se prueba |
|---|---|---|
| `m08_verification` | 240 | autopilot pipeline, finding state machine, SARIF parsers, LLM classifier, Prowler/ScoutSuite/OpenVAS, kill switch, retest loop, SSH crypto, zfp engine |
| `m21_portal_cliente` | 194 | auth flow real (WebAuthn mock), MFA TOTP, magic-link gating, RLS, SSE feed |
| `m_cloud_connectors` | 165 | gap engine (determinista, idempotente, B/M/A), remediation orchestrator+API, RLS, MAGERIT enrich, conformity score |
| `m09_audit_prep` | 154 | DdA generation, evidence matrix, ENAC gaps, draft report PDF (reportlab), simulacro pre-ENAC |
| `m13_commercial` | 109 | lead→propuesta→contrato, contract signing canvas, floor elevation service |
| `m11_copiloto` | 109 | RAG context, role-aware prompts, rate limiting, personas, RLS copilot_memory |
| `m06_document_factory` | 104 | templates library (96 plantillas), Gantt planner, PDF signing wire-in |
| `m23_retainer` | 91 | lifecycle, auto-trigger post audit_passed, pricing tiers |
| `m30_client_contacts` | 89 | contactos CRUD, deduplicacion |
| `m_workflow_engine` | 76 | engine state machine, deliverables, blocking gates |
| `m27_conformity` | 75 | E-041 conformidad, DdA vs evidence gaps, hash chain integrity |
| `m16_onboarding` | 74 | wizard, OAuth cloud link, SSE events |
| `m24_idms` | 73 | MinIO storage_path prefix `minio://`, WORM archival, version lock |
| `m18_communication` | 69 | email templates, DnD preferences |
| `m14_contracts` | 63 | contrato CRUD, adendas, audit trail, signing intent |

`m_remediation` (60 funciones, 7 ficheros): catalog policy (risk tiers SAFE_AUTO/GUARDED/BLOCKED determinista), kill switch 3 capas, cloud writers AWS (moto) + M365/Azure/Google (respx simulador), API activacion.

---

### Tests de seguridad (pentest-grade)

`security/` ~50 funciones:
- `test_llm_prompt_injection.py` (21 tests): 8 categorias violacion — pure functional sin DB
- `test_pentest_admin_escalation.py` (4+parametrize, `real_auth`): endpoints admin rechazan sin auth (401/403, NUNCA 200/500)
- `test_pentest_cliente_impersonation.py` (4+parametrize, `real_auth`): impersonacion cross-cliente rechazada
- `test_pentest_csrf_triple_binding.py` (parametrize): POST sin CSRF → 401/403/422
- `test_pentest_magic_link_replay.py` (parametrize): token invalido → 401/403/404

`auth/` 65 funciones: `test_auth_api.py` (32 tests real_auth): TOTP enroll, WebAuthn mock, JWT ticket flow. `test_rbac_per_endpoint.py` (9 tests): ADR-013 doble pool admin vs cliente.

Nota: todos los ficheros `test_pentest_*.py` usan `@pytest.mark.parametrize` → grep anchored `^def test_` da 0 (falso negativo). Las funciones existen y son ejecutables.

---

### Tests hash chain R6

- `security/test_audit_log_rls_isolation.py`: llama `fn_audit_log_verify_chain` post-insert, verifica `ok=True`
- `motors/m05_signing/test_signing_history.py` (4 tests): `event_hash_sha256` + `previous_signature_hash` chain link
- `motors/m_cloud_connectors/test_remediation_orchestrator.py`: audit_log emit 3-way OR preserved

---

### Tests corpus / ENS normativo

`corpus/` 56 funciones: `test_rd311_parser.py` (14): parsing RD 311/2022 Anexo II — 73/68/52 medidas por nivel. `test_corpus_catalog.py` (10): catalogo ENS codes. `test_hybrid_search.py` (8): BM25+pgvector. `test_rd311_vector.py` (5): embeddings e5-large.

ENS codes en assertions: `op.acc.1`, `op.acc.5`, `op.acc.6`, `op.exp.3`, `op.exp.4`, `mp.if.3`, `mp.s.2`, `org.2`, `org.3`, `mp.com.*`

---

### Areas debiles / gaps

- `m_siem/`: 4 funciones unicas (motor funcional pero subrepresentado)
- `integration/`: 18 funciones — scaffolds respx/mock, sin cuentas cloud reales
- `services/` + `clients/`: 10 funciones combinadas (escasa cobertura)
- `models/`: 17 funciones — sin tests de migration drift
- Autouse stub `auth_override_default` → cobertura RBAC granular solo en 5 ficheros `real_auth`

---

### Hallazgos de consistencia

1. `m05_obligations/` y `m05_signing/` son directorios separados (65+36 funciones). CLAUDE.md los trata como un motor unico `m05_signing`.
2. `m10_audit_sim/test_m10_audit_sim.py` tiene 35 funciones (no cero — falso positivo por grep anchored con funciones dentro de clases).
3. La suite reporta ~5.956 tests PASS (memoria CLAUDE) vs 5.642 funciones `def test_` — diferencia por `@pytest.mark.parametrize` que multiplica N casos por funcion.

---

### Veredicto

**Completo** para motores nucleares (m08, m09, m21_portal, m_cloud_connectors, m13, m11, m05_signing). **Parcial** para seguridad pentest (scaffolds funcionales, cobertura limitada). **Mixto** en integracion (mocks vs binarios reales). Suite production-correct: BD reproducible desde migraciones, RLS enforced, LLM mock-by-default.


## 91 - Tests E2E Playwright (3 niveles, axe a11y)

### Inventario real (verificado filesystem 2026-06-13)

| Ubicacion | Specs | Notas |
|---|---|---|
| `tests/e2e/` top-level `.spec.ts` | 67 | flujos funcionales: login, separacion-portales, auditor, sim-medio-*, mb*, san_e_v3/* |
| `tests/e2e/fase_*/` (24 dirs) | 135 | fases acumulativas fase_9/10/11/12/17-27/30-39/41/43 |
| `tests/polish/probe/` | 5 | smoke admin 5 paginas |
| `tests/polish/p1/` | 14 | admin project-scoped P1 |
| `tests/polish/p2/` | 35 | admin top-level P2 |
| `tests/polish/p3/` | 21 | admin P3 adicionales |
| `tests/polish/cliente/` | 10 | portal cliente 10 paginas |
| `tests/polish/auditor-portal/` | 12 | portal auditor 12 secciones |
| **TOTAL** | **299** | 202 e2e funcional + 97 polish a11y |

**Fases ausentes (huecos numericos)**: 13, 14, 15, 16, 28, 29, **40**, 42.

---

### Configuracion Playwright (2 configs)

**`playwright.config.ts`** (E2E funcional)
- `testDir: ./tests/e2e`, `globalSetup: _helpers/global-setup.ts`
- `timeout: 30_000`, `fullyParallel: false`, `retries: 0`
- `webServer`: `npx next start -p 3100` (prod build, `reuseExistingServer: !CI`), solo Chromium.

**`playwright.polish.config.ts`** (a11y 12-criterios)
- `testDir: ./tests/polish`, `timeout: 60_000`, `workers: 4`, `fullyParallel: true`
- `screenshot: "on"` always-on; HTML report en `polish-report/`.
- 6 viewports (375-1920) manejados dentro de cada spec.

---

### Auth helpers y globalSetup

**`global-setup.ts`**: `POST /api/v1/_dev/create-test-client` + `POST /api/v1/_dev/seed-rich-demo-project` (proyecto fijo UUID `00000000-...-000000000001`). Sin el proyecto sembrado, ~38 specs project-scoped fallan en cascada.

**`auth-real.ts`** — autenticacion real backend:
- `loginAsMarcos(context)`: `POST /api/v1/_dev/login-as-marcos` → cookies `fulkro_session + fulkro_csrf` → `addInitScript` para 3 guards: `fulkro_admin_tour_completed`, 9 flags `fulkro_copilot_guided_dismissed_*`, blob Zustand `fulkro-active-project` (ADR-054).
- `loginAsClient(page)`: form fill real `/client-portal/login` con `test-client-e2e@example.com` / `TestP@ssw0rd123!`; inyecta `fulkro_tutorial_completed` post-login.

**`helpers.ts`** (legacy): `mockAuthenticated(page)` — mock antiguo sin BD, cookies sinteticas + stub `/auth/me`. Coexiste con `auth-real.ts`; specs antiguas (pipeline, meetings) siguen usandolo.

**`project-shell.ts`**: `mockProjectShell(page, opts)` — stubbea `/projects/{id}/header` + `/feature-flags` para specs con projectId sintetico que de otro modo activan redirect al selector.

---

### Sistema axe-core 12-criterios (polish)

**`audit-helpers.ts`** nucleo:
- `runAxeScan`: `@axe-core/playwright` tags `wcag2a/aa, wcag21a/aa`. Retorna violaciones con `id, impact, nodeCount, nodes[0..2]`.
- `checkNoHorizontalOverflow`: `scrollWidth <= viewportWidth` por viewport.
- `captureTabOrder(maxTabs=50)`: Tab programatico, anti-flaky CI (6 intentos, re-Tab si foco en body).
- Intercept helpers: `interceptRouteSlow`, `interceptRoute500`, `interceptRouteEmpty`.

**12 criterios** — 5 REAL / 2 PARCIAL / 5 STUB:
- REAL: `mobileResponsive` (overflow 6vp), `wcagAA` (axe critical/serious=0), `keyboardNav` (tabOrder+focusIndicator), `projectContext` (breadcrumb data-testid), `titleBreadcrumb` (main h1/h2).
- PARCIAL: `ctaVisible` (botones en main), `helpTooltip` (aria-describedby).
- STUB siempre `true`: `loadingSkeleton`, `errorRetry` (`retryButtons>=0`), `emptyState`, `tanstackQuery`, `serverFeedback` (`toastContainer>=0`).

**Gate CI**: `wcagAA && mobileResponsive && keyboardNav && passCount >= 9/12`.

**Templates reutilizables**:
- `runProjectScopedProbe` — admin project-scoped (detecta redirect post-networkidle 800 ms).
- `runTopLevelAdminProbe` — admin global (`isProjectScoped: false`).
- `runClientPortalProbe` — portal cliente (R29 isolation, no breadcrumb).
- `runAuditorPortalProbe` — requiere `AUDITOR_PORTAL_TOKEN` env; skip automatico si ausente. Soporta OTP step-up via `AUDITOR_PORTAL_OTP`.

---

### CI Workflow (`admin-polish-empirical.yml`)

3 jobs independientes (trigger PR/push `main` paths `frontend/**`):

| Job | Paginas | Timeout |
|---|---|---|
| `polish-empirical` (admin) | 75 specs probe+p1+p2+p3 | 60 min |
| `cliente-polish-empirical` | 10 specs | 45 min |
| `auditor-polish-empirical` | 12 specs (token via `/_dev/auditor-portal-token`) | 45 min |

Caracteristicas CI: claves Ed25519 **efimeras por run** (`openssl genpkey → GITHUB_ENV`), sin secretos de repo. BD: `pgvector:pg16`, extensiones subset (uuid-ossp, pgcrypto, vector; SIN age/pgaudit). Backend: `uvicorn` repo root, rol `fulkro_app` asyncpg con RLS.

**E2E funcional en `ci.yml`**: `if: github.event_name == 'workflow_dispatch'` — los 202 specs funcionales solo corren **manualmente**, NO en PR automatico.

---

### Flujos ENS cubiertos (muestra)

- `sim-medio-full-cloth-e2e.spec.ts`: ciclo completo ENS MEDIO (lead → contrato → DdA → plan → evidencias → auditoria).
- `sim-medio-capstone-e2e.spec.ts`: galeria 100% implantado 3 actores.
- `auditor-portal-full-flow.spec.ts`: 9 pasos CLUSTER 2+3 ENAC (scaffold, requiere TOKEN).
- `mb15_simulacro_pre_enac.spec.ts`: Simulacro Pre-ENAC ejecutable 5.
- `mb14_admin_audit_chain.spec.ts`: hash chain audit_log R6 SHA-256.
- `fase_43/contract-canvas-sign-flow.spec.ts`: firma canvas Ed25519 contrato comercial.
- `pentest-authorization-cliente-e2e.spec.ts`: OTP step-up ADR-020.
- `m01-categorizacion-sync.spec.ts` / `m02-magerit-sync.spec.ts`: SSE sync M01/M02.

---

### Gotchas y deuda tecnica

1. **Bloqueante local OPS-052 72**: backend arrancado sin `FULKRO_AUTH_PRIVATE_KEY` cargado genera clave efimera → JWT mismatch con `PUBLIC_KEY` frozen frontend → portal cliente redirige a login infinitamente. CI resuelto (claves efimeras generadas en mismo run); LOCAL sin helper de reinicio.
2. **Criterios 2,3,4,8,11 siempre `true`**: `loadingSkeleton`, `errorRetry`, `emptyState`, `tanstackQuery`, `serverFeedback` no tienen verificacion real — `passCount >= 9` trivialmente alcanzable incluso en paginas rotas.
3. **`helpers.ts` legacy coexiste con `auth-real.ts`**: specs antiguas con mock no detectan regresiones de autenticacion real.
4. **36 archivos con `test.skip`** (67 ocurrencias): flujos auditor-portal y fas_43 dependen de env vars externas; saltean silenciosamente en entornos sin ellas.
5. **`san_e_v3/` no diferenciado en CLAUDE.md**: 26 specs mb1-mb8 (logout, exit-checklist, financial, discovery, dashboard-3niveles, copilot, tutorial, notificaciones, whatsapp) con estructura propia.


## 92 - Infra & Deploy (Docker, Hetzner, CD, backups, hardening)

### Servicios Docker

#### Dev (`docker-compose.yml`) — servicios principales

- `postgres` `fulkro/postgres:pg16` (custom) → puerto 5433; sin `archive_mode`; healthcheck pg_isready
- `redis` `redis:7-alpine` → 6379; sin `requirepass` en dev; credenciales hardcodeadas
- `minio` `minio/minio:latest` → 9000/9001; credenciales `changeme123` hardcodeadas
- `clamav` `clamav/clamav:stable` → 3310; siempre arranca (sin profile); cold-start 180 s
- `celery-worker/beat` → profile `workers` (opt-in)
- `fulkro-scanner` `zaproxy/zap-stable:2.15.0` → profile `scanner`; ZAP daemon API 8090
- 14 servicios MCP pentest → profile `pentest`; red interna `172.30.0.0/24`; OpenVAS 8 GB RAM
- **No existe contenedor fastembed** — embeddings in-process (ver discrepancias)

#### Prod (`docker-compose.prod.yml`) — servicios

| Servicio | Imagen | Observaciones clave |
|----------|--------|---------------------|
| `postgres` | `fulkro/postgres:pg16` | `archive_mode=on`, `wal_level=replica`, WAL archiving pgBackRest; puerto NO expuesto |
| `redis` | `redis:7-alpine` | `requirepass` desde env; `appendonly yes`; puerto NO expuesto |
| `provision` | `fulkro/backend:prod` | One-shot (`restart: "no"`); orden inviolable 7 pasos |
| `backend` | `fulkro/backend:prod` | 4 workers uvicorn; `vardata` compartido con celery; alias red `app` |
| `frontend` | `fulkro/frontend:prod` | Next.js 14; `FULKRO_BACKEND_URL=http://backend:8000` |
| `minio-init` | `minio/mc:latest` | One-shot; 7 buckets + WORM Object Lock 7 años |
| `caddy` | `caddy:2` | 80/443/443-udp; TLS Let's Encrypt auto |

Volúmenes prod: `pgdata`, `pgbackrest_repo`, `redisdata`, `miniodata`, `clamavdata`, `caddydata/config/logs`, `vardata` (compartido backend+celery).

---

### Imágenes Docker

**PostgreSQL custom** (`Dockerfile.postgres`): base `pgvector/pgvector:pg16` + `postgresql-16-pgaudit` (apt) + Apache AGE compilado (`PG16/v1.5.0-rc0`) + `pgbackrest` (apt). Extensiones: `uuid-ossp`, `pgcrypto`, `vector`, `age`, `pgaudit`. Funciones RLS: `current_client_id()`, `current_project_id()`.

**Backend** (`infra/docker/Dockerfile`): `python:3.12-slim`; herramientas pentest ligeras (`nmap`, `testssl.sh` con symlink HOTFIX debian-trixie, `lynis`, `tesseract-ocr-spa`, `libreoffice-writer-nogui`); Go binaries `nuclei` v3.3.0 / `httpx` v1.6.9 / `subfinder` v2.6.6 (best-effort); `prowler-cloud==4.0.0` + `semgrep` (best-effort); build verifica herramientas obligatorias con `which`; copia `backend/`, `frontend/`, `docs/`.

**Frontend** (`frontend/Dockerfile`): multi-stage deps→build→runtime; `FULKRO_AUTH_PUBLIC_KEY` inyectada en **runtime** (NO build-arg) — JWT verify es server-side.

---

### Roles PostgreSQL (`init-roles.sql`)

- `fulkro`: SUPERUSER — solo migraciones/seed
- `fulkro_app`: NOSUPERUSER, LOGIN — runtime RLS enforced; **NO** miembro de `fulkro` (escalada cerrada 2026-06-07)
- `fulkro_app_bypassrls`: NOSUPERUSER, NOLOGIN, BYPASSRLS — asumido vía `SET LOCAL ROLE` para admin cross-tenant
- `fulkro_migrate`: NOSUPERUSER, LOGIN, BYPASSRLS — Alembic; miembro de `fulkro` (ALTER TABLE) y de `fulkro_app_bypassrls` (seed)

`REVOKE fulkro FROM fulkro_app` idempotente. `REVOKE UPDATE,DELETE ON audit_log` en provisión (R6). `GRANT SET ON PARAMETER session_replication_role TO fulkro_app_bypassrls` (PG15+, silencioso si <15).

---

### Provisión one-shot (`provision-entrypoint.sh`)

7 pasos: extensions → functions → roles → `ALTER USER` (alinea passwords dev→prod) → `alembic upgrade head` (como `fulkro_migrate`) → re-GRANT DML → `seed_all_fulkro` + `REVOKE UPDATE,DELETE ON audit_log` (R6). Idempotente. El comentario interno dice head `client_mfa_email_code_001`; el real es `unify_pricing_fiscal_rls_001` (discrepancia).

---

### Buckets MinIO (`minio-init.sh`)

7 buckets: `fulkro-documents`, `fulkro-evidence`, `fulkro-exports`, `fulkro-corpus`, `backup-vault-fulkro`, `fulkro-admin-assets` (public-read), `fulkro-evidence-worm` (**Object Lock COMPLIANCE 2555d** si no existe; NO recreable post-creación).

---

### Caddy prod (`Caddyfile.prod`)

`fulkro.es/www` → landing + `/api/v1/public/contact` → backend. `app.fulkro.es`: `/api/*` → `app:8000` (SSE: `flush_interval -1`), resto → `frontend:3000`. Headers: HSTS 2a preload, `nosniff`, `X-Frame-Options DENY`, oculta Server. `request_body max_size 100MB`. **Rate-limit desactivado** (requiere `xcaddy --with caddy-ratelimit` no incluido en `caddy:2` estándar).

### pgBackRest

Repo 1 local: AES-256-CBC (passphrase env), retención 4 full/12 diff, zstd-6, WAL async, spool `/var/spool/pgbackrest`. **Repo 2 S3 Hetzner: íntegramente comentado** — backup offsite no activado. `pg1-user=postgres` vs superuser real `fulkro` en contenedor (discrepancia). Cron prod manual (no en repo): `pg_dump` 03:30, pgBackRest 03:45.

---

### CI/CD (GitHub Actions)

- `ci.yml`: lint (ruff, bloquea) + typecheck (mypy, `continue-on-error: true`, **NO bloquea**) en todo PR; `test`/`playwright` solo `workflow_dispatch` — **inactivos en PR automático**. CI usa `pgvector/pgvector:pg16` (sin AGE/pgAudit).
- `deploy.yml`: `git pull --ff-only` + `docker compose build` + `up -d --remove-orphans`; SSH Ed25519; `concurrency cancel-in-progress: false`; omite limpio si no hay secrets.
- `security-scan.yml`: bandit (gate HIGH+HIGH), safety (gate CRITICAL), npm-audit (gate critical, `--production`); cron Mon 06:00.
- `admin-polish-empirical.yml`: Playwright + axe-core; 75 admin + 10 cliente + 12 auditor specs; 3 jobs; trigger push/PR `frontend/**`.

---

### Gestión de secretos

`generate-prod-secrets.sh` → `.env.prod` (modo 600, gitignored): 3 pares Ed25519 (auth JWT con pública **derivada** en mismo proceso, magic-links, backup) + 3 claves documentales M05/M06/M07 persistentes cross-recreate (FIX P0-1) + passwords PG hex48 + Redis/MinIO/Fernet. Placeholders manuales: `ANTHROPIC_API_KEY`, SMTP, `BACKUP_S3_*`. Guard: rechaza escribir sobre `.env`/`.env.local`.

### Gate post-deploy (`verify-deploy.sh`)

13 checks: DB-1..4 (roles/escalada), AL-1 (1 head `unify_pricing_fiscal_rls_001`), ENS-1/2 (52/68/73 + op.exp.10), R6-1/2 (hash chain + append-only), MIO-1 (WORM), SVC-1 (healthy), API-1/FE-1 (HTTP 200). Modo `dev` valida SQL contra `fulkro_test`.

---

### ENS medidas cubiertas

| Código | Mecanismo |
|--------|-----------|
| `mp.s.5` | ClamAV TCP 3310 (dev+prod) |
| `op.exp.10` | Ed25519 estables por env; gate ENS-2 en verify-deploy |
| `op.cont.2` | pgBackRest PITR + pg_dump diario + MinIO backup-vault |
| `mp.si.5` | MinIO Object Lock COMPLIANCE 7y (evidencias WORM) |
| `op.acc.4` | 4 roles PG, privilegio mínimo, sin escalada superuser |
| `mp.com.4` | Caddy TLS Let's Encrypt + HSTS 2a preload |
| `op.mon.1` | audit_log inmutable hash-chain R6 + pgAudit |
| `mp.s.2` | Red interna `fulkro-net`; PG/Redis/MinIO sin exposición externa |

---

### Discrepancias CLAUDE.md vs código real

1. **Alembic head inconsistente**: `provision-entrypoint.sh` y `deploy-hetzner.sh` referencian head `client_mfa_email_code_001`; el real es `unify_pricing_fiscal_rls_001` (confirmado en `verify-deploy.sh` y árbol de migraciones). Log engañoso, no bloquea (`alembic upgrade head` usa el grafo real).
2. **Stack menciona fastembed `:8080`**: contenedor TEI eliminado 2026-06-10; embeddings in-process con `fastembed` Python lib. Código correcto; CLAUDE.md Stack desactualizado.
3. **`run_backup.sh` hardcodea `changeme123`**: script legado (línea 30) con credenciales dev hardcodeadas + path `/root/fulkro`. No eliminado; falla en prod real.
4. **fail2ban/auditd no como código**: activos en servidor según MEMORY, sin ficheros en el repo — configuración manual, no IaC.
5. **Gate CI test inactivo en PR**: `test` y `playwright` son `workflow_dispatch` only — PRs a main mergeables sin tests.
6. **`pg1-user=postgres` en pgbackrest.conf**: cluster usa superuser `fulkro`; requiere ajuste manual antes de `stanza-create`.
7. **pgBackRest repo2 S3 comentado**: MEMORY afirma "pgBackRest PITR activo" pero el backup offsite está íntegramente comentado; solo repo1 local existe.


## 95 - Spec & cobertura ENS (verdad sobre 52/68/73 medidas, catálogo entregables)

### Fuente única de verdad: `anexo2_rd311_2022.py`
`backend/app/motors/m03_dda/anexo2_rd311_2022.py` (168 LOC) — transcripción literal del **BOE-A-2022-7191** (Anexo II RD 311/2022), verificada celda a celda el 2026-06-07:
```python
TOTAL_MEDIDAS = 73   # 4 org + 33 op + 36 mp
APLICA_BASICA = 52 ; APLICA_MEDIA = 68 ; APLICA_ALTA = 73
```
Verificación directa: `(True,True,True)`=**52** (BÁSICA) · `(False,True,True)`=16 · `(False,False,True)`=5 → MEDIA 52+16=**68** ✓ · ALTA 52+16+5=**73** ✓. No existe ninguna entrada que aplique a un nivel inferior y no a uno superior (aplicabilidad monótona — correcto).

### Corrección RD 3/2010 → RD 311/2022
Las semillas históricas arrastraban numeración derogada. Correcciones verificadas: `op.exp.11`→`op.exp.10` (claves cripto), `mp.s.8`→`mp.s.4` (DoS), `op.acc.7`→`op.acc.6`; nuevas RD 311: `op.nub.1`, `op.mon.3`, `mp.eq.4`, `op.ext.3/4`. Guard `test_anexo2_rd311_authoritative.py` falla CI si reaparecen códigos derogados.

### Catálogo YAML vs DB
`docs/catalogs/ens_measures_catalog_v1.yaml` declara **79 entradas** (73 + 6 residuos RD 3/2010: `op.exp.11`, `mp.s.8/9`, `mp.if.9`, `mp.per.9`, `mp.com.9`). El seed filtra `_NON_OFFICIAL` → **73 rows**; `resolve_entries()` sobrescribe nombre+aplica_*+fuente desde `ANEXO_II_RD311`. Test `test_exactly_73_measures_loaded` valida `COUNT(*)=73`.

### Modelo de datos ENS (ORM)
| Tabla | RLS | Notas |
|---|---|---|
| `ens_measures` | NO (global) | 73 rows · booleans `aplica_basica/media/alta` |
| `dda_entries` | `project_id` | 1 por medida×proyecto · `ClientReviewMixinA` |
| `annual_review_records` | `project_id` | revisión anual CCN-STIC 808 |
| `ens_measure_refuerzos` | NO | refuerzos **R1-R5** (`+R6` no existe en Anexo II) · `applicable_categories` JSONB · `source_chunk_id`→corpus |
| `ens_measure_dimensiones/guias_ccn/evidencia_types` | NO | dims ACIDT, links CCN-STIC, 105+ tipos evidencia |

`ens_reinforcements` legacy **droppeada** (`83e27091b489`).

### Catálogo de preguntas de auditor (M10)
`m10_audit_sim/audit_questions.py` (783 LOC): 73 medidas con `assert` de import `_aq_codes == _anexo_codes` (73==73) → regresión imposible. Corrección 2026-06-07 elevó de 58 (códigos RD 3/2010) a 73.

### Catálogo de entregables — E-codes (m06)
| Subcarpeta | Módulos `.py` | Rango |
|---|---|---|
| `policies/` | **35** | E-002/003/010, E-100→E-127, E-150/160/170/180 |
| `procedures/` | **39** | E-200→E-235 + E-204A + EIT001 + EPF001 |
| `deliverables/` | **39** | E-001/012, E-040→043, E-050/090/155, E-400→406, E-500→504, E-600→604, E-700→709, E-808 |
| `commercial/` | **3** | C-001, C-003, P-001 |
| **TOTAL** | **116 módulos** | 132 `.md` backing real |

### ENS Radar (M10b) retirado — confirmado
`drop_ens_radar_001` borra 19 tablas; no existe motor `m10_ens_radar` ni ruta `app/(radar)`. El activo `m10_audit_sim` es el simulador pre-ENAC (distinto).

### Spec maestra
`ENS_PLATFORM_MASTER_SPEC_v2.1 (2).md` (biblia: 10 fases, 73 medidas, entregables, agentes, SQL) + `CORRECCION_1` (renumeración E-1xx) + `5A/5B` (19 políticas) + `6A/6BC` (27 procedimientos) + `CIERRE_FINAL_3_GAPS`. v2.1 corrigió encabezados a 4+33+36=73 (v2.0 tenía 31 op + 38 mp erróneos).

### Discrepancias spec/código
| Afirmación docs/CLAUDE.md | Realidad |
|---|---|
| «104 entries» plantillas (1.D.F.tris) | **116 módulos** .py en m06 (sesiones posteriores añadieron E-500→E-809, EIT/EPF) |
| `ens_measures_catalog_v1.yaml` «73 medidas» | YAML tiene **79** (73+6 residuos); seed filtra a 73 |
| «refuerzos R1-R9» | El código materializa **R1-R5** (R6+ no en Anexo II) |
| `audit_questions` «58 con RD 3/2010» | Corregido 2026-06-07 → 73 con assert rígido |
| `MASTER_PLAN` lista `m10_ens_radar` activo | Relic pre-retiro; el motor real es `m10_audit_sim` |

### Veredicto
**COMPLETO** respecto a la verdad de las 52/68/73 medidas: implementación autoritativa, correcta y blindada con tests + assert de import permanente. El catálogo de entregables (116) **supera** lo documentado (104). La corrección RD 3/2010 → RD 311/2022 está completa.


## 96 - Negocio, diferenciadores, pricing, estado cerrado, limitaciones

> Auditoría empírica 2026-06-13. Ficheros leídos: `docs/ACCEPTANCE_CLOSED_PRODUCT.md`, `docs/SYSTEM_KNOWLEDGE_BASE.md`, `docs/pricing/CANONICAL_PRICING.md`, `docs/differentiators/magerit_risk_floor.md`, `docs/decisions/*.md` (4), `docs/master_plan/fulkro_26_motores_v1.md`, `docs/limitations/pilar_export.md`, `README.md`, `DECISIONS.md`, `MEMORY.md`, `backend/app/core/pricing/rules.py`, `backend/app/fulkro_identity.py`, `docs/audits/EJECUTABLE_8_PASADA_{8,21}_*.md`.

---

### Posicionamiento y cliente objetivo

- **Producto**: plataforma SaaS de implantación ENS (RD 311/2022) operada por consultor autónomo Marcos Mata (Madrid).
- **Cliente directo**: empresas privadas que licitan a la AAPP. AAPP = customer-of-customer, nunca cliente directo.
- **Modelo**: Outcome-as-a-Service — el cliente VE/AUTORIZA/FIRMA/RECIBE; Marcos opera todo lo técnico desde admin.
- **Identidad canónica** (`backend/app/fulkro_identity.py` verificado): tel `+34 637 165 328`, web `www.fulkro.es`, email `marcosmata@fulkro.es`.
- **CIF**: placeholder explícito "pendiente alta autónomo" en `MEMORY.md`. NO registrado en BD ni código.

---

### Diferenciadores verificados vs competencia

| Diferenciador | Evidencia código |
|---|---|
| **MAGERIT floor riesgo** fiel Libro III p.6-7 (activos MA → riesgo mínimo B, nunca MB) | `m02_magerit/service.py` `_lookup_impact_qualitative` + `_lookup_risk_matrix`; test específico verde |
| **Tabla impacto 3→5 columnas** por interpolación consistente | ADR `docs/decisions/magerit_impact_5_columns.md`; marcado en docstring |
| **Determinismo > LLM** decisiones normativas (R1) | `m01_categorization` puro; pricing sin LLM |
| **Audit log inmutable R6** SHA-256 hash-chain + append-only por privilegio | trigger `d4f8b2a90001`; gate `verify-deploy.sh` 9/9 PASS |
| **SoA real per-proyecto** 73 medidas con `dda_entries` | `m03_dda/service.py:71-168` Pasada 21 Frente A confirmado |
| **M8 Pentesting Autopilot v2.0** SARIF/CVSS/EPSS + 5 gates + agente anti-injection Opus 4.8 | motor `m08_verification`; rama `main` verificada |
| **Auto-remediación cloud** ADR-055 kill-switch OFF por defecto | `m_remediation` 60 tests; desplegado prod 2026-06-13 |
| **3 portales**: admin + cliente magic-link + auditor ENAC | rutas Next.js verificadas `(admin)` / `(client-portal)` / `(portal)` |
| **Compliance propio** dogfooding (R7) | `m_compliance_monitor` 19 checks reales |

**Audidat vs Fulkro**: Audidat Básica 3-8k€ / Media 8-18k€ / Alta 18k+ · Fulkro 3.200/10.700/22.800€ (mid). Diferencial: plataforma propia + consultor directo + presencia in-situ auditoría ENAC.

**Limitación PILAR** (`docs/limitations/pilar_export.md`): XML nativo, NOT `.mgr` PILAR CCN (propietario, sin XSD público). Ciclo cerrado imposible sin intervención manual.

**PKG-lite vs AGE**: tablas SQL `pkg_nodes`+`pkg_edges` JSONB; AGE excluido por conflicto pgvector. Traversals ≤3 hops SQL.

---

### Pricing canónico (verificado `backend/app/core/pricing/rules.py`)

Fuente única: tabla `pricing_config` (BD) → `BASE_PRICES`/`BASE_PRICES_CANONICAL` (mutación in-place al arranque). Sin precios sombra.

| Categoría | Precio base | Ceiling | Plazo impl. | Audit ext. |
|---|---|---|---|---|
| **BÁSICA** | **3.200€** | 4.500€ | 2-4 sem | NO |
| **MEDIA** | **10.700€** | 13.000€ | +8-16 sem ENAC | SÍ ENAC |
| **ALTA** | **22.800€** | 28.000€ | +12-20 sem ENAC | SÍ ENAC+SOC+DR |

Verificado en código: `{"BASICA": Decimal("3200.00"), "MEDIA": Decimal("10700.00"), "ALTA": Decimal("22800.00")}` ✅

**Retainers** (verificados `RETAINER_TIERS` en `rules.py`):
- `R_MICRO` 150€ · `R_LITE` 300€ · **`R_STD` 700€** (base negocio) · `R_PLUS` 1.200€ · `R_CRITICAL` 3.000€
- Divergencia histórica R_STD 400€ vs 700€ resuelta por migración `unify_pricing_fiscal_rls_001` ✅
- Extra sector regulado: +2.000€ impl. / +300€/mes retainer (desde R_PLUS).

Exclusiones: auditoría ENAC externa, HW/SW, hosting, pentest externo.

---

### Estado cerrado (ACCEPTANCE_CLOSED_PRODUCT.md · 2026-06-08)

| Frente | Estado |
|---|---|
| Suite backend | **5.950 passed · 0 fallos** · BD limpia · LLM sellado |
| TypeScript | `tsc --noEmit` exit 0 |
| ENS medidas | 52/68/73 (BÁSICA/MEDIA/ALTA BOE RD 311/2022) ✅ |
| Alembic | 1 head `m8_autopilot_canonical_001` (240+ tablas) |
| E2E Playwright | 230 passed / **147 failed** (deuda specs UI, NO bugs producto) |
| Infra prod | `docker-compose.prod.yml` 12 servicios; gate 9/9 PASS |
| Git | 19 MB / 4.014 ficheros / sin secretos |

**Fronteras Hetzner-only** (no validables en dev): TLS/Let's Encrypt, Yubikey WebAuthn, `ANTHROPIC_API_KEY` real, SMTP, fastembed con modelo, MinIO WORM runtime, ClamAV, MCP-pentest `USE_MCP_REAL`, pgBackRest físico.

**5 pasos manuales Marcos**: Hetzner CPX31+, DNS `fulkro.es`, Yubikey enroll, secretos reales, SMTP.

---

### Cobertura ENS real (Pasada 21)

- **Frente A (73 medidas)**: SoA/DdA real. Huecos: `op.exp.8` logs ≥12m cliente (ausente), semáforo per-medida STUB (`m04_gap/control_status_service.py:112-121` = `pass`), TSA real `mp.info.4` ALTA (sin integración).
- **Frente B (fases 0-7)**: implantación sólida. **BLOQUEA cierre BÁSICA conforme**: firmante no-RSEG + campo AMPARO ausente en declaración.
- **Frente C (retainer)**: servicios reales pero beat dispara stubs; LUCIA + recertificación dead-code. No bloquea certificación inicial.
- **Frente D (dogfooding)**: real, 19 checks lógica genuina.

Fallos silenciosos HIGH pre-piloto: coach cliente `/coach` roto (`AttributeError` → siempre "Todo al día"); SSE `signing.*` + accompaniment fuera de `CLIENTE_EVENT_TYPES` → polling 30s.

---

### ADRs y decisiones clave

| Decisión | Fichero | Esencia |
|---|---|---|
| PKG-lite vs AGE | `docs/decisions/pkg_lite_vs_apache_age.md` | SQL JSONB; AGE Future-X si complejidad |
| MAGERIT 5 cols | `docs/decisions/magerit_impact_5_columns.md` | Extensión 3→5 interpolación |
| Freeze/unfreeze M2 | `docs/decisions/motor2_freeze_unfreeze_vs_versioning.md` | Snapshot único JSONB; no historial |
| LLM ingesta masiva | `docs/decisions/llm_ingestion_pipeline.md` | Fase 1 determinista; Fase 2 M11 LLM+RAG (DEFERRED) |
| ADR-003 dev auth | `DECISIONS.md` | WebAuthn stub dev; desactivado con `APP_ENV=production` |

---

### Discrepancias CLAUDE.md vs código real

1. **Número de motores**: CLAUDE.md "42 motores reales" · `README.md` "44 directorios" · Ejecutable 8 Pasada 2 verificó 47. Sin consenso en docs.
2. **`docs/master_plan/`**: plan v1 2026-04-13 con 26 motores (2 completos, 23 stubs). Desactualizado vs 40+ motores funcionales reales. No existe versión actualizada.
3. **`MEMORY.md` raíz**: fecha 2026-05-13, Sprint Polish Máximo sesión 14. Artefacto de sprint obsoleto, NO estado final del producto.
4. **`DECISIONS.md` raíz**: sólo ADR-001/002/003. Los 50+ ADRs restantes viven en `docs/architecture/ADR-*.md`. Catálogo raíz incompleto.
5. **Pricing ALTA 22.000€ sombra**: divergencia histórica resuelta. `rules.py` confirma 22.800€ ✅.


