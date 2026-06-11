# DOCUMENTO E-119 — POLÍTICA DE RESPUESTA A BRECHAS DE DATOS PERSONALES

**Política nueva. Materializa la obligación de los artículos 33 y 34 del RGPD y de la Guía de la AEPD para la notificación de brechas de datos personales. Complementa la Política de Gestión de Incidentes (E-108) en lo específico de datos personales.**

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-119"
titulo: "Política de Respuesta a Brechas de Datos Personales"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
clasificacion: "INTERNA"
propietario: "{{ responsables.responsable_seguridad.cargo }}"
aprobado_por: "{{ cliente.organo_aprobador_politicas }}"
---

# POLÍTICA DE RESPUESTA A BRECHAS DE DATOS PERSONALES DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-119 — Versión {{ proyecto.version_actual }}**

---

## MARCO NORMATIVO

Esta política se desarrolla en cumplimiento conjunto del **Real Decreto 311/2022**, de 3 de mayo, por el que se regula el Esquema Nacional de Seguridad (ENS), y del **Reglamento (UE) 2016/679 (RGPD)** y la **LO 3/2018 LOPDGDD**.

Del Anexo II del RD 311/2022 (ENS) materializa:

- **op.exp.7** — Gestión de incidentes (específicamente brechas con impacto en datos personales).
- **mp.info.2** — Calificación de la información (datos personales como categoría reforzada).
- **mp.si.2** — Criptografía (cifrado de la información como control compensatorio relevante para mitigar el impacto de una brecha).

Del marco de protección de datos materializa:

- **Artículo 33 RGPD** — Notificación a la autoridad de control (AEPD) en plazo máximo de 72 horas desde conocimiento de la brecha.
- **Artículo 34 RGPD** — Comunicación de la brecha al interesado cuando entrañe alto riesgo.
- **Artículo 5 LOPDGDD** — Deber de confidencialidad durante y después de la brecha.

Se alinea con la *Guía de la AEPD para la notificación de brechas de datos personales* (edición vigente) y con la *Guía CCN-STIC 817* sobre gestión de ciberincidentes del ENS. Complementa la Política Maestra ({{ proyecto.codigo_documento_base }}-100) y la Política de Gestión de Incidentes ({{ proyecto.codigo_documento_base }}-108) en lo específico de brechas que afecten a datos personales.

---

## 1. OBJETO

Establecer el marco de actuación de {{ cliente.razon_social }} ante las brechas de seguridad que afecten a datos personales, garantizando la detección, valoración, contención, notificación a las autoridades y comunicación a los interesados afectados en los plazos y con los contenidos exigidos por los artículos 33 y 34 del Reglamento (UE) 2016/679 (RGPD).

## 2. DEFINICIÓN

Se entiende por **brecha de seguridad de datos personales** toda violación de la seguridad que ocasione la destrucción, pérdida o alteración accidental o ilícita de datos personales transmitidos, conservados o tratados de otra forma, o la comunicación o acceso no autorizados a dichos datos (artículo 4.12 RGPD).

Las brechas se clasifican en tres tipos, que pueden concurrir simultáneamente:

a) **Brecha de confidencialidad**: acceso no autorizado o divulgación de datos personales.

b) **Brecha de integridad**: alteración no autorizada de datos personales.

c) **Brecha de disponibilidad**: pérdida de acceso o destrucción de datos personales.

## 3. DETECCIÓN Y VALORACIÓN INICIAL

### 3.1 Detección

Toda brecha de datos personales se detectará a través de los mecanismos previstos en la Política de Gestión de Incidentes ({{ proyecto.codigo_documento_base }}-108) y en el procedimiento de incidentes ({{ proyecto.codigo_documento_base }}-204).

### 3.2 Valoración del riesgo para los derechos y libertades

Tan pronto como se confirme que un incidente afecta a datos personales, el Responsable de la Seguridad, en coordinación con el DPO, realizará una **valoración del nivel de riesgo** para los derechos y libertades de las personas afectadas, considerando:

a) Naturaleza, sensibilidad y volumen de los datos afectados.

b) Facilidad de identificación de los interesados.

c) Gravedad de las consecuencias para los afectados.

d) Características especiales de los interesados (menores, personas vulnerables).

e) Número de personas afectadas.

f) Características especiales del responsable del tratamiento.

El resultado de la valoración determinará las obligaciones de notificación:

| Nivel de riesgo | Notificación a la AEPD | Comunicación a los interesados |
|---|---|---|
| **Sin riesgo** | No | No |
| **Riesgo bajo/medio** | Sí, en 72 horas | No (salvo que la AEPD lo requiera) |
| **Riesgo alto** | Sí, en 72 horas | Sí, sin dilación indebida |

## 4. NOTIFICACIÓN A LA AEPD

### 4.1 Plazo

Cuando la brecha entrañe riesgo para los derechos y libertades de las personas, la Entidad notificará a la Agencia Española de Protección de Datos en el plazo máximo de **72 horas** desde que tenga conocimiento de ella, conforme al artículo 33 del RGPD.

Si la notificación no es posible en 72 horas, se acompañará de los motivos del retraso.

### 4.2 Canal y contenido

La notificación se realizará a través del **formulario electrónico de la sede electrónica de la AEPD** (https://sedeaepd.gob.es) y contendrá, como mínimo:

a) Naturaleza de la brecha, categorías y número aproximado de interesados y registros afectados.

b) Datos de contacto del DPO o punto de contacto.

c) Consecuencias probables de la brecha.

d) Medidas adoptadas o propuestas para remediar la brecha y mitigar sus efectos.

### 4.3 Responsable de la notificación

La interlocución con la AEPD corresponde al DPO ({{ responsables.delegado_proteccion_datos.nombre }}), en coordinación con el Responsable de la Seguridad.

## 5. COMUNICACIÓN A LOS INTERESADOS

Cuando la brecha entrañe **riesgo alto** para los derechos y libertades de las personas físicas, se comunicará a los interesados afectados **sin dilación indebida**, conforme al artículo 34 del RGPD, utilizando un lenguaje claro y sencillo, e informando al menos de:

a) La naturaleza de la brecha.

b) Las recomendaciones dirigidas al interesado para mitigar los posibles efectos adversos (cambio de contraseñas, vigilancia de cuentas, etc.).

c) Los datos de contacto del DPO.

d) Las medidas adoptadas por la Entidad.

No será necesaria la comunicación individual cuando la Entidad haya adoptado medidas que hagan ininteligibles los datos para cualquier persona no autorizada (cifrado) o haya tomado medidas posteriores que garanticen que ya no es probable que se materialice el riesgo alto.

## 6. REGISTRO

Toda brecha, con independencia de su nivel de riesgo, quedará registrada en el **Registro de Brechas de Datos Personales**, mantenido por el DPO, que documentará: hechos, efectos, medidas correctivas adoptadas y decisiones de notificación/comunicación con su justificación.

## 7. APROBACIÓN, REVISIÓN Y VIGENCIA

Aprobada por {{ cliente.organo_aprobador_politicas }} el {{ proyecto.fecha_aprobacion_inicial }}. Revisión anual.

---

**Documento {{ proyecto.codigo_documento_base }}-119 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---
