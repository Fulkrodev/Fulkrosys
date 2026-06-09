# DOCUMENTO E-213 — PROCEDIMIENTO DE NOTIFICACIÓN DE BRECHAS A LA AEPD

**Procedimiento técnico complementario a E-212. Detalla el contenido exacto del formulario AEPD y los pasos en la sede electrónica.**

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-213"
titulo: "Procedimiento de Notificación de Brechas a la AEPD"
version: "{{ proyecto.version_actual }}"
clasificacion: "INTERNA"
politica_madre: "{{ proyecto.codigo_documento_base }}-119"
---

# PROCEDIMIENTO DE NOTIFICACIÓN DE BRECHAS A LA AEPD DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-213 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Detallar el contenido, formato, canal y plazos de la notificación de brechas de datos personales a la Agencia Española de Protección de Datos, en cumplimiento del artículo 33 del RGPD.

## 2. CANAL

La notificación se realizará **exclusivamente** a través de la sede electrónica de la AEPD: https://sedeaepd.gob.es, usando el formulario específico de notificación de brechas.

Se requiere certificado digital (persona jurídica o representante) o Cl@ve para acceder a la sede.

## 3. CONTENIDO OBLIGATORIO (art. 33.3 RGPD)

El formulario exige:

a) **Naturaleza de la violación:** descripción del tipo de brecha (confidencialidad/integridad/disponibilidad), vectores de ataque si conocidos.

b) **Categorías de datos afectados:** identificativos, contacto, financieros, salud, categorías especiales, etc.

c) **Número aproximado de interesados afectados** y de registros de datos afectados.

d) **Datos del DPO** o punto de contacto: nombre, email, teléfono.

e) **Consecuencias probables** de la brecha para los interesados.

f) **Medidas adoptadas o propuestas** para poner remedio a la brecha y, en su caso, para mitigar sus efectos.

## 4. PLAZOS

| Situación | Plazo |
|---|---|
| Notificación completa | ≤ 72 horas desde el conocimiento |
| Notificación parcial (información incompleta) | ≤ 72 horas con indicación de los motivos del retraso |
| Complemento de la notificación parcial | Sin dilación, tan pronto como se disponga de la información |
| Notificación de seguimiento (si la AEPD lo requiere) | En el plazo que indique la AEPD |

## 5. RESPONSABLE

La interlocución con la AEPD corresponde al DPO ({{ responsables.delegado_proteccion_datos.nombre }}), con apoyo del Responsable de la Seguridad para la información técnica.

## 6. CONSERVACIÓN

El acuse de recibo de la notificación, el formulario enviado y toda la correspondencia con la AEPD se conservarán durante **6 años** en el Registro de Brechas.

---

**Documento {{ proyecto.codigo_documento_base }}-213 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---
