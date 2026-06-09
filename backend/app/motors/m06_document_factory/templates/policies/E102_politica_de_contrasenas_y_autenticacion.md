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
