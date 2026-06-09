# DOCUMENTO E-115 — POLÍTICA DE GESTIÓN DE VULNERABILIDADES

**Política madre del procedimiento E-205. Materializa op.exp.4 del Anexo II. Obligatoria desde categoría MEDIA.**

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-115"
titulo: "Política de Gestión de Vulnerabilidades"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
clasificacion: "INTERNA"
aprobado_por: "{{ cliente.organo_aprobador_politicas }}"
---

# POLÍTICA DE GESTIÓN DE VULNERABILIDADES DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-115 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Establecer los principios y compromisos de {{ cliente.razon_social }} en materia de identificación, valoración, priorización y tratamiento de las vulnerabilidades técnicas que afecten a sus sistemas de información, en cumplimiento de la medida **op.exp.4 (Mantenimiento y actualizaciones de seguridad)** del Anexo II del Real Decreto 311/2022.

## 2. PRINCIPIOS

**2.1 Visibilidad completa.** La Entidad mantendrá una cobertura de escaneo de vulnerabilidades ≥95% de los activos inventariados del alcance del SGSI.

**2.2 Priorización basada en riesgo.** Las vulnerabilidades se priorizarán combinando la puntuación CVSS con factores contextuales (criticidad del activo, exposición a Internet, existencia de exploit público, inclusión en el catálogo CISA KEV).

**2.3 Plazos de corrección proporcionales.** Los plazos máximos de corrección se establecen por criticidad:

| Criticidad efectiva | Plazo máximo de corrección |
|---|---|
| CRÍTICA con explotación activa | 24 horas |
| CRÍTICA | 7 días |
| ALTA | 15 días |
| MEDIA | 60 días |
| BAJA | 180 días |

**2.4 Excepción documentada.** Cuando no sea posible corregir una vulnerabilidad en plazo, se gestionará como excepción conforme al apartado 9 de la Política de Seguridad ({{ proyecto.codigo_documento_base }}-100), documentando el riesgo asumido y las mitigaciones compensatorias.

## 3. FUENTES DE INTELIGENCIA

El Responsable de la Seguridad monitorizará al menos: CCN-CERT, INCIBE-CERT, NVD (NIST), CISA KEV, boletines de los fabricantes del software utilizado.

## 4. PROCEDIMIENTO OPERATIVO

El detalle operativo se desarrolla en el procedimiento {{ proyecto.codigo_documento_base }}-205 (Gestión de Vulnerabilidades) y {{ proyecto.codigo_documento_base }}-206 (Aplicación de Parches).

## 5. APROBACIÓN Y VIGENCIA

Aprobada por {{ cliente.organo_aprobador_politicas }} el {{ proyecto.fecha_aprobacion_inicial }}. Revisión anual.

---

**Documento {{ proyecto.codigo_documento_base }}-115 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---
