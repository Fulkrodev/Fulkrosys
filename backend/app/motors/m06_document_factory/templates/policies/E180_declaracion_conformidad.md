# Declaración de Conformidad con el Esquema Nacional de Seguridad (Categoría Básica)

**Cliente**: {{ client_name }}
**CIF**: {{ client_cif }}
**Sistema**: {{ system_name }}
**Categoría**: {{ system_category }}
**Identificador certificado**: {{ cert_id }}
**Fecha de emisión**: {{ today }}
**Vigencia**: 2 años (vencimiento {{ expiry_date }})

---

## 1. Identificación de la entidad

{{ client_name }} ({{ client_cif }}), con domicilio en {{ client_domicilio }},
declara haber cumplido los requisitos del Esquema Nacional de Seguridad
(RD 311/2022) en la **Categoría {{ system_category }}**, conforme al
procedimiento de autoevaluación previsto en CCN-STIC 809 para sistemas
clasificados como BÁSICA.

## 2. Sistema certificado y alcance

- **Sistema**: {{ system_name }}
- **Servicios prestados**: {{ services_summary }}
- **Tipos de información**: {{ information_summary }}
- **Inventario activos esenciales**: {{ assets_essential_count }}
- **Periodo de la declaración**: {{ today }} – {{ expiry_date }}

## 3. Categoría del sistema

Conforme al RD 311/2022 Anexo I (regla del máximo aplicada sobre las
dimensiones D-I-C-A-T), el sistema {{ system_name }} se ha clasificado
como **Categoría {{ system_category }}**.

## 4. Resultado de la autoevaluación

Total medidas Anexo II evaluadas: **{{ dda_total }}**

- Aplicables (base): {{ dda_aplicables }}
- Aplicables con refuerzos: {{ dda_con_refuerzos }}
- No aplicables (justificadas): {{ dda_no_aplica }}
- Conformes: {{ conformes_count }}
- No conformes: {{ no_conformes_count }}
- Porcentaje conformidad: {{ pct_conformidad }}%

La Declaración de Aplicabilidad (DdA) firmada por el Responsable de
Seguridad y el detalle del análisis de riesgos MAGERIT v3 quedan
custodiados en el repositorio FULKRO con identificador del proyecto
{{ project_id }} y son aportables a CCN-CERT bajo demanda.

## 5. Distintivo de conformidad

Conforme a CCN-STIC 809, esta entidad publicará el distintivo de
conformidad en su sede electrónica con URL:

```
{{ public_badge_url }}
```

El distintivo incluye firma digital Ed25519 verificable contra la
clave pública FULKRO publicada en `/api/v1/auth/public-key`.

## 6. Compromiso de mantenimiento

{{ client_name }} se compromete a:

- Mantener vigentes las medidas declaradas durante el periodo de
  conformidad (2 años).
{% if cliente.sector_aplicacion == 'publico' %}
- Notificar a CCN-CERT vía LUCIA cualquier incidente significativo
  conforme art. 33 RD 311/2022.
{% else %}
- Notificar a CCN-CERT cualquier incidente significativo conforme
  art. 33 RD 311/2022 (LUCIA aplica con carácter recomendado para
  sector privado bajo ENS · obligatoria para sector público).
{% endif %}
- Ejecutar autoevaluación o reauditoría antes del vencimiento.
- Disparar auditoría extraordinaria ante cambios sustanciales
  (nuevo CPD, fusión, cambio cloud) conforme art. 31.

## 7. Firma de la Dirección (órgano superior · CCN-STIC 809 Anexo A)

Conforme a la CCN-STIC 809 Anexo A, la Declaración de Conformidad la suscribe la
Dirección u órgano superior de la entidad, que asume la responsabilidad sobre la
seguridad del sistema. El Responsable de Seguridad gestiona y supervisa las
medidas; la declaración de conformidad es un acto de responsabilidad de la
Dirección.

| Campo | Valor |
|-------|-------|
| Nombre (Dirección / órgano superior) | {{ sponsor_name }} |
| Email | {{ sponsor_email }} |
| Firma | _____________ |
| Fecha de firma | _____________ |

---

*Documento generado por FULKRO conforme CCN-STIC 809 · RD 311/2022.*
*Plantilla E180 · v{{ template_version }}.*
*Identificador único: {{ cert_id }}.*
