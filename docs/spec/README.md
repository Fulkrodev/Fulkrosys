# README — DOCUMENTACIÓN FULKRO PARA CLAUDE CODE

**Propietario:** Marcos Mata García · consultor ENS autónomo · Madrid
**Destinatario:** Claude Code
**Fecha:** 10 de abril de 2026
**Objetivo:** construir la plataforma FULKRO de implantación del Esquema Nacional de Seguridad (RD 311/2022) conforme al plan de 40 semanas de la Parte 9 del v2.1.

---

## 1. QUÉ ES ESTO

Este paquete contiene **todo lo que necesitas para construir la plataforma FULKRO** desde cero. La plataforma permite a Marcos implantar el ENS a clientes españoles (PYMEs que licitan con el sector público) con un modelo 95/5 — 95 % automatizado por la plataforma, 5 % trabajo humano del consultor — y escalar a 20-40 clientes simultáneos en retainer.

El paquete está formado por:

1. **`ENS_PLATFORM_MASTER_SPEC_v2.1.md`** — la **especificación maestra** de 6.810 líneas. Es tu biblia. Todo lo que construyas tiene que ser conforme a este documento. Contiene 26 motores, 27 agentes, ~75 tablas SQL, 9 pantallas UI, el plan de construcción de 40 semanas y 15 apéndices.

2. **21 entregables de contenido** (políticas, procedimientos, plantillas, código Python de dos motores, tests E2E, corpus normativo verificado, etc.) que te dan una ventaja enorme: no tienes que inventar texto legal en español ni código del Motor 8 o el Motor 22.

3. **Correcciones aplicadas sobre los entregables originales** (renumeración, ampliaciones, cierres de gaps).

4. **Este README** que te dice el orden de lectura, la regla de precedencia y las instrucciones operativas.

---

## 2. ORDEN DE LECTURA

Claude Code, sigue este orden al abrir los ficheros. No te saltes pasos.

### Paso 1 — LA BIBLIA (primero y sin excepción)

**`ENS_PLATFORM_MASTER_SPEC_v2.1.md`**

Léelo entero. Son 6.810 líneas pero cada sección importa. Cuando termines, deberías ser capaz de responder a estas preguntas sin volver a abrirlo:

- ¿Cuáles son los 26 motores de la plataforma y qué hace cada uno?
- ¿Cuáles son los 27 agentes y qué temperatura y modelo usa cada uno?
- ¿Cómo se estructura la base de datos y qué RLS policies se aplican?
- ¿Cuál es el plan de construcción en 40 semanas?
- ¿Qué medidas del Anexo II del RD 311/2022 tiene que cubrir la plataforma?
- ¿Cómo funciona el modelo 95/5?
- ¿Qué es el tenant virtual y cómo se implementa con RLS + MinIO prefix?

**Secciones críticas que te marco con nombre propio:**

- **Parte 4.3** — Modelo de datos (~75 tablas SQL). Especialmente las **nuevas tablas v2.1 revisión abril 2026** que añaden gestor documental, ciclo de vida y backups.
- **Parte 5 — Motores 1 a 26.** Los Motores 24 (IDMS), 25 (Lifecycle) y 26 (Backup) son de esta revisión; no los ignores.
- **Parte 8** — Dogfooding ENS Medio sobre la propia plataforma. **Esto no es opcional: la plataforma se audita a sí misma.**
- **Parte 9 — Plan de construcción de 40 semanas.** Especialmente la **§9.13 — Plan de integración de los Motores 24, 25 y 26**, que te dice exactamente en qué semanas encajarlos.
- **Apéndice C y Apéndice I** — Prompts de los agentes. **No los modifiques.** Son el control anti-alucinación.
- **Apéndice H** — Corpus normativo completo para ingesta. Úsalo literalmente.
- **Apéndice K** — 9 pantallas UI con detalle de layout. No diseñes UX a mano: sigue estas pantallas.

### Paso 2 — LA RENUMERACIÓN (antes de cualquier entregable F1/F2)

**`CORRECCION_1_RENUMERACION_v2.1.md`**

**CRÍTICO.** Los ficheros originales F1_1, F1_2, F2_1 y F2_2 usan una numeración antigua de políticas y procedimientos que **NO coincide** con la numeración v2.1 del Anexo II de v2.1. Esto causaría conflictos gravísimos si lo ignoras: por ejemplo, el fichero F1.1 llama "E-101" a "Roles y Responsabilidades" pero v2.1 dice que E-101 es "Control de Accesos". Esta corrección contiene la **tabla de mapeo completa** y el **script Python `rename_sgsi_ids.py`** para ejecutar la renumeración automáticamente.

**Acción:** aplica esta renumeración antes de procesar cualquier otro entregable F1/F2.

### Paso 3 — LOS ENTREGABLES DE CONTENIDO

Léelos en este orden porque el orden refleja las dependencias y el ciclo del consultor:

**Bloque A — Políticas del SGSI (27/27 documentos):**

1. `F1_1_POLITICAS_CRITICAS_E100_E104.md` — 5 políticas madre (**RENUMERAR según Corrección 1**)
2. `F1_2_POLITICAS_CRITICAS_E105_E108.md` — 4 políticas más (**RENUMERAR**)
3. `CORRECCION_5A_7_POLITICAS_ALTA_PRIORIDAD.md` — 7 políticas nuevas (ya con numeración v2.1 correcta)
4. `CORRECCION_5B_12_POLITICAS_RESTANTES.md` — 12 políticas restantes (ya con numeración v2.1 correcta)

**Bloque B — Procedimientos del SGSI (35/35 documentos):**

5. `F2_1_PROCEDIMIENTOS_CRITICOS_E200_E218.md` — 6 procedimientos (**RENUMERAR**)
6. `F2_2_PROCEDIMIENTOS_CRITICOS_E206_E234.md` — 6 procedimientos (**RENUMERAR**)
7. `CORRECCION_6A_11_PROCEDIMIENTOS_ALTA.md` — 11 procedimientos nuevos (ya con numeración v2.1 correcta)
8. `CORRECCION_6BC_16_PROCEDIMIENTOS_RESTANTES.md` — 16 procedimientos restantes (ya con numeración v2.1 correcta)

**Bloque C — Plantillas comerciales y de entrega (14 documentos):**

9. `F3_1_PLANTILLAS_COMERCIALES_P001_C001_C003.md` — P-001 antigua, C-001, C-003
10. `F3_2_PLANTILLAS_ENTREGABLES_E001_E040_E050_E400.md` — entregables técnicos

**Bloque D — Correcciones consolidadas que afectan a varios entregables:**

11. `CORRECCION_C3_C4_C7_C8_CONSOLIDADO.md` — contiene:
    - **C-3:** Cláusula Quinta Bis de Recursos del Cliente (se inyecta en el contrato C-001)
    - **C-4:** Reconciliación del Effort Estimator a horas base 60/150/230
    - **C-7:** 8 plantillas adicionales del Apéndice F (F.1, F.3, F.4, F.5, F.6, F.7, F.8, F.10)
    - **C-8:** System prompts de los Agentes 17-20 (versiones mejoradas)

12. `CIERRE_FINAL_3_GAPS.md` — contiene:
    - **Gap 1:** Propuesta P-001 reescrita con 15 secciones conforme a v2.1 (**REEMPLAZA la P-001 de F3.1**)
    - **Gap 2:** Tests E2E completos con ~400 líneas de pytest reales
    - **Gap 3:** Tabla `referral_partners` con Pydantic + SQL + migración Alembic

**Bloque E — Motor 8 (Pentesting):**

13. `G_MOTOR_8_PENTESTING_MCP_LLM.md` — código Python del Motor 8 original (5 herramientas)
14. `CORRECCION_C2_MOTOR8_AMPLIADO.md` — ampliación a 17 herramientas con pipeline de 11 fases

**COMPLEMENTARIOS, NO SUSTITUTOS.** Usa el código original del G como base y añádele las 12 herramientas nuevas del C2.

**Bloque F — Motor 22 (PLACSP Scraper + PILAR Integrator):**

15. `H_PLACSP_SCRAPER_PILAR_INTEGRATOR.md` — código Python del Motor 22 completo

**Bloque G — Base de conocimiento:**

16. `APENDICE_H_VERIFICADO.md` — 92+ URLs del corpus normativo verificadas + script `corpus_ingest.py`
17. `ISO27001_ES_PARTE1.md` — traducción oficial ISO/IEC 27001:2022
18. `ISO27001_ES_PARTE2_MAPPING.md` — mapping bidireccional ENS↔ISO 27001 con 94.5 % cobertura

**Bloque H — Consultoría operativa:**

19. `ENTREGABLE_D_E_CERTIFICADORAS_ESTIMATOR.md` — 14 entidades certificadoras ENAC + Effort Estimator base (**aplicar corrección C-4**)
20. `FULKRO_BRAND_IDENTITY.md` — identidad de marca

**Bloque I — Tests:**

21. Los tests E2E reales están en `CIERRE_FINAL_3_GAPS.md` (Gap 2). El fichero `I_SUITE_TESTS_E2E_10_FASES.md` original es un índice vacío — ignóralo.

---

## 3. REGLA DE PRECEDENCIA (muy importante)

Cuando encuentres una contradicción entre dos ficheros, **el más reciente prevalece**. En la práctica, el orden de precedencia es:

1. **`ENS_PLATFORM_MASTER_SPEC_v2.1.md`** (biblia, prevalece sobre todo).
2. **Cualquier fichero que empiece por `CORRECCION_`** prevalece sobre los ficheros originales F1/F2/F3.
3. **`CIERRE_FINAL_3_GAPS.md`** prevalece sobre los entregables anteriores donde tengan conflicto.
4. **Ficheros originales F1/F2/F3** — prevalecen entre ellos por orden alfabético, pero **siempre después de aplicar la Corrección 1 de renumeración**.

### Ejemplos concretos de resolución de conflictos

| Tema | Fuente obsoleta | Fuente correcta |
|---|---|---|
| Numeración de políticas E-1XX | F1_1 y F1_2 originales | `CORRECCION_1_RENUMERACION_v2.1.md` |
| Numeración de procedimientos E-2XX | F2_1 y F2_2 originales | `CORRECCION_1_RENUMERACION_v2.1.md` |
| Propuesta P-001 (secciones) | F3_1 (11 secciones) | `CIERRE_FINAL_3_GAPS.md` (15 secciones) |
| Contrato C-001 (cláusula de recursos) | F3_1 original | `CORRECCION_C3_C4_C7_C8_CONSOLIDADO.md` (C-3 Cláusula 5bis) |
| Effort Estimator (horas base) | D+E original (45/120/220) | `CORRECCION_C3_C4_C7_C8_CONSOLIDADO.md` (C-4: 60/150/230) |
| Motor 8 (herramientas disponibles) | G original (5 herramientas) | **AMBOS COMPLEMENTARIOS** — G base + C2 ampliación (17 herramientas, 11 fases) |
| Plantillas del Apéndice F | F3_1 (solo 2) | `CORRECCION_C3_C4_C7_C8_CONSOLIDADO.md` (C-7: 8 adicionales) |
| Tests E2E | `I_SUITE_TESTS_E2E_10_FASES.md` (vacío) | `CIERRE_FINAL_3_GAPS.md` (Gap 2: pytest real) |
| Agentes 17-20 | Ninguno | `CORRECCION_C3_C4_C7_C8_CONSOLIDADO.md` (C-8) |
| Tabla `referral_partners` | Ninguna (faltaba) | `CIERRE_FINAL_3_GAPS.md` (Gap 3) |

---

## 4. QUÉ TIENES QUE CONSTRUIR

La plataforma completa tiene **26 motores**, **27 agentes**, **~75 tablas SQL**, **9 pantallas de UI** y un **plan de 40 semanas** detallado en la Parte 9 del v2.1.

### Arranca por aquí (semanas 1-3)

1. **Setup del repositorio.** Monorepo Python con FastAPI + PostgreSQL 16 + pgvector + Redis + Celery + MinIO + HTMX + Tailwind. Detalles en Parte 4.1.

2. **Dogfooding ENS Medio sobre la propia plataforma.** Desde el día 1. No negocies esto: Hetzner CCX33, LUKS, TLS 1.3, WebAuthn con Yubikey, fail2ban, CIS benchmarks, Vault, audit log inmutable con hash chain, pgAudit. Parte 8.

3. **Esquema base de datos.** Implementa todas las tablas de Parte 4.3 con migraciones Alembic. Aplica RLS desde el principio. Incluye las **26 tablas nuevas de v2.1 revisión abril 2026** (gestor documental, ciclo de vida, backups, tenant virtual).

### Semanas 4-6 — Backup antes de datos reales (NO SALTAR)

**§9.13 del v2.1 establece que el Motor 26 (Backup & DR) se construye en las semanas 4-6 ANTES de ingerir datos de cliente real.** Esto no es negociable. pgBackRest + MinIO mirror + Vault backup + primer DR drill + panel de Operaciones. El criterio de salida es: tener al menos un backup completo verificado y un restore test pasado.

### Semanas 7-13 — Corpus y motores core

- **Corpus normativo ingestado** usando `APENDICE_H_VERIFICADO.md` y el script `corpus_ingest.py`. RAG con pgvector + grafo Apache AGE.
- **Motor 1** (Categorization Engine, determinista).
- **Motor 2** (MAGERIT Risk Engine, Python propio).
- **Motor 3** (DdA Engine).
- **Motor 4** (Gap Analysis).
- **Motor 5** (Obligations & Planning).
- **Motor 16** (Adaptive Onboarding).

### Semanas 8-10 — Tenant virtual (paralelo)

Sidebar multi-cliente, switch rápido Cmd+K, URL amigable por cliente, dashboard específico por cliente, carpetas estructuradas en MinIO con prefijo obligatorio `fulkro/clients/{nif}/projects/{project_id}/...`.

### Semanas 14-20 — Gestor documental inteligente (IDMS)

**Motor 24 completo** conforme a §24 de la Parte 5 y la pantalla K.7 del Apéndice K. Incluye **Agente 27 Document Intelligence** con prompt del Apéndice I.27.

### Semanas 21-27 — Motores restantes

Motores 6 (Document Factory), 7 (Evidence Collection), 8 (Pentesting con 17 herramientas), 9 (Audit Preparation), 10 (Audit Simulation), 11 (Copiloto), 12 (Magic Link), 13-15 (Commercial + Contracts + Billing), 17-23 (Project Planning, Comunicación, Riesgos, Workspace, Diagnóstico Organizativo, Technical Discovery, Retainer).

### Semanas 28-30 — Ciclo de vida del proyecto

**Motor 25 completo** conforme a §25 de la Parte 5. Máquina de estados + wizard de archivado de 5 pasos + export puntual + reversibilidad 30 días.

### Semanas 31-36 — Primer cliente piloto

Refinamiento + integración end-to-end + validación con un primer cliente real.

### Semanas 37-40 — Reserva para imprevistos y pulido

---

## 5. REGLAS NO NEGOCIABLES

**Marcos me ha pedido explícitamente que te transmita estas reglas.** Son inviolables:

1. **Marcos es el único usuario humano permanente.** Los clientes no tienen cuentas. Solo magic links firmados Ed25519 con TTL corto y rate limiting agresivo.

2. **Los motores deterministas son la columna vertebral.** El LLM solo genera texto y conversa. Las decisiones normativas las toman los motores con código, no el LLM.

3. **El corpus oficial es la única fuente de verdad.** Si algo no está en el RD 311/2022, las ITS, las CCN-STIC serie 800 o los PCE, no se afirma. Todos los agentes tienen "modo no encontrado" obligatorio (ver Apéndice C, cabecera común).

4. **Citas obligatorias.** Cada afirmación normativa lleva su cita exacta: `[RD 311/2022 Art. X]`, `[CCN-STIC NNN §X.Y]`, `[Anexo II medida.código]`.

5. **Anti-alucinación:** temperatura LLM ≤ 0.2, validación cruzada de todas las afirmaciones del LLM contra el corpus RAG, verificador de citas con rechazo si son inválidas.

6. **Formato auditor español en todo.** Plantillas reconocibles, matriz cruzada, dossier con estructura §2.15. Si el auditor ENAC veterano no lo reconoce, la plataforma ha fallado.

7. **La plataforma cumple ENS Medio sobre sí misma.** Dogfooding obligatorio desde el día 1.

8. **Pruebas mensuales automatizadas de restauración** del propio backup. El Motor 26 las ejecuta. No son opcionales.

9. **Vigilancia normativa continua.** Cuando el CCN publica una nueva ITS, PCE o CCN-STIC, la plataforma lo detecta, ingesta y notifica automáticamente.

10. **Logs criptográficamente inmutables.** `audit_log` con hash chain + export periódico a almacenamiento WORM (S3 Object Lock modo Compliance).

11. **No hay teclado, solo Yubikey.** Autenticación de Marcos únicamente con WebAuthn + hardware key. Sin password fallback. Al menos 2 Yubikeys registradas.

12. **Firma de evidencias con Ed25519.** Cada evidencia que entra al Vault del Motor 24 se firma con la clave privada de la plataforma. Clave pública publicada para verificación externa.

---

## 6. TECHSTACK DEFINITIVO

Para evitarte dudas, esto es lo que Marcos quiere (Parte 4 del v2.1):

- **Lenguaje principal:** Python 3.12
- **Framework web:** FastAPI
- **ORM:** SQLAlchemy 2.0 (async) + Alembic
- **Base de datos:** PostgreSQL 16 con extensiones pgvector + Apache AGE + pgcrypto + pgaudit
- **Cache/colas:** Redis 7 + Celery
- **Object storage:** MinIO (S3 compatible) con Object Lock modo Compliance
- **Frontend:** HTMX + Tailwind CSS + Alpine.js para interactividad ligera. Componentes React solo para pantallas muy interactivas (gestor documental, dashboard multi-cliente).
- **LLM:** API de Anthropic (Claude Sonnet 4.6 para trabajos complejos, Claude Haiku 4.5 para clasificación masiva del Agente 27).
- **Modelo de embeddings:** `intfloat/multilingual-e5-large` local (1024 dimensiones) o alternativamente API de Voyage AI.
- **OCR:** Tesseract con paquete de español.
- **Extractores de texto:** pdfplumber, python-docx, openpyxl, python-pptx, extract-msg.
- **Firma digital:** Ed25519 con PyNaCl o cryptography.
- **Videollamadas:** LiveKit (Motor 20).
- **Infraestructura:** Hetzner CCX33 (Debian 12 hardenizada CIS), Terraform + Ansible, Hetzner Storage Box para backups fríos.
- **Secretos:** HashiCorp Vault (o `pass` como fallback barato en arranque).
- **CI/CD:** GitHub Actions (o Gitea local si Marcos prefiere soberanía).
- **Observabilidad:** Prometheus + Grafana + Loki para logs. Sentry opcional para errores.

---

## 7. PREGUNTAS QUE PUEDES (Y DEBES) HACERLE A MARCOS

Durante la construcción habrá decisiones que no están totalmente cerradas en v2.1. **No las inventes: pregúntale directamente.** Ejemplos típicos:

- ¿Qué dominio final va a usar? (probablemente `fulkro.es` pero confirma).
- ¿Registra Vault con un paquete o prefiere arrancar con `pass`?
- ¿Quiere el frontend 100 % server-side con HTMX o una SPA para el gestor documental?
- ¿Comparte las Yubikeys físicas ahora o las compra después?
- ¿Qué proveedor de email transaccional usar para los magic links? (Postmark, SES, Mailgun).
- ¿Configura el dominio con DNSSEC desde el principio?
- ¿Qué gateway de pago usa para cobrar a los clientes? (Stripe, Redsys, Bizum Business).

Cuando tengas una duda bloqueante, pregúntale. **No asumas.**

---

## 8. QUÉ HACER CUANDO ENCUENTRES UN GAP EN LA ESPECIFICACIÓN

v2.1 es muy detallada pero no lo cubre literalmente todo. Cuando te encuentres un gap:

1. **Primero verifica que no está cubierto en los apéndices.** Hay 15 apéndices (A a O) con detalles que a veces no están en el cuerpo principal.
2. **Segundo busca en los entregables de contenido.** Quizá está en los ficheros de correcciones.
3. **Tercero aplica el principio conservador:** la decisión que tomes debe ser la más simple, la más barata de operar, la más alineada con el dogfooding ENS Medio, y la que deje el código más fácil de auditar.
4. **Cuarto documenta tu decisión** en un fichero `DECISIONS.md` en la raíz del repo con formato ADR (Architecture Decision Record).
5. **Quinto pregúntale a Marcos** si la decisión es relevante para el negocio.

---

## 9. PROTOCOLO DE ENTREGA

Cada semana del plan de 40 semanas termina con un entregable concreto. Al final de cada semana:

1. Corre los tests E2E (hay una base en `CIERRE_FINAL_3_GAPS.md` Gap 2).
2. Corre el pipeline de seguridad interno sobre la propia plataforma (Trivy, Nuclei, Lynis, Semgrep).
3. Genera un informe semanal en `progress/week_NN.md` con qué se ha construido, qué queda, qué bloqueos hay.
4. Actualiza el propio dogfooding: si has tocado el esquema, la DdA de la propia plataforma debe reflejarlo.
5. Verifica que los backups del Motor 26 funcionan y que el último restore test pasó.

---

## 10. EL PRIMER COMMIT

Tu primer commit debería:

1. Inicializar el monorepo con la estructura de directorios descrita en Parte 4.2 del v2.1.
2. Añadir este README, el v2.1 y los 21 entregables en `docs/spec/`.
3. Configurar CI/CD básico (lint, type check, tests).
4. Crear `DECISIONS.md` vacío con el template ADR.
5. Crear `progress/week_00_bootstrap.md` con el estado inicial.
6. Commit message: `chore: bootstrap FULKRO repository with v2.1 spec and entregables`

---

## 11. CONTACTO

Si tienes dudas, Marcos está disponible en su dashboard de Claude.ai. Escribe tus dudas en lenguaje natural. No necesitas formalismo — Marcos trabaja contigo como con un colega técnico de confianza, en español directo, sin anglicismos innecesarios.

---

## 12. ÚLTIMA NOTA DE MARCOS PARA CLAUDE CODE

> *"He pasado meses especificando esta plataforma hasta el último detalle. No estoy buscando creatividad, estoy buscando ejecución. Lee v2.1 entero, entiende cada motor, sigue el plan de 40 semanas, aplica las correcciones, y construye exactamente lo que está descrito. Si algo no encaja, pregúntame. Si una decisión no es crítica, elige la opción más simple y barata de operar. Mi objetivo es tener un primer cliente real en la semana 36. Construyamos esto bien a la primera. Gracias."*

---

**A construir. 🔩**
