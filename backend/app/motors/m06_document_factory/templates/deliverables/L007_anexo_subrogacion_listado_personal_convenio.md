---
codigo_documento: "L-007"
titulo: "Anexo al Compromiso de Subrogación · Listado de Personal y Condiciones Laborales"
version: "{{ proyecto.version_actual if proyecto.version_actual else '1.0' }}"
clasificacion: "INTERNA · DATOS DE CARÁCTER PERSONAL"
norma_aplicable: "LCSP Art. 130.3 + ET Art. 44 + Convenio colectivo aplicable + RGPD Art. 6.1.b)"
documento_madre: "L-006"
---

# ANEXO AL COMPROMISO DE SUBROGACIÓN · LISTADO DEL PERSONAL AFECTADO Y CONDICIONES LABORALES

**Documento L-007 — Versión {{ proyecto.version_actual if proyecto.version_actual else '1.0' }}**

---

{% set contrato_ref = contrato.referencia if contrato and contrato.referencia else '[REFERENCIA EXPEDIENTE]' %}
{% set convenio = subrogacion.convenio_colectivo_aplicable if subrogacion and subrogacion.convenio_colectivo_aplicable else '[Convenio colectivo aplicable]' %}
{% set fecha_info = subrogacion.fecha_info_recibida if subrogacion and subrogacion.fecha_info_recibida else '[fecha]' %}
{% set organo_info = subrogacion.organo_facilitador_info if subrogacion and subrogacion.organo_facilitador_info else '[órgano facilitador]' %}
{% set tiene_personal = subrogacion.personal_subrogable and subrogacion.personal_subrogable | length > 0 %}
{% set num_personal = subrogacion.personal_subrogable | length if subrogacion and subrogacion.personal_subrogable else 0 %}
{% set representante_nombre = cliente.representante.nombre if cliente.representante and cliente.representante.nombre else '[REPRESENTANTE LEGAL]' %}
{% set representante_cargo = cliente.representante.cargo if cliente.representante and cliente.representante.cargo else '[CARGO]' %}

## 1. OBJETO DEL ANEXO

El presente Anexo desarrolla y complementa el Compromiso de Subrogación L-006 presentado por **{{ cliente.razon_social }}** (NIF **{{ cliente.nif }}**) en el procedimiento de contratación con referencia **{{ contrato_ref }}**, detallando el listado individualizado del personal afectado por la eventual subrogación y las condiciones laborales asociadas a cada puesto.

La información contenida en este Anexo se basa íntegramente en la facilitada por **{{ organo_info }}** en fecha **{{ fecha_info }}**, conforme a la obligación informativa del artículo 130 LCSP.

## 2. MARCO NORMATIVO Y CONVENIO COLECTIVO APLICABLE

| Concepto | Referencia |
|----------|------------|
| Ley reguladora del contrato | Ley 9/2017 LCSP · Art. 130 |
| Norma laboral aplicable | Real Decreto Legislativo 2/2015 · Estatuto de los Trabajadores · Art. 44 |
| Convenio colectivo aplicable | **{{ convenio }}** |
| Base jurídica del tratamiento de datos | Reglamento (UE) 2016/679 (RGPD) · Art. 6.1.b) ejecución contractual · Art. 6.1.c) cumplimiento obligación legal LCSP |

## 3. LISTADO DEL PERSONAL OBJETO DE SUBROGACIÓN

{% if tiene_personal %}
Personal afectado: **{{ num_personal }}** persona(s) trabajadora(s).

| Puesto | Antigüedad | Tipo de contrato | Jornada anual | Retribución bruta anual | Complementos | Categoría convenio |
|--------|-----------:|------------------|---------------:|-------------------------|--------------|--------------------|
{% for emp in subrogacion.personal_subrogable %}
| {{ emp.puesto }} | {{ emp.antiguedad_anios }} años | {{ emp.tipo_contrato }} | {{ emp.jornada_anual_horas }} h | {{ emp.retribucion_bruta_anual }} | {{ emp.complementos }} | {{ emp.convenio_categoria }} |
{% endfor %}
{% else %}
*No se han facilitado datos individualizados de personal afectado por la subrogación. En el supuesto de que el órgano de contratación facilite información complementaria con posterioridad, se incorporará al presente anexo como adenda.*
{% endif %}

### 3.1 Aclaraciones sobre el listado

a) Los datos personales identificativos (nombre, apellidos, DNI) **no se reproducen** en el presente anexo público para evitar la divulgación innecesaria de información personal protegida por el RGPD. Se conservan en el expediente interno del Licitador y se aportarán al órgano de contratación cuando lo requiera para la formalización del contrato y para la efectividad de la subrogación.

b) Las cuantías retributivas se expresan en términos brutos anuales y referidas al último ejercicio cerrado en la información facilitada por {{ organo_info }}.

c) La antigüedad se computa desde la fecha de inicio efectiva de la prestación del servicio para la entidad cedente o sus predecesoras, conforme a las reglas de subrogación del convenio colectivo aplicable.

## 4. CONDICIONES DE LA SUBROGACIÓN

a) La subrogación se producirá con efectos del **día de inicio efectivo de la ejecución del contrato** por el Licitador adjudicatario.

b) Las condiciones laborales (retribución, jornada, antigüedad, categoría profesional, complementos) se **mantendrán inalteradas** en el momento de la subrogación, salvo que el convenio colectivo o un acuerdo individual posterior establezca lo contrario.

c) Las modificaciones posteriores de condiciones de trabajo requerirán, en su caso, seguir los procedimientos previstos en los artículos 39 a 41 del Estatuto de los Trabajadores.

d) Las obligaciones de Seguridad Social, retenciones fiscales, formación obligatoria y prevención de riesgos laborales se asumirán íntegramente por el Licitador adjudicatario desde el día de inicio efectivo de la ejecución del contrato.

## 5. VERIFICACIÓN DE LA INFORMACIÓN FACILITADA

El Licitador declara haber **verificado razonablemente** la información facilitada por {{ organo_info }}, sin perjuicio de la limitación de responsabilidad establecida en el artículo 130.6 LCSP por información incompleta o inexacta facilitada por la Administración o la empresa cedente.

En el supuesto de que, una vez producida la subrogación, se detectasen discrepancias materiales entre la información facilitada y la realidad efectiva del personal afectado, el Licitador procederá a:

a) Comunicar la discrepancia al órgano de contratación en el plazo máximo de **quince (15) días hábiles** desde su detección.

b) Documentar la discrepancia mediante acta interna con la representación legal de los trabajadores cuando proceda.

c) Adoptar las medidas necesarias para la regularización de la situación conforme a la normativa laboral y al convenio colectivo aplicable.

## 6. TRATAMIENTO DE DATOS PERSONALES

El tratamiento de los datos personales del personal afectado por la subrogación se realiza por el Licitador conforme al **Reglamento (UE) 2016/679 (RGPD)** y a la **Ley Orgánica 3/2018 de Protección de Datos Personales y garantía de los derechos digitales (LOPDGDD)**, con las siguientes precisiones:

| Concepto | Detalle |
|----------|---------|
| Responsable del tratamiento | {{ cliente.razon_social }} · NIF {{ cliente.nif }} |
| Base jurídica | Ejecución contractual (Art. 6.1.b) RGPD) + cumplimiento obligación legal (Art. 6.1.c) RGPD) en relación al Art. 130 LCSP |
| Finalidad | Gestión del proceso de subrogación y posterior gestión de la relación laboral |
| Categorías de datos | Datos identificativos · datos profesionales · datos económicos asociados a la retribución |
| Plazo de conservación | Durante la vigencia de la relación laboral + plazos legales aplicables tras su extinción |
| Cesiones | A organismos públicos competentes en cumplimiento de obligaciones legales (TGSS · AEAT · órgano de contratación) |

El Licitador adoptará las medidas técnicas y organizativas apropiadas, conforme al artículo 32 del RGPD, para garantizar la confidencialidad e integridad de los datos del personal subrogado.

## 7. DECLARACIÓN FINAL

El Licitador, mediante la firma conjunta del presente Anexo con el documento madre L-006:

a) Confirma el contenido del listado de personal afectado por la subrogación conforme a la información facilitada por {{ organo_info }}.

b) Asume el compromiso de subrogación en las condiciones detalladas en las secciones 4 a 6 del presente Anexo.

c) Se obliga a aportar la documentación complementaria que sea requerida por el órgano de contratación en fase previa a la formalización del contrato.

---

**Firmado en {{ cliente.poblacion if cliente.poblacion else '[POBLACIÓN]' }}, a {{ proyecto.fecha_aprobacion_inicial if proyecto.fecha_aprobacion_inicial else '[FECHA]' }}.**

**{{ representante_nombre }}**
{{ representante_cargo }}
{{ cliente.razon_social }}
NIF: {{ cliente.nif }}

---

**Documento L-007 — Versión {{ proyecto.version_actual if proyecto.version_actual else '1.0' }} — Clasificación: INTERNA · DATOS DE CARÁCTER PERSONAL**

*Documento generado por FULKRO · plataforma de gestión de cumplimiento normativo · {{ proyecto.fecha_aprobacion_inicial if proyecto.fecha_aprobacion_inicial else '—' }}*
