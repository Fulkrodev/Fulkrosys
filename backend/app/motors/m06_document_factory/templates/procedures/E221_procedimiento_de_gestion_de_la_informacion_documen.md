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
