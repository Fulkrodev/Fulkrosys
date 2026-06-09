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

d) **Pentesting:** para aplicaciones críticas, test de intrusión específico realizado por personal cualificado conforme al procedimiento de pentesting aplicable.

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
