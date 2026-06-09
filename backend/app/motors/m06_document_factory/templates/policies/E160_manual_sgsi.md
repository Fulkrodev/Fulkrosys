# Manual del Sistema de Gestión de Seguridad de la Información (SGSI)

**Cliente**: {{ client_name }}
**Sistema**: {{ system_name }}
**Categoría**: {{ system_category }}
**Versión**: {{ version }} · **Fecha**: {{ today }}

---

## 1. Alcance del SGSI

El presente Manual define el alcance, los objetivos y la estructura
del Sistema de Gestión de Seguridad de la Información (SGSI) de
{{ client_name }}, conforme al Esquema Nacional de Seguridad
(RD 311/2022) y, en su caso, a las normas internacionales aplicables
(ISO/IEC 27001).

### 1.1 Sistema cubierto

- **Nombre**: {{ system_name }}
- **Categoría ENS**: {{ system_category }}
- **Servicios prestados**: {{ services_summary }}
- **Activos esenciales**: {{ assets_essential_count }}

### 1.2 Exclusiones y justificación

{{ exclusions_text }}

## 2. Política de Seguridad referenciada

El presente Manual se desarrolla a partir de la Política de Seguridad
de la Información aprobada por la Dirección (referencia E100,
versión {{ psi_version }}).

## 3. Roles y responsabilidades (CCN-STIC 801)

| Rol | Persona | Email | Funciones principales |
|-----|---------|-------|----------------------|
{% for role in roles_table %}
| {{ role.role_name }} | {{ role.person }} | {{ role.email }} | {{ role.functions }} |
{% endfor %}

**Segregación funcional**: el Responsable de Seguridad (RSEG) y el
Responsable del Sistema (RSIS) recaen en personas distintas (CCN-STIC
801, no-conformidad mayor en caso contrario).

## 4. Procesos del SGSI

### 4.1 Gestión de riesgos

Análisis de riesgos MAGERIT v3 ejecutado periódicamente. Riesgos
residuales aceptados por la Dirección (acta de aceptación firmada).

### 4.2 Gestión de incidentes

Procedimiento E204 con árbol de decisión: clasificación → contención
→ erradicación → recuperación → lecciones aprendidas. Notificación
obligatoria CCN-CERT vía LUCIA en incidentes significativos
(art. 33 RD 311/2022).

### 4.3 Gestión de cambios

Procedimiento E203 con autorización formal previa, evaluación de
impacto en seguridad y registro en historial. Cambios sustanciales
disparan auditoría extraordinaria (art. 31 RD 311/2022).

### 4.4 Auditorías internas

Auditoría interna anual (procedimiento E216). Para Categoría Media/Alta:
auditoría externa por ENAC bienal (CCN-STIC 802).

### 4.5 Revisión por la Dirección

Acta anual de revisión SGSI por la Dirección, contemplando:
indicadores, hallazgos auditorías, acciones correctivas/preventivas,
cambios en el contexto, plan próximo año.

## 5. Documentación SGSI (4 niveles · CCN-STIC 805)

| Nivel | Tipo documento | Aprobación | Ejemplos |
|-------|---------------|------------|----------|
| 1 | Política Seguridad | Órgano superior gobierno | E100 PSI |
| 2 | Normativas | RSEG | E101-E126 (acceso, criptografía, teletrabajo, etc.) |
| 3 | Procedimientos | RSEG / RSIS | E200-E2XX (gestión incidentes, cambios, copias, etc.) |
| 4 | Instrucciones técnicas | Técnicos | Manuales operativos, scripts hardening |

## 6. Métricas e indicadores

Indicadores SGSI catálogo CCN-STIC 815 (obligatorio Media/Alta):

- Disponibilidad servicios críticos
- Tiempo medio detección/respuesta incidentes
- % cumplimiento medidas Anexo II
- Madurez CMM por familia (L0-L5)
- Cobertura concienciación personal

## 7. Mejora continua

Ciclo PDCA aplicado mediante:

- Revisión por dirección anual
- Auditorías internas anuales
- Auditorías externas (ENAC) bienales en Media/Alta
- Auditorías extraordinarias en cambios sustanciales
- INES anual (CCN-STIC 824/844)

---

## Aprobación

| Rol | Nombre | Firma | Fecha |
|-----|--------|-------|-------|
| Sponsor / Dirección | _____________ | _____________ | _____________ |
| Responsable Seguridad (RSEG) | _____________ | _____________ | _____________ |

---

*Documento generado por FULKRO conforme RD 311/2022 + CCN-STIC 805/815 +*
*ISO 27001 (mapping CCN-STIC 825). Plantilla E160 · v{{ template_version }}.*
