# Plan Director de Seguridad (trianual)

**Cliente**: {{ client_name }}
**Periodo**: {{ year_start }} – {{ year_end }}
**Versión**: {{ version }} · **Fecha**: {{ today }}

---

## 1. Misión y visión de la seguridad

### 1.1 Misión

Garantizar la disponibilidad, integridad, confidencialidad,
autenticidad y trazabilidad (CIDAT) de la información y los servicios
electrónicos de {{ client_name }}, conforme al RD 311/2022 (ENS) y
demás normativa aplicable, manteniendo la conformidad continua frente
a auditorías ENAC y obligaciones legales (RGPD, NIS2 si aplica).

### 1.2 Visión

Alcanzar y sostener un nivel de madurez {{ target_maturity_level }}
(CMM {{ target_cmm }}) en las familias críticas del Anexo II en el
horizonte {{ year_end }}, posicionando la organización como referente
en gobernanza de seguridad dentro de su sector.

## 2. Estrategia trianual

### 2.1 Líneas estratégicas

{% for line in strategic_lines %}
- **{{ line.title }}** — {{ line.description }}
{% endfor %}

### 2.2 Hitos por año

| Año | Hito principal | KPI clave |
|-----|---------------|-----------|
| {{ year_start }} | Cierre primera certificación / declaración conformidad | % medidas conformes ≥ {{ kpi_y1 }}% |
| {{ year_start_plus_1 }} | Madurez CMM {{ target_cmm_y2 }} familias prioritarias | Madurez global L{{ kpi_y2_level }} |
| {{ year_end }} | Auditoría externa renovación + INES anual | NC mayores = 0 |

## 3. Inversión planificada

| Año | Capex (€) | Opex (€) | Total (€) |
|-----|----------:|---------:|----------:|
| {{ year_start }} | {{ capex_y1 }} | {{ opex_y1 }} | {{ total_y1 }} |
| {{ year_start_plus_1 }} | {{ capex_y2 }} | {{ opex_y2 }} | {{ total_y2 }} |
| {{ year_end }} | {{ capex_y3 }} | {{ opex_y3 }} | {{ total_y3 }} |

**Inversión trianual total estimada**: {{ total_3y }} €

## 4. KPIs de seguimiento (CCN-STIC 815)

- Disponibilidad servicios críticos: ≥ {{ kpi_disponibilidad }}%
- MTTR incidentes: ≤ {{ kpi_mttr }} h
- Cobertura concienciación: 100% personal anual
- Tasa cumplimiento medidas Anexo II: ≥ {{ kpi_cumplimiento }}%
- Madurez CMM global: ≥ L{{ kpi_madurez }}
- INES anual completado y enviado en plazo

## 5. Responsables alta dirección

| Rol | Nombre | Compromiso |
|-----|--------|-----------|
| Sponsor ejecutivo | {{ sponsor_name }} | Aprobación presupuesto + revisión anual |
| Comité Seguridad | {{ comite_chair }} (presidencia) | Sesiones trimestrales · escalado riesgos |
| Responsable Seguridad (RSEG) | {{ rseg_name }} | Ejecución plan + reporte cuatrimestral |

## 6. Revisión y actualización

El presente Plan Director se revisa anualmente con ocasión de:

- Acta de revisión por la Dirección
- Resultados auditoría externa (Media/Alta)
- Cambios sustanciales (nuevo CPD, fusión, cambio cloud) que disparan
  auditoría extraordinaria art. 31

Las actualizaciones aprobadas se versionan en este documento, manteniendo
trazabilidad de decisiones y firmantes.

---

## Aprobación

| Rol | Nombre | Firma | Fecha |
|-----|--------|-------|-------|
| Sponsor ejecutivo | _____________ | _____________ | _____________ |
| Responsable Seguridad (RSEG) | _____________ | _____________ | _____________ |
| Director General | _____________ | _____________ | _____________ |

---

*Documento generado por FULKRO conforme RD 311/2022 + CCN-STIC 806/815.*
*Plantilla E170 · v{{ template_version }}.*
