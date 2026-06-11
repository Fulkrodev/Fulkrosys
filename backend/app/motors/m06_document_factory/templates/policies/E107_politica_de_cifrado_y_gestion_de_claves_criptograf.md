# DOCUMENTO E-107 — POLÍTICA DE CIFRADO Y GESTIÓN DE CLAVES CRIPTOGRÁFICAS

**Materializa las medidas mp.si.2 (Criptografía), mp.com.2 (Protección de la confidencialidad), mp.com.3 (Protección de la integridad y de la autenticidad) y mp.info.3 (Firma electrónica) del Anexo II del ENS**, así como los controles A.8.24 (Uso de la criptografía) y A.5.31 (Requisitos legales, estatutarios, reglamentarios y contractuales) de ISO/IEC 27001:2022. Es la política técnica que el auditor pide demostrar con configuraciones reales de TLS, algoritmos en uso e inventario de claves.

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

Esta Política da cumplimiento a las medidas **mp.si.2 (Criptografía)**, **mp.com.2 (Protección de la confidencialidad de las comunicaciones)**, **mp.com.3 (Protección de la integridad y autenticidad)** y **mp.info.3 (Firma electrónica)** del Anexo II del Real Decreto 311/2022, y se desarrolla conforme a las recomendaciones técnicas del Centro Criptológico Nacional contenidas en la guía **CCN-STIC 807 (Criptología de empleo en el ENS)** y su Anexo 1 sobre Prestadores de Servicios de Confianza, así como en lo previsto por el Reglamento (UE) 910/2014 (eIDAS).

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
