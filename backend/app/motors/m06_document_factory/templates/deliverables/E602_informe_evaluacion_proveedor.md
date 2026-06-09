# E-602 · INFORME DE EVALUACIÓN DE PROVEEDOR

{% set codigo = documento.codigo if documento.codigo else 'E-602' %}
{% set version = documento.version if documento.version else '1.0' %}
{% set fecha_emision = documento.fecha_emision if documento.fecha_emision else '—' %}
{% set evaluador_nombre = assessment.evaluador.nombre if assessment.evaluador and assessment.evaluador.nombre else cliente.responsable_seguridad.nombre if cliente.responsable_seguridad else '—' %}
{% set evaluador_cargo = assessment.evaluador.cargo if assessment.evaluador and assessment.evaluador.cargo else 'Responsable de Seguridad' %}
{% set scoring_total_str = (assessment.scoring_total ~ ' / 100') if assessment.scoring_total is defined else 'No calculado' %}
{% set decision_label = assessment.decision if assessment.decision else 'PENDIENTE' %}
{% set nivel_asignado = assessment.nivel_criticidad_asignado if assessment.nivel_criticidad_asignado else 'POR DETERMINAR' %}
{% set valid_until = assessment.valid_until if assessment.valid_until else '—' %}
{% set fecha_cuestionario = assessment.fecha_cuestionario if assessment.fecha_cuestionario else '—' %}
{% set fecha_decision = assessment.fecha_decision if assessment.fecha_decision else fecha_emision %}

**Documento:** {{ codigo }}
**Versión:** {{ version }}
**Fecha de emisión:** {{ fecha_emision }}
**Entidad:** {{ cliente.razon_social }} ({{ cliente.nif }})
**Proveedor evaluado:** {{ proveedor.razon_social }}
**NIF/CIF proveedor:** {{ proveedor.nif }}
**Cuestionario base (E-601) fechado:** {{ fecha_cuestionario }}
**Clasificación:** Uso Interno

---

## 1. OBJETO DEL INFORME

El presente Informe de Evaluación documenta el resultado del análisis efectuado por {{ cliente.razon_social }} sobre la idoneidad de **{{ proveedor.razon_social }}** para prestar el servicio descrito, conforme al procedimiento **E-217 (Evaluación y Seguimiento de Proveedores)** y como parte del cumplimiento de las exigencias del **Real Decreto 311/2022 (ENS)**, en particular su artículo 18 y la medida `op.ext.1` del Anexo II.

Este informe cierra el ciclo de evaluación inicial iniciado con la entrega al proveedor del **Cuestionario E-601** y constituye la base documental para:

a) La inclusión o exclusión del proveedor en el **Inventario E-600**.

b) La determinación del nivel de criticidad asignado.

c) La definición de las condiciones contractuales que deberán formalizarse mediante la **Adenda ENS E-604**.

d) La elaboración del **Plan de Supervisión E-603** específico del proveedor.

## 2. ALCANCE Y METODOLOGÍA DE LA EVALUACIÓN

### 2.1 Documentación analizada

Para la elaboración del presente informe se ha revisado la siguiente documentación aportada por el proveedor:

- Cuestionario E-601 cumplimentado y firmado con fecha {{ fecha_cuestionario }}
- Anexos remitidos por el proveedor en el plazo formal de respuesta
- Documentación pública disponible sobre la entidad (registros mercantiles, ROAC cuando aplica, registro NIS2 si procede)
- Información de fuentes terceras consultadas (CERT-SI, listas de incidentes públicos, certificaciones registradas)

### 2.2 Marco de evaluación

La evaluación se ha articulado conforme a las siete dimensiones del cuestionario E-601:

a) **Conformidad ENS o esquema equivalente** (peso 25%)
b) **Cumplimiento RGPD cuando trata datos personales** (peso 20%)
c) **Cibersegridad NIS2 si aplica** (peso 10%)
d) **Cumplimiento DORA si aplica** (peso 10%)
e) **Capacidades técnicas y certificaciones** (peso 15%)
f) **Plan de continuidad y procedimiento de salida** (peso 10%)
g) **Capacidad de respuesta ante incidentes** (peso 10%)

## 3. DATOS DEL PROVEEDOR EVALUADO

| Concepto | Valor |
|----------|-------|
| Razón social | {{ proveedor.razon_social }} |
| NIF/CIF | {{ proveedor.nif }} |
| Domicilio social | {% if proveedor.domicilio %}{{ proveedor.domicilio }}{% else %}—{% endif %} |
| País sede | {% if proveedor.pais_sede %}{{ proveedor.pais_sede }}{% else %}España{% endif %} |
| Servicio objeto | {{ proveedor.servicio_descripcion }} |
| Categoría de servicio | {% if proveedor.categoria_servicio %}{{ proveedor.categoria_servicio }}{% else %}—{% endif %} |
| Volumen anual contratado (EUR) | {% if proveedor.volumen_eur %}{{ proveedor.volumen_eur }}{% else %}—{% endif %} |
| Tratamiento de datos personales | {% if proveedor.es_encargado_rgpd %}Sí (encargado de tratamiento){% else %}No{% endif %} |
| Subcontrataciones previstas | {% if proveedor.subcontrata %}Sí{% else %}No{% endif %} |

## 4. ANÁLISIS POR DIMENSIÓN

### 4.1 Dimensión B — Conformidad ENS o equivalente

**Hallazgos:**

{% if assessment.dimension_b and assessment.dimension_b.descripcion %}{{ assessment.dimension_b.descripcion }}{% else %}La revisión de la documentación aportada permite establecer el siguiente estado de cumplimiento ENS o equivalente para el servicio objeto.{% endif %}

{% if assessment.dimension_b and assessment.dimension_b.evidencias %}
**Evidencias aportadas:**

{% for ev in assessment.dimension_b.evidencias %}
- {{ ev }}
{% endfor %}
{% endif %}

**Conclusión dimensión:** {% if assessment.dimension_b and assessment.dimension_b.conclusion %}{{ assessment.dimension_b.conclusion }}{% else %}Pendiente de cierre tras subsanación{% endif %}

### 4.2 Dimensión C — Protección de datos personales (RGPD)

{% if proveedor.es_encargado_rgpd %}
**Hallazgos:**

{% if assessment.dimension_c and assessment.dimension_c.descripcion %}{{ assessment.dimension_c.descripcion }}{% else %}El proveedor actúa como encargado de tratamiento de datos personales por cuenta de la Entidad. Se han analizado las garantías documentadas por el proveedor en relación con el cumplimiento del Reglamento (UE) 2016/679 (RGPD) y la Ley Orgánica 3/2018 (LOPDGDD).{% endif %}

**Categorías de datos identificadas:** {% if assessment.dimension_c and assessment.dimension_c.categorias_datos %}{{ assessment.dimension_c.categorias_datos | join(', ') }}{% else %}Identificativos comunes{% endif %}

**Transferencias internacionales:** {% if assessment.dimension_c and assessment.dimension_c.transferencias %}{{ assessment.dimension_c.transferencias }}{% else %}No declaradas{% endif %}

**Conclusión dimensión:** {% if assessment.dimension_c and assessment.dimension_c.conclusion %}{{ assessment.dimension_c.conclusion }}{% else %}Requerirá contrato encargo de tratamiento ex Art. 28 RGPD anexado a la adenda E-604{% endif %}
{% else %}
*No aplica · el servicio no implica tratamiento de datos personales por cuenta de la Entidad.*
{% endif %}

### 4.3 Dimensión D — NIS2

{% if assessment.aplica_nis2 %}
{% if assessment.dimension_d and assessment.dimension_d.descripcion %}{{ assessment.dimension_d.descripcion }}{% else %}El proveedor declara estar en el ámbito de la Directiva (UE) 2022/2555 (NIS2). Se han revisado las prácticas de gestión de riesgos de ciberseguridad declaradas conforme al Art. 21.{% endif %}

**Conclusión:** {% if assessment.dimension_d and assessment.dimension_d.conclusion %}{{ assessment.dimension_d.conclusion }}{% else %}Cumplimiento NIS2 valorado favorablemente{% endif %}
{% else %}
*No aplica al servicio objeto.*
{% endif %}

### 4.4 Dimensión E — DORA

{% if assessment.aplica_dora %}
{% if assessment.dimension_e and assessment.dimension_e.descripcion %}{{ assessment.dimension_e.descripcion }}{% else %}El servicio se enmarca como servicio TIC bajo el Reglamento (UE) 2022/2554 (DORA). Se han revisado los compromisos contractuales mínimos del Art. 30 y los planes de continuidad asociados.{% endif %}

**Conclusión:** {% if assessment.dimension_e and assessment.dimension_e.conclusion %}{{ assessment.dimension_e.conclusion }}{% else %}Cumplimiento DORA condicionado a la firma de adenda con cláusulas Art. 30{% endif %}
{% else %}
*No aplica · la Entidad no es entidad financiera UE o el servicio no es TIC crítico bajo DORA.*
{% endif %}

### 4.5 Dimensión F — Capacidades técnicas y certificaciones

**Certificaciones acreditadas vigentes:**

{% if assessment.certificaciones_vigentes %}
{% for cert in assessment.certificaciones_vigentes %}
- {{ cert }}
{% endfor %}
{% else %}
*No se han acreditado certificaciones vigentes en la documentación aportada.*
{% endif %}

**Conclusión dimensión:** {% if assessment.dimension_f and assessment.dimension_f.conclusion %}{{ assessment.dimension_f.conclusion }}{% else %}Capacidades técnicas valoradas conforme al servicio prestado{% endif %}

### 4.6 Dimensión G — Continuidad y procedimiento de salida

**RTO comprometido:** {% if assessment.rto_horas %}{{ assessment.rto_horas }} horas{% else %}No declarado{% endif %}
**RPO comprometido:** {% if assessment.rpo_horas %}{{ assessment.rpo_horas }} horas{% else %}No declarado{% endif %}
**Plan de continuidad aportado:** {% if assessment.bcp_aportado %}Sí{% else %}No{% endif %}
**Aceptación procedimiento salida 30 días:** {% if assessment.acepta_salida_30d %}Sí{% else %}No · requiere negociación{% endif %}

### 4.7 Capacidad de respuesta ante incidentes

**Tiempo máximo de notificación a la Entidad comprometido:** {% if assessment.notificacion_horas %}{{ assessment.notificacion_horas }} horas{% else %}No declarado{% endif %}
**Colaboración INES + CCN-CERT aceptada:** {% if assessment.colabora_ines %}Sí{% else %}No · requiere negociación{% endif %}

## 5. HALLAZGOS MATERIALES

### 5.1 Hallazgos positivos

{% if assessment.hallazgos_positivos %}
{% for h in assessment.hallazgos_positivos %}
- {{ h }}
{% endfor %}
{% else %}
*No se han identificado hallazgos positivos materiales en la evaluación.*
{% endif %}

### 5.2 Hallazgos críticos o que requieren subsanación

{% if assessment.hallazgos_criticos %}
{% for h in assessment.hallazgos_criticos %}
- **{{ h.titulo }}** — {{ h.descripcion }} *(Severidad: {{ h.severidad }})*
{% endfor %}
{% else %}
*No se han identificado hallazgos críticos que impidan la aprobación del proveedor.*
{% endif %}

## 6. SCORING Y NIVEL DE CRITICIDAD ASIGNADO

### 6.1 Puntuación por dimensión

{% if assessment.scoring_por_seccion %}
| Dimensión | Puntuación (0-100) |
|-----------|-------------------:|
{% for d, score in assessment.scoring_por_seccion.items() %}
| {{ d }} | {{ score }} |
{% endfor %}
{% else %}
*Scoring detallado no disponible en el contexto del informe.*
{% endif %}

### 6.2 Puntuación total

**Puntuación global ponderada:** {{ scoring_total_str }}

### 6.3 Nivel de criticidad asignado al proveedor

**Nivel asignado en el Inventario E-600:** {{ nivel_asignado }}

Justificación: {% if assessment.nivel_criticidad_justificacion %}{{ assessment.nivel_criticidad_justificacion }}{% else %}Conforme a la metodología documentada en E-217 y el resultado del scoring.{% endif %}

## 7. DECISIÓN DE LA ENTIDAD

**Decisión:** {{ decision_label }}

{% if decision_label == 'APROBADO' %}
La Entidad **APRUEBA** la contratación del proveedor para el servicio objeto, sin condiciones suspensivas adicionales más allá de la formalización de la adenda contractual E-604 y el inicio de las revisiones programadas conforme al Plan de Supervisión E-603.
{% elif decision_label == 'CONDICIONAL' %}
La Entidad **APRUEBA CONDICIONALMENTE** la contratación, supeditada al cumplimiento previo o concurrente de las siguientes condiciones:

{% if assessment.condiciones %}
{% for c in assessment.condiciones %}
- {{ c.descripcion }} *(Plazo máximo: {{ c.plazo }})*
{% endfor %}
{% else %}
- (Las condiciones específicas se relacionan en documento anexo.)
{% endif %}

Hasta el cierre de todas las condiciones, el proveedor permanecerá en estado *PENDIENTE-CONDICIONAL* en el Inventario E-600 y la Entidad mantendrá supervisión reforzada.
{% elif decision_label == 'PENDIENTE' %}
La Entidad considera **PENDIENTE** la decisión final hasta la aportación por parte del proveedor de información adicional o evidencias documentales relacionadas con los hallazgos críticos identificados en la sección 5.2.

El proveedor no quedará incluido en el Inventario E-600 ni se procederá a la firma de adenda hasta el cierre satisfactorio de los hallazgos.
{% elif decision_label == 'RECHAZADO' %}
La Entidad **RECHAZA** la contratación del proveedor en los términos planteados, sobre la base de los hallazgos críticos identificados en la sección 5.2 y los riesgos de incumplimiento normativo derivados.

El proveedor será notificado de la decisión y se preservará el presente informe a efectos de trazabilidad documental sin proceder a la inclusión en el Inventario E-600.
{% endif %}

**Vigencia de la decisión:** {{ valid_until }} (sin perjuicio de revisiones extraordinarias por cambios materiales).

## 8. PRÓXIMOS PASOS

{% if decision_label == 'APROBADO' or decision_label == 'CONDICIONAL' %}
a) Formalización de la **Adenda ENS E-604** con las cláusulas obligatorias resultantes de las normativas aplicables y, en su caso, las condiciones derivadas de esta evaluación.

b) Inclusión del proveedor en el **Inventario E-600** con el nivel de criticidad **{{ nivel_asignado }}**.

c) Emisión del **Plan de Supervisión E-603** específico, con la frecuencia de revisiones correspondiente al nivel asignado.

d) Comunicación de los puntos de contacto operativos a ambas partes.
{% else %}
a) Notificación formal al proveedor del resultado de la evaluación, indicando los hallazgos a subsanar o la firmeza de la decisión.

b) Archivo del presente informe junto con el cuestionario E-601 y anexos en el repositorio de proveedores del sistema FULKRO.

c) Reevaluación cuando proceda, conforme al procedimiento E-217.
{% endif %}

## 9. FIRMA DEL INFORME

| Rol | Nombre | Cargo | Fecha | Firma |
|-----|--------|-------|-------|-------|
| Evaluador | {{ evaluador_nombre }} | {{ evaluador_cargo }} | {{ fecha_decision }} | |
| Revisor | {% if cliente.responsable_sistemas %}{{ cliente.responsable_sistemas.nombre }}{% else %}—{% endif %} | {% if cliente.responsable_sistemas %}{{ cliente.responsable_sistemas.cargo }}{% else %}Responsable de Sistemas{% endif %} | | |
| Aprobador final | {% if cliente.direccion %}{{ cliente.direccion.nombre }}{% else %}—{% endif %} | {% if cliente.direccion %}{{ cliente.direccion.cargo }}{% else %}Dirección{% endif %} | | |

---

*Documento generado por FULKRO · plataforma de gestión ENS · {{ fecha_emision }}*
*Trazabilidad: este informe se vincula al registro `provider_assessment_id={{ assessment.id if assessment.id else '—' }}` del sistema FULKRO y al proveedor `provider_id={{ proveedor.id if proveedor.id else '—' }}`.*
