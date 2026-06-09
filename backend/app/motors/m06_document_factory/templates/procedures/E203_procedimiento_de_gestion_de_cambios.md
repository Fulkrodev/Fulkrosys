# DOCUMENTO E-203 — PROCEDIMIENTO DE GESTIÓN DE CAMBIOS

**Materializa la medida op.exp.5 del Anexo II del ENS** y el control A.8.32 de ISO/IEC 27001:2022. Es uno de los procedimientos que más impacto tiene en la operación diaria porque cualquier cambio no controlado puede romper la conformidad del sistema o introducir vulnerabilidades.

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-203"
titulo: "Procedimiento de Gestión de Cambios"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
fecha_proxima_revision: "{{ proyecto.proxima_revision }}"
clasificacion: "INTERNA"
propietario: "{{ responsables.responsable_seguridad.cargo }}"
politica_madre: "{{ proyecto.codigo_documento_base }}-100"
---

# PROCEDIMIENTO DE GESTIÓN DE CAMBIOS DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-203 — Versión {{ proyecto.version_actual }}**

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
- Altas y bajas de usuario gestionadas conforme al procedimiento {{ proyecto.codigo_documento_base }}-231.

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

**Documento {{ proyecto.codigo_documento_base }}-203 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---

# DOCUMENTO E-PF-001 — PROCEDIMIENTO DE CONCIENCIACIÓN Y FORMACIÓN EN SEGURIDAD

**Materializa las medidas mp.per.3 (Concienciación) y mp.per.4 (Formación) del Anexo II del ENS** y los controles A.6.3 (Information security awareness, education and training) de ISO/IEC 27001:2022. Es el procedimiento que el auditor pide demostrar con registros de asistencia y resultados de tests.

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-PF-001"
titulo: "Procedimiento de Concienciación y Formación en Seguridad de la Información"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
fecha_proxima_revision: "{{ proyecto.proxima_revision }}"
clasificacion: "INTERNA"
propietario: "{{ responsables.responsable_seguridad.cargo }}"
politica_madre: "{{ proyecto.codigo_documento_base }}-100, {{ proyecto.codigo_documento_base }}-103"
---

# PROCEDIMIENTO DE CONCIENCIACIÓN Y FORMACIÓN EN SEGURIDAD DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-PF-001 — Versión {{ proyecto.version_actual }}**

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
- Lectura y firma de la Política de Uso Aceptable ({{ proyecto.codigo_documento_base }}-103).
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

**Documento {{ proyecto.codigo_documento_base }}-PF-001 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---
