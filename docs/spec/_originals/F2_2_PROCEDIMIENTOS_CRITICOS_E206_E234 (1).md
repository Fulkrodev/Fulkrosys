# F2.2 — PROCEDIMIENTOS CRÍTICOS DEL SGSI ENS — TEXTO OPERATIVO REAL EN ESPAÑOL (E-206 a E-234)

**Plan 100/100 FULKRO — Bloque 4 de plantillas reales**
**Versión:** 1.0 — 9 de abril de 2026
**Continuación de:** F2.1 (procedimientos E-200, E-203, E-204, E-205, E-217, E-218)
**Destinatarios:** Claude Code (para conversión a `.docx` con `docxtpl`) + Marcos

---

## NOTA PRELIMINAR

Este documento completa el bloque procedimental crítico del SGSI. Tras F2.2, los **12 procedimientos operativos críticos** quedan completos, cerrando junto con el bloque F1 (9 políticas) el **núcleo documental SGSI ENS** que cubre aproximadamente el 92% del Anexo II del Real Decreto 311/2022.

Las advertencias legales, el catálogo de placeholders Jinja2 y el flujo de conversión a `.docx` son los mismos que en F1.1, F1.2 y F2.1, y se dan aquí por reproducidos.

---

## CATÁLOGO DE PROCEDIMIENTOS DEL BLOQUE F2.2

| Código | Título | Política madre | Familia ENS principal |
|---|---|---|---|
| E-206 | Procedimiento de Gestión de Cambios | E-100 | op.exp.5 |
| E-207 | Procedimiento de Concienciación y Formación en Seguridad | E-100, E-106 | mp.per.3, mp.per.4 |
| E-210 | Procedimiento de Copias de Seguridad y Restauración | E-104 | mp.info.9 |
| E-219 | Procedimiento de Hardening y Configuración Segura | E-100 | op.exp.2, op.exp.3 |
| E-228 | Procedimiento de Recopilación y Custodia de Evidencias | E-103 | op.exp.8 |
| E-234 | Procedimiento de Auditoría Interna del SGSI | E-100 | Art. 31 ENS |

---

# DOCUMENTO E-206 — PROCEDIMIENTO DE GESTIÓN DE CAMBIOS

**Materializa la medida op.exp.5 del Anexo II del ENS** y el control A.8.32 de ISO/IEC 27001:2022. Es uno de los procedimientos que más impacto tiene en la operación diaria porque cualquier cambio no controlado puede romper la conformidad del sistema o introducir vulnerabilidades.

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-206"
titulo: "Procedimiento de Gestión de Cambios"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
fecha_proxima_revision: "{{ proyecto.proxima_revision }}"
clasificacion: "INTERNA"
propietario: "{{ responsables.responsable_seguridad.cargo }}"
politica_madre: "{{ proyecto.codigo_documento_base }}-100"
---

# PROCEDIMIENTO DE GESTIÓN DE CAMBIOS DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-206 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Establecer el método mediante el cual {{ cliente.razon_social }} planifica, evalúa, autoriza, ejecuta y verifica los cambios que afectan a los sistemas de información comprendidos en el alcance del SGSI, garantizando que ningún cambio se introduzca en producción sin haber sido evaluado en términos de seguridad, estabilidad y reversibilidad, en cumplimiento de la medida **op.exp.5 (Gestión de cambios)** del Anexo II del Real Decreto 311/2022.

## 2. ALCANCE

Aplica a todo cambio que afecte a:

a) Hardware y software de los sistemas productivos.
b) Configuraciones de seguridad de cualquier elemento del sistema.
c) Arquitectura de red, reglas de cortafuegos y políticas de enrutamiento.
d) Aplicaciones, librerías, dependencias y servicios externos integrados.
e) Procedimientos operativos, normas internas y políticas del SGSI.
f) Estructura organizativa relacionada con la operación del sistema.

Quedan **expresamente excluidos** del alcance del presente procedimiento los cambios menores que cumplan acumulativamente los siguientes criterios: (a) están preautorizados como cambios estándar conforme al apartado 6, (b) no afectan a controles de seguridad y (c) son reversibles trivialmente.

## 3. DEFINICIONES OPERATIVAS

a) **Cambio estándar:** cambio repetitivo, de bajo riesgo, preautorizado y documentado en el catálogo de cambios estándar.

b) **Cambio normal:** cambio no incluido en el catálogo estándar, que requiere análisis y autorización individual.

c) **Cambio de emergencia:** cambio que debe implementarse con la mayor brevedad para resolver un incidente, mitigar una vulnerabilidad crítica o restablecer un servicio caído.

d) **Comité de Cambios (CAB, Change Advisory Board):** órgano colegiado responsable de la evaluación y autorización de los cambios normales de impacto medio o alto.

## 4. CLASIFICACIÓN DE LOS CAMBIOS POR IMPACTO

| Nivel | Descripción | Aprobación requerida |
|---|---|---|
| **BAJO** | Cambio rutinario, reversible, sin afectación a controles de seguridad ni a usuarios finales | Responsable del Sistema |
| **MEDIO** | Cambio que afecta a un servicio no esencial, con ventana de mantenimiento prevista | Responsable del Sistema + Responsable de la Seguridad |
| **ALTO** | Cambio que afecta a servicios esenciales, controles de seguridad o estructura del sistema | Comité de Cambios |
| **CRÍTICO** | Cambio que afecta a la arquitectura del SGSI o que requiere modificación de la Declaración de Aplicabilidad | Comité de Cambios + Comité de Seguridad |
| **EMERGENCIA** | Cambio para resolver incidente o vulnerabilidad crítica | Aprobación abreviada del Responsable de la Seguridad, ratificación posterior del Comité |

## 5. RESPONSABILIDADES — MATRIZ RACI

| Actividad | Solicitante | Resp. Sistema | Resp. Seguridad | CAB | Comité Seguridad |
|---|---|---|---|---|---|
| Solicitud del cambio | **R** | I | I | — | — |
| Análisis técnico | C | **R** | C | — | — |
| Análisis de impacto en seguridad | I | C | **R** | I | — |
| Autorización cambio BAJO | I | **A/R** | C | — | — |
| Autorización cambio MEDIO | I | C | **A/R** | I | — |
| Autorización cambio ALTO | I | C | C | **A/R** | I |
| Autorización cambio CRÍTICO | I | C | C | C | **A/R** |
| Ejecución | I | **R** | C | I | I |
| Verificación post-cambio | I | C | **R** | I | I |
| Cierre y registro | I | **R** | C | I | I |

## 6. CATÁLOGO DE CAMBIOS ESTÁNDAR

El Responsable de la Seguridad mantendrá un **Catálogo de Cambios Estándar** en el que se preautorizan determinados cambios repetitivos. Cada entrada del catálogo incluirá:

a) Identificador único del cambio estándar.
b) Descripción detallada.
c) Sistemas afectados.
d) Procedimiento de ejecución.
e) Criterios de éxito y rollback.
f) Persona o rol autorizado para ejecutarlo.
g) Periodicidad de revisión del catálogo.

**Ejemplos de cambios estándar habituales:**

- Aplicación de actualizaciones rutinarias del sistema operativo en estaciones de trabajo (no servidores).
- Reinicio programado de servicios para liberación de recursos.
- Reintegración de backups verificados.
- Renovación rutinaria de certificados antes de su expiración.
- Altas y bajas de usuario gestionadas conforme al procedimiento {{ proyecto.codigo_documento_base }}-205.

El catálogo se revisa **anualmente** por el Responsable de la Seguridad.

## 7. FLUJO DE GESTIÓN — CAMBIO NORMAL

### 7.1 Solicitud

**Paso 1.** El solicitante (usuario funcional, técnico, proveedor o responsable de área) cumplimenta el **Formulario de Solicitud de Cambio (RFC)** del Anexo I, indicando:

- Descripción del cambio propuesto.
- Justificación y beneficio esperado.
- Sistemas, servicios y datos afectados.
- Fecha propuesta de implementación.
- Estimación preliminar del impacto.

**Paso 2.** La solicitud se registra en el **Sistema de Gestión de Cambios** del SGSI con identificador único `CHG-AAAA-NNNN`.

### 7.2 Análisis técnico y de seguridad

**Paso 3.** El Responsable del Sistema realiza el análisis técnico, evaluando:

- Viabilidad técnica del cambio.
- Recursos necesarios (humanos, tecnológicos, económicos).
- Tiempo estimado de implementación y ventana requerida.
- Plan de implementación detallado.
- Plan de marcha atrás (rollback) específico.
- Pruebas a realizar antes y después del cambio.
- Dependencias con otros sistemas o cambios pendientes.

**Paso 4.** El Responsable de la Seguridad realiza el **análisis de impacto en seguridad**, valorando si el cambio:

- Modifica algún control de seguridad existente.
- Afecta a la arquitectura de red o segmentación.
- Introduce nuevos componentes en el inventario.
- Modifica permisos de acceso.
- Requiere actualización del análisis de riesgos.
- Requiere actualización de la Declaración de Aplicabilidad.
- Genera nuevos requisitos legales o contractuales.

**Paso 5.** Con base en ambos análisis, se determina la **clasificación final** del cambio (BAJO, MEDIO, ALTO o CRÍTICO).

### 7.3 Autorización

**Paso 6.** Según la clasificación, el cambio se eleva al órgano competente conforme al apartado 4, que dispone de los siguientes plazos máximos para resolver:

| Nivel | Plazo máximo de decisión |
|---|---|
| BAJO | 2 días hábiles |
| MEDIO | 5 días hábiles |
| ALTO | Próxima reunión del CAB (frecuencia mínima quincenal) |
| CRÍTICO | Próxima reunión del Comité de Seguridad o sesión extraordinaria |

**Paso 7.** La autorización (o denegación) se documenta indicando:

- Decisión adoptada y motivación.
- Persona u órgano que decide.
- Condiciones impuestas, si las hubiera.
- Fecha autorizada de implementación.
- Ventana de mantenimiento aprobada.

### 7.4 Comunicación previa

**Paso 8.** Antes de la implementación, se comunica el cambio a las personas afectadas con la antelación adecuada:

| Nivel | Antelación mínima |
|---|---|
| BAJO | 24 horas |
| MEDIO | 3 días hábiles |
| ALTO | 5 días hábiles |
| CRÍTICO | 10 días hábiles |

### 7.5 Implementación

**Paso 9.** El Responsable del Sistema ejecuta el cambio conforme al plan aprobado, dentro de la ventana de mantenimiento autorizada.

**Paso 10.** Durante la ejecución se mantiene un **registro técnico detallado** que incluye marcas de tiempo, comandos ejecutados, salidas obtenidas y desviaciones observadas respecto al plan.

**Paso 11.** Si durante la ejecución surgen problemas no previstos que puedan comprometer la estabilidad o seguridad del sistema, se activa el **plan de rollback** y el cambio se considera fallido a efectos de su clasificación.

### 7.6 Verificación post-cambio

**Paso 12.** Tras la ejecución, el Responsable de la Seguridad verifica que:

- El cambio se ha implementado conforme al plan.
- Los servicios afectados funcionan correctamente.
- Los controles de seguridad relevantes mantienen su eficacia.
- No se han introducido nuevas vulnerabilidades observables.
- La documentación del sistema (inventario, diagramas, configuraciones) ha sido actualizada.

### 7.7 Cierre

**Paso 13.** Una vez verificado el éxito del cambio, este se marca como **CERRADO** en el sistema.

**Paso 14.** Si el cambio falla y se ejecuta rollback, se marca como **REVERTIDO** y se elabora un breve informe de causas para la mejora del proceso.

**Paso 15.** Para cambios de nivel ALTO o CRÍTICO se elabora **Informe de Cierre** que se eleva al CAB y, en su caso, al Comité de Seguridad.

## 8. FLUJO DE GESTIÓN — CAMBIO DE EMERGENCIA

**Paso 16.** Cuando un cambio deba implementarse con la mayor brevedad por concurrir una situación de emergencia (incidente de seguridad activo, vulnerabilidad crítica con explotación in the wild, caída de servicio esencial), se aplica el **flujo abreviado** siguiente:

a) El Responsable de la Seguridad o, en su ausencia, el Responsable del Sistema, autoriza verbalmente o por escrito el cambio.

b) Se ejecuta el cambio dejando registro detallado de las acciones realizadas.

c) En las **24 horas siguientes** a la implementación, se cumplimenta el formulario completo del cambio y se eleva al CAB para ratificación posterior.

d) El CAB analiza el cambio en su siguiente reunión y, si detecta deficiencias, exige acciones correctivas adicionales.

## 9. COMITÉ DE CAMBIOS (CAB)

El Comité de Cambios estará compuesto por:

- Presidente: {{ responsables.responsable_seguridad.nombre }}, {{ responsables.responsable_seguridad.cargo }}
- Vocal técnico: {{ responsables.responsable_sistema.nombre }}, {{ responsables.responsable_sistema.cargo }}
- Vocal funcional: {{ responsables.responsable_servicio.nombre }}, {{ responsables.responsable_servicio.cargo }}
- Otros vocales convocados según la naturaleza del cambio.

**Frecuencia mínima de reuniones:** quincenal, con sesiones extraordinarias cuando se requieran.

## 10. INDICADORES

| Indicador | Fórmula | Objetivo |
|---|---|---|
| Tasa de éxito de cambios | (cambios exitosos / cambios totales) × 100 | ≥ 95% |
| Tasa de rollback | (cambios revertidos / cambios totales) × 100 | < 5% |
| Cambios de emergencia ratificados en plazo | (ratificados ≤ 24h / total emergencia) × 100 | 100% |
| Cambios no autorizados detectados | nº incidentes por cambio fuera del procedimiento | 0 |
| Antigüedad media del catálogo de cambios estándar | meses desde última revisión | ≤ 12 |

## 11. ANEXOS

- **Anexo I:** Formulario de Solicitud de Cambio (RFC)
- **Anexo II:** Plantilla del Plan de Implementación y Rollback
- **Anexo III:** Catálogo de Cambios Estándar
- **Anexo IV:** Plantilla del Acta del CAB
- **Anexo V:** Formulario de Cambio de Emergencia

---

**Documento {{ proyecto.codigo_documento_base }}-206 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---

# DOCUMENTO E-207 — PROCEDIMIENTO DE CONCIENCIACIÓN Y FORMACIÓN EN SEGURIDAD

**Materializa las medidas mp.per.3 (Concienciación) y mp.per.4 (Formación) del Anexo II del ENS** y los controles A.6.3 (Information security awareness, education and training) de ISO/IEC 27001:2022. Es el procedimiento que el auditor pide demostrar con registros de asistencia y resultados de tests.

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-207"
titulo: "Procedimiento de Concienciación y Formación en Seguridad de la Información"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
fecha_proxima_revision: "{{ proyecto.proxima_revision }}"
clasificacion: "INTERNA"
propietario: "{{ responsables.responsable_seguridad.cargo }}"
politica_madre: "{{ proyecto.codigo_documento_base }}-100, {{ proyecto.codigo_documento_base }}-106"
---

# PROCEDIMIENTO DE CONCIENCIACIÓN Y FORMACIÓN EN SEGURIDAD DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-207 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Establecer el método mediante el cual {{ cliente.razon_social }} planifica, ejecuta, mide y mejora las actividades de concienciación y formación en seguridad de la información dirigidas a su personal y a los terceros con acceso a sus sistemas, en cumplimiento de las medidas **mp.per.3 (Concienciación)** y **mp.per.4 (Formación)** del Anexo II del Real Decreto 311/2022 y conforme al **Plan Anual de Concienciación y Formación** aprobado por el Comité de Seguridad.

## 2. ALCANCE

Aplica a:

a) Todo el personal de la Entidad, con independencia de su régimen jurídico, categoría profesional o modalidad de contratación.

b) Personal externo y proveedores con acceso a sistemas de la Entidad, en la medida que sus contratos lo establezcan.

c) Personal de nueva incorporación, durante el proceso de acogida.

d) Becarios, personal en prácticas y personal eventual.

## 3. SEGMENTACIÓN DE LA AUDIENCIA

A los efectos del presente procedimiento, el personal se segmenta en los siguientes grupos, cada uno con necesidades formativas específicas:

| Grupo | Perfil | Foco principal de formación |
|---|---|---|
| **G1 — General** | Todo el personal sin perfil técnico ni privilegiado | Higiene digital, phishing, contraseñas, uso aceptable, RGPD básico |
| **G2 — Funcional con datos personales** | Personal que trata datos personales en su día a día | RGPD avanzado, brechas, derechos de los interesados, secreto profesional |
| **G3 — Técnico** | Personal del departamento TI con responsabilidades operativas | Gestión segura, hardening, gestión de incidentes, vulnerabilidades |
| **G4 — Privilegiado** | Administradores con privilegios elevados | Seguridad avanzada, defensa en profundidad, threat hunting, response |
| **G5 — Directivo** | Personal directivo y miembros del órgano de gobierno | Riesgos estratégicos, gobernanza, obligaciones legales del cargo |
| **G6 — Roles ENS** | Personas designadas como roles del art. 11 ENS | Marco normativo ENS, MAGERIT, gestión del SGSI |

## 4. PLAN ANUAL DE CONCIENCIACIÓN Y FORMACIÓN

### 4.1 Elaboración

**Paso 1.** Durante el mes de enero de cada año, el Responsable de la Seguridad elabora el **Plan Anual de Concienciación y Formación** que incluirá:

- Objetivos generales y específicos por grupo.
- Acciones formativas previstas con su contenido, modalidad y duración.
- Calendario de ejecución.
- Audiencia objetivo de cada acción.
- Mecanismos de evaluación previstos.
- Indicadores de éxito.
- Recursos necesarios (presupuesto, formadores, plataforma).

**Paso 2.** El Plan se eleva al Comité de Seguridad para aprobación en su primera reunión ordinaria del año.

### 4.2 Contenidos mínimos exigibles

Por cada grupo de audiencia, el Plan deberá contemplar como mínimo las siguientes acciones formativas anuales:

| Grupo | Acciones mínimas anuales | Horas mínimas/año |
|---|---|---|
| G1 — General | Sesión inicial + 2 píldoras + simulacro phishing | 2 h |
| G2 — Datos personales | Sesión específica RGPD + actualización normativa | 4 h |
| G3 — Técnico | Formación técnica especializada | 16 h |
| G4 — Privilegiado | Formación avanzada + ejercicios prácticos | 24 h |
| G5 — Directivo | Sesión ejecutiva + briefing trimestral | 4 h |
| G6 — Roles ENS | Formación específica ENS + actualización normativa | 16 h |

## 5. ACCIONES DE CONCIENCIACIÓN

### 5.1 Sesión de acogida

**Paso 3.** Toda persona de nueva incorporación recibirá, durante su primera semana, una **sesión de acogida en seguridad** de duración mínima 2 horas que cubra:

- Presentación del SGSI y de la Política de Seguridad ({{ proyecto.codigo_documento_base }}-100).
- Lectura y firma de la Política de Uso Aceptable ({{ proyecto.codigo_documento_base }}-106).
- Normas básicas de higiene digital.
- Procedimiento para la notificación de incidentes.
- Datos de contacto del Responsable de la Seguridad.

**Paso 4.** La sesión se documenta con **registro de asistencia firmado** y queda incorporada al expediente del trabajador.

### 5.2 Píldoras formativas

**Paso 5.** Con periodicidad **trimestral**, el Responsable de la Seguridad distribuye **píldoras formativas** breves (vídeos de 3-5 minutos, infografías, casos prácticos) sobre temas concretos:

- Reconocimiento de phishing y suplantación.
- Gestión segura de contraseñas y MFA.
- Uso seguro de redes Wi-Fi públicas.
- Protección de información en desplazamientos.
- Cifrado de dispositivos y soportes.
- Ingeniería social telefónica (vishing).
- Detección de mensajes fraudulentos (smishing).
- Riesgos de redes sociales corporativas.

### 5.3 Simulacros de phishing

**Paso 6.** Con periodicidad **trimestral**, el Responsable de la Seguridad ejecutará **simulacros de phishing controlados** dirigidos a toda la audiencia G1, G2, G3, G4 y G5.

**Paso 7.** Los simulacros utilizarán plantillas de mensajes que reproduzcan tácticas reales observadas (suplantación de marca, urgencia falsa, premios falsos, falsas notificaciones administrativas).

**Paso 8.** Los resultados se analizarán identificando:

- Tasa de apertura del mensaje.
- Tasa de clic en enlaces.
- Tasa de introducción de credenciales.
- Tasa de notificación al equipo de seguridad.

**Paso 9.** Las personas que caigan en el simulacro reciben formación correctiva específica, sin carácter sancionador en una primera ocasión, y los resultados agregados se elevan al Comité de Seguridad.

### 5.4 Campañas temáticas

**Paso 10.** La Entidad participará al menos una vez al año en una campaña temática alineada con eventos como el **Mes Europeo de la Ciberseguridad** (octubre), distribuyendo material divulgativo y organizando charlas o jornadas internas.

## 6. ACCIONES DE FORMACIÓN ESPECÍFICA

### 6.1 Formación técnica especializada

**Paso 11.** El personal de los grupos G3 y G4 recibirá formación técnica especializada en:

- Hardening de sistemas operativos y bases de datos.
- Gestión segura de configuraciones cloud.
- Análisis de logs y detección de anomalías.
- Respuesta a incidentes y análisis forense básico.
- Uso seguro de herramientas de administración remota.

**Paso 12.** Esta formación podrá impartirse mediante cursos externos certificados, formación interna o plataformas de e-learning especializadas.

### 6.2 Formación específica para roles ENS

**Paso 13.** Las personas designadas como roles del artículo 11 del ENS recibirán formación específica que cubra:

- Marco normativo del ENS y guías CCN-STIC aplicables.
- Metodología MAGERIT v3 para análisis de riesgos.
- Herramientas oficiales del CCN (PILAR, INES, AMPARO, LUCIA).
- Proceso de adecuación y certificación.
- Funciones y responsabilidades específicas del rol.

**Paso 14.** Para el Responsable de la Seguridad se valorará la obtención de certificaciones profesionales reconocidas internacionalmente (CISA, CISM, CISSP, ISO 27001 Lead Implementer/Auditor).

### 6.3 Formación específica para directivos

**Paso 15.** El personal directivo y los miembros del órgano de gobierno superior recibirán **briefings ejecutivos** semestrales sobre:

- Estado del SGSI y métricas clave.
- Riesgos estratégicos detectados.
- Cambios normativos relevantes.
- Tendencias de amenazas en el sector.
- Obligaciones legales del cargo en materia de ciberseguridad y protección de datos.

## 7. EVALUACIÓN DEL APRENDIZAJE

**Paso 16.** Cada acción formativa relevante incluirá un mecanismo de evaluación del aprendizaje, que podrá consistir en:

- Test de conocimientos al finalizar la formación.
- Casos prácticos o ejercicios.
- Simulacros operativos.
- Evaluaciones tipo *security hygiene assessment*.

**Paso 17.** El umbral mínimo para considerar superada una acción formativa será del **70% de aciertos** en las evaluaciones objetivas.

**Paso 18.** Las personas que no superen una evaluación recibirán formación de refuerzo y volverán a ser evaluadas. Tres no superaciones consecutivas serán comunicadas al responsable jerárquico para análisis de la situación.

## 8. REGISTROS GENERADOS

| Registro | Conservación |
|---|---|
| Plan Anual de Concienciación y Formación | Vida del SGSI |
| Registro de asistencia a sesiones de acogida | Vida laboral del empleado + 4 años |
| Registro de asistencia a formaciones específicas | 5 años |
| Resultados de evaluaciones del aprendizaje | 5 años |
| Informe trimestral de simulacros de phishing | 5 años |
| Informe anual de cumplimiento del Plan | Vida del SGSI |

## 9. INDICADORES

| Indicador | Objetivo |
|---|---|
| Cobertura del Plan Anual (personal formado / total) | ≥ 95% |
| Personal nuevo con sesión de acogida en plazo | 100% |
| Personal G3-G4 con horas mínimas anuales completadas | ≥ 90% |
| Tasa de clic en simulacros de phishing | < 10% (objetivo final 5%) |
| Tasa de notificación correcta de simulacros de phishing | ≥ 50% |
| Personal con tres no superaciones consecutivas | 0 |

## 10. ANEXOS

- **Anexo I:** Plantilla del Plan Anual de Concienciación y Formación
- **Anexo II:** Material de la sesión de acogida
- **Anexo III:** Catálogo de píldoras formativas vigentes
- **Anexo IV:** Registro de asistencia
- **Anexo V:** Plantilla de evaluación del aprendizaje
- **Anexo VI:** Plantilla del informe trimestral de phishing

---

**Documento {{ proyecto.codigo_documento_base }}-207 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---

# DOCUMENTO E-210 — PROCEDIMIENTO DE COPIAS DE SEGURIDAD Y RESTAURACIÓN

**Materializa la medida mp.info.9 (Copias de seguridad) del Anexo II del ENS** y desarrolla el apartado 6.2 de la Política de Continuidad ({{ proyecto.codigo_documento_base }}-104). Es el procedimiento que el auditor pide demostrar con un test real de restauración reciente.

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-210"
titulo: "Procedimiento de Copias de Seguridad y Restauración"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
fecha_proxima_revision: "{{ proyecto.proxima_revision }}"
clasificacion: "INTERNA"
propietario: "{{ responsables.responsable_seguridad.cargo }}"
politica_madre: "{{ proyecto.codigo_documento_base }}-104"
---

# PROCEDIMIENTO DE COPIAS DE SEGURIDAD Y RESTAURACIÓN DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-210 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Establecer el método operativo mediante el cual {{ cliente.razon_social }} planifica, ejecuta, verifica, custodia y, en caso necesario, utiliza copias de seguridad de los datos, configuraciones y sistemas comprendidos en el alcance del SGSI, garantizando la disponibilidad e integridad de la información ante cualquier tipo de pérdida, corrupción, destrucción o cifrado malicioso.

Este procedimiento desarrolla el apartado 6.2 de la Política de Continuidad del Servicio ({{ proyecto.codigo_documento_base }}-104) y materializa la medida **mp.info.9 (Copias de seguridad)** del Anexo II del Real Decreto 311/2022.

## 2. ALCANCE

Aplica a todos los datos, configuraciones, sistemas operativos, aplicaciones, máquinas virtuales y elementos cuya pérdida o corrupción pudiera afectar a la operación de los servicios comprendidos en el alcance del SGSI.

## 3. ESTRATEGIA DE COPIA — REGLA 3-2-1-1-0

La estrategia de copia adoptada se ajusta a la **regla 3-2-1-1-0**:

- **3** copias de los datos críticos en total (incluido el original).
- **2** soportes diferentes para almacenarlas.
- **1** copia almacenada **fuera de las instalaciones principales** (offsite).
- **1** copia adicional **inmutable o air-gapped** para protección frente a ransomware.
- **0** errores detectados en las pruebas de restauración periódicas.

## 4. MATRIZ DE COPIA POR TIPO DE DATO

| Tipo de dato | Frecuencia | Retención mínima | Tipo de copia | Almacenamiento |
|---|---|---|---|---|
| Bases de datos críticas | Cada 4 horas (incremental) + diaria (completa) | 6 meses | Snapshot + dump lógico | Local + offsite cifrado |
| Bases de datos no críticas | Diaria | 3 meses | Dump lógico | Local + offsite |
| Sistemas de ficheros corporativos | Diaria (incremental) + semanal (completa) | 3 meses | A nivel de bloque o fichero | Local + offsite |
| Configuraciones de servidores | Tras cada cambio + semanal | 1 año | Snapshot + IaC en repositorio | Repositorio versionado |
| Configuraciones de red (firewall, switches, routers) | Tras cada cambio + diaria | 1 año | Export en formato texto | Repositorio versionado |
| Imágenes de máquinas virtuales | Semanal | 3 meses | Snapshot completo | Local + offsite |
| Código fuente y artefactos | Continuo | Indefinida | Repositorio Git + binarios firmados | Repositorio + offsite |
| Logs y trazas de auditoría | Continuo (envío a SIEM) + diaria | Según política {{ proyecto.codigo_documento_base }}-203 | Append-only | SIEM + almacenamiento WORM |
| Registros del SGSI | Diaria | Vida del SGSI + 5 años | Snapshot del repositorio | Repositorio + offsite |

## 5. REQUISITOS DE PROTECCIÓN DE LAS COPIAS

### 5.1 Cifrado

**Paso 1.** Todas las copias de seguridad se almacenarán **cifradas en reposo** mediante algoritmos conformes al apartado 4 de la Política de Cifrado ({{ proyecto.codigo_documento_base }}-105):

- AES-256 en modo GCM o CCM para el cifrado de los datos.
- Claves gestionadas en HSM o vault corporativo conforme al apartado 6 de la Política {{ proyecto.codigo_documento_base }}-105.

### 5.2 Verificación de integridad

**Paso 2.** Cada copia se acompañará de un **valor hash SHA-256** calculado en el momento de su creación, que permita verificar posteriormente su integridad.

**Paso 3.** El sistema de copias verificará automáticamente los hashes con periodicidad semanal y emitirá alerta ante cualquier discrepancia.

### 5.3 Inmutabilidad

**Paso 4.** Para protegerse frente a ataques de ransomware, al menos una copia de cada dato crítico se almacenará en un sistema **inmutable** durante el periodo de retención, mediante:

- Object lock en almacenamiento S3-compatible (modo *compliance*, no *governance*).
- Sistemas de cinta con protección de escritura física.
- Soluciones de backup con snapshots inmutables.

### 5.4 Air-gapping

**Paso 5.** Para sistemas de máxima criticidad, se mantendrá adicionalmente una copia en un soporte físicamente desconectado de la red (air-gapped), actualizada con periodicidad mensual.

### 5.5 Localización offsite

**Paso 6.** La copia offsite se almacenará en una **ubicación física distinta y suficientemente alejada** de las instalaciones principales para que un mismo evento (incendio, inundación, ataque físico) no pueda destruir simultáneamente el original y la copia.

Cuando la copia offsite se almacene en proveedor cloud externo, se aplicarán las exigencias del apartado 7 de la Política {{ proyecto.codigo_documento_base }}-107 (Política de Proveedores).

## 6. EJECUCIÓN DE LAS COPIAS

### 6.1 Programación

**Paso 7.** Las copias se programan en horarios que minimicen el impacto en la operación, preferentemente fuera de las ventanas de mayor actividad operativa.

**Paso 8.** El sistema de gestión de copias monitoriza automáticamente la ejecución y emite alertas en caso de:

- Fallo en la ejecución de una tarea programada.
- Tarea no completada en el plazo previsto.
- Discrepancia en el tamaño esperado.
- Error en la verificación de integridad.

### 6.2 Resolución de fallos

**Paso 9.** Ante cualquier alerta de fallo, el Responsable del Sistema procederá a:

- Diagnosticar la causa.
- Reintentar la ejecución de la copia fallida.
- Si el fallo persiste, escalar al Responsable de la Seguridad y registrar la incidencia.
- Documentar la solución aplicada.

**Paso 10.** Tres fallos consecutivos en el mismo conjunto de datos requieren la apertura de un análisis específico y se reportan en el informe mensual al Comité de Seguridad.

### 6.3 Registros de copias

**Paso 11.** Cada ejecución de copia genera un registro automático que incluye:

- Identificador único de la copia.
- Conjunto de datos copiado.
- Fecha y hora de inicio y fin.
- Tamaño de los datos copiados.
- Hash SHA-256 de la copia.
- Ubicación de almacenamiento.
- Resultado (exitoso, con avisos, fallido).
- Operador o sistema que ejecutó la copia.

## 7. PRUEBAS DE RESTAURACIÓN

### 7.1 Programa de pruebas

**Paso 12.** Las pruebas de restauración se realizarán con la siguiente periodicidad mínima, alineada con la categoría ENS del sistema:

| Tipo de prueba | Categoría BÁSICA | Categoría MEDIA | Categoría ALTA |
|---|---|---|---|
| Restauración de fichero individual | Trimestral | Mensual | Mensual |
| Restauración de base de datos completa | Semestral | Trimestral | Mensual |
| Restauración de sistema completo (DR) | Anual | Semestral | Trimestral |
| Recuperación de copia inmutable / air-gapped | Anual | Anual | Semestral |

### 7.2 Ejecución de las pruebas

**Paso 13.** Cada prueba se planifica con un **escenario predeterminado** que documenta:

- Conjunto de datos a restaurar.
- Punto en el tiempo objetivo (RPO de prueba).
- Objetivo de tiempo (RTO de prueba).
- Entorno de destino (siempre entorno aislado, nunca productivo).
- Criterios de éxito.

**Paso 14.** Las pruebas se ejecutan en **entorno de laboratorio aislado**, sin interferir con los sistemas productivos.

**Paso 15.** Tras la restauración se verifica la **integridad funcional** del entorno restaurado mediante pruebas de:

- Acceso a los datos.
- Consistencia de las relaciones entre tablas.
- Integridad referencial.
- Funcionamiento de las aplicaciones que consumen los datos.

### 7.3 Documentación de resultados

**Paso 16.** Cada prueba genera un **Informe de Prueba de Restauración** que incluye:

- Identificación de la prueba y fecha.
- Conjunto de datos restaurado.
- Tiempo real de restauración (RTR) frente al objetivo.
- Resultados de las verificaciones de integridad.
- Incidencias detectadas y acciones correctivas.
- Conclusiones y recomendaciones.

**Paso 17.** Los informes se elevan al Comité de Seguridad y se incorporan al expediente del SGSI conforme al procedimiento {{ proyecto.codigo_documento_base }}-203.

### 7.4 Acción correctiva ante fallos

**Paso 18.** Si una prueba falla, se abre **acción correctiva inmediata** que incluya:

- Análisis de la causa raíz.
- Plan de corrección con plazo definido.
- Reverificación tras la corrección.
- Notificación al Comité de Seguridad.

## 8. RESTAURACIÓN OPERATIVA

### 8.1 Solicitud

**Paso 19.** Cualquier solicitud de restauración operativa se canaliza al Responsable del Sistema, indicando:

- Conjunto de datos a restaurar.
- Punto en el tiempo deseado.
- Justificación de la solicitud.
- Impacto previsto de no realizarla.

### 8.2 Autorización

**Paso 20.** La restauración será autorizada por:

- Restauraciones rutinarias (recuperación de fichero individual): Responsable del Sistema.
- Restauraciones de base de datos completa: Responsable de la Seguridad.
- Restauraciones tras incidente grave: Coordinador del ERI conforme al procedimiento {{ proyecto.codigo_documento_base }}-204.

### 8.3 Ejecución

**Paso 21.** La restauración se ejecuta conforme a la guía técnica correspondiente (instrucciones técnicas IT-210-XX), documentando todas las acciones.

**Paso 22.** Tras la restauración, se verifica la integridad y se notifica al solicitante.

### 8.4 Registro

**Paso 23.** Toda restauración operativa se registra en el sistema con identificador único, persona solicitante, autorizador, ejecutor, conjunto de datos restaurado y resultado.

## 9. INDICADORES

| Indicador | Objetivo |
|---|---|
| Tasa de éxito de copias programadas | ≥ 99% |
| Tasa de éxito de pruebas de restauración | 100% |
| RTO real / RTO objetivo | ≤ 1.0 |
| Antigüedad media de la última prueba de restauración por sistema | < periodicidad mínima |
| Conjuntos de datos sin copia offsite | 0 |
| Conjuntos de datos críticos sin copia inmutable | 0 |

## 10. ANEXOS

- **Anexo I:** Inventario de conjuntos de datos y matriz de copia
- **Anexo II:** Plantilla del Informe de Prueba de Restauración
- **Anexo III:** Calendario anual de pruebas de restauración
- **Anexo IV:** Instrucciones técnicas de restauración por sistema (IT-210-XX)

---

**Documento {{ proyecto.codigo_documento_base }}-210 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---

# DOCUMENTO E-219 — PROCEDIMIENTO DE HARDENING Y CONFIGURACIÓN SEGURA

**Materializa las medidas op.exp.2 (Configuración de seguridad) y op.exp.3 (Gestión de la configuración) del Anexo II del ENS** y los controles A.8.9 (Configuration management) de ISO/IEC 27001:2022. Es el procedimiento que el auditor pide demostrar con configuraciones reales comparadas contra una baseline.

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-219"
titulo: "Procedimiento de Hardening y Configuración Segura"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
fecha_proxima_revision: "{{ proyecto.proxima_revision }}"
clasificacion: "INTERNA"
propietario: "{{ responsables.responsable_seguridad.cargo }}"
politica_madre: "{{ proyecto.codigo_documento_base }}-100"
---

# PROCEDIMIENTO DE HARDENING Y CONFIGURACIÓN SEGURA DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-219 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Establecer los criterios técnicos y el método operativo mediante el cual {{ cliente.razon_social }} configura de forma segura los sistemas operativos, bases de datos, aplicaciones, dispositivos de red, servicios cloud y demás componentes tecnológicos comprendidos en el alcance del SGSI, en cumplimiento de las medidas **op.exp.2 (Configuración de seguridad)** y **op.exp.3 (Gestión de la configuración)** del Anexo II del Real Decreto 311/2022.

## 2. ALCANCE

Aplica a todos los componentes tecnológicos productivos comprendidos en el alcance del SGSI, así como a sus entornos de desarrollo y preproducción cuando estos puedan afectar a la seguridad del entorno productivo.

## 3. PRINCIPIOS

### 3.1 Mínima funcionalidad

Cada sistema se configura con los **servicios, puertos, cuentas, protocolos y funcionalidades estrictamente necesarios** para su función operativa. Todo lo demás debe deshabilitarse o eliminarse.

### 3.2 Configuración segura por defecto

Las configuraciones por defecto del fabricante rara vez son seguras. Toda nueva instalación debe pasar por el proceso de hardening antes de su puesta en producción.

### 3.3 Reproducibilidad

Las configuraciones seguras se documentan mediante **plantillas reproducibles** (preferentemente Infrastructure as Code) que permitan desplegar nuevos sistemas con la misma configuración base de forma automatizada.

### 3.4 Verificación continua

La conformidad con la configuración segura no es un estado puntual sino una propiedad que debe verificarse de forma continua mediante herramientas automatizadas.

## 4. BASELINES DE REFERENCIA

### 4.1 Fuentes de las baselines

Como punto de partida para la elaboración de las baselines internas se utilizarán, en orden de preferencia:

a) Las **guías CCN-STIC de la serie 500** (Productos de Seguridad) y de la serie 600 (Aplicaciones), publicadas por el Centro Criptológico Nacional para los productos específicos cubiertos.

b) Los **CIS Benchmarks** del Center for Internet Security para sistemas operativos, bases de datos, aplicaciones y servicios cloud.

c) Los **STIGs (Security Technical Implementation Guides)** del DISA estadounidense.

d) Las recomendaciones específicas del **fabricante** del producto.

e) Las **plantillas Microsoft Security Baselines** para entornos Windows.

### 4.2 Adaptación a la realidad de la Entidad

**Paso 1.** El Responsable de la Seguridad, con el apoyo del Responsable del Sistema, adaptará las baselines de referencia a la realidad operativa de la Entidad, considerando:

- Compatibilidad con las aplicaciones y servicios productivos.
- Restricciones operativas específicas.
- Riesgo aceptable conforme al análisis del procedimiento {{ proyecto.codigo_documento_base }}-200.

**Paso 2.** Toda divergencia respecto a la baseline de referencia se documentará como **excepción justificada** con el correspondiente análisis de riesgos.

### 4.3 Catálogo de baselines

**Paso 3.** El Responsable de la Seguridad mantendrá un **Catálogo de Baselines** del SGSI que incluya, como mínimo, las siguientes:

| Tipo de sistema | Baseline aplicable |
|---|---|
| Linux servidor (Ubuntu, RHEL, Debian) | CIS Benchmark + adaptaciones |
| Windows Server | CIS Benchmark + Microsoft Security Baseline |
| Estaciones de trabajo Windows | CIS Benchmark + Microsoft Security Baseline |
| Estaciones de trabajo macOS | CIS Benchmark |
| Bases de datos PostgreSQL / MySQL / SQL Server | CIS Benchmark |
| Servidores web (Nginx, Apache, IIS) | CIS Benchmark |
| Contenedores Docker / Kubernetes | CIS Benchmark + ENISA recommendations |
| AWS / Azure / GCP | CIS Benchmark cloud + Well-Architected Framework |
| Dispositivos de red (Cisco, Fortinet) | STIG + recomendaciones del fabricante |
| Productos del CPSTIC del CCN | Guías CCN-STIC específicas |

## 5. PROCESO DE HARDENING DE NUEVOS SISTEMAS

### 5.1 Análisis previo

**Paso 4.** Antes de la instalación de un nuevo sistema, el Responsable del Sistema identifica:

- Tipo de sistema y baseline aplicable.
- Función específica que va a desempeñar.
- Nivel de seguridad exigible conforme a la categoría ENS del servicio que sustenta.
- Excepciones previsibles a la baseline.

### 5.2 Instalación y hardening

**Paso 5.** La instalación se realiza utilizando, cuando sea posible, plantillas Infrastructure as Code (IaC) preconfiguradas con la baseline aplicable.

**Paso 6.** Tras la instalación se aplica el procedimiento de hardening específico documentado en la **Instrucción Técnica IT-219-XX** correspondiente al tipo de sistema, que incluye:

- Eliminación de servicios y software innecesarios.
- Configuración de cuentas: deshabilitar cuentas por defecto, renombrar la administradora local, fijar políticas de contraseñas.
- Configuración del firewall local: regla por defecto DENY, apertura solo de puertos estrictamente necesarios.
- Configuración del sistema de logging conforme al procedimiento {{ proyecto.codigo_documento_base }}-220.
- Configuración del sistema de actualizaciones automáticas conforme al procedimiento {{ proyecto.codigo_documento_base }}-218.
- Configuración del antimalware corporativo cuando proceda.
- Restricciones de protocolos y cifrados (TLS, SSH).
- Eliminación de banners informativos innecesarios.
- Configuración de auditoría.
- Configuración del sincronismo de tiempo con servidor NTP corporativo.

### 5.3 Validación

**Paso 7.** Tras el hardening se ejecuta una **validación automática** mediante herramienta de cumplimiento (CIS-CAT, OpenSCAP, Lynis, Wazuh u otras), que verifica el grado de cumplimiento con la baseline.

**Paso 8.** El umbral mínimo aceptable de cumplimiento es del **85%** para sistemas de categoría BÁSICA y del **90%** para categorías MEDIA y ALTA.

**Paso 9.** Las divergencias se analizan caso por caso:

- Si pueden corregirse, se corrigen y se reverifica.
- Si no pueden corregirse, se documentan como excepciones justificadas.

### 5.4 Aceptación y puesta en producción

**Paso 10.** Una vez validado el hardening, el sistema se pone en producción siguiendo el procedimiento de gestión de cambios ({{ proyecto.codigo_documento_base }}-206).

**Paso 11.** Se incorpora al **Inventario de Activos** y al **Inventario de Configuraciones** del SGSI.

## 6. GESTIÓN CONTINUA DE LA CONFIGURACIÓN

### 6.1 Monitorización del cumplimiento

**Paso 12.** El cumplimiento de cada sistema con su baseline se monitoriza de forma **continua o periódica** mediante:

- Agentes de cumplimiento instalados en los sistemas.
- Escaneos programados desde una herramienta centralizada.
- Integración con el SIEM corporativo cuando sea posible.

**Paso 13.** Las desviaciones detectadas generan alertas que son tratadas por el Responsable del Sistema en los siguientes plazos:

| Severidad de la desviación | Plazo máximo de corrección |
|---|---|
| Crítica | 24 horas |
| Alta | 7 días |
| Media | 30 días |
| Baja | 90 días |

### 6.2 Cambios autorizados

**Paso 14.** Cualquier modificación intencional de la configuración debe gestionarse a través del procedimiento de gestión de cambios ({{ proyecto.codigo_documento_base }}-206), actualizándose la documentación del sistema y, cuando proceda, la propia baseline.

### 6.3 Cambios no autorizados (drift)

**Paso 15.** Cuando se detecta una modificación no autorizada de la configuración (drift), el Responsable de la Seguridad:

- Analiza el cambio y determina su origen.
- Decide si se trata de un incidente que requiera activar el procedimiento {{ proyecto.codigo_documento_base }}-204.
- Restaura la configuración correcta.
- Refuerza los controles para evitar la repetición.

## 7. REVISIÓN PERIÓDICA DE LAS BASELINES

**Paso 16.** Las baselines se revisan al menos **anualmente** por el Responsable de la Seguridad, atendiendo a:

- Actualizaciones de las baselines de referencia (CIS, STIG, CCN-STIC).
- Nuevas vulnerabilidades publicadas.
- Lecciones aprendidas de incidentes.
- Nuevas necesidades operativas.
- Cambios en el inventario tecnológico.

**Paso 17.** Las modificaciones aprobadas se aplican a los sistemas existentes según el calendario que apruebe el Comité de Seguridad, priorizando los sistemas de mayor categoría.

## 8. INDICADORES

| Indicador | Objetivo |
|---|---|
| Sistemas con baseline aplicada | 100% |
| Cumplimiento medio con la baseline (todos los sistemas) | ≥ 90% |
| Desviaciones críticas abiertas | 0 |
| Antigüedad media de la última verificación | < 30 días |
| Excepciones documentadas y autorizadas | 100% |
| Drift no autorizado detectado y resuelto en plazo | 100% |

## 9. ANEXOS

- **Anexo I:** Catálogo de Baselines del SGSI
- **Anexo II:** Plantilla de Excepción a la Baseline
- **Anexo III:** Formulario de Validación de Hardening
- **Anexo IV:** Listado de Instrucciones Técnicas IT-219-XX

---

**Documento {{ proyecto.codigo_documento_base }}-219 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---

# DOCUMENTO E-228 — PROCEDIMIENTO DE RECOPILACIÓN Y CUSTODIA DE EVIDENCIAS

**Materializa la medida op.exp.8 (Registro de la actividad) del Anexo II del ENS** en su vertiente forense, y desarrolla el apartado 5.3 del procedimiento de gestión de incidentes ({{ proyecto.codigo_documento_base }}-204). Sin un procedimiento sólido de cadena de custodia, las evidencias recopiladas durante un incidente pueden carecer de validez en sede judicial.

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-228"
titulo: "Procedimiento de Recopilación y Custodia de Evidencias"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
fecha_proxima_revision: "{{ proyecto.proxima_revision }}"
clasificacion: "INTERNA"
propietario: "{{ responsables.responsable_seguridad.cargo }}"
politica_madre: "{{ proyecto.codigo_documento_base }}-103"
---

# PROCEDIMIENTO DE RECOPILACIÓN Y CUSTODIA DE EVIDENCIAS DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-228 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Establecer el método mediante el cual {{ cliente.razon_social }} recopila, identifica, preserva, analiza y custodia las evidencias derivadas de incidentes de seguridad, investigaciones internas o requerimientos legales, garantizando su integridad, autenticidad y trazabilidad a lo largo de toda la cadena de custodia, de modo que conserven su valor probatorio en sede administrativa, judicial o disciplinaria.

## 2. ALCANCE

Aplica a toda evidencia, en cualquier formato, recopilada en el contexto de:

a) La gestión de un incidente de seguridad conforme al procedimiento {{ proyecto.codigo_documento_base }}-204.

b) Una investigación interna por sospecha de incumplimiento de la normativa interna.

c) Un requerimiento de autoridad administrativa o judicial.

d) Una auditoría interna o externa que requiera evidencias específicas.

## 3. DEFINICIONES OPERATIVAS

a) **Evidencia digital:** cualquier información o dato de valor probatorio almacenado, recibido o transmitido por un dispositivo electrónico.

b) **Cadena de custodia:** documentación cronológica que registra todas las personas y procesos que han manipulado una evidencia desde su recopilación hasta su uso final, garantizando su integridad.

c) **Hash:** función criptográfica que produce una huella única de un conjunto de datos, permitiendo verificar posteriormente que no han sido modificados.

d) **Integridad:** propiedad de la evidencia de no haber sido alterada desde su recopilación.

e) **Volátil:** información que se pierde cuando el sistema se apaga o reinicia (memoria RAM, conexiones de red activas, procesos en ejecución).

f) **No volátil:** información que persiste tras el apagado del sistema (discos duros, ficheros, logs almacenados).

## 4. PRINCIPIOS GENERALES

### 4.1 No alteración de la evidencia original

Cuando sea técnicamente posible, las acciones de análisis se realizarán sobre **copias** de la evidencia, preservando el original sin alteraciones. Cuando no sea posible, se documentarán meticulosamente todas las acciones realizadas sobre el original.

### 4.2 Documentación exhaustiva

Toda actuación realizada sobre una evidencia se documentará de inmediato, incluyendo persona, fecha, hora exacta, herramientas utilizadas y resultado obtenido.

### 4.3 Cadena de custodia ininterrumpida

La cadena de custodia debe ser **continua y completa** desde el momento de la recopilación hasta el destino final de la evidencia. Cualquier interrupción o transferencia se documenta.

### 4.4 Mínima intervención

Solo el personal autorizado y debidamente formado intervendrá en la recopilación y manipulación de evidencias. Se evitará en todo momento la intervención de personas no autorizadas.

### 4.5 Orden de volatilidad

En la recopilación de evidencias se respetará el principio del **orden de volatilidad**, priorizando la captura de la información más volátil antes de que se pierda.

## 5. ROLES Y RESPONSABILIDADES

| Rol | Responsabilidades |
|---|---|
| **Coordinador de evidencias** ({{ responsables.responsable_seguridad.nombre }}) | Coordinación general, autorización de las acciones, custodia del registro de cadena de custodia |
| **Analista forense interno** | Ejecución técnica de la recopilación y análisis preliminar |
| **Analista forense externo** (si procede) | Análisis forense en profundidad |
| **Asesor legal** | Asesoramiento sobre validez probatoria y requerimientos formales |
| **Testigo independiente** | Cuando proceda, presencia durante la recopilación para refrendar la integridad del procedimiento |

## 6. ORDEN DE VOLATILIDAD

La recopilación de evidencias debe seguir el siguiente orden, de mayor a menor volatilidad:

1. Registros de CPU, caché y registros del sistema.
2. Memoria RAM.
3. Estado de la red: conexiones activas, tablas de enrutamiento, ARP, sesiones.
4. Procesos en ejecución.
5. Información de discos: ficheros temporales, swap, slack space.
6. Datos en discos duros y otros soportes no volátiles.
7. Logs locales del sistema.
8. Configuración del sistema y software instalado.
9. Información de soportes físicos extraídos.
10. Backups y archivos remotos.

## 7. PROCESO DE RECOPILACIÓN

### 7.1 Decisión y autorización

**Paso 1.** Cuando en el contexto de un incidente o investigación se decida iniciar la recopilación de evidencias, el Coordinador de evidencias emite una **autorización formal** que indique:

- Identificador del caso (vinculado al `INC-AAAA-NNNN` del incidente, si procede).
- Sistemas o activos sobre los que se va a actuar.
- Tipo de evidencia a recopilar.
- Personal autorizado para intervenir.
- Acciones autorizadas y restricciones específicas.

### 7.2 Preparación

**Paso 2.** Antes de iniciar la recopilación, el equipo asignado prepara:

- Herramientas forenses verificadas (write blockers, software forense con versiones documentadas).
- Soportes vírgenes y verificados para almacenar las copias.
- Plantilla de la cadena de custodia (Anexo I).
- Material de identificación y embalaje seguro.
- Reloj sincronizado con fuente fiable para anotación de marcas de tiempo.

### 7.3 Llegada al sistema y observación inicial

**Paso 3.** Al llegar al sistema o ubicación, el equipo:

- Documenta el estado encontrado (encendido/apagado, sesión activa, mensajes en pantalla).
- Captura fotografías del estado físico cuando proceda.
- Identifica testigos presentes.
- Anota la fecha y hora exactas de inicio de la actuación.

### 7.4 Recopilación de evidencias volátiles (solo si el sistema está encendido)

**Paso 4.** Si el sistema está encendido, **antes de cualquier otra acción**, se procede a la recopilación de evidencias volátiles siguiendo el orden de volatilidad:

- Captura de la memoria RAM mediante herramienta forense.
- Listado de procesos en ejecución.
- Captura de conexiones de red activas.
- Captura de tablas ARP y enrutamiento.
- Captura del estado del sistema.

**Paso 5.** Cada captura se almacena en soporte externo verificado y se calcula su hash SHA-256 inmediatamente.

### 7.5 Aislamiento del sistema

**Paso 6.** Tras la recopilación de evidencias volátiles, el sistema se **aisla de la red** desconectando físicamente los cables de red y deshabilitando interfaces inalámbricas, evitando que un atacante remoto pueda destruir evidencias.

**Paso 7.** No se debe apagar el sistema mediante el procedimiento normal del sistema operativo, salvo decisión expresa del Coordinador. Si se debe apagar, se hará desconectando la alimentación para preservar el estado del disco.

### 7.6 Recopilación de evidencias no volátiles

**Paso 8.** Las evidencias no volátiles (discos duros, soportes extraíbles) se obtienen preferentemente mediante:

- Imagen forense bit a bit del soporte completo, utilizando write-blocker.
- Cálculo del hash SHA-256 del original y de la imagen para verificar la copia.
- Verificación de que ambos hashes coinciden.

**Paso 9.** Si el sistema está en producción y no puede ser apagado, se realiza una **adquisición en caliente** del disco mediante herramientas que permitan obtener una imagen consistente del sistema en uso.

### 7.7 Recopilación de evidencias lógicas

**Paso 10.** Cuando la evidencia consista en ficheros o registros específicos (logs, capturas de tráfico, mensajes de correo, registros de aplicaciones), se exportan estos elementos preservando su contexto y metadatos.

**Paso 11.** Se calcula y registra el hash SHA-256 de cada fichero exportado.

### 7.8 Identificación y embalaje

**Paso 12.** Cada evidencia recopilada recibe una **etiqueta de identificación única** que incluye:

- Identificador único en formato `EVI-AAAA-NNNN` (donde AAAA es el año y NNNN un correlativo).
- Identificador del caso.
- Descripción breve.
- Hash SHA-256.
- Fecha, hora y persona que la recopila.

**Paso 13.** Las evidencias físicas se embalan en bolsas o sobres antiestáticos, debidamente sellados y firmados por la persona que las custodia.

## 8. CADENA DE CUSTODIA

### 8.1 Apertura del registro

**Paso 14.** Para cada evidencia se abre un **registro de cadena de custodia** (Anexo I) que se mantiene desde la recopilación hasta el destino final.

### 8.2 Registro de movimientos

**Paso 15.** Cada vez que la evidencia cambia de manos, lugar, estado o se le aplica cualquier acción, se registra en la cadena de custodia:

- Fecha y hora exactas.
- Persona que entrega y persona que recibe (con firma).
- Acción realizada.
- Lugar de destino.
- Verificación del hash en cada transferencia (cuando sea técnicamente posible).
- Observaciones relevantes.

### 8.3 Almacenamiento

**Paso 16.** Las evidencias se custodian en un lugar seguro con acceso restringido, preferentemente:

- Caja fuerte o armario blindado con control de acceso.
- Sala con acceso restringido y monitorización.
- Para evidencias digitales, repositorio cifrado con control de acceso.

**Paso 17.** El acceso al almacenamiento se documenta y se restringe al personal estrictamente autorizado.

## 9. ANÁLISIS

### 9.1 Análisis sobre copias

**Paso 18.** El análisis se realiza sobre **copias de trabajo**, nunca sobre el original, salvo casos excepcionales debidamente justificados.

**Paso 19.** Las copias de trabajo se generan a partir de la imagen forense original y se verifica que su hash coincide con el original.

### 9.2 Documentación del análisis

**Paso 20.** Cada acción de análisis se documenta indicando:

- Herramienta utilizada y versión.
- Comando o procedimiento ejecutado.
- Salida obtenida.
- Interpretación de los resultados.
- Persona que realiza el análisis y fecha.

### 9.3 Informe forense

**Paso 21.** Al finalizar el análisis se elabora un **Informe Forense** que incluye:

- Resumen ejecutivo.
- Antecedentes del caso.
- Descripción de las evidencias analizadas.
- Metodología utilizada.
- Hallazgos detallados.
- Conclusiones.
- Anexos técnicos.

**Paso 22.** El informe se firma electrónicamente y se conserva junto con las evidencias.

## 10. DESTINO FINAL DE LAS EVIDENCIAS

**Paso 23.** Las evidencias se conservan durante el plazo necesario para cumplir su finalidad y, en cualquier caso, durante el **plazo de prescripción** de las acciones legales que pudieran derivarse del caso.

**Paso 24.** Transcurrido el plazo de conservación, las evidencias se destruyen mediante procedimientos que garanticen la imposibilidad de recuperación, conforme al apartado 9 de la Política de Clasificación ({{ proyecto.codigo_documento_base }}-108).

**Paso 25.** La destrucción se documenta en la propia cadena de custodia y mediante **acta de destrucción** firmada por dos personas.

## 11. INDICADORES

| Indicador | Objetivo |
|---|---|
| Evidencias con cadena de custodia completa | 100% |
| Verificaciones de hash exitosas en transferencias | 100% |
| Tiempo medio entre detección de incidente y recopilación de evidencias críticas | < 4 horas |
| Personal forense con formación específica vigente | 100% |

## 12. ANEXOS

- **Anexo I:** Plantilla de la cadena de custodia
- **Anexo II:** Etiqueta de identificación de evidencias
- **Anexo III:** Plantilla del Informe Forense
- **Anexo IV:** Acta de destrucción de evidencias
- **Anexo V:** Listado de herramientas forenses autorizadas

---

**Documento {{ proyecto.codigo_documento_base }}-228 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---

# DOCUMENTO E-234 — PROCEDIMIENTO DE AUDITORÍA INTERNA DEL SGSI

**Materializa el artículo 31 del RD 311/2022 y la ITS de Auditoría de la Seguridad** (Resolución BOE-A-2018-4573), así como el control A.9.2 (Internal audit) de ISO/IEC 27001:2022. Es el procedimiento que el auditor externo ENAC pide consultar antes de empezar su propia auditoría: si la auditoría interna está bien hecha, la externa fluye.

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-234"
titulo: "Procedimiento de Auditoría Interna del SGSI"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
fecha_proxima_revision: "{{ proyecto.proxima_revision }}"
clasificacion: "INTERNA"
propietario: "{{ responsables.responsable_seguridad.cargo }}"
politica_madre: "{{ proyecto.codigo_documento_base }}-100"
---

# PROCEDIMIENTO DE AUDITORÍA INTERNA DEL SGSI DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-234 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Establecer el método mediante el cual {{ cliente.razon_social }} planifica, ejecuta, comunica y realiza el seguimiento de las auditorías internas del SGSI, con el doble objetivo de:

a) Verificar el cumplimiento del SGSI con los requisitos del Real Decreto 311/2022 y de las normas y procedimientos internos de la Entidad.

b) Identificar oportunidades de mejora del SGSI y de la postura general de seguridad.

Este procedimiento da cumplimiento al **artículo 31 del Real Decreto 311/2022** (Auditoría) y a la **Instrucción Técnica de Seguridad de Auditoría de la Seguridad** publicada por Resolución de 27 de marzo de 2018 (BOE-A-2018-4573), y complementa, sin sustituirla, a la auditoría externa de certificación realizada por una entidad acreditada por ENAC conforme a la norma UNE-EN ISO/IEC 17065:2012.

## 2. ALCANCE

La auditoría interna abarca la totalidad del SGSI implantado en {{ cliente.razon_social }}, incluyendo:

a) Cumplimiento documental: verificación de la existencia, vigencia y aprobación de las políticas, procedimientos e instrucciones técnicas.

b) Cumplimiento operativo: verificación de que las medidas declaradas en la Declaración de Aplicabilidad están realmente implantadas y son eficaces.

c) Cumplimiento técnico: verificación mediante pruebas de la robustez técnica de los controles desplegados.

d) Cumplimiento de obligaciones legales: verificación del cumplimiento del marco normativo aplicable (RD 311/2022, RGPD, LOPDGDD y normativa sectorial cuando proceda).

## 3. PRINCIPIOS DE LA AUDITORÍA INTERNA

### 3.1 Independencia

El equipo auditor será **funcionalmente independiente** de las áreas auditadas. En particular, el Responsable del Sistema no podrá auditar los aspectos técnicos cuya operación tenga encomendada.

Cuando, por la dimensión de la Entidad, no sea posible garantizar plenamente la independencia interna, se recurrirá a un **auditor externo independiente** específicamente contratado para esta función, distinto en cualquier caso de la entidad de certificación.

### 3.2 Objetividad

Los hallazgos de auditoría se basarán exclusivamente en **evidencias objetivas** documentadas, no en opiniones o impresiones del auditor.

### 3.3 Profesionalidad

El equipo auditor contará con la **formación y experiencia** adecuadas en materia de seguridad de la información, ENS y técnicas de auditoría.

### 3.4 Confidencialidad

La información a la que el equipo auditor acceda en el ejercicio de sus funciones estará sujeta a estricto deber de confidencialidad, formalizándose mediante el correspondiente acuerdo cuando intervengan auditores externos.

### 3.5 Carácter constructivo

La auditoría interna tiene **carácter constructivo y de mejora**, no sancionador. Su objetivo es identificar oportunidades de mejora y no buscar culpables.

## 4. FRECUENCIA

### 4.1 Auditoría completa ordinaria

Se realizará una **auditoría interna completa anual** del SGSI, conforme exige el artículo 31 del RD 311/2022. La auditoría se programará idealmente para los **3-6 meses anteriores** a la auditoría externa de certificación, de modo que sus hallazgos puedan ser corregidos antes del paso del auditor ENAC.

### 4.2 Auditorías parciales

Adicionalmente, podrán realizarse **auditorías parciales** centradas en aspectos específicos cuando:

- Se introduzcan cambios significativos en el sistema.
- Se materialice un incidente relevante.
- Se identifiquen áreas de riesgo elevado en el análisis de riesgos.
- Lo decida el Comité de Seguridad.

### 4.3 Auditorías de seguimiento

Tras una auditoría que detecte no conformidades, se realizarán **auditorías de seguimiento** para verificar la efectividad de las acciones correctivas.

## 5. EQUIPO AUDITOR

### 5.1 Composición

El equipo auditor estará integrado por al menos:

- **Auditor jefe:** persona con experiencia acreditada en auditoría de SGSI conforme al ENS o a ISO 27001, formación específica en técnicas de auditoría y conocimiento del marco normativo aplicable.

- **Auditor técnico:** persona con conocimientos técnicos suficientes para evaluar los controles tecnológicos.

- **Auditor de procesos:** cuando proceda, persona especializada en procesos organizativos.

### 5.2 Cualificación

El equipo auditor acreditará formación en, al menos, una de las siguientes vías:

- Curso oficial de auditoría ENS impartido por el CCN o por entidad reconocida.
- Certificación ISO 27001 Lead Auditor.
- Certificación CISA (Certified Information Systems Auditor).
- Experiencia demostrable de al menos 3 auditorías SGSI ENS previas.

### 5.3 Designación

El equipo auditor será propuesto por el Responsable de la Seguridad y aprobado por el Comité de Seguridad, garantizando los principios de independencia y objetividad del apartado 3.

## 6. PROCESO DE AUDITORÍA

### 6.1 Planificación

**Paso 1.** Con al menos 30 días naturales de antelación al inicio de la auditoría, el Responsable de la Seguridad elabora el **Plan de Auditoría Interna** que incluirá:

- Alcance específico de la auditoría.
- Criterios de auditoría (RD 311/2022, normativa interna, normas ISO aplicables).
- Calendario detallado.
- Composición del equipo auditor.
- Áreas y procesos a auditar.
- Métodos a emplear (entrevistas, revisión documental, observación, pruebas técnicas).
- Recursos necesarios.

**Paso 2.** El Plan se comunica a las áreas auditadas con la antelación suficiente.

### 6.2 Reunión de apertura

**Paso 3.** La auditoría se inicia con una **reunión de apertura** en la que:

- Se presenta el equipo auditor.
- Se confirma el alcance, los criterios y el calendario.
- Se acuerdan los canales de comunicación y los enlaces operativos.
- Se aclaran las dudas previas.

### 6.3 Trabajo de campo

**Paso 4.** El equipo auditor realiza el trabajo de campo aplicando una combinación de las siguientes técnicas:

a) **Revisión documental:** revisión de las políticas, procedimientos, registros, actas, informes y demás documentación del SGSI.

b) **Entrevistas:** entrevistas estructuradas con los responsables y operadores de los procesos, basadas en preguntas estándar (Anexo II).

c) **Observación:** observación directa de la ejecución de los procesos.

d) **Pruebas de cumplimiento:** verificación práctica del cumplimiento de los controles mediante muestras representativas.

e) **Pruebas técnicas:** ejecución de pruebas técnicas concretas (revisión de configuraciones, escaneos, pruebas de control de acceso, verificación de logs).

**Paso 5.** Cada hallazgo se documenta indicando:

- Criterio de auditoría aplicado.
- Evidencia objetiva observada.
- Conformidad o no conformidad.
- En caso de no conformidad, su tipificación (ver apartado 7).

### 6.4 Reunión de cierre

**Paso 6.** Al finalizar el trabajo de campo se celebra una **reunión de cierre** en la que el equipo auditor presenta los principales hallazgos a las áreas auditadas, recoge sus comentarios y aclara posibles malentendidos.

### 6.5 Informe de auditoría

**Paso 7.** En el plazo máximo de **15 días naturales** desde la reunión de cierre, el equipo auditor elabora el **Informe de Auditoría Interna** que incluirá:

- Resumen ejecutivo.
- Alcance, objetivos y criterios de la auditoría.
- Equipo auditor y áreas auditadas.
- Metodología empleada.
- Resumen de hallazgos.
- Detalle de cada no conformidad y observación.
- Recomendaciones de mejora.
- Conclusiones generales y valoración global del SGSI.

**Paso 8.** El Informe se eleva al Comité de Seguridad y, en su caso, a {{ cliente.organo_aprobador_politicas }}.

## 7. TIPIFICACIÓN DE HALLAZGOS

Los hallazgos de auditoría se tipifican conforme a la siguiente escala:

| Tipo | Definición | Acción requerida |
|---|---|---|
| **No conformidad mayor** | Incumplimiento sistemático de un requisito esencial, ausencia total de un control crítico, o conjunto de no conformidades menores que en agregado evidencian un fallo sistémico | Plan de acción correctivo en 15 días, ejecución máxima en 90 días, verificación obligatoria |
| **No conformidad menor** | Incumplimiento puntual o aislado, fallo en un control no crítico o ineficacia parcial de una medida implantada | Plan de acción correctivo en 30 días, ejecución máxima en 180 días |
| **Observación** | Cumplimiento formal pero con potencial mejora, hallazgo que sin ser incumplimiento merece atención | Análisis y, en su caso, plan de mejora voluntario |
| **Oportunidad de mejora** | Recomendación del auditor para optimizar el SGSI, sin que exista incumplimiento | Análisis del Comité de Seguridad |

## 8. PLAN DE ACCIÓN CORRECTIVA

**Paso 9.** Para cada no conformidad detectada, el responsable del área auditada elabora un **Plan de Acción Correctiva** (PAC) que incluya:

- Análisis de la causa raíz del hallazgo.
- Acciones correctivas a implantar.
- Acciones preventivas para evitar la repetición.
- Responsable de cada acción.
- Plazo de ejecución.
- Indicador para verificar el cierre.

**Paso 10.** El PAC se eleva al Responsable de la Seguridad para su aprobación, y posteriormente al Comité de Seguridad para conocimiento.

## 9. SEGUIMIENTO Y CIERRE

**Paso 11.** El Responsable de la Seguridad realiza el seguimiento del cumplimiento de los PAC, registrando el avance en el sistema de gestión del SGSI.

**Paso 12.** Una vez completadas las acciones correctivas, se realiza una **verificación del cierre**, que puede consistir en:

- Revisión documental de las evidencias aportadas.
- Auditoría parcial de seguimiento.
- Verificación in situ por parte del auditor original.

**Paso 13.** Las no conformidades verificadas se cierran formalmente. Las no verificadas o cuya solución no resulta satisfactoria permanecen abiertas y se reportan al Comité de Seguridad.

## 10. RELACIÓN CON LA AUDITORÍA EXTERNA

**Paso 14.** Los resultados de la auditoría interna se ponen a disposición del auditor externo de certificación (entidad ENAC) cuando lo solicite. La existencia de auditoría interna eficaz se considerará por el auditor externo como evidencia de la **madurez del SGSI**.

**Paso 15.** Las no conformidades detectadas en la auditoría interna y no resueltas pueden ser detectadas también por el auditor externo, por lo que es responsabilidad del SGSI cerrarlas con anticipación a la auditoría externa.

## 11. INDICADORES

| Indicador | Objetivo |
|---|---|
| Auditoría interna anual realizada | 100% (1 al año) |
| Cumplimiento del Plan de Auditoría | ≥ 95% del alcance previsto |
| No conformidades mayores cerradas en plazo | 100% |
| No conformidades menores cerradas en plazo | ≥ 90% |
| No conformidades repetidas año a año | 0 |
| Antelación de la auditoría interna respecto a la externa | 3-6 meses |

## 12. ANEXOS

- **Anexo I:** Plantilla del Plan de Auditoría Interna
- **Anexo II:** Cuestionarios estándar de entrevista por área
- **Anexo III:** Plantilla del Informe de Auditoría Interna
- **Anexo IV:** Plantilla del Plan de Acción Correctiva
- **Anexo V:** Lista de comprobación de cumplimiento ENS basada en CCN-STIC 808 Anexo III

---

**Documento {{ proyecto.codigo_documento_base }}-234 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---

## INSTRUCCIONES PARA CLAUDE CODE — CIERRE DEL BLOQUE F2

### Estado del bloque F2 tras F2.1 + F2.2

Los **12 procedimientos críticos operativos** del SGSI ENS quedan completos:

| Código | Título | Bloque | Estado |
|---|---|---|---|
| E-200 | Análisis y Gestión de Riesgos | F2.1 | ✅ |
| E-203 | Gestión de la Información Documentada | F2.1 | ✅ |
| E-204 | Gestión de Incidentes de Seguridad | F2.1 | ✅ |
| E-205 | Gestión de Cuentas y Accesos | F2.1 | ✅ |
| E-206 | Gestión de Cambios | **F2.2** | ✅ |
| E-207 | Concienciación y Formación | **F2.2** | ✅ |
| E-210 | Copias de Seguridad y Restauración | **F2.2** | ✅ |
| E-217 | Evaluación y Seguimiento de Proveedores | F2.1 | ✅ |
| E-218 | Gestión de Vulnerabilidades y Parches | F2.1 | ✅ |
| E-219 | Hardening y Configuración Segura | **F2.2** | ✅ |
| E-228 | Recopilación y Custodia de Evidencias | **F2.2** | ✅ |
| E-234 | Auditoría Interna del SGSI | **F2.2** | ✅ |

### Cobertura ENS final tras F1 + F2 completos

| Familia ENS | Cobertura | Documentos |
|---|---|---|
| **org** | 95% | E-100, E-101, E-203 |
| **op.pl** | 100% | E-100, E-200 |
| **op.acc** | 100% | E-102, E-205 |
| **op.exp** | **95%** | E-204, E-206, E-218, E-219, E-228 |
| **op.ext** | 100% | E-107, E-217 |
| **op.cont** | **100%** | E-104, E-210 |
| **mp.if** | 0% | (política E-110 secundaria pendiente) |
| **mp.per** | **90%** | E-100, E-106, E-207 |
| **mp.eq** | 80% | E-106, E-218, E-219 |
| **mp.com / mp.si / mp.info** | 100% | E-105, E-108 |
| **mp.sw** | 60% | E-218, E-219 (resto en políticas secundarias) |
| **mp.s** | 100% | E-106, E-218 |
| **Auditoría (art. 31 ENS)** | 100% | E-234 |

**Cobertura total tras F1 + F2 completos: ~92% del Anexo II del ENS.**

El 8% restante corresponde a:
- Política específica de seguridad física y ambiental (E-110, mp.if): pendiente
- Políticas secundarias de software seguro (E-114, mp.sw): pendiente
- Política específica de gestión del personal (E-113, mp.per ampliado): pendiente

Estas tres políticas secundarias podrán generarse posteriormente con plantillas más ligeras o con consultor ENS senior antes del primer cliente real.

### Actividades para el Motor 6 (Document Factory) durante la Semana 5-6

1. **Crear `templates/` con 21 ficheros `.docx`**: 9 políticas (F1) + 12 procedimientos (F2).

2. **Crear `templates/anexos/`** con los formularios anexos referenciados en cada procedimiento (~80 anexos en total).

3. **Implementar el pipeline completo de generación**:
   ```
   onboarding Motor 16 → modelo OrganizacionCliente populated
   → Motor 6 invoca docxtpl con cada plantilla
   → validación post-generación (sin {{ }} sin sustituir)
   → SHA-256 + firma Ed25519 del Motor 6
   → registro en BD: cliente_id + version + hash + firma
   → almacenamiento del .docx en repositorio documental del cliente
   → generación de tabla de contenidos del SGSI completo
   → empaquetado en .zip del dossier completo del cliente
   ```

4. **Generar el dossier completo del SGSI** del cliente como `.zip` con estructura:
   ```
   /SGSI_{cliente}_{fecha}.zip
   ├── 00_Politicas/
   │   ├── POL-100_Politica_Seguridad.docx
   │   ├── POL-101_Roles_Responsabilidades.docx
   │   ├── ... (9 políticas)
   ├── 01_Procedimientos/
   │   ├── POL-200_Analisis_Riesgos.docx
   │   ├── ... (12 procedimientos)
   ├── 02_Anexos/
   │   ├── ... (formularios)
   ├── 03_Indice/
   │   └── Indice_SGSI.docx
   └── 04_Manifest/
       └── manifest.json (hashes, firmas, metadatos)
   ```

### Próximos bloques pendientes del plan 100/100

- **F3** — Plantillas comerciales reales (P-001 propuesta, C-001 contrato, C-003 retainer, E-001, E-040, E-050, E-400 BIA)
- **G** — Motor 8 pentesting con MCP + LLM autónomo
- **H** — LUCIA/PILAR/INES scraping con Playwright
- **I** — Suite tests E2E para las 10 fases

---

**Fin del Entregable F2.2.**

6 procedimientos operativos críticos restantes con texto operativo real español, ~13.000 palabras, completando el bloque **F2 — 12 procedimientos críticos del SGSI ENS**. Junto con F1 (9 políticas) conforman el **núcleo documental SGSI ENS de FULKRO** suficiente para cubrir el 92% del Anexo II del Real Decreto 311/2022 y presentar a una primera auditoría externa real con probabilidad de éxito alta (asumiendo correcta implantación de los controles técnicos asociados).
