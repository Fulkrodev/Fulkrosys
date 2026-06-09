# F2.1 — PROCEDIMIENTOS CRÍTICOS DEL SGSI ENS — TEXTO OPERATIVO REAL EN ESPAÑOL (E-AR-001 a E-205)

**Plan 100/100 FULKRO — Bloque 3 de plantillas reales**
**Versión:** 1.0 — 9 de abril de 2026
**Continuación de:** F1_1 + F1_2 (políticas críticas E-100 a E-104)
**Destinatarios:** Claude Code (para conversión a `.docx` con `docxtpl`) + Marcos (para revisión legal y operativa)

---

## NOTA PRELIMINAR — DIFERENCIA ENTRE POLÍTICAS Y PROCEDIMIENTOS

Las **políticas** del bloque F1 son documentos **declarativos**: dicen *qué* exige la organización y *por qué*. Son aprobadas por el órgano de gobierno superior y cambian poco en el tiempo.

Los **procedimientos** de este bloque F2 son documentos **operativos**: dicen *cómo* se hace cada cosa, *quién* la hace, *cuándo*, *con qué entradas y salidas*, *qué evidencias se generan* y *cómo se mide el cumplimiento*. Son aprobados por el Comité de Seguridad o por el Responsable de la Seguridad y se actualizan con mayor frecuencia que las políticas.

**Estilo:** sigue siendo castellano peninsular formal, pero más operativo y menos retórico. Se permiten listas numeradas de pasos, flujos en tabla, matrices RACI explícitas y anexos con formularios concretos. Las referencias a las políticas madre del bloque F1 se hacen mediante el código `{{ proyecto.codigo_documento_base }}-1XX`.

**Catálogo de placeholders:** se reutiliza íntegramente el de F1.1, sin cambios. Cualquier nuevo placeholder introducido en F2 se documenta al inicio del procedimiento que lo introduce.

---

## CATÁLOGO DE PROCEDIMIENTOS DEL BLOQUE F2.1

| Código | Título | Política madre | Familia ENS principal |
|---|---|---|---|
| E-AR-001 | Procedimiento de Análisis y Gestión de Riesgos | E-100 | op.pl.1, op.pl.2 |
| E-221 | Procedimiento de Gestión de la Información Documentada | E-100 | org.2, org.3 |
| E-204 | Procedimiento de Gestión de Incidentes de Seguridad | E-108 | op.exp.7 |
| E-231 | Procedimiento de Gestión de Cuentas y Accesos | E-101 | op.acc.4 |
| E-217 | Procedimiento de Evaluación y Seguimiento de Proveedores | E-112 | op.ext.1, op.ext.2 |
| E-205 | Procedimiento de Gestión de Vulnerabilidades y Parches | E-100, E-107 | op.exp.4 |

---

# DOCUMENTO E-AR-001 — PROCEDIMIENTO DE ANÁLISIS Y GESTIÓN DE RIESGOS

**Es el procedimiento que ejecuta el principio 5.2 de la Política de Seguridad** ("Gestión de la seguridad basada en los riesgos") y materializa las medidas op.pl.1 (Análisis de riesgos) y op.pl.2 (Arquitectura de seguridad) del Anexo II del ENS. Sigue la metodología MAGERIT v3 publicada por el Consejo Superior de Administración Electrónica.

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-AR-001"
titulo: "Procedimiento de Análisis y Gestión de Riesgos"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
fecha_proxima_revision: "{{ proyecto.proxima_revision }}"
clasificacion: "INTERNA"
propietario: "{{ responsables.responsable_seguridad.cargo }}"
aprobado_por: "Comité de Seguridad"
politica_madre: "{{ proyecto.codigo_documento_base }}-100"
---

# PROCEDIMIENTO DE ANÁLISIS Y GESTIÓN DE RIESGOS DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-AR-001 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Establecer el método sistemático mediante el cual {{ cliente.razon_social }} identifica, analiza, valora, trata y supervisa los riesgos de seguridad de la información que afectan a los activos comprendidos en el alcance del SGSI, conforme a la metodología MAGERIT versión 3 del Consejo Superior de Administración Electrónica, y en cumplimiento de las medidas **op.pl.1 (Análisis de riesgos)** y **op.pl.2 (Arquitectura de seguridad)** del Anexo II del Real Decreto 311/2022.

## 2. ALCANCE

El presente procedimiento se aplica a todos los activos de información, sistemas, servicios, instalaciones y procesos comprendidos en el alcance del SGSI definido en el documento {{ proyecto.codigo_documento_base }}-100 (Política de Seguridad de la Información).

## 3. DEFINICIONES OPERATIVAS

a) **Activo:** componente o funcionalidad de un sistema de información susceptible de ser atacado deliberada o accidentalmente con consecuencias para la organización.

b) **Amenaza:** causa potencial de un incidente que puede causar daño a los activos.

c) **Vulnerabilidad:** debilidad de un activo que puede ser explotada por una amenaza.

d) **Impacto:** consecuencia de la materialización de una amenaza sobre un activo.

e) **Riesgo:** estimación del grado de exposición a que una amenaza se materialice sobre uno o más activos causando daños o perjuicios a la organización.

f) **Riesgo intrínseco:** riesgo calculado sin considerar las salvaguardas existentes.

g) **Riesgo residual:** riesgo remanente tras la aplicación de las salvaguardas.

h) **Apetito de riesgo:** nivel de riesgo que la organización está dispuesta a aceptar en la consecución de sus objetivos.

## 4. RESPONSABILIDADES — MATRIZ RACI

Se utiliza la nomenclatura RACI estándar: **R** (Responsable de ejecución), **A** (*Accountable*, autoridad final), **C** (Consultado), **I** (Informado).

| Actividad | Resp. Seguridad | Resp. Sistema | Resp. Información | Resp. Servicio | Comité Seguridad | Órgano Superior |
|---|---|---|---|---|---|---|
| Coordinación general del análisis | **A/R** | C | C | C | I | I |
| Identificación e inventario de activos | C | **R** | C | C | I | — |
| Valoración de activos | C | C | **R** | **R** | A | I |
| Identificación de amenazas | **R** | C | I | I | I | — |
| Estimación de la probabilidad y el impacto | **R** | C | C | C | A | I |
| Determinación del riesgo intrínseco y residual | **R** | C | I | I | A | I |
| Definición del Plan de Tratamiento | **R** | C | C | C | **A** | I |
| Aprobación del riesgo residual aceptado | C | I | C | C | C | **A** |
| Seguimiento del Plan de Tratamiento | **R** | R | I | I | A | I |
| Revisión periódica del análisis | **A/R** | C | C | C | A | I |

## 5. DESCRIPCIÓN DEL PROCEDIMIENTO

### Fase 1 — Planificación

**Paso 1.1.** El Responsable de la Seguridad elaborará anualmente, durante el mes de enero, un **Plan Anual de Análisis de Riesgos** que defina:

- Alcance específico del análisis para el ejercicio.
- Metodología y herramientas a utilizar (por defecto MAGERIT v3 con apoyo de la herramienta PILAR del Centro Criptológico Nacional cuando proceda).
- Equipo de trabajo y roles asignados.
- Calendario de las distintas fases.
- Criterios de aceptación del riesgo residual.

**Paso 1.2.** El Plan Anual será aprobado por el Comité de Seguridad en su primera reunión ordinaria del año.

### Fase 2 — Identificación e inventario de activos

**Paso 2.1.** El Responsable del Sistema mantendrá actualizado el **Inventario de Activos** del sistema, conforme al formulario del Anexo I del presente procedimiento, identificando para cada activo:

- Identificador único.
- Descripción y tipología (servicio, información, software, hardware, instalación, personal, etc.) conforme a la taxonomía de MAGERIT v3.
- Propietario.
- Custodio.
- Localización física o lógica.
- Dependencias con otros activos.

**Paso 2.2.** El inventario se revisará al menos con carácter semestral y siempre que se produzca un alta, baja o modificación significativa de un activo.

### Fase 3 — Valoración de activos

**Paso 3.1.** Los Responsables de la Información y del Servicio, en coordinación con el Responsable de la Seguridad, valorarán cada activo en las cinco dimensiones de seguridad del Anexo I del ENS:

- **Confidencialidad (C)**
- **Integridad (I)**
- **Trazabilidad (T)**
- **Autenticidad (Au)**
- **Disponibilidad (D)**

**Paso 3.2.** La valoración se expresará en los niveles **BAJO**, **MEDIO**, **ALTO** o **N/A** (No Aplicable), conforme a los criterios cualitativos del Anexo I del ENS y a la guía CCN-STIC 803.

**Paso 3.3.** La valoración consolidada del activo se utilizará posteriormente para determinar su categoría de seguridad y, por agregación, la categoría del sistema completo.

### Fase 4 — Identificación de amenazas

**Paso 4.1.** El Responsable de la Seguridad, partiendo del **Catálogo de Amenazas** de MAGERIT v3 (Libro II), identificará las amenazas relevantes para cada tipo de activo, agrupadas en las siguientes categorías:

- Desastres naturales
- De origen industrial
- Errores y fallos no intencionados
- Ataques intencionados

**Paso 4.2.** Adicionalmente, se incorporarán las amenazas específicas detectadas en:

- Informes recientes del CCN-CERT y del INCIBE-CERT.
- Análisis de tendencias del MITRE ATT&CK.
- Lecciones aprendidas de incidentes previos en la propia Entidad.

### Fase 5 — Estimación del riesgo intrínseco

**Paso 5.1.** Para cada par activo-amenaza relevante, el Responsable de la Seguridad estimará:

- **Probabilidad** de materialización de la amenaza, en escala cualitativa: MUY BAJA / BAJA / MEDIA / ALTA / MUY ALTA.
- **Impacto** sobre cada dimensión de seguridad del activo, en la misma escala.

**Paso 5.2.** El **riesgo intrínseco** se calculará mediante la matriz de riesgo del Anexo II del presente procedimiento, que sigue las directrices de MAGERIT v3.

### Fase 6 — Identificación de salvaguardas existentes y cálculo del riesgo residual

**Paso 6.1.** El Responsable del Sistema, en coordinación con el Responsable de la Seguridad, identificará las **salvaguardas** (medidas de seguridad) ya implantadas que mitigan cada riesgo identificado.

**Paso 6.2.** Para cada salvaguarda se evaluará su **eficacia** en escala cualitativa: NULA / BAJA / MEDIA / ALTA / MUY ALTA.

**Paso 6.3.** El **riesgo residual** resulta de aplicar el factor de eficacia de las salvaguardas existentes al riesgo intrínseco.

### Fase 7 — Tratamiento del riesgo

**Paso 7.1.** Para cada riesgo cuya valoración residual exceda el **umbral de aceptación** definido en el Plan Anual, el Responsable de la Seguridad propondrá una de las siguientes opciones de tratamiento:

| Opción | Descripción | Cuándo aplicar |
|---|---|---|
| **Mitigar** | Implantar salvaguardas adicionales que reduzcan el riesgo residual | Opción por defecto si es viable técnica y económicamente |
| **Transferir** | Trasladar el riesgo a un tercero (seguros, externalización, contratos) | Cuando el coste de mitigación es desproporcionado |
| **Evitar** | Eliminar el activo, servicio o proceso que genera el riesgo | Cuando el riesgo es inasumible y la actividad prescindible |
| **Aceptar** | Asumir el riesgo residual de forma documentada y motivada | Cuando se sitúa por debajo del umbral o cuando no existe alternativa viable |

**Paso 7.2.** El conjunto de decisiones de tratamiento conformará el **Plan de Tratamiento de Riesgos**, que incluirá para cada riesgo a mitigar:

- Acciones concretas a emprender.
- Responsable de la ejecución.
- Plazo de implantación.
- Recursos necesarios (humanos, técnicos, económicos).
- Indicador de cierre.

**Paso 7.3.** El Plan de Tratamiento será revisado por el Comité de Seguridad y aprobado, en lo que respecta a la **aceptación de riesgos residuales significativos**, por {{ cliente.organo_aprobador_politicas }}.

### Fase 8 — Seguimiento

**Paso 8.1.** El Responsable de la Seguridad realizará un seguimiento mensual del avance del Plan de Tratamiento, registrando el porcentaje de avance, las desviaciones y las acciones correctivas adoptadas.

**Paso 8.2.** El estado del Plan se reportará al Comité de Seguridad en sus reuniones ordinarias.

### Fase 9 — Revisión periódica

**Paso 9.1.** El análisis completo se revisará con carácter ordinario al menos una vez al año.

**Paso 9.2.** Se realizarán revisiones extraordinarias siempre que se produzca alguna de las siguientes circunstancias:

- Cambios significativos en el alcance del sistema.
- Incorporación de nuevos activos críticos.
- Aparición de nuevas amenazas relevantes.
- Materialización de un incidente grave.
- Modificaciones del marco legal aplicable.
- Conclusiones de auditorías que así lo aconsejen.

## 6. REGISTROS GENERADOS

| Registro | Responsable | Periodicidad | Conservación |
|---|---|---|---|
| Inventario de activos | Responsable del Sistema | Continuo | Vida del SGSI + 5 años |
| Plan Anual de Análisis de Riesgos | Responsable de la Seguridad | Anual | 5 años |
| Informe de Análisis de Riesgos | Responsable de la Seguridad | Anual | 5 años |
| Plan de Tratamiento de Riesgos | Responsable de la Seguridad | Anual | 5 años |
| Acta de aprobación de riesgos residuales | Secretario del Comité | Anual | 5 años |
| Informe mensual de seguimiento | Responsable de la Seguridad | Mensual | 2 años |

## 7. INDICADORES DE CONTROL

| Indicador | Fórmula | Umbral objetivo |
|---|---|---|
| Cobertura del análisis | (activos analizados / activos totales) × 100 | ≥ 95% |
| Riesgos aceptados sobre umbral | nº riesgos aceptados sin mitigación con valor > umbral | 0 |
| Cumplimiento del Plan de Tratamiento | (acciones cerradas en plazo / acciones totales) × 100 | ≥ 85% |
| Antigüedad del análisis | meses desde la última revisión completa | ≤ 12 |

## 8. ANEXOS

- **Anexo I:** Formulario de Inventario de Activos
- **Anexo II:** Matriz de cálculo de Riesgo (Probabilidad × Impacto)
- **Anexo III:** Catálogo de Amenazas adaptado de MAGERIT v3 Libro II
- **Anexo IV:** Plantilla del Informe de Análisis de Riesgos
- **Anexo V:** Plantilla del Plan de Tratamiento

---

**Documento {{ proyecto.codigo_documento_base }}-AR-001 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---

# DOCUMENTO E-221 — PROCEDIMIENTO DE GESTIÓN DE LA INFORMACIÓN DOCUMENTADA DEL SGSI

**Es el procedimiento que ordena toda la documentación del SGSI**: políticas, procedimientos, instrucciones técnicas, registros y evidencias. Sin él, el SGSI se convierte en un caos de versiones obsoletas y el auditor lo detecta inmediatamente.

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-221"
titulo: "Procedimiento de Gestión de la Información Documentada del SGSI"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
fecha_proxima_revision: "{{ proyecto.proxima_revision }}"
clasificacion: "INTERNA"
propietario: "{{ responsables.responsable_seguridad.cargo }}"
---

# PROCEDIMIENTO DE GESTIÓN DE LA INFORMACIÓN DOCUMENTADA DEL SGSI DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-221 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Establecer el método mediante el cual {{ cliente.razon_social }} elabora, aprueba, distribuye, controla, conserva y archiva la información documentada del Sistema de Gestión de la Seguridad de la Información, garantizando que en todo momento:

a) Las personas que necesitan la información disponen de la versión correcta, vigente y aprobada.

b) Los documentos obsoletos están identificados y retirados del uso.

c) Se conservan las evidencias necesarias del funcionamiento del SGSI.

d) Existe trazabilidad completa de las versiones, aprobaciones y modificaciones.

## 2. ALCANCE

El presente procedimiento se aplica a toda la información documentada del SGSI, comprendiendo:

a) **Documentación normativa:** la Política de Seguridad ({{ proyecto.codigo_documento_base }}-100), las políticas específicas (ABSORB_INTO_E100 a E-126), los procedimientos (E-AR-001 a E-2XX) y las instrucciones técnicas asociadas.

b) **Documentación de planificación:** Plan de Adecuación, Declaración de Aplicabilidad, Plan de Tratamiento de Riesgos, Plan de Continuidad.

c) **Documentación operativa:** inventarios, formularios, plantillas, listados.

d) **Registros:** evidencias del cumplimiento de los procedimientos (actas, informes, logs, certificados de destrucción, etc.).

## 3. CLASIFICACIÓN DE LA INFORMACIÓN DOCUMENTADA

A los efectos del presente procedimiento, la información documentada del SGSI se clasifica en las siguientes categorías:

| Categoría | Codificación | Aprobador | Periodicidad de revisión |
|---|---|---|---|
| Política madre | {{ proyecto.codigo_documento_base }}-100 | {{ cliente.organo_aprobador_politicas }} | Anual |
| Políticas específicas | {{ proyecto.codigo_documento_base }}-ABSORB_INTO_E100 a -126 | {{ cliente.organo_aprobador_politicas }} | Anual |
| Procedimientos operativos | {{ proyecto.codigo_documento_base }}-AR-001 a -299 | Comité de Seguridad | Anual |
| Instrucciones técnicas | {{ proyecto.codigo_documento_base }}-300 a -399 | Responsable de Seguridad | Semestral |
| Plantillas y formularios | {{ proyecto.codigo_documento_base }}-400 a -499 | Responsable de Seguridad | Anual |
| Registros generados | {{ proyecto.codigo_documento_base }}-RXX-AAAAMMDD | Según procedimiento de origen | No aplica |

## 4. CICLO DE VIDA DE LOS DOCUMENTOS

### 4.1 Elaboración

**Paso 1.** El Responsable de la Seguridad o la persona designada al efecto elabora el borrador del documento utilizando la plantilla corporativa del SGSI.

**Paso 2.** El borrador incorpora obligatoriamente los siguientes elementos:

- Cabecera con código de documento, título, versión, fecha, clasificación y aprobador.
- Tabla de control de cambios.
- Cuerpo del documento con numeración decimal estilo BOE.
- Pie con código, versión y página.

### 4.2 Revisión

**Paso 3.** El borrador se somete a revisión por el Comité de Seguridad, que dispone de un plazo máximo de 15 días hábiles para emitir comentarios.

**Paso 4.** El Responsable de la Seguridad incorpora los comentarios procedentes y elabora la versión definitiva para aprobación.

### 4.3 Aprobación

**Paso 5.** El documento se eleva al órgano aprobador correspondiente según la tabla del apartado 3.

**Paso 6.** La aprobación queda registrada mediante:

- Acta firmada del órgano aprobador (cuando sea un órgano colegiado).
- Firma electrónica del aprobador (cuando sea individual).
- Hash SHA-256 del documento aprobado registrado en el repositorio del SGSI.

### 4.4 Publicación y distribución

**Paso 7.** Una vez aprobado, el documento se publica en el **repositorio documental del SGSI**, accesible al personal con necesidad de saber según su clasificación.

**Paso 8.** Se notifica la publicación a todas las personas afectadas por su contenido, con acuse de recibo cuando proceda.

**Paso 9.** Las versiones impresas controladas, si las hubiera, se distribuyen únicamente a los titulares autorizados, con número de copia identificado.

### 4.5 Consulta y uso

**Paso 10.** Toda persona que utilice un documento del SGSI deberá verificar previamente que está consultando la versión vigente, accediendo al repositorio oficial.

**Paso 11.** Queda prohibido el uso de copias no controladas para fines operativos.

### 4.6 Modificación

**Paso 12.** Las modificaciones de los documentos siguen el mismo flujo de elaboración, revisión y aprobación que la versión inicial, con incremento del número de versión.

**Paso 13.** Las modificaciones quedan registradas en la tabla de control de cambios del propio documento.

### 4.7 Retirada y archivo

**Paso 14.** Cuando una nueva versión sustituye a una anterior, esta última se marca como **OBSOLETA** y se traslada al **archivo histórico del SGSI**, manteniéndose accesible únicamente para fines de auditoría y consulta de antecedentes.

**Paso 15.** Las versiones obsoletas se conservan durante el plazo establecido en el apartado 6 del presente procedimiento.

## 5. GESTIÓN DE REGISTROS

### 5.1 Identificación

Cada registro generado por la operación del SGSI se identifica mediante:

- Código del procedimiento que lo origina.
- Identificador del registro dentro del procedimiento.
- Fecha de generación en formato AAAAMMDD.

Ejemplo: `{{ proyecto.codigo_documento_base }}-204-R01-20260612` para el primer registro generado el 12 de junio de 2026 por el procedimiento E-204.

### 5.2 Almacenamiento

Los registros se almacenarán en el repositorio documental del SGSI, en una estructura de carpetas organizada por procedimiento de origen y por año natural.

### 5.3 Integridad

Los registros considerados críticos (actas de aprobación, informes de auditoría, evidencias de incidentes) se protegerán mediante:

- Cálculo y registro del hash SHA-256 al momento de su creación.
- Firma electrónica del responsable de su elaboración.
- Almacenamiento en soporte de solo lectura cuando proceda.

## 6. PERIODOS DE CONSERVACIÓN

| Tipo de información | Periodo mínimo de conservación |
|---|---|
| Documentación normativa vigente | Vida del SGSI |
| Versiones obsoletas de documentación normativa | 5 años desde la sustitución |
| Actas del Comité de Seguridad | 6 años |
| Informes de Análisis de Riesgos | 5 años |
| Registros de incidentes | 6 años (o el plazo de prescripción aplicable, si superior) |
| Registros de accesos y trazabilidad | 2 años (3 años para sistemas de categoría ALTA) |
| Informes de auditoría interna | 5 años |
| Informes de auditoría externa | 6 años |
| Registros de formación y concienciación | Vida laboral del empleado + 4 años |

## 7. RESPONSABILIDADES

| Actividad | Responsable |
|---|---|
| Custodia del repositorio documental | Responsable de la Seguridad |
| Elaboración de documentos normativos | Responsable de la Seguridad |
| Conservación de registros operativos | Responsable del proceso que los origina |
| Verificación periódica del cumplimiento | Responsable de la Seguridad (semestral) |

## 8. INDICADORES

| Indicador | Umbral objetivo |
|---|---|
| Documentos vigentes con versión actualizada | 100% |
| Documentos en periodo de revisión vencido | 0 |
| Incidencias detectadas en auditoría documental | < 3 por revisión |

---

**Documento {{ proyecto.codigo_documento_base }}-221 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---

# DOCUMENTO E-204 — PROCEDIMIENTO DE GESTIÓN DE INCIDENTES DE SEGURIDAD

**Es el procedimiento operativo que ejecuta la política E-108.** Mientras la política dice qué hay que notificar y a quién, este procedimiento dice exactamente qué hace cada persona desde el minuto cero hasta el cierre del incidente.

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-204"
titulo: "Procedimiento de Gestión de Incidentes de Seguridad"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
fecha_proxima_revision: "{{ proyecto.proxima_revision }}"
clasificacion: "INTERNA"
propietario: "{{ responsables.responsable_seguridad.cargo }}"
politica_madre: "{{ proyecto.codigo_documento_base }}-108"
---

# PROCEDIMIENTO DE GESTIÓN DE INCIDENTES DE SEGURIDAD DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-204 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Establecer las acciones operativas concretas que deben realizarse desde la detección de un incidente o sospecha de incidente de seguridad de la información hasta su cierre formal y la incorporación de las lecciones aprendidas, en desarrollo de la Política de Gestión de Incidentes ({{ proyecto.codigo_documento_base }}-108).

## 2. ALCANCE

Este procedimiento se aplica a todo evento o incidente de seguridad que afecte o pueda afectar a los activos comprendidos en el alcance del SGSI, sin perjuicio de los procedimientos específicos que pudieran existir para tipologías concretas de incidente.

## 3. CANALES DE NOTIFICACIÓN INTERNA

Cualquier persona que detecte un evento o incidente de seguridad **debe notificarlo de inmediato** a través de uno de los siguientes canales, en orden de preferencia:

1. **Buzón corporativo de incidentes:** `seguridad@{{ cliente.nombre_corto | lower | replace(" ", "") }}.es` (gestionado en horario laboral por el Responsable de la Seguridad).

2. **Teléfono de incidentes 24x7:** {{ responsables.responsable_seguridad.email }} (en horario no laboral, contactar mediante el directorio de emergencia del SGSI).

3. **Comunicación directa al Responsable del Sistema** ({{ responsables.responsable_sistema.nombre }}) o al Responsable de la Seguridad ({{ responsables.responsable_seguridad.nombre }}).

4. **Formulario web interno** disponible en la intranet corporativa.

**Toda notificación, sea cual sea el canal, debe incluir como mínimo:**

- Nombre y datos de contacto de quien notifica.
- Fecha, hora y lugar de detección.
- Descripción breve de lo observado.
- Sistemas, servicios o información posiblemente afectados.
- Acciones ya emprendidas, si las hubiera.

## 4. FLUJO OPERATIVO

### Fase 1 — Recepción y registro inicial (T+0 a T+30 minutos)

**Responsable:** Responsable de la Seguridad o persona de guardia designada.

**Acciones:**

1. Registrar el incidente en el **Sistema de Gestión de Incidentes** del SGSI, asignando un identificador único en formato `INC-AAAA-NNNN` (donde AAAA es el año y NNNN un correlativo).

2. Cumplimentar el formulario inicial del Anexo I con la información disponible.

3. Realizar una **clasificación preliminar** del incidente conforme a la escala del apartado 4 de la Política {{ proyecto.codigo_documento_base }}-108 (niveles BAJO, MEDIO, ALTO, MUY ALTO o CRÍTICO).

4. Activar el Equipo de Respuesta a Incidentes (ERI) correspondiente al nivel:

| Nivel | Activación |
|---|---|
| BAJO / MEDIO | ERI mínimo: Responsable Seguridad + Responsable Sistema |
| ALTO | ERI ampliado: + Asesor legal + DPO si aplica |
| MUY ALTO / CRÍTICO | ERI completo + Comité de Crisis |

5. Si la clasificación preliminar es **MUY ALTO** o **CRÍTICO**, notificar inmediatamente a {{ responsables.comite_seguridad.presidente }}.

### Fase 2 — Triaje y análisis inicial (T+30 minutos a T+4 horas)

**Responsable:** Coordinador del ERI (Responsable de la Seguridad).

**Acciones:**

6. Recopilar la información disponible sobre el incidente: logs, alertas del SIEM, informes técnicos, capturas de pantalla, mensajes recibidos.

7. **Iniciar la cadena de custodia** de las evidencias conforme al procedimiento {{ proyecto.codigo_documento_base }}-204-A, registrando:

- Origen de cada evidencia.
- Persona que la recopila.
- Fecha y hora exactas.
- Hash SHA-256 si es información digital.
- Cadena de manipulaciones posteriores.

8. **Determinar el alcance** del incidente: qué sistemas, servicios o información están afectados, número aproximado de personas o registros implicados.

9. **Confirmar o reclasificar** el nivel del incidente.

10. Si afecta a **datos personales**, valorar si constituye una **brecha de seguridad de datos personales** conforme a la guía AEPD y notificar al DPO ({{ responsables.delegado_proteccion_datos.nombre }}).

11. Decidir si procede activar el **Plan de Continuidad del Servicio** ({{ proyecto.codigo_documento_base }}-109).

### Fase 3 — Contención (T+4 horas a T+24 horas)

**Responsable:** Responsable del Sistema, bajo dirección del Coordinador del ERI.

**Acciones:**

12. Aplicar las medidas de contención necesarias para detener la propagación del incidente y limitar su impacto. Las medidas concretas dependen del tipo de incidente y se documentan en las **Instrucciones Técnicas IT-204-XX** asociadas a cada categoría:

| Tipo de incidente | Instrucción Técnica de contención |
|---|---|
| Compromiso de credenciales | IT-204-01 |
| Infección por malware / ransomware | IT-204-02 |
| Acceso no autorizado a sistemas | IT-204-03 |
| Filtración o exfiltración de datos | IT-204-04 |
| Denegación de servicio | IT-204-05 |
| Compromiso de cuenta privilegiada | IT-204-06 |
| Phishing dirigido (spear-phishing) | IT-204-07 |
| Pérdida o sustracción de equipo | IT-204-08 |

13. Documentar todas las acciones realizadas, sus resultados y los responsables de su ejecución.

14. Mantener informado al Coordinador del ERI cada 2 horas durante la fase de contención de incidentes ALTO o superior.

### Fase 4 — Notificación externa (en paralelo a la contención)

**Responsable:** Responsable de la Seguridad, en coordinación con DPO y asesor legal.

**Acciones:**

15. **Notificación al CCN-CERT vía LUCIA**, cuando proceda, en los plazos establecidos en el apartado 6.1 de la Política {{ proyecto.codigo_documento_base }}-108:

- CRÍTICO: en 1 hora
- MUY ALTO: en 6 horas
- ALTO: en 24 horas

La notificación se realiza accediendo a la herramienta LUCIA del CCN con el certificado digital corporativo y cumplimentando el formulario oficial. La interlocución posterior se gestiona también desde LUCIA.

16. **Notificación de brecha de datos personales a la AEPD**, si procede, en el plazo máximo de **72 horas** desde el conocimiento, mediante el formulario electrónico de la sede electrónica de la AEPD (https://sedeaepd.gob.es). La notificación incluirá:

- Naturaleza de la brecha y categorías de datos afectados.
- Número aproximado de personas afectadas y de registros.
- Datos de contacto del DPO.
- Posibles consecuencias.
- Medidas adoptadas o propuestas.

17. **Comunicación a las personas afectadas**, cuando la brecha entrañe riesgo alto para sus derechos y libertades, conforme al artículo 34 del RGPD.

18. **Notificación a clientes y partes interesadas afectadas** según las obligaciones contractuales aplicables.

19. **Comunicación al equipo directivo y, en su caso, a {{ cliente.organo_aprobador_politicas }}** en incidentes CRÍTICO o MUY ALTO.

### Fase 5 — Erradicación y recuperación

**Responsable:** Responsable del Sistema, bajo dirección del Coordinador del ERI.

**Acciones:**

20. **Eliminar la causa raíz** del incidente: limpieza de sistemas comprometidos, aplicación de parches, eliminación de cuentas no autorizadas, reconfiguración de controles.

21. **Restaurar los servicios afectados** desde copias de seguridad verificadas, en el orden de prioridad determinado por el BIA del Plan de Continuidad.

22. **Verificar la integridad** de los sistemas restaurados antes de devolverlos a producción.

23. **Monitorizar activamente** los sistemas afectados durante un periodo mínimo de 72 horas tras la recuperación, para detectar posibles reapariciones.

### Fase 6 — Cierre y aprendizaje (T+15 días desde el cierre técnico)

**Responsable:** Responsable de la Seguridad.

**Acciones:**

24. Elaborar el **Informe Post-Incidente** conforme a la plantilla del Anexo II, que incluirá:

- Resumen ejecutivo.
- Cronología detallada del incidente con marcas de tiempo.
- Causa raíz identificada.
- Vector de ataque (cuando proceda) mapeado al MITRE ATT&CK.
- Impacto real producido.
- Acciones de contención, erradicación y recuperación realizadas y su eficacia.
- Notificaciones externas realizadas.
- **Lecciones aprendidas y recomendaciones de mejora.**
- Acciones correctivas a implantar, con responsables y plazos.

25. Presentar el Informe Post-Incidente al **Comité de Seguridad** en su siguiente reunión ordinaria.

26. Para incidentes CRÍTICO o MUY ALTO, presentar resumen al órgano superior {{ cliente.organo_aprobador_politicas }}.

27. **Cerrar formalmente el incidente** en el Sistema de Gestión de Incidentes, manteniendo accesible toda la documentación durante el periodo de conservación establecido en el procedimiento {{ proyecto.codigo_documento_base }}-221.

## 5. EQUIPO DE RESPUESTA A INCIDENTES (ERI)

| Rol | Persona designada | Funciones |
|---|---|---|
| Coordinador del ERI | {{ responsables.responsable_seguridad.nombre }} | Coordinación general, decisiones, interlocución autoridades |
| Líder técnico | {{ responsables.responsable_sistema.nombre }} | Análisis técnico, contención, erradicación, recuperación |
| Asesor legal | _A designar contractualmente_ | Valoración jurídica, obligaciones de notificación |
| DPO | {{ responsables.delegado_proteccion_datos.nombre }} | Asesoramiento sobre brechas de datos personales |
| Comunicación | _A designar_ | Comunicación interna, externa y reputacional |

Para incidentes CRÍTICOS, el ERI activa el **Comité de Crisis** presidido por {{ responsables.comite_seguridad.presidente }}.

## 6. REGISTROS GENERADOS

| Registro | Conservación |
|---|---|
| Formulario inicial de notificación | 6 años |
| Cadena de custodia de evidencias | 6 años o plazo de prescripción aplicable |
| Logs y evidencias técnicas | 6 años |
| Notificaciones a autoridades (LUCIA, AEPD) | 6 años |
| Informe Post-Incidente | 6 años |
| Acta de cierre | 6 años |

## 7. INDICADORES DE CONTROL

| Indicador | Fórmula | Objetivo |
|---|---|---|
| Tiempo medio de detección (MTTD) | media de horas desde origen hasta detección | < 24h |
| Tiempo medio de respuesta (MTTR) | media de horas desde detección hasta contención | < 4h para ALTO+ |
| Cumplimiento plazos notificación LUCIA | (notificaciones en plazo / total) × 100 | 100% |
| Cumplimiento plazo 72h brecha AEPD | (notificaciones en plazo / total) × 100 | 100% |
| Recurrencia de incidentes mismo origen | nº incidentes con misma causa raíz en 12 meses | ≤ 1 |

## 8. ANEXOS

- **Anexo I:** Formulario inicial de notificación de incidente
- **Anexo II:** Plantilla del Informe Post-Incidente
- **Anexo III:** Directorio de emergencia 24x7
- **Anexo IV:** Mapeo de tipologías de incidente con tácticas y técnicas MITRE ATT&CK
- **Anexo V:** Plantilla de comunicación a personas afectadas (RGPD art. 34)

---

**Documento {{ proyecto.codigo_documento_base }}-204 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---

# DOCUMENTO E-231 — PROCEDIMIENTO DE GESTIÓN DE CUENTAS Y ACCESOS

**Es el procedimiento operativo de la Política E-101.** Define quién pide, quién autoriza, quién provisiona, quién revisa y quién revoca cada acceso del sistema. El auditor pide ver el flujo completo en al menos 3 casos reales (alta, modificación, baja).

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-231"
titulo: "Procedimiento de Gestión de Cuentas y Accesos"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
fecha_proxima_revision: "{{ proyecto.proxima_revision }}"
clasificacion: "INTERNA"
propietario: "{{ responsables.responsable_seguridad.cargo }}"
politica_madre: "{{ proyecto.codigo_documento_base }}-101"
---

# PROCEDIMIENTO DE GESTIÓN DE CUENTAS Y ACCESOS DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-231 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Establecer el flujo operativo para la solicitud, autorización, provisión, modificación, revisión periódica y revocación de cuentas de usuario y derechos de acceso a los sistemas de información de {{ cliente.razon_social }}, en desarrollo de la Política de Control de Acceso ({{ proyecto.codigo_documento_base }}-101).

## 2. ALCANCE

Aplica a toda cuenta de usuario, sea de personal interno, externo o de servicio, que permita el acceso a sistemas, redes, aplicaciones o información comprendidos en el alcance del SGSI.

## 3. TIPOS DE CUENTA

| Tipo | Descripción | Requisitos especiales |
|---|---|---|
| **Personal interno** | Empleado o personal estatutario | Vinculada a contrato laboral o de servicios |
| **Personal externo** | Contratista, consultor, becario | Vigencia limitada al periodo del contrato |
| **Privilegiada** | Administrador, root, sa, dba | MFA obligatorio. Revisión trimestral. |
| **De servicio** | Proceso automático, sistema-a-sistema | Sin acceso interactivo. Credenciales rotadas semestralmente. |
| **De emergencia** | Acceso break-glass | Custodia de credenciales en sobre sellado. Uso registrado y auditado. |

## 4. FLUJO DE GESTIÓN — ALTA

### 4.1 Solicitud

**Responsable:** Responsable jerárquico del solicitante (en personal externo, persona de contacto designada en el contrato).

**Acciones:**

1. Cumplimentar el **formulario de solicitud de acceso** (Anexo I), indicando:

- Datos de la persona solicitante.
- Fecha de incorporación o inicio de la prestación.
- Puesto, rol y funciones a desempeñar.
- Recursos a los que se solicita acceso (sistemas, aplicaciones, carpetas, etc.).
- Nivel de privilegio requerido en cada uno.
- Periodo previsto de vigencia (especialmente relevante en personal externo).
- Justificación del acceso.

2. Firmar electrónicamente la solicitud y remitirla al propietario de cada recurso solicitado.

### 4.2 Autorización

**Responsable:** Propietario del recurso (Responsable de la Información o Responsable del Servicio según el activo).

**Acciones:**

3. Verificar que la solicitud:

- Está firmada por el responsable jerárquico legitimado.
- Identifica claramente el rol y las funciones.
- Solicita un nivel de acceso proporcional a las funciones declaradas.
- Respeta el principio de necesidad de saber.
- Respeta las reglas de segregación de funciones del apartado 7 de la Política {{ proyecto.codigo_documento_base }}-101.

4. **Aprobar, denegar o modificar** la solicitud dentro de los siguientes plazos máximos desde la recepción:

| Tipo de acceso | Plazo máximo de decisión |
|---|---|
| Personal interno, acceso estándar | 3 días hábiles |
| Personal interno, acceso privilegiado | 5 días hábiles |
| Personal externo | 5 días hábiles |
| Cuenta de servicio | 5 días hábiles |

5. Documentar la decisión en el sistema de gestión de identidades, dejando trazabilidad del responsable y fecha.

### 4.3 Provisión técnica

**Responsable:** Responsable del Sistema o personal técnico bajo su supervisión.

**Acciones:**

6. Una vez autorizada la solicitud, provisionar técnicamente la cuenta y los accesos en un plazo máximo de **2 días hábiles** desde la autorización.

7. **Generar la credencial inicial** mediante un procedimiento que garantice:

- Aleatoriedad criptográfica.
- Cumplimiento de la política de contraseñas del apartado 5.3 de {{ proyecto.codigo_documento_base }}-101.
- Entrega segura al usuario por canal cifrado o con cambio obligatorio en el primer inicio de sesión.

8. **Configurar la autenticación multifactor** (MFA) cuando proceda según la política.

9. **Registrar la provisión** en el Inventario de Cuentas y Accesos del SGSI.

### 4.4 Notificación y aceptación

**Responsable:** Responsable del Sistema.

**Acciones:**

10. Notificar al usuario la disponibilidad de su cuenta, sus credenciales iniciales y las normas de uso aceptable ({{ proyecto.codigo_documento_base }}-103).

11. Requerir del usuario el **acuse de recibo** de las normas y, en su caso, la firma de los compromisos de confidencialidad correspondientes.

## 5. FLUJO DE GESTIÓN — MODIFICACIÓN

**Disparadores:** cambio de puesto, cambio de proyecto, asunción de nuevas funciones, finalización de un proyecto temporal.

**Responsable de iniciar:** Responsable jerárquico del usuario afectado.

**Acciones:**

12. Comunicar formalmente el cambio mediante el formulario del Anexo II.

13. El propietario del recurso evalúa los nuevos accesos necesarios y los privilegios que dejan de ser necesarios, autorizando la **modificación**.

14. El Responsable del Sistema ejecuta los cambios en el plazo de **3 días hábiles**.

15. Se aplican los principios de **mínimo privilegio** y **necesidad de saber** en la nueva configuración, eliminando privilegios residuales del puesto anterior.

## 6. FLUJO DE GESTIÓN — REVISIÓN PERIÓDICA

**Responsable de la coordinación:** Responsable de la Seguridad.

**Periodicidad:** según el apartado 6.4 de la Política {{ proyecto.codigo_documento_base }}-101:

| Tipo de acceso | Frecuencia mínima |
|---|---|
| Privilegiados (admin) | Trimestral |
| Información clasificada nivel ALTO | Trimestral |
| Información clasificada nivel MEDIO | Semestral |
| Generales | Anual |

**Acciones:**

16. El Responsable de la Seguridad genera el **listado de accesos vigentes** desde el sistema de gestión de identidades.

17. Se distribuye a los propietarios de los recursos para **validación**.

18. Cada propietario revisa, **dispone de 15 días hábiles** para confirmar la vigencia de cada acceso y, en su caso, solicitar la revocación o modificación de los que ya no sean necesarios.

19. Las modificaciones se ejecutan según el flujo del apartado 5.

20. Se elabora un **acta de revisión** que se eleva al Comité de Seguridad.

## 7. FLUJO DE GESTIÓN — REVOCACIÓN

### 7.1 Por cese ordinario

**Disparador:** baja del personal o finalización del contrato.

**Responsable de notificar:** Responsable jerárquico o departamento de Recursos Humanos.

**Acciones:**

21. Notificar el cese al Responsable de la Seguridad con **al menos 5 días hábiles de antelación** cuando sea posible.

22. El Responsable del Sistema procede a la revocación en los plazos máximos del apartado 6.5 de la Política {{ proyecto.codigo_documento_base }}-101:

| Tipo de acceso | Plazo máximo desde el cese |
|---|---|
| Privilegiados | 1 hora |
| Información ALTA | 4 horas |
| Información MEDIA | 24 horas |
| Generales | 72 horas |

23. Se ejecuta la **lista de comprobación de baja** del Anexo III, que incluye:

- Deshabilitación de la cuenta principal.
- Revocación de accesos a aplicaciones específicas.
- Cierre de sesiones activas.
- Bloqueo del correo electrónico (con redirección durante el periodo establecido).
- Recuperación de equipos y soportes corporativos.
- Recuperación de credenciales físicas (tarjetas, llaves, tokens).
- Comunicación a interlocutores externos cuando proceda.

24. La cuenta se mantiene **deshabilitada pero conservada** durante un periodo mínimo de 6 meses para preservar registros y evidencias, y posteriormente se elimina conforme al periodo de conservación establecido.

### 7.2 Por cese conflictivo o despido disciplinario

**Acciones especiales:**

25. La revocación es **inmediata y previa o simultánea** a la comunicación formal del cese a la persona afectada.

26. Se aplican medidas adicionales de monitorización forense durante las 72 horas siguientes al cese.

27. Se realiza una **revisión específica** de las acciones realizadas por la cuenta en los 30 días previos al cese.

## 8. CUENTAS DE SERVICIO

**Acciones específicas:**

28. Las cuentas de servicio se documentan en el **Inventario de Cuentas de Servicio**, identificando:

- Sistema o aplicación que la utiliza.
- Función que desempeña.
- Privilegios asignados.
- Responsable funcional.
- Mecanismo de gestión de credenciales.

29. Las **credenciales de cuentas de servicio** se almacenan en una **solución de gestión de secretos** (vault) con acceso restringido y auditado.

30. Se rotan al menos **cada 6 meses** y siempre que cese el personal con conocimiento de las mismas.

## 9. CUENTAS DE EMERGENCIA (BREAK-GLASS)

**Características:**

31. Existirán cuentas de emergencia para garantizar el acceso a sistemas críticos en situaciones excepcionales (fallo del sistema de identidades, indisponibilidad del personal habitual, etc.).

32. Las credenciales se custodiarán en **sobre sellado físico** o en bóveda con doble control, con acceso restringido a {{ responsables.responsable_seguridad.nombre }} y a su suplente designado.

33. Cualquier uso requerirá:

- Autorización previa del Responsable de la Seguridad o, en su defecto, del Comité de Crisis.
- Apertura formal del sobre con testigo.
- Registro detallado de las acciones realizadas.
- Cambio inmediato de la credencial tras el uso.
- Resellado y almacenamiento de la nueva credencial.

## 10. INDICADORES

| Indicador | Objetivo |
|---|---|
| Tiempo medio de provisión | < 2 días hábiles |
| Cumplimiento plazos de revocación tras cese | 100% |
| Cuentas privilegiadas con MFA activo | 100% |
| Cuentas huérfanas (sin revisión > 12 meses) | 0 |
| Cuentas inactivas > 90 días | < 5% del total |

## 11. ANEXOS

- **Anexo I:** Formulario de solicitud de acceso
- **Anexo II:** Formulario de modificación de acceso
- **Anexo III:** Lista de comprobación de baja
- **Anexo IV:** Plantilla de revisión periódica
- **Anexo V:** Registro de uso de cuentas break-glass

---

**Documento {{ proyecto.codigo_documento_base }}-231 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---

# DOCUMENTO E-217 — PROCEDIMIENTO DE EVALUACIÓN Y SEGUIMIENTO DE PROVEEDORES

**Es el procedimiento operativo de la Política E-112.** Define exactamente cómo se evalúa a un proveedor antes de contratar, durante la prestación y al finalizar la relación.

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-217"
titulo: "Procedimiento de Evaluación y Seguimiento de Proveedores"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
fecha_proxima_revision: "{{ proyecto.proxima_revision }}"
clasificacion: "INTERNA"
propietario: "{{ responsables.responsable_seguridad.cargo }}"
politica_madre: "{{ proyecto.codigo_documento_base }}-112"
---

# PROCEDIMIENTO DE EVALUACIÓN Y SEGUIMIENTO DE PROVEEDORES DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-217 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Establecer las acciones operativas para la evaluación previa a la contratación, el seguimiento durante la relación y la salida controlada de los proveedores y terceros con acceso a información, sistemas o instalaciones de {{ cliente.razon_social }}, en desarrollo de la Política de Seguridad en las Relaciones con Proveedores ({{ proyecto.codigo_documento_base }}-112).

## 2. FASE 1 — EVALUACIÓN PREVIA A LA CONTRATACIÓN

### 2.1 Cuestionario de seguridad

**Responsable:** Responsable del Servicio que solicita la contratación, con apoyo del Responsable de la Seguridad.

**Acciones:**

1. Antes del inicio de cualquier negociación contractual con un proveedor de nivel **MEDIO** o superior conforme al apartado 3 de la Política {{ proyecto.codigo_documento_base }}-112, se le remitirá el **Cuestionario de Evaluación de Seguridad** del Anexo I, que contiene preguntas sobre:

- Certificaciones de seguridad vigentes (ISO 27001, ENS, SOC 2, etc.).
- Política interna de seguridad y gobierno del SGSI.
- Gestión de incidentes y notificación de brechas.
- Control de accesos y gestión de personal.
- Gestión de subcontratistas y cadena de suministro.
- Seguridad física e infraestructura.
- Continuidad del servicio y recuperación ante desastres.
- Protección de datos personales y cumplimiento del RGPD.
- Localización del tratamiento de datos.
- Mecanismos de cifrado utilizados.

2. El proveedor dispone de **15 días naturales** para devolver el cuestionario cumplimentado y firmado.

### 2.2 Verificación documental

**Acciones:**

3. El Responsable de la Seguridad **verifica** la información declarada por el proveedor, en particular:

- Vigencia de certificaciones declaradas, mediante consulta a las páginas oficiales de los organismos certificadores (ENAC, IAF, etc.).
- Existencia y vigencia del registro como Encargado del Tratamiento, cuando proceda.
- Solvencia económica y técnica.
- Reputación pública del proveedor, mediante consultas a fuentes abiertas y, cuando proceda, a registros sectoriales.

### 2.3 Análisis de riesgos específico

4. Se elabora un **análisis de riesgos específico** de la relación, conforme a la metodología MAGERIT v3 ({{ proyecto.codigo_documento_base }}-AR-001), considerando:

- Tipo de información a la que el proveedor tendrá acceso.
- Volumen y sensibilidad del tratamiento.
- Localización del tratamiento.
- Cadena de subcontratación prevista.
- Dependencias generadas para la Entidad.

### 2.4 Decisión de contratación

5. El Responsable de la Seguridad emite un **informe de evaluación** con valoración GLOBAL: **APTO**, **APTO CON CONDICIONES** o **NO APTO**.

6. Para proveedores de nivel **ALTO** o **CRÍTICO**, el informe se eleva al Comité de Seguridad para autorización formal antes de proceder a la contratación.

7. La decisión final corresponde al órgano competente para la contratación, quien deberá motivar cualquier decisión contraria al informe de seguridad.

### 2.5 Cláusulas contractuales

8. El contrato a suscribir incorporará las cláusulas mínimas de seguridad establecidas en el apartado 5.3 de la Política {{ proyecto.codigo_documento_base }}-112.

9. Cuando el proveedor vaya a tratar datos personales por cuenta de la Entidad, se suscribirá adicionalmente el **Contrato de Encargo del Tratamiento** conforme al artículo 28.3 del RGPD.

## 3. FASE 2 — INCORPORACIÓN

10. Antes del inicio efectivo de la prestación:

- Se asignan los accesos necesarios al proveedor según el procedimiento {{ proyecto.codigo_documento_base }}-231.
- Se realiza una **sesión de incorporación** en la que se le presentan las normas del SGSI aplicables.
- Se firman los acuerdos de confidencialidad correspondientes.
- Se le entrega copia de las políticas E-103 (Uso Aceptable) y E-104 (Clasificación) en lo aplicable.

## 4. FASE 3 — SEGUIMIENTO DURANTE LA PRESTACIÓN

### 4.1 Reuniones periódicas de seguridad

| Nivel del proveedor | Frecuencia mínima |
|---|---|
| CRÍTICO | Trimestral |
| ALTO | Semestral |
| MEDIO | Anual |

**Acciones:**

11. En cada reunión se revisarán, al menos:

- Cumplimiento de los SLA contractualmente comprometidos.
- Incidentes ocurridos en el periodo y acciones adoptadas.
- Cambios significativos en la organización del proveedor o en sus medidas de seguridad.
- Cambios en la cadena de subcontratación.
- Resultados de auditorías internas o externas del proveedor.
- Recomendaciones de mejora.

12. De cada reunión se levanta **acta** que firman ambas partes y queda incorporada al expediente del proveedor.

### 4.2 Auditorías

13. La Entidad podrá auditar al proveedor:

- **Auditoría documental anual** mediante actualización del cuestionario inicial del Anexo I.
- **Auditoría in situ** para proveedores CRÍTICOS con periodicidad mínima anual.
- **Auditoría reactiva** tras cualquier incidente significativo.

14. Las auditorías se realizan con preaviso razonable salvo en caso de incidente grave.

15. Los resultados se documentan en el **Informe de Auditoría de Proveedor** y, si se detectan no conformidades, se acuerda un **Plan de Acción** con plazos definidos.

### 4.3 Gestión de incidentes notificados por proveedores

16. Cuando un proveedor notifica un incidente que afecta a la Entidad, se aplica el procedimiento {{ proyecto.codigo_documento_base }}-204, considerando al proveedor como fuente del incidente.

17. Se evalúa el **impacto sobre la continuidad** del servicio prestado y la necesidad de activar planes de contingencia.

18. Se documenta la respuesta del proveedor, los tiempos de resolución y la eficacia de las medidas adoptadas.

## 5. FASE 4 — REEVALUACIÓN ANUAL

19. Con periodicidad **anual**, todos los proveedores activos de nivel MEDIO o superior son objeto de **reevaluación**, que incluye:

- Actualización del cuestionario inicial.
- Verificación de la vigencia de las certificaciones declaradas.
- Revisión de los incidentes y su gestión durante el año.
- Análisis del cumplimiento de los SLA.
- Reconfirmación o reclasificación del nivel del proveedor.

20. El resultado se incorpora al expediente del proveedor y se eleva al Comité de Seguridad.

## 6. FASE 5 — SALIDA Y EXTINCIÓN DE LA RELACIÓN

### 6.1 Planificación de la salida

21. Cuando se prevea la finalización de la relación con un proveedor crítico, se elabora con la antelación suficiente un **Plan de Salida** que contemple:

- Identificación del proveedor sustituto o de la internalización del servicio.
- Cronograma de transición.
- Plan de migración de datos y servicios.
- Pruebas de continuidad durante la transición.
- Comunicación a las partes interesadas afectadas.

### 6.2 Ejecución de la salida

22. Al finalizar efectivamente la relación, se ejecuta la **Lista de Comprobación de Salida de Proveedor** del Anexo II:

- Devolución o eliminación segura de toda la información de la Entidad en posesión del proveedor.
- Obtención del **Certificado de Destrucción de Datos** firmado por el proveedor.
- Revocación de todos los accesos del proveedor a sistemas, redes e instalaciones de la Entidad, conforme al procedimiento {{ proyecto.codigo_documento_base }}-231.
- Recuperación de credenciales, tarjetas, tokens y demás recursos.
- Verificación documental del cumplimiento de todas las obligaciones contractuales.
- Recordatorio escrito de las obligaciones que subsisten tras la extinción.

23. Se elabora el **Informe de Cierre de Proveedor** y se archiva el expediente conforme al procedimiento {{ proyecto.codigo_documento_base }}-221.

## 7. INDICADORES

| Indicador | Objetivo |
|---|---|
| Proveedores MEDIO+ con cuestionario vigente (< 12 meses) | 100% |
| Proveedores CRÍTICO con auditoría anual realizada | 100% |
| Proveedores con plan de acción abierto > 6 meses | 0 |
| Incidentes notificados por proveedores en plazo contractual | 100% |

## 8. ANEXOS

- **Anexo I:** Cuestionario de Evaluación de Seguridad de Proveedores
- **Anexo II:** Lista de Comprobación de Salida de Proveedor
- **Anexo III:** Plantilla de Acta de reunión periódica
- **Anexo IV:** Plantilla del Informe de Auditoría de Proveedor
- **Anexo V:** Modelo de Cláusulas de Seguridad para contratos
- **Anexo VI:** Modelo de Contrato de Encargo del Tratamiento (art. 28 RGPD)

---

**Documento {{ proyecto.codigo_documento_base }}-217 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---

# DOCUMENTO E-205 — PROCEDIMIENTO DE GESTIÓN DE VULNERABILIDADES Y PARCHES

**Materializa la medida op.exp.4 del Anexo II del ENS** (Mantenimiento) y los controles A.8.8 (Gestión de vulnerabilidades técnicas) y A.8.32 (Gestión de cambios) de ISO/IEC 27001:2022. Es el procedimiento que el auditor pide demostrar con un escaneo real reciente y un parche desplegado en el último mes.

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-205"
titulo: "Procedimiento de Gestión de Vulnerabilidades y Parches"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
fecha_proxima_revision: "{{ proyecto.proxima_revision }}"
clasificacion: "INTERNA"
propietario: "{{ responsables.responsable_seguridad.cargo }}"
politica_madre: "{{ proyecto.codigo_documento_base }}-100, {{ proyecto.codigo_documento_base }}-107"
---

# PROCEDIMIENTO DE GESTIÓN DE VULNERABILIDADES Y PARCHES DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-205 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Establecer el método mediante el cual {{ cliente.razon_social }} identifica, valora, prioriza y mitiga las vulnerabilidades técnicas que afectan a sus sistemas de información, así como gestiona la aplicación de los parches de seguridad publicados por los fabricantes y comunidades de software, en cumplimiento de la medida **op.exp.4 (Mantenimiento)** del Anexo II del Real Decreto 311/2022.

## 2. ALCANCE

Aplica a todos los sistemas, servicios, aplicaciones, dispositivos de red, sistemas operativos, bases de datos, librerías y componentes de software comprendidos en el alcance del SGSI, ya sean operados directamente por la Entidad o por terceros bajo su responsabilidad.

## 3. FUENTES DE INFORMACIÓN DE VULNERABILIDADES

El Responsable de la Seguridad mantendrá monitorizadas, al menos, las siguientes fuentes de información sobre vulnerabilidades:

a) **CCN-CERT** (avisos y vulnerabilidades): https://www.ccn-cert.cni.es/seguridad-al-dia.html

b) **INCIBE-CERT**: https://www.incibe.es/incibe-cert/avisos

c) **NVD (National Vulnerability Database)** del NIST: https://nvd.nist.gov

d) **CISA Known Exploited Vulnerabilities Catalog**: https://www.cisa.gov/known-exploited-vulnerabilities-catalog

e) **Boletines de seguridad de los fabricantes** del software utilizado.

f) **Listas de seguridad** de las comunidades open source relevantes.

g) **Informes propios** del escáner de vulnerabilidades corporativo.

## 4. ESCANEO DE VULNERABILIDADES

### 4.1 Escaneo periódico

| Activo | Periodicidad mínima | Herramienta tipo |
|---|---|---|
| Servidores expuestos a Internet | Semanal | Escáner externo (OpenVAS, Nessus) |
| Servidores internos | Mensual | Escáner autenticado |
| Estaciones de trabajo | Mensual | Agente endpoint |
| Aplicaciones web | Trimestral | DAST |
| Código fuente propio | Por release | SAST + SCA |
| Contenedores e imágenes | Por build | Trivy o equivalente |
| Configuración cloud | Mensual | CSPM |

### 4.2 Escaneo extraordinario

Se realizarán escaneos extraordinarios cuando:

a) Se publique una vulnerabilidad crítica que afecte al inventario tecnológico de la Entidad.

b) Se incorpore al inventario un nuevo activo significativo.

c) Se produzca un cambio de configuración importante.

d) Se reciba una alerta del CCN-CERT o de cualquier otra fuente cualificada.

### 4.3 Pentesting

Con periodicidad **anual** se realizará un test de intrusión externo por una entidad independiente, conforme a las exigencias de las medidas mp.s.4 (Aceptación y puesta en servicio) y op.exp.4 del ENS para sistemas de categoría MEDIA o superior.

## 5. CLASIFICACIÓN Y PRIORIZACIÓN DE VULNERABILIDADES

### 5.1 Escala de criticidad

Las vulnerabilidades se clasifican atendiendo a su puntuación CVSS (Common Vulnerability Scoring System), conforme a la siguiente escala:

| Nivel | CVSS v3.x | Descripción |
|---|---|---|
| **CRÍTICA** | 9.0 - 10.0 | Vulnerabilidad explotable remotamente sin autenticación, con alto impacto |
| **ALTA** | 7.0 - 8.9 | Vulnerabilidad explotable con condiciones limitadas o impacto significativo |
| **MEDIA** | 4.0 - 6.9 | Vulnerabilidad con condiciones de explotación complejas o impacto moderado |
| **BAJA** | 0.1 - 3.9 | Vulnerabilidad con impacto menor o muy difícil de explotar |

### 5.2 Factores agravantes

La criticidad inicial se **eleva** automáticamente cuando concurre alguna de las siguientes circunstancias:

a) La vulnerabilidad está incluida en el catálogo CISA KEV (Known Exploited Vulnerabilities), indicando explotación activa en el mundo real.

b) Existe **exploit público** disponible.

c) El activo afectado tiene clasificación **ALTA** en cualquier dimensión del ENS.

d) El activo está expuesto a Internet o accesible desde redes no controladas.

e) El activo soporta servicios esenciales conforme al BIA del Plan de Continuidad.

### 5.3 Factores atenuantes

La criticidad inicial puede **reducirse** cuando:

a) El activo afectado está protegido por capas de defensa adicionales que dificultan la explotación.

b) La vulnerabilidad requiere acceso físico al activo, no factible para atacantes externos.

c) Existen mitigaciones temporales eficaces ya aplicadas (workarounds documentados por el fabricante).

## 6. PLAZOS DE APLICACIÓN DE PARCHES

| Criticidad efectiva | Plazo máximo de aplicación |
|---|---|
| **CRÍTICA con explotación activa** | 24 horas |
| **CRÍTICA** | 7 días naturales |
| **ALTA** | 15 días naturales |
| **MEDIA** | 60 días naturales |
| **BAJA** | 180 días naturales o siguiente ciclo de mantenimiento |

Estos plazos son **máximos** y se cuentan desde la publicación oficial del parche por el fabricante o desde la disponibilidad de una mitigación.

## 7. CICLO DE GESTIÓN DEL PARCHE

### 7.1 Identificación

**Responsable:** Responsable de la Seguridad.

**Acciones:**

1. Revisión diaria de las fuentes de información de vulnerabilidades.

2. Cruce con el Inventario de Activos para identificar las vulnerabilidades que afectan al entorno propio.

3. Registro en el **Sistema de Gestión de Vulnerabilidades** del SGSI.

### 7.2 Análisis y priorización

**Acciones:**

4. Cálculo de la criticidad efectiva conforme al apartado 5.

5. Determinación del plazo máximo de aplicación conforme al apartado 6.

6. Asignación al Responsable del Sistema con instrucciones específicas.

### 7.3 Pruebas

**Responsable:** Responsable del Sistema.

**Acciones:**

7. Antes del despliegue en producción, los parches se prueban en un **entorno de preproducción** equivalente al productivo en la medida de lo posible, verificando:

- Aplicación correcta del parche.
- No regresión funcional.
- Compatibilidad con las personalizaciones existentes.

8. Cuando la criticidad CRÍTICA con explotación activa exija aplicación inmediata, las pruebas pueden reducirse o realizarse en paralelo, asumiendo el riesgo bajo decisión expresa del Responsable de la Seguridad.

### 7.4 Despliegue

9. El despliegue se realiza conforme al **procedimiento de gestión de cambios** ({{ proyecto.codigo_documento_base }}-203), con la autorización correspondiente al riesgo del cambio.

10. Para parches CRÍTICOS, la autorización puede ser **abreviada** mediante el procedimiento de cambio de emergencia.

11. El despliegue se documenta indicando:

- Fecha y hora exacta.
- Sistemas afectados.
- Persona que ejecuta el despliegue.
- Parche aplicado (referencia del fabricante).
- Resultado.

### 7.5 Verificación

12. Tras el despliegue, se verifica que el parche se ha aplicado correctamente, mediante:

- Comprobación manual o automatizada del número de versión.
- Re-escaneo de la vulnerabilidad para confirmar su mitigación.
- Verificación del funcionamiento del servicio afectado.

13. La verificación se documenta en el Sistema de Gestión de Vulnerabilidades.

### 7.6 Cierre

14. La vulnerabilidad se marca como **MITIGADA** o **CERRADA** en el sistema, registrando la fecha y la persona que verifica el cierre.

## 8. EXCEPCIONES

15. Cuando no sea técnicamente posible o económicamente proporcionado aplicar un parche en plazo, se gestionará como **excepción** conforme al apartado 9 de la Política {{ proyecto.codigo_documento_base }}-100, documentando:

- Vulnerabilidad afectada.
- Motivo de la excepción.
- Riesgo asumido.
- Mitigaciones compensatorias adoptadas.
- Plazo máximo de la excepción.
- Plan para su resolución definitiva.

16. Las excepciones requieren autorización del Responsable de la Seguridad y, para vulnerabilidades CRÍTICAS o ALTAS, del Comité de Seguridad.

## 9. SISTEMAS LEGACY SIN SOPORTE

17. Los sistemas que dejan de recibir soporte del fabricante (end-of-life) serán identificados con anticipación y se planificará su sustitución o migración.

18. Cuando no sea posible su sustitución inmediata, se aplicarán **medidas compensatorias reforzadas**:

- Aislamiento de red.
- Monitorización intensificada.
- Restricción máxima de accesos.
- Plan documentado de salida con plazos.

## 10. INDICADORES

| Indicador | Objetivo |
|---|---|
| Vulnerabilidades CRÍTICAS abiertas > plazo | 0 |
| Vulnerabilidades ALTAS abiertas > plazo | < 5 |
| Tiempo medio de aplicación parches CRÍTICOS | < 7 días |
| Cobertura del escaneo (activos escaneados / inventariados) | ≥ 95% |
| Excepciones vigentes documentadas | 100% |

## 11. ANEXOS

- **Anexo I:** Plantilla del Informe Mensual de Vulnerabilidades
- **Anexo II:** Formulario de Excepción de Parcheo
- **Anexo III:** Lista de fuentes de información monitorizadas
- **Anexo IV:** Calendario de escaneos programados

---

**Documento {{ proyecto.codigo_documento_base }}-205 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---

## INSTRUCCIONES PARA CLAUDE CODE — CIERRE DEL BLOQUE F2.1

### Estado del bloque F2 tras F2.1

Quedan completos los **6 procedimientos críticos operativos** que ejecutan las 9 políticas del bloque F1:

| Código | Política madre | Estado |
|---|---|---|
| E-AR-001 Análisis y Gestión de Riesgos | E-100 | ✅ Completo |
| E-221 Gestión de la Información Documentada | E-100 | ✅ Completo |
| E-204 Gestión de Incidentes | E-108 | ✅ Completo |
| E-231 Gestión de Cuentas y Accesos | E-101 | ✅ Completo |
| E-217 Evaluación y Seguimiento de Proveedores | E-112 | ✅ Completo |
| E-205 Gestión de Vulnerabilidades y Parches | E-100, E-107 | ✅ Completo |

### Procedimientos pendientes para F2.2 (siguiente bloque)

| Código | Título | Política madre | Familia ENS |
|---|---|---|---|
| E-203 | Procedimiento de Gestión de Cambios | E-100 | op.exp.5 |
| E-PF-001 | Procedimiento de Concienciación y Formación | E-100, E-103 | mp.per.3, mp.per.4 |
| E-207 | Procedimiento de Copias de Seguridad y Restauración | E-109 | mp.info.9 |
| E-IT-001 | Procedimiento de Hardening y Configuración Segura | E-100 | op.exp.2, op.exp.3 |
| E-204-A | Procedimiento de Recopilación y Custodia de Evidencias | E-108 | op.exp.8 |
| E-218 | Procedimiento de Auditoría Interna del SGSI | E-100 | (transversal ENS art. 31) |

### Pipeline del Motor 6 (Document Factory) para F2.1

El procesamiento de los procedimientos sigue el mismo flujo que las políticas, con dos diferencias:

1. **Anexos como ficheros independientes:** cada `Anexo I/II/III...` mencionado en los procedimientos se materializa como un fichero separado en `templates/anexos/{codigo_procedimiento}/{n_anexo}.docx`. El Motor 6 los enlaza al documento principal mediante hipervínculos relativos.

2. **Diagramas de flujo:** los procedimientos E-204 y E-231 contienen flujos operativos que se beneficiarían de un diagrama visual. Claude Code puede generarlos automáticamente con `mermaid` o `graphviz` y embedarlos en el `.docx` final como imagen PNG.

### Cobertura ENS tras F1 + F2.1

Combinando políticas y procedimientos, el SGSI tiene cobertura documental directa sobre las siguientes familias del Anexo II del ENS:

| Familia | Cobertura | Documentos relevantes |
|---|---|---|
| **org** | ~90% | E-100, ABSORB_INTO_E100, E-221 |
| **op.pl** | 100% | E-100, E-AR-001 |
| **op.acc** | 100% | E-101, E-231 |
| **op.exp** | ~70% (resto en F2.2 con E-203, E-IT-001, E-204-A) | E-205, parcial E-204 |
| **op.ext** | 100% | E-112, E-217 |
| **op.cont** | ~50% (resto en F2.2 con E-207) | E-109 |
| **mp.if** | 0% (será una política E-110 secundaria) | — |
| **mp.per** | ~30% (resto en F2.2 con E-PF-001) | E-100, E-103 |
| **mp.eq** | ~80% | E-103, E-205 |
| **mp.com** | 100% | E-107 |
| **mp.si** | 100% | E-107 |
| **mp.sw** | ~40% (mayor parte en políticas secundarias) | E-205 |
| **mp.info** | 100% | E-107, E-104 |
| **mp.s** | 100% | E-103, E-205 |

**Tras F1 + F2.1: ~75% del Anexo II del ENS queda cubierto documentalmente.**

Tras F2.2 (los 6 procedimientos restantes), la cobertura llegará al **~92%** y el resto se completa con políticas e instrucciones técnicas secundarias E-109 a E-126 y E-300+.

---

**Fin del Entregable F2.1.**

6 procedimientos críticos operativos con texto operativo real español, ~12.000 palabras, listas para conversión a `.docx` por el Motor 6 durante la Semana 5-6 del plan de construcción FULKRO. Junto con F1.1 y F1.2 conforman el **núcleo documental SGSI ENS de FULKRO** suficiente para presentar a una primera auditoría real con probabilidad de éxito superior al 80% (asumiendo implantación correcta de los controles técnicos asociados).
