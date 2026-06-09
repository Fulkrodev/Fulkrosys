# INFORME INES · SNAPSHOT ANUAL DEL ESTADO DEL ENS DE {{ cliente.razon_social|upper }}

Documento {{ proyecto.codigo_documento_base }}-709 — Versión {{ proyecto.version_actual }}

## CONTROL DE CAMBIOS

| Versión | Fecha | Autor | Descripción |
|---|---|---|---|
| {{ proyecto.version_actual }} | {{ proyecto.fecha_aprobacion_inicial }} | {{ responsables.consultor.nombre }} | Versión inicial |

## REGISTRO DE APROBACIÓN

El presente Snapshot INES ha sido elaborado por {{ responsables.consultor.nombre }} en su condición de {{ responsables.consultor.cargo }}, revisado por {{ responsables.responsable_seguridad.nombre }} ({{ responsables.responsable_seguridad.cargo }}) y aprobado por {{ cliente.organo_aprobador_politicas }} de {{ cliente.razon_social }}.

## 1. OBJETO Y MARCO NORMATIVO

El presente documento es el **Snapshot Anual** que sirve de soporte al reporte INES (Informe Nacional del Estado de Seguridad) que {{ cliente.razon_social }} elabora conforme a:

- **Real Decreto 311/2022** Artículo 35 (reporte del estado de seguridad).
- **Guía CCN-STIC-824** Informe del Estado de Seguridad.
- **Plataforma INES** del Centro Criptológico Nacional (`https://ines.ccn-cert.cni.es`).

El reporte INES presenta una distinción de exigibilidad según la naturaleza de la entidad:

- Para **entidades del sector público** dentro del ámbito de aplicación del ENS (Administraciones Públicas y organismos vinculados), el reporte INES es **obligatorio con periodicidad anual**.
- Para **entidades del sector privado bajo ámbito ENS** ({{ cliente.razon_social }} en su condición de proveedora de servicios a Administraciones Públicas), su exigibilidad **depende de las cláusulas del pliego o contrato del cliente público** y de las instrucciones específicas del CCN cuando el sistema bajo alcance ENS preste servicios incluidos en infraestructuras esenciales.

Independientemente de la exigibilidad formal, **{{ cliente.razon_social }} elabora este Snapshot Anual** como evidencia interna de madurez del SGSI, manteniéndolo disponible para presentación al cliente público cuando éste lo solicite y como insumo del expediente que el auditor externo ENAC revisa durante el ciclo de certificación.

## 2. PERIODO DEL REPORTE

| Campo | Valor |
|---|---|
| Año reportado | {{ ines.año }} |
| Fecha de la fotografía | {{ ines.fecha_snapshot }} |
| Periodo cubierto | {{ ines.fecha_inicio }} a {{ ines.fecha_fin }} |
| Responsable del envío INES | {{ responsables.responsable_seguridad.nombre }} |
| Fecha programada de envío al CCN | {{ ines.fecha_envio }} |

## 3. DATOS DE LA ENTIDAD

| Campo | Valor |
|---|---|
| Razón social | {{ cliente.razon_social }} |
| NIF | {{ cliente.nif }} |
| Sector de actividad | {{ cliente.sector }} |
| Ámbito ENS | {{ cliente.ambito_ens }} |
| Personal en plantilla bajo alcance | {{ cliente.num_empleados_alcance }} |

## 4. SISTEMAS DECLARADOS EN INES

| Sistema | Alcance | Categoría | Estado certificación | Fecha próxima auditoría |
|---|---|:---:|:---:|:---:|
{% for sis in sistemas_declarados %}| {{ sis.nombre }} | {{ sis.alcance }} | {{ sis.categoria }} | {{ sis.estado_certificacion }} | {{ sis.proxima_auditoria }} |
{% endfor %}

## 5. NIVEL DE MADUREZ E0-E5 POR DIMENSIÓN

INES mide el nivel de madurez del sistema en cada dimensión de seguridad conforme a la escala E0-E5:

| Dimensión | Nivel objetivo | Nivel real | Estado |
|---|:---:|:---:|:---:|
| Confidencialidad | {{ madurez.confidencialidad.objetivo }} | {{ madurez.confidencialidad.real }} | {{ madurez.confidencialidad.estado }} |
| Integridad | {{ madurez.integridad.objetivo }} | {{ madurez.integridad.real }} | {{ madurez.integridad.estado }} |
| Disponibilidad | {{ madurez.disponibilidad.objetivo }} | {{ madurez.disponibilidad.real }} | {{ madurez.disponibilidad.estado }} |
| Autenticidad | {{ madurez.autenticidad.objetivo }} | {{ madurez.autenticidad.real }} | {{ madurez.autenticidad.estado }} |
| Trazabilidad | {{ madurez.trazabilidad.objetivo }} | {{ madurez.trazabilidad.real }} | {{ madurez.trazabilidad.estado }} |

**Niveles de madurez E0-E5**: E0 inexistente · E1 inicial · E2 reproducible · E3 definido · E4 gestionado · E5 optimizado.

## 6. CUMPLIMIENTO DE LAS MEDIDAS DEL ANEXO II

| Familia | Medidas aplicables | Cumplidas | Parciales | No cumplidas | Cumplimiento % |
|---|:---:|:---:|:---:|:---:|:---:|
{% for fam in cumplimiento_familia %}| {{ fam.nombre }} | {{ fam.aplicables }} | {{ fam.cumplidas }} | {{ fam.parciales }} | {{ fam.no_cumplidas }} | {{ fam.pct }}% |
{% endfor %}

**Cumplimiento global del Anexo II**: {{ cumplimiento_global }}%.

## 7. INCIDENTES SIGNIFICATIVOS DEL PERIODO

| ID | Fecha | Tipo | Severidad | Reportado a autoridades | Cerrado |
|---|:---:|:---:|:---:|:---:|:---:|
{% for inc in incidentes_periodo %}| {{ inc.id }} | {{ inc.fecha }} | {{ inc.tipo }} | {{ inc.severidad }} | {{ inc.reportado }} | {{ inc.cerrado }} |
{% endfor %}

**Total incidentes**: {{ resumen_incidentes.total }} · **con notificación a autoridades**: {{ resumen_incidentes.notificados }}.

## 8. AUDITORÍAS Y EJERCICIOS DEL PERIODO

| Tipo | Fecha | Resultado | Documento de referencia |
|---|:---:|:---:|:---:|
{% for aud in auditorias_periodo %}| {{ aud.tipo }} | {{ aud.fecha }} | {{ aud.resultado }} | {{ aud.documento }} |
{% endfor %}

## 9. PROGRAMA DE FORMACIÓN Y CONCIENCIACIÓN

| Indicador | Valor |
|---|:---:|
| Cobertura plan anual | {{ formacion.cobertura_pct }}% |
| Sesión de acogida en plazo | {{ formacion.acogida_pct }}% |
| Tasa de click en phishing (anual) | {{ formacion.click_pct }}% |
| Tasa de reporte de phishing | {{ formacion.reporte_pct }}% |

Documentos de referencia: E-500 (plan), E-502 (registro), E-503 (phishing), E-504 (KPIs).

## 10. PLAN DE TRATAMIENTO DE RIESGOS

| Indicador | Valor |
|---|:---:|
| Total riesgos identificados (Magerit) | {{ riesgos.total }} |
| Riesgo alto residual | {{ riesgos.alto_residual }} |
| Riesgos tratados en el periodo | {{ riesgos.tratados }} |
| Riesgos en seguimiento | {{ riesgos.seguimiento }} |

## 11. INVERSIÓN EN SEGURIDAD (PERIODO)

| Concepto | Importe |
|---|---|
| Infraestructura de seguridad (hardware + software) | {{ inversion.infraestructura }} |
| Servicios profesionales (consultoría, auditoría) | {{ inversion.servicios }} |
| Formación y concienciación | {{ inversion.formacion }} |
| Personal interno dedicado a seguridad (FTE equivalente) | {{ inversion.personal }} |
| **Total invertido en el periodo** | **{{ inversion.total }}** |

## 12. EVOLUCIÓN INTERANUAL

| Indicador | Valor año anterior | Valor año actual | Variación |
|---|:---:|:---:|:---:|
{% for ev in evolucion %}| {{ ev.indicador }} | {{ ev.año_anterior }} | {{ ev.año_actual }} | {{ ev.variacion }} |
{% endfor %}

## 13. PRINCIPALES HITOS DEL AÑO

{% for hito in hitos_año %}- {{ hito }}
{% endfor %}

## 14. OBJETIVOS PARA EL PRÓXIMO PERIODO

{% for obj in objetivos_proximo %}- {{ obj }}
{% endfor %}

## 15. CONCLUSIÓN

**Estado global del ENS de {{ cliente.razon_social }}**: {{ conclusion.estado_global }}.

{{ conclusion.texto }}

## TABLA DE FIRMAS

| Función | Nombre | Cargo | Fecha | Firma |
|---|---|---|---|---|
| Elaborado | {{ firmas.elaborado.nombre }} | {{ firmas.elaborado.cargo }} | {{ firmas.elaborado.fecha }} | {{ firmas.elaborado.firma_marca }} |
| Revisado | {{ firmas.revisado.nombre }} | {{ firmas.revisado.cargo }} | {{ firmas.revisado.fecha }} | {{ firmas.revisado.firma_marca }} |
| Aprobado | {{ firmas.aprobado.nombre }} | {{ firmas.aprobado.cargo }} | {{ firmas.aprobado.fecha }} | {{ firmas.aprobado.firma_marca }} |
