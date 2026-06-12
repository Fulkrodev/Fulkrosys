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
