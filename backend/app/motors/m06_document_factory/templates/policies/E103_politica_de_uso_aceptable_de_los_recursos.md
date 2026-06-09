# DOCUMENTO E-103 — POLÍTICA DE USO ACEPTABLE DE LOS RECURSOS

**Es la política con mayor impacto operativo en el día a día del personal.** Materializa las medidas mp.eq.1 a mp.eq.4 (Protección de los equipos), mp.s.1 (Protección de los servicios) y org.4 (Proceso de autorización) del Anexo II del ENS, así como los controles A.5.10 (Uso aceptable de los activos), A.6.7 (Trabajo a distancia) y A.8.1 (Dispositivos de usuario final) de ISO/IEC 27001:2022. Es la política que **todo el personal debe firmar como parte de su contrato laboral o de su acuerdo de incorporación**.

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-103"
titulo: "Política de Uso Aceptable de los Recursos"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
fecha_proxima_revision: "{{ proyecto.proxima_revision }}"
clasificacion: "INTERNA"
propietario: "{{ responsables.responsable_seguridad.cargo }}"
aprobado_por: "{{ cliente.organo_aprobador_politicas }}"
---

# POLÍTICA DE USO ACEPTABLE DE LOS RECURSOS DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-103 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

El presente documento establece las normas de uso aceptable de los recursos tecnológicos, de información y de comunicación puestos a disposición del personal de {{ cliente.razon_social }} y de cualesquiera terceros con acceso a dichos recursos, con la finalidad de garantizar su utilización adecuada, proporcionada, lícita y conforme con los intereses legítimos de la Entidad.

Esta Política configura, junto con las demás normas internas, el marco de derechos y deberes del personal en relación con los recursos puestos a su disposición y constituye una norma de obligado cumplimiento.

## 2. ÁMBITO DE APLICACIÓN

### 2.1 Ámbito subjetivo

La presente Política es de obligado cumplimiento para:

a) Todo el personal de la Entidad, con independencia de su régimen jurídico de relación, categoría profesional, antigüedad o modalidad de contratación.

b) El personal externo, contratistas, subcontratistas, becarios, personal en prácticas y consultores con acceso a los recursos de la Entidad.

c) Cualquier tercero al que la Entidad facilite, de forma puntual o continuada, el acceso a sus recursos tecnológicos.

### 2.2 Ámbito objetivo

Constituyen "recursos" a los efectos del presente documento, con carácter no limitativo:

a) Equipos informáticos de cualquier tipo (ordenadores de sobremesa, portátiles, dispositivos móviles, tabletas).

b) Software corporativo, ya sea licenciado, propio o de terceros.

c) Acceso a redes corporativas e Internet a través de la infraestructura de la Entidad.

d) Cuentas de correo electrónico corporativas.

e) Almacenamiento corporativo, ya sea local o cloud.

f) Sistemas de telefonía, videoconferencia y mensajería corporativa.

g) Cuentas en plataformas externas creadas en nombre de la Entidad o para el desempeño de funciones profesionales.

h) Documentación e información en cualquier formato perteneciente a la Entidad.

i) Cualquier otro recurso identificado en el inventario de activos.

## 3. DERECHOS DEL PERSONAL USUARIO

El personal usuario tiene derecho a:

a) Disponer de los recursos necesarios para el correcto desempeño de las funciones que tenga encomendadas.

b) Recibir la formación adecuada sobre el uso de los recursos puestos a su disposición y sobre las obligaciones derivadas de la presente Política.

c) Conocer las medidas de monitorización a las que estén sujetos los recursos que utiliza, conforme al apartado 9 del presente documento, en cumplimiento del artículo 87 de la LOPDGDD.

d) Ser informado de las consecuencias del incumplimiento de la presente Política.

e) Recibir asistencia técnica del Responsable del Sistema cuando experimente dificultades en el uso de los recursos.

## 4. NORMAS GENERALES DE USO

### 4.1 Finalidad profesional

Los recursos puestos a disposición del personal serán utilizados, con carácter general, **exclusivamente para fines profesionales** vinculados a las funciones que cada persona tenga encomendadas en el seno de la Entidad.

Se admite un uso personal **moderado, ocasional y razonable** de los recursos, siempre que:

a) No interfiera con el desempeño normal de las funciones profesionales.

b) No suponga un coste significativo para la Entidad.

c) No comprometa la seguridad de los sistemas, la información o las comunicaciones.

d) No vulnere la legislación vigente ni las normas internas de la Entidad.

e) No afecte negativamente a la imagen o reputación de la Entidad.

### 4.2 Diligencia y custodia

El personal usuario actuará con la diligencia debida en la custodia y uso de los recursos, debiendo:

a) Mantener los equipos y soportes en condiciones adecuadas de conservación.

b) Bloquear la sesión cuando se ausente del puesto de trabajo, aunque sea por un breve periodo.

c) Adoptar las medidas razonables para evitar la sustracción, pérdida, daño o acceso no autorizado por terceros.

d) Notificar de inmediato cualquier incidencia, anomalía o sospecha de incidente al Responsable del Sistema o al Responsable de la Seguridad.

### 4.3 Confidencialidad

El personal usuario deberá mantener la confidencialidad de toda la información a la que acceda en el ejercicio de sus funciones, debiendo:

a) No divulgar, copiar, reproducir o difundir información confidencial de la Entidad fuera del ámbito de sus funciones.

b) No utilizar información confidencial para finalidades distintas de aquellas para las que ha sido legítimamente obtenida.

c) Adoptar las precauciones razonables para evitar que terceros no autorizados accedan a la información, especialmente en espacios públicos, durante el trabajo a distancia o en desplazamientos.

d) Mantener la obligación de confidencialidad incluso después de la extinción de la relación con la Entidad, conforme a los compromisos suscritos.

## 5. USOS PROHIBIDOS

Sin perjuicio de cualesquiera otras prohibiciones derivadas de la legislación aplicable o de las normas internas de la Entidad, queda **expresamente prohibido**:

### 5.1 En relación con la integridad y disponibilidad de los sistemas

a) Realizar acciones, intencionales o por negligencia grave, que puedan comprometer la disponibilidad, integridad, confidencialidad, autenticidad o trazabilidad de los sistemas o de la información.

b) Instalar software no autorizado, incluidos programas, aplicaciones, extensiones de navegador, complementos, juegos y servicios cloud no aprobados.

c) Modificar la configuración de seguridad de los equipos sin autorización expresa del Responsable del Sistema.

d) Conectar dispositivos personales a la red corporativa fuera de los supuestos autorizados por la Política de uso de dispositivos personales (BYOD).

e) Eludir o intentar eludir los mecanismos de seguridad implantados por la Entidad, incluyendo sistemas antimalware, filtros de contenido, controles de acceso, herramientas de monitorización y cualquier otro control de seguridad.

f) Utilizar herramientas de hacking, escaneo de vulnerabilidades, sniffing de red u otras herramientas ofensivas, salvo cuando ello forme parte explícita de las funciones laborales y exista autorización expresa.

### 5.2 En relación con el contenido

a) Almacenar, distribuir, descargar, reproducir o difundir contenidos ilegales, ofensivos, discriminatorios, sexistas, racistas, xenófobos, violentos, pornográficos, de apología del terrorismo o de cualquier otra naturaleza contraria a la dignidad de las personas o a la legislación vigente.

b) Vulnerar derechos de propiedad intelectual o industrial mediante la descarga, reproducción, distribución o uso no autorizado de obras protegidas.

c) Suplantar la identidad de otras personas, físicas o jurídicas, mediante el uso de cuentas, firmas electrónicas o cualquier otro mecanismo de identificación.

d) Difundir información falsa, calumniosa o injuriosa sobre la Entidad, su personal, sus partes interesadas o terceros.

e) Utilizar los recursos de la Entidad para actividades comerciales, lucrativas o políticas ajenas a las funciones profesionales.

### 5.3 En relación con datos personales

a) Tratar datos personales para finalidades distintas de las legítimas y previstas en el ejercicio de las funciones profesionales.

b) Comunicar datos personales a terceros sin autorización del Responsable del Tratamiento o sin la base de legitimación correspondiente conforme al RGPD.

c) Almacenar datos personales en dispositivos o servicios no autorizados por la Entidad.

d) Realizar copias o extracciones masivas de datos personales sin autorización expresa.

### 5.4 En relación con la seguridad de las credenciales

a) Comunicar las credenciales de autenticación personales a otra persona, sea o no del personal de la Entidad.

b) Utilizar las credenciales de otro usuario, incluso con su consentimiento.

c) Anotar las credenciales en soportes accesibles a terceros.

d) Reutilizar las credenciales corporativas en sistemas o servicios externos a la Entidad.

## 6. USO DEL CORREO ELECTRÓNICO CORPORATIVO

### 6.1 Naturaleza del correo corporativo

Las cuentas de correo electrónico corporativas son un instrumento de trabajo titularidad de la Entidad y, en consecuencia, **no constituyen un canal de comunicación personal**, sin perjuicio del uso personal moderado autorizado conforme al apartado 4.1.

### 6.2 Reglas específicas

Al utilizar el correo electrónico corporativo, el personal usuario deberá:

a) Utilizar exclusivamente la cuenta corporativa para comunicaciones profesionales en nombre de la Entidad.

b) Verificar la identidad del destinatario antes de enviar información sensible.

c) Cifrar los mensajes que contengan información confidencial cuando la herramienta lo permita.

d) No abrir adjuntos o enlaces sospechosos de remitentes desconocidos o inesperados.

e) Notificar de inmediato al Responsable de la Seguridad cualquier mensaje sospechoso de constituir un intento de phishing, spear-phishing, suplantación o cualquier otro fraude.

f) No participar en cadenas de correos masivos, *spam* o difusión de bulos.

g) Adoptar precauciones especiales al utilizar las funciones de respuesta automática durante ausencias.

## 7. NAVEGACIÓN POR INTERNET

### 7.1 Uso responsable

El acceso a Internet desde los recursos de la Entidad está sujeto a las normas generales del presente documento y, en particular, a la prohibición de acceder a contenidos ilícitos o inapropiados.

### 7.2 Filtrado de contenidos

La Entidad puede disponer de mecanismos técnicos de filtrado de contenidos web que bloqueen el acceso a sitios considerados peligrosos, ilícitos o ajenos a las finalidades profesionales. Estos mecanismos no requieren autorización individual del personal y forman parte de las medidas de seguridad ordinarias.

### 7.3 Descargas

Las descargas de software desde Internet quedan limitadas a las realizadas desde fuentes oficiales y, en cualquier caso, requieren la autorización previa del Responsable del Sistema cuando el software vaya a instalarse en equipos corporativos.

## 8. TRABAJO A DISTANCIA Y MOVILIDAD

### 8.1 Autorización

El trabajo a distancia se realizará exclusivamente en los términos y condiciones autorizados por la Entidad y conforme a la normativa laboral aplicable.

### 8.2 Medidas específicas

Cuando el personal usuario trabaje fuera de las instalaciones controladas por la Entidad, deberá:

a) Conectarse a los sistemas corporativos exclusivamente a través de los canales seguros autorizados (VPN corporativa o equivalente).

b) Adoptar precauciones razonables para que terceros no observen la información mostrada en pantalla, especialmente en espacios públicos.

c) No conectar los equipos corporativos a redes Wi-Fi públicas no confiables sin canal cifrado adicional.

d) Custodiar los equipos con la diligencia debida, evitando dejarlos desatendidos en espacios accesibles.

e) Notificar de inmediato la pérdida o sustracción de cualquier dispositivo corporativo.

f) Cumplir las obligaciones específicas establecidas en el documento {{ proyecto.codigo_documento_base }}-117 (Política de Trabajo a Distancia y Movilidad) cuando este sea aplicable.

## 9. MONITORIZACIÓN DEL USO DE LOS RECURSOS

### 9.1 Facultad de control y supervisión

Conforme al artículo 87 de la Ley Orgánica 3/2018, de 5 de diciembre, de Protección de Datos Personales y garantía de los derechos digitales, la Entidad podrá acceder a los contenidos derivados del uso de los medios digitales facilitados al personal a los solos efectos de controlar el cumplimiento de las obligaciones laborales o estatutarias y de garantizar la integridad de dichos dispositivos, en los términos y con las garantías establecidas en dicho precepto.

### 9.2 Información previa

El personal usuario es informado, mediante la presente Política, de la existencia de las siguientes medidas de monitorización y control:

a) Registro de los accesos a los sistemas corporativos, conforme al documento {{ proyecto.codigo_documento_base }}-118 (Política de Registro y Auditoría).

b) Registro de las acciones realizadas con privilegios elevados.

c) Monitorización agregada del uso de la conexión a Internet, sin acceso al contenido específico de la navegación salvo en los supuestos de incidente o investigación formalmente abiertos.

d) Filtrado automatizado de contenidos web no autorizados.

e) Análisis automatizado del correo electrónico mediante herramientas antispam, antimalware y antifraude.

f) Inventario y monitorización del estado de seguridad de los equipos corporativos.

g) Posibilidad de acceso al contenido de los equipos y cuentas corporativas en los supuestos previstos en el artículo 87 de la LOPDGDD, con las garantías allí establecidas.

### 9.3 Garantías

El acceso a los contenidos derivados del uso de los recursos por parte del personal se realizará con respeto a los derechos fundamentales del trabajador, en particular a su derecho a la intimidad y al secreto de las comunicaciones, y conforme a los principios de finalidad, proporcionalidad y mínima intervención. Cualquier acceso no rutinario será documentado y justificado.

## 10. DEVOLUCIÓN DE RECURSOS A LA EXTINCIÓN DE LA RELACIÓN

Al término de la relación con la Entidad, el personal usuario procederá a:

a) Devolver todos los equipos, soportes, llaves, tarjetas y demás recursos físicos puestos a su disposición.

b) Devolver o eliminar, según las indicaciones recibidas, toda la documentación e información de la Entidad de la que disponga, en cualquier formato y ubicación.

c) Cumplir con las obligaciones de confidencialidad que subsistan tras la extinción de la relación.

d) Colaborar de buena fe en el traspaso ordenado de las funciones a su sucesor.

## 11. RÉGIMEN DE INCUMPLIMIENTO

El incumplimiento de la presente Política podrá dar lugar a la apertura del correspondiente expediente disciplinario, conforme a lo previsto en el régimen disciplinario interno aplicable y en la legislación laboral o estatutaria, sin perjuicio de las responsabilidades civiles, administrativas o penales en que pudiera incurrirse, atendiendo a la naturaleza y gravedad del incumplimiento.

En el caso del personal externo, el incumplimiento podrá dar lugar a la resolución del contrato vigente con su empleador y a la exigencia de las responsabilidades contractuales correspondientes.

## 12. ACEPTACIÓN

La presente Política será comunicada a todo el personal en el momento de su incorporación a la Entidad y se requerirá la firma o acuse de recibo formal de su aceptación, que se incorporará a su expediente.

Las modificaciones posteriores serán comunicadas y, cuando supongan obligaciones nuevas o más exigentes, requerirán nueva aceptación.

## 13. APROBACIÓN, REVISIÓN Y VIGENCIA

El presente documento ha sido aprobado por {{ cliente.organo_aprobador_politicas }} el {{ proyecto.fecha_aprobacion_inicial }} y será objeto de revisión, al menos, con la misma periodicidad que la Política de Seguridad de la Información de la que es desarrollo.

---

**Documento {{ proyecto.codigo_documento_base }}-103 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---
