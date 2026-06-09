# DOCUMENTO E-227 — PROCEDIMIENTO DE USO DE CLOUD

**Es el procedimiento operativo que ejecuta la Política de Uso de Servicios Cloud ({{ proyecto.codigo_documento_base }}-111) y materializa la medida op.nub.1.** Define cómo se aprueban, contratan, configuran, monitorizan y dan de baja los servicios cloud utilizados por {{ cliente.razon_social }}.

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-227"
titulo: "Procedimiento de Uso de Cloud"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
fecha_proxima_revision: "{{ proyecto.proxima_revision }}"
clasificacion: "INTERNA"
propietario: "{{ responsables.responsable_sistema.cargo }}"
politica_madre: "{{ proyecto.codigo_documento_base }}-111"
medidas_ens: ["op.nub.1", "op.ext.1", "op.ext.2", "mp.info.3"]
---

# PROCEDIMIENTO DE USO DE CLOUD DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-227 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Establecer las acciones operativas para la adopción, configuración, supervisión y baja de los servicios en la nube (IaaS, PaaS, SaaS) utilizados en el alcance del SGSI de {{ cliente.razon_social }}, garantizando el cumplimiento del Esquema Nacional de Seguridad, del RGPD y de los Perfiles de Cumplimiento Específico (PCE) aplicables.

Este procedimiento desarrolla la medida **op.nub.1 (protección de servicios en la nube)** del Anexo II del Real Decreto 311/2022 conforme a la guía CCN-STIC 823 (Cloud) y al PCE de proveedor cloud aprobado por el CCN.

## 2. ALCANCE

Aplica a:

- IaaS (AWS EC2, Azure VM, GCP Compute Engine).
- PaaS (Azure App Service, AWS Elastic Beanstalk, Google App Engine, bases de datos gestionadas, almacenamiento S3/Blob/GCS).
- SaaS corporativo (Microsoft 365, Google Workspace, CRM, ERP, herramientas de colaboración).
- FaaS (Lambda, Azure Functions, Cloud Functions).
- Servicios de IA generativa de proveedor cloud cuando traten información del alcance.

## 3. PROVEEDORES APROBADOS

| Proveedor | Servicios admitidos | Categoría ENS máxima |
|---|---|---|
| **AWS** (regiones UE-WEST y UE-CENTRAL) | IaaS, PaaS, SaaS gestionado | ALTA con PCE-AWS-ENS |
| **Microsoft Azure** (regiones UE) | IaaS, PaaS, M365 | ALTA con PCE-Azure-ENS |
| **Google Cloud** (regiones UE) | IaaS, PaaS, Workspace | MEDIA / ALTA según servicio |
| **OVHcloud** | IaaS, PaaS | ALTA con configuración específica |
| **Otros proveedores UE** | Caso a caso, requiere aprobación expresa | A evaluar |

{% if proyecto.categoria_ens == "ALTA" %}
**Categoría ALTA:** la información debe procesarse y almacenarse exclusivamente en regiones de la Unión Europea, con cifrado de claves gestionadas por el cliente (CMK / BYOK / HYOK) y compromiso contractual de no acceso por jurisdicciones extracomunitarias salvo orden judicial española.
{% endif %}

## 4. ROLES Y RESPONSABILIDADES

| Rol | Responsabilidades |
|---|---|
| **Cloud Architect / Responsable Cloud** | Diseñar la arquitectura, mantener landing zone corporativa, gestionar IaC. |
| **Responsable del Sistema** | Operación diaria, monitorización, gestión de costes. |
| **Responsable de la Seguridad** | Validar arquitecturas, aprobar nuevos servicios, supervisar postura de seguridad. |
| **DPO** | Validar tratamientos de datos personales, transferencias internacionales, contratos Art. 28. |
| **Compras / Legal** | Negociar contrato y cláusulas ENS/RGPD/DPA. |
| **FinOps** | Gobernar costes, alertas de gasto, optimización. |

## 5. CICLO DE VIDA DEL SERVICIO CLOUD

### Fase 1 — Solicitud y aprobación

1. El área solicitante presenta el formulario **F-227.1 — Solicitud de Servicio Cloud** con:
   - Servicio solicitado, proveedor, región.
   - Tipos de datos a tratar (clasificación, datos personales, categoría especial).
   - Volumen estimado y criticidad.
   - Justificación funcional.
   - Coste estimado.

2. El Responsable Cloud evalúa la viabilidad técnica.
3. El Responsable de Seguridad evalúa la idoneidad respecto a la categoría ENS y los riesgos derivados.
4. El DPO valida los aspectos de privacidad si hay datos personales.
5. La aprobación final se gestiona por el procedimiento {{ proyecto.codigo_documento_base }}-203 (cambios) cuando el servicio es nuevo en la organización.

### Fase 2 — Contratación

6. Negociación del contrato con cláusulas mínimas:
   - Compromiso de cumplimiento del PCE aplicable o equivalencias (ISO 27001 + 27017 + 27018 + 27701).
   - Localización de los datos (regiones UE) y ausencia de transferencias automáticas a terceros países.
   - Sub-encargados declarados (cláusulas RGPD Art. 28).
   - Notificación de incidentes ≤ 24 horas.
   - Derecho de auditoría documental anual y presencial cada 3 años para servicios CRÍTICO/ALTO.
   - Gestión de claves: BYOK / HYOK / CMK.
   - Plan de salida: portabilidad de datos en formatos estándar y borrado certificado tras la baja.

### Fase 3 — Configuración (landing zone)

7. **Cuentas / suscripciones / proyectos** segregadas por entorno (PROD/PRE/TEST/DEV) y, opcionalmente, por unidad de negocio.

8. **Identidad federada** con el IdP corporativo. **MFA obligatorio** para todos los accesos. Cuentas raíz/owner con custodia especial.

9. **Configuración base obligatoria** validada por herramientas automatizadas (Prowler con perfil ENS, ScoutSuite, Cloud Custodian):

   - Cifrado en reposo activado en todos los servicios de almacenamiento.
   - Cifrado en tránsito (TLS 1.2+) para todas las APIs y endpoints expuestos.
   - Logging completo activado y centralizado en SIEM ({{ proyecto.codigo_documento_base }}-223).
   - Network segmentation con principio de mínimo privilegio.
   - WAF en cargas web públicas.
   - Backup nativo conforme a {{ proyecto.codigo_documento_base }}-207.
   - Versioning + protección frente a borrado en buckets críticos.
   - Bloqueo de creación de recursos con configuraciones inseguras (Service Control Policies, Azure Policy, Org Policies).

10. **IaC obligatorio** para toda recurso productivo (Terraform / CloudFormation / Bicep / Pulumi). Cambios manuales en consola están prohibidos salvo emergencia documentada.

### Fase 4 — Operación y supervisión

11. **Monitorización continua de la postura de seguridad** (Cloud Security Posture Management):
    - Auditorías Prowler con perfil ENS — semanal automatizada, mensual con revisión humana.
    - ScoutSuite trimestral.
    - Métricas en cuadro de mando con remediación priorizada.

12. **Detección de anomalías:** uso de los servicios nativos del proveedor (GuardDuty, Defender for Cloud, Security Command Center) integrados con el SIEM.

13. **Gobernanza de costes (FinOps):**
    - Etiquetado obligatorio de recursos (cost-center, owner, environment, data-class).
    - Alertas de gasto al 80 % y al 100 % del presupuesto mensual por unidad.
    - Revisión mensual con propietarios.

14. **Revisión de configuraciones IAM** trimestral conforme a {{ proyecto.codigo_documento_base }}-210.

### Fase 5 — Cambios significativos

15. Los cambios significativos en la arquitectura cloud (nueva región, cambio de modelo de cifrado, salida de proveedor, fusión/escisión) se canalizan por el CAB conforme a {{ proyecto.codigo_documento_base }}-203 con análisis de impacto de privacidad si afecta a datos personales.

### Fase 6 — Baja del servicio

16. Plan de salida ejecutado:
    - Exportación de datos en formato estándar (CSV/JSON/Parquet, según naturaleza).
    - Borrado certificado de los datos en el proveedor (DSAR / certificado ad-hoc).
    - Revocación de credenciales del cliente y del proveedor.
    - Cierre formal del servicio en el inventario.
    - Notificación al DPO si afectaba a tratamientos.

## 6. GESTIÓN DE INCIDENTES EN CLOUD

- Los incidentes detectados en cloud se canalizan por el procedimiento {{ proyecto.codigo_documento_base }}-204.
- Para incidentes que afecten al proveedor (caída regional, brecha en su perímetro), aplican los procedimientos del proveedor con seguimiento por parte del Responsable Cloud.
- En caso de **brecha de datos personales originada por el proveedor**, éste debe notificar en 24 horas conforme al contrato; el cliente notifica a la AEPD en 72 horas conforme a {{ proyecto.codigo_documento_base }}-213.

## 7. CONSIDERACIONES ESPECÍFICAS

### 7.1. Servicios SaaS de proveedor único

- Validación inicial mediante el cuestionario F-216.2.
- Limitación de la información a INTERNA salvo contrato específico.
- Configuración de exportación periódica de datos al backup corporativo.

### 7.2. Servicios de IA generativa

- Prohibido enviar a IA generativa pública información clasificada como CONFIDENCIAL o superior, ni datos personales, ni código fuente protegido por IPR.
- Solo se autorizan instancias enterprise del proveedor con compromiso de no entrenamiento con los datos del cliente y tratamiento dentro de la UE.

### 7.3. Multi-cloud

- Documentación obligatoria de la dependencia de cada componente con cada proveedor.
- Plan de continuidad ante caída regional / proveedor para servicios CRÍTICOS.

## 8. REGISTROS GENERADOS

| Código | Registro | Conservación |
|---|---|---|
| F-227.1 | Solicitud de Servicio Cloud | 6 años |
| INV-cloud | Inventario de Servicios Cloud | Permanente |
| R-227.1 | Informes Prowler / ScoutSuite | 24 meses |
| R-227.2 | Actas de revisión mensual | 3 años |
| R-227.3 | Plan de Salida por proveedor | Vigente + 6 años |

## 9. INDICADORES (KPI)

| Indicador | Fórmula | Objetivo |
|---|---|---|
| % servicios con configuración Prowler/ENS conforme | conformes / total | ≥ 95 % |
| Hallazgos críticos cloud abiertos | recuento | 0 |
| Cobertura IaC (recursos productivos) | recursos en IaC / total | ≥ 90 % |
| % servicios con plan de salida documentado | con plan / total CRITICOS | 100 % |
| Tiempo medio de remediación de findings ALTOS | media días | ≤ 30 |

## 10. REVISIÓN

Este procedimiento se revisa **anualmente** o cuando:

- Cambie el PCE de proveedor cloud aprobado por el CCN.
- Se incorpore un nuevo proveedor cloud.
- Cambien las medidas op.nub.1 o las guías CCN-STIC asociadas.
- Se publique nuevo régimen UE sobre soberanía digital aplicable.

Responsabilidad: **Responsable Cloud** + **Responsable de la Seguridad**, con aprobación del **Comité de Seguridad**.
