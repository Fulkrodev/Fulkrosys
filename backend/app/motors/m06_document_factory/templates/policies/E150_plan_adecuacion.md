# Plan de Adecuación al Esquema Nacional de Seguridad (PdA)

**Cliente**: {{ client_name }}
**Sistema**: {{ system_name }}
**Categoría**: {{ system_category }}
**Versión**: {{ version }} · **Fecha**: {{ today }}

---

## 1. Política de Seguridad aprobada

La presente adecuación se enmarca en la Política de Seguridad de la
Información aprobada formalmente por la Dirección de {{ client_name }}
(referencia E100, versión {{ psi_version }}).

## 2. Información tratada y servicios prestados

### 2.1 Tipos de información

{% for info in information_types %}
- **{{ info.name }}** — {{ info.description }}
{% endfor %}

### 2.2 Servicios prestados

{% for svc in services %}
- **{{ svc.name }}** — {{ svc.description }}
{% endfor %}

## 3. Categoría del sistema (M01 Categorización)

Categorización según RD 311/2022 Anexo I (regla del máximo sobre
dimensiones D-I-C-A-T):

| Dimensión | Nivel | Justificación |
|-----------|-------|---------------|
{% for dim in dimensions %}
| {{ dim.code }} {{ dim.name }} | {{ dim.level }} | {{ dim.justification }} |
{% endfor %}

**Categoría resultante: {{ system_category }}**

## 4. Declaración de Aplicabilidad (M03 DdA)

Total medidas Anexo II evaluadas: **{{ dda_total }}** · de las cuales:

- Aplicables base: {{ dda_aplicables }}
- Aplicables con refuerzos: {{ dda_con_refuerzos }}
- No aplicables (motivo justificado): {{ dda_no_aplica }}

DdA completa disponible en sistema FULKRO (firmable por RSEG).

## 5. Análisis de Riesgos (M02 MAGERIT)

Análisis ejecutado conforme MAGERIT v3 (Libros I/II/III). Inventario
de activos clasificado en 9 categorías canónicas. Total escenarios
de riesgo: {{ risk_scenarios_count }}. Riesgo residual aceptado por
la Dirección al cierre del análisis.

## 6. Insuficiencias detectadas (M04 Gap Analysis)

Análisis de brecha contra las {{ dda_aplicables }} medidas aplicables.

| Familia | Aplicables | Conformes | No conformes | % conformidad |
|---------|-----------:|----------:|-------------:|--------------:|
{% for fam in gap_summary %}
| {{ fam.family }} | {{ fam.aplicables }} | {{ fam.conformes }} | {{ fam.no_conformes }} | {{ fam.pct_conformidad }}% |
{% endfor %}

## 7. Plan de acciones correctivas

{% for task in plan_tasks %}
### {{ task.code }} — {{ task.title }}

- **Medida ENS**: {{ task.ens_measure }}
- **Responsable**: {{ task.responsible_role }}
- **Prioridad**: {{ task.priority }}
- **Esfuerzo estimado**: {{ task.effort_hours }} horas
- **Plazo objetivo**: {{ task.target_date }}
- **Coste estimado**: {{ task.cost_eur }} €
- **Descripción**: {{ task.description }}

{% endfor %}

## 8. Programa de concienciación y formación

{% if training_plan %}
- **Sesiones formativas**: {{ training_plan.sessions_count }}
- **Cobertura personal**: 100% (firma asistencia obligatoria)
- **Frecuencia mínima**: anual
- **Plataforma LMS**: {{ training_plan.lms_provider }}
- **Próxima sesión**: {{ training_plan.next_session_date }}
{% else %}
*Programa de concienciación pendiente de definir vía M16 onboarding.*
{% endif %}

---

## Aprobación

| Rol | Nombre | Firma | Fecha |
|-----|--------|-------|-------|
| Responsable de Seguridad (RSEG) | _____________ | _____________ | _____________ |
| Responsable del Sistema (RSIS) | _____________ | _____________ | _____________ |
| Sponsor / Dirección | _____________ | _____________ | _____________ |

---

*Documento generado por FULKRO conforme CCN-STIC 806 · RD 311/2022.*
*Plantilla E150 · versión {{ template_version }}.*
