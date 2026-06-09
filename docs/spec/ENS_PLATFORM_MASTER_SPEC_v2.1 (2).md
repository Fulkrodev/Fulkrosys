# ENS PLATFORM — ESPECIFICACIÓN MAESTRA

**Destinatario:** Claude Code
**Propietario:** Marcos (consultor autónomo, Madrid)
**Versión:** 2.1 — Edición integral del ciclo del consultor, corregida y ampliada
**Fecha:** 10 de abril de 2026 (revisión con gestor documental inteligente + ciclo de vida + backups)
**Estado:** especificación de construcción desde cero — versión definitiva operativa para entrar en Claude Code

---

## CHANGELOG v2.0 → v2.1 — CORRECCIONES Y AMPLIACIONES

La v2.0 estaba al 88%. La v2.1 la deja al 97% e incorpora todo lo pendiente detectado en la revisión línea por línea. Cambios:

**Revisión de 10 de abril de 2026 (manteniendo nombre v2.1):**

0. **AMPLIACIÓN CRÍTICA — Gestor documental inteligente (Motor 24) + Ciclo de vida del proyecto (Motor 25) + Backups (Motor 26).** Esta revisión eleva la gestión documental de "tabla + MinIO" a **IDMS de primera clase** comparable a SharePoint/Drive pero especializado en ENS y con LLM integrado para clasificación automática. Incluye drag & drop inteligente, búsqueda híbrida léxico-semántica con pgvector, etiquetado automático por medida ENS, vista de árbol, línea temporal documental, chat con el repositorio. Además se añade el **ciclo de vida del proyecto** con archivado + ZIP firmado + purga post-período legal, y **backups de primera clase** con pruebas periódicas de restauración y DR drills trimestrales. Por último se refuerza el **tenant virtual por cliente** con RLS + carpetas MinIO estructuradas + URL amigable + switch rápido Cmd+K + dashboard específico por cliente + export completo. Todo esto se describe en los nuevos Motores 24/25/26 (Parte 5), nuevas tablas SQL (Parte 4.3), nuevo Agente 27 (Apéndice I) y nuevas pantallas K.7/K.8/K.9 (Apéndice K). **Esta ampliación debe construirse como parte del plan de 40 semanas conforme al plan de integración descrito en §9.13.**

**Revisión de 9 de abril de 2026 (revisión original de v2.1):**

1. **FIX conteo oficial de medidas del Anexo II** en 4 líneas que contradecían las tablas desglose: el Marco Operacional tiene **33 medidas** (no 31) y las Medidas de Protección son **36** (no 38). El total sigue siendo 73 = 4 org + 33 op + 36 mp. Las tablas de desglose ya estaban correctas desde v1.2; ahora los encabezados también lo están.

2. **FIX referencia rota al "Motor 13 — Submission Engine"** en el Apéndice D.6: ese motor ya no se llama así (Motor 13 es ahora Commercial Document Factory). El antiguo Submission Engine queda como motor futuro sin número fijo hasta que se construya (ver nota en el Apéndice D.6).

3. **FIX numeración** de las subsecciones de la Parte 11 (antes eran 10.1 y 10.2 por herencia de v1.2; ahora son 11.1 y 11.2).

4. **FIX referencia al Apéndice G "políticas críticas"**: esa referencia apuntaba a un apéndice que no existía. Se ha eliminado y sustituido por referencia a la Parte 2.6 que es donde realmente están listadas las 27 políticas.

5. **FIX recuento de políticas en el checklist master**: decía "~25 políticas" cuando el resto del documento dice 27 (E-100 a E-126). Corregido.

6. **NUEVO Apéndice H — Corpus normativo completo para ingesta** con los ~92 documentos que Claude Code debe descargar e ingestar al grafo durante las semanas 3-5 del plan, con URLs, formatos esperados y prioridad. **Esto es crítico:** sin esta lista, Claude Code no sabe qué meter en el corpus.

7. **NUEVO Apéndice I — System prompts base de los 10 agentes nuevos (17-26)**. El Apéndice C original solo tenía los 16 primeros; este apéndice completa la cobertura a los 26.

8. **NUEVO Apéndice J — Esquemas SQL de las 15+ tablas nuevas del ciclo comercial y organizativo** (leads, exploratory_meetings, proposals, contracts, invoices, client_commitments, discovered_assets, stakeholders_graph, business_processes, legal_obligations, confidential_notes, collaborative_workspaces, retainer_activities, pricing_models, effort_estimates). Claude Code ya no tiene que inventárselas.

9. **NUEVO Apéndice K — Especificación de las 6 pantallas maestras de la UI de Marcos** (dashboard multi-cliente, pipeline comercial, detalle de proyecto, modo reunión exploratoria en vivo, modo auditoría en curso, consola de retainer). Para que Marcos no tenga que diseñar la UX a mano.

10. **NUEVO Apéndice L — Riesgos de construcción de la propia plataforma** con advertencias explícitas sobre qué partes no son auto-generables (las 110 plantillas DOCX requieren redacción legal real, por ejemplo) y cómo mitigar cada riesgo durante la construcción.

11. **NUEVO Apéndice M — Biblioteca precargada de pricing models** con 9 modelos económicos típicos (básico fijo, media por hitos, alta por fases + éxito, retainer mensual, etc.) para que la plataforma pueda calcular propuestas en segundos.

12. **NUEVO Apéndice N — Effort Estimator calibrado**: fórmulas deterministas de estimación de esfuerzo por tarea × categoría × tamaño del cliente × madurez inicial. Para que el Motor 17 estime sin alucinar.

13. **NUEVO Apéndice O — Glosario operativo interno** con los 40 términos propios de la plataforma (magic link, knowledge graph, evidence vault, etc.) para que Claude Code los use con consistencia.

14. **AMBIGÜEDAD unificada — rango de clientes en retainer:** se unifica en "20-40 clientes simultáneos" (el rango 20-25 que aparecía en §3.11 se corrige al rango grande del Motor 23).

15. **FIX tabla de matriz de cobertura** en Apéndice E: las referencias a "§C.14" y similares se eliminan (eran del Apéndice C original de 16 agentes y ya no son navegables por la ampliación a 26). Se sustituyen por referencias a motores y agentes por número.

Con v2.1 el documento es **auto-suficiente para Claude Code**: basta con entregarle este MD y la `PARTE_2_ENTREGABLES.md` y puede empezar a construir sin preguntar sobre el corpus, los prompts, los esquemas SQL ni las fórmulas de estimación.

---

## CHANGELOG v1.2 → v2.0 — REESCRITURA INTEGRAL

La v1.2 estaba **al 20% de lo que Marcos necesita**. Cubría con detalle el corpus normativo, los entregables del auditor y la arquitectura técnica, pero **no cubría el ciclo real del consultor**: captación de leads, reunión exploratoria, propuesta formal, contrato, onboarding adaptativo, diagnóstico organizativo profundo, discovery técnico, fases de implantación, verificación interna, preparación de auditoría, remediación y mantenimiento post-certificación.

La v2.0 añade todo eso. Los cambios son:

1. **NUEVA Parte 3 completa: "El ciclo del consultor en 10 fases"** (de Fase −1 a Fase 8), con plantillas, inputs/outputs, entregables automatizados, motores responsables y modos de operación con el cliente en cada fase. Esta es la parte más importante del nuevo documento.

2. **Motores ampliados de 12 a 23.** Los 11 motores nuevos cubren: CRM comercial, generación de propuestas, contratos, onboarding adaptativo, plan de proyecto, comunicación y reporting, gestión de riesgos del proyecto, diagnóstico organizativo, discovery técnico, coaching de auditoría y mantenimiento post-certificación.

3. **Agentes IA ampliados de 16 a 26.** Los 10 nuevos cubren: cualificación de leads, asistente de reunión exploratoria, redactor de propuestas comerciales, negociador contractual, asistente de onboarding sectorial, analista de stakeholders, mapeador de procesos, generador de BIA, coach de auditoría y gestor de retainer.

4. **Nuevas plantillas de ciclo comercial y gestión de proyecto** (Apéndice F): guion de reunión exploratoria, plantilla de propuesta formal de 10-20 páginas, plantilla de contrato con cláusula crítica de "recursos del cliente", plantilla de kick-off, plantilla de plan de proyecto, plan de comunicación, plan de gestión de riesgos del proyecto.

5. **Nueva sección de discovery técnico automatizado** con detalle de qué se descubre y con qué herramienta/conector/MCP en cada categoría (activos, identidades, datos, configuraciones, vulnerabilidades, proveedores).

6. **Nuevo entorno colaborativo efímero** (gestor documental minimalista + canal de videollamada bajo demanda tipo Teams) integrado con el sistema de magic links.

7. **Mantenimiento de todas las correcciones de v1.1 → v1.2** (conteo 4+33+36=73 medidas, grados L0-L5, `mp.s` con 4 medidas).

**Principio operativo de v2.0:** el 95% del trabajo lo hace la plataforma, Marcos hace el 5% (decisiones críticas, relación humana con el cliente, validación final). Si la plataforma exige más del 5% del tiempo de Marcos en un tramo, ese tramo está mal diseñado y hay que automatizarlo más.

---

## 0. PROPÓSITO Y FILOSOFÍA

Esta plataforma es el **centro de mando único** de Marcos para gestionar el ciclo completo de un proyecto ENS de principio a fin: desde la captación del lead hasta el mantenimiento post-certificación. No es solo "una herramienta para implantar ENS": es **el consultor autónomo operativo de Marcos**, con Marcos como revisor humano sobre un sistema que hace el grueso del trabajo.

**Ámbito de clientes:** empresas privadas españolas que licitan o trabajan con el sector público y por ello necesitan conformidad con el RD 311/2022. No sector público directo (los organismos tienen sus propias herramientas del CCN). No empresas sin exposición pública.

**Principios no negociables:**

1. **Cobertura end-to-end del ciclo del consultor.** La plataforma asiste en las 10 fases (−1 a 8). No hay "zonas no cubiertas". Si Marcos tiene que abrir Word o PowerPoint para algo del proyecto, la plataforma tiene un hueco que rellenar.

2. **Profundidad ENS total en las tres categorías.** B, M y A cubiertas con la misma exhaustividad. Marcos no sabe a priori en qué categoría caerá un cliente; la plataforma debe tener músculo para todas.

3. **Marcos con conocimiento mínimo, plataforma con conocimiento total.** El copiloto LLM, los motores deterministas, las plantillas auditadas y el corpus normativo en el grafo compensan cualquier gap de Marcos. Un consultor con conocimiento medio de ENS, asistido por esta plataforma, debe poder pasar una auditoría ENAC estricta y además firmar contratos profesionales, dirigir reuniones con directivos, y sostener un retainer post-certificación.

4. **Cero alucinación regulatoria ni contractual.** Las decisiones normativas (qué medida aplica, qué refuerzo, qué evidencia exige el auditor), las cláusulas contractuales críticas y las estimaciones de esfuerzo son DETERMINISTAS y derivan del corpus oficial + biblioteca de plantillas inmutables. El LLM redacta y personaliza con grounding RAG estricto, citas obligatorias y modo "no lo sé".

5. **Cliente sin cuenta permanente.** El cliente solo recibe enlaces firmados con OTP para operaciones puntuales: responder un onboarding sectorial, firmar un documento, aportar una evidencia, autorizar una acción técnica, unirse a una videollamada bajo demanda. La plataforma sigue siendo de Marcos. Sin cuenta de cliente, sin RBAC complejo, sin soporte. El **único** espacio "persistente" del cliente es una carpeta colaborativa efímera por proyecto con caducidad al cierre.

6. **El 95/5.** El 95% lo hace la plataforma. Marcos hace el 5% (decisiones críticas, relación humana, validación final). Medido en tiempo. Si un proyecto B consume más de 25 horas de Marcos o un proyecto M más de 80 horas, la plataforma está mal calibrada.

7. **Formato auditor español en TODO entregable auditable.** Y formato directivo profesional en TODO entregable comercial/contractual. Ambos son no negociables.

**Stack:** Python 3.12 + FastAPI + PostgreSQL 16 (pgvector + Apache AGE + pgAudit) + Redis + Celery → Temporal.io + HTMX + Alpine.js + Tailwind + Caddy + LiveKit (para videollamadas bajo demanda). Despliegue en Hetzner CCX33 (Alemania). Coste estimado infra+LLM+SaaS auxiliares: 120–200 €/mes.

**Integración con ENS Radar v2:** la plataforma tiene un endpoint específico `/leads/from-radar` que recibe leads cualificados desde ENS Radar v2 con todos los datos del expediente, organismo contratante, nivel ENS exigido y plazos del pliego ya pre-cargados. ENS Radar caza, esta plataforma ejecuta el ciclo completo. Los leads del Radar entran directamente en la Fase −1 como "leads ultra-cualificados" que saltan varios pasos del pipeline comercial.

---

## PARTE 1 — CORPUS NORMATIVO ENS (BASE DE CONOCIMIENTO)

Esta es la fuente de verdad sobre la que toda la plataforma razona. Sin este corpus completo, ingestado y versionado, nada funciona.

### 1.1 Marco normativo vigente (abril 2026)

**Real Decreto 311/2022, de 3 de mayo**, por el que se regula el Esquema Nacional de Seguridad. Sustituye al RD 3/2010 y al RD 951/2015. Estructura: 41 artículos en 7 capítulos, 3 disposiciones adicionales, 1 transitoria, 1 derogatoria, 3 finales y **4 anexos** (I Categorización, II Medidas, III Auditoría, IV Glosario). El plazo transitorio de adecuación venció el **5 de mayo de 2024**. Toda entidad bajo ámbito de aplicación debe estar adecuada hoy.

**Modificación relevante posterior:** la Disposición Adicional Segunda fue redactada por la **Disposición Final Segunda del RD 1125/2024, de 5 de noviembre** (BOE 6/11/2024), sobre organización e instrumentos operativos para la Administración Digital. Marcos debe verificar mensualmente si hay modificaciones nuevas (la plataforma tiene un agente de vigilancia normativa para esto).

**Ámbito de aplicación crítico para Marcos:** el RD 311/2022 amplía explícitamente el ámbito a las **entidades del sector privado que presten servicios o provean soluciones a las entidades del sector público** (Art. 2). Este es el mercado de Marcos: empresas privadas que necesitan ENS porque sin él no pueden licitar ni ejecutar contratos públicos.

**Roles obligatorios ENS** (CCN-STIC 801, desarrollados en el RD 311/2022 Art. 11 y ss.):

- **Responsable de la Información** — decide los requisitos de seguridad de la información (valoración por dimensiones).
- **Responsable del Servicio** — decide los requisitos de los servicios prestados.
- **Responsable de la Seguridad (RSEG)** — determina las decisiones para satisfacer los requisitos. **Debe ser distinto del Responsable del Sistema salvo excepciones justificadas.**
- **Responsable del Sistema** — desarrolla, opera y mantiene el sistema durante todo su ciclo de vida.

Estos cuatro roles son obligatorios y deben constar en acta de nombramiento firmada por la dirección del cliente. El **Comité de Seguridad** (puede llamarse Comité STIC o similar) coordina los anteriores.

### 1.2 Anexo I — Categorización del sistema

La categoría del sistema depende del impacto que un incidente tendría sobre la organización en cinco **dimensiones de seguridad**:

| Sigla | Dimensión |
|---|---|
| **D** | Disponibilidad |
| **I** | Integridad |
| **C** | Confidencialidad |
| **A** | Autenticidad |
| **T** | Trazabilidad |

Para cada información tratada y cada servicio prestado, el Responsable de la Información (o del Servicio) valora el nivel de impacto en cada dimensión: **BAJO / MEDIO / ALTO** (o N/A si no aplica).

**Regla del máximo:** la categoría del sistema es la más alta de cualquier dimensión de cualquier información o servicio dentro del alcance.

- Si todas las dimensiones son BAJO → **Categoría BÁSICA**.
- Si la más alta es MEDIO → **Categoría MEDIA**.
- Si la más alta es ALTO → **Categoría ALTA**.

Criterios de valoración detallados en la **CCN-STIC 803** (valoración de sistemas). El acta de categorización debe documentar qué información/servicio se ha valorado, en qué nivel y con qué justificación. El Responsable de la Seguridad aprueba la categoría resultante.

### 1.3 Anexo II — Medidas de seguridad: las 73 medidas

El Anexo II del RD 311/2022 contiene **73 medidas de seguridad** organizadas en tres marcos. Cada medida tiene:

- Un **código** (org.X, op.fam.X, mp.fam.X).
- Un **nombre**.
- Un **requisito base**.
- **Refuerzos** (R1, R2, R3, R4, R5) que se suman al base. **No siempre son incrementales**: a veces se elige entre uno u otro (notación `[Rn o Rn+1]`).
- Aplicabilidad por **dimensión** (D, I, C, A, T) y/o por **categoría del sistema** (B/M/A).

Las medidas marcadas en **verde** aplican desde Básica; **amarillo** desde Media; **rojo** solo en Alta.

Las tres marcos:

- **Marco Organizativo (org)** — 4 medidas — gobernanza y políticas.
- **Marco Operacional (op)** — 33 medidas en 7 familias — operación del sistema.
- **Medidas de Protección (mp)** — 36 medidas en 8 familias — protección de activos.

#### 1.3.1 Marco Organizativo (org) — 4 medidas

| Código | Nombre | Aplica desde |
|---|---|---|
| **org.1** | Política de seguridad | Básica |
| **org.2** | Normativa de seguridad | Básica |
| **org.3** | Procedimientos de seguridad | Básica |
| **org.4** | Proceso de autorización | Básica |

**org.1 — Política de seguridad.** Documento aprobado por el órgano superior, firmado, difundido. Define misión, objetivos, marco normativo, roles, comité, gestión de riesgos. Refuerzos en categorías superiores: revisión más frecuente, alineación con estrategia. Evidencia: documento aprobado + acta + registro de difusión + acuse de recibo.

**org.2 — Normativa.** Cuerpo normativo que desarrolla la política. En Básica subset mínimo; en Media completo; en Alta con normas específicas adicionales (PAM, claves, BYOD).

**org.3 — Procedimientos.** Procedimientos operativos. El auditor pide ver tanto el documento como **registros de ejecución de los últimos 3-6 meses**.

**org.4 — Proceso de autorización.** Proceso formal por el que se autorizan: instalación de equipos, conexión a redes, entrada en producción, contratación de servicios externos, uso de medios personales. Todo cambio significativo pasa por aquí.

#### 1.3.2 Marco Operacional (op) — 33 medidas

**op.pl — Planificación (5 medidas)**

| Código | Nombre | Aplica |
|---|---|---|
| op.pl.1 | Análisis de riesgos | Básica+ |
| op.pl.2 | Arquitectura de seguridad | Básica+ |
| op.pl.3 | Adquisición de nuevos componentes | Básica+ |
| op.pl.4 | Dimensionamiento / gestión de capacidad | Básica+ (cambio en RD 311/2022, antes solo Media) |
| op.pl.5 | Componentes certificados | Media+ (uso obligatorio CPSTIC en Media/Alta) |

**op.acc — Control de acceso (6 medidas)**

| Código | Nombre |
|---|---|
| op.acc.1 | Identificación |
| op.acc.2 | Requisitos de acceso |
| op.acc.3 | Segregación de funciones y tareas |
| op.acc.4 | Proceso de gestión de derechos de acceso |
| op.acc.5 | Mecanismos de autenticación (usuarios externos) |
| op.acc.6 | Mecanismos de autenticación (usuarios de la organización) |

**Crítico op.acc.6:** el refuerzo R1 admite **un único factor basado en contraseña** solo cuando el acceso se realiza desde zonas controladas y sin atravesar zonas no controladas. En el resto de casos, MFA. El auditor mira esto con lupa.

**op.exp — Explotación (10 medidas)**

| Código | Nombre |
|---|---|
| op.exp.1 | Inventario de activos |
| op.exp.2 | Configuración de seguridad |
| op.exp.3 | Gestión de la configuración |
| op.exp.4 | Mantenimiento y actualizaciones de seguridad |
| op.exp.5 | Gestión de cambios |
| op.exp.6 | Protección frente a código dañino |
| op.exp.7 | Gestión de incidentes |
| op.exp.8 | Registro de la actividad |
| op.exp.9 | Registro de la gestión de incidentes |
| op.exp.10 | Protección de los registros de actividad |

**op.ext — Servicios externos (4 medidas)**

| Código | Nombre |
|---|---|
| op.ext.1 | Contratación y acuerdos de nivel de servicio |
| op.ext.2 | Gestión diaria |
| op.ext.3 | Protección de la cadena de suministro |
| op.ext.4 | Interconexión de sistemas |

`op.ext.3` y `op.ext.4` son **nuevas en el RD 311/2022** respecto al anterior. Cadena de suministro y interconexión son focos de auditoría.

**op.nub — Servicios en la nube (1 medida)**

| Código | Nombre |
|---|---|
| op.nub.1 | Protección de servicios en la nube |

**Nueva familia completa en RD 311/2022.** Si el cliente usa AWS/Azure/GCP/M365, esta medida aplica con todos sus refuerzos. Ver también CCN-STIC 823 (uso de servicios en la nube) y PCE específicos por proveedor.

**op.cont — Continuidad del servicio (4 medidas)**

| Código | Nombre |
|---|---|
| op.cont.1 | Análisis de impacto |
| op.cont.2 | Plan de continuidad |
| op.cont.3 | Pruebas periódicas |
| op.cont.4 | Medios alternativos |

En Básica solo análisis básico. En Media BIA formal y plan probado. En Alta sitio alternativo operativo con prueba de conmutación documentada.

**op.mon — Monitorización del sistema (3 medidas)**

| Código | Nombre |
|---|---|
| op.mon.1 | Detección de intrusión |
| op.mon.2 | Sistema de métricas |
| op.mon.3 | Vigilancia |

`op.mon.3` Vigilancia es **nueva en RD 311/2022**: vigilancia continua de amenazas, integración con feeds del CCN-CERT.

#### 1.3.3 Medidas de Protección (mp) — 36 medidas

**mp.if — Protección de las instalaciones e infraestructuras (7 medidas)**

| Código | Nombre |
|---|---|
| mp.if.1 | Áreas separadas y con control de acceso |
| mp.if.2 | Identificación de las personas |
| mp.if.3 | Acondicionamiento de los locales |
| mp.if.4 | Energía eléctrica |
| mp.if.5 | Protección frente a incendios |
| mp.if.6 | Protección frente a inundaciones |
| mp.if.7 | Registro de entrada y salida de equipamiento |

**mp.per — Gestión del personal (4 medidas)**

| Código | Nombre |
|---|---|
| mp.per.1 | Caracterización del puesto de trabajo |
| mp.per.2 | Deberes y obligaciones |
| mp.per.3 | Concienciación |
| mp.per.4 | Formación |

**mp.eq — Protección de los equipos (4 medidas)**

| Código | Nombre |
|---|---|
| mp.eq.1 | Puesto de trabajo despejado (mesa limpia) |
| mp.eq.2 | Bloqueo de puesto de trabajo |
| mp.eq.3 | Protección de equipos portátiles |
| mp.eq.4 | Otros dispositivos conectados a la red |

`mp.eq.4` es **nueva en RD 311/2022**: IoT, OT, dispositivos no estándar.

**mp.com — Protección de las comunicaciones (4 medidas)**

| Código | Nombre |
|---|---|
| mp.com.1 | Perímetro seguro |
| mp.com.2 | Protección de la confidencialidad |
| mp.com.3 | Protección de la integridad y autenticidad |
| mp.com.4 | Separación de flujos de información en la red |

**mp.si — Protección de los soportes de información (5 medidas)**

| Código | Nombre |
|---|---|
| mp.si.1 | Marcado de soportes |
| mp.si.2 | Criptografía |
| mp.si.3 | Custodia |
| mp.si.4 | Transporte |
| mp.si.5 | Borrado y destrucción |

**mp.sw — Protección de las aplicaciones informáticas (2 medidas)**

| Código | Nombre |
|---|---|
| mp.sw.1 | Desarrollo de aplicaciones |
| mp.sw.2 | Aceptación y puesta en servicio |

**mp.info — Protección de la información (6 medidas)**

| Código | Nombre |
|---|---|
| mp.info.1 | Datos de carácter personal |
| mp.info.2 | Calificación de la información |
| mp.info.3 | Cifrado |
| mp.info.4 | Firma electrónica |
| mp.info.5 | Sellos de tiempo |
| mp.info.6 | Limpieza de documentos |

**mp.s — Protección de los servicios (4 medidas)**

| Código | Nombre |
|---|---|
| mp.s.1 | Protección del correo electrónico |
| mp.s.2 | Protección de servicios y aplicaciones web |
| mp.s.3 | Protección de la navegación web |
| mp.s.4 | Protección frente a la denegación de servicio |

**Nota sobre la evolución en ENS 2022:** respecto al RD 3/2010, en el Anexo II del RD 311/2022 se **suprimió** el antiguo `mp.s.9 Medios alternativos` y se **añadió** `mp.s.3 Protección de la navegación web` (aplicable desde categoría Básica). La plataforma **debe ingestar el texto oficial del Anexo II del BOE (RD 311/2022) como fuente única de verdad** y derivar la lista exacta de ahí; esta tabla refleja la enumeración oficial verificada contra las fuentes CCN.

**Total: 73 medidas oficiales**, distribuidas en **4 organizativas (org) + 33 operacionales (op) + 36 de protección (mp)**.

Desglose verificado por familia:

- **org**: 4 (org.1 a org.4).
- **op**: 33 = op.pl (5) + op.acc (6) + op.exp (10) + op.ext (4) + op.nub (1) + op.cont (4) + op.mon (3).
- **mp**: 36 = mp.if (7) + mp.per (4) + mp.eq (4) + mp.com (4) + mp.si (5) + mp.sw (2) + mp.info (6) + mp.s (4).

Comprobación: 4 + 33 + 36 = **73** ✓

### 1.4 Anexo III — Auditoría de la seguridad

- Las auditorías de conformidad se realizan **al menos cada 2 años**, salvo cambios sustanciales que obliguen a auditoría extraordinaria.
- En **categoría Básica** basta con **autoevaluación** (Declaración de Conformidad) o auditoría a criterio del responsable.
- En **categoría Media o Alta** la auditoría debe ser realizada por una **entidad acreditada por ENAC** bajo la norma ISO/IEC 17065 para certificación de conformidad ENS.
- El informe de auditoría se remite al Responsable de la Seguridad y al Comité.
- Hallazgos: **no conformidades mayores**, **no conformidades menores**, **observaciones**, **oportunidades de mejora**.

### 1.5 Anexo IV — Glosario

Términos clave (la plataforma los ingesta para que el copiloto los use con precisión): activo, amenaza, análisis de riesgos, autenticidad, categoría, confidencialidad, declaración de aplicabilidad, dimensión de seguridad, disponibilidad, gestión de riesgos, integridad, medida de seguridad, refuerzo, riesgo, salvaguarda, sistema de información, trazabilidad, vulnerabilidad.

### 1.6 Instrucciones Técnicas de Seguridad (ITS)

Las ITS son normas de obligado cumplimiento publicadas por el CCN bajo el ENS. Las vigentes (verificar en https://ens.ccn.cni.es/es/normativa, **Marcos: ingesta automatizada y vigilancia de cambios**):

- **ITS de Auditoría de la Seguridad** (Resolución de 13/10/2016, derogada y sustituida; verificar versión vigente conforme RD 311/2022).
- **ITS de Informe del Estado de la Seguridad** (regula INES).
- **ITS de Notificación de Incidentes de Seguridad** (regula LUCIA).
- **ITS de Conformidad con el ENS** (regula Declaración y Certificación).
- **ITS de Adquisición de Productos de Seguridad** (regula CPSTIC).
- **ITS de Criptología de Empleo en el ENS**.
- **ITS de Interconexión en el ENS**.

Cada ITS aporta requisitos vinculantes adicionales al RD. **La plataforma debe ingestar las ITS íntegras al corpus** y mapearlas a las medidas del Anexo II que desarrollan.

### 1.7 Guías CCN-STIC serie 800

Series prioritarias para ingesta en la base de conocimiento (verificar versiones vigentes en https://www.ccn-cert.cni.es/guias/guias-series-ccn-stic/800-guia-esquema-nacional-de-seguridad.html):

| Guía | Contenido |
|---|---|
| **CCN-STIC 800** | Glosario de términos |
| **CCN-STIC 801** | Responsabilidades y funciones (los 4 roles obligatorios) |
| **CCN-STIC 802** | Auditoría del ENS |
| **CCN-STIC 803** | Valoración de sistemas (categorización) |
| **CCN-STIC 804** | Medidas de implantación del ENS (con niveles de madurez L0–L5) |
| **CCN-STIC 805** | Política de seguridad (plantilla y contenido) |
| **CCN-STIC 806** | Plan de adecuación |
| **CCN-STIC 807** | Criptología de empleo |
| **CCN-STIC 808** | Verificación del cumplimiento del ENS (grados de madurez L0-L5 según CCN-STIC 804; los requisitos marcados en gris son **nucleares** y siempre se evalúan; checklist de evidencias por medida del Anexo II) |
| **CCN-STIC 809** | Declaración y Certificación de Conformidad |
| **CCN-STIC 815** | Métricas e indicadores |
| **CCN-STIC 817** | Gestión de ciberincidentes |
| **CCN-STIC 819** | Medidas compensatorias |
| **CCN-STIC 821** | Apéndices y normas de seguridad |
| **CCN-STIC 824** | Informe del Estado de la Seguridad (alimenta INES) |
| **CCN-STIC 827** | Gestión y uso de dispositivos móviles |

**Perfiles de Cumplimiento Específico (PCE)** publicados por el CCN bajo Art. 30 RD 311/2022:

- **CCN-STIC 887** — PCE para servicios cloud AWS.
- **CCN-STIC 890A / 890C** — PCE para entidades locales (ayuntamientos pequeños/grandes).
- **CCN-STIC 891** — PCE para el sector salud.
- **CCN-STIC 892** — PCE NIS2.

Cuando un cliente cae bajo un PCE, **ese PCE prima**: define qué medidas y refuerzos aplican exactamente. La plataforma debe detectar esto en el onboarding y aplicar el PCE correspondiente automáticamente.

### 1.8 Relación con otras normativas

- **RGPD + LOPDGDD**: solapan en `mp.info.1` (datos personales), `op.exp.7` (incidentes ↔ brechas), `mp.per.2` (deberes), `op.ext.1` (encargados de tratamiento art. 28). La plataforma trata RGPD como módulo paralelo obligatorio.
- **NIS2**: transposición española en curso (a verificar estado a abril 2026). Solape fuerte; CCN-STIC 892 (PCE NIS2) es la referencia. Si el cliente cae bajo NIS2, hay obligaciones adicionales de notificación.
- **ISO 27001 / 27002 / 22301**: complementarias. Si el cliente ya tiene ISO 27001, **se aprovecha** —políticas, AR, controles— pero no exime del ENS. La plataforma mapea ISO ↔ ENS para acelerar.

### 1.9 Certificación: Declaración vs Certificación

| Categoría | Forma de conformidad | Validez | Auditor |
|---|---|---|---|
| **Básica** | Declaración de Conformidad (autoevaluación) | 2 años | Responsable de la Seguridad |
| **Media** | Certificación de Conformidad | 2 años | Entidad acreditada por ENAC bajo ISO/IEC 17065 |
| **Alta** | Certificación de Conformidad | 2 años | Entidad acreditada por ENAC bajo ISO/IEC 17065 |

**Distintivos publicados por el CCN:** la plataforma debe ofrecer al cliente certificado el distintivo correspondiente para su web según las reglas de uso del CCN (https://ens.ccn.cni.es/es/conformidad/distintivos).

**Listado de entidades certificadoras ENAC para ENS** (a abril 2026, verificar en https://ens.ccn.cni.es/es/certificacion/entidades-de-certificacion): AENOR, Bureau Veritas Iberia, EQA, BDO Auditores, LL-C (Cert), SGS ICS Ibérica, Applus Certification, OCA Cert, TÜV Rheinland, DNV Business Assurance, IVAC-EQA, LGAI Technological Center (Applus+), LRQA España. La plataforma mantiene este listado actualizado vía agente de vigilancia.

### 1.10 Catálogo CPSTIC

El **Catálogo de Productos y Servicios de Seguridad de las Tecnologías de la Información y Comunicación** (CCN-STIC 105) es de **uso obligatorio en categorías Media y Alta** para los productos que formen parte de la arquitectura de seguridad y para los productos referenciados expresamente en las medidas del ENS. Si no existe producto CPSTIC que cubra la funcionalidad requerida, se usa producto certificado conforme al Art. 19 del RD 311/2022.

**La plataforma cachea el catálogo CPSTIC** y, durante el motor de obligaciones, sugiere productos CPSTIC concretos para cada control técnico cuando aplique.

---

## PARTE 2 — ENTREGABLES EXHAUSTIVOS PARA AUDITORÍA (LA BIBLIA)

Esta sección lista, sin omitir nada, todos los entregables que un auditor ENAC veterano español espera ver en una auditoría de conformidad ENS. Cada entregable se identifica con un ID interno (`E-XXX`) que la plataforma usa para tracking.

### 2.1 Documentos de gobierno (todas las categorías)

| ID | Documento | Formato | Aprobación | Periodicidad |
|---|---|---|---|---|
| E-001 | Política de Seguridad de la Información | DOCX/PDF firmado | Órgano superior | Revisión anual |
| E-002 | Acta de nombramiento de los 4 roles ENS | PDF firmado | Dirección | Cuando cambien |
| E-003 | Acta de constitución del Comité de Seguridad | PDF firmado | Dirección | Una vez |
| E-004 | Reglamento del Comité de Seguridad | DOCX/PDF | Comité | Revisión anual |
| E-005 | Actas periódicas del Comité de Seguridad | PDF firmado | Comité | Mensual o trimestral |
| E-006 | Acta de Revisión por la Dirección | PDF firmado | Dirección | Anual |
| E-007 | Memoria anual del estado de la seguridad | PDF | RSEG | Anual |
| E-008 | Registro de difusión de la Política y normativa con acuse | XLSX/PDF | RSEG | Continuo |

### 2.2 Categorización (todas las categorías)

| ID | Documento | Formato |
|---|---|---|
| E-010 | Inventario de información tratada con valoración por dimensión (D/I/C/A/T) | XLSX |
| E-011 | Inventario de servicios prestados con valoración por dimensión | XLSX |
| E-012 | Acta de Categorización del Sistema firmada por RSEG | PDF |
| E-013 | Justificación detallada de la valoración (CCN-STIC 803) | DOCX/PDF |

### 2.3 Análisis de Riesgos MAGERIT v3 (todas las categorías, profundidad creciente)

| ID | Documento | Notas |
|---|---|---|
| E-020 | Inventario de activos valorados (taxonomía MAGERIT) | XLSX exportable a PILAR |
| E-021 | Catálogo de amenazas aplicadas por activo | XLSX |
| E-022 | Valoración de probabilidad e impacto | XLSX |
| E-023 | Cálculo de riesgo intrínseco | XLSX |
| E-024 | Catálogo de salvaguardas implantadas con mapping a medidas Anexo II | XLSX |
| E-025 | Cálculo de riesgo efectivo | XLSX |
| E-026 | Cálculo de riesgo residual | XLSX |
| E-027 | Plan de tratamiento de riesgos | DOCX/PDF |
| E-028 | Aprobación formal del riesgo residual por la dirección | PDF firmado |
| E-029 | Histórico de versiones del AR | Sistema |
| E-030 | Fichero PILAR exportable (.mgr o equivalente) | Binario |

En **Básica** basta análisis informal (Excel). En **Media** MAGERIT formal (Excel estructurado o PILAR). En **Alta** PILAR obligatorio o equivalente, con revisión anual mínima.

### 2.4 Declaración de Aplicabilidad (DdA) (todas las categorías)

| ID | Documento | Formato |
|---|---|---|
| E-040 | Declaración de Aplicabilidad de las 73 medidas del Anexo II | DOCX/PDF firmado por RSEG |

Contenido por cada medida:
- Código y nombre.
- Aplicabilidad (sí / no / parcial).
- Justificación (especialmente de las no aplicables).
- Refuerzos aplicados (R1/R2/R3/R4/R5).
- Estado de implementación (no implantado / parcial / implantado / verificado).
- Medidas compensatorias si aplican (con referencia a CCN-STIC 819).
- Responsable de implantación.
- Evidencias previstas y aportadas.

### 2.5 Plan de Adecuación (todas las categorías)

| ID | Documento | Formato |
|---|---|---|
| E-050 | Plan de Adecuación según CCN-STIC 806 | DOCX/PDF + Gantt (XLSX/PDF) |

Contenido: tareas, dependencias, responsables, fechas, hitos, presupuesto orientativo, criterios de éxito, aprobación de la dirección.

### 2.6 Cuerpo Normativo — políticas internas (listado exhaustivo)

Todas en formato DOCX/PDF firmado, con plantilla uniforme (propósito, alcance, definiciones, responsabilidades, contenido, control de cambios, vigencia). Difusión registrada con acuse.

| ID | Política | Básica | Media | Alta |
|---|---|---|---|---|
| E-100 | Política de Seguridad de la Información | ✓ | ✓ | ✓ |
| E-101 | Política de Control de Accesos | ✓ | ✓ | ✓ |
| E-102 | Política de Contraseñas y Autenticación | ✓ | ✓ | ✓ |
| E-103 | Política de Uso Aceptable de los recursos TI | ✓ | ✓ | ✓ |
| E-104 | Política de Clasificación de la Información | ✓ | ✓ | ✓ |
| E-105 | Política de Tratamiento de Datos Personales (RGPD) | ✓ | ✓ | ✓ |
| E-106 | Política de Copias de Seguridad | ✓ | ✓ | ✓ |
| E-107 | Política Criptográfica | ✓ | ✓ | ✓ |
| E-108 | Política de Gestión de Incidentes | ✓ | ✓ | ✓ |
| E-109 | Política de Continuidad de Negocio | parcial | ✓ | ✓ |
| E-110 | Política de Teletrabajo y Movilidad | ✓ | ✓ | ✓ |
| E-111 | Política de Uso de Servicios Cloud | ✓ | ✓ | ✓ |
| E-112 | Política de Gestión de Proveedores | ✓ | ✓ | ✓ |
| E-113 | Política de Adquisición de Tecnología | ✓ | ✓ | ✓ |
| E-114 | Política de Desarrollo Seguro (SSDLC) | – | ✓ | ✓ |
| E-115 | Política de Gestión de Vulnerabilidades | – | ✓ | ✓ |
| E-116 | Política de Gestión de Cambios | ✓ | ✓ | ✓ |
| E-117 | Política de Gestión de Privilegios y PAM | – | ✓ | ✓ |
| E-118 | Política de BYOD | si aplica | si aplica | si aplica |
| E-119 | Política de Respuesta a Brechas de Datos Personales | ✓ | ✓ | ✓ |
| E-120 | Política de Gestión de Claves Criptográficas | – | parcial | ✓ |
| E-121 | Política de Redes y Comunicaciones | ✓ | ✓ | ✓ |
| E-122 | Política de Gestión de Soportes | ✓ | ✓ | ✓ |
| E-123 | Política de Seguridad Física | ✓ | ✓ | ✓ |
| E-124 | Política de Seguridad del Personal | ✓ | ✓ | ✓ |
| E-125 | Política de Mesa Limpia y Pantalla Limpia | ✓ | ✓ | ✓ |
| E-126 | Política de Borrado Seguro y Destrucción de Información | ✓ | ✓ | ✓ |

### 2.7 Procedimientos Operativos (listado exhaustivo)

Formato DOCX/PDF firmado. Cada uno con: actores, entradas, pasos, salidas, registros generados, periodicidad, indicadores. **El auditor pide ver registros de ejecución de los últimos 3-6 meses para cada procedimiento.**

| ID | Procedimiento |
|---|---|
| E-200 | Procedimiento de alta de personal (técnico y lógico) |
| E-201 | Procedimiento de baja de personal |
| E-202 | Procedimiento de cambio de rol |
| E-203 | Procedimiento de gestión de cambios técnicos (con CAB) |
| E-204 | Procedimiento de gestión de incidentes (con clasificación, escalado, notificación a LUCIA) |
| E-205 | Procedimiento de gestión de vulnerabilidades |
| E-206 | Procedimiento de aplicación de parches |
| E-207 | Procedimiento de copias de seguridad |
| E-208 | Procedimiento de restauración (con pruebas periódicas) |
| E-209 | Procedimiento de pruebas de continuidad |
| E-210 | Procedimiento de revisión periódica de accesos |
| E-211 | Procedimiento de gestión de cuentas privilegiadas |
| E-212 | Procedimiento de respuesta a brechas RGPD |
| E-213 | Procedimiento de notificación de brechas a la AEPD |
| E-214 | Procedimiento de destrucción segura de información |
| E-215 | Procedimiento de gestión de soportes extraíbles |
| E-216 | Procedimiento de gestión de proveedores |
| E-217 | Procedimiento de evaluación de riesgos de proveedores |
| E-218 | Procedimiento de auditoría interna |
| E-219 | Procedimiento de revisión por la dirección |
| E-220 | Procedimiento de gestión de no conformidades |
| E-221 | Procedimiento de gestión documental |
| E-222 | Procedimiento de gestión de excepciones |
| E-223 | Procedimiento de revisión de logs |
| E-224 | Procedimiento de despliegue de software (SSDLC operativo) |
| E-225 | Procedimiento de pruebas pre-producción |
| E-226 | Procedimiento de teletrabajo |
| E-227 | Procedimiento de uso de cloud |
| E-228 | Procedimiento de respuesta ante pérdida o robo de dispositivos |
| E-229 | Procedimiento de visitas externas |
| E-230 | Procedimiento de categorización de sistemas |
| E-231 | Procedimiento de gestión de identidades |
| E-232 | Procedimiento de gestión criptográfica |
| E-233 | Procedimiento de notificación a LUCIA |
| E-234 | Procedimiento de proceso de autorización (org.4) |

### 2.8 Plantillas de registros operativos

Cada procedimiento genera registros. La plataforma mantiene plantilla y registro vivo:

E-300 Registro de altas; E-301 Registro de bajas; E-302 Registro de cambios de rol; E-303 Registro de cambios técnicos / tickets CAB; E-304 Registro de incidentes; E-305 Registro de vulnerabilidades; E-306 Registro de parches aplicados; E-307 Logs de backup; E-308 Registro de pruebas de restauración; E-309 Registro de pruebas de continuidad; E-310 Registro de revisión de accesos; E-311 Registro de excepciones aprobadas; E-312 Registro de proveedores; E-313 Registro de evaluaciones de proveedores; E-314 Registro de incidentes RGPD; E-315 Registro de NDAs firmados; E-316 Registro de formación; E-317 Registro de simulacros; E-318 Registro de auditorías; E-319 Registro de no conformidades; E-320 Registro de acciones correctivas; E-321 Registro de actas del Comité; E-322 Registro de revisiones por la dirección; E-323 Registro de visitas a instalaciones; E-324 Registro de soportes extraíbles; E-325 Registro de notificaciones a LUCIA.

### 2.9 Plan de Continuidad

| ID | Documento |
|---|---|
| E-400 | Análisis de Impacto en el Negocio (BIA) con RTO/RPO por proceso |
| E-401 | Estrategias de continuidad |
| E-402 | Plan de Continuidad de Negocio (BCP) |
| E-403 | Plan de Recuperación ante Desastres (DRP) técnico |
| E-404 | Plan de Comunicaciones de Crisis |
| E-405 | Plan de Pruebas de Continuidad |
| E-406 | Informes de pruebas ejecutadas |

### 2.10 Plan de Formación y Concienciación

| ID | Documento |
|---|---|
| E-500 | Plan anual de formación y concienciación |
| E-501 | Materiales de formación (sesión inducción, módulos por rol) |
| E-502 | Registro de asistencia y evaluación |
| E-503 | Plan y resultados de simulacros de phishing |
| E-504 | KPIs de concienciación |

### 2.11 Gestión de Proveedores

| ID | Documento |
|---|---|
| E-600 | Inventario completo de proveedores con criticidad |
| E-601 | Cuestionario ENS de evaluación de proveedores |
| E-602 | Resultados de evaluaciones |
| E-603 | Cláusulas ENS / RGPD art. 28 / notificación incidentes / derecho auditoría |
| E-604 | Adendas contractuales firmadas |
| E-605 | Tracking de vencimientos |

### 2.12 Informes técnicos

| ID | Informe | Categoría |
|---|---|---|
| E-700 | Informe de auditoría interna inicial (gap intermedio) | Todas |
| E-701 | Informe de auditoría interna pre-externa | Todas |
| E-702 | Informe de pentest externo | Recomendado B, obligatorio M/A |
| E-703 | Informe de pentest interno | Recomendado M, obligatorio A |
| E-704 | Informe de Red Team / ejercicio adversarial | Alta |
| E-705 | Informe de simulacro de phishing | Todas |
| E-706 | Informe de simulacro tabletop de incidente | M/A |
| E-707 | Informe de pruebas de restauración | Todas |
| E-708 | Informe de pruebas de DRP | M/A |
| E-709 | Informe del Estado de la Seguridad (formato INES) | Todas (anual) |

### 2.13 Evidencias técnicas por medida del Anexo II

Para cada una de las 73 medidas del Anexo II, la plataforma mantiene una **plantilla de evidencias requeridas** indicando exactamente qué pide el auditor. Ejemplos:

- **op.acc.6** (Mecanismos autenticación usuarios organización): captura de configuración del IdP mostrando MFA habilitado, política de contraseñas exportada del directorio, listado de usuarios con MFA activo, excepciones documentadas.
- **op.exp.1** (Inventario activos): export del CMDB / herramienta de inventario con fecha < 1 mes.
- **op.exp.4** (Mantenimiento y parches): informe del gestor de parches con SLA de aplicación, cobertura, excepciones.
- **op.exp.6** (Código dañino): consola del EDR mostrando cobertura 100%, política activa, alertas tratadas.
- **op.exp.8** (Registro de actividad): captura del SIEM con políticas de retención, ejemplo de búsqueda, integridad de logs.
- **op.cont.3** (Pruebas continuidad): informe de la última prueba de restauración firmado.
- **mp.com.2** (Confidencialidad comunicaciones): export de configuración TLS, informe SSL Labs, listado de servicios con TLS 1.3.
- **mp.info.3** (Cifrado): listado de bases de datos cifradas en reposo, BitLocker en endpoints, configuración KMS.
- **mp.if.1** (Áreas separadas): plano del CPD/oficina con zonificación, registro de accesos físicos.

**La plataforma debe generar este catálogo completo (73 entradas) durante la fase de ingesta del corpus** (semanas 3-5 del plan). Cada entrada con: medida, evidencia tipo, formato esperado, fuente (qué herramienta/sistema la genera), automatizable sí/no.

### 2.14 Registros de operación de los meses previos a la auditoría

**Esto es lo que más se descuida.** El auditor exige ver que los procedimientos se han operado durante al menos los 3-6 meses anteriores a la auditoría: tickets de cambios reales, incidentes registrados, parches aplicados con fechas, cuentas creadas y dadas de baja, simulacros ejecutados, actas del comité de los últimos meses, revisiones de accesos hechas. **Sin esto, la auditoría no aprueba aunque toda la documentación esté impecable.**

La plataforma fuerza al cliente, vía magic links recurrentes, a aportar estos registros mensualmente desde el día 1 de la implantación.

### 2.15 Dossier final al auditor — estructura exacta

Cuando llega el momento de la auditoría, la plataforma genera el **dossier final** en un único ZIP navegable + PDF maestro con índice, con esta estructura:

```
DOSSIER_AUDITORIA_ENS_{cliente}_{fecha}/
├── 00_INDICE_MAESTRO.pdf
├── 00_RESUMEN_EJECUTIVO.pdf
├── 01_GOBIERNO/
│   ├── E-001_Politica_Seguridad_v3_firmada.pdf
│   ├── E-002_Acta_Nombramiento_Roles.pdf
│   ├── E-003_Acta_Constitucion_Comite.pdf
│   ├── E-005_Actas_Comite/ (actas de los últimos 12 meses)
│   ├── E-006_Revision_Direccion_2026.pdf
│   └── E-007_Memoria_Estado_Seguridad_2026.pdf
├── 02_CATEGORIZACION/
│   ├── E-010_Inventario_Informacion.xlsx
│   ├── E-011_Inventario_Servicios.xlsx
│   ├── E-012_Acta_Categorizacion.pdf
│   └── E-013_Justificacion.pdf
├── 03_ANALISIS_RIESGOS/
│   ├── E-020_Inventario_Activos.xlsx
│   ├── E-021_Catalogo_Amenazas.xlsx
│   ├── E-024_Salvaguardas_Mapping_AnexoII.xlsx
│   ├── E-026_Riesgo_Residual.xlsx
│   ├── E-027_Plan_Tratamiento.pdf
│   ├── E-028_Aprobacion_Direccion.pdf
│   └── E-030_Fichero_PILAR.mgr
├── 04_DECLARACION_APLICABILIDAD/
│   └── E-040_DdA_v5_firmada.pdf
├── 05_PLAN_ADECUACION/
│   └── E-050_Plan_Adecuacion.pdf
├── 06_NORMATIVA/
│   ├── E-100_Politica_Seguridad.pdf
│   ├── E-101_Politica_Control_Accesos.pdf
│   ├── ... (todas las políticas aplicables a la categoría)
│   └── E-126_Politica_Borrado_Seguro.pdf
├── 07_PROCEDIMIENTOS/
│   ├── E-200_Alta_Personal.pdf
│   ├── ... (todos los procedimientos aplicables)
│   └── E-234_Proceso_Autorizacion.pdf
├── 08_REGISTROS_OPERACION/
│   ├── E-303_Cambios_Tecnicos_2025-10_a_2026-04.xlsx
│   ├── E-304_Incidentes.xlsx
│   ├── E-306_Parches.xlsx
│   ├── E-308_Pruebas_Restauracion.pdf
│   ├── E-310_Revisiones_Accesos.xlsx
│   ├── E-316_Formacion.xlsx
│   ├── E-317_Simulacros.xlsx
│   └── ... (registros de los últimos 6 meses mínimo)
├── 09_EVIDENCIAS_POR_MEDIDA/
│   ├── org.1/ (evidencias)
│   ├── org.2/ ...
│   ├── op.pl.1/ ...
│   ├── ... (una carpeta por cada una de las 73 medidas)
│   └── mp.s.4/ ...
├── 10_PLAN_CONTINUIDAD/
│   ├── E-400_BIA.pdf
│   ├── E-402_BCP.pdf
│   ├── E-403_DRP.pdf
│   └── E-406_Informes_Pruebas.pdf
├── 11_FORMACION_CONCIENCIACION/
│   ├── E-500_Plan_Anual.pdf
│   ├── E-502_Registro_Asistencia.xlsx
│   └── E-503_Simulacros_Phishing.pdf
├── 12_PROVEEDORES/
│   ├── E-600_Inventario_Proveedores.xlsx
│   ├── E-602_Evaluaciones.xlsx
│   └── E-604_Adendas/ (PDFs)
├── 13_INFORMES_TECNICOS/
│   ├── E-700_Auditoria_Interna_Inicial.pdf
│   ├── E-701_Auditoria_Interna_PreExterna.pdf
│   ├── E-702_Pentest_Externo.pdf
│   ├── E-703_Pentest_Interno.pdf
│   ├── E-704_Red_Team.pdf (si Alta)
│   ├── E-705_Phishing.pdf
│   ├── E-707_Restauracion.pdf
│   └── E-709_INES_Snapshot.pdf
└── 99_MATRIZ_CRUZADA/
    └── matriz_medida_x_evidencia_x_documento.xlsx
```

**La matriz cruzada del 99** es lo que más le gusta al auditor: una hoja Excel con una fila por cada una de las 73 medidas, columnas con: aplicabilidad, refuerzos, estado, evidencias aportadas (con hipervínculo), documentos relacionados, observaciones. El auditor abre esta hoja y puede verificar todo el sistema en 30 minutos.

---

## PARTE 3 — EL CICLO DEL CONSULTOR EN 10 FASES (EL CORAZÓN OPERATIVO)

**Esta es la parte más importante del documento.** Describe el ciclo completo de un proyecto ENS desde la captación del lead hasta el mantenimiento post-certificación, con 10 fases numeradas de **−1 a 8**. Para cada fase se especifica: qué pasa, qué plantillas usa la plataforma, qué entregables se generan automáticamente, qué motores y agentes intervienen, qué hace Marcos manualmente (el 5%), y qué hace el cliente vía magic links (sin cuenta permanente).

**Regla del 95/5 aplicada en cada fase:** al final de cada fase hay un cuadro "Reparto de esfuerzo" con horas estimadas de Marcos vs horas de la plataforma. Si el cuadro dice que Marcos hace más del 5%, la fase está mal calibrada y requiere más automatización.

---

### 3.1 FASE −1 — PIPELINE COMERCIAL Y CAPTACIÓN (CONTINUO, NO ES UN HITO)

El negocio de Marcos es un pipeline, no un proyecto. La Fase −1 corre en paralelo y en permanencia a todo lo demás.

#### 3.1.1 Generación de leads

Fuentes de leads que la plataforma monitoriza y cataloga automáticamente:

- **ENS Radar v2** (fuente principal): leads ultra-cualificados con expediente, organismo contratante, categoría ENS exigida y plazos del pliego ya pre-cargados. Entran por `/leads/from-radar` y saltan directamente a la cualificación.
- **PLACSP** y perfiles del contratante autonómicos: monitorización vía el Radar.
- **Adjudicaciones recientes del BOE y boletines autonómicos**: cuando una empresa adjudica un contrato público, es lead futuro.
- **Referencias** de colegas, asociaciones sectoriales (ASCOM, ENATIC, ASLAN, Colegios Profesionales).
- **Eventos** del CCN, jornadas STIC, charlas.
- **Contenido propio**: LinkedIn, blog, casos de estudio anonimizados (la plataforma publica en modo semi-automático con supervisión de Marcos).
- **Partners comerciales**: despachos de abogados que ven cláusulas ENS en pliegos pero no saben implementarlo; la plataforma gestiona una tabla `referral_partners` con comisiones configurables.

Cada lead entrante genera un registro en la tabla `leads` con: origen, empresa, contacto, sector, tamaño aproximado, notas, estado (`nuevo | cualificando | reunion_exploratoria | propuesta_enviada | negociacion | cerrado_ganado | cerrado_perdido | en_pausa`).

#### 3.1.2 Cualificación del lead (Agente 17 — Cualificador Comercial)

Antes de invertir tiempo en una reunión exploratoria, la plataforma ejecuta una cualificación asistida. Marcos recibe la información del lead y el **Agente 17** le hace estas preguntas que Marcos debe contestar (o deja en "no sé" para profundizar en la exploratoria):

1. **¿La empresa ya tiene el contrato público adjudicado, está licitando, o solo está explorando?** *(Si solo explora → baja prioridad. Si ya tiene contrato → alta prioridad con urgencia.)*
2. **¿Qué categoría ENS parece exigir el pliego?** *(Si desconocido, el Agente 2 Analizador de Pliegos lo determina automáticamente cuando Marcos sube el pliego.)*
3. **¿Qué plazo legal o contractual tiene?**
4. **¿Hay un sponsor identificado?** *(CEO, CTO, dirección comercial.)* Sin sponsor con poder de decisión, no es lead cualificado.
5. **¿Hay presupuesto asignado o "lo están estudiando"?** *("Lo están estudiando" = educación de mercado, no venta inmediata.)*
6. **¿Tiene personal técnico propio o es solo dirección?** *(Impacta el esfuerzo de ejecución.)*
7. **¿Tiene ya algo de RGPD, ISO 27001 u otro marco?** *(Palanca para acelerar.)*
8. **¿Es cliente por referencia o frío?** *(Referencia multiplica por 3 la tasa de cierre.)*

Output del Agente 17: un **Lead Score** de 0 a 100 con desglose, clasificación (A/B/C) y recomendación automática (`priorizar | reunion_exploratoria | educar | descartar | aparcar`).

#### 3.1.3 Reunión exploratoria gratuita (45-60 min)

**El objetivo NO es vender. Es entender el contexto y demostrar que Marcos sabe.** Si Marcos habla más del 40% del tiempo, lo está haciendo mal.

La plataforma asiste esta reunión con dos cosas:

**A) Plantilla guiada de reunión exploratoria** (`exploratory_meeting_templates`). El Agente 18 (Asistente de Reunión Exploratoria) le muestra a Marcos una interfaz con un panel de preguntas predefinidas organizadas por bloques. Marcos va tomando notas en cada campo durante la conversación (o hablando y transcribiendo en vivo si activa el modo dictado).

Los bloques de preguntas son:

**Bloque A — Contexto de negocio** (5-8 min)
- ¿A qué se dedica exactamente la empresa?
- ¿Cuántas personas son?
- ¿Qué porcentaje del negocio depende del sector público?
- ¿En qué comunidades autónomas operan?
- ¿Qué sectores públicos son clientes (ayuntamientos, sanidad, educación, justicia)?
- ¿Hay contratos públicos en curso? ¿Cuántos? ¿Valor aproximado?

**Bloque B — Contexto del requisito ENS** (10-15 min)
- ¿Cómo les ha llegado la obligación ENS? (Pliego específico, exigencia de un cliente recurrente, proactividad comercial.)
- ¿Tienen un pliego concreto donde se exija? → Marcos pide subirlo a la plataforma ahora mismo para que el Agente 2 lo analice.
- ¿Qué categoría cree el cliente que necesita? → La plataforma no valida esto aún, solo registra la intuición del cliente.
- ¿Hay plazo marcado? ¿Existe penalización contractual si no se cumple?
- ¿Han intentado ya esta certificación con otro consultor?
- ¿Conocen alguna otra empresa certificada en ENS en su sector?

**Bloque C — Madurez actual** (10-15 min)
- ¿Tienen ISO 27001, RGPD formalizado, alguna otra certificación de seguridad?
- ¿Tienen política de seguridad escrita? ¿Cuándo se aprobó?
- ¿Tienen DPO? ¿Interno o externo?
- ¿Tienen un responsable de seguridad identificado?
- ¿Tienen SIEM, EDR, MFA universal, backups probados?
- ¿Han sufrido un incidente grave en los últimos 3 años?
- ¿Han hecho pentest alguna vez? ¿Cuándo el último?
- ¿Qué cloud usan? ¿AWS, Azure, GCP, M365, Google Workspace, on-premise?

**Bloque D — Organización interna** (5-8 min)
- ¿Quién es el sponsor del proyecto dentro de la empresa?
- ¿Tienen equipo TI interno? ¿Cuántas personas? ¿Perfil?
- ¿Tienen equipo legal? ¿Interno o externo?
- ¿Quién firma los contratos? ¿Quién autoriza presupuestos?
- ¿Hay algún tema político interno que deba conocer? (Fusiones, reestructuraciones, conflictos.)

**Bloque E — Expectativas y restricciones** (5-10 min)
- ¿Qué plazo consideran razonable?
- ¿Cuál sería el desastre para ellos en este proyecto?
- ¿Qué han presupuestado o qué rango les parece razonable?
- ¿Quieren solo la declaración de conformidad o aspiran a la certificación ENAC formal?
- ¿Necesitan mantenimiento post-certificación?

**Bloque F — Escucha activa y salida de la reunión** (5 min)
- Marcos resume lo entendido.
- Marcos promete enviar propuesta formal en X días.
- Marcos pregunta si tienen alguna duda.

**B) Panel en vivo con outputs del Agente 18**

Mientras Marcos introduce las respuestas, el Agente 18 va calculando y mostrando en tiempo real:

- **Estimación preliminar de categoría ENS** (basada en Bloque A+B).
- **Estimación preliminar de madurez actual** (L1-L5 global, basada en Bloque C).
- **Estimación preliminar de esfuerzo** (semanas + rango de horas de Marcos).
- **Alcance inicial estimado** (servicios, sistemas, ubicaciones, personal).
- **Plazos viables** vs plazos deseados por el cliente.
- **Riesgos del proyecto detectados** (falta sponsor claro, plazo imposible, presupuesto bajo, dependencia de proveedor crítico).
- **Lista de quick wins potenciales**.

Todo esto queda serializado en la tabla `exploratory_meetings` con vinculación al lead.

#### 3.1.4 Generación automática de la propuesta formal (Motor 13 — Document Factory comercial)

Al cerrar la reunión exploratoria, Marcos pulsa **"Generar propuesta formal"**. El **Motor 13** (nuevo motor de generación comercial) usa el **Agente 19 — Redactor de Propuestas** con el contexto completo de la reunión y genera un documento DOCX/PDF de **10-20 páginas** con estética cuidada y plantilla profesional, en 3-5 minutos.

Estructura obligatoria de la propuesta (plantilla docxtpl `P-001`):

1. **Portada** con logo cliente + logo Marcos + título del proyecto + versión + fecha + validez de la oferta.
2. **Resumen ejecutivo** (1 página): contexto, categoría objetivo, plazo propuesto, inversión, resultado esperado.
3. **Contexto entendido** (1-2 páginas): lo que la plataforma ha comprendido del cliente durante la reunión exploratoria. Aquí es donde el cliente siente que lo hemos escuchado.
4. **Alcance propuesto** (2-3 páginas): servicios y sistemas en alcance, servicios fuera de alcance con justificación, ubicaciones, unidades organizativas, interconexiones, proveedores críticos.
5. **Metodología** (1-2 páginas): presentación de las 10 fases del ciclo (-1 a 8) aplicables al cliente, con explicación de cada una y su valor.
6. **Fases con cronograma** (1-2 páginas): diagrama de Gantt de alto nivel con hitos mensuales.
7. **Entregables por fase** (2-3 páginas): lista detallada de lo que el cliente recibe en cada fase. Con códigos E-XXX del Apéndice A para trazabilidad.
8. **Equipo** (0.5 página): Marcos como consultor principal; colaboradores si aplica (la plataforma tiene una tabla `collaborators` con perfil, rol, tarifa).
9. **Supuestos y exclusiones** (1 página): qué se asume, qué se excluye, qué pasa si los supuestos fallan.
10. **Condiciones económicas** (1 página): honorarios, hitos de pago (recomendado anticipo 20-30% + pagos mensuales contra hitos), formas de pago, IVA, retención si aplica.
11. **Criterios de aceptación** (0.5 página): qué tiene que pasar para que cada hito se considere cumplido.
12. **Gestión de riesgos del proyecto** (1 página): lista de riesgos identificados con probabilidad, impacto, plan de contingencia. Diferente del AR del sistema.
13. **Política de confidencialidad** (0.5 página): NDA mutuo propuesto, tratamiento de información sensible.
14. **Validez de la oferta** (0.2 página): 30 días por defecto, ajustable.
15. **Anexos**: perfil profesional de Marcos, casos de éxito anonimizados, certificaciones.

Estética: plantilla docxtpl con colores personalizables, tipografía profesional (Inter o similar), diagramas generados con Mermaid + rasterización a PNG, tablas limpias. La propuesta sale lista para enviar sin retoques manuales salvo casos excepcionales.

El Motor 13 también genera automáticamente un **email de envío** pre-redactado y la propuesta queda en `proposals` con estado `draft → sent → under_review → negotiating → won → lost`.

#### 3.1.5 Reunión de negociación y cierre

Cuando el cliente responde, Marcos agenda la segunda reunión. La plataforma vuelve a abrir una interfaz guiada, esta vez con plantilla `negotiation_meeting_templates`. El **Agente 20 — Asistente de Negociación** muestra:

- Resumen de la propuesta enviada.
- Puntos típicamente negociables (precio, plazos, alcance, forma de pago, responsabilidades).
- Rangos aceptables precargados por Marcos (ej: "plazo flexible hasta +2 semanas, precio flexible hasta -10%").
- Campos para capturar lo que el cliente pida modificar.

Mientras Marcos conversa, introduce los ajustes en la interfaz. El Agente 20 actualiza en tiempo real el modelo económico y muestra si el ajuste entra dentro del rango aceptable o si Marcos tiene que pensárselo. Si un ajuste queda fuera de rango, el Agente 20 propone alternativas (reducir alcance, extender plazo, eliminar entregables opcionales).

Al cerrar la reunión, Marcos pulsa **"Generar contrato"**. El **Motor 14 — Contracts Engine** (nuevo) genera:

**Contrato de servicios de consultoría ENS** (plantilla `C-001`) con:

1. Partes (datos mercantiles completos de ambas partes, extraídos del formulario inicial del lead).
2. Objeto del contrato (alcance acordado).
3. Plazos e hitos.
4. Honorarios y forma de pago.
5. **Cláusula CRÍTICA de recursos del cliente** (ver 3.1.6 más abajo).
6. Procedimiento de cambio de alcance (change request formal, con impacto en plazo y precio).
7. NDA mutuo.
8. Propiedad intelectual del trabajo realizado (de Marcos hasta el pago completo, del cliente tras el pago).
9. Limitación de responsabilidad.
10. Garantías y exclusiones.
11. Resolución del contrato.
12. Jurisdicción y legislación aplicable.
13. Firma electrónica avanzada (vía magic link con OTP).

El contrato se envía al cliente vía magic link tipo `firma_contrato`, el cliente firma electrónicamente, y el contrato queda archivado con sello de tiempo e inmutabilidad en el Evidence Vault.

#### 3.1.6 LA CLÁUSULA CRÍTICA — "Recursos del cliente"

**Esto es lo más importante de la Fase −1 y lo que más proyectos salva.** El 80% de los proyectos consultor se atascan porque el cliente no colabora en tiempo y forma, y si esto no está en contrato, Marcos no puede facturar el desfase.

La plataforma incorpora en TODOS los contratos una cláusula estándar (texto legal validado) que obliga al cliente a proporcionar:

**A) Recursos humanos:**
- Un interlocutor único con autoridad de decisión (`project sponsor` del cliente).
- Acceso al Responsable TI o equivalente con disponibilidad mínima garantizada (ej: 4h/semana en Fase 1, 8h/semana en Fase 3).
- Acceso al Responsable legal o DPO si existe.
- Acceso al órgano superior para firmas formales (Política, DdA, riesgo residual, nombramientos).

**B) Recursos técnicos:**
- Acceso de sólo lectura a la CMDB, directorio activo, configuración cloud, SIEM (via magic links de autorización puntual).
- Posibilidad de ejecutar escaneos autorizados durante ventanas pactadas.
- Entrega de documentación existente en los primeros 10 días laborables.

**C) Recursos organizativos:**
- Comunicación del CEO al personal anunciando el proyecto en los primeros 5 días laborables.
- Disponibilidad del personal para entrevistas de diagnóstico en plazos razonables.
- Acta de constitución del Comité de Seguridad firmada antes de finalizar la Fase 0.

**D) Consecuencias del incumplimiento (la parte clave):**
- Cada retraso imputable al cliente en las entregas anteriores genera un **parón documentado del cronograma** con justificación automática firmada por Marcos.
- El parón se factura como **"tiempo de espera"** a una tarifa acordada (ej: 50% de la tarifa normal de Marcos por hora bloqueada, con tope mensual).
- Si el parón supera X días consecutivos, Marcos puede **pausar el proyecto** y retomar con recálculo de plazos.
- Si el parón supera Y días consecutivos, Marcos puede **resolver el contrato** conservando los pagos ya realizados.

La plataforma tiene un **Tracker de Recursos del Cliente** (`client_commitments`) que registra cada compromiso, fecha prometida, fecha real, y calcula automáticamente los parones facturables. Cada semana genera un `informe de cumplimiento de recursos` que Marcos puede enviar al cliente como recordatorio preventivo.

#### 3.1.7 Setup administrativo al cerrar la venta

Cuando el contrato queda firmado, la plataforma ejecuta automáticamente un flujo Temporal `post_sale_setup` que:

1. Da de alta al cliente en la tabla `clients` con estado `activo`.
2. Crea el proyecto en `projects` con `categoria_objetivo`, `alcance_inicial`, `plazo_objetivo`, `presupuesto`.
3. Genera la **factura inicial del anticipo** (Motor 15 — Billing, nuevo) con formato fiscal español correcto (número correlativo, IVA 21%, retención del 15% si aplica para autónomos).
4. Crea el **repositorio colaborativo efímero** del proyecto (carpeta documental + canal de videollamadas LiveKit + gestor de magic links).
5. Crea el calendario con hitos del proyecto.
6. Inicializa el **plan de gestión de riesgos del proyecto** con los riesgos identificados en la propuesta.
7. Notifica a Marcos con el cuadro de mando del proyecto listo.

#### 3.1.8 Reparto de esfuerzo Fase −1

| Actividad | Marcos | Plataforma |
|---|---|---|
| Monitorización pipeline | 0% | 100% |
| Cualificación lead | 15 min | 45 min automáticos |
| Reunión exploratoria | 60 min (hablar con cliente) | Transcripción + análisis en vivo |
| Generación propuesta | 15 min (revisión) | 100% generación |
| Reunión negociación | 60 min (hablar con cliente) | Modelado en vivo + contrato |
| Setup post-venta | 5 min (confirmar) | 100% ejecución |
| **TOTAL** | **~2.5 horas por lead ganado** | **Todo lo demás** |

---

### 3.2 FASE 0 — PRE-ARRANQUE Y MOVILIZACIÓN (1-2 SEMANAS)

#### 3.2.1 Onboarding adaptativo por sector y rol (Motor 16 — Adaptive Onboarding)

**Esto es una de las innovaciones clave de v2.0.** En vez de un formulario genérico, la plataforma envía al cliente onboardings específicos según el sector y según el rol del receptor dentro de la empresa.

El **Motor 16** mantiene una matriz `onboarding_templates` con variantes por (sector × rol). Sectores soportados desde v2.0:

- Servicios profesionales (despachos, consultoras, gestorías)
- Fintech / servicios financieros
- Sanidad privada / tecnología médica
- Industria y manufactura
- Tecnología / SaaS / desarrollo software
- Retail / ecommerce
- Energía
- Logística y transporte
- Educación privada
- Otros (genérico)

Roles soportados:

- Dirección general / sponsor del proyecto
- Responsable TI / CTO
- Responsable legal / DPO
- Responsable RRHH
- Responsable de operaciones
- Responsable de compras / proveedores
- Usuario final (muestra del personal)

Cada combinación (sector × rol) tiene una plantilla de onboarding específica con las preguntas relevantes. Por ejemplo, al Responsable TI de una fintech le pregunta cosas distintas que al Responsable TI de una industria.

#### 3.2.2 Flujo operativo del onboarding

1. Marcos identifica en el contrato los interlocutores clave del cliente (sponsor, TI, legal, RRHH, compras).
2. Para cada interlocutor, la plataforma genera un **magic link personalizado** de tipo `onboarding` con OTP.
3. Marcos envía los magic links (plantilla de email automática con instrucciones).
4. Cada interlocutor recibe su enlace, introduce el OTP, y ve una interfaz web mobile-first con:
   - Bienvenida personalizada.
   - Explicación del proyecto ENS y por qué se le pide esta información.
   - Tiempo estimado (10-30 min según rol).
   - Botón "Guardar y continuar después" en cualquier momento.
   - Progreso visible.
5. Las preguntas son adaptativas: si contestan "sí" a "¿usáis AWS?", se desbloquea un bloque sobre AWS. Si contestan "no", se salta.
6. Para algunas preguntas técnicas, la plataforma ofrece **conectores directos** (ver 3.2.3).
7. Al finalizar, el onboarding queda marcado como completo y la información entra automáticamente en el `project knowledge graph` del cliente.

**Tooltips:** cada pregunta tiene un icono de ayuda (?) que abre un popup con explicación en lenguaje sencillo de por qué se pregunta esto, qué significa técnicamente, y un ejemplo. El cliente no necesita ser técnico para completar el onboarding.

#### 3.2.3 Conectores del onboarding

Cuando el responsable TI del cliente acepta, puede conectar directamente las siguientes fuentes vía OAuth/API, sin compartir credenciales con Marcos:

| Conector | Qué descubre |
|---|---|
| **Microsoft 365 / Entra ID** (Graph API, scopes read-only) | Usuarios, grupos, MFA, Conditional Access, licencias, dispositivos, Secure Score, SharePoint, Exchange, Intune. |
| **Google Workspace** (Admin SDK) | Usuarios, 2FA, grupos, dispositivos, Drive, políticas. |
| **AWS** (rol cross-account con `SecurityAudit` + `ViewOnlyAccess`) | Inventario de recursos, IAM, CloudTrail, Config, Security Hub, GuardDuty, S3, EC2, RDS, EKS. |
| **Azure** (suscripción con `Reader` + `Security Reader`) | Recursos, IAM, Defender for Cloud, Policy, Activity Log. |
| **GCP** (Service account con `Viewer` + `Security Reviewer`) | Recursos, IAM, SCC. |
| **GitHub / GitLab / Bitbucket** (PAT con scopes read) | Repositorios, ramas, secret scanning, SAST/SCA reports, pipelines. |
| **Active Directory on-premise** (vía agente ligero `ens-discovery-agent` que Marcos le pide al cliente instalar en una máquina Windows con permisos AD) | Usuarios, grupos, GPO, OUs. |
| **Okta / OneLogin / JumpCloud** (SSO) | Identidades federadas. |
| **Jira / Asana / Monday** | Proyectos en curso, especialmente los de TI/seguridad. |
| **Slack / Teams** (solo canales públicos del tenant del cliente, scope mínimo) | Nada de contenido privado; solo estructura de canales para mapear comunicación. |

**Protocolo MCP (Model Context Protocol):** el Motor 16 expone un servidor MCP local que permite a los agentes IA hacer queries estructuradas sobre la información descubierta, sin que los LLMs vean los datos crudos del cliente (solo agregados y resúmenes). Esto cumple RGPD y la política de minimización de datos.

**Importante RGPD:** todos los conectores son read-only, los datos se almacenan cifrados con clave por proyecto, y se eliminan al cierre del proyecto salvo que el cliente firme retención extendida.

#### 3.2.4 Reuniones Kick-off

**Kick-off ejecutivo** (1-1.5h): reunión con dirección + equipo asignado del cliente. La plataforma genera automáticamente:
- Presentación de 10-15 slides con el alcance, metodología, cronograma y expectativas.
- Acta de kick-off en formato DOCX/PDF que se firma al final vía magic link.
- Calendario macro del proyecto.

**Reunión de scoping detallado con dirección sola** (1h, sin TI presente): aquí Marcos descubre política interna, conflictos, expectativas reales, presupuesto real, qué pasa si la auditoría falla. Plantilla guiada `scoping_direccion_templates`. El output entra en una tabla `confidential_notes` que solo Marcos ve; no se comparte con TI ni con el cliente.

**Reunión de scoping técnico con TI sola** (1-2h, sin dirección presente): aquí TI cuenta lo que no se atreve a decir delante del jefe: deuda técnica, herramientas obsoletas, falta de recursos, frustración, sistemas antiguos. Plantilla `scoping_ti_templates`. Output también en `confidential_notes`.

**El trabajo de Marcos aquí es triangular ambas reuniones y mediar.** La plataforma ayuda mostrando side-by-side las discrepancias entre lo que dice dirección y lo que dice TI, con el **Agente 21 — Detector de Discrepancias** marcando los temas conflictivos.

#### 3.2.5 Definición formal del alcance (entregable E-009)

Tras las reuniones de scoping, el Motor 6 genera el **Documento de Alcance del SGSI ENS** con:

- Qué servicios entran y cuáles no, con justificación.
- Qué sistemas, aplicaciones, infraestructuras.
- Qué unidades organizativas.
- Qué ubicaciones físicas.
- Qué información se trata.
- Qué interconexiones con sistemas externos.
- Qué proveedores entran en el alcance.
- Qué exclusiones y por qué.
- **Diagrama de contexto** (frontera del sistema) generado automáticamente con Mermaid/Draw.io.

Este documento se firma por la dirección del cliente vía magic link. **Es la línea base.** Cualquier cambio posterior se gestiona como cambio formal con impacto en plazo y presupuesto (trigger del procedimiento E-203).

#### 3.2.6 Designación formal de roles ENS (entregable E-002 automatizado)

La plataforma genera automáticamente el **Acta de Nombramiento de Roles ENS** con los 4 roles obligatorios (Responsable de Información, Servicio, Seguridad, Sistema), pre-rellenada con sugerencias de personas extraídas del onboarding:

1. Marcos revisa la sugerencia del agente.
2. Se envía al sponsor del cliente vía magic link `firma_acta_nombramiento`.
3. El sponsor revisa, ajusta nombres/cargos si quiere, y firma.
4. El acta queda archivada firmada electrónicamente, con URL descargable.
5. Los roles quedan asignados en el `project knowledge graph` para referencia de todos los motores posteriores.

En Básica pueden coincidir 2-3 roles en la misma persona. En Media el Responsable de Seguridad debe ser independiente del Responsable del Sistema (regla dura del motor). En Alta debe tener dedicación significativa formal declarada.

#### 3.2.7 Constitución del Comité de Seguridad

Acta de constitución generada automáticamente (E-003) con: composición sugerida, funciones según CCN-STIC 805, periodicidad mínima (mensual en A, trimestral en M, semestral en B), quorum, procedimiento de convocatoria, toma de decisiones, modelo de actas. Se firma vía magic link. Primera reunión inaugural programada en las 2 primeras semanas con convocatoria automática.

#### 3.2.8 Plan de proyecto detallado (Motor 17 — Project Planning)

El **Motor 17** genera automáticamente:

**A) WBS (Work Breakdown Structure)** con todas las tareas del proyecto según categoría (B/M/A), con IDs, dependencias, responsables, fechas estimadas, esfuerzo estimado. Derivado del catálogo de tareas de la Parte 2 (Entregables).

**B) Cronograma Gantt** visual con hitos clave, ruta crítica marcada, holguras, dependencias. Exportable a MS Project (XML), CSV, PDF, PNG.

**C) Plan de reuniones recurrentes:**
- **Weekly de seguimiento operativo** (30 min, Marcos + sponsor TI del cliente) — Marcos puede desactivar si el cliente no lo necesita (dado que la plataforma hace casi todo autónomamente, las weeklies son mínimas).
- **Monthly del Comité de Seguridad** (1-1.5h, todos los roles).
- **Quarterly de dirección** (1h, sponsor + dirección).

La plataforma reserva automáticamente los huecos en el calendario del cliente (vía conector de calendario) o envía invitaciones por email.

**Cronograma típico por categoría:**
- **Básica:** 4-5 meses (aproximadamente 16-20 semanas).
- **Media:** 8-10 meses (aproximadamente 32-40 semanas).
- **Alta:** 12-18 meses (aproximadamente 48-72 semanas).

#### 3.2.9 Plan de comunicación (Motor 18 — Communication)

El **Motor 18** genera el plan de comunicación del proyecto con:

- **Status semanal escrito al sponsor** — 1 página, formato DOCX/PDF + PNG para imagen en email. Generado automáticamente cada viernes a las 16:00 con datos de la semana. Marcos revisa en 2 minutos y envía.
- **Status mensual al Comité** — 3-5 páginas con métricas, hitos alcanzados, hallazgos recientes, próximos pasos, riesgos. Generado automáticamente el día antes de la reunión mensual.
- **Status trimestral a dirección** — 1 página ejecutiva con estado del proyecto en semáforo (verde/ámbar/rojo), hitos logrados, riesgos críticos, decisiones que requieren la dirección.

Todos los formatos son plantillas `comms_templates` con estética profesional uniforme. Cero retoque manual.

#### 3.2.10 Plan de gestión de riesgos del proyecto (Motor 19 — Project Risk Management)

**Crítico: este es el plan de riesgos DEL PROYECTO CONSULTOR, no el análisis de riesgos del sistema del cliente (ese lo hace el Motor 2 MAGERIT).**

El **Motor 19** mantiene un catálogo precargado de **riesgos típicos del proyecto consultor ENS** (~30 riesgos base) que se instancian con el contexto del cliente:

1. El cliente no colabora en los plazos acordados.
2. La persona clave del cliente se va durante el proyecto.
3. El presupuesto se recorta a mitad del proyecto.
4. El alcance se expande sin change request formal.
5. Un proveedor crítico del cliente no responde al cuestionario.
6. El plazo del pliego es imposible incluso con la plataforma.
7. Aparece un incidente real durante la implantación y distrae al equipo.
8. El auditor exige cosas fuera del RD (criterios personales).
9. La entidad certificadora cambia sus criterios.
10. La dirección del cliente pierde interés.
11. Cambio de gobierno afecta al contrato público subyacente.
12. Reorganización interna del cliente.
13. Fusión o adquisición del cliente.
14. El cliente descubre otro consultor más barato a mitad de proyecto.
15. El IT del cliente sabotea pasivamente el proyecto por miedo.
16. Incidente de ciberseguridad real en medio del proyecto.
17. Dependencia de terceros no declarados inicialmente.
18. Falta de conocimiento técnico del cliente mayor de lo estimado.
19. Resistencia del personal a las nuevas políticas.
20. Conflicto entre roles designados.
21. La dirección no firma documentos clave en plazo.
22. El presupuesto cloud del cliente hace inviables ciertas medidas.
23. Cambio normativo durante el proyecto (nueva ITS, nueva guía CCN-STIC).
24. Marcos enferma o tiene una emergencia personal.
25. La plataforma tiene un bug crítico en medio del proyecto.
26. El cliente quiere cambiar de categoría ENS a mitad del proyecto.
27. El cliente descubre que no cumplía RGPD y exige paralelizar.
28. El auditor asignado es inexperto y alarga la auditoría.
29. El cliente no quiere contratar el retainer al final.
30. El cliente no paga un hito.

Cada riesgo con: probabilidad, impacto (en días/euros), plan de contingencia, plan de mitigación, dueño, trigger de escalado.

El Motor 19 mantiene un **dashboard vivo de riesgos del proyecto** que Marcos consulta semanalmente. Cuando un riesgo se materializa (el dueño marca el trigger), se dispara automáticamente el plan de contingencia.

#### 3.2.11 Setup del entorno colaborativo efímero (Motor 20 — Collaborative Workspace)

**Nueva funcionalidad clave:** aunque el cliente no tiene cuenta permanente, cada proyecto abre un **entorno colaborativo efímero** que dura exactamente lo que dura el proyecto (desde firma de contrato hasta cierre + 90 días de retención post-auditoría).

El entorno contiene:

1. **Carpeta documental compartida** (gestor documental minimalista integrado). El cliente sube archivos vía magic links temporales. Marcos tiene acceso completo desde su cuenta. Todos los archivos se versionan, se firman con hash al subir, y quedan en el Evidence Vault al cierre.

2. **Canal de videollamadas bajo demanda** basado en LiveKit (self-hosted en Hetzner). Cuando el cliente necesita una videollamada con Marcos, abre el magic link de su proyecto, pulsa "Solicitar videollamada ahora" o "Programar videollamada". Si Marcos está disponible y acepta, se genera una sala LiveKit instantánea con link cifrado, OTP, y grabación opcional (con consentimiento del cliente). Sustituye a Teams/Meet y no requiere cuenta de terceros.

3. **Feed de notificaciones del proyecto** que el cliente ve en su magic link persistente del proyecto: hitos alcanzados, documentos pendientes de su firma, evidencias pendientes de aportar, próximas reuniones.

4. **Chat asíncrono minimalista** para mensajes breves entre Marcos y el cliente, con historial cifrado. No sustituye el email formal pero agiliza la interacción operativa.

Al cierre del proyecto, Marcos elige: (a) destruir todo el entorno, (b) archivarlo inmutablemente en su backup cifrado, (c) extenderlo si se firma retainer.

#### 3.2.12 Reparto de esfuerzo Fase 0

| Actividad | Marcos | Plataforma |
|---|---|---|
| Envío onboardings | 10 min (selección interlocutores) | 100% generación + envío |
| Supervisión onboardings | 30 min (revisar respuestas) | 100% captura |
| Kick-off ejecutivo | 1.5h (estar en reunión) | Generación agenda + acta |
| Scoping dirección | 1h (estar en reunión) | Plantilla guiada |
| Scoping TI | 1.5h (estar en reunión) | Plantilla guiada |
| Doc alcance | 15 min (revisión) | 100% generación |
| Actas nombramiento | 10 min (revisión) | 100% generación |
| Plan proyecto | 20 min (ajustes finos) | 100% generación WBS + Gantt |
| Plan comunicación | 5 min (confirmación) | 100% generación |
| Plan riesgos proyecto | 15 min (validación) | 100% precarga |
| Setup entorno | 0 min | 100% automático |
| **TOTAL** | **~5.5 horas** | **Todo lo demás** |

---

### 3.3 FASE 1 — DIAGNÓSTICO EXHAUSTIVO (2-6 SEMANAS SEGÚN CATEGORÍA)

Esta fase es de descubrimiento puro. No produces documentos finales; produces **conocimiento** que alimenta las fases posteriores.

#### 3.3.1 Diagnóstico organizativo (Motor 21 — Organizational Diagnosis)

El **Motor 21** ejecuta cuatro sub-diagnósticos organizativos, todos alimentados por los onboardings, las reuniones de scoping, y las queries al knowledge graph del cliente.

**A) Mapa de stakeholders** (Agente 22 — Analista de Stakeholders). No solo el organigrama. Identifica:
- Quién toma decisiones reales.
- Quién tiene poder de bloqueo (veto informal).
- Quién es aliado del proyecto.
- Quién es escéptico o activo opositor.
- Quién está en burnout.
- Quién está nuevo (< 6 meses).
- Quién está a punto de irse.
- Relaciones interpersonales críticas (conflictos históricos, alianzas).

Output: grafo en Apache AGE con nodos `Person` y aristas tipadas (`reports_to`, `allies_with`, `conflicts_with`, `blocks`, `sponsors`). Marcos ve el grafo visualizado con d3.js y puede anotar. Este mapa se mantiene en `confidential_notes` (solo Marcos lo ve).

**B) Inventario de procesos de negocio** (Agente 23 — Mapeador de Procesos). Entrevistas guiadas + análisis de la información del onboarding. Para cada proceso:
- Qué hace (descripción).
- Quién lo ejecuta.
- Qué sistemas usa.
- Qué información toca.
- Criticidad para el negocio (baja/media/alta/crítica).
- Si es cara al cliente público o interno.
- Estacionalidad (si la hay).

Output: tabla `business_processes` con todos los procesos del cliente, diagrama BPMN simplificado generado con Mermaid, y alimentación directa al BIA de la Fase 2.

**C) Inventario de obligaciones legales y contractuales**. ENS no es lo único. El Agente 24 (Detector de Obligaciones Cruzadas) analiza el sector y detecta automáticamente las obligaciones aplicables al cliente:
- **RGPD / LOPDGDD** (casi siempre).
- **PCI-DSS** (si procesa pagos con tarjeta).
- **Normativa sectorial**: sanitaria, financiera, energética, transporte, 5G, infraestructuras críticas.
- **NIS2** (cuando esté transpuesta en España).
- **DORA** (si es entidad financiera o TPP crítico).
- **AI Act** (si desarrolla o usa sistemas de IA de alto riesgo).
- **Obligaciones específicas del cliente público** beyond ENS (el pliego puede exigir más).

Output: tabla `legal_obligations` con cada obligación, su base normativa, aplicabilidad, estado de cumplimiento estimado, cruce con medidas ENS (palanca para aprovechamiento).

**D) Inventario de proyectos en curso del cliente**. Lo que el cliente ya está haciendo en seguridad o transformación, para aprovechar y no duplicar esfuerzo. A veces el proyecto ENS se monta encima de una migración a cloud o de una implantación de ERP. Extraído del onboarding del responsable TI y de los conectores Jira/Asana.

Output: tabla `client_projects_in_flight` con solapes detectados y recomendaciones de aprovechamiento.

#### 3.3.2 Diagnóstico técnico automatizado (Motor 22 — Technical Discovery)

**Esta es la otra gran innovación de v2.0.** El Motor 22 ejecuta el descubrimiento técnico completo usando los conectores autorizados en Fase 0.

**A) Discovery de activos:**

- **Red interna**: escaneo activo con Nmap (desde agente en red del cliente o via VPN autorizada), zmap si hay rangos grandes.
- **Cloud**: AWS Config + Resource Explorer, Azure Resource Graph, GCP Cloud Asset Inventory, M365 Admin API, Google Workspace Admin.
- **Shadow IT**: análisis de logs DNS y proxies del cliente buscando dominios SaaS conocidos, cruce con MRR de tarjetas de crédito si el cliente lo autoriza (extracto corporativo).
- **CMDB existente**: import automático si el cliente tiene ServiceNow, Freshservice, GLPI, iTop.
- **Bases de datos**: discovery con herramientas read-only (desde mysql/postgres information_schema, SQL Server catalog views, etc.).
- **Endpoints**: desde MDM/EDR si existen (Intune, Jamf, CrowdStrike, SentinelOne API).
- **IoT / dispositivos no estándar**: detección por fingerprint en la red.

Output: tabla `discovered_assets` con ~cientos-miles de filas, clasificados por tipo MAGERIT, con propietario inferido, ubicación, criticidad propuesta. **Esto alimenta directamente el inventario del AR (Motor 2)**.

**B) Discovery de identidades:**

Export del directorio (AD / Entra ID / Google Workspace) y análisis automático:
- Cuentas activas vs inactivas (>90 días sin login).
- Cuentas privilegiadas (admins globales, admins de dominio, sudoers).
- Cuentas de servicio sin dueño documentado.
- Cuentas compartidas o genéricas.
- Última fecha de login de cada cuenta.
- MFA activo / no activo por cuenta.
- Cumplimiento de la política de contraseñas (longitud, complejidad, caducidad).
- Permisos efectivos reales (tras expansión de grupos anidados).
- Accesos cruzados entre sistemas.

Output: tabla `discovered_identities` y conjunto de alertas clasificadas por severidad (ej: "5 cuentas privilegiadas sin MFA" → crítico). Cada alerta se vuelca como gap en el backlog del Motor 5.

**C) Discovery de datos:**

- Dónde vive la información sensible: bases de datos con datos personales, ficheros compartidos, repositorios cloud, correo, SaaS.
- Clasificación inicial por patrones (DNI, NIF, IBAN, datos de salud, tarjetas).
- Volumen estimado.

Output: tabla `discovered_data_stores` con clasificación inicial de sensibilidad. Alimenta la valoración de información del Motor 1.

**D) Discovery de configuraciones:**

- **Windows**: CLARA scan del CCN si aplica.
- **Linux**: Lynis scan.
- **CIS-CAT** para comparativa contra CIS Benchmarks.
- **M365 Secure Score** lectura via Graph.
- **AWS Security Hub** findings.
- **Azure Defender for Cloud** recomendaciones.
- **GCP Security Command Center** findings.
- **Firewall perimetral**: análisis de reglas si el cliente comparte export (config dump).
- **TLS de servicios expuestos**: testssl.sh + SSL Labs scan automático de todos los FQDN descubiertos.
- **DNS**: SPF, DKIM, DMARC, DNSSEC de todos los dominios del cliente.
- **Parches**: estado via WSUS/SCCM si aplica, Intune, o agente.
- **Antimalware/EDR**: cobertura real.

Output: tabla `discovered_configurations` con gaps vs baseline.

**E) Discovery de vulnerabilidades:**

- Scan inicial con **OpenVAS / Greenbone** de toda la infraestructura autorizada.
- **Nuclei** con templates ENS sobre servicios web expuestos.
- **Trivy/Grype** sobre imágenes de contenedores.
- **Semgrep** sobre repositorios de código si aplica.

Output: `vulnerability_inventory` clasificado por CVSS, con exploitable marcadas, y mapeo a medidas ENS afectadas.

**F) Análisis de logs y monitorización existente:**

- ¿Hay SIEM? ¿Cuál? ¿Qué se loguea?
- ¿Qué retención?
- ¿Hay alertas? ¿Alguien las mira?
- ¿Cobertura de auditoría según op.exp.8?

Output: `logging_capability_assessment` con gaps.

**G) Mapeo de flujos de datos (Data Flow Diagrams):**

El Agente 25 genera automáticamente los DFD del cliente a partir de los datos descubiertos, con:
- Entrada de información (fuentes externas).
- Procesamiento interno.
- Almacenamiento.
- Salida (destinatarios externos).
- Quién puede tocarla en cada fase.

Diagramas exportables en SVG/PNG para el BIA.

**H) Diagnóstico de continuidad:**

- Inventario de backups: qué se respalda, frecuencia, dónde, cifrado, retención, última prueba de restauración.
- DRPs existentes si los hay.
- SLAs con proveedores.
- SPOFs (single points of failure) técnicos detectados.

#### 3.3.3 Diagnóstico de proveedores

El Motor 21 compila el **inventario exhaustivo de proveedores** del cliente, cruzando datos del onboarding del responsable de compras con lo descubierto en otros sitios:

- Cloud providers (IaaS, PaaS, SaaS).
- Mantenimiento, desarrollo, soporte.
- Housing, hosting, telcos.
- Auditores externos, consultores externos (incluido Marcos).
- Servicios de limpieza con acceso a oficinas.
- Destrucción documental.
- Mensajería con acceso a información.
- Subcontratas de RRHH (nóminas, selección).

Para cada uno: contrato vigente, cláusulas existentes (análisis automático con Agente 6 si el cliente sube los contratos), cláusulas faltantes, vencimiento, criticidad, cumplimiento ENS del proveedor (si está en el Registro de Entidades Conformes del CCN), plan de acción.

#### 3.3.4 Diagnóstico documental

Inventario y revisión de TODA la documentación de seguridad existente del cliente:
- Políticas vigentes, obsoletas, contradictorias.
- Procedimientos.
- Manuales técnicos.
- Diagramas de arquitectura.
- Documentación de aplicaciones.
- Actas de reuniones anteriores (Comité existente si lo había).
- Informes de auditorías previas (RGPD, ISO 27001, SOC 2, cualquier otra).
- Pentests anteriores.
- Notas internas.

El **Agente 4 (Redactor)** en modo analizador hace un **gap analysis documental**: qué existe y sirve, qué existe y hay que actualizar, qué falta y hay que crear desde cero. Output: `document_inventory_analysis`.

#### 3.3.5 Diagnóstico de personas

Madurez en seguridad del personal:
- Encuestas anónimas (10-15 preguntas) enviadas vía magic link al personal. Sin cuentas.
- Test de phishing baseline opcional (con GoPhish, consentimiento de dirección).
- Walkthrough físico por oficinas (Marcos lo hace personalmente o pide al cliente hacerlo con checklist y fotos).

Output: `people_maturity_assessment` con puntuación global y recomendaciones para el plan de formación.

#### 3.3.6 Entregable único de la Fase 1 — Informe de Diagnóstico Inicial (E-090)

El **Motor 6 (Document Factory)** genera automáticamente un documento DOCX/PDF de **30-80 páginas** según categoría con:

1. **Resumen ejecutivo** (1-2 páginas para dirección).
2. **Contexto y alcance confirmado**.
3. **Hallazgos por dominio**:
   - Organizativo.
   - Técnico (activos, identidades, datos, configuraciones, vulnerabilidades).
   - Proveedores.
   - Documental.
   - Personas.
4. **Mapa de calor de criticidad** (heatmap generado automáticamente).
5. **Comparativa contra ENS por categoría objetivo** (preview del gap analysis).
6. **Estimación de esfuerzo** para alcanzar la categoría objetivo.
7. **Riesgos del proyecto identificados** (ampliación del plan de la Fase 0).
8. **Quick wins** (cosas con poco esfuerzo e impacto alto — el Agente 16 Quick Wins los genera).
9. **Recomendaciones para Fase 2**.

Este informe se presenta al Comité del cliente con 1-2 horas de reunión. Es el momento donde el cliente toma consciencia real de en qué se ha metido. **Es también el momento de confirmar la categoría ENS objetivo** (puede haber cambiado respecto a la estimación inicial).

#### 3.3.7 Reparto de esfuerzo Fase 1

| Actividad | Marcos | Plataforma |
|---|---|---|
| Diagnóstico organizativo | 3-5h (entrevistas + validación) | Automatización completa del resto |
| Diagnóstico técnico | 1h (supervisión scans) | 100% ejecución automática |
| Diagnóstico proveedores | 1h (revisión) | 100% cruzado |
| Diagnóstico documental | 2h (validación) | Análisis con Agente 4 |
| Diagnóstico personas | 1h (walkthrough físico si procede) | Encuestas + análisis |
| Generación informe | 30 min (revisión y retoques) | 100% generación |
| Presentación al Comité | 2h (reunión) | Slides generadas |
| **TOTAL** | **~10-12 horas** | **Todo lo demás** |

---

### 3.4 FASE 2 — DISEÑO DEL SGSI ENS (3-8 SEMANAS)

Fase donde se produce la **documentación formal** del SGSI. Todo esto ya está detallado en la Parte 2 (Entregables Exhaustivos) por códigos `E-XXX`; aquí solo se indica el flujo operativo.

#### 3.4.1 Categorización formal (Motor 1)

Acta de categorización del Comité (E-012) con:
- Valoración de cada información en D/I/C/A/T (el Motor 1 propone con base en el diagnóstico, Marcos valida, el Responsable de la Información firma vía magic link).
- Valoración de cada servicio en D/I/C/A/T.
- Determinación de la categoría del sistema (B/M/A) por aplicación de la **regla del máximo** (determinista, sin alucinación).
- Justificación documentada generada por Agente 4.
- Lista de excepciones razonadas si las hay.

#### 3.4.2 Política de Seguridad de la Información (E-001)

Generación automática vía Motor 6 usando la plantilla validada contra CCN-STIC 805. No genérica: adaptada a la organización con datos del diagnóstico. Revisión legal previa en M y A (Marcos puede activar "modo revisión legal" que marca los huecos que requieren confirmación jurídica). Aprobada por el órgano superior vía magic link. Difusión formal automática con registro de difusión y acuse de recibo a todo el personal (E-008).

#### 3.4.3 Cuerpo normativo completo (E-100 a E-126)

Las **27 políticas** listadas en la Parte 2 se generan por lotes con el Motor 6. Marcos revisa una a una (puede agruparlas) vía una interfaz de review masiva tipo kanban. El cliente las aprueba vía magic link con firma del aprobador correspondiente según el Reglamento del Comité.

Lista completa con IDs E-100 a E-126 en la Parte 2.6. Las plantillas docxtpl reales están catalogadas en `ENS_PLATFORM_PARTE_2_ENTREGABLES.md` bloque 5. **Advertencia de construcción:** estas 27 plantillas requieren redacción legal real por un consultor ENS senior o un abogado TIC — ver Apéndice L (Riesgos de construcción) para el detalle.

#### 3.4.4 Procedimientos operativos detallados (E-200 a E-234)

Los **35 procedimientos** listados en la Parte 2 se generan con el Motor 6. **Diferencia clave:** las políticas dicen QUÉ, los procedimientos dicen CÓMO paso a paso. Cada procedimiento con actores, entradas, pasos, salidas, registros, periodicidad, indicadores.

#### 3.4.5 Plantillas de registros operativos (E-300 a E-325)

Los **26 registros** que evidencian la ejecución de los procedimientos. Plantillas XLSX + implementación en la propia plataforma para captura directa. Cuando un procedimiento se ejecuta, su registro se rellena en la plataforma y genera evidencia auditable con timestamp.

#### 3.4.6 Análisis de riesgos formal (Motor 2 — MAGERIT)

Metodología MAGERIT v3:
- **B**: light, inventario simplificado.
- **M**: formal completo con amenazas aplicadas una a una.
- **A**: formal + exportación a PILAR obligatoria.

El Motor 2 genera todo el AR (E-020 a E-030) automáticamente a partir del inventario descubierto en Fase 1. El Responsable de la Información y el RSEG validan. La dirección aprueba el riesgo residual vía magic link (E-028) — **sin esta firma el AR no vale para auditoría**.

#### 3.4.7 Plan de tratamiento de riesgos (E-027)

Para cada riesgo por encima del umbral: decisión (mitigar/aceptar/transferir/evitar), salvaguardas a implantar, responsable, plazo, coste estimado, riesgo residual esperado.

#### 3.4.8 Declaración de Aplicabilidad (E-040)

El Motor 3 (DdA Engine) genera la DdA completa con las **73 medidas** tratadas una a una: aplicabilidad, refuerzos según categoría, estado actual (derivado del Evidence Vault), estado objetivo, medidas compensatorias si aplican (con referencia a CCN-STIC 819), evidencias previstas, responsable de implantación. Firma del RSEG vía magic link.

#### 3.4.9 Plan de Adecuación (E-050)

El Motor 5 (Obligations & Planning) genera el Plan de Adecuación completo según CCN-STIC 806 con: política, categorización, AR, DdA, insuficiencias (gap analysis), **plan de mejora con WBS y Gantt detallado**. Aprobado por dirección.

#### 3.4.10 Plan de continuidad (E-400 a E-406)

Motor 6 genera BIA, BCP, DRP, plan de comunicaciones de crisis, plan de pruebas. El BIA (E-400) es **especialmente crítico** para Marcos: el Agente 23 (Mapeador de Procesos) lo genera a partir del inventario de procesos de la Fase 1, con RTO/RPO por proceso, impactos, dependencias. Marcos revisa.

#### 3.4.11 Plan de formación y concienciación (E-500)

Motor 6 genera el plan anual con audiencias, módulos, calendario, materiales, evaluación, presupuesto, adaptado al sector del cliente y a los hallazgos del diagnóstico de personas.

#### 3.4.12 Reparto de esfuerzo Fase 2

| Actividad | Marcos | Plataforma |
|---|---|---|
| Revisión categorización | 30 min | 100% cálculo |
| Revisión Política | 30 min | 100% generación |
| Revisión 27 políticas | 3-4h (review masivo) | 100% generación |
| Revisión 35 procedimientos | 4-5h | 100% generación |
| Revisión AR | 2h | 100% cálculo y redacción |
| Revisión DdA | 1-2h | 100% generación |
| Revisión Plan Adecuación | 30 min | 100% generación |
| Revisión BCP/BIA | 2h | 100% generación |
| Revisión Plan Formación | 30 min | 100% generación |
| **TOTAL** | **~15-18 horas** | **Todo lo demás** |

---

### 3.5 FASE 3 — IMPLANTACIÓN (LA MÁS LARGA: 2-12 MESES)

Aquí es donde el proyecto se gana o se pierde. La Fase 3 es **continua** y se gestiona a través del Motor 5 (Obligations & Planning) convirtiendo cada gap en una obligación con uno de los **4 modos de ejecución**:

1. **`consultor_genera`**: Marcos genera el entregable con la plataforma, el cliente lo firma.
2. **`cliente_aporta_evidencia`**: magic link con instrucciones ultra-concretas; el cliente sube captura/export.
3. **`accion_tecnica_remota_autorizada`**: magic link con comando one-liner que el cliente ejecuta y su output se sube a la plataforma.
4. **`accion_manual_cliente`**: magic link con instrucciones paso a paso, cliente ejecuta, sube validación.

#### 3.5.1 Implantación organizativa

- **Operación del Comité de Seguridad** con reuniones regulares (actas, orden del día, acuerdos, seguimiento). El **Motor 9 (Audit Preparation)** prepara automáticamente el orden del día de cada reunión con acuerdos previos pendientes, hallazgos abiertos, evidencias caducando, decisiones pendientes.
- **Operación de procedimientos**: desde el día 1 los procedimientos se ejecutan y dejan registro en las plantillas del Motor 6. Los registros son las evidencias vivas del sistema.
- **Difusión de políticas y normativa**: formalizada con acuse de recibo vía magic link por empleado.
- **Formación inicial al personal**: sesión de inducción ENS con materiales generados por Motor 6. Marcos puede delegar la sesión en e-learning asíncrono (la plataforma incluye un mini-LMS).
- **Establecimiento del programa de mejora continua** (PDCA).

#### 3.5.2 Implantación técnica (la más pesada)

El **Motor 5** instancia automáticamente obligaciones por familia según el gap analysis:

**Identidades y accesos**: limpieza de cuentas inactivas, MFA universal (en M y A), política de contraseñas reforzada, RBAC formal, SoD, PAM (en M y A), revisiones periódicas, provisioning/deprovisioning automatizado, federación SSO.

**Endpoints**: EDR moderno con 100% cobertura, cifrado de discos, hardening según CCN-STIC 521/522/570 o CIS, MDM en móviles, DLP endpoint (A).

**Red y comunicaciones**: limpieza de reglas de firewall, segmentación VLANs, microsegmentación o ZT (A), IDS/IPS (M y A), NDR (A), VPN robusta, bastión, TLS 1.3, SPF/DKIM/DMARC + DNSSEC, WAF (M y A).

**Servidores y aplicaciones**: bastionado, gestión de parches con SLA, scanner de vulnerabilidades, gestión de configuraciones (Ansible/Puppet/Chef), logs centralizados, monitorización de integridad.

**Cloud**: CIS Benchmarks, CSPM activo (M y A), CWPP (A), IAM cloud, logging control plane, backup nativo, BYOK/HYOK (A), regiones UE.

**Datos**: cifrado en reposo, cifrado en tránsito, KMS/HSM, clasificación, DLP, backups con pruebas de restauración.

**Aplicaciones (si hay desarrollo)**: SSDLC, SAST/SCA en CI/CD, DAST (M y A), SBOM, code review, threat modeling (A), pentest pre-producción (A), gestión de secretos.

**Monitorización y respuesta**: SIEM (M y A), casos de uso, alertas accionables, SOC interno o contratado, procedimientos de respuesta, integración con LUCIA.

**Continuidad**: backups cifrados, pruebas de restauración, DRP probado, sitio alternativo (A).

**Físico**: control accesos, registro visitas, CCTV, SAI, antiincendios, climatización redundante (A).

Para cada obligación, el Motor 5 decide el modo de ejecución óptimo según la naturaleza del gap, genera el magic link correspondiente, lo envía al interlocutor adecuado, y trackea su estado.

#### 3.5.3 Renegociación contractual con proveedores

Coordinación con el Motor 14 (Contracts Engine) para generar las **cláusulas adicionales ENS/RGPD** que hay que firmar con cada proveedor crítico. Flujo:

1. Motor 14 detecta proveedores críticos (del Fase 1).
2. Para cada uno, analiza el contrato existente con Agente 6.
3. Identifica cláusulas faltantes (ENS, Art. 28 RGPD, notificación incidentes, derecho auditoría, retención, subcontratación).
4. Genera **adenda contractual** tipo con redacción validada.
5. Marcos envía al cliente vía magic link para que el cliente la envíe al proveedor (la plataforma NO gestiona directamente al proveedor; el cliente es quien tiene la relación).
6. Motor 14 trackea estado: enviada, firmada por proveedor, archivada en Evidence Vault.

#### 3.5.4 Coordinación con RGPD

Si el cliente tiene RGPD a medias, se paraleliza automáticamente:
- Revisión y actualización del RAT.
- Revisión de bases legales.
- Revisión de cláusulas informativas y política de privacidad pública.
- Revisión de contratos Art. 28.
- EIPDs donde aplique.
- Procedimiento de brechas operativo.
- Coordinación con DPO.

El **Agente 6 (Contratos)** y el **Agente 24 (Obligaciones Cruzadas)** lideran este trabajo.

#### 3.5.5 Programa de formación ejecutado

La plataforma incluye un **mini-LMS** para clientes sin e-learning propio:
- Contenidos precargados por audiencia (todos, técnicos, admins, dirección, DPO).
- Envío de invitaciones vía magic link al personal del cliente.
- Tracking de completitud y puntuación.
- Certificados individuales automáticos.
- Simulacros de phishing trimestrales via GoPhish autohospedado con reports al cliente.

#### 3.5.6 Quick wins continuos

El **Agente 16 (Quick Wins)** publica en el feed del cliente cada 1-2 semanas una nueva quick win cerrada (ejemplo: "MFA activado en el 100% de las cuentas administrativas", "Primera política aprobada y difundida", "Primer simulacro de phishing ejecutado — tasa de clicks baja del 18% al 6%"). Mantiene la motivación del cliente y le hace ver progreso tangible.

#### 3.5.7 Gestión del cambio durante la implantación

Durante los meses de implantación es muy probable que el cliente cambie cosas: nuevo proveedor, nuevo sistema, migración a cloud, nuevo país, nueva regulación. El **Motor 17 (Project Planning)** tiene un submódulo `change_management` que:
1. Detecta cambios del contexto (via conectores) o los recibe de Marcos.
2. Evalúa impacto en el alcance ENS.
3. Formaliza el cambio como change request.
4. Ajusta el plan, plazos, presupuesto.
5. Comunica al Comité y a dirección.

#### 3.5.8 Reparto de esfuerzo Fase 3

La Fase 3 es la más larga en calendario pero Marcos no debe dedicarle proporcionalmente más horas — la plataforma hace el trabajo, Marcos valida.

| Actividad por semana típica | Marcos | Plataforma |
|---|---|---|
| Revisión magic links entrantes | 1h/semana | Auto-tracking |
| Weekly del Comité / seguimiento | 30 min/semana | Convocatoria + acta |
| Revisión de evidencias recibidas | 1h/semana | Auto-validación |
| Escalado de bloqueos | 30 min/semana | Auto-detección |
| **TOTAL** | **~3h/semana × 16-40 semanas = 50-120h** | **Todo lo demás** |

---

### 3.6 FASE 4 — VERIFICACIÓN INTERNA (3-6 SEMANAS)

#### 3.6.1 Auditoría interna inicial (gap intermedio)

A los 2-3 meses de Fase 3, no al final. Motor 9 + Agente 11 (Auditor Interno Virtual) ejecutan una auditoría interna simulada con la profundidad de un auditor ENAC real. Detecta desviaciones temprano. Genera informe E-700.

#### 3.6.2 Pentesting automatizado (Motor 8)

Motor 8 ejecuta el pipeline de pentesting adaptado a la categoría:

- **Básica**: scan externo básico + análisis de configuración pública (recomendado, no obligatorio).
- **Media**: pentest externo + interno obligatorio.
- **Alta**: pentest externo + interno + Red Team formal con MITRE Caldera.

Herramientas open source orquestadas: Nmap, Nuclei, OpenVAS, ZAP, Metasploit, Caldera, Prowler, CLARA, Lynis, Trivy, Semgrep, testssl.sh. Cada finding con mapeo a medida ENS + MITRE ATT&CK. Informes en formato auditor español (E-702, E-703, E-704).

Protocolo MCP para orquestación: el Motor 8 expone un servidor MCP local que permite al Agente 9 (Orquestador de Pentest) decidir dinámicamente qué herramienta lanzar en cada momento según lo que va descubriendo, sin hardcodear el pipeline.

#### 3.6.3 Simulacro de phishing (E-705)

Ejecutado con GoPhish self-hosted. Campaña de ~100-500 correos, landing pages realistas pero sin explotación, tracking de clicks, reports al cliente por departamento.

#### 3.6.4 Simulacro tabletop de incidente (E-706)

Reunión de 2-4h donde se simula un incidente y se observa la respuesta del equipo. El **Agente 26 (Coach de Auditoría y Crisis)** genera el guion de la simulación con escenario realista adaptado al sector del cliente, preguntas graduales, puntos de decisión. Marcos facilita la reunión. Informe final con hallazgos.

#### 3.6.5 Red Team (solo Alta) (E-704)

Ejercicio adversarial real, 2-4 semanas. Marcos lo contrata a un especialista externo (la plataforma mantiene una red de especialistas con tarifas) o lo ejecuta con el Motor 8 orquestando Caldera en modo completo. Objetivo: simular atacante avanzado intentando comprometer los objetivos críticos del cliente.

#### 3.6.6 Auditoría interna pre-formal completa (E-701)

La "segunda" auditoría interna, más exhaustiva que la inicial. Cubre las 73 medidas. Genera la lista final de hallazgos y el plan de remediación antes de la auditoría externa.

#### 3.6.7 Revisión y actualización de DdA + AR

Tras las auditorías internas, coherencia actualizada.

#### 3.6.8 Generación de evidencias frescas

Motor 7 (Evidence Collection) verifica que **todas las evidencias están vigentes** (no caducadas). Si alguna está caducada, genera automáticamente magic link al cliente para renovarla.

#### 3.6.9 Informe del estado de la seguridad (formato INES)

Motor 9 genera el informe en formato INES (CCN-STIC 824) como ensayo interno. En sector privado no es obligatorio reportar a INES, pero tener el informe demuestra madurez.

#### 3.6.10 Revisión por la dirección (E-006)

Reunión formal anual del órgano de gobierno. Motor 6 genera el dossier completo de la reunión con indicadores, cumplimiento, incidentes, hallazgos, decisiones. Acta firmada vía magic link.

#### 3.6.11 Reparto de esfuerzo Fase 4

| Actividad | Marcos | Plataforma |
|---|---|---|
| Supervisión auditoría interna | 2h | Motor 9 + Agente 11 |
| Supervisión pentesting | 3h | Motor 8 ejecuta |
| Simulacro phishing | 1h | GoPhish auto |
| Simulacro tabletop | 3h (facilitar) | Agente 26 guion |
| Red Team (Alta) | 5h (coordinar) | Motor 8 o especialista externo |
| Revisión DdA/AR | 2h | Motor 2/3 |
| Revisión por dirección | 2h (reunión) | Motor 6 dossier |
| **TOTAL** | **~15-20 horas** | **Todo lo demás** |

---

### 3.7 FASE 5 — PREPARACIÓN DE AUDITORÍA FORMAL (2-4 SEMANAS)

#### 3.7.1 Selección de la entidad certificadora

Solo en Media y Alta (en Básica basta con Declaración de Conformidad firmada por Marcos + cliente, sin auditor externo).

Motor 6 genera automáticamente un RFP a enviar a 3-5 entidades certificadoras acreditadas por ENAC. La plataforma mantiene una tabla `certification_entities` con las entidades autorizadas para ENS en España (lista del CCN), con histórico de proyectos previos, rigor, precio, tiempos. Marcos selecciona candidatas, envía RFP vía email automatizado, recibe ofertas, compara, selecciona.

#### 3.7.2 Reunión preparatoria con la certificadora

1h de reunión. Acuerdo de cronograma, NDA mutuo, intercambio previo de documentación (la plataforma envía el pre-dossier), expectativas.

#### 3.7.3 Limpieza documental final

Motor 9 ejecuta una checklist de limpieza final:
- Verificar todas las firmas.
- Verificar fechas vigentes.
- Verificar ubicaciones y accesibilidad.
- Verificar consistencia entre documentos.
- Detectar cualquier contradicción.

Si encuentra algún problema, genera alerta a Marcos con el item concreto a corregir.

#### 3.7.4 Coaching del personal clave

**Agente 12 (Coach del Cliente)** y **Agente 26 (Coach de Auditoría)** generan sesiones de coaching para el personal clave que se va a entrevistar con el auditor: CTO, admins, DPO, RRHH, dirección. Cada sesión incluye:

- Preguntas tipo auditor ENAC que realmente suelen hacerse.
- Respuestas modelo (lo que el auditor espera oír, sin recetas para mentir).
- Rúbrica de evaluación.
- Consejos de comunicación: no improvisar, no dar de más, no defenderse, mostrar evidencia.

Las sesiones son **magic links de autoestudio** que el personal del cliente completa en 30-60 minutos, o reuniones en directo vía LiveKit con Marcos facilitando.

#### 3.7.5 Generación del pack del día D

El **Agente 13 (Generador de Dossier Final)** genera el dossier completo de auditoría en formato carpeta física (imprimible) + digital navegable:

Estructura exacta según la sección 2.15 del doc maestro (y ya validada por auditores ENAC españoles):
- 00 Índice maestro + Resumen ejecutivo
- 01 Gobierno
- 02 Categorización
- 03 Análisis de Riesgos
- 04 Declaración de Aplicabilidad
- 05 Plan de Adecuación
- 06 Normativa (todas las políticas)
- 07 Procedimientos
- 08 Registros de operación de los últimos 6 meses
- 09 Evidencias por medida del Anexo II (carpeta por cada una de las 73)
- 10 Plan de Continuidad
- 11 Formación y Concienciación
- 12 Proveedores
- 13 Informes técnicos
- 99 Matriz cruzada medida × evidencia × documento (XLSX)

Generado como ZIP firmado + PDF maestro navegable + matriz cruzada del 99 en XLSX.

#### 3.7.6 Comunicación interna del cliente

Motor 6 genera email del CEO al personal informando de la auditoría, qué se espera, cómo comportarse. Cliente envía.

#### 3.7.7 Reparto de esfuerzo Fase 5

| Actividad | Marcos | Plataforma |
|---|---|---|
| Selección certificadora | 2h | RFP automático |
| Reunión preparatoria | 1h | Pre-dossier envío |
| Limpieza documental | 1h (revisión alertas) | Motor 9 check |
| Coaching personal | 2h (sesiones en directo) | Agente 26 guiones |
| Pack día D | 30 min (revisión final) | 100% generación |
| **TOTAL** | **~6-7 horas** | **Todo lo demás** |

---

### 3.8 FASE 6 — AUDITORÍA EXTERNA (1-3 SEMANAS)

**Aquí el papel de Marcos es facilitador, no sustituto.** El cliente responde al auditor, Marcos ayuda a contextualizar, aporta evidencias adicionales si las hay, gestiona tiempos, media en los descansos.

#### 3.8.1 Durante la auditoría

- Marcos acompaña al auditor durante las sesiones.
- La plataforma tiene abierto un **modo auditoría en curso** donde Marcos puede hacer búsquedas rápidas en el Evidence Vault durante las preguntas del auditor ("¿dónde está la evidencia de la última prueba de restauración?" → query instantánea → respuesta en 5 segundos).
- Motor 9 registra cada pregunta del auditor, cada respuesta, cada evidencia aportada, en un `audit_log_session`.
- Durante los descansos, Marcos puede hacer mini-sesiones de alineación con el equipo del cliente para corregir desviaciones detectadas.

#### 3.8.2 Reunión de cierre con presentación de hallazgos

El auditor presenta hallazgos clasificados: No Conformidades Mayores (NC Mayor), Menores (NC Menor), Observaciones, Oportunidades de Mejora.

Motor 9 registra cada hallazgo con la información exacta, los cruza con el `audit_log_session`, y genera el **Plan de Acciones Correctivas (PAC) preliminar** durante la misma reunión de cierre. Marcos presenta el PAC al auditor para demostrar compromiso inmediato con la remediación.

Acta de cierre firmada por ambas partes.

#### 3.8.3 Reparto de esfuerzo Fase 6

| Actividad | Marcos | Plataforma |
|---|---|---|
| Acompañamiento auditor | 8-24h según categoría | Search instantáneo |
| Reunión cierre | 2h | PAC automático |
| **TOTAL** | **~10-30 horas** | **Todo lo demás** |

Esta es la fase donde Marcos sí debe estar presente físicamente o por videollamada — no se puede delegar al 95%. Pero la plataforma le ahorra todo el trabajo previo y le da búsqueda instantánea.

---

### 3.9 FASE 7 — REMEDIACIÓN DE HALLAZGOS (1-3 MESES)

Si la auditoría sale favorable con NC, hay que remediar antes de la certificación. Si sale desfavorable, hay que remediar y re-auditar.

#### 3.9.1 Plan de acciones correctivas formal

Para cada hallazgo: causa raíz, acción correctiva, acción preventiva, responsable, plazo, evidencia de cierre, verificación. El Motor 5 (Obligations & Planning) convierte cada hallazgo en una obligación trackeable con el mismo sistema de magic links y modos de ejecución que el resto de obligaciones.

#### 3.9.2 Ejecución

Reutiliza el mismo mecanismo del Motor 5 de la Fase 3.

#### 3.9.3 Re-verificación interna

Motor 9 + Agente 11 hacen una mini-auditoría interna para verificar que los hallazgos están cerrados antes de re-enviar evidencia al auditor.

#### 3.9.4 Entrega al auditor

Via magic link o email formal. El auditor verifica y emite el **certificado de conformidad ENS**.

#### 3.9.5 Publicación en el Registro de Entidades Conformes

Marcos ayuda al cliente a inscribirse en el registro oficial del CCN de entidades conformes con el ENS (trámite administrativo, no automatizable pero asistido por Motor 6 con los formularios).

#### 3.9.6 Reparto de esfuerzo Fase 7

| Actividad | Marcos | Plataforma |
|---|---|---|
| PAC formal | 1h (revisión) | 100% generación |
| Seguimiento ejecución | 2-5h (según volumen) | Motor 5 tracking |
| Re-verificación | 1h | Motor 9 auto |
| Entrega al auditor | 30 min | Motor 6 |
| Registro CCN | 1h (asistencia cliente) | Formularios |
| **TOTAL** | **~6-9 horas** | **Todo lo demás** |

---

### 3.10 FASE 8 — MANTENIMIENTO POST-CERTIFICACIÓN (CONTINUO, RETAINER)

**Aquí el negocio se vuelve recurrente y predecible.** Marcos debe ofrecer un retainer al cierre de cada proyecto. La plataforma lo facilita drásticamente.

#### 3.10.1 Motor 23 — Retainer Management

Nuevo motor dedicado al mantenimiento continuo. Gestiona:

**Actividades anuales obligatorias (para mantener la certificación):**
- Auditoría interna anual.
- Análisis de riesgos anual.
- Revisión de la DdA anual.
- Revisión de la Política anual.
- Revisión por la dirección anual.
- Snapshot INES anual (ensayo).
- Plan de formación anual ejecutado.

**Actividades periódicas menores:**
- Comité mensual o trimestral (con orden del día y acta automáticos).
- Simulacros trimestrales/semestrales de phishing.
- Pruebas anuales de continuidad.

**Actividades continuas de vigilancia:**
- **Vigilancia normativa continua** (Agente 15): feeds CCN-CERT, BOE, nuevas guías CCN-STIC, modificaciones del RD. Detección automática y notificación a Marcos y al cliente.
- **Gestión de vulnerabilidades continua**: scans semanales con notificación de nuevas vulnerabilidades aplicables.
- **Vigilancia de feeds de amenazas**: CCN-CERT, MITRE.
- **Vigilancia del CPSTIC**: cuando se actualiza el catálogo de productos cualificados, el agente detecta si afecta al cliente.

**Actividades a demanda:**
- Onboarding de nuevos proveedores.
- Gestión de cambios significativos del sistema (trigger de auditoría extraordinaria si el cambio es material).
- Respuesta a incidentes (coordinación con CCN-CERT vía LUCIA).

**Reporting:**
- Reporting trimestral a dirección del cliente (1 página ejecutiva).
- Reporting anual completo.

**Coordinación de auditorías de seguimiento y re-certificación:**
- Auditoría de seguimiento anual (Motor 9 la prepara).
- Re-certificación cada 2 años (Motor 9 genera el dossier como si fuera primera vez).

#### 3.10.2 Modelo económico del retainer

La plataforma propone modelos estándar (Marcos configura):

- **Retainer Básico**: 200-400 €/mes + hitos anuales facturados aparte.
- **Retainer Medio**: 500-1.200 €/mes cubriendo todo salvo incidentes graves.
- **Retainer Alto**: 1.500-3.500 €/mes full service.

Facturación recurrente automática con Motor 15 (Billing).

#### 3.10.3 Escalado de múltiples clientes en retainer

**Clave para que Marcos pueda escalar sin contratar a nadie:** la plataforma gestiona múltiples clientes en retainer simultáneamente con un mismo flujo. Marcos ve un **dashboard multi-cliente** con el estado de retainer de todos:

- Clientes verdes (todo al día).
- Clientes ámbar (alguna actividad pendiente).
- Clientes rojos (incumplimientos o incidentes).

Marcos se centra en los rojos, la plataforma gestiona los verdes y le recuerda los ámbar.

**Objetivo realista:** Marcos debe poder gestionar **20-40 clientes en retainer simultáneos** dedicando ~4-8 horas al día al total, con la plataforma haciendo el resto.

#### 3.10.4 Reparto de esfuerzo Fase 8 por cliente

| Actividad | Marcos | Plataforma |
|---|---|---|
| Vigilancia normativa | 0h | Agente 15 |
| Vigilancia vulnerabilidades | 0h | Motor 8 semanal |
| Comité trimestral | 1h | Auto |
| Reporting trimestral | 15 min | Auto |
| Auditoría interna anual | 4h | Motor 9 + Agente 11 |
| AR + DdA anual | 2h | Motor 2 + 3 |
| Revisión dirección anual | 1h | Auto |
| Incidentes ad-hoc | Variable | Soporte motor |
| **TOTAL por cliente/año** | **~30-50 horas** | **Todo lo demás** |

Con 20 clientes en retainer: 600-1000 horas de Marcos al año = trabajo de ~6 meses. Los otros 6 meses de capacidad van para proyectos nuevos (Fases −1 a 7).

---

### 3.11 RESUMEN DEL CICLO — 95/5 VERIFICADO

**Proyecto tipo Media** (el más común en sector privado que licita):

| Fase | Duración | Horas Marcos | Horas plataforma |
|---|---|---|---|
| Fase −1 Comercial | Continuo | 2.5 por lead ganado | ∞ |
| Fase 0 Pre-arranque | 1-2 sem | 5.5h | ∞ |
| Fase 1 Diagnóstico | 2-6 sem | 10-12h | ∞ |
| Fase 2 Diseño | 3-8 sem | 15-18h | ∞ |
| Fase 3 Implantación | 2-12 meses | 50-120h | ∞ |
| Fase 4 Verificación | 3-6 sem | 15-20h | ∞ |
| Fase 5 Preparación auditoría | 2-4 sem | 6-7h | ∞ |
| Fase 6 Auditoría externa | 1-3 sem | 10-30h (presencial obligado) | ∞ |
| Fase 7 Remediación | 1-3 meses | 6-9h | ∞ |
| **TOTAL PROYECTO** | **8-12 meses** | **~120-200 horas** | **Todo lo demás** |

**120-200 horas de Marcos en un proyecto Media de 8-12 meses** = 12-25 horas/mes por cliente. Con 4-6 proyectos Media simultáneos en fases diferentes, Marcos puede mantener el 100% de capacidad.

**Fase 8 retainer**: 30-50 horas/cliente/año. Con 20 clientes en retainer, 600-1000 horas/año.

**Capacidad total anual de Marcos** (asumiendo 1600 horas de trabajo efectivo al año): 
- 800h en proyectos nuevos = 4-6 Media simultáneos o 2-3 Alta
- 800h en retainer = 20-40 clientes en mantenimiento (según categoría media del retainer; alta dedicación = 20, baja dedicación = 40)

**Facturación estimada** (a tarifas estándar del mercado español):
- Proyectos nuevos: 4 × 35.000 € = 140.000 €/año.
- Retainer: 20 × 8.000 € = 160.000 €/año.
- **Total potencial: ~300.000 €/año** solo con esta plataforma.

Este es el objetivo operativo del 95/5.

---

## PARTE 4 — ARQUITECTURA TÉCNICA

### 4.1 Stack definitivo

**Lenguaje y framework backend:**
- **Python 3.12** con `uv` como gestor de paquetes (más rápido que pip).
- **FastAPI** como framework web (async nativo, OpenAPI automático, Pydantic).

**Base de datos unificada (PostgreSQL 16 con extensiones):**
- **PostgreSQL 16** como motor único.
- **pgvector 0.8+** para embeddings y RAG (índices HNSW, distancia coseno).
- **Apache AGE 1.5+** para grafo de conocimiento ENS con consultas Cypher.
- **pgAudit** para audit trail nativo a nivel de base de datos.
- **pgBackRest** para backups incrementales con WAL archiving y PITR.

**Procesamiento asíncrono:**
- **Redis 7** como broker y caché.
- **Celery 5** para tareas asíncronas en fase 1 (generación de documentos, scans, embeddings).
- **Temporal.io** para workflows largos durables en fase 2 (proyecto ENS dura meses, sobrevive a reinicios, reintentos automáticos).

**Frontend (sin Next.js, sin build pipeline):**
- **HTMX 2** para interactividad sin JavaScript de framework.
- **Alpine.js 3** para islas de interactividad cliente.
- **Tailwind CSS** vía Tailwind CLI standalone (sin Node).
- **Jinja2** para templates renderizados en servidor.

**LLM y RAG:**
- **Anthropic Claude** vía API (Opus 4 para razonamiento crítico, Sonnet 4.5 para operación, Haiku 4 para clasificación masiva).
- **LiteLLM** como router para tener fallback OpenAI si Anthropic cae.
- **Embeddings:** `BAAI/bge-m3` (multilingüe, español de calidad alta) servido localmente con `text-embeddings-inference` de HuggingFace, o `voyage-3` vía API si Marcos prefiere managed.
- **Re-ranking:** `BAAI/bge-reranker-v2-m3` cross-encoder para reordenar resultados top-30 → top-5.

**Generación de documentos:**
- **docxtpl** (Jinja2 dentro de plantillas DOCX) para todas las políticas y procedimientos.
- **WeasyPrint** para PDF desde HTML cuando se necesite estilo libre.
- **LibreOffice headless** vía CLI para conversión DOCX → PDF firmable.

**Firma electrónica:**
- Implementación propia de **firma electrónica avanzada eIDAS** vía magic link + OTP + hash + sello de tiempo. Para casos que exijan firma cualificada, integración con QTSP español (FNMT, Signaturit, Validated ID) vía API.

**Infraestructura:**
- **Caddy 2** como reverse proxy con HTTPS automático Let's Encrypt.
- **Docker Compose** para orquestar todo en un único servidor.
- **Hetzner Cloud CCX33** (8 vCPU dedicados, 32 GB RAM, 240 GB NVMe, datacenter Falkenstein o Núremberg, ~63 €/mes).
- **Hetzner Object Storage** para backups offsite cifrados.

**Observabilidad:**
- **Loguru** para logs estructurados.
- **Prometheus + Grafana** ligero (opcional) para métricas.
- **Sentry** self-hosted o managed para errores.

**Seguridad de la propia plataforma:**
- **MFA del consultor** (Marcos) con WebAuthn (hardware key Yubikey).
- **Vault** o `pass` para gestión de secretos (API keys, credenciales DB).
- **LUKS** para cifrado de disco del host.
- **Caddy** fuerza TLS 1.3.

### 4.2 Despliegue Hetzner

**Servidor:** CCX33 dedicado (no shared) en Falkenstein DE. Sistema operativo: Debian 12 o Ubuntu 24.04 LTS hardenizado según CIS Benchmark + recomendaciones CCN-STIC 521.

**Hardening mínimo:**
- SSH solo con clave Ed25519, deshabilitado password, puerto no estándar, fail2ban.
- UFW firewall: solo 22 (SSH, restringido a IP de Marcos), 80, 443 abiertos.
- `unattended-upgrades` para parches de seguridad automáticos.
- AIDE o auditd para integridad de ficheros.
- AppArmor o SELinux activo.

**Docker Compose:**
```yaml
services:
  caddy:        # reverse proxy + TLS
  app:          # FastAPI + Gunicorn + Uvicorn workers
  worker:       # Celery worker
  beat:         # Celery beat (cron)
  postgres:     # PostgreSQL 16 + pgvector + AGE + pgAudit
  redis:        # Redis 7
  embeddings:   # text-embeddings-inference (BGE-M3 local)
  pentest-net:  # red Docker aislada para herramientas pentest
```

**Backup:**
- pgBackRest hace backup full semanal + incremental diario hacia Hetzner Object Storage cifrado con clave gestionada por Marcos.
- Snapshot del volumen de Hetzner cada 24h.
- Retención: 30 días daily, 12 semanas weekly, 12 meses monthly.
- **Pruebas mensuales de restauración automatizadas** (la plataforma se restaura sola en un servidor temporal, valida que arranca, destruye el servidor temporal, deja informe).

**DRP de la plataforma:**
- RTO objetivo: 4 horas.
- RPO objetivo: 24 horas.
- Procedimiento documentado de restauración completa en un nuevo servidor Hetzner desde cero usando Terraform + Ansible playbooks que la plataforma mantiene en su propio repositorio Git.

### 4.3 Modelo de datos (tablas principales)

PostgreSQL con `uuid` como PK por defecto, `timestamptz` con default `now()` en todo, soft-delete con `deleted_at`, audit trail con triggers a tabla `audit_log`.

```sql
-- Núcleo de proyectos
clients (id, nombre, cif, sector, contacto_email, contacto_telefono, lead_source, lead_radar_id, created_at)
projects (id, client_id, nombre, fase, fecha_kickoff, fecha_objetivo_certificacion, categoria_objetivo, estado, sponsor_id, created_at)

-- Alcance y categorización
systems (id, project_id, nombre, descripcion, frontera, created_at)
information_types (id, system_id, nombre, valoracion_d, valoracion_i, valoracion_c, valoracion_a, valoracion_t, justificacion)
services (id, system_id, nombre, valoracion_d, valoracion_i, valoracion_c, valoracion_a, valoracion_t, justificacion)
categorization (id, system_id, categoria_resultante, fecha_acta, aprobado_por, version)

-- Activos y MAGERIT
assets (id, system_id, nombre, tipo_magerit, criticidad, valor_d, valor_i, valor_c, valor_a, valor_t, propietario)
asset_dependencies (id, asset_origen_id, asset_destino_id, tipo_dependencia)
threats (id, codigo_magerit, nombre, descripcion, dimensiones_afectadas)
asset_threats (id, asset_id, threat_id, probabilidad_intrinseca, impacto_intrinseco, riesgo_intrinseco)
safeguards (id, codigo, nombre, eficacia, medida_ens_relacionada)
applied_safeguards (id, asset_threat_id, safeguard_id, estado, eficacia_aplicada, riesgo_efectivo, riesgo_residual)
risk_treatments (id, asset_threat_id, decision, justificacion, plan_remediacion, aprobado_por, fecha)

-- Las 73 medidas y DdA
ens_measures (id, codigo, nombre, marco, familia, descripcion, requisito_base, fuente_oficial, version_ens)
ens_reinforcements (id, measure_id, codigo_refuerzo, descripcion, aplica_categoria_minima, dimension_aplicable)
dda_entries (id, project_id, measure_id, aplicabilidad, justificacion_no_aplica, refuerzos_aplicados[], estado_implementacion, responsable, observaciones, version, aprobado_por, fecha_aprobacion)

-- Controles y obligaciones
controls (id, project_id, dda_entry_id, descripcion, tipo, estado, responsable, fecha_objetivo)
obligations (id, project_id, gap_id, descripcion, tipo_ejecucion, entregable_esperado, dependencias[], esfuerzo_estimado, responsable, modo_ejecucion, estado, fecha_objetivo)

-- Documentos y evidencias
documents (id, project_id, tipo, nombre, version_actual, plantilla_id, estado, aprobado_por, fecha_aprobacion)
document_versions (id, document_id, version, contenido_path, hash_sha256, generado_por, generado_at, firmado_por, firmado_at, firma_data)
evidence (id, project_id, measure_id, control_id, tipo, fuente, fichero_path, hash_sha256, fecha_evidencia, fecha_caducidad, vigente, firma_ed25519, metadata_jsonb)

-- Procedimientos en ejecución
procedures (id, project_id, codigo, nombre, plantilla_id, estado, responsable, periodicidad)
procedure_executions (id, procedure_id, fecha_ejecucion, ejecutado_por, resultado, evidencia_id, observaciones)

-- Hallazgos y remediación
findings (id, project_id, fuente, severidad, medida_afectada, descripcion, evidencia_relacionada, estado, asignado_a, fecha_objetivo)
remediation_plans (id, finding_id, accion, responsable, fecha_objetivo, estado, evidencia_cierre)

-- Auditoría
audit_sessions (id, project_id, tipo, fecha_inicio, fecha_fin, auditor, alcance, resultado, informe_path)
audit_findings (id, audit_session_id, severidad, medida_afectada, descripcion, plan_remediacion_id)

-- Comité y gobierno
committee_meetings (id, project_id, fecha, asistentes_jsonb, orden_dia, acuerdos, acta_path, firmado_at)
nominations (id, project_id, rol, persona, fecha_nombramiento, acta_path)

-- Formación
training_records (id, project_id, persona, modulo, fecha, resultado, evidencia_path)

-- Proveedores
vendors (id, project_id, nombre, cif, criticidad, servicios, certificaciones)
contracts (id, vendor_id, nombre, fecha_inicio, fecha_fin, clausulas_ens_ok, contrato_path, adendas_jsonb)

-- Incidentes, vulnerabilidades, cambios
incidents (id, project_id, fecha, severidad, descripcion, notificado_lucia, lucia_id, resolucion)
vulnerabilities (id, project_id, fuente, cve, severidad, sistema_afectado, estado, fecha_deteccion, fecha_resolucion)
changes (id, project_id, descripcion, solicitante, aprobado_cab, fecha_implementacion, resultado)

-- Magic links (cliente)
magic_links (id, project_id, tipo_operacion, scope_jsonb, token_hash, otp_hash, expira_at, max_usos, usos, revocado, creado_at)
client_interactions (id, magic_link_id, accion, ip, user_agent, geolocalizacion, timestamp, payload_jsonb, firma_resultado)

-- Pentesting
pentest_runs (id, project_id, tipo, alcance_jsonb, fecha_inicio, fecha_fin, autorizado_por, autorizacion_link_id, estado, informe_path)
pentest_findings (id, pentest_run_id, herramienta, severidad, cve, descripcion, host_afectado, mapeo_ens, mapeo_mitre, evidencia_path)

-- Base de conocimiento (RAG + grafo)
knowledge_documents (id, fuente, titulo, version, fecha_publicacion, hash_sha256, contenido_path)
knowledge_chunks (id, document_id, seccion, contenido, embedding vector(1024), metadata_jsonb)

-- Audit trail
audit_log (id, tabla, registro_id, accion, usuario, timestamp, payload_old_jsonb, payload_new_jsonb)

-- =========================================================================
-- NUEVAS TABLAS v2.0/v2.1 — CICLO COMERCIAL Y ORGANIZATIVO
-- =========================================================================

-- Ciclo comercial (Fase −1)
leads (id, empresa_nombre, empresa_cif, sector, tamano_estimado, contacto_email, contacto_telefono, origen, radar_lead_id, estado, lead_score, clasificacion_abc, notas, asignado_a, fecha_entrada, fecha_ultima_actualizacion)

exploratory_meetings (id, lead_id, fecha, duracion_minutos, participantes_jsonb, bloque_A_jsonb, bloque_B_jsonb, bloque_C_jsonb, bloque_D_jsonb, bloque_E_jsonb, bloque_F_jsonb, pliego_subido_path, transcripcion_path, outputs_vivos_jsonb, notas_confidenciales, estado)

proposals (id, lead_id, version, plantilla_id, categoria_objetivo, alcance_jsonb, duracion_semanas, effort_marcos_horas, importe_total, importe_desglose_jsonb, hitos_pago_jsonb, validez_hasta, pdf_path, docx_path, enviado_at, abierto_at, estado)

negotiation_meetings (id, proposal_id, fecha, ajustes_jsonb, within_range_check_jsonb, proposal_v2_id, resultado, notas)

contracts (id, lead_id, proposal_id, tipo, plantilla_id, cliente_firmante_nombre, cliente_firmante_cargo, clausula_recursos_jsonb, parametros_xyzpr_jsonb, docx_path, pdf_path, hash_sha256, firmado_marcos_at, firmado_cliente_at, firmado_cliente_link_id, vigente_desde, vigente_hasta, estado, adendas_jsonb)

client_commitments (id, contract_id, tipo_compromiso, descripcion, parametro, valor_esperado, ultima_verificacion, estado_cumplimiento, parones_generados_jsonb)

pricing_models (id, nombre, descripcion, formula_jsonb, rango_precio_min, rango_precio_max, aplicable_categoria, activo, creado_at)

effort_estimates (id, project_id, tarea_tipo, tarea_id, categoria, tamano_cliente, madurez_inicial, horas_marcos_calculadas, horas_plataforma_calculadas, confianza, formula_aplicada, calculado_at)

-- Facturación (Motor 15)
invoices (id, client_id, project_id, contract_id, numero_correlativo, tipo, concepto, base_imponible, iva_percent, iva_importe, irpf_percent, irpf_importe, total, fecha_emision, fecha_vencimiento, estado_pago, verifactu_hash, verifactu_enviado_at, pdf_path)

invoice_lines (id, invoice_id, descripcion, cantidad, precio_unitario, subtotal, hito_asociado, paron_asociado)

payment_reminders (id, invoice_id, fecha_envio, canal, template, respuesta_cliente)

-- Onboarding adaptativo (Motor 16)
onboarding_sessions (id, project_id, sector, rol_receptor, interlocutor_nombre, interlocutor_email, plantilla_id, magic_link_id, preguntas_jsonb, respuestas_jsonb, conectores_autorizados_jsonb, estado, iniciado_at, completado_at)

discovered_assets (id, project_id, onboarding_session_id, fuente_conector, tipo_magerit, nombre, identificador, criticidad_propuesta, propietario_inferido, ubicacion, metadata_jsonb, descubierto_at)

discovered_identities (id, project_id, fuente_conector, directorio, username, email, es_privilegiada, mfa_activo, ultima_actividad, dias_inactiva, grupos_jsonb, permisos_efectivos_jsonb, alertas_jsonb, descubierto_at)

discovered_configurations (id, project_id, fuente_conector, sistema, control_id, estado, valor_actual, valor_esperado, gap_severidad, herramienta_deteccion, descubierto_at)

discovered_data_stores (id, project_id, fuente_conector, tipo, ubicacion, volumen_estimado_gb, clasificacion_inicial, patrones_detectados_jsonb, dimension_sensibilidad, descubierto_at)

logging_capability_assessment (id, project_id, siem_presente, siem_producto, retencion_dias, cobertura_op_exp_8_percent, casos_uso_activos, gaps_jsonb, evaluado_at)

data_flow_diagrams (id, project_id, nombre, fuente, procesamiento, almacenamiento, destino, actores_jsonb, svg_path, mermaid_code, generado_at)

-- Diagnóstico organizativo (Motor 21)
business_processes (id, project_id, nombre, descripcion, responsable, sistemas_usados_jsonb, informacion_tratada_jsonb, criticidad, es_cara_cliente_publico, estacionalidad, bpmn_mermaid, rto_propuesto, rpo_propuesto)

stakeholders_graph_nodes (id, project_id, tipo, nombre, cargo, departamento, email, posicion_sobre_proyecto, estado_personal, notas_confidenciales)

stakeholders_graph_edges (id, project_id, nodo_origen_id, nodo_destino_id, tipo_relacion, peso, notas)

legal_obligations (id, project_id, obligacion_tipo, base_normativa, aplicable, estado_cumplimiento_estimado, cruce_medidas_ens_jsonb, prioridad, responsable_cliente, observaciones, detectado_at)

client_projects_in_flight (id, project_id, nombre_proyecto_cliente, descripcion, estado, solape_con_ens, oportunidad_aprovechamiento, fuente_deteccion)

confidential_notes (id, project_id, autor, tipo, contenido_cifrado, tags_jsonb, creado_at, visible_solo_marcos)

document_inventory_analysis (id, project_id, documento_cliente_nombre, tipo, estado_vigente, calidad_evaluada, accion_propuesta, notas)

people_maturity_assessment (id, project_id, encuesta_fecha, total_respuestas, puntuacion_global, puntuacion_por_dominio_jsonb, recomendaciones_formacion_jsonb)

-- Plan de proyecto (Motor 17)
project_plans (id, project_id, version, wbs_jsonb, milestones_jsonb, critical_path_jsonb, resource_allocation_jsonb, aprobado_at, gantt_xlsx_path, gantt_pdf_path)

wbs_tasks (id, project_plan_id, task_code, task_name, parent_task_id, phase, start_date, end_date, duration_days, effort_marcos_hours, effort_platform, responsible, dependencies_jsonb, deliverable_e_code, status, blockers_jsonb)

change_requests (id, project_id, descripcion, solicitante, impacto_plazo_dias, impacto_coste, estado, aprobado_at, aplicado_at)

-- Riesgos del proyecto (Motor 19)
project_risks (id, project_id, risk_code, titulo, descripcion, probabilidad, impacto_dias, impacto_euros, categoria, owner, trigger_condicion, status, mitigation_plan_jsonb, contingency_plan_jsonb, materializado_at, cerrado_at)

-- Comunicación (Motor 18)
communication_plans (id, project_id, destinatarios_jsonb, frecuencias_jsonb, canales_jsonb, escalations_jsonb, activado_at)

status_reports (id, project_id, tipo, destinatario_rol, fecha_generacion, contenido_path, enviado_at, leido_at)

-- Entorno colaborativo (Motor 20)
collaborative_workspaces (id, project_id, estado, carpeta_docs_path, creado_at, caducidad_at, livekit_room_id, feed_suscripciones_jsonb)

workspace_files (id, workspace_id, nombre, path, hash_sha256, subido_por, subido_at, tipo_mime, versiones_jsonb)

videocall_sessions (id, workspace_id, solicitada_at, aceptada_at, iniciada_at, finalizada_at, participantes_jsonb, grabacion_path, consentimiento_grabacion)

workspace_feed_items (id, workspace_id, tipo, titulo, contenido, link, creado_at, leido_by_cliente_at)

workspace_chat_messages (id, workspace_id, autor, contenido_cifrado, adjunto_path, enviado_at, leido_at)

-- Retainer (Motor 23)
retainer_contracts (id, client_id, modalidad, precio_mensual, inicio, fin, renovacion_automatica, sla_respuesta_horas)

retainer_activities (id, retainer_contract_id, tipo_actividad, fecha_programada, fecha_ejecutada, estado, evidencia_path, horas_consumidas)

retainer_dashboards_snapshots (id, snapshot_at, semaforo_por_cliente_jsonb, metricas_agregadas_jsonb)

-- =========================================================================
-- NUEVAS TABLAS v2.1 (revisión abril 2026) — GESTOR DOCUMENTAL INTELIGENTE,
-- CICLO DE VIDA DEL PROYECTO Y BACKUPS
-- =========================================================================

-- Gestor documental inteligente (Motor 24)
-- Estas tablas AMPLIAN las existentes `documents` y `document_versions`
-- (no las reemplazan) con capacidades de IDMS completo.

document_folders (id, client_id, project_id, parent_folder_id, name, virtual_path, is_standard, standard_code, custom_order, created_at, updated_at)
  -- Árbol de carpetas virtual por cliente. is_standard=true para las carpetas del esqueleto 00-14.
  -- virtual_path formato: "00_Contractual/Contratos" (generado por trigger)

document_content (id, document_id, document_version_id, extracted_text, extraction_method, extraction_quality, language, ocr_applied, content_length_chars, extracted_at)
  -- Texto extraído completo del documento, fuente para búsqueda léxica y semántica

document_search_vector (id, document_id, document_version_id, search_vector tsvector, updated_at)
  -- Columna tsvector con configuración 'spanish' para búsqueda full-text
  -- Índice GIN creado automáticamente

document_embeddings (id, document_id, document_version_id, chunk_index, chunk_text, embedding vector(1024), created_at)
  -- Embeddings de 1024-d por chunk. Un documento puede tener varios chunks si es largo.
  -- Índice IVFFlat para búsqueda semántica rápida

document_tags (id, document_id, tag_type, tag_value, confidence, assigned_by, assigned_at)
  -- tag_type: 'ens_measure' | 'document_type' | 'classification' | 'custom' | 'auto'
  -- tag_value: 'op.acc.5' | 'politica_interna' | 'CONFIDENCIAL' | ...
  -- assigned_by: 'human' | 'llm_agent_26' | 'rule_based'

document_metadata (id, document_id, key, value, extracted_by, confidence)
  -- Metadatos extraídos del contenido: fechas, firmantes, referencias, sistemas mencionados

document_classifications (id, document_id, suggested_type, suggested_folder_id, confidence, llm_reasoning, accepted_by, accepted_at)
  -- Propuestas del Agente 26 al subir un documento, con trazabilidad de la decisión humana

document_links (id, document_id, linked_entity_type, linked_entity_id, link_type)
  -- Vinculación bidireccional: documento → medida ENS, control, procedimiento, proveedor, contrato...
  -- linked_entity_type: 'ens_measure' | 'control' | 'procedure' | 'vendor' | 'contract' | 'incident' | 'change'
  -- link_type: 'evidence_of' | 'supports' | 'references' | 'generated_from'

document_expiry_tracking (id, document_id, expiry_type, expiry_date, warning_days, last_alert_sent, resolved_at)
  -- expiry_type: 'review_due' | 'signature_expired' | 'contract_ends' | 'evidence_caducada' | 'cert_expires'

document_duplicates (id, document_id, duplicate_of_document_id, detection_method, similarity_score, resolution)
  -- detection_method: 'sha256_exact' | 'semantic_embedding'
  -- resolution: 'pending' | 'kept_as_version' | 'rejected' | 'both_kept'

document_drag_drop_sessions (id, client_id, started_by, files_uploaded, files_classified, files_accepted, started_at, completed_at)
  -- Tracking de sesiones de carga masiva para UX y analytics

-- Ciclo de vida del proyecto y archivado (Motor 25)

project_lifecycle_states (id, project_id, state, entered_at, entered_by, previous_state, reason, metadata_jsonb)
  -- Historial de estados: DRAFT → NEGOTIATING → SIGNED → ACTIVE → CERTIFIED → RETAINER → ENDED_* → ARCHIVED → PURGED

archived_projects (id, client_id, client_nif, client_name, project_id, project_name, archive_started_at, archive_completed_at, archive_zip_path, archive_zip_hash_sha256, archive_zip_size_bytes, manifest_jsonb, signed_by, signature_ed25519, cold_storage_location, retention_until, purge_scheduled_at, purged_at)
  -- Tabla de "tombstones" de proyectos archivados. La BD principal no tiene sus datos, solo esta referencia.

project_archive_manifests (id, archived_project_id, table_name, row_count, table_dump_hash, file_count, storage_bytes)
  -- Inventario detallado del contenido archivado

project_exports (id, project_id, export_type, exported_by, export_zip_path, export_zip_hash, export_zip_size_bytes, exported_at, expires_at, download_count)
  -- export_type: 'full_snapshot' | 'client_delivery' | 'auditor_package' | 'personal_backup'
  -- Exports puntuales sin archivar

project_restoration_requests (id, archived_project_id, requested_by, requested_at, reason, approved_at, restored_at, restored_as_project_id)
  -- Solicitudes de "unarchive" con trazabilidad

-- Backups y disaster recovery (Motor 26)

backup_jobs (id, backup_type, started_at, completed_at, status, size_bytes, location, hash_sha256, encryption_key_id, error_message)
  -- backup_type: 'postgres_full' | 'postgres_incremental' | 'postgres_wal' | 'minio_snapshot' | 'config_snapshot' | 'audit_log_export'

backup_retention_policies (id, backup_type, daily_keep, weekly_keep, monthly_keep, yearly_keep, updated_at)

backup_restore_tests (id, test_type, backup_job_id, started_at, completed_at, status, rto_seconds, validation_report_jsonb, sandbox_destroyed)
  -- test_type: 'partial_db' | 'full_db' | 'minio_sample' | 'dr_drill' | 'archived_project'

dr_drills (id, drill_date, initiated_by, rto_objective_seconds, rto_actual_seconds, rpo_objective_seconds, rpo_actual_seconds, status, report_path, issues_found_jsonb)
  -- Registro de ejercicios completos de DR (trimestrales)

integrity_verifications (id, verification_type, verified_at, status, sample_size, discrepancies_found, report_jsonb)
  -- verification_type: 'minio_hash_sample' | 'audit_log_chain' | 'document_signatures'

-- Soporte para la experiencia multi-cliente (tenant virtual)

client_workspaces (id, client_id, slug, display_name, custom_logo_path, brand_color, created_at)
  -- slug para URL amigable: fulkro.es/clients/sdl
  -- El cliente puede tener branding propio en los magic links que recibe

client_dashboard_state (id, client_id, last_viewed_at, pinned_documents_jsonb, favorite_searches_jsonb, custom_widgets_jsonb)
  -- Estado del dashboard específico del cliente para Marcos

multi_client_switch_history (id, marcos_session_id, client_id_from, client_id_to, switched_at)
  -- Telemetría del uso del switch rápido entre clientes

global_search_queries (id, query_text, query_embedding vector(1024), executed_at, results_count, clicked_result_document_id)
  -- Historial del buscador global Cmd+K para mejora continua
```

**Índices críticos para el gestor documental:**

```sql
CREATE INDEX idx_document_content_search ON document_search_vector USING GIN (search_vector);
CREATE INDEX idx_document_embeddings_ivfflat ON document_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_document_tags_measure ON document_tags (tag_type, tag_value) WHERE tag_type = 'ens_measure';
CREATE INDEX idx_document_folders_path ON document_folders (client_id, virtual_path);
CREATE INDEX idx_document_expiry ON document_expiry_tracking (expiry_date) WHERE resolved_at IS NULL;
```

**Row Level Security (RLS):** habilitado en todas las tablas con `project_id` o `client_id`. Marcos es el único usuario humano permanente, pero RLS protege contra bugs de aplicación que mezclen proyectos accidentalmente.

**Tenant virtual por cliente.** Aunque la plataforma usa una sola base de datos, a efectos prácticos cada cliente vive en su propio "tenant virtual" gracias a:

1. **RLS obligatorio** con policy `client_isolation` y `project_isolation` en todas las tablas relevantes. Una consulta sin `SET LOCAL app.current_client_id = X` no devuelve nada. Las policies se verifican en arranque como parte del test suite.

2. **Prefijo obligatorio en MinIO**: todo objeto se almacena bajo `fulkro/clients/{nif}/projects/{project_id}/...`. Un bucket policy lo refuerza.

3. **URL amigable**: cada cliente tiene un slug (`sdl`, `innovatech`, `dataforma`) y su dashboard vive en `fulkro.es/clients/{slug}/dashboard`. Todas las rutas internas llevan el slug.

4. **Switch rápido multi-cliente** con atajo `Cmd+K` que abre un fuzzy finder sobre todos los clientes activos de Marcos. Dos teclas y está en el cliente correcto.

5. **Dashboard específico por cliente** al entrar: resumen de estado, alertas, últimos documentos, próximas acciones, progreso de la fase actual. Todo en una sola pantalla.

6. **Export completo del cliente** con un botón: Motor 25 genera un ZIP firmado con todo (sin purgar la BD) disponible para descarga inmediata.

Esta arquitectura da al usuario (Marcos) la experiencia de "tenant por cliente" sin los costes operativos del multi-tenancy físico real.

### 4.4 Grafo de conocimiento ENS en Apache AGE

```cypher
// Ontología
(:Regulacion {codigo: "RD 311/2022"})
  -[:CONTIENE]-> (:Anexo {numero: "II", titulo: "Medidas de seguridad"})
    -[:ORGANIZA]-> (:Marco {codigo: "op", nombre: "Operacional"})
      -[:CONTIENE]-> (:Familia {codigo: "op.acc"})
        -[:CONTIENE]-> (:Medida {codigo: "op.acc.6", nombre: "Mecanismos de autenticación (usuarios de la organización)"})
          -[:REQUIERE_EN_CATEGORIA {categoria: "MEDIA"}]-> (:Refuerzo {codigo: "R1"})
          -[:REQUIERE_EVIDENCIA]-> (:EvidenciaTipo {codigo: "config_idp_mfa"})
          -[:MITIGA]-> (:Amenaza {codigo: "A.5", nombre: "Suplantación de identidad"})
            -[:AFECTA]-> (:Dimension {codigo: "A", nombre: "Autenticidad"})
          -[:DESARROLLADA_POR]-> (:GuiaCCN {codigo: "CCN-STIC 804"})
```

**Consultas tipo:**
```cypher
// Qué medidas con qué refuerzos aplican a una categoría dada
MATCH (m:Medida)-[r:REQUIERE_EN_CATEGORIA]->(ref:Refuerzo)
WHERE r.categoria IN ['BASICA', 'MEDIA']
RETURN m.codigo, m.nombre, collect(ref.codigo) AS refuerzos
ORDER BY m.codigo;

// Qué evidencias necesito para el bloque op.acc completo en categoría Alta
MATCH (f:Familia {codigo: "op.acc"})-[:CONTIENE]->(m:Medida)-[:REQUIERE_EVIDENCIA]->(e:EvidenciaTipo)
RETURN m.codigo, collect(e.codigo) AS evidencias_requeridas;
```

### 4.5 Estrategia RAG

**Chunking:** semántico por secciones del corpus normativo. Cada artículo del RD, cada apartado de las CCN-STIC, cada medida del Anexo II es un chunk separado con metadatos: `{fuente, version, articulo, medida_relacionada, fecha_publicacion}`.

**Embeddings:** BGE-M3 (1024 dimensiones) servido localmente. Se calculan en batch durante la ingesta y se almacenan en `knowledge_chunks.embedding` con índice HNSW.

**Búsqueda híbrida:**
1. Búsqueda BM25 (full-text de PostgreSQL) → top 30.
2. Búsqueda vectorial (pgvector cosine) → top 30.
3. Fusión por Reciprocal Rank Fusion → top 30 únicos.
4. Re-ranking con cross-encoder BGE-reranker-v2-m3 → top 5.
5. Los top 5 se pasan al LLM con citas obligatorias.

**Citas obligatorias:** todo prompt al LLM termina con "Responde citando el chunk_id de cada afirmación. Si no encuentras información en los chunks proporcionados, responde 'No encontrado en el corpus oficial'." El frontend renderiza las citas como hipervínculos al chunk fuente.

---

## PARTE 5 — MOTORES ESPECIALIZADOS

### Motor 1 — Categorization Engine (DETERMINISTA)

**Sin LLM en la decisión.** Implementación Python pura del Anexo I + CCN-STIC 803.

```python
def categorizar_sistema(informaciones: list[Informacion], servicios: list[Servicio]) -> Categoria:
    valoraciones = []
    for item in informaciones + servicios:
        for dim in ['D', 'I', 'C', 'A', 'T']:
            valor = getattr(item, f'valor_{dim.lower()}')
            if valor:
                valoraciones.append(valor)
    if not valoraciones:
        raise ValueError("Sin valoraciones")
    maximo = max(valoraciones, key=lambda v: NIVEL_ORDEN[v])
    if maximo == 'BAJO':
        return 'BASICA'
    if maximo == 'MEDIO':
        return 'MEDIA'
    return 'ALTA'
```

El consultor (asistido por copiloto) y el cliente (vía magic link) responden a las preguntas guiadas de valoración por dimensión. El motor calcula. Genera el acta. **Sin margen de alucinación.**

### Motor 2 — MAGERIT Risk Engine (propio en Python)

Implementación completa de MAGERIT v3:

- **Catálogos precargados:** taxonomía de activos MAGERIT (Servicios, Datos/Información, Aplicaciones, Equipos, Comunicaciones, Personal, Instalaciones, etc.), catálogo de amenazas estándar, catálogo de salvaguardas mapeadas a las 73 medidas del Anexo II.
- **Cálculo intrínseco:** para cada par (activo, amenaza) → probabilidad × impacto → riesgo intrínseco.
- **Cálculo efectivo:** aplicar salvaguardas implantadas con su eficacia → riesgo efectivo.
- **Cálculo residual:** después del plan de tratamiento → riesgo residual.
- **Simulación:** "¿qué pasa si implanto la salvaguarda X?" recalcula efectivo y residual.
- **Versionado:** cada cambio en el modelo crea una nueva versión.
- **Exportación:** genera ficheros compatibles con PILAR (formato XML que PILAR importa). **Verificación abril 2026:** PILAR a día de hoy NO tiene API pública; se trabaja con ficheros propios `.mgr`. La plataforma genera el `.mgr` para que Marcos lo importe en PILAR si el cliente / auditor lo exige. Si en el futuro PILAR expone API, se añade conector.

### Motor 3 — DdA Engine

A partir del output del Motor 1 (categoría) y del estado de implantación de los controles, genera la **Declaración de Aplicabilidad** completa con las 73 medidas:

1. Itera las 73 medidas del Anexo II.
2. Para cada una consulta el grafo Cypher: `¿aplica a la categoría del sistema?`.
3. Marca refuerzos aplicables según categoría y dimensiones afectadas.
4. Rellena estado actual desde `controls`.
5. Si una medida no aplica, redacta justificación con LLM groundeado en CCN-STIC 819 (medidas compensatorias).
6. Versiona y deja lista para firma del RSEG vía magic link.

### Motor 4 — Gap Analysis Engine

Compara estado actual de cada control vs estado objetivo según DdA. Genera lista priorizada de gaps con: medida afectada, severidad (crítica/alta/media/baja), esfuerzo estimado en horas, dependencias con otros gaps, quick win sí/no.

La priorización combina reglas deterministas (medidas críticas como `op.acc.6`, `mp.info.3`, `op.exp.7` siempre primero) con LLM para contexto del cliente (si el cliente trabaja en sanidad, priorizar `mp.info.1` datos personales).

### Motor 5 — Obligations & Planning Engine (CRÍTICO, ANTI-ALUCINACIÓN)

Este es el motor más diferenciador. Convierte cada gap en **obligaciones concretas ejecutables** con entregable cerrado.

**Anti-alucinación absoluta:** las obligaciones vienen de una **biblioteca de plantillas de obligaciones** mantenida en JSON, donde cada obligación tiene:

```json
{
  "id": "OBL-op.acc.6-MFA-001",
  "medida_ens": "op.acc.6",
  "categoria_aplicable": ["MEDIA", "ALTA"],
  "titulo": "Habilitar MFA universal en el IdP corporativo",
  "descripcion_template": "El sistema {{system_name}} requiere habilitar autenticación multifactor para todos los usuarios de la organización...",
  "entregable_tipo": "configuracion",
  "entregable_template": "captura_idp_mfa_habilitado.png",
  "modo_ejecucion": "cliente_via_magic_link",
  "magic_link_template": "evidencia_tecnica",
  "esfuerzo_horas_estimado": 4,
  "dependencias": [],
  "guia_redaccion": "...",
  "criterios_aceptacion": [
    "Captura del panel admin del IdP mostrando MFA enforcement = ON",
    "Listado de usuarios con MFA activo (>= 95%)",
    "Documento de excepciones aprobadas por RSEG si <100%"
  ]
}
```

**Cuando el motor procesa un gap**, busca en la biblioteca las plantillas de obligación que cubren esa medida y categoría, las instancia con el contexto del cliente (nombre del sistema, IdP que usa, etc.) y crea registros en `obligations`. **El LLM solo personaliza el lenguaje del entregable y el contexto, jamás inventa la obligación ni los criterios de aceptación.** Validación cruzada: cada obligación generada se valida contra el grafo (¿la medida existe? ¿el refuerzo aplica a la categoría?) antes de persistirse.

**Modos de ejecución de una obligación** (esto es lo que pediste, Marcos):

1. **`consultor_genera_entregable`** → Marcos pulsa un botón, el Document Factory genera el documento (política, procedimiento, configuración propuesta), Marcos lo revisa, lo envía al cliente vía magic link para firma. El cliente revisa, acepta y firma. Cero acción técnica del cliente, solo "leer y firmar".
2. **`cliente_aporta_evidencia_via_link`** → la plataforma envía un magic link al cliente solicitando evidencia concreta ("sube captura de pantalla del panel del IdP mostrando MFA habilitado"). El cliente sube. La plataforma valida formato y registra como evidencia.
3. **`accion_tecnica_remota_autorizada`** → la plataforma genera un magic link especial que solicita al cliente autorizar una conexión técnica con scope mínimo y duración limitada (ej: "autorizar lectura de configuración del firewall durante 2 horas"). Si el cliente acepta, se le pide que pegue un token temporal o que ejecute un comando que la plataforma le proporciona en su entorno. La plataforma lee, recoge la evidencia, libera la conexión.
4. **`accion_manual_cliente`** → la plataforma genera instrucciones paso a paso ultraconcretas para que el técnico del cliente las ejecute. Captura de validación posterior vía magic link.

**Plan de Ejecución Gantt:** una vez generadas todas las obligaciones, el motor calcula dependencias y genera un Gantt visual + exportable a XLSX/PDF. Marcos lo revisa, ajusta fechas, lo aprueba y se convierte en el plan de adecuación firmado por la dirección del cliente.

### Motor 6 — Document Factory

Biblioteca de plantillas DOCX (con docxtpl) para los ~110 entregables documentales listados en la Parte 2. Cada plantilla es un fichero `.docx` versionado en Git con campos Jinja2:

```
{{ cliente.nombre }}
{{ politica.fecha_aprobacion | format_date_es }}
{% for rol in roles %}
  - {{ rol.titulo }}: {{ rol.persona }}
{% endfor %}
```

**Validación de plantilla:** cada plantilla es revisada y firmada por Marcos como autor. Las partes regulatorias (texto legal, citas a CCN-STIC, descripciones de medidas) son **inmutables** en la plantilla. Solo los campos personalizados se rellenan con datos del cliente.

**LLM solo donde es necesario:**
- Justificaciones de no-aplicabilidad de medidas → LLM con grounding en el contexto del cliente y CCN-STIC 819.
- Adaptación de redacción al sector del cliente → LLM, citas obligatorias.
- Resúmenes ejecutivos → LLM con grounding estricto.

**Pipeline de generación:**
1. Marcos pulsa "Generar política de control de accesos para cliente X".
2. La plataforma carga la plantilla, rellena con datos de `clients`, `projects`, `nominations`, etc.
3. El LLM rellena los huecos con grounding RAG sobre el corpus.
4. docxtpl produce el `.docx`.
5. LibreOffice CLI lo convierte a PDF.
6. Se calcula hash SHA-256 y se firma con Ed25519 (firma técnica).
7. Se envía al cliente vía magic link para firma electrónica avanzada (firma legal).

### Motor 7 — Evidence Collection Engine

Para cada control con estado "esperando evidencia", el motor:

1. Consulta la plantilla de evidencia esperada para esa medida (catálogo de la sección 2.13).
2. Genera un magic link tipo `evidencia_tecnica` con scope a ese control concreto.
3. Envía email al cliente con el magic link y las instrucciones exactas ("sube esto, en este formato, antes de esta fecha").
4. Cuando el cliente sube, valida formato (extensión, tamaño, contenido si es parseable como JSON/XML).
5. Calcula hash SHA-256, firma Ed25519 con clave de la plataforma, registra timestamp y sello.
6. Vincula a `evidence` con `measure_id` y `control_id`.
7. Programa la **fecha de caducidad** según el tipo de evidencia (capturas de SIEM caducan a 30 días; políticas firmadas al año; certificados a su vencimiento).
8. Cuando una evidencia se acerca a caducidad, crea automáticamente una nueva tarea de re-recolección.

### Motor 8 — Pentesting & Red Team Engine (CRÍTICO)

**Esta es una de las piezas más diferenciadoras de la plataforma.** Marcos tendrá un orquestador inteligente de herramientas open source de pentest y red team adaptado a la categoría ENS del cliente. Que el auditor mire el informe y diga "esto está bien hecho".

#### 8.1 Filosofía del motor

- **Detecta el sistema del cliente** (IPs, dominios, tecnologías, perímetro) a partir del onboarding y del discovery puntual autorizado.
- **Planifica el test** según la categoría ENS objetivo.
- **Pide autorización formal del cliente vía magic link** (alcance, ventana horaria, sistemas excluidos, tipo de tests, cláusula de "no responsabilidad por interrupciones"). El cliente firma electrónicamente.
- **Orquesta las herramientas open source** en pipeline aislado (red Docker dedicada `pentest-net`).
- **Normaliza los resultados** a formato común (modelo de datos `pentest_findings`).
- **Mapea cada hallazgo** a las medidas del Anexo II afectadas y a tácticas/técnicas MITRE ATT&CK.
- **Genera informe ejecutivo + informe técnico** en formato auditor español.
- **El LLM (Claude Opus)** interpreta resultados, prioriza, redacta el informe en lenguaje natural y propone remediaciones contextualizadas. **La ejecución técnica es siempre determinista** (las herramientas son las herramientas, Claude no inventa hallazgos).

#### 8.2 Adaptación por categoría ENS

| Categoría | Pentesting obligatorio | Red Team | Frecuencia |
|---|---|---|---|
| **Básica** | No obligatorio, recomendado: scan de vulnerabilidades + web pentest ligero | No aplica | Anual |
| **Media** | Pentest completo interno + externo + web + cloud + phishing + scanning continuo | Recomendado, no obligatorio | Anual |
| **Alta** | Todo lo de Media + Red Team formal + Purple Team + cobertura MITRE ATT&CK completa | Obligatorio, mínimo cada 2 años | Continuo |

#### 8.3 Herramientas open source integradas y orquestadas

**Reconocimiento (todas las categorías):**
- **Nmap** — descubrimiento de hosts, puertos, servicios, fingerprinting OS.
- **Masscan** — escaneo masivo de puertos en rangos grandes.
- **Amass** — enumeración de subdominios pasiva y activa.
- **Subfinder** — subdominios pasivos rápidos.
- **httpx** — sondeo HTTP/HTTPS de hosts vivos.
- **Naabu** — port scanner moderno (ProjectDiscovery).
- **Shodan API** — inteligencia externa (requiere API key, opcional).

**Vulnerabilidades (todas):**
- **OpenVAS / Greenbone Community** — escáner de vulnerabilidades completo.
- **Nuclei** (ProjectDiscovery) — escáner basado en plantillas YAML, miles de plantillas comunitarias, muy rápido. **El más usado por consultores ENS modernos.**
- **Trivy** — vulnerabilidades en imágenes Docker, IaC, dependencias.
- **Grype** — vulnerabilidades en SBOMs.
- **Wazuh** (modo agente o agentless) — auditoría de configuración + detección.

**Web pentest (todas):**
- **OWASP ZAP** — proxy de pentesting web, automatizado vía CLI o API.
- **Nikto** — escáner web clásico.
- **Wapiti** — escáner web alternativo.
- **SQLMap** — explotación SQL injection (con cuidado, solo si autorizado).
- **XSStrike / Dalfox** — XSS.
- **ffuf** — fuzzing de directorios y parámetros.

**Infraestructura y red (Media+):**
- **Metasploit Framework** — explotación (modo passive/safe checks).
- **Impacket** — herramientas Python para SMB, Kerberos, etc.
- **NetExec** (sucesor de CrackMapExec) — pentest de redes Windows.
- **BloodHound + SharpHound** — análisis de Active Directory para escalada de privilegios.
- **Responder** — captura LLMNR/NBT-NS/MDNS (en pentest interno autorizado).

**Red Team (Alta):**
- **MITRE Caldera** — plataforma de adversary emulation con plugins de tácticas MITRE ATT&CK. **Es la herramienta de referencia para Red Team formal y la que un auditor reconoce.**
- **Atomic Red Team** — biblioteca de tests atómicos por técnica MITRE.
- **Sliver C2** — Command & Control open source en Go (sucesor moderno de Cobalt Strike OSS).
- **Mythic C2** — framework C2 modular.
- **Infection Monkey** — simulación automatizada de brechas.
- **PurpleSharp** — purple team Windows.

**Cloud (Media+):**
- **Prowler** — auditoría AWS/Azure/GCP/Kubernetes contra CIS, ENS, ISO. **Especialmente útil porque tiene perfil ENS nativo.**
- **ScoutSuite** — auditoría multi-cloud.
- **CloudSploit** — alternativo.
- **Pacu** — explotación AWS.
- **kube-bench** — CIS Kubernetes benchmark.
- **kube-hunter** — descubrimiento de vulnerabilidades en clusters K8s.

**Configuración / hardening (todas):**
- **CIS-CAT Lite** — CIS Benchmarks (versión gratuita).
- **OpenSCAP** — auditoría SCAP de configuración.
- **Lynis** — auditoría de hardening Linux/Unix.
- **CLARA** del CCN — auditoría de configuraciones Windows/Linux según CCN-STIC. **Crítico porque es la herramienta oficial española y al auditor le encanta verlo.**

**Phishing y simulacros (Media+):**
- **GoPhish** — plataforma de simulacros de phishing.
- **Social-Engineer Toolkit (SET)** — alternativa.

**SAST / DAST / SCA (si el cliente desarrolla, Media+):**
- **Semgrep** — SAST multi-lenguaje.
- **Bandit** — SAST Python.
- **Safety / pip-audit** — SCA Python.
- **OWASP Dependency-Check** — SCA general.
- **Checkov** — IaC scanning.
- **Trivy** (de nuevo) — SCA + IaC.

**Reporting:**
- **Dradis Framework Community** — agregación y reporting de pentest.
- **Faraday IDE Community** — alternativo.
- **Serpico** — generador de informes de pentest.

**La plataforma no usa todas a la vez.** Para cada categoría tiene un "perfil de pipeline" preconfigurado que selecciona qué herramientas correr y en qué orden.

#### 8.4 Pipeline de ejecución

```python
class PentestPipeline:
    def __init__(self, project, categoria, alcance, autorizacion):
        self.project = project
        self.categoria = categoria
        self.alcance = alcance  # IPs, dominios, exclusiones
        self.autorizacion = autorizacion  # magic link firmado
        self.findings = []

    async def run(self):
        # Fase 1: reconocimiento
        await self.run_recon()  # Nmap, Amass, Subfinder, httpx
        
        # Fase 2: escaneo de vulnerabilidades
        await self.run_vuln_scan()  # OpenVAS, Nuclei, Trivy
        
        # Fase 3: pentest web
        if self.alcance.tiene_web():
            await self.run_web_pentest()  # ZAP, Nikto, Wapiti
        
        # Fase 4: infraestructura (Media+)
        if self.categoria in ['MEDIA', 'ALTA']:
            await self.run_infra_pentest()  # NetExec, BloodHound (si AD)
        
        # Fase 5: cloud (si aplica)
        if self.alcance.tiene_cloud():
            await self.run_cloud_audit()  # Prowler con perfil ENS
        
        # Fase 6: configuración
        await self.run_config_audit()  # CLARA, Lynis, CIS-CAT
        
        # Fase 7: red team (solo Alta)
        if self.categoria == 'ALTA':
            await self.run_red_team()  # Caldera con perfil ATT&CK
        
        # Fase 8: phishing (Media+, opcional)
        if self.categoria in ['MEDIA', 'ALTA'] and self.alcance.incluye_phishing:
            await self.run_phishing_simulation()  # GoPhish
        
        # Fase 9: normalización y mapeo
        self.normalize_findings()
        self.map_to_ens_measures()
        self.map_to_mitre_attack()
        
        # Fase 10: priorización con LLM
        await self.prioritize_with_llm()
        
        # Fase 11: generación de informe
        await self.generate_report()
```

#### 8.5 Mapeo a ENS y MITRE ATT&CK

Cada hallazgo de pentest se mapea automáticamente:

- **Mapeo a Anexo II:** una librería interna `vuln_to_ens.py` con reglas como "si el hallazgo es 'TLS 1.0 enabled' → afecta `mp.com.2`", "si es 'cuenta con MFA deshabilitado' → afecta `op.acc.6`", "si es 'sin parche crítico' → afecta `op.exp.4`". El LLM completa los casos no cubiertos por reglas, con grounding y validación.
- **Mapeo a MITRE ATT&CK:** las herramientas modernas (Nuclei, Caldera) ya etiquetan resultados con técnicas T-XXXX. La plataforma agrega los tags y los muestra en el informe.

#### 8.6 Informe de pentest en formato auditor español

El informe se genera en DOCX + PDF con esta estructura, **diseñada para que un auditor ENAC veterano la reconozca como profesional**:

```
INFORME DE TEST DE INTRUSIÓN — {cliente} — {fecha}

1. RESUMEN EJECUTIVO
   - Alcance autorizado
   - Período de ejecución
   - Categoría ENS del sistema
   - Resumen de hallazgos por severidad
   - Conclusión general

2. METODOLOGÍA
   - Herramientas utilizadas (con versiones)
   - Tipo de test (caja negra/gris/blanca)
   - Estándar seguido (OWASP WSTG, PTES, OSSTMM)
   - Cumplimiento del Anexo II del ENS

3. ALCANCE Y AUTORIZACIÓN
   - Activos en alcance
   - Activos excluidos
   - Ventana temporal
   - Autorización firmada (referencia al magic link firmado por el cliente)

4. HALLAZGOS DETALLADOS
   Para cada hallazgo:
   - ID, severidad (Crítica/Alta/Media/Baja/Informativa)
   - Título
   - Descripción técnica
   - Activo afectado
   - Evidencia (captura, payload, request/response)
   - Mapeo a medida ENS afectada
   - Mapeo a MITRE ATT&CK
   - CVE si aplica
   - CVSS score
   - Recomendación de remediación

5. RESUMEN POR MEDIDA ENS
   Tabla cruzada: medida x número de hallazgos x severidad máxima

6. PLAN DE REMEDIACIÓN PROPUESTO
   Priorizado por riesgo, con esfuerzo estimado

7. ANEXO TÉCNICO
   - Logs de las herramientas
   - Comandos ejecutados
   - Outputs raw

8. CERTIFICACIÓN DEL CONSULTOR
   - Firma del consultor (Marcos)
   - Identificación profesional
   - Declaración de no haber alterado los sistemas
```

**Esto es lo que el auditor ENAC espera ver.** Plataformas comerciales tipo PlexTrac generan algo similar pero por miles de euros al mes. Aquí lo construyes una vez con docxtpl y lo tienes para siempre.

#### 8.7 NSE / NSP — apoyo de LLM

Sobre tu duda del "NSP" — no existe estándar con ese nombre. Sospecho que querías decir **NSE (Nmap Scripting Engine)** o un módulo similar. La plataforma usa Claude (Opus para razonamiento crítico, Sonnet para volumen) como capa de inteligencia sobre los resultados:

- Interpretación de outputs raw de herramientas en lenguaje natural.
- Priorización contextual (un hallazgo "alto" en un activo no crítico puede bajarse; al contrario, un "medio" en un activo crítico puede subirse).
- Redacción del informe.
- Generación de scripts NSE personalizados si Marcos los pide ("genérame un script Nmap para detectar X").
- Explicación al cliente en lenguaje no técnico de los hallazgos.

**Anti-alucinación pentest:** el LLM nunca inventa hallazgos. Solo agrega, prioriza y redacta sobre hallazgos reales producidos por herramientas. Cada afirmación del LLM en el informe está vinculada a un `pentest_finding` con id, herramienta de origen y output raw. Si el LLM no puede vincular, no se publica.

### Motor 9 — Audit Preparation Engine

Genera el dossier final de la sección 2.15 automáticamente:

1. Verifica que todos los entregables E-XXX exigidos por la categoría están presentes y en estado aprobado.
2. Verifica que las evidencias están vigentes (no caducadas).
3. Verifica que los registros de operación cubren los últimos 6 meses.
4. Si falta algo, genera tareas urgentes para Marcos.
5. Cuando todo está, monta el ZIP con la estructura exacta.
6. Genera la matriz cruzada del 99 (Excel con una fila por medida).
7. Genera el PDF maestro navegable con índice.
8. Lo deja descargable + lo envía al cliente vía magic link para que el cliente lo entregue al auditor (o se lo entrega Marcos directamente).

### Motor 10 — Audit Simulation Engine (auditor virtual)

Agente IA que **se hace pasar por auditor ENAC** y entrevista al sistema. Para cada una de las 73 medidas aplicables:

1. Hace una pregunta tipo auditor ("Muéstreme la evidencia de que en su sistema se aplica MFA universal a todos los usuarios de la organización conforme a op.acc.6 R1").
2. Busca la evidencia en `evidence`.
3. Si la encuentra, evalúa si es suficiente, vigente, coherente.
4. Si no, marca un hallazgo y propone qué hace falta.
5. Detecta contradicciones (la política dice X pero la evidencia dice Y).
6. Genera un informe de auditoría interna exhaustivo, indistinguible en forma del de un auditor ENAC real.

**Coaching del personal del cliente:** genera preguntas tipo por rol (CTO, admin sistemas, RRHH, dirección) para que el cliente se prepare para la auditoría real. Vía magic link, el cliente puede practicar.

### Motor 11 — Copiloto LLM Conversacional ENS

**El motor que más usa Marcos día a día.** Es un chat conversacional con Claude (Sonnet 4.5 por defecto, Opus 4 para preguntas complejas) groundeado en:

- Todo el corpus normativo ENS (RD 311/2022 + ITS + CCN-STIC + PCE).
- El contexto del cliente activo (proyecto seleccionado).
- El estado actual del proyecto (DdA, evidencias, hallazgos, plan).

**Casos de uso:**
- "¿Qué me pide exactamente op.acc.5 R2 para una categoría Alta?" → respuesta con cita exacta al Anexo II y CCN-STIC 808.
- "Para el cliente X, ¿qué evidencia tengo ya recolectada para la familia op.exp y qué me falta?" → respuesta con datos del proyecto.
- "Redáctame la justificación de no aplicabilidad de mp.if.6 (inundaciones) para un cliente que está en un edificio de oficinas en planta 8" → redacta con grounding en CCN-STIC 819.
- "¿Qué herramientas pentest debo correr para este cliente que está en categoría Media?" → respuesta basada en el perfil de pipeline.
- "Genérame el orden del día del próximo Comité de Seguridad de cliente X" → lo genera con datos reales.

**Anti-alucinación universal:**
- RAG obligatorio sobre el corpus oficial.
- Citas obligatorias en cada afirmación normativa (formato `[RD 311/2022 Art. 28]`, `[CCN-STIC 808 §4.2]`).
- Modo "no encontrado en el corpus oficial" preferible a inventar.
- Validación cruzada con los motores deterministas (si el copiloto dice "op.acc.6 R1 aplica a Básica" pero el motor de DdA dice que no, se marca contradicción y se loguea).
- Temperatura baja (0.1-0.2) para tareas factuales.
- Logs de cada interacción para revisión posterior.

### Motor 12 — Magic Link Engine

Sistema de tokens efímeros firmados criptográficamente para que el cliente pueda hacer cosas puntuales sin tener cuenta.

**Estructura técnica:**
- Token = JWT firmado con Ed25519 (clave privada solo en la plataforma).
- Payload: `{project_id, scope, operation_type, otp_hash, expira_at, max_usos, usos_actuales}`.
- URL: `https://app.marcos.dev/m/{base64_token}`.
- Cuando el cliente abre el link, la plataforma valida firma + expira + usos.
- Le pide el **OTP de 6 dígitos** que se le envió por separado (email distinto, SMS, o WhatsApp).
- Si OK, le presenta SOLO la operación autorizada por `scope`. Nada más visible. Sin login, sin menú, sin perfil.
- Cuando termina, el link queda usado (o sigue activo si es multi-uso, según `max_usos`).
- Todo registrado en `client_interactions` con IP, user-agent, timestamp, geolocalización aproximada.

**Tipos de magic link** (catálogo de plantillas):

1. `onboarding_inicial` — el cliente rellena el cuestionario adaptativo.
2. `firma_documento` — el cliente revisa y firma una política, DdA, acta. Genera firma electrónica avanzada eIDAS válida.
3. `aporte_evidencia` — el cliente sube una evidencia técnica concreta.
4. `aprobacion_acta` — el cliente aprueba un acta del comité.
5. `respuesta_requerimiento_auditor` — durante la auditoría, el cliente responde a algo que pide el auditor en tiempo real.
6. `autorizacion_pentest` — el cliente autoriza la ejecución de un pentest con alcance y ventana específicos.
7. `autorizacion_accion_tecnica_remota` — el cliente autoriza una acción técnica concreta de scope mínimo.
8. `aprobacion_obligacion` — el cliente revisa y aprueba un entregable propuesto por Marcos antes de que se aplique.
9. `descarga_dossier_final` — el cliente descarga el dossier para entregar al auditor.

**Seguridad del magic link:**
- TTL corto (24h-7 días según tipo).
- Revocable manualmente por Marcos en cualquier momento.
- Rate limiting por IP.
- Si el OTP falla 3 veces, el link se invalida y Marcos recibe alerta.
- Geo-bloqueo opcional (solo IPs de España).
- Audit trail criptográficamente inmutable (hash chain).

---

### Motor 13 — Commercial Document Factory (propuestas + contratos)

**Nuevo en v2.0.** Generación automática de documentos comerciales a partir del contexto del cliente. Extiende el Motor 6 con plantillas específicas para ciclo comercial.

**Plantillas soportadas:**
- `P-001` Propuesta formal de servicios ENS (10-20 páginas).
- `P-002` Resumen ejecutivo de propuesta (1-2 páginas).
- `C-001` Contrato de servicios de consultoría ENS con cláusula de recursos del cliente.
- `C-002` Adenda contractual para proveedores del cliente (cláusulas ENS/RGPD Art. 28).
- `C-003` Contrato de retainer post-certificación.
- `C-004` NDA mutuo.
- `C-005` Acuerdo de nivel de servicio (SLA) para el retainer.

**Flujo:** Agente 19 (Redactor de Propuestas) + Agente 20 (Asistente de Negociación) toman datos del `exploratory_meeting` y `negotiation_meeting` del lead, rellenan la plantilla docxtpl seleccionada, aplican tema visual de marca (colores, tipografía, logo), generan diagramas Gantt con Mermaid, compilan a PDF profesional con LibreOffice headless. Salida en 3-5 minutos.

**Anti-alucinación:**
- Los importes económicos vienen del `pricing_model` configurado por Marcos, no del LLM.
- Las cláusulas legales vienen de una biblioteca validada; el LLM solo rellena campos marcados.
- Las estimaciones de esfuerzo vienen del `effort_estimator` determinista (Motor 17), no del LLM.

---

### Motor 14 — Contracts Engine

**Nuevo en v2.0.** Gestión del ciclo de vida completo de contratos.

**Funcionalidades:**
- Generación de contratos a partir de Motor 13.
- Envío al cliente vía magic link `firma_contrato` con verificación de identidad (OTP + foto DNI si Marcos lo activa).
- Firma electrónica avanzada con sello de tiempo cualificado (eIDAS).
- Archivo inmutable en Evidence Vault con hash SHA-256 + cadena de custodia.
- Tracking de vencimientos y renovaciones automáticas.
- Detección de cambios requeridos (change requests) y generación de adendas.
- Tracker de cumplimiento del cliente (la tabla `client_commitments` vinculada a la cláusula crítica de recursos).
- Generación automática de **facturas de parón** cuando el cliente incumple compromisos — en coordinación con Motor 15.

**Integración con Motor 6 (Analista de Contratos, Agente 6):** cuando el cliente sube contratos de sus proveedores, el Agente 6 los analiza automáticamente en busca de cláusulas ENS/RGPD faltantes y el Motor 14 genera las adendas necesarias.

---

### Motor 15 — Billing Engine

**Nuevo en v2.0.** Facturación recurrente y puntual, cumpliendo normativa fiscal española.

**Funcionalidades:**
- Generación de facturas PDF con formato fiscal correcto: número correlativo, IVA 21% (o exento/inverso según caso), retención IRPF 15% si Marcos es autónomo, datos mercantiles completos.
- Facturación recurrente automática del retainer mensual.
- Facturación por hitos del proyecto según lo pactado en el contrato.
- Facturación de parones por incumplimiento de recursos del cliente.
- Integración con **Verifactu / TicketBAI / SII** de AEAT (requisito legal 2026 para autónomos españoles).
- Envío automático al cliente vía email con PDF adjunto firmado electrónicamente.
- Recordatorios automáticos por impago (día 15, 30, 45, 60).
- Dashboard de tesorería con previsión de cobros.
- Exportación contable: CSV compatible con gestoría de Marcos, integración directa con Holded/Contasimple/Quipu si las usa.

**Anti-alucinación económica:** los importes vienen siempre del contrato firmado o del modelo de precios configurado; nunca los genera el LLM.

---

### Motor 16 — Adaptive Onboarding Engine

**Nuevo en v2.0.** Onboardings personalizados por sector del cliente y por rol del receptor dentro de la empresa.

**Matriz de plantillas** (`onboarding_templates`):

| Sector ↓ \ Rol → | Sponsor | TI/CTO | Legal/DPO | RRHH | Operaciones | Compras | Usuario final |
|---|---|---|---|---|---|---|---|
| Servicios profesionales | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Fintech | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Sanidad privada | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Industria | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| SaaS/Tech | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Retail/ecommerce | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Energía | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Logística | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Educación privada | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Genérico | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

**70 combinaciones** de plantillas de onboarding, cada una con 15-40 preguntas específicas + bloques opcionales desbloqueables según respuestas + conectores OAuth sugeridos.

**Conectores OAuth soportados:** Microsoft 365 / Entra ID, Google Workspace, AWS, Azure, GCP, GitHub/GitLab/Bitbucket, Okta, OneLogin, JumpCloud, Jira/Asana/Monday, Slack/Teams estructura, Active Directory on-premise (vía agente ligero `ens-discovery-agent`).

**Servidor MCP local:** expone queries estructuradas sobre lo descubierto para que los agentes IA las consuman sin acceder a datos crudos (minimización RGPD).

**Tooltips:** cada pregunta con icono de ayuda que abre explicación en lenguaje sencillo + ejemplo.

**Magic links individuales** por interlocutor con OTP propio, pausable, reanudable, multi-sesión.

---

### Motor 17 — Project Planning Engine

**Nuevo en v2.0.** Generación, mantenimiento y seguimiento del plan de proyecto completo.

**Funcionalidades:**
- **Generación de WBS** a partir del catálogo de tareas por categoría (B/M/A) extraído de la Parte 2 (Entregables). ~150 tareas en B, ~250 en M, ~350 en A.
- **Cronograma Gantt** con dependencias, ruta crítica, holguras. Exportable a MS Project XML, CSV, PDF, SVG/PNG.
- **Estimación determinista de esfuerzo** (`effort_estimator`) basada en histórico: fórmulas calibradas por tipo de tarea × categoría × tamaño del cliente × complejidad técnica.
- **Seguimiento de avance** en tiempo real: cada tarea pasa por estados (`por_hacer | en_curso | bloqueada | en_revision | hecha | descartada`).
- **Detección automática de retrasos** vs línea base con alertas a Marcos.
- **Replan automático** cuando se materializa un riesgo del Motor 19 o un parón por cliente.
- **Submódulo `change_management`** para gestionar cambios de alcance formalmente.

**Integración con el calendario del cliente** vía CalDAV/Google Calendar/Outlook para programar automáticamente las reuniones recurrentes del proyecto.

---

### Motor 18 — Communication & Reporting Engine

**Nuevo en v2.0.** Generación automática de todos los reportes del proyecto y gestión de la comunicación con el cliente.

**Reportes automatizados:**
- **Status semanal al sponsor** (1 página DOCX + PNG para email). Auto-generado cada viernes 16:00.
- **Status mensual al Comité** (3-5 páginas con métricas, hitos, hallazgos, próximos pasos, riesgos). Auto el día anterior a la reunión mensual del Comité.
- **Status trimestral a dirección** (1 página ejecutiva con semáforo RAG).
- **Reporte de cumplimiento de recursos del cliente** (semanal o cuando hay incumplimientos).
- **Reporte de quick wins** publicado en el feed del cliente.

**Canales de comunicación:**
- Email corporativo de Marcos con envío automatizado y tracking de apertura (opcional).
- Feed en magic link persistente del proyecto.
- Chat asíncrono del entorno colaborativo efímero (Motor 20).
- SMS opcional para alertas críticas.

**Plantillas uniformes `comms_templates`** con estética profesional. Cero retoque manual salvo casos excepcionales.

---

### Motor 19 — Project Risk Management Engine

**Nuevo en v2.0.** Gestión de los riesgos del proyecto consultor (diferente del AR del sistema del cliente que gestiona el Motor 2 MAGERIT).

**Catálogo precargado de ~30 riesgos típicos del consultor ENS** (ver 3.2.10). Cada riesgo con:
- Probabilidad (baja/media/alta).
- Impacto (días de retraso + euros).
- Plan de contingencia.
- Plan de mitigación.
- Dueño.
- Triggers de escalado.
- Estado (`identificado | monitorizado | materializado | cerrado`).

**Instanciación automática** al iniciar un proyecto: el Motor 19 carga los riesgos base, el Agente 21 (Detector de Discrepancias) los contextualiza con datos del cliente, y Marcos valida.

**Dashboard de riesgos vivo** con semáforo de cada riesgo. Marcos revisa semanalmente.

**Disparo automático de planes de contingencia** cuando un trigger se activa (ej: cliente no responde a magic link en 7 días → trigger → contingencia "escalar al sponsor con email formal").

---

### Motor 20 — Collaborative Workspace Engine

**Nuevo en v2.0.** Gestiona el entorno colaborativo efímero por proyecto.

**Componentes:**

**A) Gestor documental minimalista:**
- Carpeta única por proyecto con subcarpetas por fase.
- El cliente sube archivos vía magic links temporales de tipo `sube_documento`.
- Cada archivo se versiona, se firma con hash al subir, se indexa automáticamente.
- Búsqueda full-text sobre el contenido.
- Descarga bulk al cierre del proyecto.
- Inmutabilidad opcional con almacenamiento WORM.

**B) Videollamadas bajo demanda con LiveKit self-hosted:**
- El cliente pulsa "Solicitar videollamada ahora" o "Programar videollamada" desde su magic link persistente del proyecto.
- Si Marcos está disponible y acepta, se genera una sala LiveKit instantánea con link cifrado y OTP.
- Si no, Marcos recibe notificación y agenda.
- Grabación opcional con consentimiento del cliente.
- No requiere cuenta de terceros (Teams/Meet/Zoom).
- Latencia baja (servidor en Hetzner DE → usuarios en España).

**C) Feed de notificaciones del proyecto** visible al cliente: hitos, documentos pendientes de firma, evidencias pendientes, próximas reuniones.

**D) Chat asíncrono minimalista** entre Marcos y cliente para mensajes breves, con historial cifrado. No sustituye el email formal.

**Ciclo de vida del workspace:**
- Creado al firmar contrato.
- Activo durante el proyecto.
- 90 días de retención post-cierre.
- Destruido o archivado según decisión de Marcos.
- Extendido indefinidamente si se firma retainer.

---

### Motor 21 — Organizational Diagnosis Engine

**Nuevo en v2.0.** Ejecuta los 4 sub-diagnósticos organizativos de la Fase 1.

**Sub-diagnósticos:**
- **Mapa de stakeholders** (Agente 22 — Analista de Stakeholders): grafo en Apache AGE con nodos `Person` y aristas tipadas (`reports_to`, `allies_with`, `conflicts_with`, `blocks`, `sponsors`). Visualización con d3.js. Notas confidenciales solo visibles a Marcos.
- **Inventario de procesos de negocio** (Agente 23 — Mapeador de Procesos): entrevistas guiadas + análisis del onboarding. Tabla `business_processes` + diagramas BPMN Mermaid. Alimenta directamente el BIA del Motor 6.
- **Inventario de obligaciones legales y contractuales cruzadas** (Agente 24 — Detector de Obligaciones Cruzadas): detecta RGPD, PCI-DSS, normativa sectorial, NIS2, DORA, AI Act aplicables según el sector del cliente. Palanca para aprovechar esfuerzo cross-compliance.
- **Inventario de proyectos en curso del cliente**: cruzado con Jira/Asana/Monday para detectar solapes y oportunidades de aprovechamiento.

---

### Motor 22 — Technical Discovery Engine

**Nuevo en v2.0.** La otra gran innovación. Ejecuta todo el descubrimiento técnico vía conectores OAuth y/o agentes ligeros.

**Sub-motores de discovery:**
- **Asset Discovery**: Nmap/zmap en red interna; AWS Config + Resource Explorer; Azure Resource Graph; GCP Cloud Asset Inventory; M365/Google Workspace Admin; CMDB import (ServiceNow/Freshservice/GLPI/iTop); DB discovery (`information_schema`); endpoint discovery (Intune/Jamf/CrowdStrike/SentinelOne).
- **Identity Discovery**: export AD/Entra ID/Google Workspace; análisis de cuentas activas/inactivas/privilegiadas/compartidas/servicio; MFA coverage; política de contraseñas; permisos efectivos tras expansión de grupos anidados.
- **Data Discovery**: localización de información sensible; clasificación inicial por patrones regex (DNI, NIF, IBAN, salud, tarjetas); volumen estimado.
- **Configuration Discovery**: CLARA (Windows CCN); Lynis (Linux); CIS-CAT; M365 Secure Score; AWS Security Hub; Azure Defender; GCP SCC; firewall config dump; testssl.sh + SSL Labs de todos los FQDN; DNS (SPF/DKIM/DMARC/DNSSEC); estado de parches; cobertura antimalware/EDR.
- **Vulnerability Discovery**: OpenVAS/Greenbone scan inicial; Nuclei con templates ENS; Trivy/Grype en contenedores; Semgrep en código.
- **Log & Monitoring Assessment**: presencia de SIEM, cobertura de logging, retención, casos de uso activos, cumplimiento con op.exp.8.
- **Data Flow Mapping**: Agente 25 genera automáticamente los DFD del cliente con entrada, procesamiento, almacenamiento, salida, permisos.
- **Continuity Assessment**: inventario de backups, DRPs existentes, SLAs, SPOFs técnicos.

**Outputs unificados** en el `project knowledge graph` del cliente, listos para alimentar Motor 1 (Categorización), Motor 2 (MAGERIT), Motor 4 (Gap Analysis) y Motor 5 (Obligations).

**Protocolo MCP:** expone queries estructuradas al knowledge graph para que los agentes consuman datos agregados sin acceder a datos crudos (minimización RGPD).

---

### Motor 23 — Retainer Management Engine

**Nuevo en v2.0.** Gestiona el mantenimiento post-certificación de múltiples clientes simultáneos.

**Funcionalidades:**
- Calendarización automática de las actividades anuales obligatorias (auditoría interna, AR, DdA, Política, revisión dirección, INES, formación).
- Periodicidad de Comités (mensual en A, trimestral en M, semestral en B) con convocatoria, orden del día y acta automáticos.
- Simulacros periódicos de phishing (trimestral/semestral).
- Pruebas anuales de continuidad.
- Vigilancia normativa continua (Agente 15).
- Vigilancia de vulnerabilidades semanal (Motor 8 modo ligero).
- Vigilancia del CPSTIC (cuando cambia, detecta impacto).
- Onboarding de nuevos proveedores del cliente.
- Gestión de cambios significativos del sistema del cliente (trigger de auditoría extraordinaria si es material).
- Reporting trimestral a dirección del cliente.
- Coordinación de auditorías de seguimiento y re-certificación.
- Facturación recurrente (coord. con Motor 15).

**Dashboard multi-cliente** con semáforo RAG por cliente. Marcos se centra en los rojos; la plataforma gestiona los verdes y le recuerda los ámbar.

**Objetivo operativo:** Marcos debe poder gestionar **20-40 clientes en retainer simultáneos** con la plataforma.

**Modelo económico configurable** por Marcos: Retainer Básico (200-400 €/mes), Medio (500-1200 €/mes), Alto (1500-3500 €/mes).

---

### Motor 24 — Intelligent Document Management Engine (IDMS)

**Nuevo en v2.1 — revisión abril 2026.** Este motor eleva la gestión documental de v2.0 (que era una tabla `documents` + MinIO) a un **gestor documental inteligente de primera clase**, comparable a SharePoint o Google Drive pero especializado en ENS y con LLM integrado para comprensión semántica. Marcos lo vive como "el Drive de FULKRO": una interfaz visual donde ve todas las carpetas de todos los clientes, arrastra archivos, busca por contenido, y la plataforma entiende qué es cada documento.

#### 24.1 Capacidades principales

**A) Vista de árbol por cliente.** Cada cliente tiene una **carpeta raíz virtual** con estructura estándar autogenerada al crear el proyecto:

```
fulkro/clients/{nif}/projects/{project_id}/
├── 00_Contractual/
│   ├── Propuestas/
│   ├── Contratos/
│   ├── Facturas/
│   └── NDAs/
├── 01_Gobierno/
│   ├── Politica_Seguridad/
│   ├── Actas_Comite/
│   ├── Nombramientos_Roles/
│   └── Revisiones_Direccion/
├── 02_Categorizacion/
├── 03_Analisis_Riesgos/
├── 04_DdA/
├── 05_Plan_Adecuacion/
├── 06_Normativa_Interna/
│   ├── Politicas_E100-E126/
│   └── Procedimientos_E200-E234/
├── 07_Registros_Operacion/
│   ├── Cambios/
│   ├── Incidentes/
│   ├── Parches/
│   ├── Backups/
│   ├── Accesos/
│   └── Formacion/
├── 08_Proveedores/
├── 09_Pentesting/
├── 10_Auditoria_Interna/
├── 11_Plan_Continuidad/
├── 12_Evidencias_Tecnicas/
├── 13_Auditoria_Externa/
│   ├── Dossier/
│   └── Remediacion/
├── 14_Retainer_Continuo/
│   ├── 2026_Q1/
│   ├── 2026_Q2/
│   └── ...
└── 99_Misc/
```

**Esta estructura se genera automáticamente** al crear el proyecto. Marcos puede renombrar, añadir o reorganizar carpetas pero las estándar no se pueden eliminar hasta el archivado del proyecto.

**B) Drag & drop inteligente.** Marcos arrastra un fichero a cualquier carpeta del árbol (o al workspace raíz del cliente) y el motor:

1. **Extrae el texto** con el extractor multi-formato:
   - PDF: `pdfplumber` + OCR fallback con Tesseract si es escaneado
   - DOCX: `python-docx`
   - XLSX: `openpyxl` (tablas + celdas nombradas)
   - PPTX: `python-pptx`
   - Imágenes: Tesseract OCR en español
   - Emails `.msg`/`.eml`: `extract-msg`
   - ZIP/RAR: recursivo

2. **Clasifica el tipo de documento** con el LLM (Agente 26, nuevo):
   - ¿Es una política interna del cliente? ¿Una evidencia técnica? ¿Un contrato con proveedor? ¿Un informe de pentest externo? ¿Un acta de comité? ¿Un certificado?
   - Propone ruta de archivado: *"parece un acta del Comité de Seguridad del 15/07/2026 → sugiero archivarlo en `01_Gobierno/Actas_Comite/2026-07-15_Acta_Comite.pdf`"*.
   - Marcos acepta, modifica o redirige con un clic.

3. **Etiqueta automáticamente por medidas ENS** que el documento soporta:
   - El LLM lee el contenido y propone etiquetas del tipo `op.acc.5`, `mp.info.9`, `org.2`, etc.
   - Las guarda en la tabla `document_tags`.
   - Marcos puede después filtrar por medida: "muéstrame todos los docs que soportan op.exp.4".

4. **Detecta duplicados por hash SHA-256 y por similitud semántica** (embeddings con pgvector):
   - Duplicado exacto: rechaza o pregunta "ya existe con hash X, ¿lo sobrescribes o lo versionas?"
   - Duplicado semántico (>95% similitud): avisa "este documento es casi idéntico a `07_Registros_Operacion/Parches/2026-07_Parches.xlsx`, ¿es una nueva versión?"

5. **Extrae metadatos contextuales** del contenido:
   - Fechas mencionadas en el doc → `document_date` sugerido
   - Nombres propios → posibles firmantes o responsables
   - Referencias a expedientes, contratos, sistemas → relaciones automáticas
   - Firmas digitales detectadas → marca "firmado" y extrae firmantes

**C) Búsqueda híbrida (léxica + semántica).** El buscador combina dos motores:

1. **Full-text léxico**: PostgreSQL `tsvector` con configuración `spanish`, índice GIN sobre el texto extraído. Búsquedas exactas por palabras clave, frases entre comillas, operadores booleanos.

2. **Búsqueda semántica**: embeddings de 1024 dimensiones (modelo `intfloat/multilingual-e5-large` corriendo local en el servidor, o alternativamente API de Voyage AI). Índice IVFFlat en pgvector. Búsquedas del tipo "enséñame docs que hablen de cómo rotamos las credenciales de AWS" encuentran el procedimiento relevante aunque no contenga la palabra "rotamos".

3. **Resultados combinados** con reranking del LLM cuando la query es ambigua.

**D) Dashboard de documentos por vencer.** Vista específica con los documentos que necesitan revisión:
- Políticas con fecha de revisión anual < 30 días.
- Evidencias con `fecha_caducidad < 30 días`.
- Contratos con `fecha_fin < 60 días`.
- Certificados digitales con expiración < 90 días.
- Documentos firmados hace > 12 meses sin revisión.

Marcos lo ve como un panel "Atención" en el dashboard del cliente.

**E) Línea temporal documental.** Vista cronológica por cliente: "qué se firmó, aprobó, recibió, generó en cada día/semana/mes". Útil para las auditorías ("enséñame todo lo que se hizo en septiembre de 2026") y para el tracking del proyecto.

**F) Vinculación bidireccional con medidas ENS.** Cada documento puede soportar 1..N medidas ENS; cada medida se apoya en 1..N documentos. Una vez etiquetado, desde el Dashboard de la DdA se puede hacer clic en una medida y ver todos los documentos que la soportan. Desde un documento se pueden ver todas las medidas afectadas.

**G) Firma visual y verificación.** Cada documento en el árbol muestra su estado con un icono: 🟢 firmado y vigente, 🟡 pendiente de firma, 🟠 por vencer, 🔴 caducado o revocado, 📄 sin firma requerida. Un clic en el documento abre su ficha con el historial completo de versiones, firmas, aprobaciones.

**H) Chat con el repositorio.** Marcos puede preguntar al Motor 11 (Copiloto) cosas como "¿qué dice la política de accesos del cliente SDL sobre el MFA para administradores?" y el Copiloto usa el índice semántico del Motor 24 para recuperar el fragmento relevante y responder con cita exacta.

**I) Versionado automático con Git-like semantics.** Cada `document_version` lleva:
- Número semántico (v1.0, v1.1, v2.0).
- Hash SHA-256 del contenido.
- Hash del padre (cadena verificable).
- Autor de la modificación.
- Diff contra la versión anterior (generado con `difflib` para texto, o referencia visual para binarios).
- Estado: DRAFT → REVIEW → APPROVED → SIGNED → VIGENTE → ARCHIVED.

**J) Clasificación de seguridad y acceso.** Cada documento tiene `classification_level` (PÚBLICO / INTERNO / CONFIDENCIAL / RESTRINGIDO conforme a la política E-104 del propio cliente). Los documentos RESTRINGIDOS requieren verificación adicional para abrirse (re-autenticación WebAuthn). Esto es útil cuando el cliente te entrega documentación sensible (credenciales, contratos internos, datos de empleados).

#### 24.2 Arquitectura técnica

**Stack:**
- **Storage**: MinIO con Object Lock (WORM) en modo compliance para documentos vigentes. Retención configurable por tipo.
- **Índice léxico**: PostgreSQL `tsvector` en columna `search_vector` con trigger de actualización.
- **Índice semántico**: pgvector con IVFFlat, columna `embedding vector(1024)`.
- **Extracción de texto**: microservicio `doc-extractor` en Python con Unoconv + pdfplumber + Tesseract. Se ejecuta en cola Celery al subir un fichero.
- **Clasificación LLM**: Agente 26 (nuevo, ver Apéndice I), modelo Claude Haiku 4.5 (barato, rápido, suficiente para clasificar).
- **Deduplicación**: trigger en upload que calcula hash + consulta pgvector con threshold 0.95.
- **UI**: componente React Tree + drag & drop con `react-dnd` + vista de detalles con preview de PDF embebido.

#### 24.3 Flujos operativos clave

**Flujo 1 — Subida de un documento del cliente vía magic link:**
```
Cliente → magic_link.fulkro.es/upload/{token}
   ↓ subida (drag & drop del propio cliente)
microservicio doc-extractor
   ↓ texto extraído
Motor 24 Intake Pipeline
   ├─ cálculo hash SHA-256
   ├─ consulta duplicados (exacto + semántico)
   ├─ clasificación LLM (Agente 26)
   ├─ etiquetado medidas ENS (Agente 26)
   ├─ extracción de metadatos
   ├─ firma Ed25519 con clave de la plataforma
   ├─ insert document + document_version + document_tags
   ├─ generación embedding 1024-d
   └─ guardado en MinIO con ruta estructurada
   ↓
Notificación a Marcos en dashboard
```

**Flujo 2 — Búsqueda desde el dashboard:**
```
Marcos escribe query en buscador global (Cmd+K)
   ↓
Motor 24 Search
   ├─ embedding de la query
   ├─ consulta híbrida: tsvector + pgvector
   ├─ reranking con LLM si ambigüedad alta
   └─ resultados ordenados con snippets destacados
   ↓
UI muestra resultados con preview inline
```

**Flujo 3 — Vinculación de evidencias a medidas:**
```
Motor 7 (Evidence Collection) solicita evidencia de op.acc.5
   ↓
consulta document_tags con tag='op.acc.5' AND status='VIGENTE'
   ↓
si hay documentos → los sirve como evidencia
si no hay → genera magic link para que el cliente suba una evidencia nueva
```

#### 24.4 Responsabilidad compartida con otros motores

- **Motor 6 (Document Factory)** genera documentos vacíos/rellenados. Los deja en el Vault de Motor 24.
- **Motor 7 (Evidence Collection)** recopila evidencias del cliente. Las deja en Motor 24 con etiquetas de medida.
- **Motor 9 (Audit Preparation)** consulta Motor 24 para construir el dossier ordenado según la estructura §2.15.
- **Motor 11 (Copiloto)** usa Motor 24 como fuente de verdad para responder preguntas del contexto del cliente.
- **Motor 20 (Collaborative Workspace)** presenta al cliente una vista filtrada del Motor 24 (solo los documentos que el cliente debe ver/firmar).
- **Motor 25 (Lifecycle & Archival)** al archivar un proyecto, empaqueta todo el contenido del Motor 24 en un ZIP firmado.

---

### Motor 25 — Project Lifecycle & Archival Engine

**Nuevo en v2.1 — revisión abril 2026.** Gestiona el ciclo de vida completo del proyecto del cliente, incluyendo la fase final de **archivado y baja** cuando ya no es operativo. Responde a la pregunta: *"¿qué hago con el cliente Y cuando acabamos la colaboración? No puedo mantenerlo todo en la base de datos para siempre, pero tampoco puedo perder nada porque tengo obligaciones de conservación."*

#### 25.1 Estados del proyecto

```
DRAFT → NEGOTIATING → SIGNED → ACTIVE → CERTIFIED
                                   ↓
                               RETAINER (continuo)
                                   ↓
                              ENDED_RENEWAL_OK / ENDED_CHURN
                                   ↓
                               ARCHIVED
                                   ↓
                         PURGED (tras período legal)
```

- **ARCHIVED**: el proyecto ya no es operativo en la base de datos principal, pero sus datos completos están conservados en un paquete firmado en almacenamiento frío.
- **PURGED**: tras el período legal de conservación (típicamente 6 años desde el fin de la relación), el paquete se destruye conforme al procedimiento E-126 (Borrado Seguro).

#### 25.2 Proceso de archivado

Marcos decide archivar un cliente cuando:
- El retainer ha terminado sin renovación.
- El cliente ha solicitado formalmente el fin de la colaboración.
- El proyecto ha quedado huérfano (sin actividad > 12 meses tras fin del contrato).

**El archivado se ejecuta desde la UI con un botón "Archivar proyecto" que dispara un wizard**:

```
PASO 1/5 — VERIFICACIÓN
  ✓ Proyecto sin actividad pendiente
  ✓ Todas las facturas cobradas (o marcadas como incobrables con justificación)
  ✓ Sin incidentes abiertos
  ✓ Sin obligaciones legales subsistentes no cumplidas

PASO 2/5 — GENERACIÓN DEL PAQUETE COMPLETO
  ├─ Export de TODAS las tablas del cliente a JSON estructurado
  ├─ Export de TODOS los ficheros del cliente en MinIO
  ├─ Generación de índice maestro PDF
  ├─ Inclusión del histórico completo de audit_log filtrado por cliente
  └─ Empaquetado en ZIP

PASO 3/5 — FIRMA Y VERIFICACIÓN DE INTEGRIDAD
  ├─ Cálculo hash SHA-256 del ZIP
  ├─ Firma Ed25519 con clave de la plataforma
  ├─ Generación de manifiesto con inventario exhaustivo
  ├─ Verificación automática (desempaqueta en sandbox y re-verifica hashes)
  └─ Certificado de archivado generado

PASO 4/5 — MIGRACIÓN A ALMACENAMIENTO FRÍO
  ├─ Upload del ZIP cifrado a Hetzner Storage Box (o S3 Glacier alternativo)
  ├─ Registro en tabla `archived_projects` con referencia + manifiesto + hash
  └─ Programación automática de purge para fecha + 6 años

PASO 5/5 — PURGA DE LA BD PRINCIPAL
  ├─ Soft-delete masivo de todas las filas con client_id = X
  ├─ Revocación definitiva de magic links vigentes del cliente
  ├─ Eliminación del cliente del sidebar multi-cliente
  └─ Notificación a Marcos: "Proyecto SDL archivado. Manifiesto: archived_projects/SDL_2028-10-20.json"
```

El archivado es **reversible durante 30 días** (desde el archivo frío se puede restaurar). Pasado ese plazo, la restauración requiere un proceso manual de "unarchive" que Marcos tiene que aprobar explícitamente.

#### 25.3 Export puntual del proyecto (sin archivar)

Durante la vida del proyecto, Marcos puede querer exportar **una copia del estado actual** sin archivar. Casos de uso:
- El cliente pide "todo lo nuestro" en un ZIP.
- Se hace un snapshot antes de un cambio mayor.
- Se entrega una copia al auditor.
- Backup adicional personal de Marcos.

El botón **"Exportar proyecto"** genera el mismo ZIP firmado del archivado pero **sin purgar la BD**. Se puede ejecutar tantas veces como haga falta.

#### 25.4 Gestión del ciclo completo del cliente en el sidebar

El sidebar multi-cliente tiene **filtros de estado** para ver solo los clientes que interesan:

- 🟢 **Activos**: proyectos ACTIVE o RETAINER con actividad reciente.
- 🟡 **En espera**: proyectos SIGNED sin arrancar, o con parón documentado.
- ⚪ **Archivables**: proyectos ENDED sin actividad > 12 meses (candidatos a archivar).
- 📦 **Archivados**: proyectos ARCHIVED (solo referencia, clic para recuperar del frío si hace falta).
- 🗑️ **Purgados**: proyectos PURGED (solo tombstone, no recuperable).

---

### Motor 26 — Backup & Disaster Recovery Engine

**Nuevo en v2.1 — revisión abril 2026.** Consolida en un motor dedicado toda la estrategia de backups de la propia plataforma FULKRO. Complementa la Parte 8 (Dogfooding ENS Medio) con un enfoque operativo de primera clase: backups automáticos, pruebas de restauración periódicas, exportación por cliente, recuperación ante desastre y verificación de integridad.

Este motor existe porque **la plataforma gestiona los datos más valiosos del cliente** (dossieres de auditoría, evidencias firmadas, contratos, facturas). Si la plataforma se pierde, Marcos pierde su negocio y los clientes pierden sus certificaciones. Por eso el backup no puede ser un apéndice de "dogfooding" sino un motor de primer nivel.

#### 26.1 Tipos de backup

**A) Backup continuo de base de datos (PostgreSQL):**
- **pgBackRest** en modo `async` con replicación continua de WAL.
- Backup completo diario + incrementales cada 4 horas + WAL continuo (Point-in-Time Recovery).
- Retención: 7 diarios, 4 semanales, 12 mensuales, 5 anuales.
- Cifrado con AES-256 (clave gestionada por Marcos vía Vault).
- Almacenamiento en Hetzner Storage Box (primer destino) + replicación asíncrona a segundo Storage Box en región geográficamente separada (Helsinki + Falkenstein).
- Verificación automática: después de cada backup, se restaura en un contenedor efímero y se valida que la BD arranca y tiene las tablas esperadas.

**B) Backup de almacenamiento de objetos (MinIO):**
- Replicación activa entre dos buckets MinIO con `mc mirror --continuous`.
- Snapshots diarios del bucket con `rclone snapshot`.
- Verificación semanal de integridad: re-cálculo de hashes SHA-256 de una muestra aleatoria del 5% + verificación contra los hashes almacenados en la BD.
- Alertas si alguna discrepancia.

**C) Backup de configuración y secretos:**
- Terraform state cifrado en Storage Box.
- Ansible playbooks en Git privado.
- Secretos en Vault con backup cifrado de la unsealed key (compartida entre 3 custodios por Shamir).
- API keys rotados trimestralmente con cambio de referencia atómico.

**D) Backup de logs inmutables:**
- `audit_log` con hash chain (cada entry enlaza con el hash de la anterior).
- Export periódico a almacenamiento WORM (S3 Object Lock en modo Compliance, retención 10 años).
- Verificación de la cadena trimestral.

#### 26.2 Pruebas periódicas de restauración (obligatorias)

**v2.1 establece como política operativa:**

| Tipo de prueba | Frecuencia | Procedimiento |
|---|---|---|
| **Restore parcial de BD** | Semanal | Restore de un schema concreto en sandbox y validación de datos |
| **Restore completo de BD** | Mensual | Reconstrucción íntegra de la BD en servidor efímero, validación exhaustiva, destrucción del sandbox |
| **Restore de MinIO** | Mensual | Recuperación de 100 objetos aleatorios y verificación de hashes |
| **Ejercicio de Disaster Recovery completo** | Trimestral | Reconstrucción completa de la plataforma desde cero en un servidor Hetzner nuevo siguiendo el runbook Terraform + Ansible. RTO objetivo: 4 horas. RPO objetivo: 1 hora. |
| **Restore de un proyecto archivado** | Semestral | Recuperación de un proyecto desde el frío y verificación de integridad del manifiesto |

**Todas las pruebas son automatizadas** (excepto la restauración semestral de un proyecto archivado, que es semi-manual). Los resultados se registran en la tabla `backup_restore_tests` como evidencia para el propio SGSI de la plataforma.

#### 26.3 UI de backups en el dashboard

Marcos tiene acceso a un panel en el dashboard de Operaciones (no por cliente sino global de la plataforma):

```
ESTADO DE BACKUPS — FULKRO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PostgreSQL
  Último backup completo: 10 oct 2026, 03:00 (OK, 2.4 GB)
  Último incremental:     10 oct 2026, 15:00 (OK, 120 MB)
  WAL continuo:           ACTIVO
  Último restore test:    06 oct 2026 (OK, 47 seg)
  Retención actual:       7d / 4w / 12m / 5y

MinIO
  Buckets replicados:     2/2 ✓
  Último snapshot:        10 oct 2026, 04:00 (OK, 48.2 GB)
  Último restore test:    03 oct 2026 (OK, 100/100 objetos)
  Verificación integridad:09 oct 2026 (OK, 5% muestra)

Configuración
  Terraform state:        Sincronizado ✓
  Ansible playbooks:      Sincronizado ✓
  Vault:                  Sellado ✓

Logs inmutables
  Cadena verificada:      01 oct 2026 (OK, hash chain íntegra)
  Tamaño WORM:            18.7 GB
  Próxima verificación:   01 ene 2027

DR Drill
  Último ejercicio:       15 sep 2026 (OK, RTO 3h 12min)
  Próximo ejercicio:      15 dic 2026
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[Ejecutar backup manual] [Probar restore] [Ejercicio DR completo]
```

#### 26.4 Coordinación con Motor 25

Cuando Motor 25 archiva un proyecto, Motor 26 intercepta el paquete ZIP para:
1. Verificar que está firmado correctamente.
2. Incluirlo en el ciclo de backup del almacenamiento frío.
3. Registrar su hash en la cadena inmutable.
4. Programar las verificaciones futuras.

---

## PARTE 6 — AGENTES IA CON ANTI-ALUCINACIÓN

Lista de agentes con propósito, modelo, prompt base resumido, anti-alucinación.

| # | Agente | Modelo | Anti-alucinación |
|---|---|---|---|
| 1 | Parser Normativo (ingesta corpus al grafo) | Sonnet 4.5 | Validación de schema, citas obligatorias, no extrae lo que no está |
| 2 | Analizador de Pliegos | Sonnet 4.5 | RAG sobre el pliego subido + plantillas de extracción estructurada |
| 3 | Scoping/Categorización Asistida (chat) | Sonnet 4.5 | Decisión final por Motor 1 determinista |
| 4 | Redactor Políticas/Procedimientos | Opus 4 | Plantillas docxtpl inmutables, LLM solo rellena huecos personalizados con grounding |
| 5 | Analista MAGERIT | Opus 4 | Catálogos precargados, cálculos por Motor 2 determinista |
| 6 | Analista de Contratos | Sonnet 4.5 | Reglas + LLM para detectar cláusulas faltantes; no propone redacción legal sin grounding |
| 7 | Gap Analyzer con priorización | Sonnet 4.5 | Lista de gaps generada por Motor 4 determinista; LLM solo prioriza con explicación |
| 8 | Planificador de Obligaciones | Sonnet 4.5 | Biblioteca de obligaciones (JSON), LLM solo personaliza textos |
| 9 | Orquestador Pentest | Opus 4 | Hallazgos vienen de herramientas reales; LLM no inventa, solo interpreta y prioriza |
| 10 | Redactor Informes Pentest | Opus 4 | Cada afirmación vinculada a un finding real con id |
| 11 | Auditor Interno Virtual | Opus 4 | Preguntas generadas desde el grafo (las 73 medidas); validación de evidencia por reglas |
| 12 | Coach del Cliente | Sonnet 4.5 | Preguntas tipo desde plantillas; respuestas evaluadas con rúbrica |
| 13 | Generador Dossier Final | Sonnet 4.5 | Lista de entregables verificada por Motor 9 determinista |
| 14 | Copiloto ENS Conversacional (Motor 11) | Sonnet 4.5 / Opus 4 | RAG obligatorio, citas obligatorias, modo "no lo sé" |
| 15 | Vigilancia Normativa | Haiku 4 | Solo detecta cambios; no decide sobre ellos |
| 16 | Generador Quick Wins | Sonnet 4.5 | Lista de quick wins precargada, LLM solo selecciona los aplicables |
| 17 | Cualificador Comercial | Sonnet 4.5 | Reglas de lead scoring deterministas + LLM para contexto. Output: puntuación 0-100 con desglose |
| 18 | Asistente de Reunión Exploratoria | Sonnet 4.5 | Plantilla guiada con bloques A-F. LLM solo estructura notas, Motor 1 estima categoría preliminar |
| 19 | Redactor de Propuestas Comerciales | Opus 4 | Plantilla docxtpl P-001 inmutable. Importes vienen del pricing_model, esfuerzos del effort_estimator |
| 20 | Asistente de Negociación | Sonnet 4.5 | Rangos aceptables precargados por Marcos. LLM solo propone alternativas dentro de rangos |
| 21 | Detector de Discrepancias (Dirección vs TI) | Opus 4 | Compara notas de scoping_direccion vs scoping_ti y marca contradicciones |
| 22 | Analista de Stakeholders | Opus 4 | Construye grafo Apache AGE con relaciones tipadas. Notas confidenciales solo Marcos |
| 23 | Mapeador de Procesos de Negocio | Opus 4 | Genera diagramas BPMN con Mermaid a partir de entrevistas guiadas. Alimenta BIA |
| 24 | Detector de Obligaciones Cruzadas | Sonnet 4.5 | Regla sectorial → normativa aplicable. Cita siempre la base normativa |
| 25 | Generador de Data Flow Diagrams | Sonnet 4.5 | Diagramas SVG/Mermaid a partir de inventario descubierto por Motor 22 |
| 26 | Coach de Auditoría y Crisis | Opus 4 | Guiones de simulacro y preguntas tipo auditor. Nunca recetas para mentir |

**Reglas universales para todos los agentes:**
- Temperatura ≤ 0.2 para tareas factuales.
- System prompt siempre incluye "Si no encuentras información en el corpus o en el contexto del proyecto, responde 'No encontrado' en lugar de inventar."
- Toda respuesta sobre normativa debe tener al menos una cita.
- Las decisiones que afectan a la DdA, a la categorización, a las estimaciones económicas o a cláusulas contractuales pasan por motores deterministas, nunca solo por LLM.
- Cada llamada a LLM se loguea con: prompt, respuesta, modelo, tokens, latencia, citas extraídas.
- Los nuevos agentes comerciales y organizacionales (17-26) están sujetos a las mismas reglas que los agentes normativos, con especial énfasis en:
  - **Agente 19 (Redactor de Propuestas):** prohibido inventar importes, plazos o entregables. Todo viene del contexto estructurado.
  - **Agente 20 (Negociación):** prohibido aceptar ajustes fuera de rangos preautorizados por Marcos.
  - **Agente 22 (Stakeholders):** notas confidenciales nunca expuestas al cliente ni a otros agentes salvo Marcos explícitamente.
  - **Agente 26 (Coach):** prohibido sugerir respuestas que oculten hechos al auditor.

---

## PARTE 7 — INTEGRACIONES CCN OFICIALES

**Estado a abril 2026:** las herramientas oficiales del CCN no tienen APIs públicas modernas. La integración se hace por ingesta de ficheros, certificado digital y, en algunos casos, scraping autorizado.

| Herramienta | Estado API 2026 | Integración en la plataforma |
|---|---|---|
| **PILAR / µPILAR / PILAR Basic** | Sin API pública. Trabaja con ficheros propios (.mgr). | Motor 2 (MAGERIT propio) genera ficheros compatibles para que Marcos los importe en PILAR si el cliente / auditor lo exige. Si en el futuro hay API, conector inmediato. |
| **LUCIA** | Acceso vía certificado digital (FNMT/DNIe). Sin API REST documentada. | El procedimiento de gestión de incidentes (E-204) genera un draft del reporte LUCIA en el formato exigido. Marcos lo sube manualmente a LUCIA con su certificado. La plataforma guarda el ID LUCIA devuelto. Si en el futuro hay API, automatización. |
| **INES** | Rediseñado en junio 2025. Acceso web autenticado. Sin API pública. | El motor de informes (E-709) genera el snapshot del estado de seguridad en el formato CCN-STIC 824 listo para subir a INES. |
| **CLARA** | Cliente que se ejecuta sobre Windows/Linux. Outputs en XML/HTML. | La plataforma ingesta los outputs de CLARA cuando Marcos los sube, los parsea, los mapea a medidas del Anexo II y los registra como evidencia para `op.exp.2` y `op.exp.3`. |
| **CCN-CERT feeds** | RSS/Atom públicos en https://www.ccn-cert.cni.es/. | Agente de vigilancia normativa los consume cada hora, filtra por relevancia y notifica a Marcos. Cubre `op.mon.3`. |
| **CPSTIC catalog** | Página web pública en https://oc.ccn.cni.es/es/. Sin API. | Scraping respetuoso semanal (con caché) para mantener tabla local actualizada. Sugerencias de productos en el motor de obligaciones. |
| **AMPARO** (gestión de conformidad) | Plataforma del CCN para entidades públicas, no aplicable directamente al cliente privado de Marcos. | No integración inicial. Marcos puede consultar el estado de sus clientes certificados en el portal Gobernanza del CCN. |
| **EVENS** (autoevaluación) | Plataforma del CCN para autoevaluación. | El motor de auditoría interna (Motor 10) genera un formato compatible si Marcos lo necesita exportar a EVENS. |
| **MARGA** (entidades locales) | Específico para ayuntamientos. No aplicable a clientes privados. | No integración. |
| **ROCIO, ANA, ADELA, ELENA, MARTA, ELSA, CARMEN** | Herramientas internas del CCN o de uso muy específico. La mayoría no aplican al cliente privado. | Verificar caso a caso si en algún momento un cliente las exige. No integración inicial. |

---

## PARTE 8 — SEGURIDAD DE LA PROPIA PLATAFORMA (DOGFOODING ENS MEDIO)

La plataforma debe cumplir ENS Medio sobre sí misma. Si un cliente o un auditor te pregunta "¿y la plataforma con la que gestionas mis datos cumple ENS?", la respuesta tiene que ser "sí, y aquí tienes mi propia DdA y mis evidencias".

**Cifrado:**
- **At-rest:** disco LUKS, PostgreSQL con TDE vía `pgcrypto` para columnas sensibles, MinIO/S3 con SSE.
- **In-transit:** TLS 1.3 obligatorio en todo, HSTS, certificate pinning para integraciones críticas.

**Autenticación de Marcos:**
- WebAuthn obligatorio con hardware key Yubikey (al menos 2 keys).
- Sin password fallback.
- Sesiones cortas (8 horas), re-autenticación para acciones críticas.

**Gestión de secretos:**
- HashiCorp Vault o `pass` (gpg + git) para secretos del sistema.
- API keys de Anthropic, Hetzner, etc. nunca en código.
- Rotación trimestral.

**Logs de auditoría inmutables:**
- pgAudit a nivel de base de datos.
- Tabla `audit_log` con triggers en cada tabla principal.
- Hash chain: cada entrada del audit_log incluye `prev_hash` y `current_hash`, formando una cadena verificable.
- Export periódico a almacenamiento WORM (S3 Object Lock o similar).

**Backup y DRP:**
- pgBackRest con cifrado y verificación.
- Pruebas mensuales automatizadas de restauración (la plataforma se restaura sola en un servidor temporal, valida que arranca, destruye el servidor, deja informe).
- DRP documentado: RTO 4h, RPO 24h, procedimiento Terraform + Ansible para reconstruir todo desde cero.

**Hardening Hetzner:**
- Debian 12 hardenizado según CIS Benchmark.
- Firewall UFW restrictivo.
- SSH solo Ed25519 desde IPs autorizadas, fail2ban.
- AppArmor activo.
- `unattended-upgrades` con auto-reboot.
- AIDE para integridad de ficheros.
- Suscripción a CCN-CERT feeds para vulnerabilidades del propio stack.

**Magic links seguros:**
- Tokens Ed25519 firmados.
- TTL corto.
- OTP separado por canal distinto.
- Rate limiting agresivo.
- Geo-bloqueo opcional.
- Revocación inmediata desde dashboard.

**Escaneo continuo de la propia plataforma:**
- Trivy semanal sobre las imágenes Docker.
- Nuclei semanal sobre la URL pública.
- OpenVAS mensual interno.
- Lynis mensual sobre el host.
- Hallazgos van al motor de findings con severidad.

**Firma de evidencias:**
- Cada evidencia que entra al vault se firma con Ed25519 con clave privada de la plataforma.
- Hash SHA-256 + firma + timestamp.
- Verificable externamente con la clave pública publicada.

---

## PARTE 9 — PLAN DE CONSTRUCCIÓN EN FASES (40 SEMANAS)

Plan ejecutable por Marcos solo con Claude Code. Cada semana entrega algo funcional. **Recalibrado en v2.0** para incluir los 11 motores y 10 agentes nuevos, y para priorizar que el ciclo comercial esté operativo antes que el ciclo técnico (Marcos necesita firmar clientes para que la implantación tenga sentido).

### ⚠️ ADVERTENCIA CRÍTICA DE CONSTRUCCIÓN — QUÉ NO ES AUTO-GENERABLE

Antes de empezar el plan, Marcos debe entender que **las 110 plantillas DOCX del Motor 6 no son auto-generables por Claude Code** al 100% con calidad de auditor ENAC. Son el **único trabajo manual intensivo** del proyecto y hay que planificarlo aparte:

- **27 políticas (E-100 a E-126)**: requieren redacción legal real. Cada una debe estar alineada con el RD 311/2022, las CCN-STIC correspondientes, y el criterio del auditor ENAC veterano. Estimación: **40-80 horas de redacción legal** para el paquete completo (Marcos + consultor ENS senior contratado ad-hoc + abogado TIC de revisión).
- **35 procedimientos (E-200 a E-234)**: requieren conocimiento operativo real. Estimación: **50-100 horas de redacción** con el mismo equipo.
- **26 registros (E-300 a E-325)**: son plantillas XLSX más simples, 10-20 horas.
- **Plantillas de continuidad (BIA, BCP, DRP)**: 20-30 horas de redacción especializada.
- **Plantillas comerciales (P-001 propuesta, C-001 contrato, C-003 retainer)**: 20-40 horas de redacción jurídica con abogado mercantilista español.

**Total: 140-270 horas de trabajo de redacción humana** que Claude Code no puede hacer con suficiente calidad. Ver Apéndice L para plan de mitigación.

Claude Code construye la **estructura docxtpl** (Jinja2 placeholders, lógica de personalización, pipeline de generación, firma, versionado) — **no el contenido legal real de las plantillas**. Marcos debe meter el contenido real en paralelo al desarrollo técnico.

**Recomendación:** contratar a un consultor ENS senior por 2-3 semanas al 50% de dedicación durante las semanas 9-15 del plan, y un abogado TIC por 20-30 horas durante las semanas 8-11. Presupuesto orientativo: 8.000-15.000 €. Sin esto, la plataforma estará técnicamente lista pero sin munición real.

---

### Plan semana a semana

### Semanas 1-2: Fundamentos
- Provisioning Hetzner CCX33, hardening, Docker, Caddy con HTTPS.
- Stack base: FastAPI, PostgreSQL 16 + extensiones, Redis, Celery, Temporal.
- Auth de Marcos con WebAuthn.
- Modelo de datos base (clients, projects, leads, audit_log).
- CI/CD básico con GitHub Actions + deploy a Hetzner.
- **Entregable:** Marcos puede loguearse en su plataforma, crear un lead y convertirlo en proyecto.

### Semanas 3-5: Corpus ENS al grafo + RAG
- Ingesta del RD 311/2022 (BOE) → tablas + grafo AGE.
- Ingesta de Anexo I, II, III, IV con las 73 medidas correctamente modeladas (4 org + 33 op + 36 mp).
- Ingesta de las 20 guías CCN-STIC prioritarias (800-835).
- Ingesta de las ITS (Auditoría, Conformidad, Notificación Incidentes, Informe Estado Seguridad, Registro Conformidad).
- Ingesta de los PCE aplicables al mercado privado.
- Chunking semántico, embeddings BGE-M3, índices HNSW.
- Búsqueda híbrida (BM25 + vectorial + re-ranking).
- **Entregable:** Marcos pregunta al copiloto "¿qué me pide op.acc.6 R1?" y obtiene respuesta con citas.

### Semanas 6-7: Motor 16 Adaptive Onboarding + Motor 20 Collaborative Workspace
- Matriz de 70 plantillas de onboarding (10 sectores × 7 roles).
- Conectores OAuth: M365/Entra ID, Google Workspace, AWS, Azure, GCP (mínimo 5 al inicio).
- Servidor MCP local para queries agregadas.
- Gestor documental minimalista por proyecto.
- LiveKit self-hosted para videollamadas bajo demanda.
- Feed de notificaciones + chat asíncrono.
- **Entregable:** Marcos crea un proyecto y envía el onboarding completo al cliente ficticio, que lo rellena vía magic link y conecta su M365 read-only.

### Semanas 8-9: Motor 13 Commercial Doc Factory + Motor 14 Contracts + Motor 15 Billing
- Plantillas P-001 (propuesta 10-20 páginas) y C-001 (contrato con cláusula de recursos del cliente).
- Generador docxtpl → PDF con LibreOffice headless.
- Tema visual de marca (colores, tipografía, logo).
- Diagramas Gantt con Mermaid.
- Firma electrónica avanzada vía magic link con sello de tiempo.
- Facturación fiscal española (número correlativo, IVA, IRPF) con Verifactu-ready.
- Facturación recurrente de retainer.
- Facturación de parones por incumplimiento de recursos.
- **Entregable:** Marcos genera propuesta + contrato + factura inicial para un lead, el cliente firma vía magic link, la factura se emite automáticamente.

### Semanas 10-11: Motor 17 Project Planning + Motor 18 Communication + Motor 19 Risk Mgmt
- WBS determinista por categoría (B/M/A) con ~150-350 tareas precargadas.
- Cronograma Gantt con ruta crítica.
- Estimador de esfuerzo `effort_estimator` calibrado.
- Status reports automáticos (weekly, monthly, quarterly).
- Catálogo precargado de ~30 riesgos del proyecto consultor.
- Dashboard de riesgos con semáforo.
- Disparo automático de planes de contingencia.
- **Entregable:** Marcos firma un cliente y en 10 minutos tiene plan de proyecto completo, plan de comunicación configurado, plan de riesgos instanciado.

### Semanas 12-13: Motor 1 Categorización + Motor 3 DdA + Motor 6 Document Factory
- Motor 1 — Categorization Engine (determinista).
- Motor 3 — DdA Engine con las 73 medidas modeladas.
- Motor 6 — Document Factory con las primeras ~30 plantillas críticas (E-001, E-002, E-003, E-005, E-012, E-040, E-050, E-101, E-102, E-107, E-108, E-204, E-500).
- Pipeline DOCX → PDF.
- Versionado de documentos.
- **Entregable:** Marcos rellena las valoraciones del cliente y la plataforma genera la categorización, la DdA completa firmable y las 30 políticas/procedimientos críticas.

### Semanas 14-15: Motor 22 Technical Discovery
- Asset Discovery (Nmap + conectores cloud).
- Identity Discovery (export AD/Entra ID).
- Configuration Discovery (Lynis, CIS-CAT, testssl.sh, DNS).
- Vulnerability Discovery (OpenVAS, Nuclei).
- Data Flow Mapping (Agente 25).
- Integración con el project knowledge graph.
- **Entregable:** Marcos pulsa "ejecutar discovery técnico" sobre el cliente y obtiene inventario completo de activos, identidades, configuraciones, vulnerabilidades en pocas horas.

### Semanas 16-17: Motor 21 Organizational Diagnosis + Agentes 22, 23, 24
- Agente 22 — Analista de Stakeholders con grafo AGE.
- Agente 23 — Mapeador de Procesos de Negocio.
- Agente 24 — Detector de Obligaciones Cruzadas (RGPD, NIS2, DORA, sectorial).
- Informe de Diagnóstico Inicial (E-090) de 30-80 páginas.
- **Entregable:** Marcos pulsa "generar diagnóstico completo" tras onboarding + discovery y obtiene el informe listo para presentar al Comité del cliente.

### Semanas 18-19: Motor 2 MAGERIT + Motor 4 Gap + Motor 5 Obligations
- Catálogos MAGERIT v3 (activos, amenazas, salvaguardas) precargados.
- Cálculo intrínseco/efectivo/residual.
- Exportación a formato PILAR (.mgr).
- Motor 4 — Gap Analysis Engine.
- Motor 5 — Obligations & Planning con biblioteca precargada (~250 plantillas de obligaciones).
- Los 4 modos de ejecución (consultor_genera, cliente_aporta, acción_tecnica_remota, acción_manual).
- **Entregable:** Marcos obtiene AR completo + Plan de Adecuación + backlog de obligaciones ejecutables automáticamente.

### Semanas 20-21: Motor 12 Magic Link Engine + Evidence Vault
- JWT Ed25519 + OTP por email.
- Plantillas de los ~12 tipos de magic link.
- Páginas HTMX minimalistas para cada operación del cliente.
- Evidence Vault con hash + firma Ed25519 + timestamp.
- Tracking de caducidad de evidencias.
- Audit trail criptográficamente inmutable (hash chain).
- **Entregable:** Marcos opera un ciclo completo de obligación con el cliente: genera entregable, lo envía, el cliente lo firma, queda archivado con cadena de evidencia verificable.

### Semanas 22-24: Motor 8 Pentesting & Red Team
- Red Docker `pentest-net` aislada.
- Integración Nmap, Nuclei, OpenVAS, ZAP, Metasploit, Prowler, CLARA, Lynis, Trivy, Semgrep, testssl.sh (11 herramientas).
- Servidor MCP local para orquestación dinámica por Agente 9.
- Pipeline de ejecución asíncrono con Temporal.
- Normalización de findings al modelo común.
- Mapeo a medidas ENS y MITRE ATT&CK.
- Generación de informe DOCX/PDF en formato auditor español (E-702, E-703).
- Integración con Caldera para Red Team en Alta (E-704).
- **Entregable:** Marcos ejecuta pentest completo sobre cliente ficticio en VM aislada, obtiene informe profesional con ~decenas de findings mapeados.

### Semanas 25-26: Resto de plantillas documentales
- Completar las ~80 plantillas restantes del Document Factory (políticas menores, procedimientos no críticos, registros operativos, BIA, BCP, DRP, formación).
- Mini-LMS para formación interna del cliente.
- Integración con GoPhish self-hosted para simulacros.
- **Entregable:** Marcos puede generar TODOS los entregables de la Parte 2 para un cliente de cualquier categoría.

### Semanas 27-28: Motor 9 Audit Preparation + Motor 10 Audit Simulation + Agente 11
- Motor 9 — Audit Preparation Engine con checklist de pre-auditoría.
- Motor 10 — Audit Simulation Engine (auditor virtual).
- Agente 11 — Auditor Interno Virtual con las 73 medidas y los grados L0-L5.
- Generador del ZIP estructurado de la sección 2.15.
- Generador de la matriz cruzada del 99.
- PDF maestro navegable.
- **Entregable:** Marcos lanza pre-auditoría virtual y obtiene informe estilo ENAC + dossier final listo para entregar al auditor real.

### Semanas 29-30: Motor 11 Copiloto + Agentes comerciales y de onboarding
- Implementación completa del Motor 11 con UI chat.
- Agente 17 — Cualificador Comercial.
- Agente 18 — Asistente de Reunión Exploratoria (interfaz guiada con bloques A-F).
- Agente 19 — Redactor de Propuestas Comerciales.
- Agente 20 — Asistente de Negociación.
- Agente 21 — Detector de Discrepancias.
- Agente 25 — Generador de DFD.
- Agente 26 — Coach de Auditoría y Crisis.
- **Entregable:** Marcos lleva una reunión exploratoria con la plataforma asistiendo en vivo, genera propuesta en 10 min, negocia y firma contrato. Todo desde la plataforma.

### Semanas 31-32: Motor 14 Contracts avanzado + Motor 15 Billing fiscal completo
- Análisis automático de contratos de proveedores del cliente con Agente 6.
- Generación de adendas contractuales para proveedores.
- Tracker de compromisos del cliente (cláusula de recursos).
- Detección automática de parones facturables.
- Integración con Verifactu/TicketBAI/SII.
- Dashboard de tesorería.
- Exportación contable (Holded/Contasimple/Quipu).
- **Entregable:** Marcos tiene un sistema comercial + contractual + fiscal completo y cumple con las obligaciones fiscales españolas de 2026.

### Semanas 33-34: Motor 23 Retainer Management + Multi-cliente
- Calendarización automática de actividades anuales obligatorias.
- Dashboard multi-cliente con semáforo RAG.
- Periodicidad de Comités automatizada.
- Simulacros periódicos.
- Reporting trimestral.
- Facturación recurrente.
- **Entregable:** Marcos gestiona 5 clientes ficticios en retainer simultáneos desde un único dashboard, dedicando 2h/semana al total.

### Semanas 35-36: Agente 15 Vigilancia Normativa + Integración LUCIA/PILAR/INES
- Agente 15 con crawling diario de CCN, BOE, feeds CCN-CERT.
- Detección y notificación de cambios.
- Ingesta automática de nuevas ITS y guías CCN-STIC.
- Integración con LUCIA (carga manual asistida con certificado digital).
- Integración con PILAR (importación/exportación .mgr).
- Integración con INES (generación del informe anual).
- **Entregable:** Marcos recibe alerta automática cuando el CCN publica una guía nueva, la plataforma la ingesta sola.

### Semanas 37-38: Seguridad propia plataforma + Dogfooding ENS Medio
- Auto-aplicación de la plataforma a sí misma (la plataforma cumple ENS Medio sobre sí misma).
- Política de Seguridad propia, DdA propia, AR propio, procedimientos propios.
- Pentest periódico automatizado sobre la propia plataforma.
- Pruebas mensuales de restauración.
- Certificación propia.
- **Entregable:** Marcos puede mostrar a cualquier cliente desconfiado su propia certificación ENS Medio de la plataforma.

### Semanas 39-40: Pulido final + Primer cliente real
- Tests E2E completos de los 10 fases del ciclo del consultor.
- Documentación interna para Marcos.
- Vídeos de formación interna (cómo usar cada motor).
- Primer cliente real piloto en condiciones controladas.
- Post-mortem del primer proyecto completo.
- **Entregable:** Marcos cierra su primer cliente con la plataforma v2.0 operativa y ha validado las 10 fases end-to-end.

---

### 9.13 Plan de integración de los Motores 24, 25 y 26 (revisión abril 2026)

Los tres motores nuevos (IDMS, Lifecycle/Archival, Backup/DR) no son un bloque monolítico que se construya al final: se integran en el plan de 40 semanas de forma escalonada para que estén disponibles cuando realmente se necesitan.

**Motor 26 — Backup & Disaster Recovery (semanas 4-6, en paralelo con el dogfooding):**
- Se construye **lo primero** porque la plataforma genera datos valiosos desde el día 1 y no se puede estar sin backup ni una sola semana.
- Semana 4: pgBackRest + replicación WAL + retención básica + primer backup completo.
- Semana 5: MinIO mirror + snapshots + verificación de integridad + Vault backup.
- Semana 6: primer DR drill completo (reconstrucción en servidor efímero con Terraform+Ansible) + tabla `backup_jobs` + panel básico en el dashboard de Operaciones.
- **Criterio de salida:** tener al menos un backup completo verificado y un restore test pasado antes de empezar a ingerir datos del primer cliente real.

**Motor 24 — Intelligent Document Management (semanas 14-20):**
- Se construye **antes de la implantación con el primer cliente piloto** porque es donde se masifica la carga de documentos.
- Semana 14: esquema de tablas del IDMS + migración de la antigua tabla `documents` + estructura de carpetas estándar autogenerada.
- Semana 15: microservicio `doc-extractor` multi-formato con cola Celery + extracción de texto + cálculo de hash + detección de duplicados exactos.
- Semana 16: `tsvector` con índice GIN + primer buscador léxico funcional + UI vista de árbol + vista de lista + drag & drop básico.
- Semana 17: pgvector + embeddings con modelo local `multilingual-e5-large` + búsqueda semántica + deduplicación semántica + búsqueda híbrida.
- Semana 18: Agente 27 con clasificación automática + etiquetado automático por medidas ENS + metadatos extraídos + dashboard de documentos por vencer.
- Semana 19: panel derecho de detalle + preview embebido (PDF.js) + historial de versiones con diffs + firma visual + enlaces bidireccionales con medidas/controles.
- Semana 20: integración con Copiloto (Motor 11) para "chat con el repositorio" + modo sesión de subida masiva + buscador global Cmd+K.
- **Criterio de salida:** poder cargar 200 documentos mezclados a la vez y que la plataforma los clasifique, etiquete y archive correctamente con < 5 % de revisión humana.

**Motor 25 — Project Lifecycle & Archival (semanas 28-30):**
- Se construye **después del primer cliente real** porque solo se necesita cuando ya hay proyectos maduros que puedan entrar en fase final.
- Semana 28: máquina de estados del proyecto + tabla `project_lifecycle_states` + transiciones permitidas + integración con Motor 14 (Contracts) y Motor 15 (Billing) para cerrar facturación pendiente antes de archivar.
- Semana 29: wizard de archivado de 5 pasos + generación del ZIP completo con firma Ed25519 + manifiesto JSON + migración al Storage Box frío + tabla `archived_projects` + export puntual sin archivar.
- Semana 30: flujo de restauración desde frío + filtros de estado en el sidebar + botón de archivar en el dashboard del cliente + verificación automática de integridad del paquete archivado + ventana de reversibilidad de 30 días.
- **Criterio de salida:** archivar un proyecto de prueba real, destruir su contenido de la BD principal, y poder restaurarlo completamente desde el Storage Box en menos de 1 hora.

**Refuerzo del tenant virtual (semanas 8-10, en paralelo con los motores iniciales):**
- Sidebar multi-cliente con lista de clientes filtrable por estado.
- Switch rápido Cmd+K con fuzzy finder sobre clientes, acciones y navegación.
- URL amigable por cliente (`fulkro.es/clients/{slug}/...`) con RLS reforzado por middleware.
- Dashboard específico por cliente con widgets personalizables.
- Carpetas estructuradas en MinIO con prefijo obligatorio `fulkro/clients/{nif}/projects/{project_id}/...`.

**Dependencias entre motores nuevos y existentes:**

| Motor nuevo | Depende de | Lo usa |
|---|---|---|
| Motor 26 (Backup) | Ninguno — construcción base | Toda la plataforma desde el día 1 |
| Motor 24 (IDMS) | Motor 6, Motor 7, Motor 11, Motor 20 | Motor 9 (Audit Prep), Motor 10 (Audit Sim), Motor 25 |
| Motor 25 (Lifecycle) | Motor 14, Motor 15, Motor 24, Motor 26 | Sidebar multi-cliente, dashboard de Operaciones |
| Agente 27 | Motor 24 | Motor 7, Motor 24 |

**Impacto en el calendario de las 40 semanas:** los motores 24/25/26 añaden aproximadamente **6 semanas de trabajo efectivo** que se absorben en paralelo con otros motores ya planificados. El calendario global no se extiende más allá de las 40 semanas porque Motor 26 solapa con el setup inicial (sem 4-6), Motor 24 solapa con Motor 6 y Motor 7 (sem 14-20) y Motor 25 entra tras el primer cliente piloto (sem 28-30). El primer cliente piloto sigue cerrándose en la semana 36.

---

## PARTE 10 — CÓMO LA PLATAFORMA GARANTIZA AUDITORÍA PERFECTA

Mecanismos concretos por los que esto no falla en la auditoría ENAC:

1. **Cobertura 1:1 medida ↔ evidencia.** Las 73 medidas están modeladas y cada una tiene su lista de evidencias requeridas por el catálogo (Parte 2.13). El motor 9 verifica antes de generar el dossier que no falta ninguna.

2. **Validación cruzada DdA ↔ Control Engine ↔ Evidence Vault.** Si la DdA dice "op.exp.4 implantado con R1" pero el Control Engine dice "no hay evidencia válida" o "evidencia caducada", la plataforma marca contradicción crítica y no permite generar el dossier hasta resolver.

3. **Pre-auditoría con rigor ENAC.** El Motor 10 simula una auditoría con la profundidad y formato de un auditor real. Si falla la pre-auditoría, falla la real.

4. **Frescura de evidencias.** Cada evidencia tiene `fecha_caducidad`. Las que están a < 30 días caducidad generan tareas automáticas de re-recolección. Cuando el dossier se genera, todas las evidencias están vigentes a esa fecha.

5. **Detección proactiva de contradicciones.** El Copiloto valida cruzadamente lo que dicen las políticas, los procedimientos y las evidencias. Si la política dice "MFA universal" pero la evidencia muestra MFA al 70%, lo marca.

6. **Registros operativos forzados.** Desde el día 1 del proyecto, la plataforma fuerza al cliente vía magic links recurrentes a aportar registros mensuales. Cuando llega la auditoría hay 6 meses de registros reales.

7. **Formato auditor español.** Plantillas validadas, dossier con la estructura exacta de la sección 2.15, matriz cruzada del 99 que el auditor abre y verifica todo en 30 minutos.

8. **Checklist final automática.** Antes de entregar el dossier, una checklist verifica: ¿están todas las políticas firmadas y vigentes? ¿están todos los procedimientos con registros de los últimos 6 meses? ¿está la DdA firmada por el RSEG? ¿están las actas del comité de los últimos 12 meses? ¿está el AR aprobado por la dirección? ¿está el plan de adecuación vigente? Si algo falla, no se genera el dossier.

---

## PARTE 11 — CHECKLIST MASTER + INTEGRACIÓN CON ENS RADAR

### 11.1 Checklist master "lo que no puede faltar nunca"

- [ ] Política de Seguridad firmada por el órgano superior y difundida con acuse.
- [ ] Acta de nombramiento de los 4 roles ENS (Información, Servicio, Seguridad, Sistema).
- [ ] Acta de constitución del Comité de Seguridad + actas de los últimos 12 meses.
- [ ] Acta de Categorización del Sistema firmada por el RSEG.
- [ ] Análisis de Riesgos completo MAGERIT con riesgo residual aprobado por la dirección.
- [ ] Declaración de Aplicabilidad firmada por el RSEG con las 73 medidas.
- [ ] Plan de Adecuación vigente.
- [ ] Cuerpo normativo completo (**27 políticas E-100 a E-126**) firmado y difundido.
- [ ] Procedimientos operativos (**35 procedimientos E-200 a E-234**) con registros de los últimos 6 meses.
- [ ] Plan de Continuidad con BIA, BCP, DRP y informe de pruebas.
- [ ] Plan de Formación ejecutado con registros de asistencia y simulacros de phishing.
- [ ] Inventario de proveedores con cláusulas ENS/RGPD y evaluaciones.
- [ ] Informes de pentest interno y externo (Media+) o red team (Alta).
- [ ] Informe de auditoría interna previo a la externa.
- [ ] Revisión por la dirección anual.
- [ ] Memoria del estado de seguridad (formato INES).
- [ ] Evidencias técnicas vigentes para las 73 medidas aplicables.
- [ ] Registros de incidentes, cambios, vulnerabilidades, parches, accesos de los últimos 6 meses.
- [ ] Dossier final estructurado según la sección 2.15.
- [ ] Matriz cruzada del 99 (medida × evidencia × documento).

### 11.2 Integración con ENS Radar v2

ENS Radar v2 (sistema separado, ya en construcción) detecta empresas españolas que necesitan ENS porque están licitando con el sector público. Su output son leads cualificados con: empresa, CIF, organismo contratante, expediente, nivel ENS exigido, plazos del pliego, taller comercial recomendado, dossier de entrada.

**Endpoint de integración:** `POST /api/v1/leads/from-radar`

```json
{
  "lead_id_radar": "uuid",
  "empresa": {
    "nombre": "...",
    "cif": "...",
    "sector": "...",
    "tamano_estimado": "..."
  },
  "expediente": {
    "organismo_contratante": "...",
    "numero": "...",
    "objeto": "...",
    "importe": ...,
    "plazo_ejecucion": "..."
  },
  "ens_exigido": {
    "nivel": "MEDIO",
    "tipo_requisito": "solvencia_obligatoria",
    "fecha_limite": "..."
  },
  "taller_recomendado": "taller_2",
  "dossier_url": "https://radar.marcos.dev/dossiers/...",
  "fecha_deteccion": "..."
}
```

**Cuando llega un lead:**
1. La plataforma crea automáticamente un registro en `clients` (estado "lead").
2. Crea un proyecto pre-cargado con `categoria_objetivo` = nivel ENS exigido por el pliego.
3. Carga el dossier de entrada del Radar como contexto inicial.
4. Notifica a Marcos en el dashboard "nuevo lead caliente del Radar".
5. Si Marcos cierra el lead, el proyecto pasa a estado "activo" y arranca el pipeline de implantación.

ENS Radar caza, esta plataforma certifica. **Cero fricción entre los dos sistemas.**

---

## ANEXO — LO QUE NO HAY QUE OLVIDAR

- **El cliente no tiene cuenta. Solo magic links.** Esto es no-negociable. Cualquier intento de meter "una pequeña área de cliente" se gestiona como nuevo proyecto futuro (el add-on de monitoreo que Marcos ya tiene en mente).
- **Los motores deterministas son la columna vertebral.** El LLM es la capa de redacción y conversación. Las decisiones normativas no las toma el LLM.
- **El corpus oficial es la única fuente de verdad.** Si algo no está en el RD, las ITS, las CCN-STIC o los PCE, no se afirma.
- **Formato auditor español en todo.** Plantillas reconocibles, matriz cruzada, dossier estructurado. Si el auditor no lo reconoce, hemos fallado.
- **La plataforma cumple ENS Medio sobre sí misma.** Dogfooding obligatorio.
- **Pruebas mensuales de restauración** del propio backup de la plataforma.
- **Vigilancia normativa continua.** Cuando el CCN publica una nueva ITS o PCE, la plataforma lo detecta, ingesta y notifica a Marcos.
- **Logs criptográficamente inmutables** para todo lo que afecte a evidencias o decisiones del cliente.
- **Marcos es el único usuario humano.** La plataforma trabaja PARA Marcos, no para los clientes. Los clientes son objetos de servicio, no usuarios.

---

---

## APÉNDICE A — CATÁLOGO DE EVIDENCIAS POR CADA UNA DE LAS 73 MEDIDAS

Esta tabla es la columna vertebral del **Motor 7 — Evidence Collection Engine** y del **Motor 9 — Audit Preparation**. Para cada medida del Anexo II del RD 311/2022, se especifica: qué evidencia exacta pide el auditor, en qué formato, qué herramienta la genera, automatizable sí/no, frescura máxima admitida.

**Marcos: este apéndice se ingesta como JSON estructurado a la tabla `ens_evidence_catalog` durante la fase de construcción del corpus (semanas 3-5). Cada fila tiene: `measure_code`, `evidence_type`, `format`, `source_tool`, `automatable`, `max_age_days`, `audit_query` (la pregunta exacta que hace el auditor).**

### A.1 Marco Organizativo (org)

| Medida | Evidencia esperada por el auditor | Formato | Frescura | Auto |
|---|---|---|---|---|
| **org.1** Política de seguridad | Documento de Política firmado por el órgano superior + acta de aprobación + registro de difusión con acuse de recibo del personal | PDF firmado + XLSX registro | Revisión anual | Parcial |
| **org.2** Normativa de seguridad | Cuerpo normativo completo (políticas internas) firmado y vigente, listado maestro con versiones y fechas, evidencia de difusión | PDFs + XLSX maestro | Revisión anual | Sí |
| **org.3** Procedimientos de seguridad | Procedimientos operativos firmados + **registros de ejecución de los últimos 3-6 meses** (tickets, actas, logs) | PDFs + XLSX registros | Continuo | Sí |
| **org.4** Proceso de autorización | Procedimiento formal + actas de autorización (instalación, conexión, paso a producción, contratación, medios personales) de los últimos meses | PDF + actas firmadas | Continuo | Sí |

### A.2 Marco Operacional — Planificación (op.pl)

| Medida | Evidencia esperada | Formato | Frescura | Auto |
|---|---|---|---|---|
| **op.pl.1** Análisis de riesgos | AR completo MAGERIT con inventario de activos, amenazas, valoración, riesgo intrínseco/efectivo/residual, aprobación de la dirección. En Alta: PILAR exportado | XLSX + PDF + .mgr | Revisión anual | Sí (Motor 2) |
| **op.pl.2** Arquitectura de seguridad | Documento de arquitectura técnica con diagramas de red, zonas, flujos, controles. Diagrama de despliegue actualizado | PDF + Visio/Drawio | Cuando cambie | Parcial |
| **op.pl.3** Adquisición de nuevos componentes | Procedimiento de adquisición + registro de adquisiciones recientes con criterios de seguridad aplicados | PDF + XLSX | Continuo | Sí |
| **op.pl.4** Dimensionamiento / capacidad | Plan de capacidad documentado, métricas históricas de uso, proyecciones, alertas configuradas | PDF + capturas de monitorización | 6 meses | Sí |
| **op.pl.5** Componentes certificados | Listado de componentes en arquitectura con referencia al CPSTIC o certificación equivalente. Justificación si no hay producto CPSTIC disponible | XLSX | Revisión anual | Sí (cache CPSTIC) |

### A.3 Marco Operacional — Control de Acceso (op.acc)

| Medida | Evidencia esperada | Formato | Frescura | Auto |
|---|---|---|---|---|
| **op.acc.1** Identificación | Procedimiento de identificación + listado de usuarios con identificadores únicos, sin cuentas compartidas (justificación si las hay) | PDF + export del directorio | 30 días | Sí |
| **op.acc.2** Requisitos de acceso | Política de control de accesos + matriz de roles vs permisos + actas de aprobación de accesos por el propietario | PDF + XLSX matriz | Continuo | Sí |
| **op.acc.3** Segregación de funciones | Matriz SoD documentada con identificación de conflictos, controles compensatorios para los conflictos aceptados | XLSX + PDF | 6 meses | Parcial |
| **op.acc.4** Gestión de derechos de acceso | Registros de altas, bajas, cambios de rol de los últimos 6 meses + revisión periódica de accesos firmada | XLSX + actas firmadas | Continuo | Sí |
| **op.acc.5** Autenticación usuarios externos | Configuración del IdP para usuarios externos mostrando MFA habilitado, política de contraseñas, registro de excepciones | Capturas + export + PDF | 30 días | Sí |
| **op.acc.6** Autenticación usuarios organización | Configuración del IdP corporativo con MFA enforcement, % de usuarios con MFA activo, política de contraseñas, justificación de R1 si aplica | Capturas + export + PDF | 30 días | Sí |

### A.4 Marco Operacional — Explotación (op.exp)

| Medida | Evidencia esperada | Formato | Frescura | Auto |
|---|---|---|---|---|
| **op.exp.1** Inventario de activos | Inventario completo y actualizado de activos (hardware, software, datos, servicios) con propietario y criticidad | XLSX/CMDB export | 30 días | Sí (discovery) |
| **op.exp.2** Configuración de seguridad | Líneas base de configuración (Windows, Linux, red, BBDD) documentadas + informes CLARA / CIS-CAT mostrando cumplimiento | PDF + XML CLARA | 90 días | Sí (CLARA, Lynis) |
| **op.exp.3** Gestión de la configuración | Procedimiento + herramienta de gestión de configuración (Ansible, Puppet) con registros de cambios | PDF + logs | Continuo | Sí |
| **op.exp.4** Mantenimiento y parches | Informe del gestor de parches con SLA de aplicación, cobertura, parches críticos pendientes y excepciones | PDF + XLSX | 30 días | Sí |
| **op.exp.5** Gestión de cambios | Registro de cambios técnicos de los últimos 6 meses con aprobación CAB, ejecución, validación y rollback | XLSX/Jira export | Continuo | Sí |
| **op.exp.6** Protección frente a código dañino | Consola del EDR mostrando cobertura 100% endpoints, política activa, alertas tratadas, exclusiones documentadas | Capturas + export | 30 días | Sí |
| **op.exp.7** Gestión de incidentes | Registro de incidentes de los últimos 6 meses con clasificación, respuesta, cierre, lecciones aprendidas. Notificaciones a LUCIA si aplican | XLSX + IDs LUCIA | Continuo | Sí |
| **op.exp.8** Registro de actividad | Configuración del SIEM con políticas de retención, ejemplo de búsqueda, evidencia de integridad de logs | Capturas + config | 30 días | Sí |
| **op.exp.9** Registro de gestión de incidentes | Histórico completo de incidentes con timeline, acciones, responsables, cierre | XLSX | Continuo | Sí |
| **op.exp.10** Protección de registros | Configuración mostrando logs en almacenamiento WORM o equivalente, control de acceso a logs, integridad criptográfica | Capturas + config | 90 días | Sí |

### A.5 Marco Operacional — Servicios Externos (op.ext)

| Medida | Evidencia esperada | Formato | Frescura | Auto |
|---|---|---|---|---|
| **op.ext.1** Contratación y SLAs | Inventario de proveedores con contratos, cláusulas ENS/RGPD art. 28, SLAs definidos, acuerdos firmados | XLSX + PDFs contratos | Revisión anual | Parcial |
| **op.ext.2** Gestión diaria | Registros de gestión de servicios externos: tickets, incidencias, cumplimiento de SLA, reuniones de seguimiento | XLSX + actas | Continuo | Sí |
| **op.ext.3** Cadena de suministro | Análisis de criticidad de la cadena de suministro, evaluaciones de proveedores T1/T2, plan de continuidad ante fallo de proveedor | PDF + XLSX | Revisión anual | Parcial |
| **op.ext.4** Interconexión de sistemas | Inventario de interconexiones con sistemas externos, controles aplicados en cada una, autorizaciones formales | XLSX + diagramas | 6 meses | Sí |

### A.6 Marco Operacional — Servicios en la Nube (op.nub)

| Medida | Evidencia esperada | Formato | Frescura | Auto |
|---|---|---|---|---|
| **op.nub.1** Protección de servicios en la nube | Inventario cloud (AWS/Azure/GCP/M365), informe Prowler con perfil ENS, configuración de IAM cloud, logging de control plane, regiones permitidas | PDF Prowler + capturas | 30 días | Sí (Prowler) |

### A.7 Marco Operacional — Continuidad (op.cont)

| Medida | Evidencia esperada | Formato | Frescura | Auto |
|---|---|---|---|---|
| **op.cont.1** Análisis de impacto | BIA con identificación de procesos críticos, RTO/RPO, dependencias, impacto temporal | PDF + XLSX | Revisión anual | Parcial |
| **op.cont.2** Plan de continuidad | BCP completo con escenarios, equipos, procedimientos de activación, comunicación de crisis | PDF | Revisión anual | No |
| **op.cont.3** Pruebas periódicas | Informe de la última prueba de restauración / DR firmada, con resultados, hallazgos y mejoras | PDF firmado | Anual (M), semestral (A) | Parcial |
| **op.cont.4** Medios alternativos | Inventario de medios alternativos (sitio DR, cloud, contratos), configuración, prueba de conmutación | PDF + capturas | Anual | Parcial |

### A.8 Marco Operacional — Monitorización (op.mon)

| Medida | Evidencia esperada | Formato | Frescura | Auto |
|---|---|---|---|---|
| **op.mon.1** Detección de intrusión | Configuración IDS/IPS o EDR con detección activa, ejemplos de alertas tratadas, cobertura | Capturas + logs | 30 días | Sí |
| **op.mon.2** Sistema de métricas | Cuadro de mando de métricas de seguridad según CCN-STIC 815, evolución temporal, KPIs | PDF + capturas dashboard | 30 días | Sí |
| **op.mon.3** Vigilancia | Suscripción a feeds CCN-CERT, registro de boletines tratados, threat intelligence aplicado | Capturas + XLSX | Continuo | Sí |

### A.9 Medidas de Protección — Instalaciones (mp.if)

| Medida | Evidencia esperada | Formato | Frescura | Auto |
|---|---|---|---|---|
| **mp.if.1** Áreas separadas con control acceso | Plano del CPD/oficina con zonificación, registro de accesos físicos, fotos del control de acceso | PDF + plano + fotos | 6 meses | Parcial |
| **mp.if.2** Identificación de personas | Procedimiento + registro de visitas con identificación, registro de tarjetas de acceso | PDF + XLSX | Continuo | Sí |
| **mp.if.3** Acondicionamiento de locales | Documentación de climatización, suministro eléctrico, condiciones ambientales del CPD | PDF + capturas monitorización | Anual | Parcial |
| **mp.if.4** Energía eléctrica | Documentación SAI, grupo electrógeno, pruebas periódicas, mantenimientos | PDF + actas mantenimiento | 6 meses | Parcial |
| **mp.if.5** Protección incendios | Plan contra incendios, sistemas instalados, pruebas, certificaciones | PDF + certificados | Anual | No |
| **mp.if.6** Protección inundaciones | Análisis de riesgo de inundación, medidas implantadas o justificación de no aplicabilidad | PDF | Anual | No |
| **mp.if.7** Registro entrada/salida equipamiento | Registro de movimientos de equipamiento dentro/fuera de la organización | XLSX | Continuo | Sí |

### A.10 Medidas de Protección — Personal (mp.per)

| Medida | Evidencia esperada | Formato | Frescura | Auto |
|---|---|---|---|---|
| **mp.per.1** Caracterización del puesto | Descripción de puestos con responsabilidades de seguridad, perfil técnico requerido | PDF/XLSX | Cuando cambien | No |
| **mp.per.2** Deberes y obligaciones | NDAs firmados por todo el personal, código de conducta, política de uso aceptable acusada | XLSX + PDFs | Continuo | Sí |
| **mp.per.3** Concienciación | Plan de concienciación ejecutado, materiales, asistencia, simulacros de phishing con resultados | PDF + XLSX | Continuo | Sí (GoPhish) |
| **mp.per.4** Formación | Plan de formación específico por rol, registros de asistencia, evaluaciones aprobadas | XLSX | Anual | Sí |

### A.11 Medidas de Protección — Equipos (mp.eq)

| Medida | Evidencia esperada | Formato | Frescura | Auto |
|---|---|---|---|---|
| **mp.eq.1** Mesa limpia | Política de mesa limpia firmada, walkthrough con fotos de oficina, registro de incidencias | PDF + fotos | Anual | No |
| **mp.eq.2** Bloqueo de puesto | Configuración GPO mostrando bloqueo automático tras inactividad, política activa | Capturas | 90 días | Sí |
| **mp.eq.3** Protección equipos portátiles | Listado de portátiles con cifrado activo (BitLocker/FileVault), MDM, políticas aplicadas | XLSX + capturas | 30 días | Sí |
| **mp.eq.4** Otros dispositivos conectados | Inventario de IoT/OT/dispositivos no estándar con controles aplicados | XLSX | 90 días | Parcial |

### A.12 Medidas de Protección — Comunicaciones (mp.com)

| Medida | Evidencia esperada | Formato | Frescura | Auto |
|---|---|---|---|---|
| **mp.com.1** Perímetro seguro | Configuración de firewall perimetral, reglas, segmentación, revisiones periódicas | Export config + XLSX | 90 días | Sí |
| **mp.com.2** Confidencialidad comunicaciones | Export TLS de servicios expuestos, informe SSL Labs A/A+, listado de servicios con TLS 1.3 | PDF SSL Labs + XLSX | 30 días | Sí (testssl) |
| **mp.com.3** Integridad y autenticidad | Configuración DNSSEC, SPF/DKIM/DMARC del correo, firmas de comunicaciones críticas | Capturas + DNS exports | 30 días | Sí |
| **mp.com.4** Separación de flujos | Diagrama de segmentación de red, VLANs, microsegmentación si aplica, controles entre zonas | PDF + diagramas | 6 meses | Parcial |

### A.13 Medidas de Protección — Soportes (mp.si)

| Medida | Evidencia esperada | Formato | Frescura | Auto |
|---|---|---|---|---|
| **mp.si.1** Marcado de soportes | Procedimiento + ejemplos de soportes marcados, política de etiquetado | PDF + fotos | Anual | No |
| **mp.si.2** Criptografía | Inventario de soportes cifrados (USB, discos externos), política de claves | XLSX + PDF | 6 meses | Parcial |
| **mp.si.3** Custodia | Procedimiento + registro de custodia de soportes sensibles | PDF + XLSX | Continuo | Sí |
| **mp.si.4** Transporte | Procedimiento + registros de transporte de soportes con cadena de custodia | PDF + XLSX | Continuo | Sí |
| **mp.si.5** Borrado y destrucción | Política + certificados de destrucción de soportes, registros de borrado seguro | PDF + certificados | Continuo | Sí |

### A.14 Medidas de Protección — Software (mp.sw)

| Medida | Evidencia esperada | Formato | Frescura | Auto |
|---|---|---|---|---|
| **mp.sw.1** Desarrollo de aplicaciones | Política SSDLC, integración SAST/SCA en CI/CD, code review, threat modeling (Alta) | PDF + capturas pipeline | 90 días | Sí (Semgrep, Trivy) |
| **mp.sw.2** Aceptación y puesta en servicio | Procedimiento de aceptación, criterios de seguridad, evidencias de pruebas pre-producción | PDF + actas | Continuo | Parcial |

### A.15 Medidas de Protección — Información (mp.info)

| Medida | Evidencia esperada | Formato | Frescura | Auto |
|---|---|---|---|---|
| **mp.info.1** Datos de carácter personal | RAT actualizado, bases legales, EIPDs, contratos art. 28, política de privacidad publicada | PDF + XLSX | Revisión anual | Parcial |
| **mp.info.2** Calificación de la información | Política de clasificación + ejemplos de información clasificada con marcado | PDF + ejemplos | Anual | No |
| **mp.info.3** Cifrado | Listado de bases de datos cifradas en reposo, BitLocker en endpoints, configuración KMS/HSM | XLSX + capturas | 30 días | Sí |
| **mp.info.4** Firma electrónica | Política de firma + ejemplos de uso, certificados utilizados, validez | PDF + certificados | 6 meses | Parcial |
| **mp.info.5** Sellos de tiempo | Configuración del proveedor de sellado, ejemplos de uso en documentos críticos | PDF + ejemplos | 6 meses | Sí |
| **mp.info.6** Limpieza de documentos | Procedimiento de limpieza de metadatos, herramienta utilizada, ejemplos | PDF + ejemplos | Anual | Sí |

### A.16 Medidas de Protección — Servicios (mp.s)

| Medida | Evidencia esperada | Formato | Frescura | Auto |
|---|---|---|---|---|
| **mp.s.1** Protección del correo | Configuración antispam, antimalware del correo, SPF/DKIM/DMARC, formación específica | Capturas + DNS | 90 días | Sí |
| **mp.s.2** Protección web | WAF activo (en M+), pentest web reciente, configuración HTTPS, headers de seguridad | PDF informe + capturas | 90 días | Sí (ZAP, Nuclei) |
| **mp.s.3** Protección anti-DDoS | Configuración anti-DDoS (CDN, scrubbing), pruebas de carga, plan de respuesta | PDF + capturas | Anual | Parcial |
| **mp.s.4** Otros servicios | Documentación de protección de otros servicios críticos con controles aplicados | PDF | 6 meses | Parcial |

**Total entradas del catálogo: 73 medidas × N evidencias por medida ≈ 200+ entradas concretas auditables.**

Cada entrada se genera como instancia en `evidence_catalog_templates` durante las semanas 3-5 del plan, y a partir de ahí el Motor 7 sabe automáticamente qué pedirle al cliente para cada control en estado "esperando evidencia".

---

## APÉNDICE B — BIBLIOTECA DE OBLIGACIONES (Motor 5)

Esta es la biblioteca anti-alucinación del **Motor 5 — Obligations & Planning**. Cada entrada es una plantilla de obligación inmutable. Cuando se detecta un gap en una medida del Anexo II, el motor instancia las obligaciones aplicables con el contexto del cliente. **El LLM no inventa obligaciones, solo personaliza las plantillas.**

**Estructura JSON de cada plantilla:**

```json
{
  "id": "OBL-{medida}-{seq}",
  "medida_ens": "op.acc.6",
  "categoria_aplicable": ["MEDIA", "ALTA"],
  "refuerzos_relacionados": ["R1", "R2"],
  "titulo": "...",
  "descripcion_template": "...",
  "entregable_tipo": "documento|configuracion|accion_tecnica|formacion|contrato",
  "entregable_template_id": "DOCX-XXX | CFG-XXX | ACT-XXX",
  "modo_ejecucion": "consultor_genera | cliente_aporta_evidencia | accion_tecnica_remota | accion_manual_cliente",
  "magic_link_template": "firma_documento | aporte_evidencia | autorizacion_accion",
  "esfuerzo_horas_estimado": 4,
  "dependencias": ["OBL-XXX-YY"],
  "criterios_aceptacion": ["...", "...", "..."],
  "validacion_automatica": "regla determinista verificable",
  "fuente_normativa": ["RD 311/2022 Anexo II op.acc.6", "CCN-STIC 808 §X.Y"]
}
```

**Ejemplos representativos por familia (la biblioteca completa tiene ~250 plantillas, una a varias por medida):**

### B.1 Marco Organizativo

```
OBL-org.1-001  Aprobar y publicar Política de Seguridad
OBL-org.1-002  Difundir Política con acuse de recibo del personal
OBL-org.1-003  Programar revisión anual de la Política
OBL-org.2-001  Generar cuerpo normativo completo (políticas)
OBL-org.2-002  Aprobación formal del cuerpo normativo por el Comité
OBL-org.3-001  Generar procedimientos operativos según categoría
OBL-org.3-002  Iniciar operación efectiva de procedimientos (registros)
OBL-org.4-001  Implantar proceso formal de autorización con CAB
OBL-org.4-002  Generar acta inicial del Comité con autorizaciones pendientes
```

### B.2 Control de acceso (op.acc) — el bloque más crítico

```
OBL-op.acc.1-001  Implantar identificadores únicos por usuario
OBL-op.acc.1-002  Eliminar cuentas compartidas o documentar excepciones
OBL-op.acc.4-001  Limpieza de cuentas inactivas (>90 días)
OBL-op.acc.4-002  Procedimiento de altas/bajas/cambios automatizado
OBL-op.acc.4-003  Revisión periódica de accesos firmada por managers
OBL-op.acc.5-001  Configurar MFA para usuarios externos en el IdP
OBL-op.acc.5-002  Aportar evidencia de configuración MFA externos
OBL-op.acc.6-001  Habilitar MFA universal usuarios organización en IdP
OBL-op.acc.6-002  Reforzar política de contraseñas (longitud, complejidad, rotación)
OBL-op.acc.6-003  Documentar excepciones R1 (zonas controladas)
OBL-op.acc.6-004  Aportar evidencia de cobertura MFA >= 95%
```

### B.3 Explotación (op.exp)

```
OBL-op.exp.1-001  Generar inventario completo de activos
OBL-op.exp.1-002  Implantar herramienta de descubrimiento continuo
OBL-op.exp.2-001  Aplicar líneas base de bastionado (CCN-STIC 521/522/570)
OBL-op.exp.2-002  Ejecutar CLARA y aportar resultado
OBL-op.exp.4-001  Implantar gestión de parches con SLA
OBL-op.exp.4-002  Aportar evidencia de SLA cumplido (último mes)
OBL-op.exp.5-001  Implantar CAB y procedimiento formal de cambios
OBL-op.exp.6-001  Desplegar EDR moderno con cobertura 100%
OBL-op.exp.7-001  Implantar procedimiento de gestión de incidentes
OBL-op.exp.7-002  Configurar notificación automática a LUCIA
OBL-op.exp.8-001  Centralizar logs en SIEM con retención correcta
OBL-op.exp.10-001  Configurar almacenamiento WORM o equivalente para logs
```

### B.4 Servicios externos (op.ext)

```
OBL-op.ext.1-001  Inventariar todos los proveedores en alcance
OBL-op.ext.1-002  Renegociar contratos con cláusulas ENS/RGPD art. 28
OBL-op.ext.3-001  Evaluar criticidad de cadena de suministro
OBL-op.ext.4-001  Inventariar interconexiones y aplicar controles
```

### B.5 Cloud (op.nub)

```
OBL-op.nub.1-001  Ejecutar Prowler con perfil ENS contra cloud
OBL-op.nub.1-002  Remediar findings críticos del Prowler
OBL-op.nub.1-003  Configurar logging de control plane (CloudTrail/Activity Log)
OBL-op.nub.1-004  Verificar que datos están en regiones permitidas
OBL-op.nub.1-005  Implantar BYOK/HYOK (en Alta)
```

### B.6 Continuidad (op.cont)

```
OBL-op.cont.1-001  Realizar BIA formal con RTO/RPO por proceso
OBL-op.cont.2-001  Generar BCP completo
OBL-op.cont.3-001  Ejecutar prueba de restauración y documentar
OBL-op.cont.3-002  Ejecutar prueba de DR (Media+) y documentar
OBL-op.cont.4-001  Configurar sitio alternativo (Alta)
```

### B.7 Comunicaciones (mp.com)

```
OBL-mp.com.1-001  Revisar y endurecer reglas de firewall perimetral
OBL-mp.com.2-001  Forzar TLS 1.3 en servicios expuestos
OBL-mp.com.2-002  Aportar informe SSL Labs A/A+
OBL-mp.com.3-001  Configurar SPF/DKIM/DMARC del dominio
OBL-mp.com.3-002  Activar DNSSEC
OBL-mp.com.4-001  Segmentar red en VLANs según zonas
```

### B.8 Información (mp.info)

```
OBL-mp.info.1-001  Actualizar RAT (Registro de Actividades de Tratamiento)
OBL-mp.info.1-002  Revisar contratos con encargados (RGPD art. 28)
OBL-mp.info.1-003  Actualizar política de privacidad pública
OBL-mp.info.3-001  Cifrar bases de datos en reposo
OBL-mp.info.3-002  Cifrar discos en endpoints (BitLocker/FileVault)
OBL-mp.info.3-003  Implantar gestión de claves con KMS
```

### B.9 Servicios web (mp.s)

```
OBL-mp.s.1-001  Configurar antispam y antimalware del correo
OBL-mp.s.2-001  Desplegar WAF (Media+)
OBL-mp.s.2-002  Ejecutar pentest web y aportar informe
OBL-mp.s.2-003  Configurar headers de seguridad (CSP, HSTS, X-Frame-Options)
OBL-mp.s.3-001  Configurar protección anti-DDoS
```

**Modos de ejecución detallados (esto es el corazón anti-fricción para el cliente):**

#### Modo 1: `consultor_genera` (el más usado)
Marcos pulsa "Generar" → la plataforma genera el entregable con Document Factory → Marcos revisa → envía al cliente vía magic link de tipo `firma_documento` → el cliente lo lee, opcionalmente lo discute en chat con Marcos, y firma electrónicamente. El entregable queda registrado en el dossier. **Esfuerzo del cliente: 5-15 minutos por documento. Esfuerzo de Marcos: 10-30 minutos de revisión.**

#### Modo 2: `cliente_aporta_evidencia`
La plataforma genera magic link tipo `aporte_evidencia` con instrucciones ultra-concretas: *"Acceda a https://portal.azure.com → Microsoft Entra ID → Properties → Security defaults → Manage. Realice una captura de pantalla mostrando que Security defaults o Conditional Access están activos. Suba la captura aquí."* El cliente sube → la plataforma valida formato → registra como evidencia. **Esfuerzo del cliente: 2-5 minutos por evidencia.**

#### Modo 3: `accion_tecnica_remota_autorizada`
La plataforma genera magic link tipo `autorizacion_accion` con un texto muy específico: *"Marcos solicita autorización para ejecutar lectura de la configuración de tu firewall durante 2 horas, sólo lectura, sin modificaciones, propósito: recolección de evidencia para op.acc.2 del ENS. Si autorizas, pega el siguiente comando en un terminal con acceso a tu firewall: `<comando one-liner que la plataforma genera>`. Cuando termines, pulsa 'He ejecutado'."* El cliente lo ejecuta → la salida del comando se sube al magic link → la plataforma la procesa como evidencia. **Cero credenciales viajan. Cero acceso permanente. Solo el output que el cliente decide aportar.**

#### Modo 4: `accion_manual_cliente`
Para cosas que solo puede hacer un técnico del cliente. La plataforma genera instrucciones paso a paso, el cliente las ejecuta, sube captura de validación. *"Para cumplir mp.com.2, configure el siguiente registro DNS TXT en su dominio: `_dmarc.empresa.com TXT v=DMARC1; p=reject; rua=mailto:dmarc@empresa.com`. Tras hacerlo, ejecute `dig _dmarc.empresa.com TXT` y pegue el resultado aquí."*

**Validación automática de obligaciones:** muchas obligaciones tienen reglas deterministas verificables. Cuando la evidencia se aporta, la plataforma intenta validarla automáticamente:

- Si la obligación es "habilitar TLS 1.3", la plataforma corre `testssl.sh` o `ssl-labs-scan` contra el endpoint y verifica.
- Si es "configurar DMARC", hace `dig` y verifica.
- Si es "habilitar MFA universal", parsea el export del IdP y cuenta.
- Si es "rotar claves", verifica las fechas de creación.

Si la validación pasa, la obligación se cierra automáticamente. Si falla, se le notifica al cliente con el motivo concreto vía nuevo magic link.

---

## APÉNDICE C — PROMPTS BASE DE LOS 16 AGENTES IA

Este apéndice contiene los **system prompts base de los 16 agentes originales** del **Motor 11** y la **Parte 6** (agentes 1-16). Son inmutables y forman parte del control anti-alucinación. Marcos NO los modifica salvo refinamiento explícito. **Los 10 agentes nuevos añadidos en v2.0 (agentes 17-26) siguen el mismo patrón de prompt base** y se desarrollarán completamente en una iteración posterior v2.1; su lógica operativa ya está descrita en el cuerpo del documento (Parte 3 y tabla de Parte 6).

**Cabecera común para todos los agentes:**

```
Eres un agente de la plataforma ENS de Marcos, un consultor autónomo español especializado en el Esquema Nacional de Seguridad (RD 311/2022). Trabajas exclusivamente en español. Tu fuente única de verdad es el corpus oficial: RD 311/2022, Instrucciones Técnicas de Seguridad publicadas por el CCN, guías CCN-STIC serie 800, Perfiles de Cumplimiento Específico, y el contexto del proyecto activo.

REGLAS NO NEGOCIABLES:
1. JAMÁS inventes información normativa. Si no encuentras algo en el corpus o en el contexto, responde literalmente "No encontrado en el corpus oficial".
2. CITA OBLIGATORIA: cada afirmación normativa debe ir acompañada de su fuente exacta en formato [RD 311/2022 Art. X], [CCN-STIC NNN §X.Y], [Anexo II medida.código].
3. JAMÁS tomes decisiones que afectan a la DdA, la categorización o al riesgo residual. Esas las toman los motores deterministas. Tu papel es redactar, sugerir y explicar, no decidir.
4. Si detectas contradicciones entre lo que el usuario te dice y lo que dice el corpus, señálalo explícitamente.
5. Temperatura objetivo: 0.1-0.2. Deterministico antes que creativo.
```

### C.1 Agente 1 — Parser Normativo

```
ROL: Ingestar documentos normativos oficiales (RD, ITS, CCN-STIC, PCE) al grafo de conocimiento y al vector store.

INPUT: PDF/HTML del documento normativo + metadata (fuente, versión, fecha).

OUTPUT: 
- Extracción de entidades estructuradas (artículos, medidas, refuerzos, dimensiones).
- Tripletas para Apache AGE.
- Chunks para pgvector con metadatos.
- Relaciones cruzadas con otras normas.

REGLAS ESPECÍFICAS:
- No reformules el texto del corpus. Conserva el texto original literal en los chunks.
- Identifica TODAS las referencias cruzadas internas y externas.
- Si una sección es ambigua, márcala con flag {"ambiguous": true} en lugar de interpretarla.

MODELO: Sonnet 4.5
```

### C.2 Agente 2 — Analizador de Pliegos de Licitación

```
ROL: Analizar pliegos de contratación pública subidos por Marcos para extraer requisitos ENS.

INPUT: PDF del pliego (PCAP/PPT) + metadata del expediente.

OUTPUT JSON:
{
  "ens_exigido": true/false,
  "categoria_minima": "BASICA|MEDIA|ALTA|null",
  "tipo_requisito": "solvencia_obligatoria|mejora_valorable|criterio_adjudicacion",
  "fragmentos_relevantes": [{"pagina": N, "texto": "...", "interpretacion": "..."}],
  "plazos_clave": [{"hito": "...", "fecha": "..."}],
  "obligaciones_especificas_pliego": ["..."],
  "confianza": 0.0-1.0
}

REGLAS:
- Cita textual obligatoria de cada fragmento que justifique la conclusión.
- Si confianza < 0.7, marcar para revisión manual de Marcos.
- No inferir requisitos que no estén explícitos en el pliego.

MODELO: Sonnet 4.5
```

### C.3 Agente 3 — Scoping y Categorización Asistida

```
ROL: Guiar a Marcos en la entrevista de scoping con el cliente para recoger los datos necesarios para la categorización.

INPUT: Conversación con Marcos sobre el cliente.

OUTPUT: Preguntas estructuradas, captura de respuestas, propuesta de valoración por dimensión.

REGLAS:
- La DECISIÓN final de categoría la toma el Motor 1 (determinista). Tú solo recoges datos.
- Pregunta una dimensión a la vez para evitar confusión.
- Si Marcos no sabe responder, propón ejemplos del sector del cliente para ayudar.
- Nunca afirmes "esto es categoría Media", solo "según los datos recogidos, el motor calculará la categoría".

MODELO: Sonnet 4.5
```

### C.4 Agente 4 — Redactor de Políticas y Procedimientos

```
ROL: Rellenar plantillas DOCX validadas con el contexto del cliente.

INPUT: ID de plantilla + contexto del proyecto (cliente, sistema, roles, etc.) + parámetros específicos.

OUTPUT: DOCX con los huecos personalizados rellenos.

REGLAS CRÍTICAS:
- NUNCA modifiques las partes regulatorias de la plantilla (texto legal, citas, descripciones de medidas).
- Solo rellenas los campos Jinja2 marcados como personalizables.
- Si un campo personalizable requiere información que no tienes en el contexto, marca {{TODO: pedir a Marcos}} en lugar de inventar.
- Usa lenguaje formal castellano técnico-jurídico.
- Adapta el tono al sector del cliente (sanidad, legal, industrial...) sin cambiar el fondo.

MODELO: Opus 4 (calidad alta) o Sonnet 4.5 (volumen)
```

### C.5 Agente 5 — Analista MAGERIT

```
ROL: Asistir en el análisis de riesgos MAGERIT v3 sobre el modelo del Motor 2.

INPUT: Inventario de activos del cliente + sector + contexto.

OUTPUT: 
- Sugerencias de amenazas aplicables por activo (del catálogo MAGERIT).
- Sugerencias de probabilidad e impacto basadas en el sector.
- Justificación de cada sugerencia.

REGLAS:
- TODOS los cálculos numéricos los hace el Motor 2 determinista. Tú solo sugieres valores cualitativos.
- Cita el catálogo MAGERIT v3 oficial en cada sugerencia.
- Si no hay precedente claro en el sector, marca como "requiere validación de Marcos".

MODELO: Opus 4
```

### C.6 Agente 6 — Analista de Contratos

```
ROL: Analizar contratos de proveedores del cliente para detectar cláusulas faltantes ENS/RGPD.

INPUT: PDF del contrato.

OUTPUT JSON:
{
  "tipo_contrato": "...",
  "encargado_tratamiento": true/false,
  "clausulas_presentes": ["..."],
  "clausulas_faltantes_criticas": [
    {"clausula": "art. 28 RGPD", "impacto": "...", "redaccion_propuesta": "..."}
  ],
  "sla_definidos": true/false,
  "derecho_auditoria": true/false,
  "notificacion_incidentes": true/false,
  "recomendaciones": ["..."]
}

REGLAS:
- No propongas redacciones legales sin grounding en plantillas validadas.
- Marca con confianza baja cualquier cláusula ambigua.
- Si el contrato está en otro idioma, indícalo y no traduzcas tú.

MODELO: Sonnet 4.5
```

### C.7 Agente 7 — Gap Analyzer con Priorización

```
ROL: Tomar la lista de gaps generada por el Motor 4 determinista y priorizarla en función del contexto del cliente.

INPUT: Lista de gaps del Motor 4 + contexto del cliente.

OUTPUT: Lista de gaps reordenada con criterio de priorización explícito.

REGLAS:
- NO añadas ni quites gaps. Solo reordenas y agrupas.
- Aplica reglas deterministas primero (gaps en op.acc.6, mp.info.3, op.exp.7 → siempre crítico).
- Después contextualiza por sector (cliente sanidad → priorizar mp.info.1).
- Marca quick wins (esfuerzo < 4h, impacto alto) para destacarlos.

MODELO: Sonnet 4.5
```

### C.8 Agente 8 — Planificador de Obligaciones

```
ROL: Tomar gaps priorizados y mapearlos a obligaciones de la biblioteca del Motor 5.

INPUT: Gap específico + contexto del cliente.

OUTPUT: Lista de obligaciones instanciadas con personalización de textos.

REGLAS CRÍTICAS:
- Las obligaciones vienen EXCLUSIVAMENTE de la biblioteca de plantillas. Jamás inventes una obligación nueva.
- Solo personalizas los campos `descripcion_template` y `criterios_aceptacion` con los datos del cliente.
- Validación cruzada: cada obligación generada debe pasar el check del grafo (¿la medida existe? ¿el refuerzo aplica a la categoría del proyecto?).
- Si no hay plantilla en la biblioteca para un gap, marca "GAP_NO_CUBIERTO_POR_BIBLIOTECA" y notifica a Marcos para que cree la plantilla.

MODELO: Sonnet 4.5
```

### C.9 Agente 9 — Orquestador de Pentest

```
ROL: Interpretar resultados crudos de las herramientas open source del Motor 8 y consolidarlos.

INPUT: Outputs raw de Nmap/Nuclei/OpenVAS/ZAP/Prowler/etc.

OUTPUT: Lista normalizada de findings con: severidad, descripción técnica, activo afectado, evidencia, mapeo a medida ENS, mapeo a MITRE ATT&CK, recomendación.

REGLAS NO NEGOCIABLES:
- JAMÁS inventes hallazgos. Cada finding debe estar respaldado por output raw de una herramienta real.
- Si una herramienta da un falso positivo evidente (ej. CVE en versión que ya está parcheada según otra fuente), márcalo y propón verificación, no lo descartes.
- El mapeo a medida ENS debe ser justificable. Si no hay mapeo claro, marca "REQUIERE_REVISION".
- El LLM no decide la severidad final. Usa la severidad CVSS de la herramienta.

MODELO: Opus 4
```

### C.10 Agente 10 — Redactor de Informes de Pentest

```
ROL: Redactar el informe de pentest en formato auditor español a partir de los findings consolidados.

INPUT: Lista de findings consolidados por el Agente 9 + metadata del pentest.

OUTPUT: DOCX completo siguiendo la estructura de la sección 8.6.

REGLAS:
- Cada afirmación del informe debe estar vinculada a un finding con ID. Si no hay finding, no hay afirmación.
- El resumen ejecutivo es para directivos, lenguaje no técnico, máximo 1 página.
- El detalle técnico es para auditor, con evidencias, payloads y comandos.
- Tono profesional formal. Usa vocabulario reconocible por auditores ENAC españoles.
- Incluye SIEMPRE: alcance autorizado, ventana temporal, herramientas usadas con versiones.

MODELO: Opus 4
```

### C.11 Agente 11 — Auditor Interno Virtual

```
ROL: Hacer pasar al sistema una auditoría interna simulada con la profundidad de un auditor ENAC real.

INPUT: Proyecto activo con su DdA, evidencias, documentos.

OUTPUT: Informe de auditoría interna estilo ENAC con hallazgos clasificados (NC mayor, NC menor, observación, oportunidad).

REGLAS:
- Para cada una de las 73 medidas aplicables, formula la pregunta tipo auditor.
- Busca la evidencia en el Evidence Vault.
- Aplica el checklist de la CCN-STIC 808 con grados de madurez L0-L5 (L0 inexistente, L1 inicial, L2 reproducible, L3 definido, L4 gestionado, L5 optimizado). Los mínimos exigidos son: L1-L2 en Básica, L3 en Media, L3-L4 en Alta. Los requisitos marcados en gris en la CCN-STIC 808 son **nucleares** y deben evaluarse SIEMPRE sin excepción.
- Si la evidencia existe pero está caducada, NC menor.
- Si la evidencia no existe, NC mayor.
- Si hay contradicción entre documentos y evidencia, NC mayor con detalle de la contradicción.
- Sé estricto. Mejor que falle aquí que en la auditoría real.

MODELO: Opus 4
```

### C.12 Agente 12 — Coach del Cliente

```
ROL: Generar preguntas tipo auditor por rol (CTO, admin, RRHH, dirección, DPO) para que el personal del cliente practique antes de la auditoría real.

INPUT: Rol del personal + medidas aplicables al proyecto.

OUTPUT: Lista de preguntas con respuestas modelo y rúbrica de evaluación.

REGLAS:
- Las preguntas son las que un auditor ENAC veterano realmente hace.
- Las respuestas modelo son lo que el auditor espera oír (no recetas para mentir).
- La rúbrica evalúa: completitud, exactitud, capacidad de mostrar evidencia.
- Cubrir las medidas más probables de ser preguntadas en cada rol.

MODELO: Sonnet 4.5
```

### C.13 Agente 13 — Generador de Dossier Final

```
ROL: Compilar el dossier final al auditor según la estructura exacta de la sección 2.15.

INPUT: Proyecto completo en estado "listo para auditoría".

OUTPUT: ZIP estructurado + PDF maestro navegable + matriz cruzada del 99.

REGLAS:
- Verifica QUE TODOS los entregables E-XXX exigidos por la categoría están presentes.
- Verifica que las evidencias están vigentes (no caducadas).
- Verifica que los registros de operación cubren los últimos 6 meses.
- Si falta cualquier cosa, NO genera el dossier y produce un informe de bloqueo con la lista de faltantes.
- La matriz cruzada debe tener una fila por cada una de las 73 medidas aplicables, con hipervínculos a las evidencias.

MODELO: Sonnet 4.5
```

### C.14 Agente 14 — Copiloto ENS Conversacional

```
ROL: Asistir a Marcos en cualquier pregunta sobre ENS, sobre el cliente activo o sobre el proyecto.

INPUT: Pregunta de Marcos en lenguaje natural + contexto del proyecto seleccionado.

OUTPUT: Respuesta en lenguaje natural con citas obligatorias.

REGLAS:
- RAG obligatorio sobre el corpus ENS.
- Citas obligatorias en cada afirmación normativa.
- Si Marcos pregunta algo que requiere acción (generar documento, lanzar pentest), no lo ejecutes tú: indícale qué motor usar y propónle el botón.
- Si Marcos pregunta algo del proyecto, consulta los motores deterministas antes de responder.
- Modo "no encontrado" preferible a inventar.
- Tono cercano pero profesional. Marcos sabe poco de ENS, explícale como a un colega listo que está aprendiendo.

MODELO: Sonnet 4.5 por defecto, Opus 4 si la pregunta es compleja
```

### C.15 Agente 15 — Vigilancia Normativa

```
ROL: Detectar cambios en el corpus normativo ENS y notificarlos a Marcos.

INPUT: Crawl periódico (cada 24h) de https://ens.ccn.cni.es/, https://www.ccn-cert.cni.es/, BOE.

OUTPUT: 
- Lista de cambios detectados (nuevas guías, modificaciones, derogaciones).
- Análisis de impacto en proyectos activos.
- Notificación a Marcos en el dashboard.

REGLAS:
- Solo DETECTA cambios. No interpreta.
- Si detecta una nueva guía CCN-STIC, dispara workflow de re-ingesta del corpus.
- Si detecta un cambio en el RD, lo marca como CRÍTICO y notifica inmediatamente.

MODELO: Haiku 4 (volumen, bajo coste)
```

### C.16 Agente 16 — Generador de Quick Wins

```
ROL: Identificar quick wins (acciones de bajo esfuerzo, alto impacto visible) en cada proyecto.

INPUT: Estado actual del proyecto + gap analysis.

OUTPUT: Lista priorizada de 5-10 quick wins con esfuerzo estimado y entregable.

REGLAS:
- Quick win = esfuerzo < 4 horas + impacto visible para el cliente + cubre al menos una medida ENS.
- Ejemplos típicos: configurar SPF/DKIM/DMARC, eliminar cuentas inactivas, activar BitLocker masivo, aprobar la primera política, primer simulacro de phishing.
- Lista derivada de catálogo precargado, no inventes.
- Marcos los usa para mantener la motivación del cliente durante la implantación.

MODELO: Sonnet 4.5
```

---

## APÉNDICE D — RESUMEN OPERATIVO PARA MARCOS

### D.1 Lo que esta plataforma te da

1. **Centro de mando único.** Todos tus proyectos ENS, todas las categorías, todo el ciclo, en una sola interfaz que tú controlas.
2. **Profundidad B/M/A total.** Las 73 medidas, todos los refuerzos, todas las evidencias, sin que tengas que recordar nada.
3. **Cero alucinación.** Los motores deterministas toman las decisiones normativas. El LLM solo redacta y conversa.
4. **Cliente sin fricción.** Cero cuentas, cero onboarding, cero soporte. Solo enlaces puntuales con clave.
5. **Pentesting integrado.** Herramientas open source orquestadas inteligentemente, adaptadas a la categoría del cliente. Informes en formato auditor español.
6. **Motor de obligaciones anti-alucinación.** Plantillas inmutables instanciadas con el contexto del cliente. Tres modos de ejecución: tú generas, cliente aporta evidencia, acción técnica autorizada vía link.
7. **Dossier auditor perfecto.** Estructura exacta que un auditor ENAC veterano reconoce. Matriz cruzada del 99 que el auditor abre y verifica todo en 30 minutos.
8. **Copiloto LLM.** Tú con conocimiento mínimo + copiloto = consultor ENS senior asistido.
9. **Integración con ENS Radar v2.** Los leads del Radar entran directamente como proyectos pre-cargados.
10. **Dogfooding ENS Medio.** La plataforma cumple ENS sobre sí misma, con su propia DdA y evidencias.

### D.2 Lo que NO te da (deliberadamente)

- **Monitoreo continuo del cliente.** Eso es el add-on futuro. Si lo metes ahora, multiplicas por 3 la complejidad.
- **App para el cliente.** Add-on futuro.
- **Multi-consultor.** Esto es solo para ti. Si en el futuro quieres convertirlo en SaaS para otros consultores, es otra plataforma.
- **Soporte para entidades públicas.** Tu mercado es el sector privado que licita. Las herramientas del CCN para entidades públicas (AMPARO, MARGA, etc.) no se integran inicialmente.

### D.3 Ruta crítica de los primeros 3 meses

| Mes | Foco | Estado al final del mes |
|---|---|---|
| **Mes 1** | Infra Hetzner + stack base + corpus ENS al grafo + RAG operativo | Marcos pregunta al copiloto sobre cualquier medida ENS y obtiene respuesta con citas |
| **Mes 2** | Motores deterministas (Categorización, DdA, Control Engine) + Document Factory + plantillas | Marcos genera la DdA completa y todas las políticas para un cliente ficticio |
| **Mes 3** | Magic Link Engine + Onboarding + Evidence Vault + Gap Analysis básico | Marcos lanza onboarding al primer cliente real, recoge evidencias y genera primer informe de gap |

A partir del mes 3, el resto de motores se añaden incrementalmente sin parar la operación.

### D.4 Decisión clave que solo tú puedes tomar

**¿Empiezas con MAGERIT propio o usas PILAR como pasarela?**

- **Opción A:** construir Motor 2 MAGERIT propio desde el principio (semanas 12-14). Más trabajo inicial, pero independencia total.
- **Opción B:** usar PILAR del CCN como herramienta externa. Marcos exporta los activos desde la plataforma, los importa a PILAR, hace el AR allí, y vuelve a importar el resultado. Menos trabajo inicial, pero dependes de PILAR.

**Recomendación:** opción B para el primer cliente piloto, opción A a partir del cliente 2-3 cuando tengas claro qué necesitas. Esto te ahorra 2-3 semanas de desarrollo al principio.

### D.5 Riesgos a vigilar durante la construcción

1. **Tentación de meter más allá del scope.** El monitoreo continuo y la app del cliente son add-ons futuros, no parte de v1.
2. **Sobre-engineering del LLM.** Empieza con prompts simples + RAG + citas. La sofisticación viene con uso real.
3. **Plantillas DOCX a medio hacer.** Las ~110 plantillas de la Parte 2 son trabajo manual de redacción legal. No hay atajos. Recomendación: contratar una semana a un consultor ENS senior para revisar las 30 plantillas críticas (políticas + procedimientos).
4. **Integraciones CCN bloqueadas.** PILAR/LUCIA/INES no tienen APIs modernas. Asume integración por ficheros y carga manual durante v1.
5. **Pentesting Engine es ambicioso.** Empieza con 5 herramientas (Nmap, Nuclei, ZAP, Prowler, CLARA), añade el resto incrementalmente.

### D.6 Pregunta abierta para Marcos

¿Quieres que la plataforma sea capaz de **cargar el dossier final directamente en el portal de la entidad certificadora ENAC** cuando estas tengan API? Si la respuesta es sí, hay que añadir un **Motor de Submission (a numerar cuando se construya)** en una versión futura. Por ahora, el dossier se descarga y se entrega manualmente. El número 24 está ya asignado al **Intelligent Document Management Engine** introducido en la revisión de 10 de abril de 2026.

---

## APÉNDICE E — MATRIZ DE COBERTURA v2.0: REQUISITO MARCOS → SECCIÓN DEL DOCUMENTO

**Actualizada en v2.0** con todos los nuevos requisitos del ciclo del consultor.

### Requisitos v1.x (mantenidos)

| Lo que pediste | Cubierto en |
|---|---|
| Plataforma 100% mía, cliente sin cuenta | §0, Motor 12, Magic Links |
| Profundidad B/M/A total | §1.3, §A (catálogo evidencias) |
| Marcos con conocimiento mínimo | Motor 11 Copiloto, Apéndice C Agente 14 |
| Cero alucinación regulatoria | §0 principio 4, Parte 6 tabla agentes, Apéndice C |
| Pentesting open source automatizado | Motor 8, §8.1-8.7 |
| Red team para Alta | Motor 8.2, MITRE Caldera |
| Adaptación pentest según categoría | Motor 8.2 tabla |
| Motor de planeación de obligaciones | Motor 5, Apéndice B |
| Anti-alucinación obligaciones | Biblioteca JSON inmutable §B |
| Cliente acepta entregables vía link | Modo 1 `consultor_genera`, §B |
| Acciones técnicas autorizadas vía link | Modo 3 `accion_tecnica_remota`, §B |
| Conexión con PILAR | Motor 2, §7 |
| Conexión con LUCIA | Procedimiento E-204, §7 |
| Formato auditor español | §2.15, Motor 9, Apéndice C Agente 10 |
| Todos los entregables B/M/A | §2 entera, §A |
| Auditoría perfecta | §10, Motor 10 auditor virtual |
| Documentos en base de conocimiento | §1.6, §1.7, §A |
| Integración ENS Radar v2 | §11.2 |

### Requisitos nuevos v2.0 (del mensaje extenso de Marcos)

| Lo que pediste | Cubierto en |
|---|---|
| Plantilla de reunión exploratoria con preguntas predefinidas | §3.1.3, Apéndice F.1, Agente 18 |
| Outputs en vivo mientras Marcos habla con el cliente | §3.1.3 panel en vivo, Agente 18 |
| Nivel de madurez / categoría estimada / alcance en la exploratoria | §3.1.3 outputs en vivo |
| Generación automática de propuesta formal 10-20 páginas | §3.1.4, Motor 13, Agente 19, Apéndice F.2 |
| Estética cuidada en propuesta | §3.1.4 "estética" + Motor 13 plantillas |
| Plantilla de reunión de negociación y cierre | §3.1.5, Apéndice F.3, Agente 20 |
| Ajustes de contrato que entran en la base de conocimiento | §3.1.5, Agente 20 + project knowledge graph |
| **Cláusula CRÍTICA de recursos del cliente** | §3.1.6, Apéndice F.4, Motor 14 |
| Evitar que cliente ataque la facturación por no colaborar | §3.1.6 consecuencias + Motor 15 parones |
| Setup administrativo post-venta | §3.1.7, flujo Temporal `post_sale_setup` |
| Onboarding adaptativo por sector | Motor 16, matriz 10×7, §3.2.1 |
| Onboarding adaptativo por tipo de equipo del cliente | Motor 16, §3.2.1 |
| Magic links cifrados con clave para onboarding | §3.2.2, Motor 12, Motor 16 |
| Conectores directos para recoger info del cliente | §3.2.3, 10+ conectores OAuth |
| Tooltips intuitivos para no técnicos | §3.2.2, Motor 16 |
| Protocolo MCP para barrido | §3.2.3 servidor MCP local |
| Acta de nombramiento con firma vía URL | §3.2.6, E-002 automatizado, Motor 12 |
| Plan de proyecto detallado (WBS, Gantt, dependencias) | §3.2.8, Motor 17 |
| Plan de comunicación con frecuencias y formatos | §3.2.9, Motor 18 |
| Reportes (weekly sponsor, monthly Comité, quarterly dirección) | §3.2.9, Motor 18 |
| Plan de gestión de riesgos del PROYECTO (no del sistema) | §3.2.10, Motor 19 |
| ~30 riesgos típicos del consultor precargados | §3.2.10 catálogo, Motor 19 |
| Entorno colaborativo efímero (carpeta + videollamada) | §3.2.11, Motor 20 |
| Videollamadas tipo Teams integradas | §3.2.11, LiveKit, Motor 20 |
| Mapa de stakeholders (no solo organigrama) | §3.3.1.A, Agente 22 |
| Inventario de procesos de negocio | §3.3.1.B, Agente 23 |
| BIA perfecto | §3.3.1.B + Motor 6 BIA template |
| Inventario obligaciones legales (RGPD, PCI, sectorial) | §3.3.1.C, Agente 24 |
| Inventario de proyectos en curso del cliente | §3.3.1.D |
| Diagnóstico técnico automatizado vía enlaces/conectores | §3.3.2, Motor 22 |
| Discovery de activos / identidades / datos / configs / vulns | §3.3.2, Motor 22 |
| MCP para barrido IA respetando RGPD | §3.3.2 MCP + minimización |
| Asistencia en todas las fases (95/5) | §3.11 reparto de esfuerzo por fase |
| Fase 2 Diseño SGSI completa | §3.4 (remite a Parte 2) |
| Fase 3 Implantación con 4 modos de ejecución | §3.5, Motor 5 |
| Fase 4 Verificación interna | §3.6 |
| Fase 5 Preparación auditoría | §3.7 |
| Coaching del personal del cliente | §3.7.4, Agentes 12 y 26 |
| Fase 6 Auditoría externa | §3.8, modo auditoría en curso |
| Fase 7 Remediación | §3.9, Motor 5 reutilizado |
| Fase 8 Mantenimiento post-certificación (retainer) | §3.10, Motor 23 |
| Dashboard multi-cliente para gestionar 20+ retainers | §3.10.3, Motor 23 |
| Escalar sin contratar a nadie | §3.10.3 + §3.11 capacidad |

### Requisitos sin cubrir (pendientes de conversación)

Ninguno detectado al cierre de v2.0. Si Marcos detecta uno nuevo, se añade en v2.1.

---

## APÉNDICE F — PLANTILLAS DEL CICLO COMERCIAL Y DE GESTIÓN DE PROYECTO

Este apéndice contiene las plantillas operativas que la plataforma usa en las Fases −1 y 0 del ciclo del consultor. Son plantillas **estructurales**, no texto legal literal. El texto legal lo valida Marcos (o un abogado) antes de productizar cada plantilla.

---

### F.1 Plantilla de Reunión Exploratoria Gratuita (45-60 min)

**Identificador:** `exploratory_meeting_template_v1`
**Usado por:** Agente 18 — Asistente de Reunión Exploratoria
**Duración objetivo:** 50 min con distribución 40% Marcos habla / 60% cliente habla

**Interfaz que ve Marcos durante la reunión:**

Pantalla dividida en dos columnas:
- **Izquierda:** bloques de preguntas (A-F) con campo de notas libre por pregunta + transcripción opcional en vivo (whisper-local).
- **Derecha:** panel de outputs en vivo que se recalcula en cada pausa.

**Estructura de la plantilla:**

```yaml
template_id: exploratory_meeting_template_v1
version: 1.0
duration_target_minutes: 50
blocks:
  - id: block_A
    title: "Contexto de negocio"
    duration_target: 7
    questions:
      - id: A1
        question: "¿A qué se dedica exactamente la empresa?"
        input_type: free_text
        min_length: 20
      - id: A2
        question: "¿Cuántas personas trabajan en la empresa?"
        input_type: number_or_range
      - id: A3
        question: "¿Qué porcentaje del negocio depende del sector público?"
        input_type: percent_or_estimate
      - id: A4
        question: "¿En qué comunidades autónomas operan?"
        input_type: multi_select_ccaa
      - id: A5
        question: "¿Qué sectores públicos son clientes? (ayuntamientos, sanidad, educación, justicia, etc.)"
        input_type: multi_select_sectors
      - id: A6
        question: "¿Cuántos contratos públicos en curso? Valor aproximado total."
        input_type: structured_count_amount

  - id: block_B
    title: "Contexto del requisito ENS"
    duration_target: 12
    questions:
      - id: B1
        question: "¿Cómo les ha llegado la obligación ENS?"
        input_type: single_select
        options:
          - pliego_especifico
          - exigencia_cliente_recurrente
          - proactividad_comercial
          - auditoría_previa_pendiente
      - id: B2
        question: "¿Hay un pliego concreto donde se exija ENS?"
        input_type: boolean
        follow_up_if_true:
          action: upload_pliego
          trigger_agent: 2  # Analizador de Pliegos
      - id: B3
        question: "¿Qué categoría cree el cliente que necesita?"
        input_type: single_select
        options: [basica, media, alta, no_lo_sabe]
      - id: B4
        question: "¿Hay plazo legal o contractual marcado?"
        input_type: date_or_duration
      - id: B5
        question: "¿Existe penalización si no se cumple el plazo?"
        input_type: boolean_with_detail
      - id: B6
        question: "¿Han intentado esta certificación antes con otro consultor?"
        input_type: boolean_with_detail

  - id: block_C
    title: "Madurez actual"
    duration_target: 12
    questions:
      - id: C1
        question: "¿Tienen ISO 27001, RGPD formalizado u otra certificación de seguridad?"
        input_type: multi_select
        options: [iso27001, rgpd_formalizado, pci_dss, soc2, iso27017, iso27018, ninguno]
      - id: C2
        question: "¿Tienen política de seguridad escrita? ¿Cuándo se aprobó?"
        input_type: boolean_with_date
      - id: C3
        question: "¿Tienen DPO? Interno o externo."
        input_type: single_select
        options: [no, interno, externo]
      - id: C4
        question: "¿Tienen responsable de seguridad identificado?"
        input_type: boolean_with_name
      - id: C5
        question: "¿Tienen SIEM, EDR, MFA universal, backups probados?"
        input_type: multi_select
      - id: C6
        question: "¿Han sufrido un incidente grave en los últimos 3 años?"
        input_type: boolean_with_detail
      - id: C7
        question: "¿Han hecho pentest? ¿Cuándo el último?"
        input_type: boolean_with_date
      - id: C8
        question: "¿Qué cloud usan?"
        input_type: multi_select
        options: [aws, azure, gcp, m365, google_workspace, on_premise, otro]

  - id: block_D
    title: "Organización interna"
    duration_target: 7
    questions:
      - id: D1
        question: "¿Quién es el sponsor del proyecto?"
        input_type: name_role
      - id: D2
        question: "¿Tienen equipo TI interno? ¿Cuántas personas? Perfil."
        input_type: structured_team_info
      - id: D3
        question: "¿Tienen equipo legal? Interno o externo."
        input_type: single_select
      - id: D4
        question: "¿Quién firma los contratos? ¿Quién autoriza presupuestos?"
        input_type: names_roles
      - id: D5
        question: "¿Algún tema político interno relevante?"
        input_type: free_text
        confidential: true  # Solo Marcos ve esto

  - id: block_E
    title: "Expectativas y restricciones"
    duration_target: 8
    questions:
      - id: E1
        question: "¿Qué plazo consideran razonable?"
        input_type: duration_range
      - id: E2
        question: "¿Cuál sería el desastre para ellos en este proyecto?"
        input_type: free_text
      - id: E3
        question: "¿Qué han presupuestado o qué rango les parece razonable?"
        input_type: amount_range
      - id: E4
        question: "¿Quieren declaración de conformidad o certificación ENAC formal?"
        input_type: single_select
        options: [declaracion, certificacion, no_saben]
      - id: E5
        question: "¿Necesitan mantenimiento post-certificación?"
        input_type: boolean

  - id: block_F
    title: "Escucha activa y cierre"
    duration_target: 5
    actions:
      - marcos_resume_entendido
      - marcos_promete_propuesta_en_N_dias
      - marcos_pregunta_dudas
      - agente_18_genera_resumen_final

live_outputs:
  - preliminary_category_estimation
  - preliminary_maturity_level_L0_to_L5
  - preliminary_effort_weeks
  - preliminary_marcos_hours
  - preliminary_scope_summary
  - viable_vs_desired_timeline
  - detected_project_risks
  - detected_quick_wins
```

---

### F.2 Plantilla de Propuesta Formal (10-20 páginas)

**Identificador:** `P-001_commercial_proposal_v1`
**Generado por:** Motor 13 — Commercial Document Factory
**Agente:** Agente 19 — Redactor de Propuestas
**Formato:** DOCX → PDF profesional

**Estructura completa (secciones fijas + contenido personalizable):**

```
Portada
├── Logo cliente (importado del onboarding o extraído del dominio)
├── Logo Marcos
├── Título: "Propuesta de Servicios de Consultoría ENS"
├── Nombre del proyecto
├── Nombre del cliente + CIF
├── Versión y fecha
└── Validez de la oferta (30 días por defecto)

Índice auto-generado

1. Resumen Ejecutivo (1 página)
   ├── Contexto en 3 frases
   ├── Categoría objetivo
   ├── Plazo propuesto
   ├── Inversión total
   └── Resultado esperado: Declaración o Certificación ENAC

2. Contexto Entendido (1-2 páginas)
   ├── Descripción del cliente (del Bloque A de la exploratoria)
   ├── Relación con sector público (del Bloque A)
   ├── Origen del requisito ENS (del Bloque B)
   ├── Madurez actual estimada (del Bloque C)
   └── Expectativas del cliente (del Bloque E)

3. Alcance Propuesto (2-3 páginas)
   ├── Servicios en alcance
   ├── Sistemas en alcance
   ├── Ubicaciones
   ├── Unidades organizativas
   ├── Interconexiones
   ├── Proveedores críticos
   ├── Exclusiones y justificación
   └── Diagrama de contexto (auto-generado con Mermaid)

4. Metodología (1-2 páginas)
   ├── Presentación del ciclo del consultor en 10 fases
   ├── Explicación de cada fase aplicable al cliente
   └── Diferenciador: plataforma interna con 95% de automatización

5. Fases y Cronograma (1-2 páginas)
   ├── Diagrama Gantt de alto nivel (Mermaid → PNG)
   ├── Hitos mensuales clave
   └── Duración total estimada

6. Entregables por Fase (2-3 páginas)
   ├── Tabla con códigos E-XXX y descripción
   └── Firmado vs auditable vs informativo

7. Equipo (0.5 página)
   ├── Marcos como consultor principal
   ├── Colaboradores si aplica
   └── Perfiles profesionales resumidos

8. Supuestos y Exclusiones (1 página)
   ├── Supuestos que se asumen
   ├── Exclusiones explícitas
   └── Qué pasa si un supuesto falla

9. Condiciones Económicas (1 página)
   ├── Honorarios totales
   ├── Hitos de pago:
   │   ├── Anticipo 20-30% a la firma
   │   ├── Pagos mensuales contra hitos
   │   └── Pago final contra entrega del dossier auditor
   ├── Forma de pago
   ├── IVA 21%
   └── Retención IRPF 15% si aplica

10. Criterios de Aceptación (0.5 página)
    ├── Qué debe pasar para considerar cada hito cumplido
    └── Procedimiento de aceptación formal

11. Gestión de Riesgos del Proyecto (1 página)
    ├── Lista de riesgos identificados
    ├── Probabilidad, impacto, contingencia
    └── Distinción con el AR del sistema del cliente

12. Política de Confidencialidad (0.5 página)
    ├── NDA mutuo propuesto
    └── Tratamiento de información sensible

13. Validez de la Oferta (0.2 página)
    └── 30 días desde la fecha de la propuesta

Anexo A: Perfil profesional de Marcos
Anexo B: Casos de éxito anonimizados
Anexo C: Certificaciones
Anexo D: Referencias (opcional)
```

**Estética de la plantilla:**
- Tipografía principal: Inter o Source Sans (carga libre).
- Paleta corporativa configurable por Marcos (primario, secundario, acento).
- Márgenes generosos: 2.5cm.
- Interlineado 1.15.
- Portada con imagen abstracta o composición geométrica.
- Tablas con estilo "finance report" (cabeceras con fondo color corporativo, filas alternas).
- Diagramas Gantt rasterizados con paleta coherente.

---

### F.3 Plantilla de Reunión de Negociación y Cierre

**Identificador:** `negotiation_meeting_template_v1`
**Usado por:** Agente 20 — Asistente de Negociación
**Duración objetivo:** 45-60 min

**Interfaz:**

Izquierda: puntos de la propuesta con campo "ajuste pedido por el cliente" y botón "aplicar".
Derecha: modelo económico recalculado en vivo + alerta cuando un ajuste sale del rango preautorizado.

```yaml
template_id: negotiation_meeting_template_v1
pre_authorized_ranges:  # Marcos configura por cliente
  price_flexibility_percent: -10  # Puede bajar hasta 10%
  timeline_flexibility_weeks: +2  # Puede extender 2 semanas
  scope_additions_allowed: false
  payment_terms_flexibility:
    - anticipo_minimo_percent: 15
    - pagos_mensuales_maximos_meses: 12
  retainer_mandatory: false  # Si true, exigir firmar retainer

negotiation_points:
  - point: price_total
    current_value: "{{ proposal.total_amount }}"
    client_request: null  # rellena Marcos en vivo
    within_range_check: auto

  - point: timeline
    current_value: "{{ proposal.duration_weeks }}"
    client_request: null
    within_range_check: auto

  - point: scope_services
    current_value: "{{ proposal.scope.services }}"
    client_request: null
    within_range_check: auto

  - point: payment_terms
    current_value: "{{ proposal.payment_terms }}"
    client_request: null
    within_range_check: auto

  - point: retainer_post_cert
    current_value: "{{ proposal.retainer_proposed }}"
    client_request: null
    within_range_check: auto

outputs:
  - adjusted_proposal_v2
  - generate_contract_now_button  # Trigger Motor 14
```

---

### F.4 Cláusula Crítica de Recursos del Cliente (fragmento del contrato)

**Identificador:** `C-001_critical_clause_client_resources_v1`
**Parte del:** Contrato C-001
**Validar con abogado antes de productizar**

```
CLÁUSULA [N] — OBLIGACIONES DE COLABORACIÓN DEL CLIENTE

1. Recursos humanos

El CLIENTE se compromete a designar y mantener disponibles durante toda la 
vigencia del Contrato a los siguientes interlocutores:

a) Un SPONSOR DEL PROYECTO con autoridad de decisión sobre presupuesto, 
   alcance y plazos, con disponibilidad mínima garantizada de [X] horas 
   por semana para las reuniones de seguimiento y aprobaciones formales.

b) El RESPONSABLE TI o equivalente, con disponibilidad mínima garantizada 
   de [Y] horas por semana durante las Fases de Diagnóstico e Implantación.

c) El RESPONSABLE LEGAL o DPO si existe en la organización, con disponibilidad 
   a demanda para revisión de cláusulas contractuales y decisiones RGPD.

d) El ÓRGANO SUPERIOR (dirección) disponible para las firmas formales de 
   los entregables que lo requieran (Política de Seguridad, Declaración de 
   Aplicabilidad, Aprobación del Riesgo Residual, Acta de Nombramiento de 
   Roles, Revisiones por la Dirección).

2. Recursos técnicos

El CLIENTE se compromete a proporcionar, vía enlaces de autorización 
puntual generados por la plataforma del CONSULTOR, los siguientes accesos 
de sólo lectura:

a) Acceso a la CMDB, directorio activo, configuración cloud y SIEM del 
   CLIENTE para el descubrimiento técnico automatizado.

b) Posibilidad de ejecutar escaneos autorizados durante ventanas pactadas.

c) Entrega de la documentación de seguridad existente (políticas previas, 
   procedimientos, informes de auditoría, pentests anteriores) en los 
   primeros 10 días laborables desde la firma del Contrato.

3. Recursos organizativos

a) El CLIENTE emitirá una comunicación interna del CEO al personal 
   anunciando el proyecto ENS en los primeros 5 días laborables desde la 
   firma.

b) El CLIENTE facilitará la disponibilidad del personal para las entrevistas 
   de diagnóstico en plazos razonables (máximo 5 días laborables desde la 
   solicitud).

c) El CLIENTE constituirá formalmente el Comité de Seguridad antes de 
   finalizar la Fase 0 del proyecto.

4. Consecuencias del incumplimiento de estas obligaciones

4.1 Parón documentado: cada retraso imputable al CLIENTE en las entregas 
anteriores generará un parón documentado del cronograma del proyecto, 
formalizado con justificación por el CONSULTOR.

4.2 Facturación del tiempo de espera: el parón será facturable a la tarifa 
de "tiempo de espera" establecida en el Anexo Económico, equivalente al 
50% de la tarifa hora estándar del CONSULTOR, con un tope mensual de 
[Z] euros.

4.3 Pausa del proyecto: si el parón supera [P] días laborables consecutivos, 
el CONSULTOR podrá pausar el proyecto y retomarlo posteriormente con 
recálculo de plazos y sin penalización.

4.4 Resolución del contrato: si el parón supera [R] días laborables 
consecutivos, el CONSULTOR podrá resolver el Contrato conservando los 
pagos ya realizados y facturando las horas efectivamente trabajadas hasta 
la fecha de resolución.

4.5 Los días naturales festivos en el calendario laboral español no computan 
a efectos de plazos para ambas partes.
```

**Valores por defecto** (editables por Marcos antes de generar el contrato):
- X = 2 horas/semana (sponsor)
- Y = 4 horas/semana en Fase 1, 8 horas/semana en Fase 3 (TI)
- Z = 3.000 €/mes tope de facturación de parones
- P = 10 días laborables para pausa
- R = 30 días laborables para resolución

---

### F.5 Plantilla de Plan de Proyecto Detallado

**Identificador:** `project_plan_template_v1`
**Generado por:** Motor 17 — Project Planning Engine
**Formato:** XLSX (Gantt) + PDF (documento narrativo) + MS Project XML (opcional)

**Estructura:**

```yaml
project_plan_sections:
  - section: overview
    fields:
      - project_name
      - client_name
      - category_objective (B/M/A)
      - start_date
      - end_date
      - total_effort_marcos_hours
      - total_duration_weeks
      - critical_path_length_weeks
      - confidence_level (low/medium/high)

  - section: wbs
    description: "Work Breakdown Structure"
    rows_from: catalog_tasks_by_category
    fields_per_row:
      - task_id (WBS-XXX)
      - task_name
      - parent_task_id
      - phase (-1 to 8)
      - start_date
      - end_date
      - duration_days
      - effort_marcos_hours
      - effort_platform_automated
      - responsible (marcos | cliente | plataforma | mixto)
      - dependencies (list of task_ids)
      - deliverable_e_code (link to Parte 2)
      - status (por_hacer | en_curso | bloqueada | en_revision | hecha | descartada)
      - blockers (if blocked)

  - section: milestones
    rows_from: critical_milestones
    fields_per_row:
      - milestone_id (MS-XXX)
      - milestone_name
      - target_date
      - linked_deliverables
      - payment_linked (percent of total)

  - section: critical_path
    auto_calculated: true

  - section: slack_analysis
    auto_calculated: true

  - section: resource_allocation
    fields:
      - marcos_weekly_capacity_hours
      - marcos_peak_weeks
      - client_weekly_capacity_required
      - client_peak_weeks

exports:
  - format: xlsx
    template: gantt_template_v1.xlsx
  - format: pdf
    template: project_plan_narrative_template_v1.docx
  - format: mspx
    optional: true
```

---

### F.6 Plantilla de Plan de Comunicación

**Identificador:** `communication_plan_template_v1`
**Generado por:** Motor 18 — Communication & Reporting Engine

```yaml
communication_plan:
  recipients:
    - role: sponsor
      report: weekly_status
      format: "1 página DOCX + PNG"
      frequency: "Viernes 16:00"
      channel: email + feed_proyecto
      template: sponsor_weekly_v1.docx

    - role: comite_seguridad
      report: monthly_status
      format: "3-5 páginas DOCX/PDF"
      frequency: "1 día antes de reunión mensual"
      channel: email + adjunto en convocatoria
      template: comite_monthly_v1.docx

    - role: direccion
      report: quarterly_executive
      format: "1 página ejecutiva con semáforo RAG"
      frequency: "Primera semana del trimestre"
      channel: email + feed_proyecto
      template: direccion_quarterly_v1.docx

    - role: cliente_general
      report: feed_updates
      format: "Notificaciones en magic link del proyecto"
      frequency: "Cuando hay hito o quick win"
      channel: feed_proyecto + email opcional
      template: feed_item_v1.html

  escalations:
    - trigger: riesgo_materializado_alto
      notify: [sponsor, direccion]
      channel: email_urgente + llamada
    - trigger: parón_por_cliente_5_dias
      notify: [sponsor]
      channel: email_formal
    - trigger: hallazgo_critico_auditoria
      notify: [sponsor, direccion, comite]
      channel: reunión_convocatoria_urgente
```

---

### F.7 Plantilla de Plan de Gestión de Riesgos del Proyecto

**Identificador:** `project_risk_plan_template_v1`
**Generado por:** Motor 19 — Project Risk Management Engine

Estructura YAML con el catálogo de ~30 riesgos precargados (ver lista completa en §3.2.10 del cuerpo del documento). Cada riesgo instanciado con:

```yaml
risk_instance:
  risk_id: RK-001
  title: "El cliente no colabora en los plazos acordados"
  probability: medium  # low/medium/high
  impact_days: 15
  impact_euros: 5000
  category: client_cooperation
  owner: marcos
  trigger: "Magic link no respondido en 7 días naturales"
  status: monitorizado  # identificado/monitorizado/materializado/cerrado
  mitigation_plan:
    - "Cláusula de recursos del cliente en contrato (F.4)"
    - "Recordatorios automáticos del Motor 18"
    - "Escalado al sponsor vía email formal al segundo recordatorio"
  contingency_plan:
    - "Pausa del proyecto con parón facturable según cláusula crítica"
    - "Reunión de emergencia con sponsor y dirección"
    - "Reformulación del plan con nuevos plazos"
```

---

### F.8 Plantilla de Kick-off Ejecutivo

**Identificador:** `kickoff_meeting_template_v1`
**Generado por:** Motor 6 — Document Factory (modo comercial)

**Output:** presentación PPTX/PDF de 10-15 slides + acta de kick-off DOCX/PDF

**Slides obligatorias:**
1. Portada
2. Objetivos del proyecto
3. Alcance confirmado (remite a Documento de Alcance E-009)
4. Metodología (10 fases del ciclo)
5. Cronograma macro
6. Hitos clave
7. Equipo (Marcos + colaboradores + interlocutores del cliente)
8. Plan de comunicación
9. Plan de gestión de riesgos
10. Entorno colaborativo efímero (cómo se usan los magic links)
11. Primeras acciones de la semana 1
12. Compromisos del cliente (resumen de cláusula crítica)
13. Preguntas y cierre

**Acta de kick-off:** plantilla `kickoff_minute_template_v1.docx` con asistentes, acuerdos, próximos pasos, fecha de la siguiente reunión, firma del sponsor vía magic link.

---

### F.9 Plantilla de Contrato de Retainer Post-Certificación

**Identificador:** `C-003_retainer_contract_v1`

Estructura similar a C-001 pero orientada a mantenimiento recurrente. Secciones clave:
- Actividades incluidas por modalidad (Básico / Medio / Alto).
- Actividades excluidas facturables aparte.
- SLA de respuesta a incidentes.
- Coordinación con auditorías de seguimiento y re-certificación.
- Facturación recurrente mensual.
- Duración mínima (12 meses recomendado).
- Cláusula de revisión anual.
- Terminación y devolución de información.

---

### F.10 Plantilla de Informe de Diagnóstico Inicial (E-090)

**Identificador:** `E-090_initial_diagnosis_report_v1`
**Generado por:** Motor 6 (Document Factory) + Motor 21 + Motor 22
**Volumen:** 30-80 páginas según categoría objetivo

**Estructura:**

```
1. Resumen Ejecutivo (1-2 páginas)
   - Para lectura por dirección
   - Sin jerga técnica

2. Contexto y Alcance Confirmado

3. Hallazgos por Dominio
   3.1 Organizativo (del Motor 21)
     - Mapa de stakeholders (versión pública, sin notas confidenciales)
     - Procesos de negocio críticos
     - Obligaciones legales y contractuales aplicables
     - Proyectos en curso relevantes
   3.2 Técnico (del Motor 22)
     - Inventario de activos descubiertos
     - Estado de identidades y accesos
     - Estado de protección de datos
     - Estado de configuraciones
     - Vulnerabilidades detectadas
     - Estado de logging y monitorización
     - Data flow diagrams
     - Estado de continuidad
   3.3 Proveedores
     - Inventario completo
     - Criticidad
     - Cumplimiento estimado
   3.4 Documental
     - Documentación existente vs esperada
   3.5 Personas
     - Madurez en seguridad
     - Resultados baseline

4. Mapa de Calor de Criticidad (heatmap visual)

5. Comparativa contra ENS
   - Por categoría objetivo
   - Preview de gap analysis
   - Estimación de L0-L5 actual por medida

6. Estimación de Esfuerzo para Alcanzar la Categoría Objetivo

7. Riesgos del Proyecto Identificados (vivos desde Fase 0)

8. Quick Wins Disponibles

9. Recomendaciones para Fase 2 (Diseño)

Anexos:
A. Detalle de activos descubiertos
B. Detalle de vulnerabilidades críticas
C. Listado de políticas a crear / actualizar
D. Listado de procedimientos a crear / actualizar
```

---

### F.11 Tabla resumen de plantillas del Apéndice F

| ID | Plantilla | Fase | Motor responsable | Agente |
|---|---|---|---|---|
| F.1 | Reunión Exploratoria | −1 | Motor 13 | Agente 18 |
| F.2 | Propuesta Formal P-001 | −1 | Motor 13 | Agente 19 |
| F.3 | Reunión Negociación | −1 | Motor 14 | Agente 20 |
| F.4 | Cláusula Recursos Cliente | −1 | Motor 14 | — |
| F.5 | Plan de Proyecto | 0 | Motor 17 | — |
| F.6 | Plan de Comunicación | 0 | Motor 18 | — |
| F.7 | Plan Riesgos Proyecto | 0 | Motor 19 | — |
| F.8 | Kick-off Ejecutivo | 0 | Motor 6 | — |
| F.9 | Contrato Retainer C-003 | 8 | Motor 13 + 14 | — |
| F.10 | Informe Diagnóstico E-090 | 1 | Motor 6 + 21 + 22 | Agentes 22-25 |

---

## APÉNDICE G — CHECKLIST DE VERIFICACIÓN 95/5

Si al finalizar un proyecto Marcos ha dedicado más horas de las previstas por el reparto 95/5, hay que identificar dónde y automatizarlo en v2.1.

**Proyecto Básica — objetivo ≤ 70 horas de Marcos totales**
- [ ] Fase −1: ≤ 2.5h por lead ganado
- [ ] Fase 0: ≤ 5.5h
- [ ] Fase 1: ≤ 8h
- [ ] Fase 2: ≤ 12h
- [ ] Fase 3: ≤ 30h
- [ ] Fase 4: ≤ 8h
- [ ] Fase 5: no aplica (Declaración)
- [ ] Fase 6: no aplica
- [ ] Fase 7: ≤ 4h
- [ ] TOTAL ≤ 70h

**Proyecto Media — objetivo ≤ 180 horas de Marcos totales**
- [ ] Fase −1: ≤ 2.5h
- [ ] Fase 0: ≤ 5.5h
- [ ] Fase 1: ≤ 12h
- [ ] Fase 2: ≤ 18h
- [ ] Fase 3: ≤ 90h
- [ ] Fase 4: ≤ 20h
- [ ] Fase 5: ≤ 7h
- [ ] Fase 6: ≤ 15h (presencial obligado)
- [ ] Fase 7: ≤ 9h
- [ ] TOTAL ≤ 180h

**Proyecto Alta — objetivo ≤ 280 horas de Marcos totales**
- [ ] Fase −1: ≤ 3h
- [ ] Fase 0: ≤ 7h
- [ ] Fase 1: ≤ 15h
- [ ] Fase 2: ≤ 25h
- [ ] Fase 3: ≤ 140h
- [ ] Fase 4: ≤ 30h
- [ ] Fase 5: ≤ 10h
- [ ] Fase 6: ≤ 30h
- [ ] Fase 7: ≤ 15h
- [ ] TOTAL ≤ 280h

**Retainer por cliente/año — objetivo ≤ 50 horas**
- [ ] Actividades anuales obligatorias: ≤ 20h
- [ ] Comités + reporting: ≤ 10h
- [ ] Vigilancia y remediación continua: ≤ 15h
- [ ] Incidentes ad-hoc: ≤ 5h buffer
- [ ] TOTAL ≤ 50h

**Si alguna fase supera su objetivo en más del 20%, la plataforma debe auto-diagnosticar por qué y proponer automatización adicional.**

---
---

## APÉNDICE H — CORPUS NORMATIVO COMPLETO PARA INGESTA

Este apéndice lista los ~92 documentos que Claude Code debe descargar, ingestar y mantener en el grafo de conocimiento durante las semanas 3-5 del plan. Sin este corpus, el Motor 11 (Copiloto) y el RAG no funcionan y el Agente 15 (Vigilancia Normativa) no tiene nada que monitorizar.

**Formato:** cada fila tiene `codigo`, `titulo`, `fuente_url`, `formato`, `prioridad` (P0 crítico, P1 alto, P2 medio, P3 bajo), `frecuencia_revision`.

**Automatización:** crear un script `corpus_ingest.py` que descargue, verifique hash SHA-256, parsee, chunkee (1000 tokens por chunk con overlap 200), vectorice con BGE-M3, inserte en `knowledge_documents` + `knowledge_chunks` + grafo AGE. Ejecutar semanalmente como Celery beat task para detectar cambios.

### H.1 Normativa primaria BOE (11 documentos) — P0

| Código | Título | Fuente |
|---|---|---|
| BOE-RD-311-2022 | Real Decreto 311/2022, de 3 de mayo, por el que se regula el Esquema Nacional de Seguridad | https://www.boe.es/buscar/act.php?id=BOE-A-2022-7191 |
| BOE-RD-1125-2024 | Real Decreto 1125/2024, de 5 de noviembre (DF2 modifica ENS DA2) | https://www.boe.es/diario_boe/txt.php?id=BOE-A-2024-22889 |
| BOE-LEY-40-2015 | Ley 40/2015, de 1 de octubre, de Régimen Jurídico del Sector Público (Arts. 155-157 ENS) | https://www.boe.es/buscar/act.php?id=BOE-A-2015-10566 |
| BOE-LEY-39-2015 | Ley 39/2015, de 1 de octubre, del Procedimiento Administrativo Común | https://www.boe.es/buscar/act.php?id=BOE-A-2015-10565 |
| BOE-LEY-9-2017 | Ley 9/2017, de 8 de noviembre, de Contratos del Sector Público (cláusulas ENS en pliegos) | https://www.boe.es/buscar/act.php?id=BOE-A-2017-12902 |
| BOE-RGPD | Reglamento (UE) 2016/679 General de Protección de Datos | https://www.boe.es/doue/2016/119/L00001-00088.pdf |
| BOE-LOPDGDD | Ley Orgánica 3/2018 de Protección de Datos Personales y Garantía de Derechos Digitales | https://www.boe.es/buscar/act.php?id=BOE-A-2018-16673 |
| BOE-LEY-11-2022 | Ley General de Telecomunicaciones | https://www.boe.es/buscar/act.php?id=BOE-A-2022-10757 |
| BOE-RDL-12-2018 | RDL 12/2018 sobre seguridad de las redes y sistemas de información (base NIS) | https://www.boe.es/buscar/act.php?id=BOE-A-2018-12257 |
| BOE-LEY-NIS2 | Transposición española NIS2 (verificar estado vigente en abril 2026) | https://www.boe.es (búsqueda dinámica) |
| BOE-LEY-8-2011 | Ley 8/2011 sobre Protección de Infraestructuras Críticas | https://www.boe.es/buscar/act.php?id=BOE-A-2011-7630 |

### H.2 Instrucciones Técnicas de Seguridad (ITS) del CCN (7 documentos) — P0

| Código | Título | Fuente |
|---|---|---|
| ITS-AUDITORIA | ITS de Auditoría de la Seguridad de los sistemas de información | https://ens.ccn.cni.es/es/normativa |
| ITS-CONFORMIDAD | ITS de Conformidad con el ENS | https://ens.ccn.cni.es/es/normativa |
| ITS-INFORME-ESTADO | ITS de Informe del Estado de la Seguridad | https://ens.ccn.cni.es/es/normativa |
| ITS-NOTIFICACION-INCIDENTES | ITS de Notificación de Incidentes de Seguridad | https://ens.ccn.cni.es/es/normativa |
| ITS-REGISTRO-CONFORMIDAD | ITS de Registro de la Conformidad con el ENS | https://ens.ccn.cni.es/es/normativa |
| ITS-ADQUISICION-PRODUCTOS | ITS de Adquisición de Productos de Seguridad y Servicios Cualificados | https://ens.ccn.cni.es/es/normativa |
| ITS-CRIPTOLOGIA | ITS de Criptología de empleo en el ENS | https://ens.ccn.cni.es/es/normativa |

### H.3 Guías CCN-STIC serie 800 (30 documentos) — P0 y P1

| Código | Título | Prioridad |
|---|---|---|
| CCN-STIC-800 | Glosario de términos y abreviaturas del ENS | P1 |
| CCN-STIC-801 | Responsabilidades y funciones en el ENS | P0 |
| CCN-STIC-802 | Auditoría del ENS | P0 |
| CCN-STIC-803 | Valoración de los sistemas | P0 |
| CCN-STIC-804 | Medidas de implantación del ENS (con grados L0-L5) | P0 |
| CCN-STIC-805 | Política de Seguridad de la Información | P0 |
| CCN-STIC-806 | Plan de Adecuación del ENS | P0 |
| CCN-STIC-807 | Criptología de empleo en el ENS | P0 |
| CCN-STIC-808 | Verificación del cumplimiento del ENS (grados L0-L5, requisitos nucleares en gris) | P0 |
| CCN-STIC-809 | Declaración y Certificación de Conformidad con el ENS | P0 |
| CCN-STIC-810 | Guía de creación de CERT | P2 |
| CCN-STIC-811 | Interconexión en el ENS | P1 |
| CCN-STIC-812 | Seguridad en entornos y aplicaciones web | P1 |
| CCN-STIC-813 | Componentes certificados en el ENS | P1 |
| CCN-STIC-814 | Seguridad en correo electrónico | P1 |
| CCN-STIC-815 | Métricas e indicadores en el ENS | P1 |
| CCN-STIC-817 | Gestión de ciberincidentes | P0 |
| CCN-STIC-818 | Herramientas de seguridad | P2 |
| CCN-STIC-819 | Medidas compensatorias | P0 |
| CCN-STIC-820 | Protección contra DoS | P2 |
| CCN-STIC-821 | Normas de seguridad en el ENS | P1 |
| CCN-STIC-822 | Procedimientos de seguridad en el ENS | P1 |
| CCN-STIC-823 | Uso de servicios en la nube | P0 |
| CCN-STIC-824 | Informe del Estado de la Seguridad (alimenta INES) | P0 |
| CCN-STIC-825 | Certificaciones 27001 y ENS | P2 |
| CCN-STIC-826 | Uso seguro del navegador | P2 |
| CCN-STIC-827 | Gestión y uso de dispositivos móviles | P1 |
| CCN-STIC-830 | Ámbito de aplicación del ENS (sector privado) | P0 |
| CCN-STIC-835 | Borrado y destrucción segura de información | P1 |
| CCN-STIC-836 | Seguridad en VPN | P2 |

**URL base CCN-STIC:** https://www.ccn-cert.cni.es/guias/guias-series-ccn-stic.html

### H.4 Perfiles de Cumplimiento Específico (PCE) (5 documentos) — P0 si aplica al cliente

| Código | Título | Aplica |
|---|---|---|
| CCN-STIC-887 | PCE Servicios cloud AWS | Clientes en AWS |
| CCN-STIC-888 | PCE Servicios cloud Azure | Clientes en Azure |
| CCN-STIC-889 | PCE Servicios cloud GCP | Clientes en GCP (si publicado) |
| CCN-STIC-890A | PCE Entidades Locales (ayuntamientos pequeños) | No aplica a privado directamente |
| CCN-STIC-890C | PCE Entidades Locales (ayuntamientos grandes) | No aplica a privado directamente |
| CCN-STIC-891 | PCE Sector Salud | Clientes sanidad privada |
| CCN-STIC-892 | PCE NIS2 | Clientes bajo NIS2 |

### H.5 MAGERIT v3 (4 documentos) — P0

| Código | Título | Fuente |
|---|---|---|
| MAGERIT-V3-LIBRO-I | MAGERIT v3 Libro I – Método | https://administracionelectronica.gob.es/pae_Home/pae_Documentacion/pae_Metodolog/pae_Magerit.html |
| MAGERIT-V3-LIBRO-II | MAGERIT v3 Libro II – Catálogo de elementos | idem |
| MAGERIT-V3-LIBRO-III | MAGERIT v3 Libro III – Técnicas | idem |
| PILAR-MANUAL-USUARIO | Manual de usuario PILAR (última versión) | https://www.ccn-cert.cni.es/herramientas-de-ciberseguridad/ear-pilar.html |

### H.6 Protección de datos — AEPD (9 documentos) — P0

| Código | Título | Fuente |
|---|---|---|
| AEPD-GUIA-RGPD | Guía del RGPD para responsables de tratamiento | https://www.aepd.es/documento/guia-rgpd-para-responsables-de-tratamiento.pdf |
| AEPD-GUIA-BRECHAS | Guía para la notificación de brechas de datos personales | https://www.aepd.es/documento/guia-brechas-seguridad.pdf |
| AEPD-EVALUACION-IMPACTO | Guía práctica para las Evaluaciones de Impacto en la Protección de los Datos | https://www.aepd.es/documento/guia-evaluaciones-impacto-rgpd.pdf |
| AEPD-ESQUEMA-DPD | Esquema de certificación de DPD | https://www.aepd.es/documento/esquema-certificacion-dpd.pdf |
| AEPD-ANALISIS-RIESGOS | Guía práctica de análisis de riesgos en el RGPD | https://www.aepd.es/documento/guia-analisis-de-riesgos-rgpd.pdf |
| AEPD-GESTION-RIESGO-EIPD | Gestión del riesgo y evaluación de impacto | https://www.aepd.es/documento/gestion-riesgo-y-evaluacion-impacto.pdf |
| AEPD-CONTRATO-ENCARGADO | Modelo de cláusulas Art. 28 RGPD | https://www.aepd.es/documento/clausulas-encargados-rgpd.pdf |
| AEPD-DERECHOS | Guía para el ejercicio de derechos | https://www.aepd.es/documento/guia-ejercicio-derechos.pdf |
| AEPD-RAT | Modelo de Registro de Actividades de Tratamiento | https://www.aepd.es/documento/modelo-rat.pdf |

### H.7 Normativa sectorial (8 documentos) — P1 según sector del cliente

| Código | Título | Sector |
|---|---|---|
| EU-DORA | Reglamento DORA (UE) 2022/2554 | Fintech/Financiero |
| EU-NIS2 | Directiva NIS2 (UE) 2022/2555 | Entidades esenciales/importantes |
| EU-AI-ACT | Reglamento IA (UE) 2024/1689 | Desarrolladores/usuarios IA |
| EU-eIDAS2 | Reglamento eIDAS 2 (UE) 2024/1183 | Firma/identificación electrónica |
| EU-CSA | Cybersecurity Act (UE) 2019/881 | Certificación |
| EU-CER | Directiva 2022/2557 sobre Resiliencia de Entidades Críticas | Infraestructuras críticas |
| SEPBLAC-GUIAS | Guías del SEPBLAC sobre prevención blanqueo de capitales | Financiero |
| BDE-CIRCULARES | Circulares del Banco de España sobre ciberresiliencia | Banca |

### H.8 ISO relevantes (6 documentos) — P1

| Código | Título | Licencia |
|---|---|---|
| ISO-27001 | ISO/IEC 27001:2022 SGSI Requirements | Comercial |
| ISO-27002 | ISO/IEC 27002:2022 Information security controls | Comercial |
| ISO-27005 | ISO/IEC 27005 Information security risk management | Comercial |
| ISO-27017 | ISO/IEC 27017 Cloud services information security | Comercial |
| ISO-27018 | ISO/IEC 27018 PII in public clouds | Comercial |
| ISO-22301 | ISO 22301 Business continuity management | Comercial |

**Nota de licencia:** las normas ISO son de pago. La plataforma NO las ingesta directamente. En su lugar, mantiene una tabla de **mapeo ENS ↔ ISO** basada en los cruces públicos del propio CCN (CCN-STIC 825) y los trabajos abiertos. Si Marcos adquiere licencias oficiales, puede ingresar los documentos manualmente con la marca `licensed_content = true` y restricción de uso interno.

### H.9 Catálogos externos (7 documentos/fuentes) — P1

| Código | Tipo | Fuente |
|---|---|---|
| CPSTIC-CATALOGO | Catálogo de Productos y Servicios (CCN-STIC 105) | https://oc.ccn.cni.es/es/ |
| CCN-CERT-FEEDS | Feeds de vulnerabilidades y amenazas del CCN-CERT | https://www.ccn-cert.cni.es/vulnerabilidades.html |
| MITRE-ATTCK | Framework MITRE ATT&CK Enterprise | https://attack.mitre.org/ |
| MITRE-CAPEC | MITRE Common Attack Pattern Enumeration | https://capec.mitre.org/ |
| NVD-CVE | National Vulnerability Database CVE | https://nvd.nist.gov/vuln/data-feeds |
| OWASP-TOP-10 | OWASP Top 10 Web + API | https://owasp.org/www-project-top-ten/ |
| OWASP-ASVS | OWASP Application Security Verification Standard | https://owasp.org/www-project-application-security-verification-standard/ |

### H.10 Plantillas oficiales del CCN (5 documentos) — P0

| Código | Título | Fuente |
|---|---|---|
| CCN-ANEXO-C-805 | Anexo C de la CCN-STIC 805: plantilla de Política de Seguridad | En CCN-STIC 805 |
| CCN-BP14-DdA | Plantilla oficial de Declaración de Aplicabilidad (BP/14) | https://ens.ccn.cni.es |
| CCN-PLAN-ADECUACION | Plantilla de Plan de Adecuación conforme a CCN-STIC 806 | En CCN-STIC 806 |
| CCN-INFORME-AUDITORIA | Plantilla de Informe de Auditoría ENS | En CCN-STIC 802 |
| CCN-DISTINTIVOS | Reglas de uso de los distintivos de conformidad ENS | https://ens.ccn.cni.es/es/conformidad/distintivos |

### H.11 Documentación de herramientas open source del Motor 8 (12 documentos) — P2

Documentación oficial de Nmap, Nuclei, OpenVAS, ZAP, Metasploit, Caldera, Prowler, CLARA, Lynis, Trivy, Semgrep, testssl.sh. Ingesta como referencia técnica para que el Agente 9 pueda consultar sintaxis y capacidades.

### H.12 Artefactos JSON internos (generados por la plataforma) — P0

Estos no se descargan, se generan durante la construcción y forman parte del corpus:

- `ens_measures.json` — las 73 medidas del Anexo II con código, nombre, requisito base, refuerzos, categorías aplicables.
- `ens_reinforcements.json` — los refuerzos R1-R5 con su aplicabilidad.
- `ens_evidence_catalog.json` — las evidencias esperadas por medida (del Apéndice A).
- `obligations_library.json` — las plantillas de obligaciones (del Apéndice B).
- `magerit_catalog.json` — activos, amenazas, salvaguardas de MAGERIT v3.
- `pricing_models.json` — los modelos de precios del Apéndice M.
- `effort_formulas.json` — las fórmulas del Apéndice N.
- `pentest_tool_profiles.json` — perfiles de pipeline del Motor 8.
- `sector_rules.json` — reglas de detección de obligaciones cruzadas del Agente 24.
- `onboarding_templates.json` — las 70 combinaciones sector×rol del Motor 16.

### H.13 Resumen de volumen esperado

Total documentos descargables: **~92 ficheros** (~500-800 MB, la mayoría PDFs).
Total chunks en pgvector tras ingesta: **~25.000-40.000 chunks** de 1000 tokens.
Total nodos en el grafo AGE: **~5.000-10.000** (medidas, refuerzos, amenazas, guías, etc.).
Tiempo de ingesta inicial: **~6-10 horas** con embeddings locales BGE-M3.
Refresh semanal (solo cambios detectados): **~30-60 minutos**.

---

## APÉNDICE I — PROMPTS BASE DE LOS AGENTES 17-26 (AMPLIACIÓN DEL APÉNDICE C)

Prompts operativos de los 10 agentes nuevos introducidos en v2.0. Todos siguen las reglas universales (temperatura ≤ 0.2, citas obligatorias, modo "no encontrado", logging completo).

### I.17 Agente 17 — Cualificador Comercial

```
Eres el Cualificador Comercial de la plataforma ENS de Marcos, consultor autónomo.

Tu misión: analizar un lead entrante y producir un Lead Score (0-100) con
clasificación A/B/C y recomendación de siguiente paso.

Reglas deterministas para el score (aplícalas primero, antes de opinar):
1. Pliego público ya adjudicado con requisito ENS explícito → base 60.
2. Pliego en licitación con ENS exigido → base 45.
3. Exigencia de cliente público recurrente (no pliego concreto) → base 30.
4. Solo exploración, sin pliego ni cliente recurrente → base 10.
5. Bonus por urgencia: +20 si fecha límite < 60 días; +10 si < 120 días.
6. Bonus por sponsor identificado con poder de decisión → +10.
7. Bonus por presupuesto confirmado → +10.
8. Bonus por referencia de cliente existente → +15.
9. Penalización: "están estudiando" sin fecha ni presupuesto → −15.
10. Penalización: han abandonado otro proyecto ENS previo → −10.

Tu aportación LLM: interpretar el contexto libre del lead y ajustar el score
(+/−10 máximo) justificando cada ajuste con evidencia textual del lead.

Output JSON estricto:
{
  "score": int,
  "clasificacion": "A" | "B" | "C",
  "desglose": { "regla": puntos, ... },
  "ajuste_contextual": { "delta": int, "motivo": str },
  "recomendacion": "priorizar" | "reunion_exploratoria" | "educar" | "descartar" | "aparcar",
  "justificacion": str,
  "riesgos_detectados": [str],
  "oportunidades_detectadas": [str]
}

Si no tienes datos suficientes para aplicar una regla, di "no_evaluable" en esa
regla y no inventes. Nunca inventes importes, plazos ni sponsors.
```

### I.18 Agente 18 — Asistente de Reunión Exploratoria

```
Eres el Asistente de Reunión Exploratoria de la plataforma de Marcos.

Contexto: Marcos está manteniendo una reunión exploratoria de 45-60 min con un
lead. Tú le ayudas en tiempo real desde la plantilla bloque A-F (ver F.1).

Tus tareas:
1. Cuando Marcos rellena un campo, validar que es coherente con los campos previos.
2. Al cierre de cada bloque, recalcular los outputs en vivo:
   - categoría ENS preliminar (llamando al Motor 1 con los datos actuales)
   - nivel de madurez L0-L5 global (del Bloque C)
   - estimación preliminar de esfuerzo (llamando al Apéndice N effort_estimator)
   - alcance inicial estimado
   - plazos viables vs deseados
   - riesgos del proyecto detectados (cruzado con el catálogo del Motor 19)
   - quick wins potenciales
3. Detectar inconsistencias ("el cliente dice que no tiene DPO pero trabaja con
   datos de salud") y marcarlas para que Marcos las aclare en la misma reunión.
4. Sugerir preguntas de profundización cuando una respuesta es vaga.
5. Al cierre, generar un resumen de 10-15 líneas que se archivará en
   exploratory_meetings.resumen_final.

NUNCA inventes. Si el cliente no ha dado un dato, di "desconocido" y propón
preguntarlo en el Bloque F (Escucha activa).

Output: streaming de actualizaciones al panel en vivo + al cierre, un JSON
con todos los outputs finales.
```

### I.19 Agente 19 — Redactor de Propuestas Comerciales

```
Eres el Redactor de Propuestas Comerciales de la plataforma de Marcos.

Tu única misión: rellenar la plantilla docxtpl P-001 (ver F.2) con el contexto
del lead y la reunión exploratoria para producir una propuesta formal de 10-20
páginas con estética profesional.

REGLAS INVIOLABLES:
- Los importes económicos NUNCA los generas tú. Vienen del pricing_model
  seleccionado en la tabla pricing_models y aplicado según el Apéndice M.
  Si tienes dudas del importe, llama a la función calcular_pricing() que
  consulta la BBDD.
- Las estimaciones de esfuerzo y duración NUNCA las generas tú. Vienen del
  effort_estimator del Apéndice N.
- Las cláusulas legales del contrato NO son parte de la propuesta; se incluyen
  por referencia.
- El texto narrativo (contexto entendido, metodología, valor diferencial) SÍ lo
  redactas tú, con tono profesional, frases cortas, sin clichés.

Estructura obligatoria (13 secciones + anexos):
1. Portada
2. Resumen ejecutivo
3. Contexto entendido
4. Alcance propuesto
5. Metodología (las 10 fases del ciclo)
6. Fases y cronograma
7. Entregables por fase
8. Equipo
9. Supuestos y exclusiones
10. Condiciones económicas (las rellena calcular_pricing)
11. Criterios de aceptación
12. Gestión de riesgos del proyecto
13. Validez de la oferta

Tono: profesional pero cálido. Marcos es consultor autónomo, no una corporación.
Tuteo al cliente si en la reunión exploratoria se usó tuteo; usted si se usó usted.

Output: fichero DOCX generado con docxtpl + PDF convertido con LibreOffice
headless + metadatos para la tabla proposals.
```

### I.20 Agente 20 — Asistente de Negociación

```
Eres el Asistente de Negociación de la plataforma de Marcos.

Contexto: el cliente ha recibido la propuesta P-001 y tiene objeciones o
pide ajustes. Marcos está en reunión de negociación con él y te consulta
en tiempo real desde la interfaz de F.3.

Tu misión: para cada ajuste pedido, verificar si cae dentro del
pre_authorized_ranges configurado por Marcos y generar una respuesta.

Flujo:
1. Marcos escribe el ajuste pedido por el cliente ("quiere 10% menos",
   "quiere empezar en 2 meses", "no quiere el retainer").
2. Tú consultas pre_authorized_ranges de la tabla del cliente/proyecto.
3. Si el ajuste cae dentro del rango: calculas el impacto en el modelo
   económico, actualizas la propuesta v2 y respondes "aceptable: [detalle]".
4. Si el ajuste cae fuera del rango: respondes "fuera de rango: [diferencia]"
   y sugieres contra-propuestas dentro del rango.
5. Si el ajuste toca una cláusula crítica (recursos del cliente de F.4):
   respondes "NO NEGOCIABLE: [explicación]" y propones mantener la cláusula.

NUNCA aceptes un ajuste fuera de rango por iniciativa propia. Marcos siempre
puede override manualmente, pero tú marcas la excepción y la registras.

Output: JSON por cada ajuste con aceptable/fuera_rango/no_negociable, delta
económico, propuesta alternativa, y notas para la acta de negociación.
```

### I.21 Agente 21 — Detector de Discrepancias (Dirección vs TI)

```
Eres el Detector de Discrepancias de la plataforma de Marcos.

Tu trabajo: comparar las notas de la reunión de scoping con dirección
(scoping_direccion) contra las notas de la reunión de scoping con TI
(scoping_ti) del mismo cliente, y detectar contradicciones.

Dimensiones a cruzar:
- Presupuesto declarado vs presupuesto real disponible
- Plazos deseados vs plazos técnicamente viables
- Madurez percibida vs madurez técnica real
- Personal disponible vs personal necesario
- Herramientas declaradas vs herramientas realmente en uso
- Sponsorship declarado vs compromiso real del sponsor
- Conocimiento de ENS declarado vs conocimiento real

Para cada discrepancia detectada:
- severidad: baja/media/alta/crítica
- contexto: cita literal de ambas fuentes
- impacto potencial en el proyecto
- recomendación de resolución (reunión de triangulación, escalado, cambio
  de alcance)

Notas confidenciales: si una de las partes hizo un comentario confidencial
que contradice algo oficial, lo marcas como confidential:true y solo Marcos
lo ve. No se expone al cliente.

Output: lista de discrepancias priorizada por severidad.
```

### I.22 Agente 22 — Analista de Stakeholders

```
Eres el Analista de Stakeholders de la plataforma de Marcos.

Tu trabajo: construir y mantener el mapa de stakeholders del cliente en
formato grafo (Apache AGE).

Fuentes de información:
- Onboarding del sponsor (nombres, cargos, relaciones reportadas)
- Reunión exploratoria (Bloque D – organización interna)
- Scoping con dirección y con TI
- Notas confidenciales de Marcos
- Conectores: M365 Entra ID, Google Workspace, AD (organigrama implícito)
- LinkedIn scraping autorizado (solo cargos públicos)

Tipos de nodo:
- Person(nombre, cargo, departamento, email, tenure, estado_personal)

Tipos de arista:
- REPORTS_TO (jerárquica)
- ALLIES_WITH (alianza política interna)
- CONFLICTS_WITH (conflicto activo)
- BLOCKS (poder de veto informal sobre el proyecto)
- SPONSORS (sponsor del proyecto)
- NEW_HIRE (< 6 meses en la empresa)
- LEAVING_SOON (avisado, en proceso de salida)
- BURNOUT_RISK (señales de agotamiento)

Política de notas confidenciales: CUALQUIER observación sobre estado personal,
burnout, salida inminente, conflictos interpersonales o evaluaciones
subjetivas se almacena en confidential_notes con visible_solo_marcos = true.
NUNCA expones estos datos al cliente, al auditor, ni a otros agentes salvo
que Marcos los active explícitamente.

Output: nodos y aristas en la BBDD + visualización d3.js + lista de
stakeholders críticos para el proyecto.
```

### I.23 Agente 23 — Mapeador de Procesos de Negocio

```
Eres el Mapeador de Procesos de Negocio de la plataforma de Marcos.

Tu trabajo: identificar y modelar los procesos de negocio críticos del cliente
para alimentar el BIA de la Fase 2 y el análisis de riesgos.

Fuentes:
- Entrevistas guiadas (te proporciono transcripción o notas)
- Onboarding del responsable de operaciones
- Inventario de sistemas descubiertos por el Motor 22
- Diagramas de proveedores

Para cada proceso, modelas:
- Nombre y descripción operativa en 2-3 frases
- Responsable ejecutor
- Sistemas que usa (cruzados con discovered_assets)
- Información que toca (tipos, volúmenes, clasificación)
- Criticidad para el negocio: baja, media, alta, crítica
- ¿Es cara al cliente público? (impacto en contratos)
- Estacionalidad si la hay
- Dependencias con otros procesos
- RTO propuesto (tiempo máximo de recuperación)
- RPO propuesto (pérdida máxima de datos aceptable)
- Puntos únicos de fallo (SPOFs) detectados

Genera además un diagrama BPMN simplificado en Mermaid por cada proceso
crítico.

REGLAS:
- Si falta información para modelar un proceso, marcarlo como incompleto
  y sugerir las preguntas específicas a hacer al cliente.
- RTO y RPO son propuestas técnicas; el cliente los valida en la reunión
  de aprobación del BIA.
- NUNCA inventar procesos que no existen en la evidencia.

Output: registros en business_processes + diagramas Mermaid + lista de
gaps de información para cerrar con el cliente.
```

### I.24 Agente 24 — Detector de Obligaciones Cruzadas

```
Eres el Detector de Obligaciones Cruzadas de la plataforma de Marcos.

Tu trabajo: analizar el sector y actividades del cliente para detectar
automáticamente qué normativas aplican además del ENS, y cómo se cruzan
con las medidas del Anexo II para generar palancas de aprovechamiento.

Base de reglas (sector_rules.json):
- Si sector = sanidad → aplica: RGPD, LOPDGDD, CCN-STIC 891, Ley 41/2002
  (autonomía del paciente), normativa AEMPS si dispositivo médico.
- Si sector = financiero → aplica: RGPD, DORA, Banco de España circulares,
  SEPBLAC, Ley 10/2010 blanqueo.
- Si procesa tarjetas → aplica: PCI-DSS v4.
- Si es TPP/PISP → aplica: PSD2.
- Si tiene infraestructura crítica → aplica: Ley 8/2011 PIC.
- Si entidad esencial/importante → aplica: NIS2.
- Si desarrolla IA → aplica: EU AI Act (con clasificación de riesgo).
- Si usa cloud → aplica: CCN-STIC 823 + PCE cloud correspondiente.
- Si < 50 empleados y no cumple umbrales → algunas obligaciones no aplican.

Para cada obligación detectada:
- Base normativa (con cita exacta)
- Aplicabilidad al cliente con justificación
- Estado de cumplimiento estimado según diagnóstico
- Cruce con medidas ENS aplicables (ej: RGPD art. 32 ↔ mp.info.1, op.exp.7)
- Prioridad de abordaje
- Responsable propuesto
- Palancas de aprovechamiento: "si cumple RGPD, 40% del trabajo del ENS
  ya está hecho en estas medidas [lista]"

REGLAS:
- NUNCA afirmar que una normativa aplica sin citar la base regulatoria
  exacta.
- Si el sector del cliente no está en sector_rules.json, devolver
  "sector no cubierto" y sugerir análisis manual.
- Las obligaciones cruzadas se mantienen en legal_obligations y alimentan
  el Plan de Adecuación del Motor 5.

Output: registros en legal_obligations + informe de palancas cross-compliance.
```

### I.25 Agente 25 — Generador de Data Flow Diagrams

```
Eres el Generador de Data Flow Diagrams de la plataforma de Marcos.

Tu trabajo: generar diagramas de flujo de datos (DFD) del cliente a partir
del inventario descubierto por el Motor 22 y el mapa de procesos del Agente
23, para incluirlos en el BIA y en la justificación de medidas del ENS.

Para cada flujo crítico, modelas:
- Fuente de información (externa, interna, generada)
- Procesamiento (sistemas, aplicaciones, personas implicadas)
- Almacenamiento (dónde reside, cifrado, retención)
- Salida (destinatarios, protocolos, exportaciones)
- Actores con permiso en cada fase
- Clasificación de la información en cada punto
- Controles actuales en cada frontera

Notación: DFD nivel 0 (contexto) y nivel 1 (detallado) por proceso crítico.
Formato de salida: SVG generado a partir de Mermaid con estilos limpios
apropiados para informes profesionales.

REGLAS:
- Solo dibujas flujos que existen en evidencia (assets descubiertos +
  procesos mapeados). NUNCA inventas flujos hipotéticos.
- Marcar explícitamente los flujos con datos personales (para RGPD) y
  los flujos que cruzan fronteras de zonas de confianza (para mp.com).
- Los DFD se versionan y regeneran cuando cambia el inventario.

Output: ficheros SVG + código Mermaid + metadatos en data_flow_diagrams.
```

### I.26 Agente 26 — Coach de Auditoría y Crisis

```
Eres el Coach de Auditoría y Crisis de la plataforma de Marcos.

Tienes dos modos de trabajo:

MODO 1: Coaching pre-auditoría
Preparas al personal del cliente (sponsor, RSEG, admin TI, DPO, dirección)
para las entrevistas con el auditor ENAC externo. Para cada rol:
- Generas las 15-25 preguntas tipo que realmente hacen los auditores ENAC
  españoles (extraídas del corpus y del histórico de proyectos anteriores).
- Proporcionas una respuesta modelo "lo que el auditor espera oír".
- IMPORTANTE: la respuesta modelo siempre es honesta. NUNCA sugieres
  respuestas que oculten hechos, minimicen incidentes, o confundan al
  auditor. Si un hecho es negativo, la respuesta modelo lo reconoce con
  contexto y plan de remediación.
- Añades consejos de comunicación: no improvisar, no dar información de
  más, mostrar evidencia en lugar de opinar, admitir lo que no se sabe.
- Rúbrica de autoevaluación de 5 puntos por pregunta.

MODO 2: Simulacro de incidente (tabletop)
Generas un guion de simulacro realista adaptado al sector del cliente:
- Escenario inicial (ransomware, brecha de datos, caída de servicio crítico,
  insider malicioso, ataque a cadena de suministro, etc.)
- Secuencia de eventos con puntos de decisión cada 15-30 minutos
- Actores que participan
- Evidencias que se van "revelando"
- Decisiones que el equipo debe tomar
- Métricas de evaluación: tiempo de detección, tiempo de contención,
  calidad de la comunicación interna, notificación a LUCIA en plazo, etc.

REGLAS UNIVERSALES:
- NUNCA sugerir ocultar hechos o mentir al auditor.
- NUNCA generar escenarios que ridiculicen al personal del cliente.
- Respetar la confidencialidad: no incluir en simulacros datos reales
  del cliente salvo con consentimiento explícito.

Output: guion DOCX + rúbrica XLSX + plan de debrief.
```

---

### I.27 Agente 27 — Document Intelligence Agent (Motor 24)

```
Eres el Document Intelligence Agent de la plataforma FULKRO. Tu función es
analizar cualquier documento que entra en el Motor 24 (gestor documental
inteligente) y producir una ficha estructurada que la plataforma usa para
clasificar, archivar, etiquetar y vincular el documento automáticamente.

ENTRADA:
- Texto completo extraído del documento (del microservicio doc-extractor)
- Metadatos del fichero (nombre original, tamaño, tipo MIME, fecha de subida)
- Contexto del cliente al que pertenece (categoría ENS, sector, NIF,
  inventario de sistemas, listado de proveedores conocidos)
- Listado de tipos de documento del catálogo de FULKRO
- Las 73 medidas del Anexo II con descripción breve

SALIDA (JSON estrictamente conforme al schema):

{
  "document_type": {
    "suggested": "politica_interna | procedimiento | acta_comite | evidencia_tecnica |
                   contrato_proveedor | informe_pentest | informe_auditoria |
                   certificado | factura | email | comunicacion_oficial |
                   registro_operativo | presentacion | otro",
    "confidence": 0.0-1.0,
    "reasoning": "explicación en 1-2 frases"
  },
  "suggested_folder": {
    "virtual_path": "ej: 01_Gobierno/Actas_Comite",
    "confidence": 0.0-1.0
  },
  "suggested_filename": "ej: 2026-07-15_Acta_Comite_Seguridad.pdf",
  "ens_measures_supported": [
    {"measure": "op.acc.5", "confidence": 0.9, "reasoning": "..."},
    {"measure": "op.acc.6", "confidence": 0.85, "reasoning": "..."}
  ],
  "classification_level": "PUBLICO | INTERNO | CONFIDENCIAL | RESTRINGIDO",
  "extracted_metadata": {
    "document_date": "YYYY-MM-DD o null",
    "signers": ["nombre 1", "nombre 2"],
    "referenced_systems": ["nombre sistema 1"],
    "referenced_vendors": ["proveedor 1"],
    "amounts_mentioned": [{"value": 12000, "currency": "EUR"}],
    "key_entities": ["entidades nombradas relevantes"]
  },
  "quality_flags": {
    "is_signed": true/false,
    "is_complete": true/false,
    "is_legible": true/false,
    "has_sensitive_info": true/false,
    "suspected_duplicate": true/false,
    "needs_human_review": true/false,
    "warnings": ["avisos al usuario"]
  },
  "semantic_summary": "Resumen en 2-3 frases de qué es el documento y para qué sirve"
}

REGLAS NO NEGOCIABLES:
1. Si el documento está en un idioma distinto del español, añade warning pero
   no rechaces: la plataforma soporta documentación en inglés (ingles técnico)
   y catalán/valenciano.
2. NUNCA asumas medidas ENS que el documento no soporte claramente. Prefiere
   poca cobertura con alta confianza a muchas medidas con baja confianza.
3. Si el documento parece ser un certificado digital, factura electrónica o
   documento firmado con firma cualificada, márcalo siempre en is_signed=true
   y eleva la confidencialidad.
4. Si detectas información de categorías especiales del Art. 9 RGPD (salud,
   biometría, origen étnico, etc.), marca needs_human_review=true y
   classification_level mínimo CONFIDENCIAL.
5. Si el documento parece ser una evidencia de control técnico (captura,
   export de configuración, log), etiqueta con la medida correspondiente
   basándote en el control que muestra.
6. Si no estás seguro del tipo, document_type=otro y needs_human_review=true.
   No inventes.
7. El semantic_summary debe ser factual, no promocional. "Acta del Comité
   de Seguridad del 15 de julio de 2026 con 5 acuerdos sobre la revisión
   de la DdA y aprobación del plan de formación 2027" es correcto.
   "Importante documento sobre seguridad" NO es correcto.

CITA:
No necesitas citar fuentes oficiales salvo cuando el documento hace
referencia a artículos del RD 311/2022 o a medidas concretas: entonces
verifica que la medida existe y cítala correctamente.

MODELO: Claude Haiku 4.5 (barato, rápido, suficiente).
TEMPERATURA: 0.1 (determinista).
COSTE MEDIO POR DOCUMENTO: 0.002-0.005 €.
```

---

## APÉNDICE J — ESQUEMAS DETALLADOS DE LAS TABLAS SQL NUEVAS

(Ver las definiciones DDL en la Parte 4.3 — "NUEVAS TABLAS v2.0/v2.1". Este apéndice añade observaciones de diseño.)

### J.1 Convenciones

- Todas las tablas tienen: `id UUID PK`, `created_at TIMESTAMPTZ`, `updated_at TIMESTAMPTZ`, `deleted_at TIMESTAMPTZ NULL` (soft delete).
- Columnas `*_jsonb` son JSONB con esquema validado por CHECK o por la capa de aplicación con Pydantic.
- Toda tabla con `project_id` lleva RLS habilitado con policy `project_isolation`.
- Toda tabla con datos sensibles (`confidential_notes`, `stakeholders_graph_nodes`, `discovered_identities`) lleva cifrado columnar con `pgcrypto` para las columnas con PII.

### J.2 Relaciones principales

```
clients 1 — N leads 1 — 1 exploratory_meetings
leads 1 — N proposals 1 — N negotiation_meetings
leads 1 — 1 contracts 1 — N client_commitments
contracts 1 — N invoices 1 — N invoice_lines
contracts 1 — N payment_reminders

projects 1 — N onboarding_sessions 1 — N discovered_assets
projects 1 — N discovered_identities
projects 1 — N discovered_configurations
projects 1 — N discovered_data_stores
projects 1 — 1 logging_capability_assessment
projects 1 — N data_flow_diagrams

projects 1 — N business_processes
projects 1 — N stakeholders_graph_nodes N — N stakeholders_graph_edges
projects 1 — N legal_obligations
projects 1 — N client_projects_in_flight
projects 1 — N confidential_notes

projects 1 — 1 project_plans 1 — N wbs_tasks
projects 1 — N change_requests
projects 1 — N project_risks
projects 1 — 1 communication_plans 1 — N status_reports

projects 1 — 1 collaborative_workspaces 1 — N workspace_files
collaborative_workspaces 1 — N videocall_sessions
collaborative_workspaces 1 — N workspace_feed_items
collaborative_workspaces 1 — N workspace_chat_messages

clients 1 — N retainer_contracts 1 — N retainer_activities
retainer_dashboards_snapshots (snapshots globales periódicos)
```

### J.3 Índices críticos

- `leads(estado, lead_score DESC)` para dashboard comercial
- `proposals(lead_id, version DESC)` para histórico
- `invoices(estado_pago, fecha_vencimiento)` para dashboard tesorería
- `discovered_assets(project_id, tipo_magerit)` para import al Motor 2
- `project_risks(project_id, status, probabilidad DESC)` para dashboard riesgos
- `wbs_tasks(project_plan_id, status, start_date)` para Gantt
- `retainer_activities(retainer_contract_id, fecha_programada)` para scheduler

### J.4 Triggers

- `updated_at` auto-update en todas las tablas vía trigger genérico.
- `audit_log` trigger en todas las tablas principales para trazabilidad.
- `client_commitments`: trigger que detecta incumplimiento y crea `paron` automáticamente.
- `invoices`: trigger que encola recordatorios automáticos en `payment_reminders` según fecha_vencimiento.
- `project_risks`: trigger que dispara contingencia cuando `status` pasa a `materializado`.

---

## APÉNDICE K — PANTALLAS MAESTRAS DE LA UI DE MARCOS

Marcos no debería diseñar UX a mano. Estas son las 6 pantallas principales que la plataforma le debe servir, con contenido y acciones específicas.

### K.1 Dashboard principal (pantalla de aterrizaje)

**Distribución en grid:**
- Cabecera: nombre de Marcos, reloj, botón de notificaciones, botón de salir.
- Fila 1 — KPIs de 4 columnas:
  - Proyectos activos (número + semáforo RAG agregado)
  - Leads en pipeline (número + valor potencial en €)
  - Retainers activos (número + MRR en €)
  - Tesorería prevista 30 días (€)
- Fila 2 — 3 columnas:
  - **Mi día hoy**: lista de acciones que requieren Marcos (revisión de N documentos, aprobación de N evidencias, N reuniones hoy, N magic links respondidos esperando revisión).
  - **Alertas críticas**: riesgos materializados, incumplimientos de cliente, retrasos vs línea base, plazos de auditoría acercándose.
  - **Últimas actividades de la plataforma**: feed de lo que la plataforma ha hecho autónomamente (documentos generados, scans completados, vigilancia normativa, etc.).
- Fila 3 — Acceso rápido: botones grandes "Nuevo lead", "Nuevo proyecto", "Reunión exploratoria", "Generar propuesta", "Consola de retainer".

### K.2 Pipeline comercial (vista kanban de leads)

Columnas: `nuevo | cualificando | reunion_exploratoria | propuesta_enviada | negociacion | cerrado_ganado | cerrado_perdido | en_pausa`.

Cada tarjeta muestra: empresa, lead score, valor estimado, fecha de entrada, última acción, siguiente acción recomendada, avatar del origen (Radar, referencia, frío).

Al pinchar una tarjeta: drawer lateral con el detalle completo del lead, botones para "Analizar pliego", "Programar reunión exploratoria", "Generar propuesta", "Marcar como perdido" (con motivo obligatorio).

### K.3 Detalle de proyecto (vista unificada)

Tabs horizontales: `Resumen | Diagnóstico | Plan | Implantación | Evidencias | Dossier | Financiero | Comunicación | Riesgos`.

- **Resumen:** estado de las 10 fases, cronograma alto nivel, KPIs del proyecto, mapa de stakeholders versión pública, hitos próximos.
- **Diagnóstico:** resultados de Motor 21 (organizativo) y Motor 22 (técnico), con drill-down.
- **Plan:** Gantt interactivo + WBS + ruta crítica.
- **Implantación:** tablero de obligaciones del Motor 5 con filtros por familia, categoría, responsable, estado.
- **Evidencias:** Evidence Vault con buscador full-text y filtro por medida.
- **Dossier:** preview del dossier final con validación cruzada.
- **Financiero:** contrato, hitos de pago, facturas emitidas, estado de cobro, parones.
- **Comunicación:** histórico de reportes enviados, próximos reportes programados.
- **Riesgos:** dashboard del Motor 19 con los 30 riesgos instanciados.

### K.4 Modo reunión exploratoria en vivo

Pantalla dividida 50/50:
- **Izquierda:** plantilla F.1 con los bloques A-F, campos de notas libres, transcripción en vivo opcional (whisper-local).
- **Derecha:** panel de outputs recalculados en vivo del Agente 18, con semáforos de confianza.
- **Barra inferior:** temporizador de 50 min, progreso de bloques completados, botón "Cerrar reunión → Generar propuesta".

### K.5 Modo auditoría en curso

Pensado para el día D. Interfaz minimalista con:
- **Buscador central gigante**: Marcos escribe lo que el auditor pregunta ("prueba de restauración último mes") y la plataforma devuelve evidencia en 2-3 segundos con preview.
- **Timeline lateral**: registro en tiempo real de cada pregunta del auditor, respuesta dada, evidencia mostrada.
- **Botón rojo de emergencia**: "No tengo evidencia" → abre magic link al cliente para solicitar evidencia express.
- **Cronómetro**: tiempo transcurrido de la sesión de auditoría.
- **Al cierre**: botón "Generar PAC preliminar" que produce el Plan de Acciones Correctivas con todos los hallazgos registrados.

### K.6 Consola de retainer multi-cliente

Vista de dashboard con los 20-40 clientes en retainer. Una tarjeta por cliente con:
- Nombre + sector
- Semáforo RAG general
- Próxima actividad programada (con countdown)
- Últimas 3 alertas relevantes
- MRR del cliente
- Botón "Abrir consola del cliente"

Filtros: por semáforo, por sector, por fecha próxima actividad, por estado de cobro.

Vista agregada: "Mes actual — N actividades programadas, N horas estimadas, N € a facturar".

### K.7 Gestor documental inteligente (Motor 24)

**Pantalla dedicada al IDMS, accesible desde el dashboard del cliente o como vista global multi-cliente.**

**Layout de 3 paneles:**

- **Panel izquierdo (250px)** — Árbol de carpetas:
  - Breadcrumb del cliente activo en la cabecera.
  - Árbol expandible de las 15 carpetas estándar (00_Contractual a 99_Misc) + subcarpetas.
  - Contador de documentos junto a cada carpeta.
  - Indicadores visuales de estado (🟢 todo al día, 🟡 hay docs por vencer, 🔴 hay docs caducados).
  - Iconos para crear carpeta nueva, subir archivo al nodo seleccionado, importar carpeta completa.

- **Panel central (fluido)** — Lista de documentos de la carpeta activa:
  - Vista tabla con columnas: nombre, tipo (icono), tamaño, última modificación, estado de firma, etiquetas ENS, confidencialidad.
  - Vista opcional en miniaturas (tiles) con preview visual.
  - Selección múltiple para acciones en lote.
  - Drag & drop directo desde el escritorio a cualquier carpeta o al panel central.
  - Al arrastrar, **overlay grande** con indicación visual: "Soltar para subir y clasificar automáticamente".
  - Filtros rápidos en barra superior: todos, firmados, pendientes, por vencer, caducados.
  - Buscador local de la carpeta.

- **Panel derecho (400px)** — Detalle del documento seleccionado:
  - Preview embebido (PDF.js para PDFs, visor para imágenes, descarga para otros).
  - Ficha con todos los metadatos extraídos.
  - Tabla de versiones (con diff entre versiones para documentos de texto).
  - Historial de firmas con timestamp y firmantes.
  - Etiquetas ENS asignadas (editables por Marcos).
  - Enlaces bidireccionales: "este documento soporta 3 medidas, 1 control, 2 procedimientos".
  - Acciones: renombrar, mover, versionar, firmar, archivar, eliminar (con confirmación).
  - Botón "Preguntar al Copiloto sobre este documento".

**Barra superior global:**
- **Buscador híbrido** (siempre visible, también con atajo Cmd+F): escribe y busca en todo el Vault del cliente (léxico + semántico). Resultados con snippets destacados y puntuación de relevancia.
- Selector de vista: árbol, lista plana, línea temporal, por medida ENS.
- Indicador de progreso cuando hay procesamientos en curso (subidas masivas, extracción de texto, generación de embeddings).

**Modo "Sesión de subida masiva":**
Cuando Marcos arrastra 20+ ficheros a la vez (por ejemplo, cuando el cliente le entrega una carpeta con toda su documentación histórica), se activa un modo especial:
- Barra de progreso con estadísticas en vivo: "procesando 47 de 120 ficheros".
- Clasificación automática en segundo plano con el Agente 27.
- Al finalizar, pantalla de revisión: "Se han clasificado 120 documentos en 8 carpetas sugeridas, 97 con alta confianza (verde), 18 con confianza media (ámbar), 5 requieren revisión humana (rojo). Revisar → aprobar lote → archivar en destinos sugeridos".
- Marcos puede reclasificar arrastrando entre carpetas en la propia pantalla de revisión.

**Modo "Búsqueda global":**
Activado con Cmd+K desde cualquier pantalla. Modal overlay con:
- Input gigante.
- Resultados en vivo mientras escribe: documentos, clientes, proyectos, páginas de la plataforma.
- Filtros rápidos por tipo de resultado.
- Navegación con teclado (↑↓ y Enter).
- Historial de búsquedas recientes.

### K.8 Dashboard multi-cliente y switch rápido

**Sidebar permanente** (disponible en cualquier pantalla de la plataforma, colapsable con Cmd+B):

```
┌──────────────────────────────┐
│ 🏢 FULKRO                    │
├──────────────────────────────┤
│ 🏠 Dashboard global          │
│ 📈 Pipeline comercial        │
│ 📅 Calendario                │
│ 💰 Financiero                │
│ 📁 Gestor documental         │
│ ⚙️ Operaciones               │
├──────────────────────────────┤
│ CLIENTES ACTIVOS             │
│ 🟢 Soluciones Digitales Lev. │
│ 🟢 Innovatech Burgos         │
│ 🟡 DataForma Galicia         │
│ 🟢 Consultora Moderna SL     │
│ 🟢 Ayuntamiento Valencia... │
│ ...                          │
│                              │
│ CLIENTES EN RETAINER         │
│ 🟢 Cliente A                 │
│ 🟢 Cliente B                 │
│ 🟠 Cliente C                 │
│ ...                          │
├──────────────────────────────┤
│ ⚪ Archivables (3)           │
│ 📦 Archivados (12)           │
├──────────────────────────────┤
│ [🔍 Cmd+K · buscar]          │
└──────────────────────────────┘
```

**Al hacer clic en un cliente**, se carga el **Dashboard específico del cliente** (K.8.a):

- **Cabecera del cliente**: logo, nombre, NIF, fase actual del proyecto, próximo hito con countdown.
- **KPIs del cliente**: progreso de la fase actual (%), documentos firmados / totales, evidencias recopiladas / necesarias, riesgos abiertos, tesorería pendiente.
- **Widgets personalizables**: Marcos puede añadir widgets que le interesen para ese cliente concreto.
- **Timeline del cliente**: eventos clave en línea del tiempo (firma de contrato, hitos completados, reuniones del comité, incidentes).
- **Acceso rápido a las pestañas del proyecto** (las mismas de K.3).

**Switch rápido con Cmd+K:**

Al pulsar Cmd+K en cualquier momento, overlay con:
```
┌─────────────────────────────────────┐
│ Ir a...                             │
├─────────────────────────────────────┤
│ 🔍 _________________________________│
│                                     │
│ ▸ Clientes                          │
│   Soluciones Digitales Levante      │
│   Innovatech Burgos                 │
│                                     │
│ ▸ Acciones                          │
│   Nuevo lead                        │
│   Nueva reunión exploratoria        │
│                                     │
│ ▸ Navegación                        │
│   Dashboard global                  │
│   Gestor documental                 │
│   Operaciones > Backups             │
└─────────────────────────────────────┘
```

Fuzzy finder estilo Raycast. Dos teclas y estás donde quieres.

**URL amigable por cliente:**
- `fulkro.es/clients/sdl/dashboard`
- `fulkro.es/clients/sdl/documents`
- `fulkro.es/clients/sdl/dossier`
- `fulkro.es/clients/sdl/financial`
- Cada URL es compartible internamente (con Marcos como único autorizado a abrirla tras re-autenticación WebAuthn).

**Acción "Exportar todo el proyecto":**
Disponible en el menú de acciones del cliente. Dispara el flujo de Motor 25 (export puntual sin archivar). Genera el ZIP completo firmado y lo deja disponible para descarga inmediata.

**Acción "Archivar proyecto":**
Disponible solo para proyectos en estado CERTIFIED que llevan > 30 días sin actividad o cuyo retainer ha terminado. Abre el wizard de 5 pasos del Motor 25. Tras confirmación final, ejecuta el archivado completo.

### K.9 Consola de operaciones: backups y dogfooding

**Pantalla global de la salud de la plataforma (solo accesible por Marcos con re-autenticación WebAuthn).**

**Secciones:**

- **Backups (Motor 26):** el panel descrito en §26.3 con PostgreSQL, MinIO, configuración, logs inmutables, DR drills. Botones para ejecutar backups manuales, probar restores, iniciar ejercicios DR.

- **Dogfooding ENS:** estado del SGSI de la propia plataforma. Su propia DdA, sus propias evidencias, su propia auditoría interna. La plataforma aplica Motor 9 sobre sí misma.

- **Integridad:** últimas verificaciones de hash de MinIO, cadena de audit_log, firmas Ed25519 de documentos. Alertas si algo falla.

- **Rendimiento:** latencia API, uso de CPU/RAM del servidor Hetzner, espacio en disco, uso de BD, colas Celery.

- **Scans de vulnerabilidades propios:** últimos resultados de Trivy/Nuclei/OpenVAS/Lynis sobre la propia plataforma.

- **Proyectos archivables:** lista de proyectos candidatos al archivado automático (sin actividad > 12 meses en estado ENDED).

- **Histórico de incidentes de la plataforma:** registro de cualquier downtime, incident, alerta.

---

## APÉNDICE L — RIESGOS DE CONSTRUCCIÓN DE LA PLATAFORMA

Riesgos específicos del proyecto de construir esta plataforma (no confundir con los riesgos del Motor 19, que son de los proyectos consultor).

### L.1 Plantillas DOCX no auto-generables (riesgo CRÍTICO)

**Descripción:** las 110 plantillas DOCX del Motor 6 requieren redacción legal real que Claude Code no puede producir con la calidad exigida por un auditor ENAC veterano. Estimación: 140-270 horas de trabajo humano especializado.

**Impacto:** sin plantillas reales, la plataforma es una maqueta vacía. No se puede lanzar al primer cliente real.

**Mitigación:**
1. Contratar consultor ENS senior por 2-3 semanas al 50% de dedicación (~6.000 €).
2. Contratar abogado TIC español por 20-30 horas (~3.000 €).
3. Marcos dedicar 60-80 horas propias de revisión y adaptación.
4. Priorizar las 20 plantillas más usadas: E-001, E-002, E-005, E-012, E-040, E-050, E-100, E-101, E-102, E-107, E-108, E-126, E-200, E-204, E-210, E-218, E-400, E-500, E-702, C-001. Estas cubren el 80% de los casos.
5. El resto de plantillas se desarrollan incrementalmente contra los primeros clientes reales.

**Semanas del plan afectadas:** 9-15. Paralelo al desarrollo técnico del Motor 6.

### L.2 Integraciones CCN sin API (riesgo ALTO)

**Descripción:** PILAR, LUCIA e INES no tienen APIs públicas modernas. Las integraciones son por ficheros y carga manual asistida.

**Mitigación:**
- Asumir ingesta/generación de ficheros como único modo viable en v1.
- Documentar claramente a Marcos el flujo "genera fichero → sube manualmente con certificado".
- Vigilar trimestralmente si el CCN publica APIs nuevas.

### L.3 Pentesting Engine ambicioso (riesgo MEDIO)

**Descripción:** 11 herramientas open source orquestadas es mucho. Riesgo de bloquearse en la integración de una herramienta concreta.

**Mitigación:**
- Empezar con 5 herramientas esenciales: Nmap, Nuclei, OpenVAS, ZAP, Prowler.
- Añadir las otras 6 incrementalmente (CLARA, Lynis, Trivy, Semgrep, Metasploit, Caldera).
- Aislamiento absoluto en red Docker dedicada para limitar radio de bugs.

### L.4 LLM: sobre-coste por tokens (riesgo MEDIO)

**Descripción:** el uso intensivo de Opus 4 para redacción puede disparar el presupuesto mensual de API (Marcos estimó 120-200 €/mes total de infra).

**Mitigación:**
- Usar Sonnet 4.5 por defecto, Opus 4 solo para tareas que lo justifiquen (redacción crítica de políticas, informes de pentest, coaching de auditoría).
- Usar Haiku 4.5 para clasificación masiva y parsing estructurado.
- Cachear respuestas de corpus RAG en Redis con TTL largo.
- Logging estricto de coste por llamada, alerta si supera umbral mensual.

### L.5 Plantillas DOCX vs ediciones manuales (riesgo MEDIO)

**Descripción:** cuando Marcos o el cliente editan manualmente un DOCX generado, la edición se pierde si se regenera la plantilla.

**Mitigación:**
- Cada generación crea una `document_versions` nueva, preservando histórico.
- Bloqueo opcional de versiones firmadas: tras firmar, no se regenera, solo se crea una versión nueva.
- Sistema de merge asistido (comparativa visual con docx-diff) si hay conflictos.

### L.6 Dependencia de un solo servidor Hetzner (riesgo BAJO)

**Descripción:** toda la plataforma en un CCX33 sin redundancia. Si cae el servidor, cae todo.

**Mitigación:**
- Backups diarios a Hetzner Object Storage cifrado.
- Snapshots cada 24h.
- Procedimiento Terraform + Ansible para levantar nuevo servidor en < 4 horas.
- RTO 4h, RPO 24h son aceptables para el tamaño del negocio.

### L.7 Corpus normativo: cambios en fuentes CCN (riesgo BAJO-MEDIO)

**Descripción:** si el CCN reestructura URLs o cambia formato de publicación, los scripts de ingesta dejan de funcionar.

**Mitigación:**
- Monitorización semanal del estado de las URLs del Apéndice H.
- Alerta automática si un documento devuelve 404.
- Intervención manual rápida para adaptar scraper.

### L.8 Dogfooding ENS Medio sobre sí misma (riesgo BAJO)

**Descripción:** la plataforma debe cumplir ENS Medio sobre sí misma. Esto añade trabajo.

**Mitigación:**
- Usar la propia plataforma para gestionar su propio cumplimiento (meta).
- Semanas 37-38 del plan dedicadas a esto.
- Documentación interna como "cliente 0".

---

## APÉNDICE M — BIBLIOTECA PRECARGADA DE PRICING MODELS

9 modelos económicos para que el Motor 13 calcule propuestas en segundos sin que Marcos tenga que hacer cálculos a mano. Todos almacenados en la tabla `pricing_models`.

### M.1 Modelo BÁSICA-FIJO

```yaml
id: basica_fijo
nombre: "Básica — Precio fijo chavchav"
descripcion: "Para clientes en categoría Básica que quieren simplicidad"
aplicable_categoria: [BASICA]
formula:
  base: 6500
  por_empleado_extra_de_10: 80
  por_sistema_extra_de_2: 600
rango_precio_min: 6500
rango_precio_max: 14000
hitos_pago:
  - anticipo: 30
  - mitad_proyecto: 40
  - cierre: 30
duracion_tipica_semanas: 16-20
```

### M.2 Modelo MEDIA-HITOS

```yaml
id: media_hitos
nombre: "Media — Por hitos"
descripcion: "El modelo más usado, para la mayoría de clientes Media"
aplicable_categoria: [MEDIA]
formula:
  base: 22000
  por_empleado_extra_de_25: 150
  por_sistema_extra_de_3: 1200
  por_ubicacion_extra: 1800
  por_sector_regulado_extra: 3000  # sanidad, financiero, etc.
rango_precio_min: 22000
rango_precio_max: 55000
hitos_pago:
  - firma: 20
  - diagnostico_completado: 15
  - diseno_sgsi_aprobado: 20
  - implantacion_70_percent: 25
  - dossier_entregado_auditor: 15
  - certificacion_obtenida: 5
duracion_tipica_semanas: 32-40
```

### M.3 Modelo ALTA-FASES-EXITO

```yaml
id: alta_fases_exito
nombre: "Alta — Fases + bonus éxito"
descripcion: "Para proyectos Alta con bonus por certificación en plazo"
aplicable_categoria: [ALTA]
formula:
  base: 48000
  por_empleado_extra_de_50: 180
  por_sistema_extra_de_5: 2000
  por_ubicacion_extra: 2500
  por_cpd_extra: 4500
  bonus_exito: 8000  # si certifica en plazo y sin NC mayores
rango_precio_min: 48000
rango_precio_max: 140000
hitos_pago:
  - firma: 15
  - diagnostico_completado: 10
  - diseno_sgsi_aprobado: 15
  - implantacion_50_percent: 15
  - implantacion_90_percent: 15
  - dossier_entregado_auditor: 15
  - certificacion_obtenida: 10
  - bonus_exito: 5
duracion_tipica_semanas: 48-72
```

### M.4 Modelo RETAINER-BASICO

```yaml
id: retainer_basico
nombre: "Retainer Básico post-certificación"
aplicable_categoria: [BASICA, MEDIA]
modalidad: recurrente_mensual
precio_mensual_min: 200
precio_mensual_max: 400
incluye:
  - vigilancia_normativa
  - comite_trimestral
  - reporting_trimestral
  - auditoria_interna_anual
excluye:
  - incidentes_ad_hoc
  - recertificacion (facturar aparte)
```

### M.5 Modelo RETAINER-MEDIO

```yaml
id: retainer_medio
nombre: "Retainer Medio post-certificación"
aplicable_categoria: [MEDIA, ALTA]
modalidad: recurrente_mensual
precio_mensual_min: 500
precio_mensual_max: 1200
incluye:
  - todo_basico
  - comite_mensual
  - simulacros_phishing_trimestrales
  - gestion_cambios_significativos
  - respuesta_incidentes_sla_24h
excluye:
  - red_team_formal (facturar aparte)
```

### M.6 Modelo RETAINER-ALTO

```yaml
id: retainer_alto
nombre: "Retainer Alto post-certificación"
aplicable_categoria: [ALTA]
modalidad: recurrente_mensual
precio_mensual_min: 1500
precio_mensual_max: 3500
incluye:
  - todo_medio
  - red_team_anual
  - pentest_trimestral
  - respuesta_incidentes_sla_4h
  - soporte_24_7
```

### M.7 Modelo URGENCIA

```yaml
id: urgencia
nombre: "Urgencia — plazo < 90 días"
descripcion: "Recargo por plazos ajustados (el cliente trae un pliego con fecha imposible)"
aplicable_categoria: [BASICA, MEDIA, ALTA]
formula:
  recargo_base_percent: 30  # sobre el modelo correspondiente
  plazos_recalculados: true
condiciones:
  - plazo_objetivo_dias < 90
hitos_pago: iguales al modelo base, pero con fechas comprimidas
```

### M.8 Modelo AUDITORIA-INDEPENDIENTE

```yaml
id: auditoria_independiente
nombre: "Solo auditoría interna (sin implantación)"
descripcion: "Cliente ya implantó ENS con otro consultor y quiere auditoría interna independiente"
aplicable_categoria: [BASICA, MEDIA, ALTA]
formula:
  basica: 3500
  media: 8500
  alta: 15000
duracion_tipica_semanas: 3-6
hitos_pago:
  - firma: 50
  - entrega_informe: 50
```

### M.9 Modelo CONSULTING-HORAS

```yaml
id: consulting_horas
nombre: "Bolsa de horas de consultoría ENS"
descripcion: "Para clientes que necesitan soporte puntual"
aplicable_categoria: [BASICA, MEDIA, ALTA]
formula:
  precio_hora_basica: 85
  precio_hora_media: 105
  precio_hora_alta: 125
  bolsa_minima_horas: 20
  descuento_bolsa_50h: 10  # percent
  descuento_bolsa_100h: 15
```

---

## APÉNDICE N — EFFORT ESTIMATOR CALIBRADO

Fórmulas deterministas que usa el Motor 17 para estimar esfuerzo sin alucinar. Almacenadas en `effort_formulas.json`.

### N.1 Fórmula general

```
horas_marcos = horas_base(categoria) × factor_tamaño × factor_madurez × factor_sector × factor_complejidad_tecnica
```

### N.2 Horas base por categoría

| Categoría | horas_base (horas de Marcos para proyecto completo) |
|---|---|
| Básica | 60 |
| Media | 150 |
| Alta | 230 |

### N.3 Factor tamaño (empleados)

```
< 25 empleados → 0.85
25-100 → 1.00
100-500 → 1.20
500-2000 → 1.50
> 2000 → 1.80
```

### N.4 Factor madurez inicial (estimada en la exploratoria)

```
L0-L1 (muy baja, todo desde cero) → 1.40
L2 (baja, algunas políticas) → 1.20
L3 (media, RGPD ok + políticas básicas) → 1.00
L4 (alta, ISO 27001 equivalente) → 0.75
L5 (muy alta, certificado equivalente) → 0.60
```

### N.5 Factor sector

```
Servicios profesionales → 1.00
SaaS/Tech → 0.95
Industria → 1.10
Retail/ecommerce → 1.05
Logística → 1.05
Educación privada → 1.00
Energía → 1.25
Sanidad privada → 1.30 (carga RGPD extra)
Fintech → 1.35 (carga DORA + PSD2 extra)
Infraestructura crítica → 1.50 (carga PIC + NIS2)
```

### N.6 Factor complejidad técnica

```
Entorno simple (1 cloud, < 5 sistemas, < 3 ubicaciones) → 0.90
Entorno estándar → 1.00
Entorno complejo (multi-cloud, > 20 sistemas, desarrollo interno) → 1.25
Entorno muy complejo (OT, IoT masivo, multi-país, legacy heavy) → 1.50
```

### N.7 Ejemplo de cálculo

Cliente Fintech, 80 empleados, madurez L2, multi-cloud con desarrollo propio, categoría Media:

```
horas_marcos = 150 × 1.00 × 1.20 × 1.35 × 1.25
             = 150 × 2.025
             = 303.75 horas
```

Con tarifa hora de Marcos de 110 €/h → presupuesto sugerido ~33.400 € → el Motor 13 aplica el modelo MEDIA-HITOS y ajusta.

### N.8 Calibración continua

Tras cada proyecto cerrado, Marcos registra las horas reales y el Motor 17 ajusta los factores con una regresión lineal simple para mejorar las estimaciones futuras. Al cabo de 10 proyectos las estimaciones deberían converger a ±15% de error.

---

## APÉNDICE O — GLOSARIO OPERATIVO INTERNO

40 términos propios de la plataforma que Claude Code debe usar con consistencia en código, comentarios, UI y logs.

| Término | Definición |
|---|---|
| Knowledge Graph | Grafo AGE con el corpus ENS modelado (regulación → anexo → marco → familia → medida → refuerzo → evidencia). |
| Project Knowledge Graph | Grafo AGE por proyecto con los datos del cliente (activos, identidades, procesos, stakeholders, obligaciones). |
| Evidence Vault | Almacén inmutable de evidencias con firma Ed25519 y hash chain. |
| Magic Link | JWT efímero firmado Ed25519 + OTP que permite al cliente realizar una operación puntual sin cuenta. |
| Magic Link Persistente del Proyecto | Magic link especial de larga duración que da al cliente acceso al feed del proyecto y solicitud de videollamadas durante toda la vida del proyecto. |
| Modo de Ejecución | Forma en que una obligación se materializa: consultor_genera, cliente_aporta_evidencia, accion_tecnica_remota_autorizada, accion_manual_cliente. |
| Plantilla Inmutable | Plantilla docxtpl o JSON cuyo contenido regulatorio no puede ser modificado por un LLM, solo rellenada en campos marcados. |
| Cláusula Crítica | La cláusula F.4 del contrato sobre recursos del cliente. Es la única cláusula marcada como no_negociable. |
| Dogfooding ENS Medio | Aplicación del ENS Medio a la propia plataforma para poder mostrar certificación propia al cliente. |
| Parón Documentado | Retraso imputable al cliente, formalizado por la plataforma, facturable según la cláusula crítica. |
| Lead Score | Puntuación 0-100 del Agente 17 que clasifica leads en A/B/C. |
| Pricing Model | Uno de los 9 modelos económicos del Apéndice M. |
| Effort Estimator | Fórmula determinista del Apéndice N. |
| Pipeline Comercial | Kanban de leads en la pantalla K.2. |
| Dossier Final | ZIP estructurado de la sección 2.15 que se entrega al auditor. |
| Matriz Cruzada del 99 | Hoja XLSX final del dossier con medida × evidencia × documento. |
| Semáforo RAG | Rojo / Ámbar / Verde de estado de un proyecto o cliente en retainer. |
| Quick Win | Acción de poco esfuerzo e impacto alto que el Agente 16 publica en el feed del cliente para mantener motivación. |
| Feed del Proyecto | Timeline visible al cliente desde su magic link persistente con hitos, documentos pendientes, evidencias pendientes, próximas reuniones. |
| Workspace Efímero | Entorno colaborativo del Motor 20 que dura lo que dura el proyecto + 90 días. |
| Notas Confidenciales | Observaciones subjetivas o políticas internas del cliente que solo Marcos puede ver. Cifradas en BBDD. |
| Grado de Madurez L0-L5 | Niveles de madurez de implantación según CCN-STIC 804/808. |
| Requisito Nuclear | Requisito marcado en gris en la CCN-STIC 808 que siempre se evalúa en la auditoría. |
| Regla del Máximo | Para determinar la categoría del sistema: la más alta de cualquier dimensión de cualquier información o servicio. |
| BIA | Business Impact Analysis del Motor 21 basado en los procesos del Agente 23. |
| DdA | Declaración de Aplicabilidad de las 73 medidas, firmada por el RSEG. |
| PAC | Plan de Acciones Correctivas tras auditoría externa. |
| RSEG | Responsable de la Seguridad (rol obligatorio ENS). |
| NC Mayor / Menor | No Conformidad Mayor o Menor del auditor ENAC. |
| Modo Auditoría en Curso | Pantalla K.5 con buscador instantáneo del Evidence Vault durante el día D. |
| Triangulación | Proceso de Marcos de cruzar lo que dice dirección vs lo que dice TI en scopings separados. |
| Palanca Cross-compliance | Aprovechamiento de controles existentes de otras normativas (RGPD, ISO 27001) para cumplir ENS. |
| Corpus Oficial | Los ~92 documentos del Apéndice H ingestados al Knowledge Graph. |
| Vigilancia Normativa | Monitorización automática del Agente 15 de cambios en el Corpus Oficial. |
| Validación Cruzada | Verificación del Motor 9 de que lo que dice la DdA coincide con lo que hay en el Evidence Vault. |
| Frescura de Evidencia | Cada evidencia tiene fecha_caducidad. Bajo umbral, se re-solicita automáticamente. |
| Pipeline de Pentest | Secuencia orquestada de herramientas del Motor 8 adaptada a la categoría. |
| Modo "No lo sé" | Comportamiento obligatorio de todos los agentes: si no hay evidencia, responder "no encontrado" en lugar de inventar. |
| Cita Obligatoria | Toda afirmación normativa de un agente debe incluir cita al corpus oficial. |
| Temperatura ≤ 0.2 | Parámetro LLM universal para tareas factuales en la plataforma. |

---

**Fin de la Especificación Maestra v2.1 (con apéndices A-O).**

**Marcos:** este es el documento definitivo e integral para entrar en Claude Code. Mételo junto con `ENS_PLATFORM_PARTE_2_ENTREGABLES.md` con esta instrucción:

> *"Construye la plataforma ENS según `ENS_PLATFORM_MASTER_SPEC_v2.1.md` como biblia de arquitectura y ciclo del consultor, y `ENS_PLATFORM_PARTE_2_ENTREGABLES.md` como biblia de entregables auditor. Si hay cualquier discrepancia entre ambos, prevalece la Parte 2 porque está verificada contra CCN-STIC 805/806/808/802 oficiales. Empieza por las semanas 1-2 (Fundamentos). Antes de escribir una sola línea de código, lee el Apéndice H (corpus normativo) y descarga los documentos P0 y P1; lee el Apéndice J para los esquemas SQL nuevos; lee el Apéndice L para entender los riesgos de construcción (en especial las plantillas DOCX no auto-generables). Al terminar cada bloque de semanas, genera un reporte honesto de estado, espera mi confirmación antes de pasar al siguiente bloque. No improvises fuera del scope. Si algo no está claro, pregúntame antes de inventar. Mantén siempre el principio del 95/5: el 95% del trabajo lo hace la plataforma, Marcos solo el 5%. Cualquier agente LLM que uses debe seguir las reglas universales del apéndice C e I: temperatura ≤ 0.2, citas obligatorias, modo 'no encontrado' en lugar de inventar, logging completo de cada llamada."*

Las principales diferencias operativas de v2.1 respecto a v2.0:

1. **Errores verificables corregidos**: conteo op/mp (33+36=69, total 73), numeración 11.1/11.2, clarificación de que el antiguo "Motor Submission" queda como motor futuro sin colisionar con el Motor 24 IDMS, referencias §C obsoletas, conteo 27 políticas.
2. **Apéndice H (nuevo)**: ~92 documentos del corpus normativo con URLs y prioridades para ingesta automática.
3. **Apéndice I (nuevo)**: system prompts completos de los 10 agentes 17-26.
4. **Apéndice J (nuevo)**: esquemas SQL detallados de las 30+ tablas nuevas del ciclo comercial y organizativo.
5. **Apéndice K (nuevo)**: especificación de las 6 pantallas maestras de la UI de Marcos.
6. **Apéndice L (nuevo)**: riesgos de construcción con la advertencia crítica sobre las 110 plantillas DOCX no auto-generables.
7. **Apéndice M (nuevo)**: biblioteca de 9 pricing models precargados para el Motor 13.
8. **Apéndice N (nuevo)**: effort estimator calibrado con fórmulas deterministas.
9. **Apéndice O (nuevo)**: glosario operativo interno de 40 términos.
10. **Ambigüedades cerradas**: rango retainer unificado a 20-40 clientes.

Si detectas algo más al leer, dímelo y hago v2.2. Pero con v2.1 el documento está listo para que Claude Code construya sin preguntas fundamentales.

Lo demás lo construye Claude Code con este documento como única biblia.
