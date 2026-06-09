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

> **Fecha de emisión:** {{ propuesta.fecha_emision }}
> **Validez de la oferta:** 30 días naturales desde la fecha de emisión (caduca el {{ propuesta.fecha_emision | add_days_es(30) }}).

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

## 11. VALIDEZ Y CADUCIDAD DE LA OFERTA

Esta propuesta económica tiene una **validez de 30 días naturales** a contar desde la fecha de emisión ({{ propuesta.fecha_emision }}). La oferta **caduca automáticamente el {{ propuesta.fecha_emision | add_days_es(30) }}** sin necesidad de notificación adicional por parte de FULKRO.

Transcurrido dicho plazo sin aceptación formal, los precios, plazos y condiciones aquí recogidos podrán ser revisados por FULKRO en función de la variación del entorno regulatorio, de los costes operativos o de la disponibilidad profesional del Consultor.

**Para formalizar la aceptación dentro del plazo, el Cliente podrá:**

a) Firmar la presente propuesta en la sección 12 y devolverla por correo electrónico a {{ marcos.email | default('marcosmata@fulkro.es') }}, o

b) Proceder directamente a la firma del Contrato C-001 (Implantación ENS) o C-003 (Retainer) que acompaña a esta propuesta, o

c) Notificar por escrito (correo electrónico válido) la aceptación antes del {{ propuesta.fecha_emision | add_days_es(30) }}.

La presente propuesta no obliga a FULKRO más allá del plazo de 30 días aquí indicado, ni obliga al Cliente mientras no se haya producido alguno de los actos de aceptación anteriormente descritos. No supone oferta unilateral irretractable en los términos del artículo 1.262 del Código Civil.

---

## 12. ACEPTACIÓN DE LA PROPUESTA

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
