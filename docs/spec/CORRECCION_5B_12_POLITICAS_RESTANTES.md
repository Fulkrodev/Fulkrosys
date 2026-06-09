# CORRECCIÓN 5B — 12 POLÍTICAS RESTANTES PRIORIDAD MEDIA/BAJA (numeración v2.1)

**Plan 100/100 FULKRO — Parche de auditoría**
**Fecha:** 10 de abril de 2026
**Nota:** Estas 12 políticas completan las 27/27 del catálogo v2.1 §2.6.

---

# DOCUMENTO E-113 — POLÍTICA DE ADQUISICIÓN DE TECNOLOGÍA

**Materializa op.pl.3 (Adquisición de nuevos componentes) y op.pl.5 (Componentes certificados / CPSTIC) del Anexo II.**

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-113"
titulo: "Política de Adquisición de Tecnología"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
clasificacion: "INTERNA"
aprobado_por: "{{ cliente.organo_aprobador_politicas }}"
---

# POLÍTICA DE ADQUISICIÓN DE TECNOLOGÍA DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-113 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Establecer los criterios de seguridad que {{ cliente.razon_social }} aplicará en la adquisición, contratación e incorporación de componentes tecnológicos (hardware, software, servicios y productos de seguridad) a los sistemas comprendidos en el alcance del SGSI, en cumplimiento de las medidas **op.pl.3** y **op.pl.5** del Anexo II del Real Decreto 311/2022.

## 2. PRINCIPIOS

**2.1 Evaluación previa de seguridad.** Ningún componente tecnológico se incorporará al entorno productivo sin una evaluación previa de su impacto en la seguridad del sistema, proporcional a su criticidad.

**2.2 Soporte vigente.** Solo se adquirirán productos con soporte activo del fabricante, salvo excepción documentada y autorizada conforme al apartado 9 de la Política de Seguridad ({{ proyecto.codigo_documento_base }}-100).

**2.3 Preferencia CPSTIC.** {% if proyecto.categoria_ens in ["MEDIA", "ALTA"] %}Para los productos de seguridad TIC (criptografía, cortafuegos, IDS/IPS, antimalware, gestión de identidades, SIEM), se dará **preferencia** a los productos incluidos en el **Catálogo de Productos y Servicios de Seguridad TIC (CPSTIC)** del Centro Criptológico Nacional, conforme a la medida op.pl.5 del Anexo II.{% else %}Se valorará la inclusión de los productos en el CPSTIC del Centro Criptológico Nacional como criterio positivo de selección.{% endif %}

**2.4 Cadena de suministro.** Se valorará el origen del fabricante, la existencia de obligaciones legales en su jurisdicción que pudieran afectar a la seguridad de la información, y la transparencia de su cadena de suministro.

## 3. PROCESO DE ADQUISICIÓN

Toda solicitud de adquisición de tecnología para sistemas del alcance del SGSI seguirá este flujo:

a) **Solicitud** del área funcional con justificación de necesidad.

b) **Evaluación de seguridad** por el Responsable de la Seguridad, considerando: compatibilidad con la arquitectura, impacto en la superficie de ataque, requisitos de hardening, disponibilidad de parches, certificaciones de seguridad.

c) **Verificación CPSTIC** cuando el producto sea de seguridad TIC y la categoría sea MEDIA o ALTA.

d) **Aprobación** del Responsable de la Seguridad (o del Comité de Seguridad para adquisiciones de impacto ALTO).

e) **Integración controlada** mediante el procedimiento de gestión de cambios ({{ proyecto.codigo_documento_base }}-203) y hardening conforme a las baselines aplicables.

## 4. APROBACIÓN Y VIGENCIA

Aprobada por {{ cliente.organo_aprobador_politicas }} el {{ proyecto.fecha_aprobacion_inicial }}. Revisión anual.

---

**Documento {{ proyecto.codigo_documento_base }}-113 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---

# DOCUMENTO E-114 — POLÍTICA DE DESARROLLO SEGURO (SSDLC)

**Materializa mp.sw.1 (Desarrollo de aplicaciones) y mp.sw.2 (Aceptación y puesta en servicio) del Anexo II. Obligatoria desde categoría MEDIA.**

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-114"
titulo: "Política de Desarrollo Seguro"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
clasificacion: "INTERNA"
aprobado_por: "{{ cliente.organo_aprobador_politicas }}"
---

# POLÍTICA DE DESARROLLO SEGURO DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-114 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Establecer los principios y requisitos de seguridad aplicables al ciclo de vida del desarrollo de software (SSDLC) en {{ cliente.razon_social }}, tanto para el desarrollo interno como para el software desarrollado por terceros bajo encargo, en cumplimiento de las medidas **mp.sw.1 (Desarrollo de aplicaciones)** y **mp.sw.2 (Aceptación y puesta en servicio)** del Anexo II del Real Decreto 311/2022.

{% if proyecto.categoria_ens == "BASICA" %}
**Nota sobre categoría BÁSICA:** La presente Política es recomendable en categoría BÁSICA y obligatoria en categorías MEDIA y ALTA. Su aplicación se graduará en función de la criticidad del software desarrollado.
{% endif %}

## 2. PRINCIPIOS

**2.1 Seguridad desde el diseño (Security by Design).** Los requisitos de seguridad se identificarán y documentarán desde las fases iniciales del ciclo de vida, no como corrección posterior.

**2.2 Defensa en profundidad.** Las aplicaciones implementarán múltiples capas de control de seguridad (validación de entrada, autenticación, autorización, cifrado, registro, tratamiento de errores).

**2.3 Mínimo privilegio.** Las aplicaciones solicitarán y utilizarán únicamente los privilegios estrictamente necesarios para su función.

**2.4 Fallo seguro.** Ante una condición de error, las aplicaciones fallarán de forma segura, sin revelar información sensible ni dejar el sistema en un estado vulnerable.

## 3. REQUISITOS POR FASE DEL SSDLC

### 3.1 Análisis y diseño

a) Modelado de amenazas (STRIDE, DREAD o equivalente) para componentes críticos.

b) Requisitos de seguridad documentados como parte de la especificación funcional.

c) Revisión de arquitectura de seguridad antes de iniciar la codificación.

### 3.2 Codificación

a) Cumplimiento de las guías de codificación segura aplicables al lenguaje (OWASP Coding Practices, CWE Top 25, CERT Secure Coding Standards).

b) Validación y saneamiento de toda entrada de usuario.

c) Uso de APIs criptográficas aprobadas conforme a la Política Criptográfica ({{ proyecto.codigo_documento_base }}-107).

d) Gestión segura de credenciales: nunca en código fuente ni en ficheros de configuración sin cifrar.

e) Tratamiento seguro de errores: sin exposición de stack traces, rutas internas ni información de depuración en producción.

### 3.3 Pruebas de seguridad

a) **SAST (Static Application Security Testing):** análisis estático del código fuente mediante herramientas automatizadas (Semgrep, Bandit, SonarQube o equivalentes) integrado en el pipeline CI/CD.

b) **SCA (Software Composition Analysis):** verificación de dependencias de terceros contra bases de datos de vulnerabilidades conocidas (Trivy, Safety, OWASP Dependency-Check).

c) **DAST (Dynamic Application Security Testing):** pruebas dinámicas sobre la aplicación en ejecución (OWASP ZAP, Nikto) en entorno de preproducción.

d) **Pentesting:** para aplicaciones críticas, test de intrusión específico conforme al Motor 8 (Pentesting Engine).

### 3.4 Aceptación y puesta en servicio [mp.sw.2]

Ninguna aplicación pasará a producción sin cumplir los siguientes requisitos:

a) Pruebas de seguridad completadas con hallazgos críticos y altos corregidos.

b) Revisión de hardening de la configuración del entorno de despliegue.

c) Aprobación formal del Responsable de la Seguridad para el paso a producción.

d) Documentación de seguridad actualizada (arquitectura, flujo de datos, controles).

### 3.5 Mantenimiento

a) Aplicación de parches de seguridad conforme al procedimiento de vulnerabilidades ({{ proyecto.codigo_documento_base }}-205).

b) Monitorización continua de las dependencias para detectar nuevas vulnerabilidades.

c) Re-evaluación de seguridad ante cambios significativos.

## 4. SOFTWARE DE TERCEROS

Cuando {{ cliente.razon_social }} encargue el desarrollo de software a terceros, los contratos incluirán cláusulas que obliguen al proveedor a cumplir con los requisitos de esta Política, a entregar los resultados de las pruebas de seguridad y a remediar las vulnerabilidades detectadas.

## 5. APROBACIÓN Y VIGENCIA

Aprobada por {{ cliente.organo_aprobador_politicas }} el {{ proyecto.fecha_aprobacion_inicial }}. Revisión anual.

---

**Documento {{ proyecto.codigo_documento_base }}-114 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---

# DOCUMENTO E-115 — POLÍTICA DE GESTIÓN DE VULNERABILIDADES

**Política madre del procedimiento E-205. Materializa op.exp.4 del Anexo II. Obligatoria desde categoría MEDIA.**

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-115"
titulo: "Política de Gestión de Vulnerabilidades"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
clasificacion: "INTERNA"
aprobado_por: "{{ cliente.organo_aprobador_politicas }}"
---

# POLÍTICA DE GESTIÓN DE VULNERABILIDADES DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-115 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Establecer los principios y compromisos de {{ cliente.razon_social }} en materia de identificación, valoración, priorización y tratamiento de las vulnerabilidades técnicas que afecten a sus sistemas de información, en cumplimiento de la medida **op.exp.4 (Mantenimiento y actualizaciones de seguridad)** del Anexo II del Real Decreto 311/2022.

## 2. PRINCIPIOS

**2.1 Visibilidad completa.** La Entidad mantendrá una cobertura de escaneo de vulnerabilidades ≥95% de los activos inventariados del alcance del SGSI.

**2.2 Priorización basada en riesgo.** Las vulnerabilidades se priorizarán combinando la puntuación CVSS con factores contextuales (criticidad del activo, exposición a Internet, existencia de exploit público, inclusión en el catálogo CISA KEV).

**2.3 Plazos de corrección proporcionales.** Los plazos máximos de corrección se establecen por criticidad:

| Criticidad efectiva | Plazo máximo de corrección |
|---|---|
| CRÍTICA con explotación activa | 24 horas |
| CRÍTICA | 7 días |
| ALTA | 15 días |
| MEDIA | 60 días |
| BAJA | 180 días |

**2.4 Excepción documentada.** Cuando no sea posible corregir una vulnerabilidad en plazo, se gestionará como excepción conforme al apartado 9 de la Política de Seguridad ({{ proyecto.codigo_documento_base }}-100), documentando el riesgo asumido y las mitigaciones compensatorias.

## 3. FUENTES DE INTELIGENCIA

El Responsable de la Seguridad monitorizará al menos: CCN-CERT, INCIBE-CERT, NVD (NIST), CISA KEV, boletines de los fabricantes del software utilizado.

## 4. PROCEDIMIENTO OPERATIVO

El detalle operativo se desarrolla en el procedimiento {{ proyecto.codigo_documento_base }}-205 (Gestión de Vulnerabilidades) y {{ proyecto.codigo_documento_base }}-206 (Aplicación de Parches).

## 5. APROBACIÓN Y VIGENCIA

Aprobada por {{ cliente.organo_aprobador_politicas }} el {{ proyecto.fecha_aprobacion_inicial }}. Revisión anual.

---

**Documento {{ proyecto.codigo_documento_base }}-115 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---

# DOCUMENTO E-116 — POLÍTICA DE GESTIÓN DE CAMBIOS

**Política madre del procedimiento E-203. Materializa op.exp.5 del Anexo II.**

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-116"
titulo: "Política de Gestión de Cambios"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
clasificacion: "INTERNA"
aprobado_por: "{{ cliente.organo_aprobador_politicas }}"
---

# POLÍTICA DE GESTIÓN DE CAMBIOS DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-116 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Garantizar que ningún cambio se introduzca en los sistemas productivos comprendidos en el alcance del SGSI sin haber sido previamente planificado, evaluado en términos de seguridad y estabilidad, autorizado por el órgano competente y verificado tras su implantación, en cumplimiento de la medida **op.exp.5 (Gestión de cambios)** del Anexo II del Real Decreto 311/2022.

## 2. PRINCIPIOS

**2.1 Todo cambio es formal.** Todo cambio en hardware, software, configuración, red o procedimientos operativos del sistema debe seguir un flujo formal documentado.

**2.2 Análisis de impacto previo.** Antes de su ejecución, cada cambio será evaluado en términos de impacto en la seguridad, la disponibilidad y la integridad del sistema.

**2.3 Reversibilidad.** Todo cambio debe tener un plan de marcha atrás (rollback) documentado y probado antes de su ejecución.

**2.4 Trazabilidad.** Todo cambio quedará registrado con identificador único, persona solicitante, autorizador, ejecutor, fecha y resultado.

**2.5 Comité de Cambios (CAB).** Los cambios de impacto ALTO o CRÍTICO serán evaluados y autorizados por el Comité de Cambios, conforme al procedimiento {{ proyecto.codigo_documento_base }}-203.

## 3. CLASIFICACIÓN

Los cambios se clasifican en: ESTÁNDAR (preautorizados, catálogo), NORMAL (requieren evaluación individual), EMERGENCIA (flujo abreviado con ratificación posterior).

## 4. PROCEDIMIENTO OPERATIVO

El detalle se desarrolla en el procedimiento {{ proyecto.codigo_documento_base }}-203 (Gestión de Cambios Técnicos).

## 5. APROBACIÓN Y VIGENCIA

Aprobada por {{ cliente.organo_aprobador_politicas }} el {{ proyecto.fecha_aprobacion_inicial }}. Revisión anual.

---

**Documento {{ proyecto.codigo_documento_base }}-116 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---

# DOCUMENTO E-117 — POLÍTICA DE GESTIÓN DE PRIVILEGIOS Y PAM

**Materializa op.acc.3 (Segregación de funciones) y op.acc.4 (Gestión de derechos de acceso) con foco en cuentas privilegiadas. Obligatoria desde categoría MEDIA.**

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-117"
titulo: "Política de Gestión de Privilegios y Acceso Privilegiado (PAM)"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
clasificacion: "INTERNA"
aprobado_por: "{{ cliente.organo_aprobador_politicas }}"
---

# POLÍTICA DE GESTIÓN DE PRIVILEGIOS Y ACCESO PRIVILEGIADO DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-117 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Establecer las reglas específicas para la gestión de cuentas con privilegios elevados (administradores, operadores, root, DBA, cuentas de servicio con acceso amplio) en los sistemas comprendidos en el alcance del SGSI, garantizando que el acceso privilegiado se concede con el mínimo alcance necesario, por el tiempo mínimo necesario y con trazabilidad completa.

## 2. PRINCIPIOS

**2.1 Privilegio mínimo estricto.** Los privilegios elevados se concederán únicamente para las tareas concretas que los requieran, nunca con carácter permanente o genérico.

**2.2 Justificación y aprobación.** Toda concesión de privilegios elevados requiere solicitud formal con justificación, aprobación del Responsable de la Seguridad y registro en el sistema de gestión de identidades.

**2.3 Separación de cuentas.** Las personas con funciones administrativas dispondrán de una cuenta nominativa estándar para su trabajo diario y una cuenta administrativa separada exclusivamente para tareas que requieran privilegios elevados. Queda prohibido el uso de la cuenta administrativa para actividades ordinarias.

**2.4 Sesiones acotadas.** Las sesiones privilegiadas tendrán duración limitada. Los privilegios Just-in-Time (JIT) se emplearán cuando la tecnología lo permita: el usuario solicita el privilegio, se le concede por un periodo definido, y se revoca automáticamente al expirar.

**2.5 Monitorización reforzada.** Todas las acciones realizadas con cuentas privilegiadas se registrarán en el SIEM con nivel de detalle superior al del usuario estándar, y se revisarán conforme al procedimiento de revisión de logs ({{ proyecto.codigo_documento_base }}-223).

**2.6 MFA obligatorio.** La autenticación multifactor es obligatoria para todo acceso privilegiado, sin excepción.

## 3. TIPOS DE CUENTAS PRIVILEGIADAS

| Tipo | Descripción | Requisitos específicos |
|---|---|---|
| Administrador de dominio | Control total sobre el directorio activo | MFA + sesión grabada + revisión mensual |
| Administrador de servidor | Root/Administrator en servidores | MFA + cuenta separada |
| DBA | Administrador de bases de datos | MFA + acceso restringido a producción |
| Administrador de red | Control sobre firewall, switches, routers | MFA + doble aprobación para cambios en producción |
| Administrador cloud | Consola de administración AWS/Azure/GCP | MFA + IP origen restringida |
| Cuenta de servicio privilegiada | Sistema a sistema con privilegios amplios | Credenciales en vault, rotación automática |
| Break-glass | Emergencia: acceso total al sistema | Sobre sellado, doble custodia, uso con testigo |

## 4. REVISIÓN PERIÓDICA

Las cuentas privilegiadas se revisarán **trimestralmente** para verificar que los privilegios concedidos siguen siendo necesarios y proporcionados. Las cuentas inactivas durante más de 60 días se deshabilitarán automáticamente.

## 5. PROCEDIMIENTO OPERATIVO

El detalle se desarrolla en el procedimiento {{ proyecto.codigo_documento_base }}-211 (Gestión de Cuentas Privilegiadas).

## 6. APROBACIÓN Y VIGENCIA

Aprobada por {{ cliente.organo_aprobador_politicas }} el {{ proyecto.fecha_aprobacion_inicial }}. Revisión anual.

---

**Documento {{ proyecto.codigo_documento_base }}-117 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---

# DOCUMENTO E-118 — POLÍTICA DE BYOD (Bring Your Own Device)

**Política condicional: solo aplica cuando la Entidad permite el uso de dispositivos personales para actividades laborales.**

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-118"
titulo: "Política de Uso de Dispositivos Personales (BYOD)"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
clasificacion: "INTERNA"
aprobado_por: "{{ cliente.organo_aprobador_politicas }}"
---

# POLÍTICA DE USO DE DISPOSITIVOS PERSONALES (BYOD) DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-118 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Establecer las condiciones bajo las cuales el personal de {{ cliente.razon_social }} podrá utilizar dispositivos personales (ordenadores portátiles, teléfonos móviles, tabletas) para acceder a información y sistemas corporativos.

## 2. POSICIÓN DE LA ENTIDAD

{% if cliente.permite_byod %}
{{ cliente.razon_social }} **autoriza** el uso de dispositivos personales para actividades laborales, sujeto al cumplimiento estricto de los requisitos establecidos en la presente Política.
{% else %}
{{ cliente.razon_social }} **no autoriza** con carácter general el uso de dispositivos personales para acceder a los sistemas o información comprendidos en el alcance del SGSI. Las excepciones deberán ser autorizadas individualmente por el Responsable de la Seguridad.
{% endif %}

## 3. REQUISITOS MÍNIMOS DEL DISPOSITIVO PERSONAL

Para ser autorizado, el dispositivo personal deberá cumplir:

a) Sistema operativo con soporte vigente del fabricante y actualizaciones al día.

b) **Cifrado de disco completo** activado.

c) **Código de desbloqueo** o autenticación biométrica activados, con bloqueo automático a 5 minutos de inactividad.

d) Software antimalware instalado y actualizado (o protección nativa del sistema operativo equivalente).

e) No tener root/jailbreak aplicado.

f) Posibilidad de borrado remoto (MDM corporativo o funcionalidad nativa del sistema operativo).

## 4. CONDICIONES DE USO

a) El acceso a sistemas corporativos desde dispositivos personales se realizará **exclusivamente** a través de la VPN corporativa o de soluciones de escritorio virtual (VDI) autorizadas.

b) La información clasificada como CONFIDENCIAL o RESTRINGIDA **no se almacenará localmente** en el dispositivo personal.

c) Se utilizarán contenedores corporativos (MDM) para separar los datos personales de los corporativos cuando la tecnología lo permita.

d) La Entidad se reserva el derecho de **borrar remotamente** los datos corporativos del dispositivo en caso de pérdida, sustracción, cese de la relación laboral o incidente de seguridad.

e) La persona usuaria acepta que el dispositivo personal podrá ser **inspeccionado** por el equipo de seguridad en caso de incidente, limitándose la inspección al contenedor corporativo.

## 5. APROBACIÓN Y VIGENCIA

Aprobada por {{ cliente.organo_aprobador_politicas }} el {{ proyecto.fecha_aprobacion_inicial }}. Revisión anual.

---

**Documento {{ proyecto.codigo_documento_base }}-118 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---

# DOCUMENTO E-120 — POLÍTICA DE GESTIÓN DE CLAVES CRIPTOGRÁFICAS

**Amplía la sección de ciclo de vida de claves de la Política Criptográfica (E-107) para categoría ALTA. En categoría MEDIA es parcialmente obligatoria.**

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-120"
titulo: "Política de Gestión de Claves Criptográficas"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
clasificacion: "INTERNA"
aprobado_por: "{{ cliente.organo_aprobador_politicas }}"
---

# POLÍTICA DE GESTIÓN DE CLAVES CRIPTOGRÁFICAS DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-120 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Desarrollar en detalle el ciclo de vida completo de las claves criptográficas de {{ cliente.razon_social }}, complementando la Política Criptográfica ({{ proyecto.codigo_documento_base }}-107) con los requisitos operativos para la generación, distribución, almacenamiento, rotación, archivo, revocación y destrucción de claves.

## 2. INVENTARIO DE CLAVES

Se mantendrá un **Inventario de Claves Criptográficas** que registre para cada clave: identificador, tipo (simétrica/asimétrica), algoritmo, longitud, propósito, sistema al que sirve, fecha de generación, fecha de expiración, custodio y estado (activa/expirada/revocada/destruida).

## 3. GENERACIÓN

Las claves se generarán exclusivamente mediante generadores criptográficamente seguros (CSPRNG) o hardware criptográfico dedicado (HSM). Queda prohibida la generación manual o con fuentes de aleatoriedad no verificadas.

## 4. CUSTODIA

| Tipo de clave | Mecanismo de custodia |
|---|---|
| Claves maestras (KEK) | HSM o vault corporativo con control de acceso dual |
| Claves operativas simétricas | Vault cifrado con acceso restringido |
| Claves privadas asimétricas | Almacenadas en el dispositivo destino, nunca exportables sin cifrar |
| Certificados digitales de personal | Dispositivo criptográfico personal (tarjeta inteligente, token USB) |

## 5. ROTACIÓN

| Tipo de clave | Plazo máximo de rotación |
|---|---|
| Claves de sesión TLS | Por sesión |
| Claves operativas (cifrado datos en reposo) | 24 meses |
| Claves de servidor (TLS) | 12 meses |
| Certificados de personal | Conforme al periodo del certificado (máx. 36 meses) |
| Claves maestras (KEK) | 36 meses |

## 6. COMPROMISO

En caso de compromiso o sospecha, se procederá a la revocación inmediata, generación de clave de sustitución, reevaluación de la integridad de la información afectada y gestión como incidente conforme a {{ proyecto.codigo_documento_base }}-108.

## 7. DESTRUCCIÓN

Las claves que dejen de ser necesarias se destruirán de forma irreversible, salvo las que deban conservarse para acceder a información cifrada histórica, que se archivarán en repositorio de claves históricas con controles reforzados.

## 8. APROBACIÓN Y VIGENCIA

Aprobada por {{ cliente.organo_aprobador_politicas }} el {{ proyecto.fecha_aprobacion_inicial }}. Revisión anual.

---

**Documento {{ proyecto.codigo_documento_base }}-120 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---

# DOCUMENTO E-121 — POLÍTICA DE REDES Y COMUNICACIONES

**Materializa mp.com.1 (Perímetro seguro), mp.com.2 (Protección de la confidencialidad), mp.com.3 (Protección de la integridad y autenticidad) y mp.com.4 (Segregación de redes) del Anexo II.**

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-121"
titulo: "Política de Redes y Comunicaciones"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
clasificacion: "INTERNA"
aprobado_por: "{{ cliente.organo_aprobador_politicas }}"
---

# POLÍTICA DE REDES Y COMUNICACIONES DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-121 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Establecer los principios y requisitos de seguridad aplicables al diseño, operación y protección de las redes de comunicaciones de {{ cliente.razon_social }}, en cumplimiento de las medidas **mp.com.1** a **mp.com.4** del Anexo II del Real Decreto 311/2022.

## 2. PRINCIPIOS

**2.1 Perímetro seguro.** Todo punto de entrada y salida de la red corporativa estará controlado por un cortafuegos con política por defecto DENY y reglas explícitas documentadas.

**2.2 Segmentación de redes.** La red se segmentará conforme al principio de mínima exposición, separando al menos: red corporativa, red de servidores, red de gestión, red DMZ, red de invitados. Las redes de mayor criticidad estarán aisladas del acceso directo desde redes menos confiables.

**2.3 Cifrado de comunicaciones.** Conforme a la Política Criptográfica ({{ proyecto.codigo_documento_base }}-107), toda comunicación que transporte información sensible o que atraviese redes no controladas se cifrará con TLS 1.2 o superior (preferentemente TLS 1.3).

**2.4 Protección de integridad.** Los protocolos utilizados incorporarán mecanismos de verificación de integridad (HMAC, firmas digitales) para detectar manipulaciones en tránsito.

**2.5 Monitorización.** El tráfico de red se monitorizará mediante IDS/IPS y se registrará en el SIEM corporativo para la detección de anomalías y la respuesta a incidentes.

## 3. REGLAS DE CORTAFUEGOS

a) Regla por defecto: **DENY ALL** (denegar todo tráfico no expresamente autorizado).

b) Las reglas se documentarán individualmente con: origen, destino, puerto/protocolo, justificación y fecha de autorización.

c) Las reglas se revisarán **semestralmente** para eliminar las obsoletas.

d) Los cambios en reglas de cortafuegos siguen el procedimiento de gestión de cambios ({{ proyecto.codigo_documento_base }}-203).

## 4. REDES INALÁMBRICAS

a) Las redes Wi-Fi corporativas usarán cifrado **WPA3** (o WPA2-Enterprise como mínimo) con autenticación 802.1X.

b) La red de invitados estará completamente aislada de la red corporativa.

c) Se monitorizará la presencia de puntos de acceso no autorizados (rogue APs).

## 5. INTERCONEXIONES CON TERCEROS

Las interconexiones con redes de terceros requerirán autorización del Responsable de la Seguridad, documentación del flujo autorizado, cifrado del canal y monitorización específica.

## 6. APROBACIÓN Y VIGENCIA

Aprobada por {{ cliente.organo_aprobador_politicas }} el {{ proyecto.fecha_aprobacion_inicial }}. Revisión anual.

---

**Documento {{ proyecto.codigo_documento_base }}-121 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---

# DOCUMENTO E-122 — POLÍTICA DE GESTIÓN DE SOPORTES

**Materializa mp.si.1 a mp.si.5 del Anexo II (etiquetado, criptografía, custodia, transporte, borrado de soportes de información).**

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-122"
titulo: "Política de Gestión de Soportes de Información"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
clasificacion: "INTERNA"
aprobado_por: "{{ cliente.organo_aprobador_politicas }}"
---

# POLÍTICA DE GESTIÓN DE SOPORTES DE INFORMACIÓN DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-122 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Establecer las normas aplicables al etiquetado, cifrado, custodia, transporte, reutilización y destrucción de los soportes de información (discos duros, memorias USB, cintas, discos ópticos, documentos en papel) de {{ cliente.razon_social }}, en cumplimiento de las medidas **mp.si.1 a mp.si.5** del Anexo II del Real Decreto 311/2022.

## 2. INVENTARIO

Todo soporte que contenga información del alcance del SGSI se registrará en el inventario de soportes, indicando: tipo, identificador, contenido (nivel de clasificación), custodio, ubicación y fecha de creación.

## 3. ETIQUETADO [mp.si.1]

Los soportes que contengan información CONFIDENCIAL o RESTRINGIDA llevarán etiqueta visible indicando su nivel de clasificación conforme a la Política de Clasificación ({{ proyecto.codigo_documento_base }}-104).

## 4. CIFRADO [mp.si.2]

Los soportes extraíbles que contengan información CONFIDENCIAL o RESTRINGIDA se cifrarán conforme a la Política Criptográfica ({{ proyecto.codigo_documento_base }}-107).

## 5. CUSTODIA [mp.si.3]

Los soportes se custodiarán en condiciones que garanticen su integridad, disponibilidad y confidencialidad, proporcionales a su clasificación. Los soportes con información RESTRINGIDA se guardarán bajo llave con acceso limitado a los custodios autorizados.

## 6. TRANSPORTE [mp.si.4]

El transporte de soportes fuera de las instalaciones de la Entidad requerirá cifrado, embalaje protector, registro de salida conforme al apartado 9 de la Política de Seguridad Física ({{ proyecto.codigo_documento_base }}-123) y, para información RESTRINGIDA, acompañamiento presencial.

## 7. BORRADO Y DESTRUCCIÓN [mp.si.5]

La reutilización o eliminación de soportes se realizará conforme a la Política de Borrado Seguro ({{ proyecto.codigo_documento_base }}-126), garantizando la imposibilidad de recuperación de la información.

## 8. APROBACIÓN Y VIGENCIA

Aprobada por {{ cliente.organo_aprobador_politicas }} el {{ proyecto.fecha_aprobacion_inicial }}. Revisión anual.

---

**Documento {{ proyecto.codigo_documento_base }}-122 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---

# DOCUMENTO E-124 — POLÍTICA DE SEGURIDAD DEL PERSONAL

**Materializa mp.per.1 (Caracterización del puesto de trabajo), mp.per.2 (Deberes y obligaciones), mp.per.3 (Concienciación) y mp.per.4 (Formación) del Anexo II.**

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-124"
titulo: "Política de Seguridad del Personal"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
clasificacion: "INTERNA"
aprobado_por: "{{ cliente.organo_aprobador_politicas }}"
---

# POLÍTICA DE SEGURIDAD DEL PERSONAL DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-124 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Establecer los requisitos de seguridad aplicables al ciclo de vida de la relación de las personas con {{ cliente.razon_social }} (selección, incorporación, desempeño, cambio de funciones y desvinculación), en cumplimiento de las medidas **mp.per.1 a mp.per.4** del Anexo II del Real Decreto 311/2022.

## 2. ANTES DE LA INCORPORACIÓN [mp.per.1]

a) Los puestos de trabajo con acceso a información del alcance del SGSI tendrán documentados sus requisitos de seguridad (accesos necesarios, nivel de habilitación, formación requerida).

b) Los candidatos a puestos con acceso a información CONFIDENCIAL o superior serán objeto de verificación de antecedentes proporcional al riesgo, conforme a la legislación laboral aplicable y con respeto a la normativa de protección de datos.

## 3. DURANTE LA RELACIÓN [mp.per.2, mp.per.3, mp.per.4]

a) Todo el personal firmará un **compromiso de confidencialidad** y un **acuse de recibo** de la Política de Uso Aceptable ({{ proyecto.codigo_documento_base }}-103) como parte de su proceso de incorporación.

b) Se impartirá una **sesión de acogida en seguridad** durante la primera semana, conforme al Plan de Formación (E-PF-001).

c) El personal recibirá **formación y concienciación periódica** conforme al Plan de Formación, con contenidos adaptados a su perfil (técnico, directivo, roles ENS).

d) Los deberes de seguridad se incluirán, cuando sea posible, en la descripción del puesto de trabajo y en los criterios de evaluación del desempeño.

## 4. CAMBIO DE FUNCIONES

Cuando una persona cambie de puesto o funciones, se revisarán sus accesos y privilegios conforme al procedimiento de gestión de identidades ({{ proyecto.codigo_documento_base }}-231), aplicando el principio de mínimo privilegio al nuevo puesto y revocando los accesos del puesto anterior que dejen de ser necesarios.

## 5. DESVINCULACIÓN

Al término de la relación laboral o contractual se aplicará el procedimiento de baja ({{ proyecto.codigo_documento_base }}-201), incluyendo: revocación de accesos, devolución de equipos y soportes, recordatorio de las obligaciones de confidencialidad subsistentes y, cuando proceda, entrevista de salida.

## 6. PERSONAL EXTERNO

Los requisitos de seguridad aplicables al personal externo (contratistas, consultores, becarios) serán equivalentes a los del personal interno con acceso análogo. Las cláusulas de confidencialidad y los requisitos de formación se incluirán en los contratos con los proveedores correspondientes conforme a la Política de Gestión de Proveedores ({{ proyecto.codigo_documento_base }}-112).

## 7. APROBACIÓN Y VIGENCIA

Aprobada por {{ cliente.organo_aprobador_politicas }} el {{ proyecto.fecha_aprobacion_inicial }}. Revisión anual.

---

**Documento {{ proyecto.codigo_documento_base }}-124 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---

# DOCUMENTO E-125 — POLÍTICA DE MESA LIMPIA Y PANTALLA LIMPIA

**Subpolítica operativa de la Política de Uso Aceptable (E-103). Control A.7.7 de ISO/IEC 27001:2022.**

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-125"
titulo: "Política de Mesa Limpia y Pantalla Limpia"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
clasificacion: "INTERNA"
aprobado_por: "{{ cliente.organo_aprobador_politicas }}"
---

# POLÍTICA DE MESA LIMPIA Y PANTALLA LIMPIA DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-125 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Reducir el riesgo de acceso no autorizado, pérdida o daño de la información durante y fuera del horario laboral, mediante la adopción de normas de orden del puesto de trabajo y de protección de la información visible en pantalla.

## 2. NORMAS DE MESA LIMPIA

a) La documentación en papel clasificada como CONFIDENCIAL o RESTRINGIDA se guardará bajo llave al finalizar la jornada o al abandonar el puesto.

b) Los soportes extraíbles (USB, discos) no se dejarán desatendidos sobre la mesa.

c) Las pizarras y notas adhesivas con información sensible se limpiarán al finalizar las reuniones.

d) Las impresoras y fotocopiadoras compartidas se revisarán para retirar documentos olvidados.

e) Los documentos sensibles en espera de destrucción se depositarán en contenedores de destrucción segura, nunca en papeleras ordinarias.

## 3. NORMAS DE PANTALLA LIMPIA

a) La sesión del equipo se bloqueará al abandonar el puesto, aunque sea por un breve periodo. El bloqueo automático se configurará a un máximo de **5 minutos** de inactividad.

b) La información sensible no se dejará visible en pantalla en ausencia del usuario.

c) En reuniones con personas externas, se cerrará cualquier aplicación o documento no relacionado con el objeto de la reunión.

d) Se utilizarán filtros de privacidad en los monitores de los puestos situados en zonas de tránsito o accesibles a visitantes.

## 4. VERIFICACIÓN

El Responsable de la Seguridad podrá realizar verificaciones periódicas no intrusivas del cumplimiento de esta Política, documentando los hallazgos y comunicándolos al personal afectado con carácter educativo.

## 5. APROBACIÓN Y VIGENCIA

Aprobada por {{ cliente.organo_aprobador_politicas }} el {{ proyecto.fecha_aprobacion_inicial }}. Revisión anual.

---

**Documento {{ proyecto.codigo_documento_base }}-125 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---

# DOCUMENTO E-126 — POLÍTICA DE BORRADO SEGURO Y DESTRUCCIÓN DE INFORMACIÓN

**Materializa mp.si.5 del Anexo II y desarrolla la sección 9 de la Política de Clasificación (E-104) sobre destrucción y eliminación.**

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-126"
titulo: "Política de Borrado Seguro y Destrucción de Información"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
clasificacion: "INTERNA"
aprobado_por: "{{ cliente.organo_aprobador_politicas }}"
---

# POLÍTICA DE BORRADO SEGURO Y DESTRUCCIÓN DE INFORMACIÓN DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-126 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Garantizar que la información de {{ cliente.razon_social }} se elimina de forma irreversible cuando deja de ser necesaria, evitando que pueda ser recuperada por personas no autorizadas, en cumplimiento de la medida **mp.si.5 (Borrado y destrucción)** del Anexo II del Real Decreto 311/2022, del artículo 5.1.e) del RGPD (limitación del plazo de conservación) y del artículo 32 de la LOPDGDD (bloqueo previo a la supresión).

## 2. MÉTODOS DE BORRADO Y DESTRUCCIÓN POR TIPO DE SOPORTE

### 2.1 Soportes electrónicos

| Nivel de clasificación | Método admitido |
|---|---|
| PÚBLICA / INTERNA | Borrado lógico (formateo) |
| CONFIDENCIAL | Sobreescritura segura (mínimo 1 pasada con verificación), desmagnetización (degaussing) o cifrado previo con destrucción de clave |
| RESTRINGIDA | Destrucción física del soporte (trituración, incineración) o desmagnetización certificada + sobreescritura |

Para los discos SSD y memorias flash, la sobreescritura simple no garantiza el borrado completo. Se utilizará el comando **ATA Secure Erase** del firmware del disco, o bien la destrucción física del soporte, o bien el borrado criptográfico (cifrar el soporte completo y destruir la clave de cifrado).

### 2.2 Soportes en papel

| Nivel | Método admitido | Nivel DIN 66399 / UNE-EN 15713 |
|---|---|---|
| PÚBLICA / INTERNA | Trituración básica | P-2 |
| CONFIDENCIAL | Trituración con corte cruzado | P-3 |
| RESTRINGIDA | Trituración con corte cruzado fino | P-5 o superior |

### 2.3 Soportes ópticos y cintas

Destrucción física (trituración) conforme al nivel DIN 66399 correspondiente al nivel de clasificación de la información que contienen.

## 3. PROVEEDORES DE DESTRUCCIÓN

Cuando la destrucción se confíe a proveedores especializados, estos deberán cumplir los requisitos de la Política de Gestión de Proveedores ({{ proyecto.codigo_documento_base }}-112) y emitir un **certificado de destrucción** firmado que identifique: los soportes destruidos (número de serie), el método utilizado, la fecha y hora, y la persona responsable del proveedor.

## 4. DATOS PERSONALES — BLOQUEO PREVIO

Conforme al artículo 32 de la LOPDGDD, antes de la supresión definitiva de datos personales se procederá a su **bloqueo** durante el plazo de prescripción de las acciones legales que pudieran derivarse del tratamiento, manteniéndolos a disposición exclusiva de jueces, tribunales, Ministerio Fiscal o Administraciones Públicas competentes.

## 5. REGISTRO DE DESTRUCCIÓN

Toda destrucción de soportes que contengan información CONFIDENCIAL o RESTRINGIDA se documentará en el **Registro de Destrucción**, indicando: soporte destruido, contenido, nivel de clasificación, método utilizado, fecha, persona responsable y, en su caso, referencia al certificado del proveedor.

## 6. APROBACIÓN Y VIGENCIA

Aprobada por {{ cliente.organo_aprobador_politicas }} el {{ proyecto.fecha_aprobacion_inicial }}. Revisión anual.

---

**Documento {{ proyecto.codigo_documento_base }}-126 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---

## RESUMEN DEL BLOQUE 5B

### 12 políticas restantes entregadas

| ID v2.1 | Título | Líneas aprox. | Medidas ENS cubiertas |
|---|---|---|---|
| **E-113** | Adquisición de Tecnología | ~55 | op.pl.3, op.pl.5 (CPSTIC) |
| **E-114** | Desarrollo Seguro (SSDLC) | ~90 | mp.sw.1, mp.sw.2 |
| **E-115** | Gestión de Vulnerabilidades | ~50 | op.exp.4 |
| **E-116** | Gestión de Cambios | ~45 | op.exp.5 |
| **E-117** | Gestión de Privilegios y PAM | ~75 | op.acc.3, op.acc.4 |
| **E-118** | BYOD | ~55 | Condicional |
| **E-120** | Gestión de Claves Criptográficas | ~60 | mp.si.2 (profundizado) |
| **E-121** | Redes y Comunicaciones | ~65 | mp.com.1-4 |
| **E-122** | Gestión de Soportes | ~50 | mp.si.1-5 |
| **E-124** | Seguridad del Personal | ~60 | mp.per.1-4 |
| **E-125** | Mesa Limpia y Pantalla Limpia | ~40 | A.7.7 ISO 27001 |
| **E-126** | Borrado Seguro y Destrucción | ~65 | mp.si.5 + RGPD art. 5.1.e + LOPDGDD art. 32 |

### HITO: 27/27 POLÍTICAS COMPLETADAS ✅

| Bloque | Políticas | Estado |
|---|---|---|
| F1.1+F1.2 originales (renumeradas) | E-100, E-101, E-103, E-104, E-107, E-108, E-109, E-112 | ✅ 8 renumeradas |
| Corrección 5A (nuevas ALTA) | E-102, E-105, E-106, E-110, E-111, E-119, E-123 | ✅ 7 nuevas |
| **Corrección 5B (nuevas MEDIA/BAJA)** | **E-113-E-118, E-120-E-122, E-124-E-126** | **✅ 12 nuevas** |
| **TOTAL** | **27/27** | **100%** |

### Cobertura ENS por familia tras las 27 políticas

| Familia ENS | Cobertura | Políticas que la cubren |
|---|---|---|
| **org** | 100% | E-100, E-116 |
| **op.pl** | 100% | E-100, E-113, E-115 |
| **op.acc** | 100% | E-101, E-102, E-117 |
| **op.exp** | 100% | E-108, E-115, E-116 |
| **op.ext** | 100% | E-112, E-111 |
| **op.cont** | 100% | E-109, E-106 |
| **mp.if** | **100%** | **E-123** (antes 0%) |
| **mp.per** | **100%** | **E-124** (antes 30%) |
| **mp.eq** | 100% | E-103, E-110, E-118 |
| **mp.com** | 100% | E-107, E-121 |
| **mp.si** | 100% | E-107, E-120, E-122 |
| **mp.sw** | **100%** | **E-114** (antes 60%) |
| **mp.info** | 100% | E-104, E-105, E-106, E-107, E-119 |
| **mp.s** | 100% | E-103, E-115 |
| **TOTAL** | **100%** | **Todas las familias del Anexo II cubiertas** |

### Siguiente paso: CORRECCIÓN 6 — los 27 procedimientos nuevos

Con las 27 políticas completas, el siguiente bloque es generar los **27 procedimientos que faltan** para completar 35/35 del catálogo v2.1 §2.7. Esto es el bloque más pesado restante (~4-5 respuestas).

**¿Seguimos con los procedimientos?**
