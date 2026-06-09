# DOCUMENTO E-100 — POLÍTICA DE SEGURIDAD DE LA INFORMACIÓN (Desarrollador AAPP)

**Variante específica `desarrollador_aapp`** para entidades que desarrollan
software/SaaS para Administraciones Públicas. Selecciona esta variante
automáticamente cuando `Project.archetype = desarrollador_aapp`
(SAN-D MB-17.6 · ADR-036). Marco ENS RD 311/2022 +
**Reglamento UE 2024/2847 (CRA · Cyber Resilience Act)** + **mp.sw
reforzado** (refuerzo R1 mínimo · R2 si producto digital con elementos
electrónicos).

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-100"
titulo: "Política de Seguridad de la Información (Desarrollador AAPP)"
version: "{{ proyecto.version_actual }}"
clasificacion: "INTERNA"
arquetipo: "desarrollador_aapp"
---

# POLÍTICA DE SEGURIDAD DE LA INFORMACIÓN DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-100 — Versión {{ proyecto.version_actual }}**
**Variante: Desarrollador para AAPP**

---

## 1. DOBLE CUMPLIMIENTO ENS + CRA

El software desarrollado para Administraciones Públicas requiere doble
cumplimiento:

- **ENS** aplicable a la entidad desarrolladora (si presta servicios
  digitales a AAPP, art.1 RD 311/2022)
- **Cyber Resilience Act** (Reglamento UE 2024/2847) si el producto
  contiene elementos digitales (IoT, software firmware, plataformas)
- **SDLC seguro reforzado** (medida `mp.sw Aplicaciones informáticas`
  con refuerzo R1 mínimo)
- Conformidad de medidas `mp.sw` del producto entregado a la AAPP cliente

## 2. SDLC SEGURO · medidas mínimas mp.sw + CRA

| Control | Implementación |
|---|---|
| **SAST** | Análisis estático de seguridad en CI/CD pre-merge |
| **DAST** | Análisis dinámico en entorno staging pre-release |
| **SCA** | Software Composition Analysis · vulnerabilidades terceros (CVSS) |
| **Code review** | Obligatorio · 2 aprobadores mínimo · checklist seguridad |
| **Threat modeling** | Per release mayor · STRIDE / PASTA |
| **Pentesting** | Pre-go-live productos críticos AAPP |
| **Bug bounty** | Programa activo si producto crítico · responsabilidad CRA |
| **SBOM** | Software Bill of Materials publicado (CRA art.13) |
| **Patch management** | Soporte mínimo de 5 años post-release (CRA Anexo I) |

## 3. CONFORMIDAD PRODUCTO AAPP

- Cláusulas contractuales con la AAPP cliente que documentan:
  - Categoría ENS objetivo del producto entregado
  - Controles `mp.sw` implementados
  - Plan de mantenimiento y respuesta a vulnerabilidades

- Reporte trimestral de vulnerabilidades resueltas
- Certificación CCN-STIC del producto cuando proceda (CPSTIC catálogo)

## 4. RESTO DE CLÁUSULAS GENÉRICAS

> **Nota**: el resto de la política mantiene el contenido canónico de la
> versión genérica · esta variante destaca el arquetipo Desarrollador AAPP
> sin duplicar texto base.

```
