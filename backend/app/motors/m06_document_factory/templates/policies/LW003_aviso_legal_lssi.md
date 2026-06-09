---
codigo_documento: "LW-003"
titulo: "Aviso Legal del Sitio Web (LSSI Art. 10)"
version: "{{ proyecto.version_actual if proyecto.version_actual else '1.0' }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial if proyecto.fecha_aprobacion_inicial else '—' }}"
clasificacion: "PÚBLICA"
norma_aplicable: "Ley 34/2002 LSSI · Art. 10"
---

# AVISO LEGAL DE {{ cliente.razon_social | upper }}

{% set dominio = cliente.dominio_web if cliente.dominio_web else 'www.[dominio].es' %}
{% set contacto_email = cliente.contacto_general.email if cliente.contacto_general and cliente.contacto_general.email else 'info@' ~ (cliente.dominio_web if cliente.dominio_web else 'entidad.es') %}

## 1. IDENTIFICACIÓN DEL PRESTADOR DE SERVICIOS

En cumplimiento del artículo 10 de la Ley 34/2002, de 11 de julio, de Servicios de la Sociedad de la Información y de Comercio Electrónico (LSSI-CE), se ofrecen los datos identificativos del titular del sitio web {{ dominio }}:

| Concepto | Datos |
|----------|-------|
| Razón social | {{ cliente.razon_social }} |
| NIF | {{ cliente.nif }} |
| Domicilio social | {{ cliente.domicilio if cliente.domicilio else '—' }} |
| Datos registrales | {{ cliente.datos_registrales if cliente.datos_registrales else '[a indicar · Registro Mercantil correspondiente · tomo · folio · hoja]' }} |
| Correo electrónico de contacto | {{ contacto_email }} |
| Teléfono | {{ cliente.telefono if cliente.telefono else '—' }} |

## 2. OBJETO Y ÁMBITO

El presente Aviso Legal regula el acceso y la utilización del sitio web {{ dominio }} (en adelante, "el Sitio"), titularidad de {{ cliente.razon_social }} (en adelante, "la Entidad").

La utilización del Sitio atribuye al visitante la condición de **usuario** e implica la aceptación plena de las disposiciones incluidas en el presente Aviso Legal, así como en la Política de Privacidad (LW-001) y en la Política de Cookies (LW-002) vigentes en cada momento.

## 3. SERVICIOS OFRECIDOS

El Sitio tiene por finalidad principal {{ cliente.proposito_sitio_web if cliente.proposito_sitio_web else 'proporcionar información institucional sobre la Entidad y los servicios profesionales que presta, así como habilitar canales de contacto con sus áreas comerciales y operativas' }}.

## 4. CONDICIONES DE USO

### 4.1 Uso correcto del Sitio

El usuario se compromete a utilizar el Sitio conforme a la ley, al presente Aviso Legal, a la moral y a las buenas costumbres generalmente aceptadas y al orden público, absteniéndose en particular de:

a) Utilizar el Sitio con fines o efectos ilícitos, contrarios a lo establecido en el presente Aviso Legal, lesivos de los derechos e intereses de terceros, o que de cualquier forma puedan dañar, inutilizar, sobrecargar o deteriorar el Sitio.

b) Introducir o difundir virus informáticos o cualesquiera otros sistemas físicos o lógicos que sean susceptibles de provocar daños en los sistemas del prestador, de sus proveedores o de terceros usuarios.

c) Intentar acceder, sin autorización, a áreas restringidas del Sitio.

### 4.2 Veracidad de la información aportada

El usuario garantiza la veracidad, exactitud y vigencia de los datos personales que aporte a través del Sitio, asumiendo la correspondiente responsabilidad por los daños que pudieran derivarse de la inexactitud de los mismos.

## 5. PROPIEDAD INTELECTUAL E INDUSTRIAL

### 5.1 Titularidad

Todos los contenidos del Sitio (textos, fotografías, gráficos, imágenes, iconos, marcas, nombres comerciales, logotipos, software, código fuente y, en general, cualesquiera otros elementos contenidos en el mismo) son propiedad de la Entidad o, en su caso, de terceros que han autorizado expresamente su utilización.

### 5.2 Derechos reservados

Quedan expresamente prohibidas la reproducción, distribución, transformación, comunicación pública o cualquier otro acto de explotación, total o parcial, de los contenidos del Sitio sin autorización previa y por escrito de la Entidad, salvo cuando se trate de actos permitidos por la legislación aplicable o expresamente autorizados desde el propio Sitio.

### 5.3 Enlaces

La existencia de enlaces a sitios externos no implica recomendación, promoción, identificación, conformidad o conexión alguna entre la Entidad y los responsables de dichos sitios, que asumen su propia responsabilidad sobre el contenido y políticas de uso aplicables.

## 6. EXCLUSIÓN Y LIMITACIÓN DE RESPONSABILIDAD

La Entidad se reserva el derecho a interrumpir el acceso al Sitio, así como la prestación de cualquiera de los servicios que a través del mismo se prestan, en cualquier momento y sin previo aviso, ya sea por motivos técnicos, de seguridad, de mantenimiento, por fallo del suministro eléctrico, o por cualquier otra causa.

En consecuencia, la Entidad **no garantiza la fiabilidad, disponibilidad ni continuidad** del Sitio ni de los servicios prestados a través del mismo, por lo que la utilización de estos por parte de los usuarios se lleva a cabo por su propia cuenta y riesgo, sin que en ningún momento puedan exigirse responsabilidades a la Entidad en este sentido, en los términos del artículo 16 LSSI.

## 7. PROTECCIÓN DE DATOS

El tratamiento de los datos personales recogidos a través del Sitio se rige por la **Política de Privacidad (documento LW-001)** publicada en este mismo Sitio, que forma parte integrante del presente Aviso Legal.

## 8. COOKIES

El uso de cookies en el Sitio se rige por la **Política de Cookies (documento LW-002)** publicada en este mismo Sitio.

## 9. MODIFICACIONES

La Entidad se reserva el derecho a modificar, sin previo aviso, el presente Aviso Legal. Las modificaciones surtirán efecto desde su publicación en el Sitio. La utilización del Sitio con posterioridad a la publicación implicará la aceptación tácita de las modificaciones por parte del usuario.

## 10. LEY APLICABLE Y JURISDICCIÓN

El presente Aviso Legal se rige por la legislación española. Para la resolución de cualquier controversia que pudiera derivarse de la utilización del Sitio o de la interpretación del presente Aviso Legal, las partes se someten a los Juzgados y Tribunales que correspondan al domicilio del consumidor cuando el usuario sea un consumidor en el sentido de la legislación aplicable; en otro caso, a los Juzgados y Tribunales que correspondan al domicilio de la Entidad.

---

**Última actualización:** {{ proyecto.fecha_aprobacion_inicial if proyecto.fecha_aprobacion_inicial else '—' }}

*Documento LW-003 · Aviso Legal LSSI · {{ cliente.razon_social }} · Versión {{ proyecto.version_actual if proyecto.version_actual else '1.0' }}*
