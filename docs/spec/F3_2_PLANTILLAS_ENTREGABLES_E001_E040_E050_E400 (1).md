# F3.2 — PLANTILLAS DE ENTREGABLES DEL PROYECTO ENS (E-001, E-040, E-050, E-400)

**Plan 100/100 FULKRO — Bloque 5.2 de plantillas reales**
**Versión:** 1.0 — 9 de abril de 2026
**Continuación de:** F3.1 (P-001, C-001, C-003)

---

## NOTA PRELIMINAR

Este documento completa el bloque F3 con los **4 entregables del proyecto** que el cliente recibe a lo largo de las distintas fases del proyecto FULKRO. Estos entregables son:

- **E-001 — Ficha Resumen Ejecutivo**: documento de una página con el estado del proyecto, dirigido a la dirección del cliente. Se actualiza en cada hito.

- **E-040 — Informe Final de Adecuación al ENS**: el entregable principal del proyecto, que el Cliente presenta al auditor externo de certificación ENAC.

- **E-050 — Informe de Auditoría Interna del SGSI**: plantilla del informe que produce el procedimiento E-234.

- **E-400 — Análisis de Impacto en el Negocio (BIA)**: análisis previo necesario para construir el Plan de Continuidad del Servicio (Política E-104).

Las advertencias legales, el catálogo de placeholders Jinja2 y el flujo de conversión a `.docx` son los mismos que en F1, F2 y F3.1.

---

# DOCUMENTO E-001 — FICHA RESUMEN EJECUTIVO DEL PROYECTO ENS

**Es el documento de una página que la dirección del cliente lee.** Resume el estado del proyecto en términos de negocio, sin tecnicismos. Se entrega al inicio del proyecto y se actualiza en cada hito.

```jinja
---
codigo_documento: "E-001"
titulo: "Ficha Resumen Ejecutivo del Proyecto ENS"
version: "{{ ficha.version }}"
fecha: "{{ ficha.fecha_emision }}"
clasificacion: "INTERNA — Cliente"
---

# FICHA RESUMEN EJECUTIVO DEL PROYECTO ENS

## {{ cliente.razon_social }}

**Documento E-001 · Versión {{ ficha.version }} · {{ ficha.fecha_emision }}**

---

### DATOS GENERALES DEL PROYECTO

| Concepto | Detalle |
|---|---|
| Cliente | {{ cliente.razon_social }} |
| NIF | {{ cliente.nif }} |
| Sector de actividad | {{ cliente.sector }} |
| Categoría ENS objetivo | **{{ proyecto.categoria_ens }}** |
| Alcance del proyecto | {{ proyecto.alcance.descripcion_corta }} |
| Fecha de inicio | {{ proyecto.fecha_inicio }} |
| Duración total estimada | {{ proyecto.duracion_meses }} meses |
| Fecha objetivo de certificación | {{ proyecto.fecha_objetivo_certificacion }} |
| Entidad certificadora elegida | {{ proyecto.entidad_certificadora | default('Pendiente de selección') }} |
| Inversión total contratada (FULKRO) | {{ proyecto.inversion_fulkro }} € + IVA |
| Inversión estimada en auditoría externa | {{ proyecto.inversion_auditoria_externa }} € + IVA |

---

### ESTADO ACTUAL DEL PROYECTO

| Indicador | Estado |
|---|---|
| Fase actual | **{{ ficha.fase_actual }}** ({{ ficha.numero_fase }}/{{ ficha.fases_totales }}) |
| Avance global del proyecto | **{{ ficha.avance_porcentaje }}%** |
| Estado de salud (semáforo) | {% if ficha.semaforo == "verde" %}🟢 **EN PLAZO**{% elif ficha.semaforo == "amarillo" %}🟡 **CON DESVIACIÓN MENOR**{% else %}🔴 **CON RIESGO**{% endif %} |
| Próximo hito | {{ ficha.proximo_hito }} |
| Fecha objetivo del próximo hito | {{ ficha.fecha_proximo_hito }} |
| Días hasta el próximo hito | {{ ficha.dias_proximo_hito }} días |

---

### LOGROS DEL PERIODO

{% for logro in ficha.logros_periodo %}
✅ {{ logro }}
{% endfor %}

---

### RIESGOS ABIERTOS

{% if ficha.riesgos %}
| # | Descripción | Impacto | Probabilidad | Acción mitigadora |
|---|---|---|---|---|
{% for riesgo in ficha.riesgos %}
| {{ loop.index }} | {{ riesgo.descripcion }} | {{ riesgo.impacto }} | {{ riesgo.probabilidad }} | {{ riesgo.accion }} |
{% endfor %}
{% else %}
_No hay riesgos significativos abiertos en este momento._
{% endif %}

---

### DECISIONES PENDIENTES DEL CLIENTE

{% if ficha.decisiones_pendientes %}
La siguiente lista recoge las decisiones que requieren aprobación o acción por parte de {{ cliente.razon_social }} para no bloquear el avance del proyecto:

{% for decision in ficha.decisiones_pendientes %}
**{{ loop.index }}. {{ decision.titulo }}**
- **Descripción:** {{ decision.descripcion }}
- **Decisor:** {{ decision.decisor }}
- **Fecha límite:** {{ decision.fecha_limite }}
- **Impacto si no se decide:** {{ decision.impacto_demora }}

{% endfor %}
{% else %}
_No hay decisiones pendientes del cliente en este momento._
{% endif %}

---

### CONSUMO DE INVERSIÓN

| Concepto | Importe |
|---|---|
| Honorarios FULKRO contratados | {{ proyecto.inversion_fulkro }} € |
| Honorarios FULKRO consumidos a {{ ficha.fecha_emision }} | {{ ficha.honorarios_consumidos }} € ({{ ficha.porcentaje_consumido }}%) |
| Horas FULKRO contratadas | {{ proyecto.horas_contratadas }} h |
| Horas FULKRO consumidas | {{ ficha.horas_consumidas }} h ({{ ficha.porcentaje_horas_consumidas }}%) |
| Desviación respecto al plan | {% if ficha.desviacion_horas > 0 %}+{% endif %}{{ ficha.desviacion_horas }} h |

{% if ficha.desviacion_horas > 0 %}
⚠️ **Nota:** se observa una desviación positiva de horas. Esta desviación está justificada por: {{ ficha.justificacion_desviacion }}.
{% endif %}

---

### COMENTARIO DEL CONSULTOR

> {{ ficha.comentario_consultor }}

---

**Próxima actualización prevista:** {{ ficha.proxima_actualizacion }}

**Para cualquier consulta:** Marcos Mata García · marcosmata@fulkro.es

---

**Documento E-001 · {{ cliente.razon_social }} · Versión {{ ficha.version }} · {{ ficha.fecha_emision }}**

```

---

# DOCUMENTO E-040 — INFORME FINAL DE ADECUACIÓN AL ENS

**Es el entregable principal del proyecto.** El documento que el cliente presenta al auditor externo ENAC y que prueba que está preparado para la auditoría de certificación. Es el documento más extenso y formal del proyecto.

```jinja
---
codigo_documento: "E-040"
titulo: "Informe Final de Adecuación al Esquema Nacional de Seguridad"
version: "{{ informe.version | default('1.0') }}"
fecha: "{{ informe.fecha_emision }}"
clasificacion: "CONFIDENCIAL — Cliente"
elaborado_por: "FULKRO — Marcos Mata García"
revisado_por: "{{ responsables.responsable_seguridad.nombre }}"
aprobado_por: "{{ cliente.organo_aprobador_politicas }}"
---

# INFORME FINAL DE ADECUACIÓN AL ESQUEMA NACIONAL DE SEGURIDAD

## {{ cliente.razon_social }}

**Documento E-040 · Versión {{ informe.version | default('1.0') }} · {{ informe.fecha_emision }}**

---

## 1. RESUMEN EJECUTIVO

El presente informe documenta el resultado del proyecto de adecuación de **{{ cliente.razon_social }}** al Esquema Nacional de Seguridad regulado por el Real Decreto 311/2022, de 3 de mayo, ejecutado por FULKRO entre el {{ proyecto.fecha_inicio }} y el {{ proyecto.fecha_fin }}, con el objetivo de obtener la certificación de conformidad en categoría **{{ proyecto.categoria_ens }}**.

A la fecha de emisión del presente informe, el sistema comprendido en el alcance reúne las condiciones necesarias para someterse a la auditoría externa de certificación por una entidad acreditada por ENAC, con un nivel de cumplimiento global del **{{ informe.cumplimiento_global }}%** sobre las medidas exigibles del Anexo II del ENS para la categoría declarada.

**Conclusión:** Se recomienda al Comité de Seguridad de {{ cliente.razon_social }} elevar al órgano superior la propuesta de iniciar formalmente el procedimiento de certificación externa con la entidad seleccionada.

---

## 2. ALCANCE DEL SISTEMA CERTIFICADO

### 2.1 Definición del alcance

El sistema de información objeto de la adecuación al ENS y de la futura certificación es:

> **{{ proyecto.alcance.descripcion_completa }}**

### 2.2 Servicios incluidos

{% for servicio in proyecto.alcance.servicios %}
- {{ servicio }}
{% endfor %}

### 2.3 Sistemas e infraestructura

{% for sistema in proyecto.alcance.sistemas %}
- {{ sistema }}
{% endfor %}

### 2.4 Sedes incluidas

| Sede | Dirección | Tipo |
|---|---|---|
{% for sede in proyecto.alcance.sedes %}
| {{ sede.nombre }} | {{ sede.direccion }} | {{ sede.tipo }} |
{% endfor %}

### 2.5 Exclusiones expresas

{% for exclusion in proyecto.alcance.exclusiones %}
- {{ exclusion }}
{% endfor %}

---

## 3. METODOLOGÍA DEL PROYECTO

El proyecto se ha ejecutado siguiendo la metodología FULKRO, alineada con las guías CCN-STIC 805 (Política de Seguridad), 806 (Plan de Adecuación) y 808 (Verificación del cumplimiento del ENS) y con el ciclo PDCA de la norma UNE-EN ISO/IEC 27001:2022.

Las fases ejecutadas han sido:

| Fase | Descripción | Duración real | Estado |
|---|---|---|---|
{% for fase in informe.fases %}
| {{ loop.index }}. {{ fase.nombre }} | {{ fase.descripcion }} | {{ fase.duracion_real }} sem. | {{ fase.estado }} |
{% endfor %}

---

## 4. CATEGORIZACIÓN DEL SISTEMA

### 4.1 Análisis de impacto sobre las dimensiones de seguridad

Conforme a los criterios del Anexo I del Real Decreto 311/2022 y de la guía CCN-STIC 803, se ha realizado el análisis de impacto sobre las cinco dimensiones de seguridad (Confidencialidad, Integridad, Trazabilidad, Autenticidad y Disponibilidad), con el siguiente resultado:

| Dimensión | Nivel asignado | Justificación |
|---|---|---|
| **Confidencialidad** | {{ informe.dimensiones.confidencialidad.nivel }} | {{ informe.dimensiones.confidencialidad.justificacion }} |
| **Integridad** | {{ informe.dimensiones.integridad.nivel }} | {{ informe.dimensiones.integridad.justificacion }} |
| **Trazabilidad** | {{ informe.dimensiones.trazabilidad.nivel }} | {{ informe.dimensiones.trazabilidad.justificacion }} |
| **Autenticidad** | {{ informe.dimensiones.autenticidad.nivel }} | {{ informe.dimensiones.autenticidad.justificacion }} |
| **Disponibilidad** | {{ informe.dimensiones.disponibilidad.nivel }} | {{ informe.dimensiones.disponibilidad.justificacion }} |

### 4.2 Categoría del sistema

Por aplicación del criterio de **categoría máxima de las dimensiones**, la categoría del sistema completo es **{{ proyecto.categoria_ens }}**.

Esta categoría ha sido formalmente aprobada por el Comité de Seguridad de {{ cliente.razon_social }} con fecha {{ informe.fecha_aprobacion_categoria }}.

---

## 5. ANÁLISIS DE RIESGOS

### 5.1 Metodología

El análisis de riesgos se ha realizado conforme a la metodología **MAGERIT versión 3** del Consejo Superior de Administración Electrónica, siguiendo el procedimiento E-200 (Procedimiento de Análisis y Gestión de Riesgos) implantado en el SGSI.

### 5.2 Inventario de activos

Se han identificado e inventariado un total de **{{ informe.activos.total }} activos** distribuidos según la taxonomía MAGERIT v3:

| Tipo de activo | Cantidad |
|---|---|
| Servicios | {{ informe.activos.servicios }} |
| Información | {{ informe.activos.informacion }} |
| Software | {{ informe.activos.software }} |
| Hardware | {{ informe.activos.hardware }} |
| Comunicaciones | {{ informe.activos.comunicaciones }} |
| Soportes de información | {{ informe.activos.soportes }} |
| Equipamiento auxiliar | {{ informe.activos.auxiliar }} |
| Instalaciones | {{ informe.activos.instalaciones }} |
| Personal | {{ informe.activos.personal }} |

### 5.3 Resumen del análisis de riesgos

| Concepto | Valor |
|---|---|
| Amenazas identificadas | {{ informe.riesgos.amenazas }} |
| Pares activo-amenaza analizados | {{ informe.riesgos.pares_analizados }} |
| Riesgos intrínsecos identificados | {{ informe.riesgos.intrinsecos }} |
| Riesgos residuales tras salvaguardas | {{ informe.riesgos.residuales }} |
| Riesgos residuales por encima del umbral de aceptación | {{ informe.riesgos.por_encima_umbral }} |
| Riesgos residuales aceptados formalmente | {{ informe.riesgos.aceptados }} |

### 5.4 Plan de Tratamiento de Riesgos

El Plan de Tratamiento de Riesgos derivado del análisis incluye **{{ informe.riesgos.acciones_plan }} acciones**, distribuidas según la opción de tratamiento:

| Opción | Acciones |
|---|---|
| Mitigar | {{ informe.riesgos.mitigar }} |
| Transferir | {{ informe.riesgos.transferir }} |
| Evitar | {{ informe.riesgos.evitar }} |
| Aceptar | {{ informe.riesgos.aceptar }} |

A la fecha del presente informe, el **{{ informe.riesgos.porcentaje_completado }}%** de las acciones del Plan han sido completadas.

El Análisis de Riesgos completo se incorpora como **Anexo I** del presente informe.

---

## 6. DECLARACIÓN DE APLICABILIDAD (DOA)

Se ha elaborado la **Declaración de Aplicabilidad** del sistema, que documenta para cada una de las medidas del Anexo II del Real Decreto 311/2022:

a) Si la medida es aplicable al sistema atendiendo a su categoría.
b) Si la medida está implantada y, en caso negativo, la justificación.
c) La eficacia estimada de la implantación.
d) Las evidencias asociadas.

La Declaración de Aplicabilidad completa se incorpora como **Anexo II** del presente informe.

### 6.1 Resumen de aplicabilidad por familia de medidas

| Familia ENS | Medidas aplicables | Implantadas | % Cumplimiento |
|---|---|---|---|
| Marco organizativo (org) | {{ informe.cumplimiento.org.aplicables }} | {{ informe.cumplimiento.org.implantadas }} | {{ informe.cumplimiento.org.porcentaje }}% |
| Marco operacional / Planificación (op.pl) | {{ informe.cumplimiento.op_pl.aplicables }} | {{ informe.cumplimiento.op_pl.implantadas }} | {{ informe.cumplimiento.op_pl.porcentaje }}% |
| Marco operacional / Control de acceso (op.acc) | {{ informe.cumplimiento.op_acc.aplicables }} | {{ informe.cumplimiento.op_acc.implantadas }} | {{ informe.cumplimiento.op_acc.porcentaje }}% |
| Marco operacional / Explotación (op.exp) | {{ informe.cumplimiento.op_exp.aplicables }} | {{ informe.cumplimiento.op_exp.implantadas }} | {{ informe.cumplimiento.op_exp.porcentaje }}% |
| Marco operacional / Servicios externos (op.ext) | {{ informe.cumplimiento.op_ext.aplicables }} | {{ informe.cumplimiento.op_ext.implantadas }} | {{ informe.cumplimiento.op_ext.porcentaje }}% |
| Marco operacional / Continuidad (op.cont) | {{ informe.cumplimiento.op_cont.aplicables }} | {{ informe.cumplimiento.op_cont.implantadas }} | {{ informe.cumplimiento.op_cont.porcentaje }}% |
| Medidas de protección / Instalaciones (mp.if) | {{ informe.cumplimiento.mp_if.aplicables }} | {{ informe.cumplimiento.mp_if.implantadas }} | {{ informe.cumplimiento.mp_if.porcentaje }}% |
| Medidas de protección / Personal (mp.per) | {{ informe.cumplimiento.mp_per.aplicables }} | {{ informe.cumplimiento.mp_per.implantadas }} | {{ informe.cumplimiento.mp_per.porcentaje }}% |
| Medidas de protección / Equipos (mp.eq) | {{ informe.cumplimiento.mp_eq.aplicables }} | {{ informe.cumplimiento.mp_eq.implantadas }} | {{ informe.cumplimiento.mp_eq.porcentaje }}% |
| Medidas de protección / Comunicaciones (mp.com) | {{ informe.cumplimiento.mp_com.aplicables }} | {{ informe.cumplimiento.mp_com.implantadas }} | {{ informe.cumplimiento.mp_com.porcentaje }}% |
| Medidas de protección / Sistemas información (mp.si) | {{ informe.cumplimiento.mp_si.aplicables }} | {{ informe.cumplimiento.mp_si.implantadas }} | {{ informe.cumplimiento.mp_si.porcentaje }}% |
| Medidas de protección / Software (mp.sw) | {{ informe.cumplimiento.mp_sw.aplicables }} | {{ informe.cumplimiento.mp_sw.implantadas }} | {{ informe.cumplimiento.mp_sw.porcentaje }}% |
| Medidas de protección / Información (mp.info) | {{ informe.cumplimiento.mp_info.aplicables }} | {{ informe.cumplimiento.mp_info.implantadas }} | {{ informe.cumplimiento.mp_info.porcentaje }}% |
| Medidas de protección / Servicios (mp.s) | {{ informe.cumplimiento.mp_s.aplicables }} | {{ informe.cumplimiento.mp_s.implantadas }} | {{ informe.cumplimiento.mp_s.porcentaje }}% |
| **TOTAL** | **{{ informe.cumplimiento.total.aplicables }}** | **{{ informe.cumplimiento.total.implantadas }}** | **{{ informe.cumplimiento.total.porcentaje }}%** |

---

## 7. CUERPO NORMATIVO DEL SGSI IMPLANTADO

Como resultado del proyecto, {{ cliente.razon_social }} dispone del siguiente cuerpo normativo del SGSI, formalmente aprobado por el órgano de gobierno superior:

### 7.1 Políticas

| Código | Título | Versión | Fecha aprobación |
|---|---|---|---|
| POL-100 | Política de Seguridad de la Información | {{ informe.politicas.pol100.version }} | {{ informe.politicas.pol100.fecha }} |
| POL-101 | Roles, Responsabilidades y Autoridades de Seguridad | {{ informe.politicas.pol101.version }} | {{ informe.politicas.pol101.fecha }} |
| POL-102 | Política de Control de Acceso | {{ informe.politicas.pol102.version }} | {{ informe.politicas.pol102.fecha }} |
| POL-103 | Política de Gestión de Incidentes de Seguridad | {{ informe.politicas.pol103.version }} | {{ informe.politicas.pol103.fecha }} |
| POL-104 | Política de Continuidad del Servicio | {{ informe.politicas.pol104.version }} | {{ informe.politicas.pol104.fecha }} |
| POL-105 | Política de Cifrado y Gestión de Claves Criptográficas | {{ informe.politicas.pol105.version }} | {{ informe.politicas.pol105.fecha }} |
| POL-106 | Política de Uso Aceptable de los Recursos | {{ informe.politicas.pol106.version }} | {{ informe.politicas.pol106.fecha }} |
| POL-107 | Política de Seguridad en las Relaciones con Proveedores | {{ informe.politicas.pol107.version }} | {{ informe.politicas.pol107.fecha }} |
| POL-108 | Política de Clasificación y Tratamiento de la Información | {{ informe.politicas.pol108.version }} | {{ informe.politicas.pol108.fecha }} |

### 7.2 Procedimientos operativos

| Código | Título | Versión |
|---|---|---|
| POL-200 | Procedimiento de Análisis y Gestión de Riesgos | {{ informe.procedimientos.pol200.version }} |
| POL-203 | Procedimiento de Gestión de la Información Documentada | {{ informe.procedimientos.pol203.version }} |
| POL-204 | Procedimiento de Gestión de Incidentes de Seguridad | {{ informe.procedimientos.pol204.version }} |
| POL-205 | Procedimiento de Gestión de Cuentas y Accesos | {{ informe.procedimientos.pol205.version }} |
| POL-206 | Procedimiento de Gestión de Cambios | {{ informe.procedimientos.pol206.version }} |
| POL-207 | Procedimiento de Concienciación y Formación | {{ informe.procedimientos.pol207.version }} |
| POL-210 | Procedimiento de Copias de Seguridad y Restauración | {{ informe.procedimientos.pol210.version }} |
| POL-217 | Procedimiento de Evaluación de Proveedores | {{ informe.procedimientos.pol217.version }} |
| POL-218 | Procedimiento de Gestión de Vulnerabilidades y Parches | {{ informe.procedimientos.pol218.version }} |
| POL-219 | Procedimiento de Hardening y Configuración Segura | {{ informe.procedimientos.pol219.version }} |
| POL-228 | Procedimiento de Recopilación y Custodia de Evidencias | {{ informe.procedimientos.pol228.version }} |
| POL-234 | Procedimiento de Auditoría Interna del SGSI | {{ informe.procedimientos.pol234.version }} |

---

## 8. EVIDENCIAS RECOPILADAS

Durante el proyecto se han recopilado y archivado las siguientes evidencias del cumplimiento de las medidas implantadas:

| Tipo de evidencia | Cantidad |
|---|---|
| Actas de aprobación de políticas y procedimientos | {{ informe.evidencias.actas }} |
| Registros de formación y concienciación | {{ informe.evidencias.formacion }} |
| Informes de análisis de riesgos | {{ informe.evidencias.riesgos }} |
| Capturas de configuración de sistemas | {{ informe.evidencias.configuraciones }} |
| Registros de pruebas de restauración | {{ informe.evidencias.restauracion }} |
| Informes de auditoría interna | {{ informe.evidencias.auditoria_interna }} |
| Registros de gestión de incidentes simulados | {{ informe.evidencias.incidentes }} |
| Cuestionarios de evaluación de proveedores | {{ informe.evidencias.proveedores }} |
| Informes de pentesting / vulnerabilidades | {{ informe.evidencias.vulnerabilidades }} |
| **TOTAL** | **{{ informe.evidencias.total }}** |

Todas las evidencias se conservan en el repositorio documental del SGSI, conforme al procedimiento E-203 y a los plazos de retención establecidos.

---

## 9. GAPS RESIDUALES Y EXCEPCIONES

### 9.1 Gaps residuales identificados

A la fecha del presente informe, los siguientes gaps residuales han sido identificados y aceptados formalmente por el Comité de Seguridad:

{% if informe.gaps %}
| # | Medida ENS | Descripción del gap | Riesgo asociado | Acción comprometida | Plazo |
|---|---|---|---|---|---|
{% for gap in informe.gaps %}
| {{ loop.index }} | {{ gap.medida_ens }} | {{ gap.descripcion }} | {{ gap.riesgo }} | {{ gap.accion }} | {{ gap.plazo }} |
{% endfor %}
{% else %}
_No se han identificado gaps residuales relevantes a la fecha del presente informe._
{% endif %}

### 9.2 Excepciones autorizadas

{% if informe.excepciones %}
Las siguientes excepciones han sido formalmente autorizadas por el Responsable de la Seguridad y, cuando ha procedido, por el Comité de Seguridad:

| # | Norma o medida afectada | Justificación | Vigencia | Mitigación compensatoria |
|---|---|---|---|---|
{% for exc in informe.excepciones %}
| {{ loop.index }} | {{ exc.norma }} | {{ exc.justificacion }} | {{ exc.vigencia }} | {{ exc.mitigacion }} |
{% endfor %}
{% else %}
_No se han autorizado excepciones a la fecha del presente informe._
{% endif %}

---

## 10. AUDITORÍA INTERNA REALIZADA

Conforme al procedimiento E-234 (Procedimiento de Auditoría Interna del SGSI) y al artículo 31 del Real Decreto 311/2022, se ha realizado la auditoría interna del SGSI con anterioridad a la auditoría externa de certificación.

### 10.1 Datos de la auditoría interna

| Concepto | Detalle |
|---|---|
| Fecha de realización | {{ informe.auditoria_interna.fecha }} |
| Auditor responsable | {{ informe.auditoria_interna.auditor }} |
| Independencia respecto al equipo del SGSI | {{ informe.auditoria_interna.independencia }} |
| Alcance auditado | Totalidad del SGSI |

### 10.2 Resultado de la auditoría interna

| Tipo de hallazgo | Cantidad | Estado |
|---|---|---|
| No conformidades mayores | {{ informe.auditoria_interna.nc_mayores }} | {{ informe.auditoria_interna.nc_mayores_estado }} |
| No conformidades menores | {{ informe.auditoria_interna.nc_menores }} | {{ informe.auditoria_interna.nc_menores_estado }} |
| Observaciones | {{ informe.auditoria_interna.observaciones }} | — |
| Oportunidades de mejora | {{ informe.auditoria_interna.oportunidades }} | — |

El **Informe de Auditoría Interna completo** se incorpora como **Anexo III** del presente documento.

---

## 11. CONCLUSIÓN Y RECOMENDACIÓN

### 11.1 Estado de preparación para la auditoría externa

Tras la finalización del proyecto y la realización de la auditoría interna, se considera que **{{ cliente.razon_social }} reúne las condiciones necesarias** para someterse a la auditoría externa de certificación del Esquema Nacional de Seguridad en categoría **{{ proyecto.categoria_ens }}** por una entidad acreditada por ENAC.

El nivel de cumplimiento global del **{{ informe.cumplimiento_global }}%** sobre las medidas exigibles, junto con la ausencia de no conformidades mayores no resueltas, permite afirmar que la probabilidad de obtener un dictamen favorable en la auditoría externa es **alta**.

### 11.2 Recomendaciones para la auditoría externa

a) **Iniciar formalmente el contacto con la entidad certificadora seleccionada** ({{ proyecto.entidad_certificadora }}) para la programación de la auditoría externa, con una antelación mínima de 6-8 semanas.

b) **Mantener la operativa del SGSI estable** durante el periodo previo a la auditoría, evitando cambios significativos en las políticas, procedimientos o configuraciones que pudieran requerir nueva validación.

c) **Asegurar la disponibilidad del personal clave** durante los días de auditoría, en particular del Responsable de la Seguridad, del Responsable del Sistema y de los responsables de las áreas que serán entrevistadas.

d) **Mantener actualizado el repositorio documental** del SGSI con las últimas versiones de todos los documentos, evidencias y registros.

e) **Continuar con las actividades operativas habituales** del SGSI (gestión de incidentes, revisión de accesos, monitorización) para no interrumpir la generación de evidencias.

### 11.3 Compromiso de FULKRO

FULKRO se compromete a acompañar a {{ cliente.razon_social }} durante la auditoría externa, conforme a lo establecido en el Contrato C-001 y, posteriormente, mediante la suscripción del contrato de retainer C-003 si así lo decide la dirección.

---

## 12. ANEXOS

- **Anexo I:** Análisis de Riesgos completo (referencia del documento)
- **Anexo II:** Declaración de Aplicabilidad (referencia del documento)
- **Anexo III:** Informe de Auditoría Interna del SGSI
- **Anexo IV:** Plan de Tratamiento de Riesgos
- **Anexo V:** Inventario de Activos
- **Anexo VI:** Cuerpo normativo completo del SGSI (21 documentos)
- **Anexo VII:** Registro de evidencias

---

**Elaborado por:** Marcos Mata García — FULKRO
**Revisado por:** {{ responsables.responsable_seguridad.nombre }} — {{ responsables.responsable_seguridad.cargo }}
**Aprobado por:** {{ cliente.organo_aprobador_politicas }}
**Fecha:** {{ informe.fecha_emision }}

**Documento E-040 · {{ cliente.razon_social }} · Versión {{ informe.version | default('1.0') }}**

```

---

# DOCUMENTO E-050 — INFORME DE AUDITORÍA INTERNA DEL SGSI

**Es la plantilla del informe que produce el procedimiento E-234.** Es el documento que el auditor interno (sea Marcos como consultor independiente o un auditor designado por el cliente) entrega tras realizar la auditoría interna anual del SGSI.

```jinja
---
codigo_documento: "E-050"
titulo: "Informe de Auditoría Interna del SGSI"
version: "{{ auditoria.version | default('1.0') }}"
fecha: "{{ auditoria.fecha_informe }}"
clasificacion: "CONFIDENCIAL — Cliente"
auditor_jefe: "{{ auditoria.auditor_jefe }}"
---

# INFORME DE AUDITORÍA INTERNA DEL SGSI

## {{ cliente.razon_social }}

**Documento E-050 · Versión {{ auditoria.version | default('1.0') }} · {{ auditoria.fecha_informe }}**

---

## 1. RESUMEN EJECUTIVO

| Concepto | Detalle |
|---|---|
| Cliente auditado | {{ cliente.razon_social }} |
| Categoría ENS del sistema | {{ proyecto.categoria_ens }} |
| Periodo de auditoría | {{ auditoria.fecha_inicio }} a {{ auditoria.fecha_fin }} |
| Auditor jefe | {{ auditoria.auditor_jefe }} |
| Auditor técnico | {{ auditoria.auditor_tecnico | default('—') }} |
| Norma de referencia | RD 311/2022 + UNE-EN ISO/IEC 27001:2022 |
| Tipo de auditoría | {{ auditoria.tipo }} |
| Resultado global | {% if auditoria.resultado == "favorable" %}🟢 **FAVORABLE**{% elif auditoria.resultado == "favorable_observaciones" %}🟡 **FAVORABLE CON OBSERVACIONES**{% else %}🔴 **CON HALLAZGOS RELEVANTES**{% endif %} |

### 1.1 Conclusión

{{ auditoria.conclusion_resumen }}

---

## 2. ALCANCE DE LA AUDITORÍA

### 2.1 Sistema auditado

El alcance del SGSI auditado coincide con el alcance certificado de {{ cliente.razon_social }}:

> {{ proyecto.alcance.descripcion_completa }}

### 2.2 Áreas y procesos auditados

{% for area in auditoria.areas_auditadas %}
- **{{ area.nombre }}** — {{ area.descripcion }}
{% endfor %}

### 2.3 Documentos revisados

Se han revisado todos los documentos vigentes del SGSI, incluyendo las **9 políticas** del bloque POL-100 a POL-108 y los **12 procedimientos** del bloque POL-200 a POL-234.

---

## 3. CRITERIOS DE AUDITORÍA

La auditoría se ha realizado conforme a los siguientes criterios:

a) **Real Decreto 311/2022**, de 3 de mayo, por el que se regula el Esquema Nacional de Seguridad, en particular su Anexo II (Medidas de seguridad).

b) **Resolución de 27 de marzo de 2018** (BOE-A-2018-4573), Instrucción Técnica de Seguridad de Auditoría de la Seguridad de los Sistemas de Información.

c) **Norma UNE-EN ISO/IEC 27001:2022** — Sistemas de Gestión de la Seguridad de la Información — Requisitos.

d) **Guía CCN-STIC 802** — Guía de auditoría del ENS.

e) **Guía CCN-STIC 808** — Verificación del cumplimiento del ENS.

f) **Documentación interna del SGSI** de {{ cliente.razon_social }}.

---

## 4. EQUIPO AUDITOR

| Rol | Nombre | Cualificación |
|---|---|---|
| Auditor jefe | {{ auditoria.auditor_jefe }} | {{ auditoria.cualificacion_jefe }} |
{% if auditoria.auditor_tecnico %}
| Auditor técnico | {{ auditoria.auditor_tecnico }} | {{ auditoria.cualificacion_tecnico }} |
{% endif %}

**Declaración de independencia:** {{ auditoria.declaracion_independencia }}

---

## 5. METODOLOGÍA EMPLEADA

La auditoría se ha desarrollado aplicando una combinación de las siguientes técnicas, conforme al procedimiento E-234 implantado:

a) **Revisión documental** — análisis de las políticas, procedimientos, instrucciones, registros y evidencias del SGSI.

b) **Entrevistas estructuradas** con los responsables y operadores de los procesos auditados, basadas en cuestionarios estándar por área (Anexo II del E-234).

c) **Observación directa** de la ejecución de procesos operativos clave.

d) **Pruebas de cumplimiento** mediante verificación práctica sobre muestras representativas de cuentas, accesos, configuraciones, copias de seguridad y demás controles.

e) **Pruebas técnicas** sobre configuraciones de sistemas, controles de acceso, registros de logs, ejecución de copias de seguridad y otros elementos técnicos del SGSI.

### 5.1 Cronograma de la auditoría

| Día | Actividad |
|---|---|
{% for dia in auditoria.cronograma %}
| {{ dia.fecha }} | {{ dia.actividad }} |
{% endfor %}

---

## 6. HALLAZGOS DE LA AUDITORÍA

### 6.1 Resumen de hallazgos

| Tipo | Cantidad |
|---|---|
| **No conformidades mayores** | {{ auditoria.nc_mayores | length }} |
| **No conformidades menores** | {{ auditoria.nc_menores | length }} |
| **Observaciones** | {{ auditoria.observaciones | length }} |
| **Oportunidades de mejora** | {{ auditoria.oportunidades | length }} |
| **TOTAL** | {{ auditoria.total_hallazgos }} |

### 6.2 No conformidades mayores

{% if auditoria.nc_mayores %}
{% for nc in auditoria.nc_mayores %}
**NCM-{{ '%03d' % loop.index }}** — {{ nc.titulo }}

- **Criterio incumplido:** {{ nc.criterio }}
- **Evidencia:** {{ nc.evidencia }}
- **Descripción:** {{ nc.descripcion }}
- **Impacto:** {{ nc.impacto }}
- **Acción correctiva requerida:** {{ nc.accion_correctiva }}
- **Plazo máximo:** 90 días naturales

{% endfor %}
{% else %}
_No se han detectado no conformidades mayores en la presente auditoría._
{% endif %}

### 6.3 No conformidades menores

{% if auditoria.nc_menores %}
{% for nc in auditoria.nc_menores %}
**NCm-{{ '%03d' % loop.index }}** — {{ nc.titulo }}

- **Criterio incumplido:** {{ nc.criterio }}
- **Evidencia:** {{ nc.evidencia }}
- **Descripción:** {{ nc.descripcion }}
- **Acción correctiva propuesta:** {{ nc.accion_correctiva }}
- **Plazo máximo:** 180 días naturales

{% endfor %}
{% else %}
_No se han detectado no conformidades menores en la presente auditoría._
{% endif %}

### 6.4 Observaciones

{% if auditoria.observaciones %}
{% for obs in auditoria.observaciones %}
**OBS-{{ '%03d' % loop.index }}** — {{ obs.titulo }}

{{ obs.descripcion }}

{% endfor %}
{% else %}
_No se han registrado observaciones en la presente auditoría._
{% endif %}

### 6.5 Oportunidades de mejora

{% if auditoria.oportunidades %}
{% for op in auditoria.oportunidades %}
**OM-{{ '%03d' % loop.index }}** — {{ op.titulo }}

{{ op.descripcion }}

{% endfor %}
{% else %}
_No se han identificado oportunidades de mejora específicas en la presente auditoría._
{% endif %}

---

## 7. EVALUACIÓN POR FAMILIA DE MEDIDAS DEL ANEXO II DEL ENS

| Familia | Conformidad | Hallazgos |
|---|---|---|
{% for familia in auditoria.evaluacion_por_familia %}
| {{ familia.codigo }} — {{ familia.nombre }} | {{ familia.conformidad }} | {{ familia.hallazgos }} |
{% endfor %}

---

## 8. EVALUACIÓN POR DIMENSIÓN DE SEGURIDAD

| Dimensión | Estado de los controles | Comentario |
|---|---|---|
| Confidencialidad | {{ auditoria.dimensiones.confidencialidad.estado }} | {{ auditoria.dimensiones.confidencialidad.comentario }} |
| Integridad | {{ auditoria.dimensiones.integridad.estado }} | {{ auditoria.dimensiones.integridad.comentario }} |
| Disponibilidad | {{ auditoria.dimensiones.disponibilidad.estado }} | {{ auditoria.dimensiones.disponibilidad.comentario }} |
| Autenticidad | {{ auditoria.dimensiones.autenticidad.estado }} | {{ auditoria.dimensiones.autenticidad.comentario }} |
| Trazabilidad | {{ auditoria.dimensiones.trazabilidad.estado }} | {{ auditoria.dimensiones.trazabilidad.comentario }} |

---

## 9. CONCLUSIÓN GENERAL

{{ auditoria.conclusion_completa }}

### 9.1 Valoración global del SGSI

Tras la auditoría realizada, el equipo auditor concluye que el SGSI implantado en {{ cliente.razon_social }} presenta el siguiente nivel de madurez global:

| Dimensión de evaluación | Nivel |
|---|---|
| Documentación | {{ auditoria.madurez.documentacion }} |
| Implantación operativa | {{ auditoria.madurez.implantacion }} |
| Eficacia de los controles | {{ auditoria.madurez.eficacia }} |
| Mejora continua | {{ auditoria.madurez.mejora_continua }} |
| **Valoración global** | **{{ auditoria.madurez.global }}** |

### 9.2 Recomendaciones generales

{% for rec in auditoria.recomendaciones %}
{{ loop.index }}. {{ rec }}
{% endfor %}

---

## 10. SEGUIMIENTO PROPUESTO

El equipo auditor propone el siguiente calendario de seguimiento de los hallazgos:

| Hito | Plazo desde el presente informe |
|---|---|
| Entrega de los planes de acción correctiva por parte del cliente | 15 días naturales |
| Aprobación de los planes por el Responsable de la Seguridad | 30 días naturales |
| Verificación del cierre de no conformidades menores | 6 meses |
| Verificación del cierre de no conformidades mayores | 90 días |
| Próxima auditoría interna ordinaria | {{ auditoria.proxima_auditoria }} |

---

## 11. ANEXOS

- **Anexo I:** Listado completo de documentos del SGSI revisados
- **Anexo II:** Personas entrevistadas y áreas implicadas
- **Anexo III:** Detalle técnico de las pruebas realizadas
- **Anexo IV:** Evidencias fotográficas o capturas relevantes
- **Anexo V:** Cuestionarios de auditoría empleados

---

**Auditor jefe:** {{ auditoria.auditor_jefe }}
**Fecha del informe:** {{ auditoria.fecha_informe }}
**Firma:** _____________

**Documento E-050 · {{ cliente.razon_social }} · Versión {{ auditoria.version | default('1.0') }}**

```

---

# DOCUMENTO E-400 — ANÁLISIS DE IMPACTO EN EL NEGOCIO (BIA)

**Es el análisis previo necesario para construir el Plan de Continuidad del Servicio.** Materializa la medida op.cont.1 del Anexo II del ENS y constituye la entrada fundamental para el Plan de Continuidad descrito en la Política E-104. Sigue las directrices de la norma UNE-EN ISO 22301:2019.

```jinja
---
codigo_documento: "E-400"
titulo: "Análisis de Impacto en el Negocio (BIA)"
version: "{{ bia.version | default('1.0') }}"
fecha: "{{ bia.fecha_emision }}"
clasificacion: "CONFIDENCIAL — Cliente"
elaborado_por: "{{ bia.elaborado_por }}"
aprobado_por: "Comité de Seguridad"
politica_madre: "POL-104"
---

# ANÁLISIS DE IMPACTO EN EL NEGOCIO (BIA)

## {{ cliente.razon_social }}

**Documento E-400 · Versión {{ bia.version | default('1.0') }} · {{ bia.fecha_emision }}**

---

## 1. INTRODUCCIÓN Y OBJETO

El presente Análisis de Impacto en el Negocio (en adelante, **"BIA"**, del inglés *Business Impact Analysis*) tiene por objeto identificar, valorar y documentar el impacto que tendría sobre {{ cliente.razon_social }} la interrupción de sus procesos de negocio críticos y de los servicios y sistemas que les dan soporte, con la finalidad de:

a) Identificar los procesos y servicios cuya interrupción supondría un impacto inasumible para la organización.

b) Determinar los recursos críticos necesarios para la prestación de dichos procesos y servicios.

c) Establecer los **objetivos de tiempo de recuperación (RTO)** y **objetivos de punto de recuperación (RPO)** aplicables a cada uno.

d) Identificar las dependencias internas y externas que condicionan la continuidad.

e) Proporcionar la base sobre la que construir el **Plan de Continuidad del Servicio** (PCS) descrito en la Política POL-104.

Este BIA da cumplimiento a la medida **op.cont.1 (Análisis de impacto)** del Anexo II del Real Decreto 311/2022 y se ha elaborado conforme a las directrices de la norma UNE-EN ISO 22301:2019 sobre Sistemas de Gestión de la Continuidad del Negocio.

---

## 2. ALCANCE

El presente análisis abarca la totalidad de los procesos, servicios, sistemas y recursos comprendidos en el alcance del SGSI definido en la Política POL-100 de {{ cliente.razon_social }}.

---

## 3. METODOLOGÍA

### 3.1 Fases del análisis

El BIA se ha desarrollado en las siguientes fases:

1. **Identificación de procesos críticos** mediante entrevistas con los responsables funcionales de cada área de la organización.

2. **Valoración del impacto** sobre cada proceso identificando criterios de impacto múltiples (operativo, económico, legal, reputacional).

3. **Identificación de recursos críticos** asociados a cada proceso (personal, infraestructura, aplicaciones, datos, proveedores).

4. **Determinación de los RTO y RPO** para cada proceso y recurso.

5. **Análisis de dependencias** internas y externas.

6. **Identificación de escenarios de disrupción** relevantes y de su impacto.

7. **Conclusiones y recomendaciones** para el Plan de Continuidad.

### 3.2 Escala de valoración del impacto

El impacto de la interrupción de cada proceso se valora en escala cualitativa, teniendo en cuenta su evolución temporal:

| Nivel | Descripción |
|---|---|
| **CRÍTICO** | Impacto irrecuperable o de muy difícil reparación. Pérdidas económicas superiores a {{ bia.umbral_critico_eur | default('500.000') }} €. Sanciones regulatorias graves. Daño reputacional severo. |
| **ALTO** | Impacto significativo pero recuperable. Pérdidas económicas entre {{ bia.umbral_alto_eur | default('100.000') }} y {{ bia.umbral_critico_eur | default('500.000') }} €. Incumplimiento de obligaciones contractuales relevantes. |
| **MEDIO** | Impacto moderado. Pérdidas económicas entre {{ bia.umbral_medio_eur | default('25.000') }} y {{ bia.umbral_alto_eur | default('100.000') }} €. Retrasos operativos relevantes. |
| **BAJO** | Impacto menor. Pérdidas económicas inferiores a {{ bia.umbral_medio_eur | default('25.000') }} €. Sin afectación a clientes externos. |

### 3.3 Definiciones operativas

a) **RTO (Recovery Time Objective):** tiempo máximo admisible que un proceso o servicio puede permanecer interrumpido antes de que el impacto resulte inasumible.

b) **RPO (Recovery Point Objective):** cantidad máxima admisible de datos que pueden perderse en una interrupción, expresada en términos de tiempo (cuántos minutos u horas de actividad reciente pueden perderse).

c) **MTPD (Maximum Tolerable Period of Disruption):** período máximo durante el cual la interrupción puede prolongarse antes de que la organización deje de ser viable.

d) **MBCO (Minimum Business Continuity Objective):** nivel mínimo de servicio que debe mantenerse durante una situación de disrupción para permitir la supervivencia de la organización.

---

## 4. INVENTARIO DE PROCESOS CRÍTICOS

Se han identificado los siguientes procesos críticos para la operación de {{ cliente.razon_social }}:

| ID | Proceso | Área responsable | Criticidad global |
|---|---|---|---|
{% for proceso in bia.procesos %}
| P-{{ '%03d' % loop.index }} | {{ proceso.nombre }} | {{ proceso.area }} | {{ proceso.criticidad }} |
{% endfor %}

---

## 5. ANÁLISIS DETALLADO DE PROCESOS CRÍTICOS

{% for proceso in bia.procesos %}
### 5.{{ loop.index }} {{ proceso.nombre }}

**Identificador:** P-{{ '%03d' % loop.index }}
**Área responsable:** {{ proceso.area }}
**Responsable funcional:** {{ proceso.responsable }}

**Descripción del proceso:**

{{ proceso.descripcion }}

**Recursos críticos necesarios:**

{% for recurso in proceso.recursos %}
- **{{ recurso.tipo }}:** {{ recurso.descripcion }}
{% endfor %}

**Dependencias externas:**

{% for dep in proceso.dependencias_externas %}
- {{ dep }}
{% endfor %}

**Análisis temporal del impacto de interrupción:**

| Tiempo de interrupción | Impacto operativo | Impacto económico estimado | Impacto reputacional | Impacto legal/regulatorio |
|---|---|---|---|---|
| 1 hora | {{ proceso.impacto.h1.operativo }} | {{ proceso.impacto.h1.economico }} | {{ proceso.impacto.h1.reputacional }} | {{ proceso.impacto.h1.legal }} |
| 4 horas | {{ proceso.impacto.h4.operativo }} | {{ proceso.impacto.h4.economico }} | {{ proceso.impacto.h4.reputacional }} | {{ proceso.impacto.h4.legal }} |
| 8 horas | {{ proceso.impacto.h8.operativo }} | {{ proceso.impacto.h8.economico }} | {{ proceso.impacto.h8.reputacional }} | {{ proceso.impacto.h8.legal }} |
| 24 horas | {{ proceso.impacto.h24.operativo }} | {{ proceso.impacto.h24.economico }} | {{ proceso.impacto.h24.reputacional }} | {{ proceso.impacto.h24.legal }} |
| 72 horas | {{ proceso.impacto.h72.operativo }} | {{ proceso.impacto.h72.economico }} | {{ proceso.impacto.h72.reputacional }} | {{ proceso.impacto.h72.legal }} |
| 1 semana | {{ proceso.impacto.s1.operativo }} | {{ proceso.impacto.s1.economico }} | {{ proceso.impacto.s1.reputacional }} | {{ proceso.impacto.s1.legal }} |

**Objetivos de recuperación:**

| Métrica | Valor |
|---|---|
| **RTO (Tiempo objetivo de recuperación)** | **{{ proceso.rto }}** |
| **RPO (Punto objetivo de recuperación)** | **{{ proceso.rpo }}** |
| **MTPD (Periodo máximo tolerable)** | {{ proceso.mtpd }} |
| **MBCO (Nivel mínimo de continuidad)** | {{ proceso.mbco }} |

{% endfor %}

---

## 6. RESUMEN CONSOLIDADO DE RTO Y RPO

| Proceso | RTO | RPO | Criticidad |
|---|---|---|---|
{% for proceso in bia.procesos %}
| {{ proceso.nombre }} | {{ proceso.rto }} | {{ proceso.rpo }} | {{ proceso.criticidad }} |
{% endfor %}

---

## 7. RECURSOS CRÍTICOS IDENTIFICADOS

### 7.1 Personal clave

| Rol | Procesos a los que da soporte | Suplencia identificada |
|---|---|---|
{% for persona in bia.personal_clave %}
| {{ persona.rol }} | {{ persona.procesos }} | {{ persona.suplencia | default('Sin suplencia identificada') }} |
{% endfor %}

### 7.2 Infraestructura tecnológica crítica

| Recurso | Procesos a los que da soporte | RTO requerido |
|---|---|---|
{% for infra in bia.infraestructura_critica %}
| {{ infra.nombre }} | {{ infra.procesos }} | {{ infra.rto }} |
{% endfor %}

### 7.3 Aplicaciones críticas

| Aplicación | Función | RTO requerido | RPO requerido |
|---|---|---|---|
{% for app in bia.aplicaciones_criticas %}
| {{ app.nombre }} | {{ app.funcion }} | {{ app.rto }} | {{ app.rpo }} |
{% endfor %}

### 7.4 Proveedores críticos

| Proveedor | Servicio prestado | Procesos a los que da soporte | Plan B |
|---|---|---|---|
{% for prov in bia.proveedores_criticos %}
| {{ prov.nombre }} | {{ prov.servicio }} | {{ prov.procesos }} | {{ prov.plan_b | default('Sin plan B identificado') }} |
{% endfor %}

---

## 8. ESCENARIOS DE DISRUPCIÓN ANALIZADOS

Se han considerado los siguientes escenarios de disrupción para evaluar la respuesta del Plan de Continuidad:

| ID | Escenario | Probabilidad estimada | Impacto previsto |
|---|---|---|---|
{% for esc in bia.escenarios %}
| ESC-{{ '%03d' % loop.index }} | {{ esc.descripcion }} | {{ esc.probabilidad }} | {{ esc.impacto }} |
{% endfor %}

### 8.1 Escenarios prioritarios

Los siguientes escenarios han sido identificados como prioritarios para el desarrollo de planes de respuesta específicos:

{% for esc in bia.escenarios_prioritarios %}
**{{ loop.index }}. {{ esc.titulo }}**

- **Descripción:** {{ esc.descripcion }}
- **Procesos afectados:** {{ esc.procesos_afectados }}
- **Recursos comprometidos:** {{ esc.recursos_comprometidos }}
- **Estrategia de respuesta propuesta:** {{ esc.estrategia }}

{% endfor %}

---

## 9. ANÁLISIS DE DEPENDENCIAS

### 9.1 Dependencias internas

Las dependencias internas más críticas identificadas son:

{% for dep in bia.dependencias_internas %}
- {{ dep }}
{% endfor %}

### 9.2 Dependencias externas

Las dependencias externas más críticas identificadas son:

{% for dep in bia.dependencias_externas %}
- {{ dep }}
{% endfor %}

### 9.3 Puntos únicos de fallo (SPOF)

Se han identificado los siguientes puntos únicos de fallo que requieren atención prioritaria:

{% for spof in bia.spofs %}
- **{{ spof.nombre }}** — {{ spof.descripcion }}
  - *Mitigación propuesta:* {{ spof.mitigacion }}
{% endfor %}

---

## 10. CONCLUSIONES Y RECOMENDACIONES

### 10.1 Conclusiones del análisis

{{ bia.conclusiones }}

### 10.2 Recomendaciones para el Plan de Continuidad

{% for rec in bia.recomendaciones %}
{{ loop.index }}. {{ rec }}
{% endfor %}

### 10.3 Inversiones recomendadas

A partir del presente análisis, se identifican las siguientes inversiones prioritarias para reforzar la continuidad del servicio:

| Inversión | Justificación | Coste estimado | Prioridad |
|---|---|---|---|
{% for inv in bia.inversiones_recomendadas %}
| {{ inv.descripcion }} | {{ inv.justificacion }} | {{ inv.coste }} | {{ inv.prioridad }} |
{% endfor %}

---

## 11. APROBACIÓN Y REVISIÓN

### 11.1 Aprobación

El presente Análisis de Impacto en el Negocio ha sido elaborado por {{ bia.elaborado_por }} y se eleva al Comité de Seguridad para su aprobación formal y posterior remisión a {{ cliente.organo_aprobador_politicas }} para su conocimiento.

### 11.2 Revisión periódica

Conforme al apartado 4.2 de la Política POL-104, el presente BIA será objeto de revisión al menos con carácter **anual** y, con carácter extraordinario, cuando se produzcan cambios significativos en los servicios prestados, en la organización, en la infraestructura o en el contexto operativo de {{ cliente.razon_social }}.

**Próxima revisión prevista:** {{ bia.proxima_revision }}

---

## 12. ANEXOS

- **Anexo I:** Cuestionarios cumplimentados durante las entrevistas
- **Anexo II:** Listado completo de procesos analizados (incluidos los no críticos)
- **Anexo III:** Inventario detallado de recursos críticos
- **Anexo IV:** Matriz de dependencias completa
- **Anexo V:** Histórico de incidentes relevantes utilizados como referencia

---

**Elaborado por:** {{ bia.elaborado_por }}
**Aprobado por:** Comité de Seguridad de {{ cliente.razon_social }}
**Fecha de aprobación:** {{ bia.fecha_aprobacion }}

**Documento E-400 · {{ cliente.razon_social }} · Versión {{ bia.version | default('1.0') }}**

```

---

## INSTRUCCIONES PARA CLAUDE CODE — CIERRE DEL BLOQUE F3

### Estado del bloque F3 tras F3.1 + F3.2

Las **7 plantillas comerciales y de entrega** quedan completas:

| Código | Título | Bloque | Estado |
|---|---|---|---|
| P-001 | Propuesta Comercial Maestra | F3.1 | ✅ |
| C-001 | Contrato de Prestación de Servicios | F3.1 | ✅ |
| C-003 | Contrato de Retainer Post-Certificación | F3.1 | ✅ |
| E-001 | Ficha Resumen Ejecutivo | **F3.2** | ✅ |
| E-040 | Informe Final de Adecuación al ENS | **F3.2** | ✅ |
| E-050 | Informe de Auditoría Interna del SGSI | **F3.2** | ✅ |
| E-400 | Análisis de Impacto en el Negocio (BIA) | **F3.2** | ✅ |

### Pipeline del Motor 6 (Document Factory) para F3

A diferencia de los bloques F1 y F2 (políticas y procedimientos), las plantillas de F3 tienen características diferenciadas que el Motor 6 debe gestionar:

1. **P-001 (Propuesta)**: el Motor 17 (Effort Estimator) calcula automáticamente las horas, los honorarios y la duración con base en los datos del onboarding del Motor 16. El Motor 6 los inyecta en la plantilla. **Output**: PDF firmado digitalmente para envío al cliente potencial.

2. **C-001 y C-003 (Contratos)**: deben generarse en formato `.docx` editable para que el cliente pueda revisarlos antes de la firma, y posteriormente en PDF firmado por ambas partes. El sistema debe gestionar el ciclo de versiones (borrador → revisión → firma).

3. **E-001 (Ficha Resumen)**: es un documento dinámico que se actualiza con cada hito del proyecto. El Motor 6 debe generar versiones nuevas conservando el histórico y permitir compararlas.

4. **E-040 (Informe Final de Adecuación)**: es el documento más extenso y formal del proyecto. Debe incorporar referencias a múltiples anexos generados independientemente. El Motor 6 debe gestionar los hipervínculos y la consistencia entre el documento principal y sus anexos.

5. **E-050 (Auditoría Interna)**: requiere que el Motor 6 inserte automáticamente los hallazgos detectados durante el escaneo del Motor 8 (pentesting) y del Motor 24 (Compliance verifier).

6. **E-400 (BIA)**: requiere recopilar información de los responsables funcionales del cliente mediante un cuestionario estructurado. El Motor 16 (onboarding) debe incluir un módulo específico de captura BIA.

### Flujo de generación de los entregables del proyecto

```
Onboarding Motor 16 → datos cliente
↓
Motor 17 (Effort Estimator) → cálculo horas, honorarios, plazos
↓
Motor 6 genera P-001 (Propuesta) → PDF firmado → envío al cliente
↓
Cliente firma → Motor 6 genera C-001 (Contrato) → firma digital
↓
Inicio del proyecto → Motor 6 genera E-001 inicial
↓
Cada hito → Motor 6 actualiza E-001 (control de versiones)
↓
Fase de continuidad → Motor 6 genera E-400 (BIA) tras entrevistas
↓
Fase de implantación → Motor 6 genera 9 políticas + 12 procedimientos
↓
Fase de auditoría interna → Motor 6 genera E-050 con hallazgos del Motor 8
↓
Cierre del proyecto → Motor 6 genera E-040 (Informe Final)
↓
Cliente certificado → Motor 6 genera C-003 (Retainer) → renovación anual
```

### Próximos bloques pendientes del plan 100/100

Tras F3 quedan **3 entregables técnicos**:

- **G** — Motor 8 pentesting con MCP + LLM autónomo (Osmedeus, reNgine, PingCastle, ADRecon, GoPhish)
- **H** — LUCIA/PILAR/INES scraping real con Playwright + certificado digital
- **I** — Suite tests E2E para las 10 fases del plan

Estos tres son técnicos y contendrán código Python real en lugar de plantillas en español. Serán probablemente más cortos en líneas pero más densos en código ejecutable.

---

**Fin del Entregable F3.2.**

4 plantillas de entregables del proyecto (E-001, E-040, E-050, E-400) en español jurídico-técnico real, completando el bloque F3 con un total de 7 plantillas comerciales y de entrega. Junto con el núcleo documental F1+F2, FULKRO dispone ahora del **kit completo necesario para gestionar el ciclo comercial y operativo de un cliente real**: desde la primera reunión exploratoria hasta el certificado obtenido y el contrato de mantenimiento posterior.
