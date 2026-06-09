# DOCUMENTO E-040 — INFORME FINAL DE ADECUACIÓN AL ENS

**Es el entregable principal del proyecto.** El documento que el cliente presenta al auditor externo ENAC y que prueba que está preparado para la auditoría de certificación. Es el documento más extenso y formal del proyecto.

```jinja
---
codigo_documento: "E-040"
titulo: "Informe Final de Adecuación al Esquema Nacional de Seguridad"
version: "{{ informe.version | default('1.0') }}"
fecha: "{{ informe.fecha_emision }}"
clasificacion: "CONFIDENCIAL — Cliente"
elaborado_por: "Marcos Mata García — Consultor independiente en ENS"
revisado_por: "{{ responsables.responsable_seguridad.nombre }}"
aprobado_por: "{{ cliente.organo_aprobador_politicas }}"
---

# INFORME FINAL DE ADECUACIÓN AL ESQUEMA NACIONAL DE SEGURIDAD

## {{ cliente.razon_social }}

**Documento E-040 · Versión {{ informe.version | default('1.0') }} · {{ informe.fecha_emision }}**

---

## 1. RESUMEN EJECUTIVO

El presente informe documenta el resultado del proyecto de adecuación de **{{ cliente.razon_social }}** al Esquema Nacional de Seguridad regulado por el Real Decreto 311/2022, de 3 de mayo, llevado a cabo entre el {{ proyecto.fecha_inicio }} y el {{ proyecto.fecha_fin }}, con el objetivo de obtener la certificación de conformidad en categoría **{{ proyecto.categoria_ens }}**.

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

El proyecto se ha ejecutado siguiendo una metodología alineada con las guías CCN-STIC 805 (Política de Seguridad), 806 (Plan de Adecuación) y 808 (Verificación del cumplimiento del ENS) y con el ciclo PDCA de la norma UNE-EN ISO/IEC 27001:2022.

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

### 11.3 Compromiso del consultor

El consultor se compromete a acompañar a {{ cliente.razon_social }} durante la auditoría externa, conforme a lo establecido en el contrato de consultoría suscrito entre las partes y, posteriormente, mediante la suscripción de un contrato de mantenimiento post-certificación si así lo decide la dirección.

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

**Elaborado por:** Marcos Mata García, Consultor independiente en Esquema Nacional de Seguridad
**Revisado por:** {{ responsables.responsable_seguridad.nombre }} — {{ responsables.responsable_seguridad.cargo }}
**Aprobado por:** {{ cliente.organo_aprobador_politicas }}
**Fecha:** {{ informe.fecha_emision }}

**Documento E-040 · {{ cliente.razon_social }} · Versión {{ informe.version | default('1.0') }}**

```

---
