# CORRECCIÓN 5A — 7 POLÍTICAS NUEVAS PRIORIDAD ALTA (numeración v2.1)

**Plan 100/100 FULKRO — Parche de auditoría**
**Fecha:** 10 de abril de 2026
**Nota:** Estas 7 políticas complementan las 8 existentes (renumeradas) para avanzar de 8/27 a 15/27. Las 12 restantes (prioridad MEDIA y BAJA) se entregan en el bloque 5B.

**Estilo:** castellano peninsular formal jurídico-administrativo, usted, sin anglicismos, placeholders Jinja2 docxtpl, bloques `{% if %}` por categoría ENS.

---

# DOCUMENTO E-102 — POLÍTICA DE CONTRASEÑAS Y AUTENTICACIÓN

**Extraída de la antigua E-102 (ahora E-101 Control de Acceso) como política independiente conforme a v2.1. Desarrolla los mecanismos de autenticación, la política de contraseñas y los requisitos de MFA por categoría ENS. Materializa op.acc.5 y op.acc.6 del Anexo II.**

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-102"
titulo: "Política de Contraseñas y Autenticación"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
clasificacion: "INTERNA"
propietario: "{{ responsables.responsable_seguridad.cargo }}"
aprobado_por: "{{ cliente.organo_aprobador_politicas }}"
---

# POLÍTICA DE CONTRASEÑAS Y AUTENTICACIÓN DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-102 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Establecer los requisitos mínimos de robustez, gestión y protección de las credenciales de autenticación utilizadas por las personas usuarias y los sistemas de {{ cliente.razon_social }}, así como las condiciones para la implantación de autenticación multifactor, en desarrollo de la Política de Control de Accesos ({{ proyecto.codigo_documento_base }}-101) y en cumplimiento de las medidas **op.acc.5** y **op.acc.6** del Anexo II del Real Decreto 311/2022.

## 2. ÁMBITO DE APLICACIÓN

La presente Política se aplica a todo mecanismo de autenticación empleado para acceder a los sistemas, redes, servicios, aplicaciones e información comprendidos en el alcance del SGSI, con independencia de si el acceso es local o remoto, realizado por personal interno o externo, o mediante credenciales individuales o de servicio.

## 3. FACTORES DE AUTENTICACIÓN ADMITIDOS

Se admiten los siguientes factores de autenticación, clasificados conforme a la taxonomía estándar:

a) **Factor de conocimiento** (algo que se sabe): contraseña, frase de paso, código PIN.

b) **Factor de posesión** (algo que se tiene): token físico FIDO2/U2F, certificado digital en dispositivo, código TOTP generado por aplicación autenticadora autorizada, tarjeta inteligente criptográfica.

c) **Factor de inherencia** (algo que se es): huella dactilar, reconocimiento facial, u otros mecanismos biométricos admitidos por la legislación aplicable en materia de protección de datos.

## 4. AUTENTICACIÓN MULTIFACTOR (MFA)

### 4.1 Obligatoriedad

{% if proyecto.categoria_ens == "BASICA" %}
La autenticación multifactor será **obligatoria** para los accesos de administradores y para los accesos remotos desde redes externas. Para el resto de usuarios será **recomendable**.
{% elif proyecto.categoria_ens == "MEDIA" %}
La autenticación multifactor será **obligatoria** en los siguientes supuestos:

a) Acceso de usuarios con privilegios elevados (administradores, operadores, DBA) a cualquier sistema del alcance.

b) Acceso desde redes externas a la red corporativa o desde ubicaciones no controladas por la Entidad (teletrabajo, movilidad).

c) Acceso a información clasificada como nivel MEDIO o superior en cualquier dimensión.

d) Acceso a la consola de administración de servicios cloud.

e) Acceso al sistema de gestión de identidades.

f) Cualquier otro acceso que el Responsable de la Seguridad determine atendiendo al riesgo.
{% else %}
La autenticación multifactor será **obligatoria para todo acceso** a los sistemas comprendidos en el alcance del SGSI, sin excepción. Los accesos que por limitación técnica no puedan soportar MFA deberán registrarse como excepción conforme al apartado 9 de la Política de Seguridad ({{ proyecto.codigo_documento_base }}-100) y compensarse con medidas adicionales de monitorización y restricción de red.
{% endif %}

### 4.2 Combinaciones admitidas

La autenticación multifactor exige la combinación de **al menos dos factores de categorías distintas** del apartado 3. No se considerará multifactor la combinación de dos factores de la misma categoría (por ejemplo, dos contraseñas distintas).

Las combinaciones preferentes, en orden decreciente de robustez, son:

a) Token FIDO2/U2F + PIN del token (preferente por su resistencia a phishing).

b) Certificado digital en tarjeta inteligente + PIN.

c) Contraseña + código TOTP de aplicación autenticadora.

d) Contraseña + verificación biométrica.

Queda **expresamente prohibido** el uso de SMS como segundo factor de autenticación por su vulnerabilidad demostrada a ataques de interceptación (SIM swap, SS7).

## 5. POLÍTICA DE CONTRASEÑAS

### 5.1 Requisitos por categoría ENS

| Requisito | BÁSICA | MEDIA | ALTA |
|---|---|---|---|
| Longitud mínima | 10 caracteres | 12 caracteres | 14 caracteres |
| Composición | Mayúsculas + minúsculas + dígitos | + caracteres especiales | + caracteres especiales |
| Periodo máximo de validez | 365 días | 180 días | 90 días |
| Historial mínimo | Últimas 6 | Últimas 12 | Últimas 18 |
| Bloqueo tras intentos fallidos | 10 intentos | 5 intentos | 3 intentos |
| Duración del bloqueo | 15 minutos | 30 minutos | Hasta desbloqueo manual |

### 5.2 Frases de paso

Se **fomentan** las frases de paso (passphrases) de al menos 20 caracteres como alternativa preferente a las contraseñas complejas cortas, por ofrecer mayor entropía con mayor facilidad de memorización.

### 5.3 Verificación contra diccionarios de contraseñas comprometidas

Los sistemas de autenticación verificarán, en la medida de lo técnicamente posible, que las contraseñas elegidas por los usuarios no figuran en bases de datos públicas de credenciales comprometidas (como la API de Have I Been Pwned Passwords u equivalentes), rechazando aquellas que resulten comprometidas.

### 5.4 Almacenamiento de contraseñas

Las contraseñas se almacenarán exclusivamente en forma de hash criptográfico irreversible, conforme a los algoritmos establecidos en la Política Criptográfica ({{ proyecto.codigo_documento_base }}-107):

| Categoría | Algoritmo mínimo |
|---|---|
| BÁSICA | bcrypt con coste ≥ 10 |
| MEDIA | bcrypt con coste ≥ 12 o scrypt |
| ALTA | **argon2id** (preferente) con parámetros m=65536, t=3, p=4 |

### 5.5 Transmisión de contraseñas

Las credenciales se transmitirán exclusivamente por canal cifrado (TLS 1.2 o superior, preferentemente TLS 1.3). Queda expresamente prohibida la transmisión de contraseñas en texto claro por cualquier medio, incluyendo correo electrónico no cifrado.

## 6. CUSTODIA DE CREDENCIALES

Toda persona usuaria es responsable de la custodia de las credenciales que le hayan sido asignadas, debiendo:

a) No comunicarlas a ninguna otra persona, ni siquiera al personal de soporte técnico.

b) No anotarlas en soportes accesibles a terceros.

c) No reutilizarlas en sistemas o servicios ajenos a la Entidad.

d) Notificar de inmediato al Responsable de la Seguridad cualquier sospecha de compromiso.

## 7. CREDENCIALES DE SERVICIO Y CUENTAS TÉCNICAS

Las credenciales de cuentas de servicio (sistema a sistema) se gestionarán conforme a las siguientes reglas adicionales:

a) Se almacenarán en una solución de gestión de secretos (vault) con acceso restringido y auditado.

b) Se rotarán al menos cada 6 meses y siempre que cese el personal con conocimiento de las mismas.

c) No se incrustarán en código fuente, ficheros de configuración no cifrados ni variables de entorno accesibles.

d) Se auditará su uso trimestralmente.

## 8. CUENTAS DE EMERGENCIA (BREAK-GLASS)

Las credenciales de cuentas de emergencia se custodiarán en sobre sellado o bóveda con doble control. Su uso requerirá autorización previa del Responsable de la Seguridad, apertura con testigo, registro detallado de las acciones realizadas y cambio inmediato de credenciales tras el uso.

## 9. APROBACIÓN, REVISIÓN Y VIGENCIA

El presente documento ha sido aprobado por {{ cliente.organo_aprobador_politicas }} el {{ proyecto.fecha_aprobacion_inicial }} y será objeto de revisión al menos anual y siempre que se publiquen recomendaciones del CCN o del NIST que aconsejen modificar los requisitos de autenticación.

---

**Documento {{ proyecto.codigo_documento_base }}-102 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---

# DOCUMENTO E-105 — POLÍTICA DE TRATAMIENTO DE DATOS PERSONALES (RGPD)

**Política totalmente nueva. Materializa mp.info.1 del Anexo II del ENS y coordina el cumplimiento del RGPD y la LOPDGDD con el SGSI. Es la política que el auditor pide para verificar que la protección de datos personales está integrada en el SGSI y no es un silo separado.**

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-105"
titulo: "Política de Tratamiento de Datos Personales"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
clasificacion: "INTERNA"
propietario: "{{ responsables.responsable_seguridad.cargo }}"
aprobado_por: "{{ cliente.organo_aprobador_politicas }}"
---

# POLÍTICA DE TRATAMIENTO DE DATOS PERSONALES DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-105 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Establecer los principios, obligaciones y medidas organizativas que {{ cliente.razon_social }} aplica al tratamiento de datos personales, garantizando el cumplimiento del Reglamento (UE) 2016/679 del Parlamento Europeo y del Consejo, de 27 de abril de 2016 (RGPD), y de la Ley Orgánica 3/2018, de 5 de diciembre, de Protección de Datos Personales y garantía de los derechos digitales (LOPDGDD), de forma coordinada con el Sistema de Gestión de la Seguridad de la Información implantado conforme al Real Decreto 311/2022.

## 2. ÁMBITO DE APLICACIÓN

Se aplica a todo tratamiento de datos personales realizado por la Entidad, ya actúe como responsable del tratamiento, como encargado del tratamiento por cuenta de terceros, o en régimen de corresponsabilidad, y con independencia del medio utilizado (automatizado o no).

## 3. PRINCIPIOS DEL TRATAMIENTO

De conformidad con el artículo 5 del RGPD, todo tratamiento de datos personales realizado por la Entidad se regirá por los siguientes principios:

**3.1. Licitud, lealtad y transparencia.** Los datos se tratarán de manera lícita, leal y transparente en relación con el interesado.

**3.2. Limitación de la finalidad.** Los datos se recogerán con fines determinados, explícitos y legítimos y no serán tratados ulteriormente de manera incompatible con dichos fines.

**3.3. Minimización de datos.** Los datos serán adecuados, pertinentes y limitados a lo necesario en relación con los fines para los que son tratados.

**3.4. Exactitud.** Los datos serán exactos y, si fuera necesario, actualizados, adoptándose las medidas razonables para que se supriman o rectifiquen sin dilación los inexactos.

**3.5. Limitación del plazo de conservación.** Los datos se conservarán durante no más tiempo del necesario para los fines del tratamiento, salvo obligación legal que exija su conservación.

**3.6. Integridad y confidencialidad.** Los datos se tratarán de manera que se garantice una seguridad adecuada, incluida la protección contra el tratamiento no autorizado o ilícito y contra su pérdida, destrucción o daño accidental.

**3.7. Responsabilidad proactiva.** La Entidad será responsable del cumplimiento de los principios anteriores y capaz de demostrarlo.

## 4. BASES DE LEGITIMACIÓN

Todo tratamiento de datos personales se fundamentará en al menos una de las bases de legitimación del artículo 6 del RGPD. El Registro de Actividades de Tratamiento documentará la base legitimadora de cada actividad de tratamiento.

## 5. CATEGORÍAS ESPECIALES DE DATOS

El tratamiento de datos de las categorías especiales del artículo 9 del RGPD (origen étnico, opiniones políticas, convicciones religiosas, afiliación sindical, datos genéticos, datos biométricos, datos de salud, vida sexual u orientación sexual) queda **expresamente prohibido** salvo que concurra alguna de las excepciones previstas en dicho artículo. Cualquier tratamiento excepcional requerirá la autorización previa y por escrito del Delegado de Protección de Datos y del Responsable de la Seguridad.

## 6. DELEGADO DE PROTECCIÓN DE DATOS

{% if responsables.delegado_proteccion_datos %}
La Entidad ha designado como Delegado de Protección de Datos a {{ responsables.delegado_proteccion_datos.nombre }}, {{ responsables.delegado_proteccion_datos.cargo }}, con dirección de contacto {{ responsables.delegado_proteccion_datos.email }}.

El DPO ejercerá sus funciones con plena independencia funcional conforme a los artículos 38 y 39 del RGPD y coordinará estrechamente con el Responsable de la Seguridad en todos los asuntos que afecten a la seguridad de los datos personales.
{% else %}
A la fecha de aprobación de la presente Política, la Entidad no ha designado Delegado de Protección de Datos al no concurrir las circunstancias del artículo 37 del RGPD. Esta situación se revisará anualmente y siempre que cambien las actividades de tratamiento de la Entidad.
{% endif %}

## 7. REGISTRO DE ACTIVIDADES DE TRATAMIENTO

La Entidad mantendrá un **Registro de Actividades de Tratamiento** conforme al artículo 30 del RGPD, que documentará para cada actividad: denominación, responsable, finalidades, categorías de interesados y datos, destinatarios, transferencias internacionales, plazos de conservación y medidas de seguridad.

El Registro se revisará al menos semestralmente por el DPO y el Responsable de la Seguridad.

## 8. DERECHOS DE LOS INTERESADOS

La Entidad garantizará el ejercicio efectivo de los derechos de acceso, rectificación, supresión, limitación del tratamiento, portabilidad y oposición previstos en los artículos 15 a 22 del RGPD, en los plazos y con las garantías establecidos en la normativa aplicable.

Las solicitudes de ejercicio de derechos se canalizarán a través del DPO (o, en su defecto, del Responsable de la Seguridad) y se resolverán en el plazo máximo de un mes desde su recepción, prorrogable dos meses en casos de especial complejidad.

## 9. EVALUACIONES DE IMPACTO (EIPD)

Cuando un tratamiento, por su naturaleza, alcance, contexto o fines, entrañe un alto riesgo para los derechos y libertades de las personas físicas, se realizará con carácter previo una **Evaluación de Impacto en la Protección de Datos** conforme al artículo 35 del RGPD, con la participación del DPO.

## 10. ENCARGADOS DEL TRATAMIENTO

Cuando la Entidad encomiende el tratamiento de datos personales a un tercero (encargado del tratamiento), se suscribirá el correspondiente contrato de encargo conforme al artículo 28.3 del RGPD, que incluirá las instrucciones documentadas del responsable, las medidas de seguridad exigibles, las obligaciones de confidencialidad, las condiciones de subcontratación, la asistencia en el ejercicio de derechos y la obligación de supresión o devolución al término de la prestación.

## 11. BRECHAS DE DATOS PERSONALES

Las brechas de seguridad que afecten a datos personales se gestionarán conforme a la Política de Respuesta a Brechas de Datos Personales ({{ proyecto.codigo_documento_base }}-119) y al procedimiento de gestión de incidentes ({{ proyecto.codigo_documento_base }}-204), garantizando la notificación a la AEPD en el plazo de 72 horas y, cuando proceda, la comunicación a los interesados afectados.

## 12. TRANSFERENCIAS INTERNACIONALES

Las transferencias de datos personales fuera del Espacio Económico Europeo se realizarán exclusivamente cuando exista una decisión de adecuación de la Comisión Europea, se hayan adoptado garantías adecuadas conforme a los artículos 46-49 del RGPD o concurra alguna de las excepciones previstas.

## 13. COORDINACIÓN CON EL SGSI ENS

La protección de datos personales no es un sistema de gestión paralelo sino una **dimensión integrada** en el SGSI implantado conforme al ENS. Las medidas de seguridad del Anexo II del RD 311/2022 se aplican también a la protección de los datos personales tratados por los sistemas del alcance, conforme al artículo 3 del ENS.

El Responsable de la Seguridad y el DPO mantendrán reuniones de coordinación al menos trimestrales para verificar la coherencia entre las medidas del SGSI y las exigencias del RGPD.

## 14. APROBACIÓN, REVISIÓN Y VIGENCIA

Aprobada por {{ cliente.organo_aprobador_politicas }} el {{ proyecto.fecha_aprobacion_inicial }}. Revisión anual y siempre que se modifique el RGPD, la LOPDGDD o las actividades de tratamiento de la Entidad.

---

**Documento {{ proyecto.codigo_documento_base }}-105 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---

# DOCUMENTO E-106 — POLÍTICA DE COPIAS DE SEGURIDAD

**Política derivada de E-109 (Continuidad). Materializa mp.info.9 del Anexo II del ENS. Establece la estrategia de backup como política de gobierno, remitiendo al procedimiento operativo E-207 para el detalle de ejecución.**

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-106"
titulo: "Política de Copias de Seguridad"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
clasificacion: "INTERNA"
propietario: "{{ responsables.responsable_seguridad.cargo }}"
aprobado_por: "{{ cliente.organo_aprobador_politicas }}"
---

# POLÍTICA DE COPIAS DE SEGURIDAD DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-106 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Establecer los principios y requisitos mínimos aplicables a la realización, protección, verificación y restauración de copias de seguridad de los datos, configuraciones y sistemas comprendidos en el alcance del SGSI de {{ cliente.razon_social }}, en cumplimiento de la medida **mp.info.9 (Copias de seguridad)** del Anexo II del Real Decreto 311/2022.

## 2. PRINCIPIOS

### 2.1 Estrategia 3-2-1-1-0

La Entidad adoptará como mínimo la estrategia de copia **3-2-1-1-0**: tres copias en total (incluido el original), en al menos dos soportes distintos, con al menos una copia fuera de las instalaciones principales, al menos una copia inmutable o desconectada de la red (air-gapped), y cero errores verificados en las pruebas de restauración.

### 2.2 Cifrado obligatorio

Todas las copias de seguridad se almacenarán cifradas conforme a la Política Criptográfica ({{ proyecto.codigo_documento_base }}-107).

### 2.3 Proporcionalidad

La frecuencia, retención y redundancia de las copias serán proporcionales a la criticidad de los datos protegidos y a los objetivos de recuperación (RTO/RPO) establecidos en el Análisis de Impacto en el Negocio (BIA).

## 3. REQUISITOS MÍNIMOS POR CATEGORÍA ENS

| Requisito | BÁSICA | MEDIA | ALTA |
|---|---|---|---|
| Frecuencia mínima datos críticos | Semanal | Diaria | Diaria + incremental cada 4h |
| Retención mínima | 1 mes | 3 meses | 6 meses |
| Copia offsite | Recomendable | Obligatoria | Obligatoria |
| Copia inmutable/air-gapped | Recomendable | Obligatoria mensual | Obligatoria semanal |
| Pruebas de restauración | Anuales | Semestrales | Trimestrales |
| Cifrado en reposo | Obligatorio | Obligatorio | Obligatorio |

## 4. VERIFICACIÓN DE INTEGRIDAD

Cada copia se acompañará de un valor hash SHA-256 calculado en el momento de su creación. Los sistemas de copia verificarán automáticamente los hashes con periodicidad semanal y alertarán ante cualquier discrepancia.

## 5. PROTECCIÓN FRENTE A RANSOMWARE

Al menos una copia de cada dato crítico se almacenará en un sistema **inmutable** (object lock en modo compliance, cintas con protección de escritura, o snapshots inmutables) durante todo el periodo de retención, para garantizar la recuperabilidad incluso en caso de compromiso total del entorno productivo.

## 6. RESPONSABILIDADES

El Responsable del Sistema es responsable de la operación diaria de las copias. El Responsable de la Seguridad supervisa el cumplimiento de esta Política y revisa los resultados de las pruebas de restauración.

## 7. PROCEDIMIENTO OPERATIVO

El detalle operativo de las copias (programación, herramientas, matrices por tipo de dato, pruebas de restauración, registros) se desarrolla en el procedimiento {{ proyecto.codigo_documento_base }}-207 (Procedimiento de Copias de Seguridad).

## 8. APROBACIÓN, REVISIÓN Y VIGENCIA

Aprobada por {{ cliente.organo_aprobador_politicas }} el {{ proyecto.fecha_aprobacion_inicial }}. Revisión anual.

---

**Documento {{ proyecto.codigo_documento_base }}-106 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---

# DOCUMENTO E-110 — POLÍTICA DE TELETRABAJO Y MOVILIDAD

**Política nueva. Materializa mp.eq.3 (Protección de equipos portátiles) y mp.eq.4 (Otros dispositivos conectados a la red) del Anexo II del ENS, y el control A.6.7 (Trabajo a distancia) de ISO/IEC 27001:2022.**

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-110"
titulo: "Política de Teletrabajo y Movilidad"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
clasificacion: "INTERNA"
propietario: "{{ responsables.responsable_seguridad.cargo }}"
aprobado_por: "{{ cliente.organo_aprobador_politicas }}"
---

# POLÍTICA DE TELETRABAJO Y MOVILIDAD DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-110 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Establecer las condiciones de seguridad aplicables al trabajo a distancia y al uso de dispositivos móviles fuera de las instalaciones controladas por {{ cliente.razon_social }}, garantizando que la información y los sistemas del alcance del SGSI mantienen un nivel de protección equivalente al de las instalaciones corporativas.

## 2. ÁMBITO DE APLICACIÓN

Se aplica a toda persona, interna o externa, que acceda a los sistemas o información de la Entidad desde ubicaciones no controladas por esta, incluyendo el domicilio particular, espacios de coworking, instalaciones de clientes, desplazamientos y cualquier otro entorno fuera de las sedes corporativas.

## 3. AUTORIZACIÓN

### 3.1 Autorización previa

El trabajo a distancia se realizará exclusivamente en los términos autorizados por la Entidad conforme a la normativa laboral aplicable (Real Decreto-ley 28/2020, de 22 de septiembre, de trabajo a distancia, o norma que lo sustituya) y al acuerdo individual de teletrabajo suscrito con cada persona.

### 3.2 Autorización de seguridad

Con independencia de la autorización laboral, el Responsable de la Seguridad autorizará los perfiles de acceso remoto admisibles, los dispositivos autorizados y los canales de conexión permitidos.

## 4. REQUISITOS TÉCNICOS OBLIGATORIOS

### 4.1 Canal cifrado

Todo acceso remoto a los sistemas corporativos se realizará exclusivamente a través de un **canal cifrado** (VPN corporativa con TLS 1.2 o superior, o equivalente), conforme a la Política Criptográfica ({{ proyecto.codigo_documento_base }}-107).

### 4.2 Autenticación multifactor

El acceso remoto requerirá **autenticación multifactor obligatoria**, conforme a la Política de Contraseñas y Autenticación ({{ proyecto.codigo_documento_base }}-102), sin excepción.

### 4.3 Dispositivos autorizados

Solo se permitirá el acceso remoto desde **dispositivos corporativos gestionados** por la Entidad o desde dispositivos personales que cumplan los requisitos de la Política de BYOD ({{ proyecto.codigo_documento_base }}-118), cuando esta sea aplicable.

### 4.4 Cifrado del dispositivo

Los dispositivos portátiles (laptops, tabletas) utilizados en teletrabajo deberán tener **cifrado de disco completo** activado (BitLocker, FileVault, LUKS) conforme a la Política Criptográfica.

### 4.5 Antimalware y actualización

Los dispositivos remotos deberán tener instalado y actualizado el software antimalware corporativo y las actualizaciones de seguridad del sistema operativo al día, conforme al procedimiento de vulnerabilidades ({{ proyecto.codigo_documento_base }}-205).

### 4.6 Bloqueo automático

Los dispositivos se bloquearán automáticamente tras un periodo máximo de inactividad de **5 minutos** con requerimiento de autenticación para el desbloqueo.

## 5. NORMAS DE COMPORTAMIENTO EN ENTORNO REMOTO

La persona que trabaje a distancia deberá:

a) Adoptar precauciones razonables para que terceros no observen la información mostrada en pantalla, especialmente en espacios públicos. Se recomienda el uso de filtros de privacidad.

b) No conectar los equipos corporativos a redes Wi-Fi públicas abiertas sin canal cifrado adicional (VPN activa obligatoriamente).

c) No dejar desatendidos los equipos corporativos en vehículos, hoteles o espacios compartidos sin custodia adecuada.

d) No almacenar información clasificada como CONFIDENCIAL o RESTRINGIDA en el dispositivo local si es posible trabajar directamente contra los sistemas corporativos vía VPN.

e) No imprimir documentos clasificados en impresoras no controladas por la Entidad.

f) Notificar de inmediato la pérdida o sustracción de cualquier dispositivo corporativo al Responsable de la Seguridad.

## 6. ENTORNO DOMÉSTICO

Cuando el teletrabajo se realice desde el domicilio particular, se recomienda disponer de un espacio de trabajo separado con:

a) Puerta que pueda cerrarse durante las sesiones de trabajo con información sensible.

b) Conexión a Internet propia (no compartida con otros hogares) con cifrado WPA3 o, al menos, WPA2.

c) Router doméstico con contraseña de administración cambiada respecto al valor de fábrica.

## 7. VIAJES Y DESPLAZAMIENTOS

Durante los desplazamientos se aplicarán adicionalmente las siguientes medidas:

a) No facturar equipos con información sensible en el equipaje de bodega.

b) Mantener los dispositivos bajo custodia directa en todo momento.

c) No utilizar puertos USB públicos de carga (riesgo de juice jacking) sin adaptador de solo carga.

d) Deshabilitar las conexiones inalámbricas no necesarias (Bluetooth, NFC).

## 8. REVOCACIÓN DEL ACCESO REMOTO

El Responsable de la Seguridad podrá revocar de forma inmediata y sin previo aviso el acceso remoto de cualquier persona cuando detecte un comportamiento de riesgo, un posible compromiso del dispositivo o un incumplimiento de la presente Política.

## 9. APROBACIÓN, REVISIÓN Y VIGENCIA

Aprobada por {{ cliente.organo_aprobador_politicas }} el {{ proyecto.fecha_aprobacion_inicial }}. Revisión anual.

---

**Documento {{ proyecto.codigo_documento_base }}-110 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---

# DOCUMENTO E-111 — POLÍTICA DE USO DE SERVICIOS CLOUD

**Política nueva. Desarrolla las medidas op.ext.1 a op.ext.4 y las especificidades del CCN-STIC 887 (Perfil de Cumplimiento Específico de Servicios Cloud) para la contratación y uso de servicios cloud.**

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-111"
titulo: "Política de Uso de Servicios Cloud"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
clasificacion: "INTERNA"
propietario: "{{ responsables.responsable_seguridad.cargo }}"
aprobado_por: "{{ cliente.organo_aprobador_politicas }}"
---

# POLÍTICA DE USO DE SERVICIOS CLOUD DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-111 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Establecer los principios, criterios de selección, requisitos de seguridad y condiciones de uso de los servicios cloud (IaaS, PaaS, SaaS) contratados por {{ cliente.razon_social }}, garantizando que el tratamiento de información en infraestructuras de terceros cumple con las exigencias del Real Decreto 311/2022 y, en particular, con el **Perfil de Cumplimiento Específico de Servicios Cloud (CCN-STIC 887)** del Centro Criptológico Nacional.

## 2. PRINCIPIOS

### 2.1 Modelo de responsabilidad compartida

La Entidad reconoce que la seguridad en entornos cloud es una responsabilidad compartida entre el proveedor y el cliente. La distribución de responsabilidades varía según el modelo de servicio (IaaS > PaaS > SaaS) y se documentará expresamente en cada contratación.

### 2.2 Prohibición de Shadow IT

Queda **expresamente prohibida** la utilización de servicios cloud no autorizados previamente por el Responsable de la Seguridad. Todo servicio cloud utilizado para tratar información del alcance del SGSI debe estar inventariado, evaluado y aprobado.

### 2.3 Preferencia de localización EEE

Se priorizarán los proveedores que garanticen el tratamiento de la información dentro del **Espacio Económico Europeo**, evitando transferencias internacionales innecesarias.

## 3. REQUISITOS DE SEGURIDAD PARA PROVEEDORES CLOUD

### 3.1 Certificaciones exigibles

{% if proyecto.categoria_ens in ["MEDIA", "ALTA"] %}
Los servicios cloud que traten información comprendida en el alcance del SGSI deberán acreditar conformidad con el ENS en categoría igual o superior a la del sistema servido, mediante:

a) Certificado de conformidad ENS emitido por entidad acreditada por ENAC, o

b) Cumplimiento del **Perfil de Cumplimiento Específico CCN-STIC 887**, acreditado mediante auditoría independiente, o

c) Certificación equivalente reconocida (CSA STAR Level 2, SOC 2 Type II + ISO 27001 + ISO 27017 + ISO 27018) cuando las opciones anteriores no estén disponibles para el servicio concreto, previa autorización del Responsable de la Seguridad.
{% else %}
Los servicios cloud deberán disponer, como mínimo, de certificación ISO 27001 vigente y declarar su cumplimiento con las medidas de seguridad aplicables a la categoría del sistema.
{% endif %}

### 3.2 Cifrado

Los datos de la Entidad se cifrarán conforme a la Política Criptográfica ({{ proyecto.codigo_documento_base }}-107) tanto en reposo como en tránsito. Cuando sea técnicamente viable, se exigirá que las claves de cifrado estén bajo control de la Entidad mediante mecanismos **BYOK (Bring Your Own Key)** o **HYOK (Hold Your Own Key)**.

### 3.3 Trazabilidad de accesos

El proveedor deberá proporcionar registros de acceso de su personal a las infraestructuras que alojen información de la Entidad, accesibles bajo demanda y en auditoría.

### 3.4 Plan de salida y portabilidad

Antes de la contratación se verificará la existencia de un **plan de salida documentado** que garantice la portabilidad de los datos y servicios al término de la relación, en formatos abiertos y en plazos razonables.

## 4. PROCESO DE APROBACIÓN DE NUEVOS SERVICIOS CLOUD

La incorporación de cualquier nuevo servicio cloud seguirá el siguiente flujo:

a) **Solicitud** del área funcional al Responsable de la Seguridad, indicando servicio, proveedor, tipo de información a tratar y finalidad.

b) **Evaluación de seguridad** conforme al procedimiento de evaluación de proveedores ({{ proyecto.codigo_documento_base }}-217), incluyendo el análisis del modelo de responsabilidad compartida.

c) **Aprobación o denegación** del Responsable de la Seguridad, documentada y trazable.

d) **Revisión periódica** conforme al ciclo de evaluación de proveedores.

## 5. TIPOS DE INFORMACIÓN ADMITIDOS EN CLOUD

| Nivel de clasificación (Política E-104) | Admisión en cloud | Condiciones |
|---|---|---|
| PÚBLICA | Sí | Sin restricciones especiales |
| INTERNA | Sí | Cifrado en tránsito |
| CONFIDENCIAL | Sí con autorización | Cifrado reposo + tránsito + BYOK recomendable + proveedor evaluado |
| RESTRINGIDA | Solo con autorización expresa del Comité de Seguridad | Cifrado HYOK obligatorio + localización EEE + auditoría reforzada |

## 6. MONITORIZACIÓN

El Responsable del Sistema monitorizará el uso de los servicios cloud aprobados y, cuando sea técnicamente posible, implementará herramientas CASB (Cloud Access Security Broker) o equivalentes para detectar el uso no autorizado de servicios cloud.

## 7. APROBACIÓN, REVISIÓN Y VIGENCIA

Aprobada por {{ cliente.organo_aprobador_politicas }} el {{ proyecto.fecha_aprobacion_inicial }}. Revisión anual y siempre que se contrate un nuevo servicio cloud significativo.

---

**Documento {{ proyecto.codigo_documento_base }}-111 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---

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

# DOCUMENTO E-123 — POLÍTICA DE SEGURIDAD FÍSICA

**Política nueva. Materializa mp.if.1 a mp.if.7 del Anexo II del ENS y los controles A.7.1 a A.7.14 de ISO/IEC 27001:2022. Es la política que cubría el 0% en la familia mp.if de la auditoría.**

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-123"
titulo: "Política de Seguridad Física y Ambiental"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
clasificacion: "INTERNA"
propietario: "{{ responsables.responsable_seguridad.cargo }}"
aprobado_por: "{{ cliente.organo_aprobador_politicas }}"
---

# POLÍTICA DE SEGURIDAD FÍSICA Y AMBIENTAL DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-123 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Establecer los principios y requisitos aplicables a la protección física de las instalaciones, equipos e infraestructuras que albergan los sistemas de información comprendidos en el alcance del SGSI de {{ cliente.razon_social }}, en cumplimiento de las medidas **mp.if.1 (Áreas separadas y con control de acceso)**, **mp.if.2 (Identificación de las personas)**, **mp.if.3 (Acondicionamiento de los locales)**, **mp.if.4 (Energía eléctrica)**, **mp.if.5 (Protección frente a incendios)**, **mp.if.6 (Protección frente a inundaciones)** y **mp.if.7 (Registro de entrada y salida de equipamiento)** del Anexo II del Real Decreto 311/2022.

## 2. ÁMBITO DE APLICACIÓN

La presente Política se aplica a todas las instalaciones físicas que albergan elementos del sistema comprendidos en el alcance del SGSI:

{% for sede in cliente.sedes %}
- **{{ sede.nombre }}** — {{ sede.direccion }}
{% endfor %}

## 3. ZONAS DE SEGURIDAD

Las instalaciones se organizarán en zonas de seguridad concéntricas, con control de acceso progresivamente más restrictivo:

### 3.1 Zona pública

Áreas accesibles sin restricción: recepción, salas de reuniones externas, zonas comunes del edificio.

### 3.2 Zona controlada

Áreas de oficina restringidas al personal de la Entidad y a visitantes acompañados. Requieren identificación y registro.

### 3.3 Zona restringida

Áreas que albergan equipos de red, servidores, cabinas de comunicaciones o información clasificada como CONFIDENCIAL. Acceso limitado a personal autorizado con necesidad de saber.

### 3.4 Zona crítica

Centro de proceso de datos (CPD) o sala de servidores, si existe en las instalaciones de la Entidad. Acceso limitado al personal técnico expresamente autorizado, con registro individual de entradas y salidas.

## 4. CONTROL DE ACCESO FÍSICO [mp.if.1, mp.if.2]

a) Las zonas restringidas y críticas dispondrán de mecanismos de control de acceso (tarjeta magnética, biométrico u otros) que registren la identidad de cada persona que accede, la fecha y hora.

b) Los visitantes a zonas controladas o superiores serán identificados, registrados y acompañados durante toda su visita.

c) Las llaves, tarjetas y códigos de acceso se gestionarán mediante inventario controlado por el Responsable del Sistema, con procedimiento de entrega, devolución y desactivación al cese.

## 5. ACONDICIONAMIENTO DE LOCALES [mp.if.3]

Las salas que alberguen equipos críticos dispondrán de:

a) Sistema de climatización que mantenga temperatura y humedad dentro de los rangos operativos recomendados por los fabricantes de los equipos.

b) Suelo técnico o canalización adecuada para el tendido ordenado de cableado.

c) Aislamiento acústico y visual suficiente para evitar la observación no autorizada.

## 6. SUMINISTRO ELÉCTRICO [mp.if.4]

{% if proyecto.categoria_ens in ["MEDIA", "ALTA"] %}
Los equipos críticos dispondrán de:

a) Sistemas de alimentación ininterrumpida (SAI/UPS) con autonomía suficiente para un apagado ordenado (mínimo 15 minutos para categoría MEDIA, 30 minutos para categoría ALTA).

b) Protección frente a sobretensiones y transitorios eléctricos.

c) Grupo electrógeno o acuerdo contractual con proveedor de energía alternativo para las zonas críticas, cuando la categoría sea ALTA.
{% else %}
Los equipos que soporten servicios incluidos en el alcance dispondrán de protección frente a sobretensiones y, deseablemente, de sistemas de alimentación ininterrumpida (SAI/UPS) para un apagado ordenado.
{% endif %}

## 7. PROTECCIÓN CONTRA INCENDIOS [mp.if.5]

Las instalaciones cumplirán con la normativa de protección contra incendios aplicable (CTE, RIPCI) y, adicionalmente:

a) Las zonas restringidas y críticas dispondrán de sistemas de detección automática de incendios.

b) Se dispondrá de extintores adecuados (CO₂ o agente limpio en zonas con equipos electrónicos) correctamente señalizados y revisados periódicamente.

c) Se prohíbe fumar y almacenar materiales inflamables en las zonas restringidas y críticas.

## 8. PROTECCIÓN CONTRA INUNDACIONES [mp.if.6]

a) Los equipos críticos se instalarán, siempre que sea posible, en ubicaciones no susceptibles de inundación (evitar sótanos y plantas bajas en zonas de riesgo).

b) Se instalarán sensores de agua en las salas que alberguen equipos críticos.

c) El cableado de red y de alimentación se tenderá por canalizaciones elevadas respecto al suelo.

## 9. REGISTRO DE ENTRADA Y SALIDA DE EQUIPAMIENTO [mp.if.7]

Toda entrada o salida de equipamiento (servidores, dispositivos de almacenamiento, cintas de backup, soportes extraíbles) de las zonas restringidas y críticas se registrará, indicando:

a) Descripción del equipo y número de serie.

b) Persona que lo introduce o retira y motivo.

c) Fecha y hora.

d) Autorización del Responsable del Sistema.

## 10. MANTENIMIENTO DE INSTALACIONES

Las instalaciones y sus sistemas de protección (climatización, SAI, detección de incendios, control de accesos) serán objeto de mantenimiento preventivo periódico conforme a los contratos de mantenimiento suscritos y a la normativa técnica aplicable.

## 11. APROBACIÓN, REVISIÓN Y VIGENCIA

Aprobada por {{ cliente.organo_aprobador_politicas }} el {{ proyecto.fecha_aprobacion_inicial }}. Revisión anual y siempre que se produzcan cambios en las instalaciones.

---

**Documento {{ proyecto.codigo_documento_base }}-123 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---

## RESUMEN DEL BLOQUE 5A

### 7 políticas nuevas PRIORIDAD ALTA entregadas

| ID v2.1 | Título | Líneas aprox. | Medidas ENS cubiertas |
|---|---|---|---|
| **E-102** | Contraseñas y Autenticación | ~130 | op.acc.5, op.acc.6 |
| **E-105** | Tratamiento de Datos Personales (RGPD) | ~120 | mp.info.1 |
| **E-106** | Copias de Seguridad | ~70 | mp.info.9 |
| **E-110** | Teletrabajo y Movilidad | ~110 | mp.eq.3, mp.eq.4 |
| **E-111** | Uso de Servicios Cloud | ~100 | op.ext.1-4, CCN-STIC 887 |
| **E-119** | Respuesta a Brechas de Datos Personales | ~100 | RGPD art. 33-34 |
| **E-123** | Seguridad Física y Ambiental | ~120 | mp.if.1-7 (antes 0% cobertura) |

### Estado de las 27 políticas tras este bloque

| Estado | Cantidad | IDs |
|---|---|---|
| ✅ Existentes (renumeradas de F1) | 8 | E-100, E-101, E-103, E-104, E-107, E-108, E-109, E-112 |
| ✅ **Nuevas en este bloque** | **7** | **E-102, E-105, E-106, E-110, E-111, E-119, E-123** |
| 🔲 Pendientes (bloque 5B) | 12 | E-113, E-114, E-115, E-116, E-117, E-118, E-120, E-121, E-122, E-124, E-125, E-126 |

**Progreso: 15/27 políticas completas (56%).**

### Siguiente: Bloque 5B — las 12 políticas restantes (prioridad MEDIA y BAJA)

Si me dices "seguimos" arranco inmediatamente con las 12 que faltan para cerrar las 27/27 políticas.
