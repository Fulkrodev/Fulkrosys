# F1.2 — POLÍTICAS CRÍTICAS DEL SGSI ENS — TEXTO LEGAL REAL EN ESPAÑOL (E-107 a E-104)

**Plan 100/100 FULKRO — Bloque 2 de plantillas reales**
**Versión:** 1.0 — 9 de abril de 2026
**Continuación de:** F1_1_POLITICAS_CRITICAS_E100_E104.md
**Destinatarios:** Claude Code (para conversión a `.docx` con `docxtpl`) + Marcos (para revisión legal por consultor ENS senior antes del primer cliente real)

---

## NOTA PRELIMINAR

Este documento completa el bloque de **9 políticas críticas** del SGSI ENS. Las advertencias legales, el catálogo de placeholders Jinja2 y el flujo de conversión a `.docx` son los mismos que en F1.1 y se dan aquí por reproducidos. El estilo redaccional sigue siendo castellano peninsular formal jurídico-administrativo, alineado con el Real Decreto 311/2022, ISO/IEC 27001:2022, las guías CCN-STIC 800 vigentes y la normativa europea aplicable.

Tras F1.1 y F1.2, las **9 políticas críticas** del SGSI quedan completas. Las 18 políticas secundarias restantes (E-109 a E-126) podrán generarse posteriormente con plantillas más ligeras o con consultor ENS senior.

---

# DOCUMENTO E-107 — POLÍTICA DE CIFRADO Y GESTIÓN DE CLAVES CRIPTOGRÁFICAS

**Materializa las medidas mp.info.3 (Cifrado), mp.com.2 (Protección de la confidencialidad), mp.com.3 (Protección de la integridad y de la autenticidad) y mp.si.2 (Criptografía) del Anexo II del ENS**, así como los controles A.8.24 (Uso de la criptografía) y A.5.31 (Requisitos legales, estatutarios, reglamentarios y contractuales) de ISO/IEC 27001:2022. Es la política técnica que el auditor pide demostrar con configuraciones reales de TLS, algoritmos en uso e inventario de claves.

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-107"
titulo: "Política de Cifrado y Gestión de Claves Criptográficas"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
fecha_proxima_revision: "{{ proyecto.proxima_revision }}"
clasificacion: "INTERNA"
propietario: "{{ responsables.responsable_seguridad.cargo }}"
aprobado_por: "{{ cliente.organo_aprobador_politicas }}"
---

# POLÍTICA DE CIFRADO Y GESTIÓN DE CLAVES CRIPTOGRÁFICAS DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-107 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

El presente documento establece los principios, criterios técnicos y obligaciones aplicables al uso de mecanismos criptográficos en {{ cliente.razon_social }}, así como al ciclo de vida de las claves criptográficas asociadas, con la finalidad de garantizar la confidencialidad, integridad, autenticidad y trazabilidad de la información tratada y de las comunicaciones realizadas por los sistemas comprendidos en el alcance del SGSI.

Esta Política da cumplimiento a las medidas **mp.info.3 (Cifrado de la información)**, **mp.com.2 (Protección de la confidencialidad de las comunicaciones)**, **mp.com.3 (Protección de la integridad y autenticidad)** y **mp.si.2 (Criptografía)** del Anexo II del Real Decreto 311/2022, y se desarrolla conforme a las recomendaciones técnicas del Centro Criptológico Nacional contenidas en la guía **CCN-STIC 807 (Criptología de empleo en el ENS)** y su Anexo 1 sobre Prestadores de Servicios de Confianza, así como en lo previsto por el Reglamento (UE) 910/2014 (eIDAS).

## 2. ÁMBITO DE APLICACIÓN

La presente Política se aplica a:

a) Toda información tratada por los sistemas de información comprendidos en el alcance del SGSI, en cualquiera de sus estados (en uso, en tránsito o almacenada).

b) Toda comunicación electrónica entre los sistemas de la Entidad y entre estos y sistemas externos.

c) Toda firma electrónica generada o verificada por los sistemas de la Entidad.

d) Toda clave criptográfica generada, custodiada, utilizada o destruida en el ejercicio de las funciones de la Entidad.

e) Todo certificado digital emitido o utilizado por la Entidad o por su personal en el ejercicio de sus funciones.

## 3. PRINCIPIOS GENERALES

### 3.1 Adecuación al riesgo

La selección de los mecanismos criptográficos será proporcional a la sensibilidad de la información a proteger, al nivel de seguridad exigible conforme al ENS y a los riesgos identificados en el análisis correspondiente.

### 3.2 Algoritmos públicos y normalizados

Únicamente se utilizarán algoritmos criptográficos **públicos, contrastados, normalizados y considerados seguros** por la comunidad criptográfica internacional y, en particular, por el Centro Criptológico Nacional. Queda expresamente prohibido el uso de algoritmos propietarios cuya seguridad dependa del desconocimiento de su funcionamiento interno (*security through obscurity*).

### 3.3 Implementaciones acreditadas

Las implementaciones criptográficas utilizadas serán, preferentemente, productos certificados conforme a Common Criteria u otros esquemas equivalentes y, cuando proceda, productos incluidos en el **Catálogo de Productos y Servicios de Seguridad de las Tecnologías de la Información y la Comunicación (CPSTIC)** del Centro Criptológico Nacional.

### 3.4 Protección de las claves

La seguridad del sistema criptográfico depende íntegramente de la protección de las claves. Toda clave criptográfica gozará del nivel de protección equivalente al máximo nivel de seguridad de la información a la que cifra o autentica.

### 3.5 Trazabilidad

Toda generación, distribución, uso, custodia, rotación y destrucción de claves criptográficas será objeto de registro auditable, conforme se desarrolla en el apartado 6 del presente documento.

## 4. ALGORITMOS Y PARÁMETROS APROBADOS

### 4.1 Algoritmos simétricos

| Uso | Algoritmo aprobado | Longitud mínima de clave |
|---|---|---|
| Cifrado de datos en reposo | AES en modos GCM o CCM | 256 bits |
| Cifrado de datos en tránsito | AES en modos GCM o ChaCha20-Poly1305 | 256 bits |
| Códigos de autenticación de mensajes (MAC) | HMAC-SHA-256 o superior, AES-GMAC | 256 bits |

Quedan **expresamente prohibidos** para nuevos despliegues los algoritmos DES, 3DES, RC4, Blowfish y todos los modos de operación obsoletos como ECB. Su erradicación de los sistemas existentes constituye un objetivo prioritario del Plan de Tratamiento de Riesgos.

### 4.2 Algoritmos asimétricos

| Uso | Algoritmo aprobado | Longitud mínima de clave |
|---|---|---|
| Firma digital | RSA, ECDSA con curva P-256/P-384, EdDSA con Ed25519 | RSA: 3072 bits / ECDSA: 256 bits |
| Intercambio de claves | DHE, ECDHE | DH: 3072 bits / ECDH: 256 bits |
| Cifrado de claves | RSA-OAEP, ECIES | RSA: 3072 bits / ECC: 256 bits |

Las claves RSA inferiores a 2048 bits y las claves ECC inferiores a 224 bits quedan **expresamente prohibidas**, debiendo ser sustituidas por claves de mayor longitud antes del 31 de diciembre del año en curso o, si tal sustitución no fuera técnicamente posible, ser registradas como excepción conforme al apartado 9 de la Política de Seguridad de la Información.

### 4.3 Funciones hash

| Uso | Algoritmo aprobado | Longitud de salida |
|---|---|---|
| Funciones hash de propósito general | SHA-256, SHA-384, SHA-512, SHA-3 | 256 bits o superior |
| Hashing de contraseñas | bcrypt, scrypt, **argon2id (preferente)** | — |

Los algoritmos MD5 y SHA-1 quedan **expresamente prohibidos** en cualquier uso relacionado con la seguridad, sin perjuicio de su uso para propósitos no relacionados con la seguridad (como la verificación no maliciosa de integridad de descargas legítimas).

### 4.4 Protocolos de comunicación segura

Para las comunicaciones cifradas se utilizarán, exclusivamente, las siguientes versiones de protocolo y configuraciones:

a) **TLS 1.3** como versión preferente y obligatoria para nuevos despliegues.

b) **TLS 1.2** únicamente cuando la compatibilidad con sistemas legacy lo exija, y siempre con conjuntos de cifrado restringidos a los considerados seguros por el CCN.

c) **SSH versión 2** para conexiones administrativas remotas, con autenticación por clave pública preferente sobre autenticación por contraseña.

Quedan **expresamente prohibidas** las versiones SSL 2.0, SSL 3.0, TLS 1.0, TLS 1.1 y SSH versión 1, así como cualquier conjunto de cifrado considerado obsoleto, débil o vulnerable.

### 4.5 Actualización del catálogo

El catálogo de algoritmos y parámetros aprobados será revisado al menos con carácter **anual** por el Responsable de la Seguridad, atendiendo a las recomendaciones publicadas por el CCN, ENISA, NIST y por la comunidad criptográfica internacional. Las modificaciones serán aprobadas por el Comité de Seguridad y comunicadas al personal técnico afectado.

## 5. APLICACIÓN DEL CIFRADO POR ESTADO DE LA INFORMACIÓN

### 5.1 Información en reposo

{% if proyecto.categoria_ens in ["MEDIA", "ALTA"] %}
Atendiendo a la categoría {{ proyecto.categoria_ens }} del sistema, será **obligatorio** el cifrado de la información en reposo en los siguientes casos:

a) Información clasificada como nivel **MEDIO** o **ALTO** en la dimensión de confidencialidad.

b) Información de carácter personal, conforme a las exigencias del RGPD y de la LOPDGDD.

c) Información almacenada en dispositivos móviles, portátiles y soportes extraíbles.

d) Copias de seguridad y archivos históricos, con independencia de su ubicación.

e) Cualquier información almacenada en entornos cloud o gestionados por terceros.
{% else %}
Atendiendo a la categoría BÁSICA del sistema, el cifrado de la información en reposo será **recomendable** con carácter general y **obligatorio** en los siguientes casos:

a) Información de carácter personal de categoría especial, conforme al artículo 9 del RGPD.

b) Información almacenada en dispositivos móviles, portátiles y soportes extraíbles.

c) Copias de seguridad almacenadas fuera de las instalaciones controladas por la Entidad.
{% endif %}

### 5.2 Información en tránsito

Será **obligatorio** el cifrado de las comunicaciones que transporten información de la Entidad en los siguientes casos:

a) Toda comunicación que atraviese redes no controladas por la Entidad, incluyendo Internet.

b) Toda comunicación entre sedes de la Entidad realizada sobre redes de terceros.

c) Toda comunicación administrativa de los sistemas (acceso remoto, gestión, monitorización).

d) Toda comunicación que transporte credenciales de autenticación, con independencia del medio.

e) Toda comunicación que transporte información de carácter personal.

### 5.3 Información en uso

Para la información considerada de máxima sensibilidad, la Entidad evaluará la pertinencia de adoptar mecanismos de protección de la información en uso, tales como tecnologías de *trusted execution environments*, *confidential computing* o cifrado homomórfico, atendiendo a la madurez de estas tecnologías y a la proporcionalidad respecto al riesgo.

## 6. CICLO DE VIDA DE LAS CLAVES CRIPTOGRÁFICAS

### 6.1 Generación

Las claves criptográficas se generarán mediante:

a) Generadores de números aleatorios criptográficamente seguros (CSPRNG).

b) Hardware criptográfico dedicado (HSM o módulos equivalentes) cuando la criticidad lo justifique.

c) Algoritmos públicos y parámetros conformes al apartado 4 del presente documento.

Toda generación de clave de uso operativo quedará registrada en el **Inventario de Claves Criptográficas** mantenido por el Responsable del Sistema bajo supervisión del Responsable de la Seguridad.

### 6.2 Distribución

La distribución de claves se realizará por canales seguros que garanticen su confidencialidad e integridad. En particular:

a) Las claves simétricas se distribuirán cifradas con claves asimétricas o mediante mecanismos de intercambio seguros tipo Diffie-Hellman.

b) Las claves privadas asimétricas no se distribuirán; serán generadas en el dispositivo o sistema donde vayan a utilizarse.

c) Las claves públicas asimétricas se distribuirán acompañadas de un mecanismo que permita verificar su autenticidad (certificado digital, firma electrónica del emisor, etc.).

### 6.3 Uso

Toda clave criptográfica será utilizada exclusivamente para los fines para los que ha sido generada y dentro del periodo de validez establecido. Queda prohibido el uso de una misma clave para múltiples propósitos criptográficos cuando ello pueda comprometer la seguridad del esquema.

### 6.4 Custodia

Las claves criptográficas se custodiarán con un nivel de protección equivalente al máximo nivel de seguridad de la información a la que protegen. En particular:

a) Las **claves privadas asimétricas** se almacenarán cifradas, con acceso restringido al sistema o persona autorizada para su uso, y nunca se transmitirán por canales no seguros.

b) Las **claves simétricas operativas** se almacenarán en HSM o, en su defecto, en almacenes de claves cifrados con mecanismos de control de acceso reforzados.

c) Las **claves de cifrado de claves** (KEK) recibirán el tratamiento más estricto, con protección equivalente a la de la información más sensible que custodian indirectamente.

### 6.5 Rotación

Las claves criptográficas serán objeto de rotación periódica, conforme a los siguientes plazos máximos:

| Tipo de clave | Plazo máximo de rotación |
|---|---|
| Claves de sesión TLS | Por sesión |
| Claves simétricas operativas (cifrado de datos en reposo) | 24 meses |
| Claves asimétricas de firma electrónica de personal | Conforme al periodo de validez del certificado, máximo 36 meses |
| Claves asimétricas de servidor (TLS) | 12 meses |
| Claves maestras de cifrado de claves (KEK) | 36 meses, con custodia de la clave anterior durante el periodo de retención de los datos cifrados |

La rotación se planificará y ejecutará evitando cualquier interrupción de los servicios y garantizando la continuidad del acceso a la información cifrada con claves anteriores.

### 6.6 Destrucción

Las claves criptográficas que dejen de ser necesarias serán destruidas conforme a procedimientos que garanticen la imposibilidad de su recuperación. Esta destrucción se documentará en el Inventario de Claves.

Cuando una clave deba conservarse a efectos de archivo (por ejemplo, para descifrar información histórica), se almacenará en un repositorio de claves históricas con controles de acceso reforzados y trazabilidad completa.

### 6.7 Compromiso o sospecha de compromiso

En caso de compromiso o sospecha fundada de compromiso de cualquier clave criptográfica, el Responsable del Sistema notificará inmediatamente al Responsable de la Seguridad, quien activará el procedimiento de gestión de incidentes ({{ proyecto.codigo_documento_base }}-108) y procederá a:

a) Revocar de inmediato la clave comprometida.

b) Generar y desplegar la clave de sustitución.

c) Reevaluar la integridad de la información que pudiera haberse visto afectada.

d) Documentar el incidente y sus consecuencias.

## 7. CERTIFICADOS DIGITALES

### 7.1 Uso de Prestadores de Servicios de Confianza cualificados

Cuando la Entidad requiera certificados digitales para firma electrónica avanzada o cualificada, sello electrónico cualificado, sello de tiempo cualificado o cualquier otro servicio de confianza regulado, se utilizarán **exclusivamente certificados emitidos por Prestadores de Servicios de Confianza cualificados**, conforme al Reglamento (UE) 910/2014 (eIDAS) y a la Lista de Confianza española publicada por el Ministerio competente en materia de transformación digital.

### 7.2 Certificados internos de servidor

Para los servicios internos de la Entidad podrán utilizarse certificados emitidos por una Autoridad de Certificación interna, siempre que esta opere conforme a las buenas prácticas internacionales y sus certificados raíz estén distribuidos de forma segura entre los sistemas que deban confiar en ellos.

### 7.3 Custodia de certificados de personal

Cuando un miembro del personal disponga de un certificado digital para el ejercicio de funciones profesionales en nombre de la Entidad, este será custodiado en un dispositivo seguro y nunca podrá ser cedido a otra persona. La pérdida, sustracción o sospecha de uso indebido será notificada inmediatamente al Responsable de la Seguridad.

## 8. CIFRADO EN ENTORNOS CLOUD Y CON PROVEEDORES

Cuando la información de la Entidad sea tratada por proveedores cloud o externos, las cláusulas contractuales correspondientes (conforme al documento {{ proyecto.codigo_documento_base }}-112, Política de Seguridad en las Relaciones con Proveedores) garantizarán que:

a) La información en tránsito y en reposo en infraestructuras del proveedor sea cifrada con algoritmos conformes al apartado 4 del presente documento.

b) Las claves de cifrado, siempre que sea técnicamente viable, sean controladas por la Entidad mediante mecanismos del tipo *Bring Your Own Key* (BYOK) o *Hold Your Own Key* (HYOK).

c) El proveedor no pueda acceder al contenido en claro de la información sin autorización expresa de la Entidad.

d) La Entidad pueda recuperar las claves al finalizar la relación contractual, garantizando la continuidad del acceso a la información durante el periodo legal o contractual de retención.

## 9. APROBACIÓN, REVISIÓN Y VIGENCIA

El presente documento ha sido aprobado por {{ cliente.organo_aprobador_politicas }} el {{ proyecto.fecha_aprobacion_inicial }} y será objeto de revisión, al menos, con la misma periodicidad que la Política de Seguridad de la Información de la que es desarrollo, y en todo caso siempre que se publiquen recomendaciones del CCN o del NIST que aconsejen modificar el catálogo de algoritmos aprobados.

---

**Documento {{ proyecto.codigo_documento_base }}-107 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---

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

# DOCUMENTO E-112 — POLÍTICA DE SEGURIDAD EN LAS RELACIONES CON PROVEEDORES

**Crítica para la cadena de suministro digital.** Materializa las medidas op.ext.1, op.ext.2, op.ext.3 y op.ext.4 (Servicios externos) del Anexo II del ENS, así como los controles A.5.19 a A.5.23 (Information security in supplier relationships) de ISO/IEC 27001:2022. Es la política que el auditor pide para verificar que el Anexo II del ENS se aplica también a los proveedores cloud y a los servicios externalizados, no solo al perímetro propio.

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-112"
titulo: "Política de Seguridad en las Relaciones con Proveedores"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
fecha_proxima_revision: "{{ proyecto.proxima_revision }}"
clasificacion: "INTERNA"
propietario: "{{ responsables.responsable_seguridad.cargo }}"
aprobado_por: "{{ cliente.organo_aprobador_politicas }}"
---

# POLÍTICA DE SEGURIDAD EN LAS RELACIONES CON PROVEEDORES DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-112 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

El presente documento establece los principios, criterios y obligaciones que regirán las relaciones de {{ cliente.razon_social }} con los proveedores y terceros que, en virtud de cualquier relación contractual, presten servicios a la Entidad, le suministren productos o accedan a sus sistemas, instalaciones, información o cualquier otro activo, con la finalidad de garantizar que la seguridad de la información se preserva en toda la cadena de suministro.

Esta Política da cumplimiento a las medidas **op.ext.1 (Contratación y acuerdos de nivel de servicio)**, **op.ext.2 (Gestión diaria)**, **op.ext.3 (Protección de la cadena de suministro)** y **op.ext.4 (Interconexión de sistemas)** del Anexo II del Real Decreto 311/2022, así como a los controles del dominio A.5 (relaciones con proveedores) de la norma UNE-EN ISO/IEC 27001:2022.

## 2. ÁMBITO DE APLICACIÓN

La presente Política se aplica a:

a) Todo proveedor de productos o servicios que tenga acceso a información, sistemas, redes o instalaciones de la Entidad comprendidos en el alcance del SGSI, ya sea de forma puntual o continuada.

b) Todo subcontratista, en cualquier nivel, que actúe en nombre o por cuenta de un proveedor de la Entidad.

c) Todo prestador de servicios cloud (IaaS, PaaS, SaaS) utilizado por la Entidad para tratar información comprendida en el alcance del SGSI.

d) Todo profesional independiente o consultor externo que preste servicios profesionales a la Entidad con acceso a información sensible.

## 3. CLASIFICACIÓN DE PROVEEDORES POR NIVEL DE CRITICIDAD

A los efectos de la aplicación graduada de las exigencias del presente documento, los proveedores se clasificarán en los siguientes niveles, atendiendo al riesgo derivado de la relación:

### 3.1 Nivel CRÍTICO

Son proveedores CRÍTICOS aquellos cuyos servicios cumplen al menos uno de los siguientes criterios:

a) Tratan información clasificada como nivel **ALTO** en cualquier dimensión del ENS.

b) Soportan servicios esenciales de la Entidad cuya interrupción podría producir un impacto significativo.

c) Acceden a información de carácter personal a gran escala o de categorías especiales conforme al artículo 9 del RGPD.

d) Tienen acceso administrativo o privilegiado a sistemas comprendidos en el alcance del SGSI.

e) Constituyen un punto único de fallo para alguna función crítica de la Entidad.

### 3.2 Nivel ALTO

Son proveedores de nivel ALTO aquellos cuyos servicios:

a) Tratan información clasificada como nivel **MEDIO** en cualquier dimensión del ENS.

b) Acceden de forma habitual a información de carácter personal.

c) Tienen acceso a sistemas relevantes pero sin privilegios administrativos.

### 3.3 Nivel MEDIO

Son proveedores de nivel MEDIO aquellos cuyos servicios:

a) Tratan exclusivamente información clasificada como nivel **BAJO**.

b) Acceden de forma puntual a información o sistemas de la Entidad.

c) Suministran productos o servicios que no implican acceso continuado a información sensible.

### 3.4 Nivel BAJO

Son proveedores de nivel BAJO aquellos cuyos servicios no implican acceso a información o sistemas de la Entidad y cuyo riesgo derivado para la seguridad de la información es despreciable.

### 3.5 Asignación y revisión del nivel

La clasificación inicial corresponderá al Responsable del Servicio que solicita la contratación, en coordinación con el Responsable de la Seguridad. La clasificación se revisará al menos con carácter **anual** y siempre que se modifique sustancialmente el alcance de la relación.

## 4. EXIGENCIAS DE SEGURIDAD POR NIVEL

### 4.1 Exigencias comunes a todos los niveles

Con independencia del nivel de criticidad, todo proveedor deberá:

a) Suscribir las cláusulas de confidencialidad correspondientes.

b) Cumplir con la legislación vigente en materia de protección de datos personales y, cuando proceda, suscribir el contrato de encargo del tratamiento conforme al artículo 28 del RGPD.

c) Cumplir con la legislación vigente en materia de propiedad intelectual e industrial.

d) Notificar a la Entidad cualquier incidente de seguridad que afecte o pueda afectar a sus servicios o a la información de la Entidad.

### 4.2 Exigencias adicionales para proveedores de nivel MEDIO o superior

Adicionalmente, los proveedores de nivel MEDIO, ALTO o CRÍTICO deberán:

a) Disponer de un Sistema de Gestión de la Seguridad de la Información debidamente implantado, preferentemente certificado conforme a la norma UNE-EN ISO/IEC 27001 o equivalente.

b) Aceptar las obligaciones específicas que la Entidad les imponga contractualmente derivadas del presente documento y del SGSI.

c) Permitir auditorías de seguridad por parte de la Entidad o de terceros designados por esta, en los términos establecidos en el contrato.

d) Notificar a la Entidad cualquier incidente de seguridad relevante en un plazo máximo de **24 horas** desde su detección.

e) Disponer de un Plan de Continuidad del Servicio adecuado a los SLA contractualmente comprometidos.

### 4.3 Exigencias adicionales para proveedores de nivel ALTO o CRÍTICO

Adicionalmente, los proveedores de nivel ALTO o CRÍTICO deberán:

a) Estar adheridos al Esquema Nacional de Seguridad cuando presten servicios a entidades del sector público o cuando los servicios formen parte del alcance certificado de la Entidad cliente.

b) Disponer de certificación de conformidad con el ENS en categoría igual o superior a la del sistema al que sirven.

c) Disponer de cobertura aseguradora suficiente frente a los riesgos derivados de su actividad.

d) Notificar incidentes graves en un plazo máximo de **6 horas** y proporcionar informes de seguimiento periódicos.

e) Mantener trazabilidad completa de las acciones realizadas sobre los sistemas o información de la Entidad y poner los registros a disposición de esta cuando se solicite.

### 4.4 Exigencias adicionales para proveedores CRÍTICOS

Adicionalmente, los proveedores CRÍTICOS deberán:

a) Someterse a una evaluación inicial de seguridad antes del inicio de la prestación, conforme al procedimiento {{ proyecto.codigo_documento_base }}-217 (Procedimiento de Evaluación de Proveedores).

b) Someterse a auditorías periódicas de seguridad con la frecuencia establecida en el contrato y, en cualquier caso, al menos una vez al año.

c) Disponer de un equipo de respuesta a incidentes con disponibilidad 24x7.

d) Notificar incidentes críticos en un plazo máximo de **1 hora**.

e) Garantizar la trazabilidad y la disponibilidad de los datos al término de la relación contractual, mediante procedimientos de salida documentados.

## 5. PROCESO DE INCORPORACIÓN DE PROVEEDORES

### 5.1 Evaluación previa

Antes de iniciar la relación contractual con un nuevo proveedor que vaya a clasificarse como nivel MEDIO o superior, el Responsable del Servicio promoverá, en coordinación con el Responsable de la Seguridad, una **evaluación previa de seguridad** que incluirá, al menos:

a) Cuestionario de seguridad cumplimentado por el proveedor.

b) Verificación de las certificaciones declaradas por el proveedor.

c) Análisis de la solvencia técnica y financiera del proveedor en relación con los servicios a prestar.

d) Análisis de riesgos específico de la relación, conforme a la metodología MAGERIT v3.

e) Verificación, en su caso, de la cadena de subcontratación que el proveedor pretende utilizar.

### 5.2 Aprobación

La incorporación de proveedores de nivel ALTO o CRÍTICO requerirá la aprobación expresa del Responsable de la Seguridad, previo informe del Comité de Seguridad cuando este lo estime necesario.

### 5.3 Cláusulas contractuales

Los contratos con proveedores de nivel MEDIO o superior incorporarán, como mínimo, las siguientes cláusulas:

a) **Cláusula de confidencialidad**, con vigencia que se prolongará tras la extinción del contrato durante el periodo legalmente exigible y, en defecto de norma, durante al menos cinco años.

b) **Cláusula de protección de datos personales** que recoja, cuando proceda, los elementos del artículo 28.3 del RGPD para el contrato de encargo del tratamiento.

c) **Cláusula de medidas de seguridad técnicas y organizativas** que el proveedor se compromete a aplicar.

d) **Cláusula de notificación de incidentes** con los plazos correspondientes al nivel del proveedor.

e) **Cláusula de derecho de auditoría** que permita a la Entidad o a terceros designados por ella verificar el cumplimiento de las obligaciones de seguridad.

f) **Cláusula de subcontratación**, que prohíba al proveedor subcontratar la totalidad o parte de los servicios sin autorización previa y por escrito de la Entidad, y que extienda al subcontratista las mismas obligaciones impuestas al contratista principal.

g) **Cláusula de localización del tratamiento de datos**, especificando los países en los que el proveedor podrá tratar la información de la Entidad y, cuando proceda, las garantías exigibles para las transferencias internacionales.

h) **Cláusula de devolución y destrucción** de la información al término del contrato, con plazos definidos.

i) **Cláusula de continuidad y reversibilidad**, especialmente para proveedores cloud, que garantice la portabilidad de los datos y servicios.

j) **Cláusula de penalización** por incumplimiento de las obligaciones de seguridad.

k) **Cláusula de responsabilidad**, incluyendo cobertura aseguradora exigible cuando proceda.

## 6. GESTIÓN DIARIA DE LA RELACIÓN

### 6.1 Seguimiento

El Responsable del Servicio realizará un seguimiento continuo del cumplimiento de las obligaciones contractuales por parte de los proveedores, en particular en lo relativo a los acuerdos de nivel de servicio (SLA) y a las obligaciones de seguridad.

Para los proveedores de nivel ALTO o CRÍTICO, se mantendrán **reuniones periódicas de seguimiento de seguridad**, con la frecuencia establecida en el contrato y, en cualquier caso, al menos con carácter trimestral para los CRÍTICOS y semestral para los de nivel ALTO.

### 6.2 Auditorías

La Entidad podrá auditar, directamente o a través de terceros independientes, el cumplimiento de las obligaciones de seguridad por parte de sus proveedores, conforme a lo establecido en el contrato. Las auditorías se realizarán con previo aviso razonable, salvo en caso de incidente grave que justifique la actuación inmediata.

Los resultados de las auditorías se documentarán y, en caso de detectarse no conformidades, se acordará un plan de acción con plazos definidos para su subsanación.

### 6.3 Gestión de incidentes derivados de proveedores

Los incidentes de seguridad notificados por proveedores se gestionarán conforme al procedimiento {{ proyecto.codigo_documento_base }}-204 (Procedimiento de Gestión de Incidentes), sin perjuicio de las acciones específicas que el contrato contemple frente al proveedor responsable.

## 7. SERVICIOS CLOUD

### 7.1 Especialidades

Los servicios cloud (IaaS, PaaS, SaaS) presentan particularidades relevantes para la seguridad que justifican tratamiento específico:

a) **Modelo de responsabilidad compartida**: la Entidad y el proveedor cloud comparten responsabilidades sobre la seguridad, con una distribución que varía según el modelo de servicio.

b) **Localización de los datos**: la información puede tratarse en infraestructuras situadas en distintas jurisdicciones, con implicaciones legales relevantes.

c) **Acceso del proveedor a los datos**: el proveedor puede tener acceso técnico a la información alojada, lo que exige medidas adicionales de protección.

d) **Dependencia y reversibilidad**: la migración entre proveedores puede ser técnicamente compleja y costosa.

### 7.2 Requisitos específicos

Los servicios cloud utilizados por la Entidad para tratar información comprendida en el alcance del SGSI deberán cumplir, además de los requisitos generales aplicables a su nivel de criticidad, los siguientes requisitos específicos:

a) **Conformidad con el ENS** en categoría igual o superior a la del sistema servido, cuando los servicios formen parte del alcance certificado de la Entidad. La conformidad debe acreditarse mediante el correspondiente certificado emitido por una entidad acreditada por ENAC o, alternativamente, mediante la aplicación del **Perfil de Cumplimiento Específico de Servicios Cloud (CCN-STIC 887)**.

b) **Localización de los datos** preferentemente en territorio del Espacio Económico Europeo, evitando transferencias internacionales innecesarias.

c) **Cifrado de los datos en reposo y en tránsito** conforme a los requisitos del documento {{ proyecto.codigo_documento_base }}-107.

d) **Control de las claves de cifrado** mediante mecanismos del tipo BYOK o HYOK siempre que sea técnicamente viable.

e) **Trazabilidad de los accesos del personal del proveedor** a las infraestructuras que alojan información de la Entidad.

f) **Plan de salida y reversibilidad** documentado, que garantice la portabilidad de los datos y servicios al término de la relación.

### 7.3 Aprobación de nuevos servicios cloud

La incorporación de cualquier nuevo servicio cloud requerirá la aprobación previa del Responsable de la Seguridad. Queda expresamente prohibida la utilización de servicios cloud no autorizados (*shadow IT*).

## 8. CADENA DE SUMINISTRO DE PRODUCTOS

### 8.1 Adquisición de productos de seguridad

La adquisición de productos de seguridad se realizará atendiendo, cuando proceda, a las disposiciones del **Catálogo de Productos y Servicios de Seguridad de las Tecnologías de la Información y la Comunicación (CPSTIC)** del Centro Criptológico Nacional, dando preferencia a los productos en él incluidos.

### 8.2 Origen de los productos

La Entidad valorará el origen de los productos tecnológicos críticos, atendiendo a criterios de soberanía digital, fiabilidad del fabricante y existencia de obligaciones legales aplicables al fabricante en su jurisdicción de origen que pudieran afectar a la seguridad de la información.

### 8.3 Mantenimiento del software

Solo se utilizará software con soporte vigente del fabricante y se aplicarán los parches de seguridad publicados conforme a los plazos establecidos en el procedimiento {{ proyecto.codigo_documento_base }}-205 (Procedimiento de Gestión de Vulnerabilidades).

## 9. EXTINCIÓN DE LA RELACIÓN

### 9.1 Procedimiento de salida

La extinción de la relación con un proveedor seguirá un procedimiento de salida documentado que incluirá, al menos:

a) Devolución o eliminación segura de la información de la Entidad en posesión del proveedor.

b) Revocación de todos los accesos del proveedor a sistemas, redes e instalaciones de la Entidad.

c) Devolución de todas las credenciales, tarjetas, dispositivos y demás recursos físicos.

d) Verificación documentada de que se han cumplido todas las obligaciones derivadas del contrato.

e) Recordatorio de las obligaciones que subsisten tras la extinción (confidencialidad, secreto profesional, etc.).

### 9.2 Continuidad del servicio

Cuando la extinción de la relación afecte a servicios críticos para la Entidad, se planificará con la antelación suficiente para garantizar la continuidad del servicio mediante migración a un proveedor alternativo o internalización del servicio.

## 10. APROBACIÓN, REVISIÓN Y VIGENCIA

El presente documento ha sido aprobado por {{ cliente.organo_aprobador_politicas }} el {{ proyecto.fecha_aprobacion_inicial }} y será objeto de revisión, al menos, con la misma periodicidad que la Política de Seguridad de la Información de la que es desarrollo.

---

**Documento {{ proyecto.codigo_documento_base }}-112 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---

# DOCUMENTO E-104 — POLÍTICA DE CLASIFICACIÓN Y TRATAMIENTO DE LA INFORMACIÓN

**La política transversal a todas las demás.** Materializa las medidas mp.info.1 (Datos personales), mp.info.2 (Calificación de la información), mp.info.4 (Firma electrónica), mp.info.5 (Sellos de tiempo) y mp.info.6 (Limpieza de documentos) del Anexo II del ENS, así como los controles A.5.12, A.5.13, A.5.14 (Information classification, labelling, transfer) y A.8.10, A.8.12 (Information deletion, Data leakage prevention) de ISO/IEC 27001:2022. Sin clasificación correcta de la información, ninguna otra medida puede aplicarse de forma proporcionada.

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-104"
titulo: "Política de Clasificación y Tratamiento de la Información"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
fecha_proxima_revision: "{{ proyecto.proxima_revision }}"
clasificacion: "INTERNA"
propietario: "{{ responsables.responsable_seguridad.cargo }}"
aprobado_por: "{{ cliente.organo_aprobador_politicas }}"
---

# POLÍTICA DE CLASIFICACIÓN Y TRATAMIENTO DE LA INFORMACIÓN DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-104 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

El presente documento establece los principios y reglas aplicables a la **clasificación de la información** tratada por {{ cliente.razon_social }}, así como los criterios y obligaciones para su **tratamiento, etiquetado, conservación, transmisión, almacenamiento y destrucción** a lo largo de todo su ciclo de vida, con la finalidad de garantizar que la información reciba en cada momento un nivel de protección proporcional a su valor, sensibilidad y criticidad.

Esta Política da cumplimiento a las medidas **mp.info.1 (Datos personales)**, **mp.info.2 (Calificación de la información)**, **mp.info.4 (Firma electrónica)**, **mp.info.5 (Sellos de tiempo)** y **mp.info.6 (Limpieza de documentos)** del Anexo II del Real Decreto 311/2022, y se complementa con el Reglamento (UE) 2016/679 (RGPD), la Ley Orgánica 3/2018 (LOPDGDD) y, cuando proceda, el Reglamento (UE) 910/2014 (eIDAS).

## 2. ÁMBITO DE APLICACIÓN

La presente Política se aplica a:

a) Toda la información tratada por la Entidad, en cualquier formato (electrónico, impreso, audiovisual u otros).

b) Todo soporte que contenga información de la Entidad, incluyendo equipos, dispositivos móviles, soportes extraíbles, archivos físicos y servicios cloud.

c) Toda la información en cualquier estado del ciclo de vida: creación, captura, recepción, almacenamiento, uso, transmisión, archivado y destrucción.

d) Todo el personal y los terceros con acceso a información de la Entidad.

## 3. PRINCIPIOS

### 3.1 Proporcionalidad de las medidas

Las medidas de protección aplicables a cada conjunto de información serán proporcionales a su clasificación, evitando tanto la sobreprotección innecesaria de información poco sensible como la subprotección de información crítica.

### 3.2 Necesidad de saber

El acceso a la información se rige por el principio de necesidad de saber, conforme se desarrolla en el documento {{ proyecto.codigo_documento_base }}-101.

### 3.3 Trazabilidad del ciclo de vida

Toda actuación relevante sobre la información (creación, modificación, transmisión, eliminación) será trazable en función de su clasificación.

### 3.4 Etiquetado obligatorio

Toda información clasificada como sensible llevará un etiquetado claramente visible que permita a su receptor identificar el nivel de protección requerido y las restricciones aplicables.

### 3.5 Responsabilidad del propietario

Cada conjunto de información tendrá un **propietario** identificado, responsable de su clasificación, de su mantenimiento y de la autorización de los accesos.

## 4. NIVELES DE CLASIFICACIÓN

A los efectos de la presente Política, la información tratada por la Entidad se clasifica en los siguientes niveles, alineados con las dimensiones de seguridad del Anexo I del ENS y con las prácticas habituales del sector:

### 4.1 PÚBLICA

**Definición.** Información cuya difusión sin restricciones no genera ningún perjuicio para la Entidad ni para sus partes interesadas y que ha sido formalmente autorizada para su difusión pública.

**Ejemplos:** comunicaciones de prensa publicadas, información disponible en la página web pública, estadísticas anonimizadas publicadas, normativa interna aprobada para difusión externa.

**Etiqueta sugerida:** PÚBLICA

### 4.2 INTERNA

**Definición.** Información cuyo destinatario natural es el personal de la Entidad y cuya divulgación no autorizada al exterior no produciría un perjuicio significativo, pero cuya difusión amplia tampoco está justificada por las necesidades del servicio.

**Ejemplos:** organigramas internos, comunicaciones internas no confidenciales, manuales de procedimiento operativos, normativa interna de uso ordinario.

**Etiqueta sugerida:** INTERNA

### 4.3 CONFIDENCIAL

**Definición.** Información cuya divulgación no autorizada produciría un perjuicio relevante para la Entidad, sus partes interesadas o terceros, y cuyo acceso debe restringirse a las personas que la necesiten estrictamente para el desempeño de sus funciones.

**Ejemplos:** contratos con clientes y proveedores, información financiera no publicada, planes estratégicos, datos personales de carácter ordinario, información comercial sensible, código fuente de aplicaciones propias, configuraciones detalladas de sistemas.

**Etiqueta sugerida:** CONFIDENCIAL

### 4.4 RESTRINGIDA

**Definición.** Información de máxima sensibilidad cuya divulgación no autorizada produciría un perjuicio grave, irreversible o de muy difícil reparación para la Entidad, sus partes interesadas o terceros, y cuyo acceso debe restringirse a un número muy reducido de personas debidamente autorizadas.

**Ejemplos:** datos personales de categorías especiales conforme al artículo 9 del RGPD, secretos comerciales o industriales, claves criptográficas maestras, información clasificada como nivel ALTO en cualquier dimensión del ENS, información sometida a obligación de secreto profesional.

**Etiqueta sugerida:** RESTRINGIDA

### 4.5 Correspondencia con las dimensiones del ENS

A efectos del cumplimiento del ENS, la correspondencia entre los niveles de clasificación de la presente Política y los niveles de las dimensiones de seguridad del Anexo I del ENS será la siguiente:

| Nivel de clasificación | Confidencialidad ENS | Integridad ENS | Disponibilidad ENS | Autenticidad ENS | Trazabilidad ENS |
|---|---|---|---|---|---|
| PÚBLICA | Sin requisito | BAJO | BAJO | BAJO | BAJO |
| INTERNA | BAJO | BAJO/MEDIO | BAJO/MEDIO | BAJO | BAJO |
| CONFIDENCIAL | MEDIO | MEDIO | MEDIO/ALTO | MEDIO | MEDIO |
| RESTRINGIDA | ALTO | ALTO | ALTO | ALTO | ALTO |

Esta tabla constituye una guía general; la asignación específica de niveles a cada conjunto de información concreto se realizará en el correspondiente análisis del Anexo I del ENS.

## 5. PROCESO DE CLASIFICACIÓN

### 5.1 Responsabilidad

La clasificación inicial de la información corresponde al **Responsable de la Información** (rol del artículo 11 del ENS), conforme se desarrolla en el documento {{ proyecto.codigo_documento_base }}-ABSORB_INTO_E100, en coordinación con quien la haya generado o capturado.

### 5.2 Criterios de decisión

Para clasificar la información, el Responsable de la Información considerará, al menos:

a) La naturaleza intrínseca de la información (datos personales, secretos comerciales, información financiera, etc.).

b) Las obligaciones legales o contractuales aplicables.

c) El impacto potencial de su divulgación no autorizada para la Entidad y para terceros.

d) El periodo de validez de la clasificación, que puede ser limitado en el tiempo (información embargada que pasa a pública en una fecha determinada, por ejemplo).

### 5.3 Revisión de la clasificación

La clasificación de la información será objeto de revisión cuando:

a) Cambien las circunstancias que motivaron la clasificación inicial.

b) Transcurra el periodo de validez establecido en su caso.

c) Se produzcan modificaciones en el marco legal aplicable.

d) Se proceda a la revisión periódica del Análisis de Riesgos.

### 5.4 Reclasificación

Cualquier persona que considere que una información concreta está clasificada incorrectamente podrá proponer su reclasificación al Responsable de la Información, quien adoptará la decisión motivada que proceda.

## 6. ETIQUETADO

### 6.1 Documentos electrónicos

Los documentos electrónicos clasificados como CONFIDENCIAL o RESTRINGIDO incluirán una marca de clasificación visible en, al menos:

a) La cabecera o el pie de cada página.

b) Los metadatos del documento, cuando el formato lo permita.

Los documentos clasificados como PÚBLICA o INTERNA podrán llevar marca de clasificación, pero no es obligatorio salvo que lo establezca un procedimiento específico.

### 6.2 Documentos en papel

Los documentos en papel clasificados como CONFIDENCIAL o RESTRINGIDO llevarán la marca de clasificación claramente visible en el anverso y, cuando sean documentos de varias páginas, en cada una de ellas.

### 6.3 Mensajes de correo electrónico

Los mensajes de correo electrónico que contengan información CONFIDENCIAL o RESTRINGIDA incluirán la indicación correspondiente en el asunto del mensaje, mediante prefijos del tipo `[CONFIDENCIAL]` o `[RESTRINGIDA]`, y, cuando técnicamente sea posible, llevarán cifrado de extremo a extremo.

### 6.4 Soportes extraíbles

Todo soporte extraíble (memoria USB, disco duro externo, óptico u otros) que contenga información CONFIDENCIAL o RESTRINGIDA llevará una etiqueta física visible que indique su nivel de clasificación.

## 7. TRATAMIENTO POR ESTADO DEL CICLO DE VIDA

### 7.1 Almacenamiento

Las medidas de protección durante el almacenamiento se aplicarán según el siguiente cuadro:

| Nivel | Medidas mínimas de almacenamiento |
|---|---|
| PÚBLICA | Sin requisitos específicos |
| INTERNA | Acceso restringido a personal de la Entidad. Sistemas con autenticación. |
| CONFIDENCIAL | Acceso restringido por necesidad de saber. Cifrado en reposo recomendable. Copias de seguridad cifradas. |
| RESTRINGIDA | Acceso limitado a un número reducido de personas autorizadas. Cifrado obligatorio en reposo. Copias de seguridad cifradas y en ubicación física separada. Trazabilidad completa de los accesos. |

### 7.2 Transmisión

La transmisión de información se ajustará al siguiente cuadro:

| Nivel | Medidas mínimas de transmisión |
|---|---|
| PÚBLICA | Sin requisitos específicos |
| INTERNA | Canales corporativos. Cifrado en tránsito recomendable cuando atraviese redes externas. |
| CONFIDENCIAL | Cifrado obligatorio en tránsito (TLS 1.2 o superior, VPN, etc.). Verificación de la identidad del destinatario. |
| RESTRINGIDA | Cifrado obligatorio extremo a extremo. Verificación reforzada del destinatario. Confirmación de recepción. Limitación del número de copias. |

### 7.3 Duplicación

Se evitará la creación innecesaria de copias de información clasificada como CONFIDENCIAL o RESTRINGIDA. Cuando sea necesario duplicar dicha información, las copias estarán sujetas a las mismas medidas de protección que el original y serán objeto de control de inventario.

### 7.4 Almacenamiento en dispositivos personales

Queda prohibido el almacenamiento de información clasificada como CONFIDENCIAL o RESTRINGIDA en dispositivos personales del personal, salvo en los supuestos expresamente autorizados por el documento {{ proyecto.codigo_documento_base }}-117 (Política de Trabajo a Distancia y Movilidad) y siempre que se apliquen medidas de protección equivalentes a las exigidas para los dispositivos corporativos.

### 7.5 Limpieza de metadatos

Antes de la difusión externa de un documento, especialmente cuando contenga información sensible, se procederá a la **limpieza de metadatos** que pudieran revelar información no destinada a la difusión, conforme a la medida mp.info.6 del Anexo II del ENS.

## 8. CONSERVACIÓN Y ARCHIVO

### 8.1 Periodos de conservación

La información se conservará durante el tiempo estrictamente necesario para los fines para los que ha sido tratada, y en todo caso durante los plazos legalmente establecidos.

Los periodos de conservación específicos para los principales tipos de información se documentarán en el **Calendario de Conservación**, mantenido por el Responsable de la Información en coordinación con el Responsable de la Seguridad y, cuando proceda, con el Delegado de Protección de Datos.

### 8.2 Datos personales

Los plazos de conservación de los datos personales atenderán a las exigencias del principio de limitación del plazo de conservación previsto en el artículo 5.1.e) del RGPD, así como a las obligaciones legales específicas aplicables.

### 8.3 Bloqueo

En el caso de los datos personales, transcurridos los plazos de conservación pertinentes, los datos serán bloqueados conforme al artículo 32 de la LOPDGDD, manteniéndose a disposición exclusiva de jueces, tribunales, Ministerio Fiscal o Administraciones Públicas competentes durante el plazo de prescripción de las acciones legales que pudieran derivarse del tratamiento, transcurrido el cual procederá a la supresión definitiva.

### 8.4 Archivo histórico

La información que deba conservarse por su valor histórico, jurídico, contable o documental se transferirá al archivo histórico de la Entidad conforme a los procedimientos correspondientes, manteniendo el nivel de clasificación que corresponda en cada momento.

## 9. DESTRUCCIÓN Y ELIMINACIÓN

### 9.1 Principio general

La eliminación de la información se realizará mediante procedimientos que garanticen la imposibilidad de su recuperación, en proporción a su nivel de clasificación.

### 9.2 Métodos por nivel

| Nivel | Métodos admitidos de destrucción |
|---|---|
| PÚBLICA | Eliminación ordinaria |
| INTERNA | Eliminación ordinaria. En soportes electrónicos: borrado lógico. |
| CONFIDENCIAL | Soportes electrónicos: borrado seguro mediante sobreescritura múltiple o desmagnetización. Papel: trituración con corte cruzado de seguridad mínima nivel P-3 conforme a UNE-EN 15713. |
| RESTRINGIDA | Soportes electrónicos: destrucción física del soporte o borrado seguro acreditado. Papel: trituración nivel P-5 o superior. Acta de destrucción documentada y firmada. |

### 9.3 Destrucción por proveedores especializados

Cuando la destrucción se confíe a proveedores especializados, estos cumplirán las exigencias del documento {{ proyecto.codigo_documento_base }}-112 (Política de Seguridad en las Relaciones con Proveedores) y emitirán los correspondientes certificados de destrucción.

### 9.4 Datos personales

La eliminación de datos personales atenderá a lo establecido en el artículo 17 del RGPD (derecho de supresión) y al apartado 8.3 anterior en lo relativo al bloqueo previo a la supresión definitiva.

## 10. FIRMA ELECTRÓNICA Y SELLOS DE TIEMPO

Cuando la integridad o autenticidad de la información así lo requieran, se utilizará la firma electrónica conforme a las exigencias del Reglamento (UE) 910/2014 (eIDAS) y de la guía CCN-STIC 807 Anexo 1 sobre Prestadores de Servicios de Confianza.

Los sellos de tiempo cualificados se utilizarán cuando sea necesario acreditar fehacientemente la existencia de la información en una fecha y hora determinadas, especialmente para evidencias en procedimientos administrativos o judiciales.

La gestión operativa de la firma electrónica y los sellos de tiempo se desarrolla en el documento {{ proyecto.codigo_documento_base }}-119 (Política de Firma Electrónica y Sellos de Tiempo).

## 11. INCUMPLIMIENTO

El tratamiento de información en contradicción con la presente Política, en particular el tratamiento, copia, transmisión o difusión no autorizada de información clasificada como CONFIDENCIAL o RESTRINGIDA, podrá dar lugar a la apertura del correspondiente expediente disciplinario, conforme al régimen sancionador interno aplicable y a la legislación laboral o estatutaria vigente, sin perjuicio de las responsabilidades civiles, administrativas o penales que correspondan.

## 12. APROBACIÓN, REVISIÓN Y VIGENCIA

El presente documento ha sido aprobado por {{ cliente.organo_aprobador_politicas }} el {{ proyecto.fecha_aprobacion_inicial }} y será objeto de revisión, al menos, con la misma periodicidad que la Política de Seguridad de la Información de la que es desarrollo.

---

**Documento {{ proyecto.codigo_documento_base }}-104 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---

## INSTRUCCIONES PARA CLAUDE CODE — CIERRE DEL BLOQUE F1

### Estado del bloque F1 tras F1.1 + F1.2

Las **9 políticas críticas** del SGSI ENS quedan completas:

| Código | Título | Bloque | Estado |
|---|---|---|---|
| E-100 | Política de Seguridad de la Información | F1.1 | ✅ Completa |
| ABSORB_INTO_E100 | Roles, Responsabilidades y Autoridades de Seguridad | F1.1 | ✅ Completa |
| E-101 | Política de Control de Acceso | F1.1 | ✅ Completa |
| E-108 | Política de Gestión de Incidentes de Seguridad | F1.1 | ✅ Completa |
| E-109 | Política de Continuidad del Servicio | F1.1 | ✅ Completa |
| E-107 | Política de Cifrado y Gestión de Claves Criptográficas | **F1.2** | ✅ Completa |
| E-103 | Política de Uso Aceptable de los Recursos | **F1.2** | ✅ Completa |
| E-112 | Política de Seguridad en las Relaciones con Proveedores | **F1.2** | ✅ Completa |
| E-104 | Política de Clasificación y Tratamiento de la Información | **F1.2** | ✅ Completa |

### Tareas para el Motor 6 (Document Factory) durante la Semana 5

1. **Crear `templates/` con 9 ficheros `.docx`** (uno por política), partiendo de la plantilla base FULKRO con tipografía Inter/Fraunces, cabecera con logo y pie con paginación, código documento y clasificación.

2. **Validar el modelo de datos** de `OrganizacionCliente` del Motor 16 contra el catálogo de placeholders documentado al inicio de F1.1, abortando con error explícito si falta alguna variable requerida.

3. **Implementar pipeline de generación**:
   ```
   onboarding del Motor 16 → modelo OrganizacionCliente populated
   → Motor 6 invoca docxtpl con cada plantilla
   → validación post-generación (sin {{ }} sin sustituir)
   → cálculo SHA-256 + firma Ed25519 del Motor 6
   → registro en BD: cliente_id + version + hash + firma
   → almacenamiento del .docx en repositorio documental del cliente
   ```

4. **Actualizar plantillas** cuando el Motor 24 (Regulatory Radar) detecte cambios en la normativa de referencia. La sección "Marco normativo" de E-100 es la primera que debe regenerarse ante cualquier modificación del RD 311/2022 o de la LOPDGDD.

### Cuadro de cobertura medidas ENS por las 9 políticas

| Medida ENS | Política/s que la materializan |
|---|---|
| **org.1** Política de seguridad | E-100 |
| **org.2** Normativa de seguridad | E-100 a E-104 (transversal) |
| **org.3** Procedimientos de seguridad | E-100 (apunta a los procedimientos del bloque F2) |
| **org.4** Proceso de autorización | E-103, E-112 |
| **op.acc.1 a op.acc.6** Control de acceso | E-101 |
| **op.exp.7** Gestión de incidentes | E-108 |
| **op.cont.1 a op.cont.4** Continuidad | E-109 |
| **op.ext.1 a op.ext.4** Servicios externos | E-112 |
| **mp.info.1 a mp.info.6** Información | E-104 |
| **mp.info.3** Cifrado | E-107 |
| **mp.com.2 / mp.com.3** Comunicaciones | E-107 |
| **mp.si.2** Criptografía | E-107 |
| **mp.eq.1 a mp.eq.4** Equipos | E-103 |
| **mp.s.1** Servicios | E-103 |

**Cobertura organizativa-básica: ~95%** de las medidas del Anexo II del ENS que requieren respaldo documental directo.

### Próximos bloques pendientes del plan 100/100

- **F2 — 12+ procedimientos críticos** (E-AR-001 a E-204-A selección): los procedimientos operativos detallados que ejecutan lo que las políticas declaran. Es donde Marcos pasa más horas durante la implantación porque cada uno requiere instrucciones paso a paso adaptadas al cliente.
- **F3 — Plantillas comerciales reales**: P-001 propuesta comercial maestra, C-001 contrato de prestación de servicios con cláusula crítica de no competencia auditor/consultor, C-003 contrato retainer post-certificación, E-001 ficha resumen ejecutivo, E-040 informe final de adecuación, E-050 informe de auditoría interna, E-400 BIA (Business Impact Analysis).
- **G — Motor 8 pentesting** afinado con MCP + LLM autónomo
- **H — LUCIA/PILAR/INES scraping** real con Playwright + certificado digital
- **I — Suite tests E2E** para las 10 fases del plan

---

**Fin del Entregable F1.2.**

4 políticas críticas restantes con texto legal real español (~12.000 palabras), completando el bloque **F1 — 9 políticas críticas SGSI ENS**. Listas para conversión a `.docx` por el Motor 6 durante la Semana 5 del plan de construcción FULKRO.
