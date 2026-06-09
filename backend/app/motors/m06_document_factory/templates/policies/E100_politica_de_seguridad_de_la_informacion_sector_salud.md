# DOCUMENTO E-100 — POLÍTICA DE SEGURIDAD DE LA INFORMACIÓN (Sector Salud)

**Variante específica `sector_salud`** alineada con ENS RD 311/2022 +
**art.9 RGPD** (datos categorías especiales) + **Ley 41/2002** (autonomía
del paciente y derechos y obligaciones en materia de información y
documentación clínica) + **LOPDGDD DA1ª y DA7ª** (datos sanitarios) +
**Reglamento UE 2017/745** (productos sanitarios, si aplica). Selecciona
esta variante automáticamente cuando `Project.archetype = sector_salud`
(SAN-D MB-17.6 · ADR-036).

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-100"
titulo: "Política de Seguridad de la Información (Sector Salud)"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
clasificacion: "INTERNA"
propietario: "{{ responsables.responsable_seguridad.cargo }}"
aprobado_por: "{{ cliente.organo_aprobador_politicas }}"
arquetipo: "sector_salud"
---

# POLÍTICA DE SEGURIDAD DE LA INFORMACIÓN DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-100 — Versión {{ proyecto.version_actual }}**
**Variante: Sector Salud**

---

## 1. COMPROMISO DE LA DIRECCIÓN

{{ cliente.razon_social }} establece esta Política de Seguridad de la
Información, alineada con:

- ENS RD 311/2022 (Categoría {{ proyecto.categoria_objetivo }})
- **Art.9 RGPD**: tratamiento de categorías especiales de datos personales
  (salud, datos genéticos, datos biométricos)
- **Ley Orgánica 3/2018 (LOPDGDD)**, Disposiciones Adicionales 1ª y 7ª
- **Ley 41/2002**, básica reguladora de la autonomía del paciente y de
  derechos y obligaciones en materia de información y documentación clínica
- **Reglamento UE 2017/745** (productos sanitarios) cuando aplique

## 2. DATOS DE CATEGORÍAS ESPECIALES (art.9 RGPD)

La Entidad reconoce expresamente que el tratamiento de datos puede incluir:

- Datos relativos a la salud (historiales clínicos, diagnósticos, prescripciones)
- Datos genéticos
- Datos biométricos para identificación inequívoca

### 2.1 Medidas reforzadas obligatorias

| Medida | Descripción |
|---|---|
| Cifrado at-rest | Toda información sanitaria cifrada en reposo · CCN-STIC 807 |
| MFA | Autenticación multifactor obligatoria para acceso a datos clínicos |
| Pseudonimización | Procedimientos de pseudonimización en estudios secundarios |
| Audit log inmutable | Registro inmutable de accesos clínicos · retención 5 años mínimo |
| Consentimiento explícito | Gestión de consentimiento + retirada via portal cliente |
| **DPIA obligatoria** | Evaluación de impacto pre-implantación (art.35 RGPD) |
| DPO/DPF designado | Delegado de Protección de Datos con contacto AEPD |

## 3. MARCO REGULATORIO ADICIONAL

- Cumplimiento estricto de Ley 41/2002 (consentimiento informado, custodia
  de la historia clínica mínima 5 años post-asistencia · 15 años en algunos
  casos · cf. legislación autonómica aplicable)
- Notificación brechas a AEPD en 72h (art.33 RGPD) y, cuando proceda,
  comunicación a los pacientes afectados (art.34 RGPD)
- Coordinación con Comité de Bioética cuando el tratamiento implique
  investigación o estudios clínicos

## 4. RESTO DE CLÁUSULAS GENÉRICAS

> **Nota**: el resto de la política sigue el contenido canónico de la
> versión genérica (`E100_politica_de_seguridad_de_la_informacion.md`).
> Esta variante destaca solo los elementos diferenciales del arquetipo
> Sector Salud · evita duplicación.

```
