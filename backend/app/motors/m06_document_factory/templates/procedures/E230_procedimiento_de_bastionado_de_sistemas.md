# DOCUMENTO E-230 — PROCEDIMIENTO DE BASTIONADO DE SISTEMAS

**Es el procedimiento operativo que materializa la medida op.exp.2 (configuración de seguridad).** Define cómo se construyen, aplican y verifican las líneas base (baselines) de hardening en sistemas operativos, contenedores y dispositivos de red.

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-230"
titulo: "Procedimiento de Bastionado de Sistemas"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
fecha_proxima_revision: "{{ proyecto.proxima_revision }}"
clasificacion: "INTERNA"
propietario: "{{ responsables.responsable_sistema.cargo }}"
politica_madre: "{{ proyecto.codigo_documento_base }}-100"
medidas_ens: ["op.exp.2", "op.exp.3", "mp.eq.1"]
---

# PROCEDIMIENTO DE BASTIONADO DE SISTEMAS DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-230 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Establecer las acciones operativas para definir, aplicar, verificar y mantener las líneas base de configuración segura (hardening baselines) de los sistemas que forman parte del alcance del SGSI de {{ cliente.razon_social }}, asegurando que toda nueva instancia se despliega ya bastionada y que las desviaciones se detectan y remedian de forma sistemática.

Este procedimiento desarrolla las medidas **op.exp.2 (configuración de seguridad), op.exp.3 (gestión de la configuración) y mp.eq.1 (puesto de trabajo)** del Anexo II del Real Decreto 311/2022, alineado con la guía CCN-STIC 804 y con las guías específicas de la serie 599-617 (Windows, Linux) y 836-887 (firewalls y cloud).

## 2. ALCANCE

Aplica a las líneas base de:

- **Sistemas operativos servidor:** Windows Server (CCN-STIC 599 / 580), Linux distribuciones soportadas (CCN-STIC 617 para Ubuntu LTS, equivalentes para RHEL/Debian).
- **Sistemas operativos cliente:** Windows 10/11 corporativos (CCN-STIC 599), macOS, Linux desktop si se utiliza.
- **Dispositivos móviles:** iOS y Android conforme a {{ proyecto.codigo_documento_base }}-228.
- **Hipervisores y plataformas de virtualización:** VMware, Hyper-V, KVM.
- **Contenedores y orquestadores:** imágenes base, Kubernetes (CIS Benchmarks).
- **Dispositivos de red:** firewalls (CCN-STIC 836), switches, routers, balanceadores, WAF.
- **Servicios cloud:** baselines en AWS/Azure/GCP conforme a {{ proyecto.codigo_documento_base }}-227.

## 3. PRINCIPIOS DE BASTIONADO

1. **Mínima superficie:** desactivar servicios, puertos, protocolos, cuentas y funciones que no sean necesarios para la operación.
2. **Mínimo privilegio:** los servicios se ejecutan con la cuenta de menor privilegio posible.
3. **Defensa en profundidad:** combinación de controles preventivos, detectivos y correctivos.
4. **Reproducibilidad:** las baselines son código (Ansible, Chef, Puppet, GPO, IaC). Las modificaciones manuales están prohibidas en producción.
5. **Verificable:** existen pruebas automatizadas que comprueban el estado del sistema frente a la baseline (Wazuh SCA, OpenSCAP, Inspec).

## 4. CATÁLOGO DE BASELINES

| Plataforma | Referencia base | Personalización corporativa |
|---|---|---|
| Windows Server 2019/2022 | CCN-STIC 599 + CIS Level 1 | Anexo I-W2022 |
| Windows 10/11 corporativo | CCN-STIC 599 + CIS Level 1 | Anexo I-W11 |
| Ubuntu LTS Server | CCN-STIC 617 + CIS Level 1 | Anexo I-UB |
| RHEL/Rocky | CIS RHEL Level 1 | Anexo I-RHEL |
| Kubernetes | CIS Kubernetes Benchmark | Anexo I-K8S |
| Imágenes Docker | CIS Docker Benchmark + Distroless | Anexo I-CONT |
| Microsoft 365 | CCN-STIC 453 + CIS M365 | Anexo I-M365 |
| Azure | CCN-STIC 457 + CIS Azure | Anexo I-AZ |
| AWS | CCN-STIC 887 + CIS AWS | Anexo I-AWS |
| GCP | CIS GCP | Anexo I-GCP |
| Firewalls perimetrales | CCN-STIC 836 + guía del fabricante | Anexo I-FW |
| WiFi corporativo | CCN-STIC 844 | Anexo I-WIFI |

{% if proyecto.categoria_ens == "ALTA" %}
**Categoría ALTA:** las baselines aplicadas son **CIS Level 2** (cuando exista) o equivalente, y los componentes críticos utilizan productos del catálogo CCN-STIC siempre que esté disponible una alternativa adecuada.
{% endif %}

## 5. ROLES Y RESPONSABILIDADES

| Rol | Responsabilidades |
|---|---|
| **Arquitectos de Plataforma** | Mantener las baselines, evaluar nuevas versiones, gestionar excepciones de plataforma. |
| **Administradores de Sistemas** | Aplicar las baselines, gestionar el ciclo de vida de los sistemas, remediar desviaciones. |
| **Responsable de la Seguridad** | Aprobar las baselines, validar excepciones, supervisar el cumplimiento. |
| **Equipo de DevOps / Plataforma** | Integrar las baselines en pipelines IaC y golden images. |

## 6. FLUJO OPERATIVO

### Fase 1 — Definición y aprobación de la baseline

1. El Arquitecto de Plataforma desarrolla / actualiza la baseline tomando como referencia la guía CCN-STIC aplicable y, en su caso, los CIS Benchmarks vigentes.

2. La baseline incluye:
   - Configuraciones del sistema operativo (políticas de cuentas, auditoría, servicios, registro).
   - Configuraciones de red local (firewall de host, IPv6 si no se usa, WPAD, SMBv1 deshabilitado, etc.).
   - Hardening de servicios típicos de la plataforma.
   - Telemetría requerida (Sysmon en Windows, auditd en Linux) integrada con SIEM ({{ proyecto.codigo_documento_base }}-223).
   - Agente EDR y agente SCA preinstalados.

3. Validación en laboratorio: aplicación a una instancia de prueba y batería de pruebas funcionales y de seguridad.

4. Aprobación formal por el Responsable de la Seguridad y publicación en el repositorio de baselines.

### Fase 2 — Aplicación de la baseline

5. **Nuevos sistemas:** la baseline forma parte de la **golden image** o del despliegue automatizado (Packer, Terraform + cloud-init, Kubernetes admission controllers). Ningún sistema entra en producción sin la baseline aplicada.

6. **Sistemas existentes:** ventana de migración planificada con el procedimiento {{ proyecto.codigo_documento_base }}-203 (cambios). Aplicación progresiva con verificación post-cambio.

7. **Configuraciones específicas por rol:** sobre la baseline base se aplican capas adicionales (rol web, rol BD, rol bastion) gestionadas por inventario de configuración (Ansible, Puppet, Chef, DSC).

### Fase 3 — Verificación de cumplimiento (SCA)

8. **Diariamente** los agentes SCA (Wazuh, Defender for Endpoint, OpenSCAP scheduler, Compliance Scanner) verifican el estado del sistema frente a la baseline. Los hallazgos se envían al SIEM y al cuadro de mando.

9. **Semanalmente** se ejecutan escaneos no autenticados externos para detectar configuraciones expuestas (Nmap, Nuclei) sobre los segmentos relevantes.

10. **Mensualmente** se publica el **Informe de Cumplimiento de Hardening** con:
    - % de sistemas conformes por plataforma.
    - Top desviaciones más frecuentes.
    - Acciones de remediación con responsable y plazo.

### Fase 4 — Remediación

11. Las desviaciones se categorizan:
    - **Críticas** (servicio expuesto sin justificación, autenticación deshabilitada, parche crítico ausente): remediación en **24 horas**.
    - **Altas:** 7 días.
    - **Medias:** 30 días.
    - **Bajas:** próxima ventana de mantenimiento.

12. Si la desviación está justificada, se canaliza al procedimiento de excepciones {{ proyecto.codigo_documento_base }}-222.

### Fase 5 — Mantenimiento de la baseline

13. **Revisión trimestral** ordinaria para incorporar cambios menores.

14. **Revisión anual** completa coincidiendo con la actualización de las guías CCN-STIC y CIS Benchmarks.

15. **Revisión extraordinaria** ante:
    - Publicación de un nuevo PCE o guía relevante.
    - Vulnerabilidad pública crítica que exija nueva configuración.
    - Cambio significativo en la versión del sistema operativo.

16. Cada nueva versión de la baseline se versiona, se publica con changelog y se comunica al equipo de operaciones.

## 7. CASOS ESPECIALES

### 7.1. Sistemas legacy

Sistemas que no admiten la baseline completa por dependencias funcionales:

- Documentación expresa en {{ proyecto.codigo_documento_base }}-222 con plan de migración.
- Compensaciones técnicas (segmentación reforzada, vigilancia adicional, restricción de acceso).
- Plazo máximo de tolerancia: 18 meses, salvo aprobación expresa del Comité de Seguridad.

### 7.2. Imágenes públicas (Marketplace cloud)

- Verificación previa a uso (escaneo de la imagen).
- Aplicación de capa de bastionado encima.
- Preferencia por imágenes mantenidas por el proveedor cloud o por Bitnami / verificadas, frente a imágenes comunitarias.

### 7.3. Equipos OT / industriales

- Las baselines OT se desarrollan separadamente con criterios IEC 62443 y la guía CCN-STIC 480.
- No se aplican baselines IT a sistemas OT sin validación del fabricante.

## 8. REGISTROS GENERADOS

| Código | Registro | Conservación |
|---|---|---|
| BASE-* | Baselines versionadas | Permanente |
| R-230.1 | Informe Mensual de Cumplimiento | 3 años |
| R-230.2 | Acta trimestral de revisión de baselines | 6 años |
| L-230 | Logs SCA en SIEM | conforme {{ proyecto.codigo_documento_base }}-223 |
| F-230 | Solicitudes de excepción ligadas a hardening | enlace con R-222 |

## 9. INDICADORES (KPI)

| Indicador | Fórmula | Objetivo |
|---|---|---|
| % sistemas conformes con baseline | conformes / total inventariados | ≥ 95 % |
| Sistemas críticos no conformes > 24 h | recuento | 0 |
| Tiempo medio de remediación de desviaciones críticas | media horas | ≤ 24 |
| Cobertura SCA en endpoints | con SCA / total | ≥ 98 % |
| Desviaciones por sistema (media) | total desviaciones / sistemas | ≤ 5 |

## 10. REVISIÓN

Este procedimiento se revisa **anualmente** o cuando:

- Cambien las medidas op.exp.2 / op.exp.3 / mp.eq.1 en CCN-STIC 804.
- Se publiquen nuevas versiones mayores de las guías CCN-STIC de hardening.
- Se incorporen nuevas plataformas al alcance.
- Se detecten patrones de no conformidad sistemáticos.

Responsabilidad: **Arquitectos de Plataforma** + **Responsable del Sistema**, con aprobación del **Responsable de la Seguridad**.
