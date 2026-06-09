# DOCUMENTO E-224 — PROCEDIMIENTO DE DESPLIEGUE DE SOFTWARE

**Es el procedimiento operativo que materializa la medida mp.sw.2 (aceptación y puesta en producción) y se coordina con el procedimiento de gestión de cambios ({{ proyecto.codigo_documento_base }}-203).** Garantiza que ningún software llega a producción sin haber pasado los controles de calidad, seguridad y aprobación documentados.

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-224"
titulo: "Procedimiento de Despliegue de Software"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
fecha_proxima_revision: "{{ proyecto.proxima_revision }}"
clasificacion: "INTERNA"
propietario: "{{ responsables.responsable_sistema.cargo }}"
politica_madre: "{{ proyecto.codigo_documento_base }}-114, {{ proyecto.codigo_documento_base }}-116"
medidas_ens: ["mp.sw.2", "op.exp.3", "op.exp.5"]
---

# PROCEDIMIENTO DE DESPLIEGUE DE SOFTWARE DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-224 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Establecer las acciones operativas que rigen el despliegue de software en los entornos productivos del alcance del SGSI: validación de la build, criterios de aceptación, ventanas y modalidades de despliegue, rollback y verificación post-despliegue, garantizando trazabilidad y reversibilidad.

Este procedimiento desarrolla las medidas **mp.sw.2 (aceptación y puesta en producción), op.exp.3 (gestión de la configuración) y op.exp.5 (gestión de cambios)** del Anexo II del Real Decreto 311/2022, alineado con la guía CCN-STIC 804.

## 2. ALCANCE

Aplica a todo despliegue de:

- Aplicaciones internas desarrolladas por {{ cliente.razon_social }}.
- Aplicaciones de proveedor (paquetes COTS, SaaS configurable).
- Componentes de infraestructura como código (IaC).
- Imágenes de contenedor y workloads serverless.
- Actualizaciones funcionales (no de seguridad — éstas se rigen por {{ proyecto.codigo_documento_base }}-206).
- Configuraciones de aplicación con impacto funcional (feature flags productivos).

## 3. ENTORNOS Y SU PROPÓSITO

| Entorno | Propósito | Datos | Acceso |
|---|---|---|---|
| **DEV** | Desarrollo individual y de equipo | Sintéticos | Desarrolladores |
| **TEST / QA** | Pruebas funcionales automatizadas y manuales | Sintéticos o anonimizados | Equipo de QA |
| **PRE / STAGE** | Pre-producción isofuncional con producción | Anonimizados o subset productivo enmascarado | Operaciones + QA |
| **PROD** | Producción real | Reales | Personal autorizado, mínimo privilegio |

**Está prohibido** el uso de datos productivos no anonimizados en DEV/TEST. La preparación de datasets para PRE se rige por procedimiento {{ proyecto.codigo_documento_base }}-225 (Pruebas Pre-Producción).

## 4. ROLES Y RESPONSABILIDADES

| Rol | Responsabilidades |
|---|---|
| **Equipo de Desarrollo** | Generar builds firmadas, completar checklist mp.sw, preparar release notes. |
| **Equipo de QA** | Validar suite de pruebas funcionales y de regresión, firmar aceptación funcional. |
| **Responsable de la Seguridad** | Validar checklist de seguridad (SAST, DAST, SCA), aprobar despliegues críticos. |
| **Responsable del Sistema** | Programar y ejecutar el despliegue, validar post-despliegue, gestionar rollback. |
| **CAB (Change Advisory Board)** | Aprobar despliegues estándar / ALTO / EMERGENCIA según el procedimiento {{ proyecto.codigo_documento_base }}-203. |
| **DPO** | Validar despliegues que cambien tratamientos de datos personales o introduzcan nuevos. |

## 5. CATEGORÍAS DE DESPLIEGUE Y FLUJO DE APROBACIÓN

| Categoría | Criterio | Aprobación |
|---|---|---|
| **Estándar — bajo impacto** | Cambio cosmético, parche menor, configuración con impacto < 1 % usuarios | Responsable del Sistema (vía CAB asíncrono) |
| **Estándar — alto impacto** | Nueva funcionalidad relevante, cambio de modelo de datos no destructivo | CAB ordinario semanal |
| **CRÍTICO** | Cambios estructurales, migración de datos, integración nueva con tercero | CAB extraordinario + Responsable de Seguridad |
| **EMERGENCIA** | Corrige incidente activo o vulnerabilidad CRÍTICA con CVSS ≥ 9 | CAB de emergencia (24x7), aprobación retroactiva en 48 h |

{% if proyecto.categoria_ens == "ALTA" %}
**Categoría ALTA:** todo despliegue CRÍTICO requiere prueba previa exitosa en PRE durante una ventana mínima de 5 días naturales y aprobación dual del CAB.
{% endif %}

## 6. FLUJO OPERATIVO

### Fase 1 — Preparación de la build

**Responsable:** Equipo de Desarrollo.

1. Build generada exclusivamente desde el sistema de CI corporativo (no se admiten builds locales en producción).

2. **Checklist de seguridad obligatorio** que el pipeline debe completar:
   - SAST (Semgrep / SonarQube) sin hallazgos `critical` ni `high` no aceptados.
   - SCA de dependencias (Trivy, Snyk, Safety) sin vulnerabilidades CRÍTICAS abiertas.
   - SBOM generado y archivado (CycloneDX o SPDX).
   - Firma criptográfica del artefacto (cosign / sigstore o equivalente).
   - Imágenes de contenedor escaneadas y promovidas solo desde el registro corporativo.

3. **Release notes** del build con: cambios funcionales, cambios de seguridad relevantes, dependencias actualizadas, riesgos conocidos, plan de rollback.

### Fase 2 — Validación QA y PRE

**Responsable:** Equipo de QA con apoyo de Operaciones.

4. Despliegue automatizado a TEST. Ejecución de suite funcional y de regresión.

5. Despliegue automatizado a PRE. Pruebas de integración y carga conforme a {{ proyecto.codigo_documento_base }}-225.

6. **Pruebas de seguridad dinámicas (DAST)** en PRE para cambios que afecten a la superficie expuesta (nuevos endpoints, nuevos campos de entrada).

7. **Validación de privacidad:** si el cambio introduce o modifica un tratamiento de datos personales, validación del DPO con actualización del RAT.

8. Acta de aceptación firmada por QA y por el propietario funcional.

### Fase 3 — Aprobación CAB

**Responsable:** CAB conforme al apartado 5.

9. Solicitud al CAB con:
   - Identificador de cambio (`CHG-AAAA-NNNN`).
   - Categoría.
   - Ventana propuesta (apartado 7).
   - Plan de despliegue y rollback.
   - Análisis de impacto en seguridad.
   - Comunicaciones a usuarios y partes interesadas.

10. La aprobación queda registrada en el sistema de gestión de cambios. Sin aprobación vigente, el despliegue no se ejecuta.

### Fase 4 — Despliegue en PROD

**Responsable:** Responsable del Sistema.

11. **Modalidades disponibles** (a seleccionar según la naturaleza del cambio):

| Modalidad | Descripción | Ventaja principal |
|---|---|---|
| **Big-bang** | Sustitución completa en ventana | Simplicidad |
| **Blue-green** | Despliegue paralelo, swap atómico | Rollback inmediato |
| **Canary** | Despliegue progresivo a un % de tráfico | Detección temprana |
| **Rolling** | Despliegue por nodos sucesivos | Sin tiempo de caída |
| **Feature flag** | Código desplegado, funcionalidad oculta hasta activación | Desacoplar despliegue de release |

12. **Ventanas de despliegue por defecto:** {{ proyecto.ventana_despliegue | default("martes y jueves de 10:00 a 12:00 horas") }}, salvo categoría EMERGENCIA. Despliegues en viernes, vísperas de festivo, fines de semana o cierres contables: prohibidos salvo aprobación expresa.

13. **Verificación durante el despliegue:** monitorización de métricas de salud (latencia, error-rate, saturación, throughput) en dashboard del SIEM/observabilidad. Cualquier deterioro > 10 % respecto a la línea base es señal de revertir.

### Fase 5 — Validación post-despliegue (T+0 a T+24 h)

**Responsable:** Responsable del Sistema con validación funcional del propietario.

14. **Smoke tests automatizados** del pipeline ejecutados inmediatamente tras el despliegue.

15. **Validación funcional manual** de los flujos de mayor criticidad por el propietario funcional.

16. **Hipercare** durante 24 horas (cambios estándar) o 72 horas (CRÍTICO): monitorización reforzada, capacidad de rollback inmediato, equipo de guardia identificado.

17. Cierre del cambio en CAB con resultado: EXITOSO / EXITOSO CON OBSERVACIONES / REVERTIDO.

### Fase 6 — Rollback

Si la verificación falla:

18. Se ejecuta el plan de rollback documentado en la solicitud, restaurando el estado previo en máximo:
    - 15 minutos para blue-green / canary.
    - 1 hora para rolling.
    - Hasta el RTO del activo en big-bang con migración de datos (peor caso).

19. La reversión genera **incidente operativo** (no necesariamente de seguridad) y se analiza en el siguiente CAB con identificación de causa raíz y lecciones aprendidas.

## 7. CASOS ESPECIALES

### 7.1. Software de proveedor (COTS / SaaS)

- Verificación previa del CVE-status del proveedor (disclosure responsable).
- Lectura crítica de las release notes del proveedor.
- Pruebas en PRE con la versión exacta a desplegar.
- Si es SaaS sin entorno PRE, el cliente exige al proveedor una **ventana de prueba** o un **canary** segregado.

### 7.2. Despliegues por proveedor externo

- El proveedor solo despliega bajo supervisión del Responsable del Sistema.
- Se utiliza cuenta nominativa con grabación de sesión.
- El proveedor no recibe credenciales productivas; opera vía bastion host.

### 7.3. IaC (Terraform, Pulumi, Crossplane)

- Toda modificación de IaC sigue el mismo flujo: PR revisado, plan automatizado, aplicación supervisada.
- Drift entre el código y la realidad se detecta semanalmente y se reconcilia mediante PR.

## 8. REGISTROS GENERADOS

| Código | Registro | Conservación |
|---|---|---|
| CHG-* | Solicitud de Cambio (CAB) | 6 años |
| R-224.1 | Acta de aceptación QA / PRE | 3 años |
| R-224.2 | Acta de despliegue (resultado) | 3 años |
| L-224 | Log técnico del despliegue | 12 meses |
| SBOM-* | Software Bill of Materials por release | Vigente + 3 años |

## 9. INDICADORES (KPI)

| Indicador | Fórmula | Objetivo |
|---|---|---|
| % despliegues exitosos | exitosos / total | ≥ 95 % |
| % despliegues revertidos | revertidos / total | ≤ 3 % |
| Lead time desde commit a producción | media | ≤ 7 días para estándar |
| MTTR ante despliegue fallido | media | ≤ 30 min |
| Cobertura SAST/SCA en pipeline | builds con escaneo / total | 100 % |
| Despliegues fuera de ventana sin aprobación | recuento | 0 |

## 10. REVISIÓN

Este procedimiento se revisa **anualmente** o cuando:

- Se modifique la guía CCN-STIC 804 en lo relativo a mp.sw.2 / op.exp.3 / op.exp.5.
- Se adopte una nueva plataforma de CI/CD.
- Se incorpore una nueva modalidad de despliegue en la organización.
- Se detecten incidentes recurrentes ligados al proceso de despliegue.

Responsabilidad: **Responsable del Sistema** con visto bueno del **Responsable de la Seguridad** y aprobación del **Comité de Seguridad**.
