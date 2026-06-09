# F3.1 — PLANTILLAS COMERCIALES REALES (P-001, C-001, C-003)

**Plan 100/100 FULKRO — Bloque 5.1 de plantillas reales**
**Versión:** 1.0 — 9 de abril de 2026
**Continuación de:** F1.1, F1.2, F2.1, F2.2 (núcleo documental SGSI completo)

---

## ADVERTENCIA LEGAL CRÍTICA PARA MARCOS

**Las plantillas contractuales C-001 y C-003 contienen cláusulas con consecuencias jurídicas y económicas reales.** Aunque están redactadas con calidad profesional alta, **deben ser revisadas por un abogado TIC español colegiado** antes de utilizarse con un cliente real. Presupuesto orientativo de revisión: 600-1.000 € por el paquete completo de plantillas comerciales.

Puntos especialmente sensibles que requieren revisión legal:

1. **Cláusula de incompatibilidad auditor/consultor**: la norma UNE-EN ISO/IEC 17065:2012 exige separación entre la entidad consultora y la entidad de certificación ENAC. Esta cláusula está incluida en C-001 y debe redactarse correctamente para protegerte de reclamaciones del cliente.

2. **Cláusula de propiedad intelectual sobre los entregables**: Marcos retiene la propiedad de la plataforma FULKRO y de las plantillas, cediendo al cliente únicamente el uso operativo de los documentos generados específicamente para él. Esta distinción es crítica para mantener el negocio escalable.

3. **Cláusula de limitación de responsabilidad**: en consultoría ENS la responsabilidad debe limitarse al importe del contrato, no extenderse a daños indirectos ni lucro cesante.

4. **Acuerdo de Encargo del Tratamiento (DPA) anexo**: cuando Marcos trate datos personales del cliente en el ejercicio de la consultoría, deberá suscribirse el DPA del artículo 28 RGPD como anexo al contrato.

**No uses estas plantillas sin revisión legal previa.**

---

## CATÁLOGO DE PLANTILLAS DEL BLOQUE F3.1

| Código | Título | Tipo | Audiencia |
|---|---|---|---|
| **P-001** | Propuesta Comercial Maestra de Servicios ENS | Comercial | Cliente potencial (decisor) |
| **C-001** | Contrato de Prestación de Servicios de Consultoría ENS | Contrato | Cliente firmante |
| **C-003** | Contrato de Servicios de Mantenimiento Continuo (Retainer) | Contrato | Cliente certificado |

---

# DOCUMENTO P-001 — PROPUESTA COMERCIAL MAESTRA DE SERVICIOS ENS

```jinja
---
codigo_documento: "P-001"
titulo: "Propuesta de Servicios de Adecuación y Certificación al Esquema Nacional de Seguridad"
version: "{{ propuesta.version | default('1.0') }}"
fecha: "{{ propuesta.fecha_emision }}"
clasificacion: "CONFIDENCIAL — Cliente"
emitido_por: "FULKRO — Marcos Mata García"
dirigido_a: "{{ cliente.razon_social }}"
validez_oferta: "30 días naturales desde la fecha de emisión"
---

# PROPUESTA DE SERVICIOS PARA LA ADECUACIÓN Y CERTIFICACIÓN AL ESQUEMA NACIONAL DE SEGURIDAD

## {{ cliente.razon_social }}

**Propuesta P-001 · Versión {{ propuesta.version | default('1.0') }} · {{ propuesta.fecha_emision }}**

---

**Emitida por:**

FULKRO — Servicios profesionales de consultoría en cumplimiento ENS
Marcos Mata García
Madrid · {{ marcos.email | default('marcosmata@fulkro.es') }}
{{ marcos.telefono | default('+34 ___ ___ ___') }}
fulkro.es

**Dirigida a:**

{{ cliente.razon_social }}
{{ cliente.nif }}
{{ cliente.domicilio_social }}
A la atención de: {{ cliente.persona_contacto.nombre }}, {{ cliente.persona_contacto.cargo }}

---

## 1. CARTA DE PRESENTACIÓN

Estimado/a {{ cliente.persona_contacto.tratamiento | default('Sr./Sra.') }} {{ cliente.persona_contacto.apellidos }}:

Tras la reunión exploratoria celebrada el pasado {{ propuesta.fecha_reunion_exploratoria }}, me complace presentarle la propuesta de servicios profesionales para acompañar a {{ cliente.razon_social }} en su proceso de adecuación y certificación de conformidad con el Real Decreto 311/2022, de 3 de mayo, por el que se regula el Esquema Nacional de Seguridad.

Esta propuesta no es un documento estándar. Está construida específicamente sobre la información que su equipo me trasladó durante la reunión exploratoria, en particular sobre:

- La naturaleza y el alcance de los servicios que {{ cliente.razon_social }} desea certificar.
- El nivel de madurez actual de sus controles de seguridad.
- Las obligaciones legales y contractuales que motivan la decisión de certificarse.
- Los plazos en los que necesita disponer del certificado.
- El presupuesto que la organización está dispuesta a destinar al proyecto.

Mi compromiso es que, al finalizar el proyecto, su organización disponga no solo del certificado de conformidad ENS expedido por una entidad acreditada por ENAC, sino de un Sistema de Gestión de la Seguridad de la Información operativo, sostenible y útil para el negocio.

Quedo a su disposición para cualquier aclaración.

Atentamente,

**Marcos Mata García**
Consultor de Cumplimiento ENS — FULKRO

---

## 2. RESUMEN EJECUTIVO

| Concepto | Detalle |
|---|---|
| **Cliente** | {{ cliente.razon_social }} |
| **Alcance del proyecto** | {{ propuesta.alcance.descripcion_corta }} |
| **Categoría ENS objetivo** | {{ propuesta.categoria_ens }} |
| **Entidad certificadora propuesta** | {{ propuesta.certificadora_recomendada }} (ver justificación en sección 6) |
| **Duración estimada** | {{ propuesta.duracion_meses }} meses |
| **Inversión total del proyecto** | **{{ propuesta.inversion_total_eur }} € + IVA** |
| **Modalidad de pago** | {{ propuesta.modalidad_pago }} |
| **Validez de la oferta** | 30 días naturales desde {{ propuesta.fecha_emision }} |

**Desglose de la inversión:**

| Partida | Importe (€ + IVA) |
|---|---|
| Servicios profesionales FULKRO | {{ propuesta.honorarios_marcos }} € |
| Auditoría externa de certificación ({{ propuesta.certificadora_recomendada }}) | ~{{ propuesta.coste_auditoria_externa }} € (a confirmar con la entidad) |
| **TOTAL** | **{{ propuesta.inversion_total_eur }} €** |

---

## 3. CONTEXTO Y MOTIVACIÓN

El Esquema Nacional de Seguridad, regulado por el Real Decreto 311/2022, de 3 de mayo, es de obligado cumplimiento para todas las entidades del sector público español y para los proveedores del sector privado que prestan servicios a la Administración Pública. Su finalidad es garantizar que la información tratada y los servicios prestados por los sistemas de información disfrutan de una protección adecuada en términos de confidencialidad, integridad, disponibilidad, autenticidad y trazabilidad.

Para {{ cliente.razon_social }}, la certificación ENS representa:

{% if propuesta.motivacion.contratar_aapp %}
- **Acceso a contratos con Administraciones Públicas**: la certificación ENS es requisito habitual en pliegos de contratación pública, abriendo a {{ cliente.razon_social }} el acceso a un mercado de gran volumen que actualmente le está vedado o limitado.
{% endif %}
{% if propuesta.motivacion.diferenciacion_competitiva %}
- **Diferenciación competitiva frente a competidores no certificados**: en sectores donde la confianza en la seguridad de la información es un criterio de decisión, disponer del certificado ENS sitúa a {{ cliente.razon_social }} en una posición ventajosa.
{% endif %}
{% if propuesta.motivacion.cumplimiento_legal %}
- **Cumplimiento del marco legal aplicable**: como entidad obligada conforme al artículo 2 del RD 311/2022, {{ cliente.razon_social }} tiene la obligación legal de adecuarse al ENS.
{% endif %}
{% if propuesta.motivacion.refuerzo_seguridad %}
- **Refuerzo real de la postura de ciberseguridad**: más allá del certificado, el SGSI implantado proporciona una mejora tangible de la resiliencia frente a incidentes de seguridad.
{% endif %}
{% if propuesta.motivacion.imagen_marca %}
- **Refuerzo de la imagen y reputación corporativa**: el sello ENS es reconocido en el mercado español como garantía de seriedad y compromiso con la seguridad de la información.
{% endif %}

---

## 4. ALCANCE DEL PROYECTO

### 4.1 Sistemas y servicios incluidos

El alcance de la certificación que se propone para {{ cliente.razon_social }} comprende:

> **{{ propuesta.alcance.descripcion_completa }}**

**Servicios incluidos en el alcance:**

{% for servicio in propuesta.alcance.servicios %}
- {{ servicio }}
{% endfor %}

**Sistemas e infraestructura incluidos:**

{% for sistema in propuesta.alcance.sistemas %}
- {{ sistema }}
{% endfor %}

**Sedes incluidas:**

{% for sede in propuesta.alcance.sedes %}
- {{ sede.nombre }} ({{ sede.direccion }})
{% endfor %}

### 4.2 Exclusiones expresas

Quedan expresamente excluidos del alcance del presente proyecto:

{% for exclusion in propuesta.alcance.exclusiones %}
- {{ exclusion }}
{% endfor %}

### 4.3 Categoría de seguridad objetivo

Tras analizar la información facilitada en la reunión exploratoria, conforme a los criterios del Anexo I del RD 311/2022 y de la guía CCN-STIC 803, se propone como categoría de seguridad del sistema **{{ propuesta.categoria_ens }}**.

La determinación definitiva de la categoría se realizará durante la Fase 1 del proyecto a partir del análisis de impacto formal sobre las cinco dimensiones de seguridad (Confidencialidad, Integridad, Trazabilidad, Autenticidad y Disponibilidad).

---

## 5. METODOLOGÍA Y FASES DEL PROYECTO

El proyecto se ejecutará siguiendo la metodología FULKRO, estructurada en **{{ propuesta.fases | length }} fases consecutivas** con hitos verificables y entregables documentados:

{% for fase in propuesta.fases %}
### Fase {{ loop.index }} — {{ fase.nombre }}

**Duración estimada:** {{ fase.duracion_semanas }} semanas
**Hito de cierre:** {{ fase.hito }}

**Actividades principales:**

{% for actividad in fase.actividades %}
- {{ actividad }}
{% endfor %}

**Entregables de la fase:**

{% for entregable in fase.entregables %}
- {{ entregable }}
{% endfor %}

{% endfor %}

### Cronograma resumen

| Fase | Duración | Inicio (semana) | Fin (semana) |
|---|---|---|---|
{% for fase in propuesta.fases %}
| {{ fase.nombre }} | {{ fase.duracion_semanas }} sem. | S{{ fase.semana_inicio }} | S{{ fase.semana_fin }} |
{% endfor %}

**Duración total del proyecto:** {{ propuesta.duracion_meses }} meses, equivalentes a {{ propuesta.duracion_semanas }} semanas.

---

## 6. ENTIDAD CERTIFICADORA RECOMENDADA

Tras analizar el perfil de {{ cliente.razon_social }}, su sector de actividad ({{ cliente.sector }}) y sus prioridades, se propone como entidad certificadora **{{ propuesta.certificadora_recomendada }}**, por los siguientes motivos:

{% for motivo in propuesta.justificacion_certificadora %}
- {{ motivo }}
{% endfor %}

**No obstante, esta recomendación es orientativa.** Durante la Fase 1 del proyecto se solicitarán presupuestos formales a tres entidades acreditadas por ENAC, de modo que {{ cliente.razon_social }} pueda elegir con criterio entre alternativas concretas. En la Fase 1 se propondrán como alternativas:

- {{ propuesta.certificadora_alternativa_1 }}
- {{ propuesta.certificadora_alternativa_2 }}

La decisión final corresponderá a {{ cliente.razon_social }}.

**Importante:** FULKRO actúa como entidad consultora y, conforme a lo dispuesto en la norma UNE-EN ISO/IEC 17065:2012 y en la guía CCN-CERT IC-01/19, **no puede actuar simultáneamente como entidad certificadora**. La auditoría externa de certificación deberá ser contratada directamente por {{ cliente.razon_social }} con la entidad acreditada que elija, sin que FULKRO pueda intervenir en dicha contratación.

---

## 7. INVERSIÓN Y CONDICIONES ECONÓMICAS

### 7.1 Honorarios profesionales FULKRO

| Concepto | Importe |
|---|---|
| Horas estimadas de consultoría | {{ propuesta.horas_estimadas }} h |
| Tarifa por hora | {{ propuesta.tarifa_hora }} €/h |
| **Subtotal honorarios FULKRO** | **{{ propuesta.honorarios_marcos }} € + IVA** |

### 7.2 Auditoría externa de certificación

El coste de la auditoría externa por parte de la entidad certificadora ENAC se estima en **{{ propuesta.coste_auditoria_externa }} € + IVA**, con base en los precios habituales del mercado para proyectos del alcance y categoría propuestos. Este importe será **facturado directamente** por la entidad certificadora a {{ cliente.razon_social }} y no forma parte de los honorarios FULKRO.

### 7.3 Otras inversiones a considerar

Adicionalmente, durante la ejecución del proyecto pueden identificarse necesidades de inversión en herramientas, productos o servicios técnicos cuyo coste no está incluido en esta propuesta. Entre las inversiones más habituales en proyectos similares se encuentran:

- Solución de gestión de identidades y MFA corporativo: ~{{ propuesta.estimaciones_inversion.mfa | default('1.500-4.000') }} €/año
- Solución de copias de seguridad y restauración: ~{{ propuesta.estimaciones_inversion.backup | default('2.000-8.000') }} €/año
- Solución antimalware corporativa: ~{{ propuesta.estimaciones_inversion.edr | default('30-60') }} €/usuario/año
- Solución de gestión de logs / SIEM: ~{{ propuesta.estimaciones_inversion.siem | default('5.000-15.000') }} €/año

Las necesidades concretas se identificarán durante la Fase 1 (diagnóstico) y se documentarán en el Plan de Adecuación, siempre buscando la opción más eficiente para {{ cliente.razon_social }}.

### 7.4 Inversión total del proyecto

| Partida | Importe (€ + IVA) |
|---|---|
| Honorarios FULKRO | {{ propuesta.honorarios_marcos }} € |
| Auditoría externa estimada | {{ propuesta.coste_auditoria_externa }} € |
| **INVERSIÓN TOTAL ESTIMADA** | **{{ propuesta.inversion_total_eur }} €** |

### 7.5 Modalidad de pago propuesta

Los honorarios de FULKRO se facturarán siguiendo la modalidad **{{ propuesta.modalidad_pago }}**:

{% if propuesta.modalidad_pago == "hitos" %}
- **Hito 1 (firma del contrato):** 30%
- **Hito 2 (cierre Fase 2 — Plan de Adecuación):** 30%
- **Hito 3 (cierre Fase 4 — Implantación):** 25%
- **Hito 4 (entrega del Informe Final de Adecuación):** 15%
{% elif propuesta.modalidad_pago == "mensual" %}
- **Cuota mensual fija** durante la duración del proyecto.
{% elif propuesta.modalidad_pago == "fijo" %}
- **50% a la firma del contrato**
- **50% a la entrega del Informe Final de Adecuación**
{% endif %}

Los pagos se realizarán por transferencia bancaria a la cuenta indicada en cada factura, en un plazo máximo de 30 días naturales desde la fecha de emisión.

---

## 8. LO QUE INCLUYE Y LO QUE NO INCLUYE LA OFERTA

### 8.1 Lo que SÍ está incluido

✅ Diagnóstico inicial del estado del sistema y categorización formal.
✅ Análisis de riesgos completo conforme a metodología MAGERIT v3.
✅ Plan de Adecuación al ENS adaptado a la realidad de {{ cliente.razon_social }}.
✅ Declaración de Aplicabilidad personalizada.
✅ **Las 27 políticas y procedimientos del SGSI** generados específicamente para {{ cliente.razon_social }}, cubriendo el 92% del Anexo II del ENS.
✅ Acompañamiento durante la implantación de las medidas técnicas.
✅ Auditoría interna previa a la auditoría externa de certificación.
✅ Preparación específica del dossier para el auditor externo.
✅ Acompañamiento durante la auditoría externa.
✅ Soporte para la subsanación de no conformidades menores que pudieran detectarse.
✅ Sesiones de concienciación al personal del cliente (hasta 4 sesiones de 2 horas).
✅ Soporte por correo electrónico y teléfono durante la duración del proyecto.

### 8.2 Lo que NO está incluido

❌ Coste de la auditoría externa de certificación por parte de la entidad ENAC (facturación directa al cliente).
❌ Inversión en hardware, software y servicios técnicos identificados durante el diagnóstico.
❌ Implantación técnica de las medidas que requieran trabajo del personal técnico del cliente.
❌ Servicios continuos de monitorización o respuesta a incidentes (estos servicios se ofrecen separadamente bajo modalidad retainer post-certificación).
❌ Subsanación de no conformidades mayores que requieran rediseño de arquitectura.
❌ Auditorías de seguimiento o renovación posteriores al primer certificado (cubiertas por el contrato de retainer si se contrata).
❌ Asesoramiento legal específico sobre cumplimiento normativo en otras materias (RGPD avanzado, NIS2, DORA, etc.) más allá de las intersecciones con el ENS.

---

## 9. POR QUÉ ELEGIR FULKRO

**1. Plataforma propietaria optimizada para ENS.** A diferencia de las grandes consultoras que parten de plantillas genéricas, FULKRO trabaja con una plataforma propietaria especializada en cumplimiento ENS que multiplica por 4 la velocidad de generación de la documentación sin sacrificar calidad.

**2. Especialización vertical pura.** FULKRO se dedica exclusivamente al cumplimiento ENS. No es un despacho generalista que hace ENS como una más entre veinte normas distintas.

**3. Ratio 95/5.** En proyectos FULKRO, el 95% del trabajo lo realiza la consultoría y solo el 5% recae en el cliente. Su equipo no tiene que aprenderse el ENS para certificarse.

**4. Velocidad sin perder rigor.** La media del mercado para certificar una empresa mediana en categoría MEDIA está entre 12 y 18 meses. Con FULKRO, el plazo se reduce a {{ propuesta.duracion_meses }} meses sin comprometer la calidad documental.

**5. Documentación que el auditor reconoce como propia.** Las plantillas de FULKRO están alineadas con las guías CCN-STIC 802 y 808 que los auditores ENAC utilizan como referencia. Esto reduce drásticamente las no conformidades menores en auditoría.

**6. Tarifa transparente.** No hay sorpresas. La tarifa horaria es la misma para todos los clientes. Las desviaciones de horas se comunican y se autorizan formalmente antes de incurrir en ellas.

**7. Independencia certificadora.** FULKRO no tiene acuerdos comerciales con ninguna entidad certificadora ENAC. La recomendación que se hace es exclusivamente en interés del cliente.

---

## 10. PRÓXIMOS PASOS

Si la presente propuesta resulta de su interés, los siguientes pasos serían:

1. **Aceptación formal de la propuesta** mediante firma de la presente o comunicación escrita en este sentido, dentro del plazo de validez indicado en el encabezado.

2. **Firma del Contrato de Prestación de Servicios** (documento C-001), que desarrollará jurídicamente los términos aquí esbozados, incluyendo cláusulas de confidencialidad, propiedad intelectual, protección de datos, limitación de responsabilidad y resolución del contrato.

3. **Reunión de inicio (kick-off)** en un plazo máximo de 10 días hábiles desde la firma del contrato, en la que se presentará el equipo, se confirmará el calendario detallado y se acordarán los canales de trabajo.

4. **Inicio de la Fase 1 (Diagnóstico)** conforme al cronograma acordado.

---

## 11. ACEPTACIÓN DE LA PROPUESTA

Mediante la firma de la presente, {{ cliente.razon_social }} manifiesta su aceptación de los términos y condiciones de la propuesta P-001 emitida por FULKRO el {{ propuesta.fecha_emision }}, y autoriza a FULKRO a iniciar las gestiones necesarias para la formalización del Contrato de Prestación de Servicios correspondiente.

| Por {{ cliente.razon_social }} | Por FULKRO |
|---|---|
| | |
| Nombre: {{ cliente.persona_contacto.nombre_completo }} | Nombre: Marcos Mata García |
| Cargo: {{ cliente.persona_contacto.cargo }} | Cargo: Consultor |
| Fecha: _____________ | Fecha: {{ propuesta.fecha_emision }} |
| Firma: _____________ | Firma: _____________ |

---

**FULKRO — fulkro.es**
_El punto de apoyo del consultor ENS_

```

---

# DOCUMENTO C-001 — CONTRATO DE PRESTACIÓN DE SERVICIOS DE CONSULTORÍA ENS

```jinja
---
codigo_documento: "C-001"
titulo: "Contrato de Prestación de Servicios Profesionales de Consultoría ENS"
version: "{{ contrato.version | default('1.0') }}"
fecha_firma: "{{ contrato.fecha_firma }}"
clasificacion: "CONFIDENCIAL — Cliente"
---

# CONTRATO DE PRESTACIÓN DE SERVICIOS PROFESIONALES DE CONSULTORÍA EN MATERIA DE ESQUEMA NACIONAL DE SEGURIDAD

**Contrato C-001 · Versión {{ contrato.version | default('1.0') }}**

En {{ contrato.lugar_firma | default('Madrid') }}, a {{ contrato.fecha_firma }}.

---

## REUNIDOS

**De una parte,** D. Marcos Mata García, mayor de edad, con N.I.F. {{ marcos.nif }}, y domicilio profesional a efectos del presente contrato en {{ marcos.domicilio }} (en adelante, **"FULKRO"** o **"el Consultor"**), actuando en su propio nombre y derecho como profesional autónomo dado de alta en el Régimen Especial de Trabajadores Autónomos de la Seguridad Social y en el Impuesto de Actividades Económicas, epígrafe correspondiente a actividades de consultoría informática.

**Y de otra parte,** {{ cliente.razon_social }}, con N.I.F. {{ cliente.nif }} y domicilio social en {{ cliente.domicilio_social }}, debidamente representada en este acto por D./Dña. {{ cliente.firmante.nombre_completo }}, mayor de edad, con N.I.F. {{ cliente.firmante.nif }}, en su condición de {{ cliente.firmante.cargo }}, en virtud de poder bastante al efecto que declara vigente y en uso (en adelante, **"el Cliente"**).

Ambas partes (en adelante, conjuntamente, **"las Partes"**) se reconocen mutuamente la capacidad legal necesaria para suscribir el presente contrato, y a tal efecto

## EXPONEN

**I.** Que el Cliente tiene la condición de entidad obligada o voluntariamente sujeta al cumplimiento del Esquema Nacional de Seguridad regulado por el Real Decreto 311/2022, de 3 de mayo, y se encuentra interesado en obtener la certificación de conformidad con dicho marco normativo respecto del sistema de información que ha definido como alcance.

**II.** Que el Consultor es un profesional independiente especializado en la prestación de servicios de consultoría en materia de cumplimiento del Esquema Nacional de Seguridad y otras normativas conexas de seguridad de la información, y dispone de los conocimientos, experiencia y medios necesarios para acompañar al Cliente en su proceso de adecuación y certificación.

**III.** Que con fecha {{ propuesta.fecha_emision }} el Consultor remitió al Cliente la Propuesta P-001, cuya copia constituye el **Anexo I** del presente contrato, en la que se describen los servicios ofertados, el alcance, las fases del proyecto, la duración estimada y la inversión propuesta. Dicha Propuesta ha sido aceptada por el Cliente.

**IV.** Que el Consultor ha informado al Cliente, y este expresamente reconoce, de que conforme a la norma UNE-EN ISO/IEC 17065:2012 y a la guía CCN-CERT IC-01/19 sobre Criterios Generales de Auditoría y Certificación del ENS, la entidad consultora que asiste al Cliente en su adecuación **no puede simultáneamente ser la entidad certificadora** que verifica formalmente dicho cumplimiento, debiendo el Cliente contratar la auditoría externa de certificación con una entidad acreditada por ENAC distinta del Consultor.

**V.** Que las Partes desean formalizar la relación jurídica derivada de la prestación de los servicios profesionales descritos, sometiéndola a las siguientes

## CLÁUSULAS

### PRIMERA — OBJETO DEL CONTRATO

1.1. El objeto del presente contrato es la prestación, por parte del Consultor al Cliente, de servicios profesionales de consultoría destinados a alcanzar la certificación de conformidad con el Esquema Nacional de Seguridad regulado por el Real Decreto 311/2022, en la categoría **{{ contrato.categoria_ens }}** y respecto del alcance descrito en la Propuesta P-001 incorporada como Anexo I.

1.2. Los servicios profesionales objeto del contrato comprenden, con carácter no limitativo, las actividades descritas en la sección 5 de la Propuesta P-001, agrupadas en las fases descritas en dicho documento.

1.3. **Quedan expresamente excluidos** del objeto del presente contrato:

a) La auditoría externa de certificación a realizar por una entidad acreditada por ENAC, cuya contratación corresponde directamente al Cliente.

b) La adquisición e implantación técnica de productos, herramientas o servicios tecnológicos que pudieran ser necesarios para el cumplimiento de las medidas del ENS.

c) El asesoramiento jurídico especializado en otras materias distintas del cumplimiento del ENS.

d) Los servicios continuados de mantenimiento del SGSI con posterioridad a la obtención del certificado, que serán objeto, en su caso, de un contrato de retainer separado (modelo C-003).

### SEGUNDA — DURACIÓN DEL CONTRATO

2.1. El presente contrato entrará en vigor en la fecha de su firma y tendrá una duración estimada de **{{ contrato.duracion_meses }} meses** desde el inicio efectivo de los trabajos, conforme al cronograma detallado en la Propuesta P-001.

2.2. La duración estimada podrá prorrogarse de mutuo acuerdo entre las Partes cuando concurran circunstancias objetivas que así lo justifiquen, en particular:

a) Retrasos imputables al Cliente en la entrega de información o en la disponibilidad de su personal.

b) Modificaciones sustanciales del alcance solicitadas por el Cliente.

c) Detección durante el diagnóstico de un nivel de madurez significativamente inferior al inicialmente declarado.

d) Causas de fuerza mayor.

2.3. Cualquier prórroga deberá formalizarse por escrito mediante adenda al presente contrato, especificando la nueva duración estimada y, en su caso, la modificación de los honorarios profesionales correspondiente.

### TERCERA — HONORARIOS PROFESIONALES Y CONDICIONES DE PAGO

3.1. **Honorarios.** El Cliente abonará al Consultor en concepto de honorarios profesionales la cantidad total de **{{ contrato.honorarios_eur }} euros más el IVA aplicable**, conforme al desglose y condiciones de la Propuesta P-001.

3.2. **Modalidad de facturación.** Los honorarios se facturarán siguiendo la modalidad de **{{ contrato.modalidad_pago }}** establecida en la sección 7.5 de la Propuesta P-001.

3.3. **Plazo de pago.** Las facturas emitidas por el Consultor se abonarán por transferencia bancaria a la cuenta que se indique en la propia factura, en el plazo máximo de **30 días naturales** desde la fecha de emisión.

3.4. **Demora en el pago.** El retraso en el pago de las facturas devengará automáticamente y sin necesidad de previo requerimiento los intereses de demora previstos en la Ley 3/2004, de 29 de diciembre, por la que se establecen medidas de lucha contra la morosidad en las operaciones comerciales.

3.5. **Suspensión de los servicios.** El Consultor podrá suspender la prestación de los servicios cuando el Cliente incurra en demora en el pago superior a 30 días naturales sobre el plazo establecido, previo aviso por escrito con cinco días hábiles de antelación. La suspensión no exime al Cliente de su obligación de pago de los servicios ya prestados.

3.6. **Trabajos adicionales.** Cualquier trabajo solicitado por el Cliente que exceda del alcance descrito en la Propuesta P-001 deberá ser objeto de presupuesto específico previamente aceptado por escrito antes de su ejecución. En ningún caso el Consultor estará obligado a realizar trabajos no incluidos en el alcance sin la correspondiente aceptación expresa.

### CUARTA — OBLIGACIONES DEL CONSULTOR

4.1. El Consultor se obliga a:

a) Prestar los servicios profesionales con la diligencia, profesionalidad y conocimientos técnicos exigibles a un consultor especializado en cumplimiento del Esquema Nacional de Seguridad, conforme a las buenas prácticas del sector.

b) Cumplir con el cronograma establecido en la Propuesta P-001, salvo causas justificadas o imputables al Cliente.

c) Comunicar al Cliente cualquier circunstancia que pudiera afectar al desarrollo normal del proyecto.

d) Mantener la confidencialidad de toda la información a la que acceda en el ejercicio de sus funciones, conforme a la cláusula séptima.

e) Aplicar las medidas de seguridad necesarias para proteger la información del Cliente que se encuentre bajo su custodia.

f) Suscribir y mantener vigente durante toda la duración del contrato un seguro de responsabilidad civil profesional con cobertura suficiente para los riesgos derivados de la prestación de los servicios.

g) Cumplir con sus obligaciones tributarias y de Seguridad Social, exonerando expresamente al Cliente de cualquier responsabilidad al respecto.

4.2. El Consultor presta sus servicios como **profesional autónomo independiente**, sin que del presente contrato pueda derivarse en ningún caso relación laboral ni de dependencia con el Cliente. El Consultor organiza libremente su tiempo y sus medios para el cumplimiento del objeto del contrato.

### QUINTA — OBLIGACIONES DEL CLIENTE

5.1. El Cliente se obliga a:

a) Facilitar al Consultor toda la información, documentación, accesos y recursos necesarios para la correcta prestación de los servicios, en los plazos que razonablemente se le soliciten.

b) Designar un **interlocutor único** con capacidad de decisión, que actuará como punto de contacto principal con el Consultor durante la duración del proyecto.

c) Garantizar la disponibilidad del personal del Cliente que deba intervenir en las distintas fases del proyecto, en particular en las reuniones de trabajo y entrevistas previstas.

d) Adoptar oportunamente las decisiones que correspondan a su ámbito de competencia para no obstaculizar el avance del proyecto.

e) Asumir directamente los costes de la auditoría externa de certificación, así como los de cualquier inversión técnica que resulte necesaria para el cumplimiento de las medidas del ENS.

f) Abonar los honorarios profesionales en los términos pactados.

5.2. Las decisiones que correspondan al Cliente en su ámbito propio de gobierno (aprobación de políticas, asignación de roles, autorización de excepciones, asunción de riesgos residuales, contratación de la entidad certificadora) son de su exclusiva responsabilidad. El Consultor proporcionará el asesoramiento técnico necesario, pero la decisión final corresponderá siempre al Cliente.

### SEXTA — INCOMPATIBILIDAD AUDITOR-CONSULTOR

6.1. Las Partes reconocen expresamente que, conforme a lo dispuesto en la norma **UNE-EN ISO/IEC 17065:2012**, en la guía **CCN-CERT IC-01/19** del Centro Criptológico Nacional y en los principios generales aplicables a las entidades de certificación acreditadas por ENAC, **existe una incompatibilidad estructural** entre las funciones de consultoría y las funciones de auditoría externa de certificación, en garantía de la imparcialidad y objetividad del proceso de certificación.

6.2. En consecuencia, el Consultor **no podrá**, ni durante la vigencia del presente contrato ni con posterioridad a su finalización, actuar como auditor externo de certificación del Cliente respecto del mismo sistema de información objeto del presente contrato. Queda expresamente excluida la posibilidad de que el Consultor preste servicios de certificación al Cliente.

6.3. La auditoría externa de certificación del sistema deberá ser contratada por el Cliente, de forma directa e independiente, con una entidad acreditada por ENAC y distinta del Consultor. El Consultor podrá facilitar al Cliente información orientativa sobre las entidades acreditadas, pero no actuará como intermediario en la contratación ni recibirá compensación alguna de las entidades certificadoras.

6.4. El Cliente reconoce haber sido informado de esta limitación con anterioridad a la firma del presente contrato y la acepta expresamente.

### SÉPTIMA — CONFIDENCIALIDAD

7.1. Las Partes se comprometen a mantener la más estricta confidencialidad sobre toda la información, datos, documentos, conocimientos técnicos, planes estratégicos, datos comerciales y cualquier otra información de carácter confidencial a la que accedan como consecuencia de la ejecución del presente contrato, así como a no utilizarla para fines distintos de los previstos en el mismo.

7.2. La obligación de confidencialidad subsistirá durante la vigencia del contrato y durante un período de **cinco (5) años** a contar desde su extinción, por cualquier causa.

7.3. La obligación de confidencialidad no se extenderá a la información que:

a) Sea o llegue a ser de dominio público sin culpa de la parte receptora.

b) Fuera ya conocida por la parte receptora antes de su recepción, debiendo poderlo acreditar fehacientemente.

c) Fuera obtenida lícitamente de un tercero sin obligación de confidencialidad.

d) Deba ser comunicada en cumplimiento de una obligación legal o de un requerimiento de autoridad competente, en cuyo caso la parte obligada lo notificará a la otra de forma previa siempre que sea legalmente posible.

7.4. El incumplimiento de esta cláusula será considerado incumplimiento esencial del contrato y dará derecho a la parte perjudicada a su resolución, sin perjuicio de la indemnización por daños y perjuicios que corresponda.

### OCTAVA — PROTECCIÓN DE DATOS PERSONALES

8.1. En la medida en que la prestación de los servicios objeto del presente contrato implique para el Consultor el acceso a datos personales de los que el Cliente sea responsable del tratamiento, el Consultor tendrá la condición de **encargado del tratamiento** conforme al artículo 28 del Reglamento (UE) 2016/679 (RGPD).

8.2. La regulación específica de la relación entre responsable y encargado del tratamiento se contiene en el **Anexo II** al presente contrato (Acuerdo de Encargo del Tratamiento), que las Partes suscriben como parte integrante e inseparable del contrato.

8.3. Sin perjuicio de lo anterior, el Consultor:

a) Tratará los datos personales del Cliente exclusivamente conforme a las instrucciones documentadas del Cliente.

b) Garantizará que las personas autorizadas a tratar los datos personales se han comprometido a respetar la confidencialidad.

c) Adoptará las medidas técnicas y organizativas apropiadas para garantizar un nivel de seguridad adecuado al riesgo.

d) No subcontratará a terceros el tratamiento sin la autorización previa por escrito del Cliente.

e) Asistirá al Cliente en la respuesta al ejercicio de los derechos de los interesados.

f) Notificará al Cliente, sin dilación indebida, cualquier violación de la seguridad de los datos personales.

g) A elección del Cliente, suprimirá o devolverá todos los datos personales una vez finalizada la prestación de los servicios.

### NOVENA — PROPIEDAD INTELECTUAL E INDUSTRIAL

9.1. **Plataforma FULKRO.** Las Partes reconocen expresamente que la plataforma FULKRO, su software, sus plantillas maestras, su metodología y, en general, todos los elementos que la componen, son propiedad exclusiva del Consultor. El presente contrato no transfiere al Cliente ningún derecho sobre la plataforma FULKRO ni sobre los elementos que la integran.

9.2. **Documentos generados específicamente para el Cliente.** Los documentos generados específicamente para el Cliente en el marco del presente contrato (políticas, procedimientos, instrucciones técnicas, informes, registros) son entregados al Cliente para su uso interno y operativo. El Cliente adquiere sobre dichos documentos un **derecho de uso perpetuo, no exclusivo y gratuito** para los fines internos de su organización, incluyendo el derecho a modificarlos, adaptarlos y conservarlos.

9.3. **Limitación.** El Cliente no podrá, sin consentimiento expreso y por escrito del Consultor:

a) Comercializar los documentos generados.
b) Cederlos a terceros para su uso comercial.
c) Utilizarlos como base para la prestación de servicios de consultoría a terceros.
d) Utilizarlos en perjuicio del prestigio o intereses legítimos del Consultor.

9.4. **Propiedad intelectual del Cliente.** El Consultor reconoce y respeta la propiedad intelectual e industrial del Cliente sobre la información y los activos a los que acceda en el ejercicio de sus funciones, sin que del presente contrato se derive cesión alguna de derechos sobre los mismos.

### DÉCIMA — LIMITACIÓN DE RESPONSABILIDAD

10.1. El Consultor responderá ante el Cliente por los daños directos que le cause como consecuencia del incumplimiento doloso o gravemente negligente de las obligaciones derivadas del presente contrato.

10.2. La responsabilidad total del Consultor frente al Cliente, por cualquier causa o concepto derivado del presente contrato, **no podrá exceder en ningún caso del importe total de los honorarios efectivamente percibidos** por el Consultor en el marco del mismo, salvo que la legislación aplicable establezca expresamente lo contrario.

10.3. El Consultor **no responderá en ningún caso** por:

a) Daños indirectos, lucro cesante, pérdida de oportunidades de negocio, daño reputacional, o daños consecuenciales de cualquier naturaleza.

b) Decisiones adoptadas por el Cliente en su ámbito propio de competencia, aun cuando hayan sido tomadas con asesoramiento del Consultor.

c) La no obtención del certificado de conformidad ENS por causas no imputables exclusivamente al Consultor, incluyendo, entre otras, decisiones discrecionales del auditor externo, cambios normativos sobrevenidos, deficiencias técnicas no subsanadas por el Cliente o falta de cooperación del Cliente.

d) Incidentes de seguridad o incumplimientos normativos del Cliente derivados de la actuación de su propio personal o de terceros ajenos al Consultor.

e) Daños causados por fuerza mayor, caso fortuito o acontecimientos extraordinarios fuera del control razonable del Consultor.

10.4. **Compromiso del Consultor.** No obstante lo anterior, el Consultor se compromete a aplicar todos sus conocimientos y diligencia profesional para alcanzar el objetivo del proyecto. Si por causas imputables exclusivamente al Consultor el Cliente no obtiene el certificado de conformidad ENS, el Consultor se compromete a continuar prestando los servicios necesarios para alcanzarlo, sin coste adicional, hasta su efectiva obtención o hasta la fecha en que el Cliente decida fundadamente abandonar el intento.

### UNDÉCIMA — RESOLUCIÓN DEL CONTRATO

11.1. El presente contrato podrá resolverse por las siguientes causas:

a) **Mutuo acuerdo** entre las Partes, formalizado por escrito.

b) **Cumplimiento del objeto** del contrato, con la entrega del Informe Final de Adecuación y el cierre del proyecto.

c) **Incumplimiento esencial** de las obligaciones contractuales por cualquiera de las Partes, previo requerimiento por escrito a la parte incumplidora otorgándole un plazo de quince (15) días hábiles para subsanar el incumplimiento.

d) **Demora en el pago** superior a 60 días sobre el plazo establecido, a instancia del Consultor.

e) **Imposibilidad sobrevenida** de cumplir con el objeto del contrato por causas de fuerza mayor.

f) **Concurso, liquidación o cese de actividad** de cualquiera de las Partes.

11.2. **Efectos de la resolución.** En caso de resolución anticipada del contrato:

a) El Consultor facturará al Cliente los servicios efectivamente prestados hasta la fecha de la resolución, conforme a las horas dedicadas y a la tarifa horaria pactada.

b) El Cliente abonará dichos servicios en el plazo establecido en la cláusula tercera.

c) El Consultor entregará al Cliente todos los entregables completados hasta la fecha de la resolución.

d) Subsistirán las obligaciones de confidencialidad, las relativas a la protección de datos personales y las de propiedad intelectual.

### DUODÉCIMA — NOTIFICACIONES

12.1. Cualquier comunicación entre las Partes derivada del presente contrato se realizará por escrito, dirigida a las direcciones indicadas en el encabezamiento o a las que las Partes designen en el futuro mediante notificación a la otra parte.

12.2. Se considerarán medios válidos de notificación:

a) El correo electrónico dirigido a las direcciones designadas, con confirmación de lectura.
b) El correo postal certificado con acuse de recibo.
c) Cualquier otro medio que deje constancia fehaciente de la recepción.

### DECIMOTERCERA — LEGISLACIÓN APLICABLE Y JURISDICCIÓN

13.1. El presente contrato se regirá e interpretará conforme a la legislación española.

13.2. Para la resolución de cualquier controversia derivada de la interpretación o ejecución del presente contrato, las Partes, con renuncia expresa a su propio fuero, se someten a la jurisdicción de los **Juzgados y Tribunales de la ciudad de Madrid**.

13.3. Sin perjuicio de lo anterior, las Partes podrán, si así lo acuerdan, someter las controversias a mediación previa ante un mediador profesional registrado en el Ministerio de Justicia.

### DECIMOCUARTA — INTEGRIDAD DEL ACUERDO

14.1. El presente contrato, junto con sus Anexos, constituye el acuerdo completo entre las Partes en relación con su objeto, sustituyendo cualquier acuerdo, propuesta, comunicación o entendimiento anterior, verbal o escrito.

14.2. Cualquier modificación del presente contrato deberá realizarse por escrito y firmada por ambas Partes para ser válida.

14.3. La nulidad de alguna de las cláusulas del presente contrato no afectará a la validez del resto, que continuarán siendo plenamente eficaces.

---

Y para que así conste, las Partes firman el presente contrato en dos ejemplares y a un solo efecto, en el lugar y fecha indicados al principio.

| Por FULKRO | Por {{ cliente.razon_social }} |
|---|---|
| | |
| Fdo.: D. Marcos Mata García | Fdo.: D./Dña. {{ cliente.firmante.nombre_completo }} |
| N.I.F.: {{ marcos.nif }} | Cargo: {{ cliente.firmante.cargo }} |

---

## ANEXOS AL CONTRATO

- **Anexo I:** Propuesta P-001 íntegra (incorporada por referencia)
- **Anexo II:** Acuerdo de Encargo del Tratamiento de Datos Personales (art. 28 RGPD)
- **Anexo III:** Definición detallada del alcance del proyecto
- **Anexo IV:** Cronograma detallado y matriz de hitos

```

---

# DOCUMENTO C-003 — CONTRATO DE SERVICIOS DE MANTENIMIENTO CONTINUO (RETAINER POST-CERTIFICACIÓN)

```jinja
---
codigo_documento: "C-003"
titulo: "Contrato de Servicios de Mantenimiento del SGSI ENS (Retainer)"
version: "{{ contrato.version | default('1.0') }}"
fecha_firma: "{{ contrato.fecha_firma }}"
clasificacion: "CONFIDENCIAL — Cliente"
---

# CONTRATO DE SERVICIOS DE MANTENIMIENTO CONTINUO DEL SISTEMA DE GESTIÓN DE LA SEGURIDAD DE LA INFORMACIÓN (SGSI ENS)

**Contrato C-003 · Modalidad RETAINER · Versión {{ contrato.version | default('1.0') }}**

En {{ contrato.lugar_firma | default('Madrid') }}, a {{ contrato.fecha_firma }}.

---

## REUNIDOS

**De una parte,** D. Marcos Mata García, con N.I.F. {{ marcos.nif }}, y domicilio profesional en {{ marcos.domicilio }}, en su condición de profesional autónomo independiente (en adelante, **"FULKRO"** o **"el Consultor"**).

**Y de otra parte,** {{ cliente.razon_social }}, con N.I.F. {{ cliente.nif }} y domicilio social en {{ cliente.domicilio_social }}, debidamente representada por D./Dña. {{ cliente.firmante.nombre_completo }}, en su condición de {{ cliente.firmante.cargo }} (en adelante, **"el Cliente"**).

## EXPONEN

**I.** Que con fecha {{ contrato.fecha_contrato_anterior }} las Partes suscribieron un Contrato de Prestación de Servicios Profesionales de Consultoría ENS (referencia C-001), cuyo objeto era la adecuación del Cliente al Esquema Nacional de Seguridad y la obtención del correspondiente certificado de conformidad.

**II.** Que con fecha {{ contrato.fecha_certificacion }} el Cliente obtuvo el certificado de conformidad ENS expedido por {{ contrato.entidad_certificadora }}, en categoría {{ contrato.categoria_ens }}, con vigencia hasta {{ contrato.fecha_caducidad_certificado }}.

**III.** Que el certificado de conformidad ENS, de acuerdo con la normativa aplicable, requiere ser renovado con periodicidad bienal mediante la realización de una nueva auditoría de certificación. Adicionalmente, el mantenimiento de la conformidad exige la realización continua de actividades de gobernanza, supervisión y mejora del SGSI implantado.

**IV.** Que el Cliente desea contar con el acompañamiento profesional continuo del Consultor para el mantenimiento del SGSI durante el período de validez del certificado y para la preparación de la futura auditoría de renovación.

**V.** Que las Partes desean formalizar la prestación de los servicios de mantenimiento continuo conforme a las siguientes

## CLÁUSULAS

### PRIMERA — OBJETO

1.1. El objeto del presente contrato es la prestación, por parte del Consultor al Cliente, de servicios profesionales continuados destinados al **mantenimiento del Sistema de Gestión de la Seguridad de la Información** del Cliente conforme al ENS, durante el período de validez de su certificado de conformidad y, en particular, hasta la próxima auditoría de renovación.

1.2. Los servicios incluidos en el presente contrato comprenden:

a) **Soporte continuo** por correo electrónico y teléfono para resolución de consultas operativas del Cliente sobre el SGSI.

b) **Revisión documental anual** de las políticas, procedimientos e instrucciones técnicas del SGSI, con propuesta de actualización de los documentos cuya vigencia lo requiera.

c) **Acompañamiento en la actualización del Análisis de Riesgos** anual conforme al procedimiento E-200.

d) **Acompañamiento en la realización de la auditoría interna** anual del SGSI conforme al procedimiento E-234, con asistencia opcional como auditor independiente.

e) **Vigilancia regulatoria continua**: notificación al Cliente de cualquier cambio normativo significativo (RD 311/2022, ITS, guías CCN-STIC, RGPD, NIS2, DORA en su caso) que pueda afectar al SGSI, con propuesta de las acciones necesarias para mantener el cumplimiento.

f) **Análisis de incidentes de seguridad** notificados por el Cliente, con propuesta de medidas correctivas.

g) **Preparación específica de la auditoría de renovación** durante los tres meses anteriores a su realización, incluyendo revisión documental, simulacro de auditoría y acompañamiento durante la auditoría externa.

h) **Reuniones periódicas de seguimiento** del SGSI conforme a la cláusula segunda.

### SEGUNDA — RÉGIMEN DE PRESTACIÓN

2.1. Los servicios se prestarán bajo modalidad de **retainer mensual con horas dedicadas predefinidas**, garantizando al Cliente la disponibilidad del Consultor para los servicios objeto del presente contrato.

2.2. El nivel de servicio contratado por el Cliente, conforme a la propuesta P-001-R que se adjunta como Anexo I, es:

| Concepto | Detalle |
|---|---|
| Modalidad | {{ retainer.modalidad }} |
| Horas mensuales incluidas | {{ retainer.horas_mensuales }} h/mes |
| Horas anuales incluidas | {{ retainer.horas_anuales }} h/año |
| Reuniones periódicas presenciales o por videoconferencia | {{ retainer.frecuencia_reuniones }} |
| Tiempo de respuesta a consultas urgentes | {{ retainer.sla_respuesta_urgente | default('4 horas hábiles') }} |
| Tiempo de respuesta a consultas ordinarias | {{ retainer.sla_respuesta_ordinaria | default('24 horas hábiles') }} |

2.3. **Horas no consumidas.** Las horas no consumidas en un mes podrán acumularse al mes siguiente hasta un máximo del **doble del cupo mensual**. Las horas acumuladas que excedan dicho límite se perderán al final del mes correspondiente.

2.4. **Horas adicionales.** Cuando el Cliente requiera servicios que excedan del cupo de horas contratado, el Consultor presentará presupuesto específico previo para las horas adicionales, que serán facturadas a la tarifa horaria de **{{ retainer.tarifa_hora_adicional }} €/h + IVA**.

2.5. **Servicios excluidos.** Los siguientes servicios no están incluidos en el retainer y, en su caso, serán objeto de presupuesto específico:

a) Implantación técnica de nuevos controles o tecnologías.
b) Adecuación a normativas distintas del ENS (incorporación de ISO 27001, ISO 22301, NIS2, DORA, etc.).
c) Ampliación significativa del alcance del certificado.
d) Respuesta a incidentes de seguridad graves que requieran dedicación intensiva (más de 8 horas en un solo incidente).
e) Asesoramiento jurídico especializado.
f) Auditorías internas extraordinarias fuera del calendario anual ordinario.

### TERCERA — DURACIÓN

3.1. El presente contrato tendrá una duración inicial de **veinticuatro (24) meses**, contados desde la fecha de su firma, coincidiendo con el período de validez del certificado de conformidad ENS del Cliente.

3.2. **Renovación automática.** Al término del período inicial, el contrato se renovará automáticamente por períodos sucesivos de doce (12) meses, salvo que cualquiera de las Partes comunique a la otra su voluntad de no renovar con una antelación mínima de **dos (2) meses** a la fecha de finalización del período en curso.

3.3. **Resolución anticipada.** Cualquiera de las Partes podrá resolver anticipadamente el presente contrato preavisando por escrito con una antelación mínima de **tres (3) meses**. La parte que resuelva anticipadamente sin causa justificada no estará obligada a indemnización, pero deberá abonar los servicios efectivamente prestados hasta la fecha de la resolución.

### CUARTA — CONTRAPRESTACIÓN ECONÓMICA

4.1. **Cuota mensual.** El Cliente abonará al Consultor en concepto de cuota mensual de retainer la cantidad de **{{ retainer.cuota_mensual_eur }} euros más el IVA aplicable**.

4.2. **Facturación.** La cuota mensual se facturará por anticipado dentro de los cinco primeros días naturales de cada mes y deberá ser abonada en el plazo máximo de quince días naturales desde la fecha de emisión.

4.3. **Revisión anual.** La cuota mensual será revisada anualmente conforme a la variación del Índice de Precios al Consumo publicado por el Instituto Nacional de Estadística para el período anual anterior, sin que en ningún caso pueda producirse una revisión a la baja.

4.4. **Demora en el pago.** El retraso en el pago de las cuotas mensuales devengará automáticamente los intereses de demora previstos en la Ley 3/2004, y facultará al Consultor a suspender la prestación de los servicios previo aviso de cinco días hábiles.

### QUINTA — REMISIÓN AL CONTRATO PRINCIPAL

5.1. Las cláusulas del Contrato C-001 firmado entre las Partes con fecha {{ contrato.fecha_contrato_anterior }} relativas a:

- Confidencialidad
- Protección de datos personales (incluido el Anexo II del DPA)
- Propiedad intelectual e industrial
- Limitación de responsabilidad
- Incompatibilidad auditor-consultor
- Notificaciones
- Legislación aplicable y jurisdicción

se aplicarán íntegramente al presente contrato y se entienden incorporadas por referencia, salvo que en el presente contrato se establezca expresamente lo contrario.

### SEXTA — COMPROMISO REFORZADO ANTE LA AUDITORÍA DE RENOVACIÓN

6.1. El Consultor se compromete a aplicar toda la diligencia profesional necesaria durante los tres meses anteriores a la auditoría de renovación para asegurar que el Cliente llega a dicha auditoría en condiciones óptimas para superarla.

6.2. Si la auditoría de renovación detectara no conformidades imputables exclusivamente al Consultor por defectos en el mantenimiento del SGSI durante el periodo del retainer, el Consultor se obliga a colaborar gratuitamente en su subsanación, dentro del cupo de horas del propio retainer, hasta su completa resolución.

---

Y para que así conste, las Partes firman el presente contrato en dos ejemplares y a un solo efecto, en el lugar y fecha indicados al principio.

| Por FULKRO | Por {{ cliente.razon_social }} |
|---|---|
| | |
| Fdo.: D. Marcos Mata García | Fdo.: D./Dña. {{ cliente.firmante.nombre_completo }} |

---

## ANEXOS

- **Anexo I:** Propuesta P-001-R (oferta de retainer)
- **Anexo II:** Calendario anual de actividades de mantenimiento

```

---

**Fin del Entregable F3.1.**

3 plantillas comerciales reales en español jurídico-comercial: propuesta maestra (P-001), contrato principal de consultoría (C-001) con las 14 cláusulas críticas incluyendo incompatibilidad auditor/consultor, y contrato retainer post-certificación (C-003). En el bloque F3.2 cierro los 4 entregables del proyecto: ficha resumen ejecutivo (E-001), informe final de adecuación (E-040), informe de auditoría interna (E-050) y BIA (E-400).
