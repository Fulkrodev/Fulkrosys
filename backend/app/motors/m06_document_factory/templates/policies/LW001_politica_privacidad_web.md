---
codigo_documento: "LW-001"
titulo: "Política de Privacidad del Sitio Web"
version: "{{ proyecto.version_actual if proyecto.version_actual else '1.0' }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial if proyecto.fecha_aprobacion_inicial else '—' }}"
clasificacion: "PÚBLICA"
norma_aplicable: "RGPD + LOPDGDD + LSSI Ley 34/2002"
---

# POLÍTICA DE PRIVACIDAD DE {{ cliente.razon_social | upper }}

{% set dpo_email = responsables.delegado_proteccion_datos.email if responsables.delegado_proteccion_datos and responsables.delegado_proteccion_datos.email else cliente.contacto_compliance.email if cliente.contacto_compliance and cliente.contacto_compliance.email else 'privacidad@' ~ (cliente.dominio_web if cliente.dominio_web else 'entidad.es') %}
{% set dpo_nombre = responsables.delegado_proteccion_datos.nombre if responsables.delegado_proteccion_datos and responsables.delegado_proteccion_datos.nombre else '—' %}
{% set dominio = cliente.dominio_web if cliente.dominio_web else 'www.[dominio].es' %}

## 1. RESPONSABLE DEL TRATAMIENTO

| Concepto | Datos |
|----------|-------|
| Razón social | {{ cliente.razon_social }} |
| NIF | {{ cliente.nif }} |
| Domicilio social | {{ cliente.domicilio if cliente.domicilio else '—' }} |
| Sitio web | {{ dominio }} |
| Contacto para asuntos de privacidad | {{ dpo_email }} |
| Delegado de Protección de Datos | {{ dpo_nombre }} |

## 2. INFORMACIÓN OBJETO DE TRATAMIENTO

{{ cliente.razon_social }} trata datos personales recabados a través de los siguientes canales del sitio web {{ dominio }}:

a) **Formulario de contacto:** nombre, apellidos, email, teléfono y mensaje libre del usuario.

b) **Formularios de solicitud de información comercial:** datos identificativos + datos profesionales relacionados con la consulta.

c) **Alta en boletín informativo:** email + nombre (opcional).

d) **Procesos de selección:** datos curriculares aportados por el candidato.

e) **Datos de navegación:** dirección IP, tipo de navegador, páginas visitadas, fecha y hora, conforme a la Política de Cookies (documento LW-002).

## 3. FINALIDADES DEL TRATAMIENTO

| Finalidad | Base legítima (Art. 6 RGPD) | Conservación |
|-----------|----------------------------|--------------|
| Atender consultas y comunicaciones del formulario de contacto | Interés legítimo (Art. 6.1.f) RGPD | 1 año desde la última interacción |
| Tramitar solicitudes comerciales | Medidas precontractuales (Art. 6.1.b) RGPD | 3 años o vigencia relación comercial |
| Envío de boletín informativo | Consentimiento (Art. 6.1.a) RGPD | Hasta revocación del consentimiento |
| Procesos de selección | Consentimiento (Art. 6.1.a) RGPD | 1 año desde la candidatura · luego supresión o anonimización |
| Análisis de uso del sitio web | Consentimiento (cookies analíticas · LW-002) | Según configuración cookies |
| Cumplimiento de obligaciones legales | Obligación legal (Art. 6.1.c) RGPD | Plazos legales aplicables |

## 4. CESIONES Y ENCARGADOS DE TRATAMIENTO

### 4.1 Encargados de tratamiento

Para la prestación de determinados servicios, {{ cliente.razon_social }} cuenta con proveedores que actúan como encargados de tratamiento conforme al artículo 28 del RGPD, con quienes mantiene contratos que cumplen las exigencias normativas:

- Proveedor de alojamiento del sitio web.
- Proveedor de servicios de correo electrónico corporativo.
- Proveedor de la plataforma de boletines, en su caso.
- Proveedor de análisis web, en su caso.

### 4.2 Cesiones a terceros

{{ cliente.razon_social }} no cede datos personales a terceros, salvo obligación legal o autorización expresa del interesado.

## 5. TRANSFERENCIAS INTERNACIONALES

{% if cliente.tiene_transferencias_internacionales %}
Algunos encargados de tratamiento utilizan infraestructura ubicada fuera del Espacio Económico Europeo. En esos casos, {{ cliente.razon_social }} garantiza la protección de los datos mediante las garantías previstas en los artículos 44 a 49 del RGPD (decisión de adecuación, cláusulas contractuales tipo aprobadas por la Comisión Europea, o garantías equivalentes). La relación específica de proveedores y países destino puede solicitarse al contacto de privacidad indicado en el apartado 1.
{% else %}
{{ cliente.razon_social }} no realiza transferencias internacionales de datos personales fuera del Espacio Económico Europeo. Si en el futuro esta situación cambiara, se actualizará la presente Política con la información correspondiente.
{% endif %}

## 6. DERECHOS DEL INTERESADO

El interesado puede ejercer ante {{ cliente.razon_social }}, en cualquier momento y de forma gratuita, los siguientes derechos reconocidos por el RGPD y la LOPDGDD:

a) **Acceso** (Art. 15 RGPD): obtener confirmación de si se están tratando sus datos y, en su caso, acceder a ellos.

b) **Rectificación** (Art. 16 RGPD): solicitar la corrección de datos inexactos o incompletos.

c) **Supresión / derecho al olvido** (Art. 17 RGPD): solicitar la eliminación de los datos cuando ya no sean necesarios.

d) **Limitación del tratamiento** (Art. 18 RGPD).

e) **Portabilidad** (Art. 20 RGPD): recibir sus datos en formato estructurado, de uso común y lectura mecánica.

f) **Oposición** (Art. 21 RGPD), incluyendo oposición a decisiones individuales automatizadas.

g) **No ser objeto de decisiones individualizadas automatizadas** (Art. 22 RGPD).

h) **Revocar el consentimiento** previamente otorgado, sin que ello afecte a la licitud del tratamiento basado en el consentimiento previo a su retirada.

El ejercicio de estos derechos se realizará mediante solicitud escrita dirigida a **{{ dpo_email }}**, acompañando copia del documento identificativo del solicitante. La Entidad atenderá la solicitud en el plazo máximo de un (1) mes, prorrogable a dos (2) meses adicionales en casos de especial complejidad.

## 7. RECLAMACIÓN ANTE LA AUTORIDAD DE CONTROL

El interesado tiene derecho a presentar reclamación ante la **Agencia Española de Protección de Datos (AEPD)** cuando considere que el tratamiento no se ajusta a la normativa o cuando no haya obtenido satisfacción en el ejercicio de sus derechos:

- Sede electrónica: https://sedeaepd.gob.es
- Dirección postal: C/ Jorge Juan, 6, 28001 Madrid

## 8. SEGURIDAD DE LOS DATOS

{{ cliente.razon_social }} implanta medidas técnicas y organizativas apropiadas para garantizar un nivel de seguridad adecuado al riesgo, conforme al artículo 32 del RGPD. Estas medidas se desarrollan en el Sistema de Gestión de Seguridad de la Información (SGSI) de la Entidad y son objeto de revisión periódica.

## 9. COOKIES

El sitio web utiliza cookies propias y de terceros conforme se describe en la **Política de Cookies (documento LW-002)** que forma parte integrante de la presente Política de Privacidad.

## 10. MODIFICACIONES

{{ cliente.razon_social }} podrá modificar la presente Política para adaptarla a cambios normativos, técnicos o de funcionamiento. Las modificaciones se publicarán en {{ dominio }} con indicación de la fecha de actualización. Cuando los cambios afecten a tratamientos basados en consentimiento, se solicitará nuevo consentimiento al interesado.

**Última actualización:** {{ proyecto.fecha_aprobacion_inicial if proyecto.fecha_aprobacion_inicial else '—' }}

---

*Documento LW-001 · Política de Privacidad · {{ cliente.razon_social }} · Versión {{ proyecto.version_actual if proyecto.version_actual else '1.0' }}*
