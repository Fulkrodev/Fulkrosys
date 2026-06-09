---
codigo_documento: "E-003"
titulo: "Acta de Constitución del Comité de Seguridad de la Información"
version: "{{ proyecto.version_actual if proyecto.version_actual else '1.0' }}"
clasificacion: "INTERNA"
norma_aplicable: "RD 311/2022 Anexo II · org.1 + CCN-STIC 801"
---

# ACTA DE CONSTITUCIÓN DEL COMITÉ DE SEGURIDAD DE LA INFORMACIÓN · {{ cliente.razon_social | upper }}

**Documento E-003 — Versión {{ proyecto.version_actual if proyecto.version_actual else '1.0' }}**

---

{% set fecha = comite_seguridad.fecha_constitucion if comite_seguridad and comite_seguridad.fecha_constitucion else proyecto.fecha_aprobacion_inicial %}
{% set pres = comite_seguridad.presidente if comite_seguridad and comite_seguridad.presidente else {'nombre': '[A DESIGNAR]', 'cargo': '[CARGO]'} %}
{% set sec = comite_seguridad.secretario if comite_seguridad and comite_seguridad.secretario else {'nombre': '[A DESIGNAR]', 'cargo': '[CARGO]'} %}
{% set tiene_miembros = comite_seguridad and comite_seguridad.miembros and comite_seguridad.miembros | length > 0 %}
{% set period = comite_seguridad.periodicidad_reuniones if comite_seguridad and comite_seguridad.periodicidad_reuniones else 'Trimestral · ordinarias' %}
{% set quorum = comite_seguridad.quorum_minimo if comite_seguridad and comite_seguridad.quorum_minimo else 'Mayoría absoluta de los miembros' %}

## 1. DATOS DEL ACTA

| Campo | Valor |
|-------|-------|
| Fecha de constitución | **{{ fecha }}** |
| Lugar | Sede social de **{{ cliente.razon_social }}** |
| Tipo | Acta fundacional de órgano colegiado |

## 2. ANTECEDENTES

Conforme a las medidas **org.1** (Política de seguridad) y **org.2** (Normativa de seguridad) del Anexo II del RD 311/2022, y siguiendo las directrices de la Guía CCN-STIC 801, la Entidad constituye formalmente el **Comité de Seguridad de la Información** (en adelante, "el Comité") como órgano colegiado responsable de la gobernanza estratégica del sistema sujeto al ENS, en su categoría **{{ proyecto.categoria_ens if proyecto.categoria_ens else 'MEDIA' }}**.

## 3. CONSTITUCIÓN FORMAL

Se constituye el Comité de Seguridad de la Información con la composición, competencias y régimen de funcionamiento detallados en las secciones siguientes.

## 4. COMPOSICIÓN

### 4.1 Presidencia y secretaría

| Rol | Nombre | Cargo orgánico |
|-----|--------|----------------|
| Presidente del Comité | **{{ pres.nombre }}** | {{ pres.cargo }} |
| Secretario del Comité | **{{ sec.nombre }}** | {{ sec.cargo }} |

### 4.2 Miembros del Comité

{% if tiene_miembros %}
| Nombre | Cargo orgánico |
|--------|----------------|
{% for m in comite_seguridad.miembros %}
| {{ m.nombre }} | {{ m.cargo }} |
{% endfor %}
{% else %}
*Pendiente de designación formal por el órgano de administración.*
{% endif %}

### 4.3 Invitados permanentes (sin voto)

El Comité podrá contar con la asistencia permanente, sin derecho a voto, del Responsable de Seguridad, del Responsable del Sistema de Información y del Delegado de Protección de Datos cuando éstos no formen parte como miembros titulares.

## 5. RÉGIMEN DE FUNCIONAMIENTO

| Aspecto | Detalle |
|---------|---------|
| Periodicidad de reuniones ordinarias | **{{ period }}** |
| Convocatoria de reuniones extraordinarias | Por iniciativa del Presidente o solicitud motivada de al menos un tercio de los miembros |
| Quórum mínimo | **{{ quorum }}** |
| Régimen de votación | Mayoría simple · voto de calidad del Presidente en caso de empate |
| Actas de reuniones | Redacción por el Secretario · distribución a miembros en plazo máximo de 7 días naturales · custodia en expediente SGSI |
| Convocatoria | Mínimo 7 días naturales antes de la reunión ordinaria · 48h antes de la extraordinaria |

## 6. COMPETENCIAS

Corresponden al Comité de Seguridad de la Información:

a) **Aprobación de políticas y normativas** de seguridad de la información (E-100 y subsiguientes).

b) **Validación del Plan de Adecuación** al ENS (E-050) y de sus revisiones.

c) **Aprobación del Análisis de Riesgos** (E-400) y de sus actualizaciones.

d) **Revisión periódica de incidentes de seguridad** y de las medidas correctivas adoptadas.

e) **Validación de cambios materiales** en el sistema (E-042) y propuesta al órgano de administración cuando proceda.

f) **Supervisión del cumplimiento** del Anexo II del ENS y de las auditorías internas y externas.

g) **Aprobación de la Declaración de Conformidad** (E-041) y de su mantenimiento periódico (E-043).

h) **Conocimiento del informe anual de actividad** del SGSI elevado por el Responsable de Seguridad.

i) **Validación de excepciones temporales** a las medidas de seguridad conforme al procedimiento E-222.

## 7. RÉGIMEN DE ACTAS

a) Cada reunión del Comité se documenta en acta firmada por Presidente y Secretario.

b) Las actas incluyen: convocatoria + asistencia + orden del día + deliberación resumida + acuerdos + votación + anexos.

c) Las actas se conservan en el expediente SGSI durante un plazo mínimo de **diez (10) años** desde su aprobación.

d) Las actas son confidenciales · su distribución se limita a miembros del Comité y a personas con interés legítimo acreditado.

## 8. PRIMERA REUNIÓN

La primera reunión ordinaria del Comité tendrá lugar en el plazo máximo de **treinta (30) días naturales** desde la presente constitución. En la primera reunión se procederá a la aprobación inicial de la Política de Seguridad (E-100), del Plan de Adecuación (E-050) y del Análisis de Riesgos (E-400) consolidando el marco operativo del SGSI.

## 9. VIGENCIA

El presente acta tiene vigencia indefinida hasta su revocación expresa por el órgano de administración. Las modificaciones de composición o régimen de funcionamiento se documentan mediante acta de modificación al presente documento.

---

**Firmado en {{ cliente.poblacion if cliente.poblacion else '[POBLACIÓN]' }}, a {{ fecha }}.**

| Cargo | Nombre | Firma |
|-------|--------|-------|
| Presidente del Comité | {{ pres.nombre }} | _______________ |
| Secretario del Comité | {{ sec.nombre }} | _______________ |
| Por el órgano de administración | {{ cliente.representante.nombre if cliente.representante else '[Representante legal]' }} | _______________ |

---

**Documento E-003 — Versión {{ proyecto.version_actual if proyecto.version_actual else '1.0' }} — Clasificación: INTERNA**

*Documento generado por FULKRO · {{ fecha }}*
