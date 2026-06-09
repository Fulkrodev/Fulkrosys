---
codigo_documento: "LW-002"
titulo: "Política de Cookies"
version: "{{ proyecto.version_actual if proyecto.version_actual else '1.0' }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial if proyecto.fecha_aprobacion_inicial else '—' }}"
clasificacion: "PÚBLICA"
norma_aplicable: "LSSI Art. 22.2 · RGPD · Guía AEPD Cookies 2023"
---

# POLÍTICA DE COOKIES DE {{ cliente.razon_social | upper }}

{% set dominio = cliente.dominio_web if cliente.dominio_web else 'www.[dominio].es' %}
{% set dpo_email = responsables.delegado_proteccion_datos.email if responsables.delegado_proteccion_datos and responsables.delegado_proteccion_datos.email else cliente.contacto_compliance.email if cliente.contacto_compliance and cliente.contacto_compliance.email else 'privacidad@' ~ (cliente.dominio_web if cliente.dominio_web else 'entidad.es') %}

## 1. INFORMACIÓN BÁSICA

| Concepto | Datos |
|----------|-------|
| Responsable | {{ cliente.razon_social }} ({{ cliente.nif }}) |
| Sitio web | {{ dominio }} |
| Contacto | {{ dpo_email }} |
| Norma aplicable | Art. 22.2 de la Ley 34/2002 (LSSI) y RGPD |

## 2. ¿QUÉ ES UNA COOKIE?

Una cookie es un pequeño fichero de datos que un sitio web instala en el navegador o dispositivo del usuario cuando este accede a determinadas páginas. Las cookies permiten almacenar y recuperar información sobre los hábitos de navegación de un usuario o de su equipo, recordar las preferencias de visita y, dependiendo de la información contenida y de la forma en que se utilice, identificar al usuario.

## 3. TIPOS DE COOKIES UTILIZADAS POR EL SITIO

Conforme a la **Guía sobre el uso de las cookies de la AEPD (versión vigente)**, las cookies utilizadas en {{ dominio }} se clasifican atendiendo a los siguientes criterios:

### 3.1 Según la entidad que las gestiona

- **Cookies propias:** instaladas por {{ cliente.razon_social }} desde un equipo o dominio gestionado por la propia Entidad.
- **Cookies de terceros:** instaladas por proveedores que prestan servicios a {{ cliente.razon_social }} (análisis web, integración de contenidos externos, etc.).

### 3.2 Según su finalidad

- **Cookies técnicas (estrictamente necesarias):** permiten al usuario navegar a través de la página web y utilizar funcionalidades esenciales (recordar idioma, sesión, carrito si aplica, panel de preferencias de cookies). No requieren consentimiento.
- **Cookies de preferencias o personalización:** permiten recordar opciones del usuario.
- **Cookies analíticas o de medición:** permiten cuantificar y analizar el uso de la página por parte de los usuarios.
- **Cookies de publicidad y publicidad comportamental:** permiten gestionar espacios publicitarios y mostrar publicidad personalizada.

### 3.3 Según el plazo de tiempo

- **De sesión:** se eliminan al cerrar el navegador.
- **Persistentes:** permanecen en el equipo del usuario durante un periodo definido.

## 4. RELACIÓN DETALLADA DE COOKIES UTILIZADAS

{% if cliente.cookies_detail %}
{% for c in cliente.cookies_detail %}
- **{{ c.nombre }}** — Tipo: {{ c.tipo }} · Propietario: {{ c.propietario }} · Finalidad: {{ c.finalidad }} · Duración: {{ c.duracion }}
{% endfor %}
{% else %}
A la fecha de actualización de la presente Política, se utilizan las siguientes cookies (la lista detallada se actualiza en el panel de gestión de cookies del sitio web):

- **Cookies técnicas propias** para el funcionamiento de la sesión y la propia gestión del consentimiento de cookies.
- **Cookies analíticas** (cuando el usuario las acepta) que recopilan información agregada sobre el uso del sitio.

La relación específica de cookies, su finalidad detallada, su titular y su duración se publica y actualiza en el panel de configuración accesible desde el banner de cookies del sitio web.
{% endif %}

## 5. CONSENTIMIENTO

### 5.1 Cookies estrictamente necesarias

Las cookies técnicas estrictamente necesarias para el funcionamiento del sitio web **no requieren consentimiento previo** del usuario, conforme al artículo 22.2 LSSI.

### 5.2 Resto de cookies

El resto de cookies (analíticas, preferencias no esenciales, publicidad) requieren **consentimiento previo, expreso, informado y específico** del usuario. Este consentimiento se recaba mediante el banner de cookies que aparece en la primera visita al sitio y queda registrado de forma trazable.

### 5.3 Revocación del consentimiento

El usuario puede en cualquier momento:

a) Modificar sus preferencias accediendo al **panel de configuración de cookies** desde el enlace permanente del pie del sitio web.

b) Eliminar las cookies previamente almacenadas mediante las opciones de su navegador.

## 6. CONFIGURACIÓN DESDE EL NAVEGADOR

El usuario puede permitir, bloquear o eliminar las cookies instaladas en su equipo desde la configuración del navegador que utilice. Enlaces de referencia:

- **Google Chrome:** https://support.google.com/chrome/answer/95647
- **Mozilla Firefox:** https://support.mozilla.org/es/kb/habilitar-y-deshabilitar-cookies-sitios-web
- **Safari:** https://support.apple.com/es-es/guide/safari/sfri11471/mac
- **Microsoft Edge:** https://support.microsoft.com/es-es/microsoft-edge

El bloqueo de cookies técnicas puede impedir el funcionamiento correcto del sitio.

## 7. TRANSFERENCIAS INTERNACIONALES ASOCIADAS A COOKIES DE TERCEROS

Cuando se utilizan cookies de terceros cuyos servidores se encuentran fuera del Espacio Económico Europeo, las garantías aplicables a la transferencia internacional se detallan en el panel de configuración de cookies y, cuando proceda, en la Política de Privacidad (documento LW-001).

## 8. CONSERVACIÓN DEL REGISTRO DE CONSENTIMIENTO

{{ cliente.razon_social }} conserva el registro del consentimiento del usuario durante un período mínimo de **dos (2) años** desde su otorgamiento o renovación, a efectos de poder acreditar el cumplimiento de la normativa aplicable.

## 9. MODIFICACIONES

{{ cliente.razon_social }} podrá modificar esta Política para adaptarla a cambios técnicos, normativos o de la propia configuración del sitio. Las modificaciones que impliquen cambios materiales en los tratamientos basados en consentimiento requerirán solicitar de nuevo el consentimiento al usuario.

**Última actualización:** {{ proyecto.fecha_aprobacion_inicial if proyecto.fecha_aprobacion_inicial else '—' }}

---

*Documento LW-002 · Política de Cookies · {{ cliente.razon_social }} · Versión {{ proyecto.version_actual if proyecto.version_actual else '1.0' }}*
