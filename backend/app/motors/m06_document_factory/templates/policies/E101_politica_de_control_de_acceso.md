# DOCUMENTO E-101 — POLÍTICA DE CONTROL DE ACCESO

**Materializa las medidas op.acc.1 a op.acc.6 del Anexo II del ENS** y los controles A.5.15-A.5.18, A.8.2, A.8.3 y A.8.5 de ISO 27001:2022. Es la política operativa más consultada en el día a día.

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-101"
titulo: "Política de Control de Acceso"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
fecha_proxima_revision: "{{ proyecto.proxima_revision }}"
clasificacion: "INTERNA"
propietario: "{{ responsables.responsable_seguridad.cargo }}"
aprobado_por: "{{ cliente.organo_aprobador_politicas }}"
---

# POLÍTICA DE CONTROL DE ACCESO DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-101 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

El presente documento establece los principios, criterios y reglas aplicables al control de acceso lógico y físico a los sistemas de información, redes, servicios, instalaciones y datos titularidad de {{ cliente.razon_social }}, con la finalidad de garantizar que únicamente las personas autorizadas, en el momento autorizado, mediante los medios autorizados y para los fines autorizados, accedan a los activos de información de la Entidad.

Esta Política desarrolla las medidas **op.acc.1 (Identificación)**, **op.acc.2 (Requisitos de acceso)**, **op.acc.3 (Segregación de funciones y tareas)**, **op.acc.4 (Proceso de gestión de derechos de acceso)**, **op.acc.5 (Mecanismos de autenticación – usuarios externos)** y **op.acc.6 (Mecanismos de autenticación – usuarios de la organización)** del Anexo II del Real Decreto 311/2022.

## 2. ÁMBITO DE APLICACIÓN

La presente Política se aplica a todo acceso, lógico o físico, a los sistemas, redes, servicios, instalaciones y datos comprendidos en el alcance del SGSI, conforme se define en el documento {{ proyecto.codigo_documento_base }}-100, sea dicho acceso solicitado por personal interno, por personal externo, por proveedores, por usuarios finales o por cualquier otra persona o sistema.

## 3. PRINCIPIOS RECTORES

### 3.1 Necesidad de saber y mínimo privilegio

Los accesos se concederán únicamente sobre la base del **principio de necesidad de saber** (*need to know*), conforme al cual cada persona accederá exclusivamente a la información estrictamente necesaria para el desempeño de las funciones que tenga encomendadas.

Adicionalmente, los privilegios concedidos serán los **mínimos imprescindibles** (*least privilege*) para el ejercicio de tales funciones, evitando la concesión de privilegios genéricos, agrupados o por defecto.

### 3.2 Identificación unívoca

Toda persona con acceso al sistema dispondrá de un **identificador único e inequívoco** que permita su identificación individual. Queda expresamente prohibido el uso de identificadores genéricos, compartidos o anónimos, salvo en aquellos casos excepcionales en los que su uso esté funcionalmente justificado, formalmente autorizado por el Responsable de la Seguridad y compensado mediante mecanismos adicionales de trazabilidad.

### 3.3 Autenticación

Toda solicitud de acceso al sistema requerirá la verificación previa de la identidad declarada por el solicitante, mediante mecanismos de autenticación cuya robustez será proporcional al nivel de seguridad exigido y al riesgo asociado.

### 3.4 Autorización

Una vez autenticado, el acceso del usuario al sistema y a los recursos concretos quedará condicionado a que disponga, en el momento del acceso, de la autorización formal correspondiente, gestionada conforme al apartado 6 del presente documento.

### 3.5 Registro y trazabilidad

Toda acción significativa relacionada con el acceso a los sistemas y a la información será objeto de registro, con el fin de permitir la atribución posterior de responsabilidades y el análisis forense en caso de incidente, conforme se desarrolla en el documento {{ proyecto.codigo_documento_base }}-118 (Política de Registro y Auditoría).

### 3.6 Segregación de funciones

Las funciones susceptibles de generar conflictos de interés o de permitir actuaciones fraudulentas no autorizadas estarán **segregadas entre personas distintas**, conforme se desarrolla en el apartado 7 del presente documento.

## 4. IDENTIFICACIÓN DE USUARIOS [op.acc.1]

### 4.1 Asignación del identificador

A cada persona usuaria del sistema se le asignará un identificador único, generado conforme a las reglas técnicas establecidas por el Responsable del Sistema y aprobadas por el Responsable de la Seguridad. El identificador acompañará a la persona durante toda su relación con la Entidad y quedará reservado para ella, no pudiendo ser reasignado a una persona distinta tras su baja.

### 4.2 Vinculación con la identidad real

Cada identificador estará vinculado, en el sistema corporativo de gestión de identidades, con la identidad real, completa y verificada de la persona física a quien se asigna, así como con el rol o roles que desempeña en la Entidad.

### 4.3 Periodo de retención

Los identificadores de personas que hayan cesado en su relación con la Entidad serán bloqueados o suprimidos en los plazos establecidos en el apartado 6.5, y en ningún caso podrán reutilizarse durante el periodo en que pudieran existir registros que los referencien.

## 5. AUTENTICACIÓN [op.acc.5 y op.acc.6]

### 5.1 Mecanismos admitidos

Los mecanismos de autenticación admitidos en los sistemas de la Entidad son los siguientes, en orden creciente de robustez:

a) **Algo que se sabe**: contraseña, código PIN.

b) **Algo que se tiene**: token físico, certificado digital instalado en dispositivo, código TOTP generado por aplicación móvil autorizada.

c) **Algo que se es**: huella dactilar, reconocimiento facial u otros mecanismos biométricos admitidos por la legislación aplicable.

### 5.2 Autenticación multifactor (MFA)

{% if proyecto.categoria_ens in ["MEDIA", "ALTA"] %}
Atendiendo a la categoría {{ proyecto.categoria_ens }} del sistema, será **obligatorio** el uso de autenticación multifactor (MFA), combinando al menos dos de los mecanismos descritos en el apartado 5.1, en los siguientes casos:

a) Acceso de usuarios privilegiados (administradores, operadores con privilegios elevados) a cualquier sistema del alcance.

b) Acceso a los sistemas desde redes externas a la red corporativa o desde ubicaciones no controladas por la Entidad.

c) Acceso a información clasificada de nivel **MEDIO** o **ALTO** en cualquiera de las dimensiones de seguridad.

d) Cualquier otro acceso que el Responsable de la Seguridad determine, atendiendo al riesgo asociado.
{% else %}
Atendiendo a la categoría BÁSICA del sistema, el uso de autenticación multifactor (MFA) será **recomendable** y, en todo caso, **obligatorio** para los accesos de administradores y para los accesos remotos desde redes externas a la red corporativa.
{% endif %}

### 5.3 Política de contraseñas

Cuando se utilicen contraseñas como factor de autenticación, estas deberán cumplir, como mínimo, los siguientes requisitos:

| Requisito | Categoría BÁSICA | Categoría MEDIA | Categoría ALTA |
|---|---|---|---|
| Longitud mínima | 8 caracteres | 12 caracteres | 14 caracteres |
| Composición | Letras + dígitos | Mayúsculas, minúsculas, dígitos y especiales | Mayúsculas, minúsculas, dígitos y especiales |
| Periodo máximo de validez | 12 meses | 6 meses | 3 meses |
| Historial (no reutilización) | Últimas 5 | Últimas 10 | Últimas 15 |
| Bloqueo tras intentos fallidos | 10 intentos | 5 intentos | 3 intentos |
| Almacenamiento | Hash con sal (SHA-256 mínimo) | Hash con sal y stretching (bcrypt/scrypt/argon2) | Hash con sal y stretching robusto (argon2id) |
| Comunicación | Solo cifrada (TLS 1.2 o superior) | Solo cifrada (TLS 1.3) | Solo cifrada (TLS 1.3 con cipher suite restringida) |

Estos requisitos se aplicarán automáticamente desde los sistemas de gestión de identidades y serán objeto de auditoría periódica por parte del Responsable de la Seguridad.

### 5.4 Custodia y protección de las credenciales

Toda persona usuaria es responsable de la custodia y protección de las credenciales de autenticación que le hayan sido asignadas, debiendo:

a) No comunicarlas a ninguna otra persona, ni siquiera al personal técnico de soporte.

b) No anotarlas en soportes que pudieran ser accesibles a terceros.

c) No reutilizar las credenciales corporativas en sistemas o servicios ajenos a la Entidad.

d) Notificar de inmediato al Responsable de la Seguridad cualquier sospecha de compromiso de las mismas.

### 5.5 Acceso de usuarios externos

El acceso de usuarios externos (proveedores, clientes, ciudadanos) a los sistemas de la Entidad se realizará mediante mecanismos de autenticación que ofrezcan garantías equivalentes a las exigidas a los usuarios internos para el mismo tipo de información o servicio, conforme a lo previsto en el Reglamento (UE) 910/2014 (eIDAS) y, cuando proceda, mediante el uso de certificados digitales reconocidos.

## 6. GESTIÓN DEL CICLO DE VIDA DE LOS DERECHOS DE ACCESO [op.acc.4]

### 6.1 Solicitud de acceso

Toda solicitud de acceso al sistema se formulará por escrito, mediante el procedimiento {{ proyecto.codigo_documento_base }}-231 (Procedimiento de Gestión de Cuentas y Accesos), e incluirá, al menos:

a) Identificación del solicitante.

b) Identificación del responsable jerárquico que avala la solicitud.

c) Descripción del rol o funciones a desempeñar.

d) Recursos a los que se solicita acceso y nivel de privilegio requerido.

e) Periodo previsto de vigencia de los accesos solicitados.

### 6.2 Autorización

La autorización corresponderá al **propietario del recurso** (el Responsable de la Información o el Responsable del Servicio, según proceda), quien valorará si los accesos solicitados son proporcionados al rol declarado y si respetan los principios de necesidad de saber y mínimo privilegio.

Toda autorización quedará formalmente documentada y será trazable en el sistema de gestión de identidades.

### 6.3 Provisión

Una vez autorizada, la provisión técnica de los accesos será realizada por el Responsable del Sistema o por el personal técnico bajo su supervisión, en el plazo máximo de cinco días hábiles desde la autorización.

### 6.4 Revisión periódica

Los derechos de acceso vigentes serán objeto de revisión periódica con la siguiente cadencia:

| Tipo de acceso | Frecuencia mínima de revisión |
|---|---|
| Accesos de usuarios privilegiados (administradores) | Trimestral |
| Accesos a información clasificada como nivel ALTO | Trimestral |
| Accesos a información clasificada como nivel MEDIO | Semestral |
| Accesos generales de usuarios | Anual |

La revisión será coordinada por el Responsable de la Seguridad, ejecutada por los propietarios de los recursos y sus resultados quedarán documentados y elevados al Comité de Seguridad.

### 6.5 Modificación y revocación

Todo cambio en las funciones de la persona usuaria (cambio de puesto, cambio de proyecto, asunción temporal de nuevas responsabilidades) dará lugar a la revisión inmediata de sus accesos y a su modificación cuando proceda, conforme al principio de mínimo privilegio.

En caso de **cese definitivo** de la relación laboral o contractual, los accesos serán revocados en los siguientes plazos máximos desde la efectividad del cese:

| Tipo de acceso | Plazo máximo de revocación |
|---|---|
| Accesos privilegiados (administradores) | 1 hora |
| Accesos a información clasificada como nivel ALTO | 4 horas |
| Accesos a información clasificada como nivel MEDIO | 24 horas |
| Accesos generales | 72 horas |

En el supuesto de **despido disciplinario o cese conflictivo**, la revocación será inmediata y previa o simultánea a la comunicación formal del cese a la persona afectada.

## 7. SEGREGACIÓN DE FUNCIONES [op.acc.3]

### 7.1 Funciones incompatibles

Se consideran funciones cuya acumulación por una misma persona genera conflicto de interés y queda, en consecuencia, prohibida sin autorización expresa y compensación documental, las siguientes:

a) Desarrollo de software y autorización de su despliegue en producción.

b) Operación del sistema y auditoría independiente del mismo.

c) Aprobación de gastos y registro contable de los mismos.

d) Solicitud de altas de usuario y autorización de las mismas.

e) Acceso a entornos productivos y modificación de los registros de auditoría sobre dichos entornos.

f) Cualquier otra combinación que el Comité de Seguridad determine en función del análisis de riesgos.

### 7.2 Mecanismos de control

La segregación de funciones se garantizará mediante:

a) Asignación clara y documentada de roles en el organigrama y en el sistema de gestión de identidades.

b) Configuración técnica de los sistemas de modo que las combinaciones prohibidas no sean técnicamente posibles.

c) Auditoría periódica del cumplimiento de la segregación, integrada en el ciclo de revisión de accesos del apartado 6.4.

d) En aquellos casos en que la dimensión de la Entidad impida una segregación estricta, adopción de **medidas compensatorias** documentadas (revisión por una segunda persona, supervisión continua, doble registro, etc.) y autorización expresa del Responsable de la Seguridad.

## 8. CONTROL DE ACCESO FÍSICO

El acceso físico a las instalaciones que albergan elementos del sistema se regulará por el principio de mínimo privilegio, conforme a las medidas mp.if.1 a mp.if.7 del Anexo II del ENS y al desarrollo específico del documento {{ proyecto.codigo_documento_base }}-110 (Política de Seguridad Física y Ambiental).

## 9. ACCESO REMOTO

El acceso remoto a los sistemas desde redes no controladas por la Entidad estará condicionado a:

a) Autorización expresa del Responsable de la Seguridad.

b) Uso obligatorio de canal cifrado (VPN corporativa o equivalente, con TLS 1.2 o superior).

c) Uso obligatorio de autenticación multifactor.

d) Registro completo de la sesión y posibilidad de terminación remota inmediata.

e) Cumplimiento de la política de uso de equipos personales (BYOD), cuando proceda, conforme al documento {{ proyecto.codigo_documento_base }}-117.

## 10. INCUMPLIMIENTO

El incumplimiento de la presente Política, incluyendo el intento de acceso no autorizado, la cesión de credenciales, la elusión de mecanismos de autenticación o la extracción de información a la que no se tiene derecho, podrá dar lugar a la apertura del correspondiente expediente disciplinario y, en su caso, a las responsabilidades civiles, administrativas o penales que correspondan, conforme a lo previsto en el apartado 10 del documento {{ proyecto.codigo_documento_base }}-100.

## 11. APROBACIÓN, REVISIÓN Y VIGENCIA

El presente documento ha sido aprobado por {{ cliente.organo_aprobador_politicas }} el {{ proyecto.fecha_aprobacion_inicial }} y será objeto de revisión, al menos, con la misma periodicidad que la Política de Seguridad de la Información de la que es desarrollo.

---

**Documento {{ proyecto.codigo_documento_base }}-101 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---
